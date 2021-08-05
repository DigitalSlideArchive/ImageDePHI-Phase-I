import copy
import os
import struct

from typing import Dict, List, BinaryIO, Tuple

import pyvips
from tifftools.constants import TiffConstant, TiffConstantSet, Datatype, Tag, get_or_create_tag
from tifftools.exceptions import MustBeBigTiffException, TifftoolsException
from tifftools.path_or_fobj import OpenPathOrFobj, is_filelike_object
from tifftools.tifftools import write_tag_data, check_offset, write_ifd, write_sub_ifds

from tqdm import trange

from models import IFDType
from utils import get_ifd_type, check_compatible_ifds


def write_tiff_conditional(
    original_ifds: List[Dict[str, dict]],
    redacted_ifds: List[Dict[str, dict]],
    input_filename: str,
    output_filename: str,
    svg: pyvips.Image,
    allowExisting: bool = False
):
    bigEndian = original_ifds[0].get('bigEndian', False)

    if not allowExisting and not is_filelike_object(output_filename) and os.path.exists(output_filename):
        raise TifftoolsException('File already exists')

    with OpenPathOrFobj(output_filename, 'wb') as dest:
        bom = '>' if bigEndian else '<'
        header = b'II' if not bigEndian else b'MM'
        header += struct.pack(bom + 'HHHQ', 0x2B, 8, 0, 0)
        ifdPtr = len(header) - 8
        dest.write(header)

        for i, original_ifd in enumerate(original_ifds):
            ifd_type = get_ifd_type(original_ifd)
            if ifd_type == IFDType.tile:
                redacted_ifd = find_matching_ifd(original_ifd, redacted_ifds)
                
                # check if original and redacted ifd are compatible

                is_redacted = redacted_list(svg, original_ifd)
                modified_ifd = conditional_ifd(original_ifd, redacted_ifd, is_redacted)
                ifdPtr = write_ifd_conditional(dest, bom, modified_ifd, original_ifd, redacted_ifd, ifdPtr, is_redacted)
            else:
                ifdPtr = write_ifd(dest, bom, True, original_ifd, ifdPtr)


def find_matching_ifd(tile_ifd: Dict[str, dict], ifds: List[Dict[str, dict]]):
    height = tile_ifd['tags'][Tag.ImageHeight.value]['data'][0]
    width = tile_ifd['tags'][Tag.ImageWidth.value]['data'][0]

    for ifd in ifds:
        ifd_height = ifd['tags'][Tag.ImageHeight.value]['data'][0]
        ifd_width = ifd['tags'][Tag.ImageWidth.value]['data'][0]

        if (ifd_height, ifd_width) == (height, width):
            return ifd

    return None


def conditional_ifd(
    original_ifd: Dict[str, dict],
    redacted_ifd: Dict[str, dict],
    is_redacted: List[bool],
):
    ifd = copy.deepcopy(original_ifd)
    tile_offsets = []
    tile_bytecounts = []

    original_tile_offsets = original_ifd['tags'][Tag.TileOffsets.value]['data']
    original_tile_bytecounts = original_ifd['tags'][Tag.TileByteCounts.value]['data']
    redacted_tile_offsets = redacted_ifd['tags'][Tag.TileOffsets.value]['data']
    redacted_tile_bytecounts = redacted_ifd['tags'][Tag.TileByteCounts.value]['data']

    offset = original_tile_offsets[0]
    for i, redacted in enumerate(is_redacted):
        if redacted:
            bytecount = redacted_tile_bytecounts[i]
        else:
            bytecount = original_tile_bytecounts[i]
        tile_offsets.append(offset)
        tile_bytecounts.append(bytecount)
        offset += bytecount

    ifd['tags'][Tag.TileOffsets.value]['data'] = tile_offsets
    ifd['tags'][Tag.TileByteCounts.value]['data'] = tile_bytecounts

    return ifd


