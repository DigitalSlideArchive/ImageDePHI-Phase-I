import os
import struct

from typing import Dict, List, BinaryIO

from tifftools.constants import TiffConstant, TiffConstantSet, Datatype, Tag, get_or_create_tag
from tifftools.exceptions import MustBeBigTiffException, TifftoolsException
from tifftools.path_or_fobj import OpenPathOrFobj, is_filelike_object

from tifftools.tifftools import write_tag_data, check_offset

from tqdm import trange


def write_tiff_conditional(
    ifds: List[Dict[str, dict]],
    # original_ifds: List[Dict[str, dict]],
    # redacted_ifds: List[Dict[str, dict]],
    path: str,
    allowExisting: bool = False
):
    """
    Write a tiff file based on data in a list of ifds. Always uses bigtiff.

    :param original_ifds: either a list of ifds of the original image.
    :param redacted_ifds: either a list of ifds of the redacted image.
    :param original_path: output path or stream.
    :param allowExisting: if False, raise an error if the path already exists.
    """
    # original_bigEndian = original_ifds[0].get('bigEndian', False)
    # redacted_bigEndian = redacted_ifds[0].get('bigEndian', False)
    bigEndian = ifds[0].get('bigEndian', False)

    if not allowExisting and not is_filelike_object(path) and os.path.exists(path):
        raise TifftoolsException('File already exists')

    with OpenPathOrFobj(path, 'wb') as dest:
        bom = '>' if bigEndian else '<'
        header = b'II' if not bigEndian else b'MM'
        header += struct.pack(bom + 'HHHQ', 0x2B, 8, 0, 0)
        ifdPtr = len(header) - 8
        dest.write(header)
        for ifd in ifds:
            ifdPtr = write_ifd_conditional(dest, bom, ifd, ifdPtr)


def write_ifd_conditional(
    dest: BinaryIO,
    bom: str,
    ifd: Dict[str, dict],
    ifdPtr: int,
    tagSet: TiffConstantSet = Tag
):
    """
    Write an IFD to a TIFF file. This copies image data from other tiff files. Always uses bigtiff.

    :param dest: the open file handle to write.
    :param bom: either '<' or '>' for using struct to encode values based on endian.
    :param ifd: The ifd record. This requires the tags dictionary and the path value.
    :param ifdPtr: a location to write the value of this ifd's start.
    :param tagSet: the TiffConstantSet class to use for tags.

    :return: the ifdPtr for the next ifd that could be written.
    """
    ptrpack = 'Q'
    tagdatalen = 8
    dest.seek(0, os.SEEK_END)
    ifdrecord = struct.pack(bom + 'Q', len(ifd['tags']))
    subifdPtrs: Dict[TiffConstant, int] = {}
    with OpenPathOrFobj(ifd['path_or_fobj'], 'rb') as src:
        for tag, taginfo in sorted(ifd['tags'].items()):
            tag = get_or_create_tag(
                tag,
                tagSet,
                **({'datatype': Datatype[taginfo['datatype']]} if taginfo.get('datatype') else {})
            )
            if tag.isIFD() or taginfo.get('datatype') in (Datatype.IFD, Datatype.IFD8):
                data = [0] * len(taginfo['ifds'])
                taginfo = taginfo.copy()
                taginfo['datatype'] = Datatype.IFD8
            else:
                data = taginfo['data']
            count = len(data)

            if tag.isOffsetData():
                if isinstance(tag.bytecounts, str):
                    data = write_tag_data(
                        dest, src, data,
                        ifd['tags'][int(tagSet[tag.bytecounts])]['data'],
                        ifd['size']
                    )
                else:
                    data = write_tag_data(dest, src, data, [tag.bytecounts] * count, ifd['size'])

                taginfo = taginfo.copy()
                taginfo['datatype'] = Datatype.LONG8

            if Datatype[taginfo['datatype']].pack:
                pack = Datatype[taginfo['datatype']].pack
                count //= len(pack)
                data = struct.pack(bom + pack * count, *data)
            elif Datatype[taginfo['datatype']] == Datatype.ASCII:
                # Handle null-seperated lists
                data = data.encode() + b'\x00'
                count = len(data)
            else:
                data = taginfo['data']

            tagrecord = struct.pack(bom + 'HH' + ptrpack, tag, taginfo['datatype'], count)

            if len(data) <= tagdatalen:
                if tag.isIFD() or taginfo.get('datatype') in (Datatype.IFD, Datatype.IFD8):
                    subifdPtrs[tag] = -(len(ifdrecord) + len(tagrecord))
                tagrecord += data + b'\x00' * (tagdatalen - len(data))
            else:
                # word alignment
                if dest.tell() % 2:
                    dest.write(b'\x00')
                if tag.isIFD() or taginfo.get('datatype') in (Datatype.IFD, Datatype.IFD8):
                    subifdPtrs[tag] = dest.tell()

                tagrecord += struct.pack(bom + ptrpack, dest.tell())
                dest.write(data)
            ifdrecord += tagrecord

    pos = dest.tell()
    # ifds are expected to be on word boundaries
    if pos % 2:
        dest.write(b'\x00')
        pos = dest.tell()
    dest.seek(ifdPtr)
    dest.write(struct.pack(bom + ptrpack, pos))
    dest.seek(0, os.SEEK_END)
    dest.write(ifdrecord)
    nextifdPtr = dest.tell()
    dest.write(struct.pack(bom + ptrpack, 0))
    write_sub_ifds_conditional(dest, bom, ifd, pos, subifdPtrs)
    return nextifdPtr


