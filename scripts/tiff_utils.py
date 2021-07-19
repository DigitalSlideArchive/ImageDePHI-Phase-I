import os
import struct

from typing import Dict, List, BinaryIO

import pyvips
from tifftools.constants import TiffConstant, TiffConstantSet, Datatype, Tag, get_or_create_tag
from tifftools.exceptions import MustBeBigTiffException, TifftoolsException
from tifftools.path_or_fobj import OpenPathOrFobj, is_filelike_object
from tifftools.tifftools import write_tag_data, check_offset, write_ifd, write_sub_ifds

from tqdm import trange


def write_tiff_conditional(
    original_ifds: List[Dict[str, dict]],
    redacted_ifds: List[Dict[str, dict]],
    path: str,
    svg: pyvips.Image,
    allowExisting: bool = False
):
    bigEndian = original_ifds[0].get('bigEndian', False)

    if not allowExisting and not is_filelike_object(path) and os.path.exists(path):
        raise TifftoolsException('File already exists')

    with OpenPathOrFobj(path, 'wb') as dest:
        bom = '>' if bigEndian else '<'
        header = b'II' if not bigEndian else b'MM'
        header += struct.pack(bom + 'HHHQ', 0x2B, 8, 0, 0)
        ifdPtr = len(header) - 8
        dest.write(header)

        ifdPtr = write_ifd_conditional(dest, bom, original_ifds[0], redacted_ifds[0], ifdPtr, svg)

        for ifd in original_ifds[1:]:
            ifdPtr = write_ifd(dest, bom, True, ifd, ifdPtr)


def find_directory(
    original_ifd: Dict[str, dict],
    redacted_ifds: List[Dict[str, dict]],
):
    try:
        original_tile_height = original_ifd['tags'][Tag.TileHeight.value]['data'][0]
        original_tile_width = original_ifd['tags'][Tag.TileWidth.value]['data'][0]
    except:
        return None

    for ifd in redacted_ifds:
        tile_height = ifd['tags'][Tag.TileHeight.value]['data'][0]
        tile_width = ifd['tags'][Tag.TileWidth.value]['data'][0]
        if (tile_height, tile_width) == (original_tile_height, original_tile_width):
            return ifd
    return None

def redacted_list(
    svg: pyvips.Image,
    width: int,
    height: int,
    tile_width: int,
    tile_height: int,
    num_tiles: int
) -> List[bool]:
    is_redacted: List[bool] = []
    tiles_across = (width + tile_width - 1) // tile_width
    tiles_down = (height + tile_height - 1) // tile_height

    print('calculating redacted tiles')
    for i in trange(num_tiles):
        x = (i % tiles_across) * tile_width
        y = (i // tiles_across) * tile_height
        w = min(tile_width, width - x)
        h = min(tile_height, height - y)
        tile_max = svg.extract_area(x, y, w, h).extract_band(3).max()
        is_redacted.append(tile_max > 0)

    return is_redacted


def write_ifd_conditional(
    dest: BinaryIO,
    bom: str,
    ifd: Dict[str, dict],
    redacted_ifd: Dict[str, dict],
    ifdPtr: int,
    svg: pyvips.Image
):
    ptrpack = 'Q'
    tagdatalen = 8
    dest.seek(0, os.SEEK_END)
    ifdrecord = struct.pack(bom + 'Q', len(ifd['tags']))
    subifdPtrs: Dict[TiffConstant, int] = {}
    tagSet = Tag

    with OpenPathOrFobj(ifd['path_or_fobj'], 'rb') as src, OpenPathOrFobj(redacted_ifd['path_or_fobj'], 'rb') as redacted_src:
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
                    width = ifd['tags'][Tag.ImageWidth.value]['data'][0]
                    height = ifd['tags'][Tag.ImageHeight.value]['data'][0]
                    tile_width = ifd['tags'][Tag.TileWidth.value]['data'][0]
                    tile_height = ifd['tags'][Tag.TileHeight.value]['data'][0]
                    num_tiles = len(data)
                    is_redacted = redacted_list(svg, width, height, tile_width, tile_height, num_tiles)
                    data = write_tag_data_conditional(
                        dest,
                        src,
                        data,
                        ifd['tags'][int(tagSet[tag.bytecounts])]['data'],
                        ifd['size'],
                        redacted_src,
                        redacted_ifd['tags'][Tag.TileOffsets.value]['data'],
                        redacted_ifd['tags'][Tag.TileByteCounts.value]['data'],
                        redacted_ifd['size'],
                        is_redacted
                    )
                elif isinstance(tag.bytecounts, str):
                    data = write_tag_data(
                        dest,
                        src,
                        data,
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

    if len(original_offsets) != len(original_lengths) or len(redacted_offsets) != len(redacted_lengths):
        raise Exception('Offsets and byte counts do not correspond')
    
    destOffsets = [0] * len(original_offsets)
    original_offsetList = sorted([(offset, idx) for idx, offset in enumerate(original_offsets)])
    redacted_offsetList = sorted([(offset, idx) for idx, offset in enumerate(redacted_offsets)])

    print('writing redacted files')
    for olidx in trange(len(original_offsetList)):
        if is_redacted[olidx]:
            offset, idx = redacted_offsetList[olidx]
            length = redacted_lengths[idx]
            if not check_offset(redacted_srclen, offset, length):
                continue
            # src = redacted_src
            src = original_src
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