def redacted_list(
    svg: pyvips.Image,
    ifd: Dict[str, dict],
    verbose: bool = True
) -> Tuple[List[bool], pyvips.Image]:
    width = ifd['tags'][Tag.ImageWidth.value]['data'][0]
    height = ifd['tags'][Tag.ImageHeight.value]['data'][0]
    tile_width = ifd['tags'][Tag.TileWidth.value]['data'][0]
    tile_height = ifd['tags'][Tag.TileHeight.value]['data'][0]

    is_redacted: List[bool] = []
    tiles_across = (width + tile_width - 1) // tile_width
    tiles_down = (height + tile_height - 1) // tile_height
    num_tiles = tiles_across * tiles_down

    original_height, original_width = svg.height, svg.width
    resized_svg = svg.resize(width / original_width)

    if verbose:
        print('calculating redacted tiles')
        loop = trange
    else:
        loop = range

    for i in loop(num_tiles):
        x = (i % tiles_across) * tile_width
        y = (i // tiles_across) * tile_height
        w = min(tile_width, width - x)
        h = min(tile_height, height - y)
        tile_max = resized_svg.extract_area(x, y, w, h).extract_band(3).max()
        is_redacted.append(tile_max > 0)

    return is_redacted, resized_svg


def write_ifd_conditional(
    dest: BinaryIO,
    bom: str,
    ifd: Dict[str, dict],
    original_ifd: Dict[str, dict],
    redacted_ifd: Dict[str, dict],
    ifdPtr: int,
    is_redacted: List[bool],
):
    ptrpack = 'Q'
    tagdatalen = 8
    dest.seek(0, os.SEEK_END)
    ifdrecord = struct.pack(bom + 'Q', len(ifd['tags']))
    subifdPtrs: Dict[TiffConstant, int] = {}
    tagSet = Tag

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
                if tag.value == Tag.TileOffsets.value:
                    with OpenPathOrFobj(original_ifd['path_or_fobj'], 'rb') as original_src, OpenPathOrFobj(redacted_ifd['path_or_fobj'], 'rb') as redacted_src:
                        data = write_tag_data_conditional(
                            dest=dest,
                            original_src=original_src,
                            original_offsets=original_ifd['tags'][Tag.TileOffsets.value]['data'],
                            original_lengths=original_ifd['tags'][Tag.TileByteCounts.value]['data'],
                            original_srclen=original_ifd['size'],
                            redacted_src=redacted_src,
                            redacted_offsets=redacted_ifd['tags'][Tag.TileOffsets.value]['data'],
                            redacted_lengths=redacted_ifd['tags'][Tag.TileByteCounts.value]['data'],
                            redacted_srclen=redacted_ifd['size'],
                            is_redacted=is_redacted
                        )
                elif isinstance(tag.bytecounts, str):
                    data = write_tag_data(
                        dest=dest,
                        src=src,
                        offsets=data,
                        lengths=ifd['tags'][int(tagSet[tag.bytecounts])]['data'],
                        srclen=ifd['size']
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


def write_sub_ifds_conditional(
    dest: BinaryIO,
    bom: str,
    ifd: Dict[str, dict],
    parentPos: int,
    subifdPtrs: Dict[TiffConstant, int]
):
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
    COPY_CHUNKSIZE = 1024 ** 2

    if len(original_offsets) != len(original_lengths):
        raise TifftoolsException('Original image offsets and byte counts do not correspond')
    if len(redacted_offsets) != len(redacted_lengths):
        raise TifftoolsException('Redacted image offsets and byte counts do not correspond')
    
    destOffsets = [0] * len(original_offsets)
    original_offsetList = [(offset, idx) for idx, offset in enumerate(original_offsets)]
    redacted_offsetList = [(offset, idx) for idx, offset in enumerate(redacted_offsets)]

    for olidx in range(len(original_offsetList)):
        if is_redacted[olidx]:
            offset, idx = redacted_offsetList[olidx]
            length = redacted_lengths[idx]
            src = redacted_src
            srclen = redacted_srclen
        else:
            offset, idx = original_offsetList[olidx]
            length = original_lengths[idx]
            src = original_src
            srclen = original_srclen

        if offset and check_offset(srclen, offset, length):
            src.seek(offset)
            destOffsets[idx] = dest.tell()

            while length:
                data = src.read(min(length, COPY_CHUNKSIZE))
                dest.write(data)
                length -= len(data)

    return destOffsets