def write_sub_ifds_conditional(dest: BinaryIO, bom: str, ifd: Dict[str, dict], parentPos: int, subifdPtrs: Dict[TiffConstant, int]):
    """
    Write any number of SubIFDs to a TIFF file. These can be based on tags other than the SubIFD tag. Always uses bigtiff.

    :param dest: the open file handle to write.
    :param bom: eithter '<' or '>' for using struct to encode values based on endian.
    :param ifd: The ifd record. This requires the tags dictionary and the path value.
    :param parentPos: the location of the parent IFD used for relative storage locations.
    :param: subifdPtrs: a dictionary with tags as the keys and value with either
        (a) the absolute location to store the location of the first subifd, or
        (b) a negative number whose absolute value is added to parentPos to get
            the absolute location to store the location of the first subifd.
    """
    tagdatalen = 8
    for tag, subifdPtr in subifdPtrs.items():
        if subifdPtr < 0:
            subifdPtr = parentPos + (-subifdPtr)
        for subifd in ifd['tags'][int(tag)]['ifds']:
            if not isinstance(subifd, list):
                subifd = [subifd]
            nextSubifdPtr = subifdPtr
            for ifdInSubifd in subifd:
                nextSubifdPtr = write_ifd_conditional(dest, bom, ifdInSubifd, nextSubifdPtr, getattr(tag, 'tagset', None))
            subifdPtr += tagdatalen


def write_tag_data_conditional(
    dest: BinaryIO,
    original_src: BinaryIO,
    original_offsets: List[int],
    original_lengths: List[int],
    original_srclen: int,
    redacted_src: BinaryIO,
    redacted_offsets: List[int],
    redacted_lengths: List[int],
    redacted_srclen: int,
    is_redacted: List[bool],
):
    """
    Conditionally copy data from two source tiff to a destination tiff.

    :param dest: the destination file, opened to the location to write.
    :param original_src: the source file of the original image.
    :param original_offsets: an array of offsets where data will be copied from.
    :param original_lengths: an array of lengths to copy from each offset.
    :param original_srclen: the length of the source file.
    :param redacted_src: the source file of the redacted image.
    :param redacted_offsets: an array of offsets where data will be copied from.
    :param redacted_lengths: an array of lengths to copy from each offset.
    :param redacted_srclen: the length of the source file.
    :param is_redacted: an array of booleans specifying which src to copy from 

    :return: the offsets in the destination file corresponding to the data copied.
    """
    COPY_CHUNKSIZE = 1024 ** 2

    if len(original_offsets) != len(original_lengths) or len(redacted_offsets) != len(redacted_lengths):
        raise Exception('Offsets and byte counts do not correspond')
    
    destOffsets = [0] * len(original_offsets)
    original_offsetList = sorted([(offset, idx) for idx, offset in enumerate(original_offsets)])
    redacted_offsetList = sorted([(offset, idx) for idx, offset in enumerate(redacted_offsets)])

    for olidx in trange(len(original_offsetList)):
        if is_redacted[olidx]:
            offset, idx = redacted_offsetList[olidx]
            length = redacted_lengths[idx]
            if not check_offset(redacted_srclen, offset, length):
                continue
            src = redacted_src
        else:
            offset, idx = original_offsetList[olidx]
            length = original_lengths[idx]
            if not check_offset(original_srclen, offset, length):
                continue
            src = original_src
        
        src.seek(offset)
        destOffsets[idx] = dest.tell()
        
        while length > 0:
            data = src.read(min(length, COPY_CHUNKSIZE))
            dest.write(data)
            length -= len(data)
    
    return destOffsets
