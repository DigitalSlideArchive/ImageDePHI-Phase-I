import argparse
import copy
import dataclasses
import enum
import json
import os
import re
import struct
import sys
import tempfile
from typing import Any, BinaryIO, Dict, List

import pyvips
from tifftools.constants import (
    Compression,
    Datatype,
    EstimateJpegQuality,
    Photometric,
    Tag,
    TiffConstant,
    TiffConstantSet,
    get_or_create_tag,
)
from tifftools.path_or_fobj import OpenPathOrFobj
from tifftools.tifftools import check_offset, read_tiff, write_ifd, write_tag_data


@dataclasses.dataclass
class Polygon:
    points: List[list]
    fill_color: str
    line_color: str
    line_width: float


class IFDType(str, enum.Enum):
    tile = 'tile'
    thumbnail = 'thumbnail'
    label = 'label'
    macro = 'macro'
    other = 'other'


def get_polygons(annotation_filename: str) -> List[Polygon]:
    """Extract polygon list from json annotation file."""
    with open(annotation_filename, 'r') as f:
        data = json.load(f)
    elements = data['annotation']['elements']
    polygons: List[Polygon] = []
    for e in elements:
        if e['type'] == 'polyline':
            points = e.get('points', [])
            if points:
                fill_color = e.get('fillColor', 'black')
                line_color = e.get('lineColor', 'black')
                line_width = e.get('lineWidth', 1)
                polygon = Polygon(points, fill_color, line_color, line_width)
                polygons.append(polygon)
    return polygons


def get_ifd_type(ifd: Dict[str, Any]) -> IFDType:
    """Identify the type of IFD."""
    if Tag.TileOffsets.value in ifd['tags']:
        return IFDType.tile

    new_subfile_type = ifd['tags'].get(Tag.NewSubfileType.value)
    if new_subfile_type:
        key = new_subfile_type['data'][0]
        if key == 0:
            return IFDType.thumbnail
        elif key == 1:
            return IFDType.label
        elif key == 9:
            return IFDType.macro
        else:
            return IFDType.other
    else:
        return IFDType.other


def create_svg(width: int, height: int, polygons: List[Polygon]) -> pyvips.Image:
    """Create an SVG image using polygons."""
    svg_str = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'

    for polygon in polygons:
        if isinstance(polygon.points[0][0], list):
            items = polygon.points
        else:
            items = [polygon.points]

        svg_str += f'<path fill-rule="evenodd" fill="{polygon.fill_color}" d="'
        for item in items:
            points = ' '.join([f'{pt[0]},{pt[1]}' for pt in item])
            svg_str += f'M {points} z '
        svg_str += '" />'

    svg_str += '</svg>'

    svg_image = pyvips.Image.svgload_buffer(svg_str.encode())
    return svg_image


def conditional_ifd(
    original_ifd: Dict[str, Any],
    redacted_ifd: Dict[str, Any],
    is_redacted: List[bool],
) -> Dict[str, Any]:
    """Construct an IFD conditionally from two IFD."""
    ifd = copy.deepcopy(original_ifd)
    tile_offsets: List[int] = []
    tile_bytecounts: List[int] = []

    original_tile_offsets = original_ifd['tags'][Tag.TileOffsets.value]['data']
    original_tile_bytecounts = original_ifd['tags'][Tag.TileByteCounts.value]['data']
    redacted_tile_offsets = redacted_ifd['tags'][Tag.TileOffsets.value]['data']
    redacted_tile_bytecounts = redacted_ifd['tags'][Tag.TileByteCounts.value]['data']

    if len(original_tile_offsets) != len(original_tile_bytecounts):
        raise ValueError('Original image offsets and byte counts do not correspond')
    if len(redacted_tile_offsets) != len(redacted_tile_bytecounts):
        raise ValueError('Redacted image offsets and byte counts do not correspond')
    if len(original_tile_offsets) != len(redacted_tile_offsets):
        raise ValueError('Original and redacted image offsets do not correspond')
    if len(original_tile_bytecounts) != len(redacted_tile_bytecounts):
        raise ValueError('Original and redacted image byte counts do not correspond')

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


def redacted_list(svg: pyvips.Image, ifd: Dict[str, Any]) -> List[bool]:
    """Extract list of which tiles have been modified in an SVG."""
    # extract tile data
    width = ifd['tags'][Tag.ImageWidth.value]['data'][0]
    height = ifd['tags'][Tag.ImageHeight.value]['data'][0]
    tile_width = ifd['tags'][Tag.TileWidth.value]['data'][0]
    tile_height = ifd['tags'][Tag.TileHeight.value]['data'][0]
    tiles_across = (width + tile_width - 1) // tile_width
    tiles_down = (height + tile_height - 1) // tile_height
    num_tiles = tiles_across * tiles_down

    # resize svg if needed
    original_width, original_height = svg.width, svg.height
    if (original_width, original_height) != (width, height):
        resized_svg = svg.resize(width / original_width)
    else:
        resized_svg = svg

    is_redacted: List[bool] = []
    for idx in range(num_tiles):
        x = (idx % tiles_across) * tile_width
        y = (idx // tiles_across) * tile_height
        w = min(tile_width, width - x)
        h = min(tile_height, height - y)
        tile_max = resized_svg.extract_area(x, y, w, h).extract_band(3).max()
        is_redacted.append(tile_max > 0)

    return is_redacted


def write_ifd_conditionally(
    dest: BinaryIO,
    bom: str,
    ifd: Dict[str, Any],
    original_ifd: Dict[str, Any],
    redacted_ifd: Dict[str, Any],
    is_redacted: List[bool],
    ifdPtr: int,
    tagSet: TiffConstantSet = Tag,
) -> int:
    """Copied from tifftools.tifftools.write_ifd but with conditional modification."""
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
                **({'datatype': Datatype[taginfo['datatype']]} if taginfo.get('datatype') else {}),
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
                    # special write for tiles only
                    with OpenPathOrFobj(
                        original_ifd['path_or_fobj'], 'rb'
                    ) as original_src, OpenPathOrFobj(
                        redacted_ifd['path_or_fobj'], 'rb'
                    ) as redacted_src:
                        data = write_tag_data_conditionally(
                            dest=dest,
                            original_src=original_src,
                            original_offsets=original_ifd['tags'][Tag.TileOffsets.value]['data'],
                            original_lengths=original_ifd['tags'][Tag.TileByteCounts.value]['data'],
                            original_srclen=original_ifd['size'],
                            redacted_src=redacted_src,
                            redacted_offsets=redacted_ifd['tags'][Tag.TileOffsets.value]['data'],
                            redacted_lengths=redacted_ifd['tags'][Tag.TileByteCounts.value]['data'],
                            redacted_srclen=redacted_ifd['size'],
                            is_redacted=is_redacted,
                        )
                elif isinstance(tag.bytecounts, str):
                    data = write_tag_data(
                        dest=dest,
                        src=src,
                        offsets=data,
                        lengths=ifd['tags'][int(tagSet[tag.bytecounts])]['data'],
                        srclen=ifd['size'],
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
    write_sub_ifds_conditionally(
        dest=dest,
        bom=bom,
        ifd=ifd,
        original_ifd=original_ifd,
        redacted_ifd=redacted_ifd,
        parentPos=pos,
        subifdPtrs=subifdPtrs,
        is_redacted=is_redacted,
    )
    return nextifdPtr


def write_sub_ifds_conditionally(
    dest: BinaryIO,
    bom: str,
    ifd: Dict[str, Any],
    original_ifd: Dict[str, Any],
    redacted_ifd: Dict[str, Any],
    is_redacted: List[bool],
    parentPos: int,
    subifdPtrs: Dict[TiffConstant, int],
    tagSet: TiffConstantSet = Tag,
):
    """Copied from tifftools.tifftools.write_sub_ifds but with conditional modification."""
    tagdatalen = 8
    for tag, subifdPtr in subifdPtrs.items():
        if subifdPtr < 0:
            subifdPtr = parentPos + (-subifdPtr)
        for subifd in ifd['tags'][int(tag)]['ifds']:
            if not isinstance(subifd, list):
                subifd = [subifd]
            nextSubifdPtr = subifdPtr
            for ifdInSubifd in subifd:
                nextSubifdPtr = write_ifd_conditionally(
                    dest=dest,
                    bom=bom,
                    ifd=ifdInSubifd,
                    original_ifd=original_ifd,
                    redacted_ifd=redacted_ifd,
                    is_redacted=is_redacted,
                    ifdPtr=nextSubifdPtr,
                    tagSet=getattr(tag, 'tagset', None),
                )
            subifdPtr += tagdatalen


def write_tag_data_conditionally(
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
) -> List[int]:
    """Conditionally write tag data from two IFD based on boolean list."""
    COPY_CHUNKSIZE = 1024 ** 2

    if len(original_offsets) != len(original_lengths):
        raise ValueError('Original image offsets and byte counts do not correspond')
    if len(redacted_offsets) != len(redacted_lengths):
        raise ValueError('Redacted image offsets and byte counts do not correspond')
    if len(original_offsets) != len(redacted_offsets):
        raise ValueError('Original and redacted image offsets do not correspond')
    if len(original_lengths) != len(redacted_lengths):
        raise ValueError('Original and redacted image byte counts do not correspond')
    if not (len(original_offsets) == len(original_lengths) == len(is_redacted)):
        raise ValueError('Original image data does not correspond with redacted list')
    if not (len(redacted_offsets) == len(redacted_lengths) == len(is_redacted)):
        raise ValueError('Redacted image data does not correspond with redacted list')

    destOffsets = [0] * len(original_offsets)

    for idx, redacted in enumerate(is_redacted):
        if redacted:
            offset = redacted_offsets[idx]
            length = redacted_lengths[idx]
            src = redacted_src
            srclen = redacted_srclen
        else:
            offset = original_offsets[idx]
            length = original_lengths[idx]
            src = original_src
            srclen = original_srclen

        if offset and check_offset(srclen, offset, length):
            src.seek(offset)
            destOffsets[idx] = dest.tell()

            while length > 0:
                data = src.read(min(length, COPY_CHUNKSIZE))
                dest.write(data)
                length -= len(data)

    return destOffsets


def redact_tiff(input_filename: str, output_filename: str, polygons: List[Polygon], verbose: bool):
    """Remove polygons from input TIFF and output a modified redacted TIFF."""
    original_info = read_tiff(input_filename)
    original_ifds = original_info['ifds']
    width = original_ifds[0]['tags'][Tag.ImageWidth.value]['data'][0]
    height = original_ifds[0]['tags'][Tag.ImageHeight.value]['data'][0]
    bigEndian = original_ifds[0].get('bigEndian', False)

    # construct svg overlay image
    svg_image = create_svg(width, height, polygons)

    with OpenPathOrFobj(output_filename, 'wb') as dest:
        bom = '>' if bigEndian else '<'
        header = b'II' if not bigEndian else b'MM'
        header += struct.pack(bom + 'HHHQ', 0x2B, 8, 0, 0)
        ifdPtr = len(header) - 8
        dest.write(header)

        for i, original_ifd in enumerate(original_ifds):
            ifd_type = get_ifd_type(original_ifd)
            if verbose:
                print(f'=== ifd {i}: {ifd_type} ===')

            if ifd_type == IFDType.tile:
                # extract original image ifd properties
                original_image_width = original_ifd['tags'][Tag.ImageWidth.value]['data'][0]
                original_image_height = original_ifd['tags'][Tag.ImageHeight.value]['data'][0]
                original_tile_width = original_ifd['tags'][Tag.TileWidth.value]['data'][0]
                original_tile_height = original_ifd['tags'][Tag.TileHeight.value]['data'][0]
                original_photometric = original_ifd['tags'][Tag.Photometric.value]['data'][0]
                original_compression = original_ifd['tags'][Tag.Compression.value]['data'][0]

                if original_photometric == Photometric.RGB.value:
                    original_rgbjpeg = True
                elif original_photometric == Photometric.YCbCr.value:
                    original_rgbjpeg = False
                else:
                    raise ValueError(
                        f'Unsupported photometric: {Photometric[original_photometric]}'
                    )

                if original_compression == Compression.JPEG.value:
                    original_jpeg_tables = original_ifd['tags'][Tag.JPEGTables.value]['data']
                    original_jpeg_quality = EstimateJpegQuality(original_jpeg_tables)
                else:
                    if Tag.ImageDescription.value in original_ifds['tags']:
                        original_image_description = original_ifds['tags'][Tag.ImageDesciption][
                            'data'
                        ]
                    else:
                        original_image_description = ''
                    match = re.search(r'Q=\d+', original_image_description)
                    if match:
                        original_jpeg_quality = int(match[0][2:])
                    else:
                        original_jpeg_quality = 70

                # create redacted image
                original_image = pyvips.Image.tiffload(input_filename, page=i)
                if (original_image_width, original_image_height) != (width, height):
                    resized_svg = svg_image.resize(original_image_width / width)
                else:
                    resized_svg = svg_image
                redacted_image = original_image.composite([resized_svg], pyvips.BlendMode.OVER)

                with tempfile.NamedTemporaryFile(suffix=f'{i}_out.tiff') as tmp:
                    # write redacted image to temporary file
                    if verbose:
                        print('creating redacted image')
                    redacted_image.tiffsave(
                        tmp.name,
                        tile=True,
                        tile_width=original_tile_width,
                        tile_height=original_tile_height,
                        pyramid=False,
                        bigtiff=True,
                        rgbjpeg=original_rgbjpeg,
                        compression='jpeg',
                        Q=original_jpeg_quality,
                    )

                    # extract redacted image ifd properties
                    redacted_info = read_tiff(tmp.name)
                    redacted_ifd = redacted_info['ifds'][0]
                    redacted_tile_width = redacted_ifd['tags'][Tag.TileWidth.value]['data'][0]
                    redacted_tile_height = redacted_ifd['tags'][Tag.TileHeight.value]['data'][0]
                    redacted_photometric = redacted_ifd['tags'][Tag.Photometric.value]['data'][0]
                    redacted_compression = redacted_ifd['tags'][Tag.Compression.value]['data'][0]
                    redacted_jpeg_tables = redacted_ifd['tags'][Tag.JPEGTables.value]['data']
                    redacted_jpeg_quality = EstimateJpegQuality(redacted_jpeg_tables)

                    # check if can redacted image is compatible
                    if (
                        original_tile_width != redacted_tile_width
                        or original_tile_height != redacted_tile_height
                        or original_photometric != redacted_photometric
                        or original_compression != redacted_compression
                        or original_jpeg_quality != redacted_jpeg_quality
                    ):
                        if verbose:
                            print('cannot use conditional tiles')
                            print('writing to output image')
                        ifdPtr = write_ifd(dest, bom, True, redacted_ifd, ifdPtr)
                    else:
                        if verbose:
                            print('using conditional tiles')
                        is_redacted = redacted_list(svg_image, original_ifd)
                        modified_ifd = conditional_ifd(original_ifd, redacted_ifd, is_redacted)
                        # construct combined ifd
                        if verbose:
                            print('writing to output image')
                        ifdPtr = write_ifd_conditionally(
                            dest=dest,
                            bom=bom,
                            ifd=modified_ifd,
                            original_ifd=original_ifd,
                            redacted_ifd=redacted_ifd,
                            is_redacted=is_redacted,
                            ifdPtr=ifdPtr,
                        )
            elif ifd_type == IFDType.thumbnail:
                # extract original image ifd properties
                original_image_width = original_ifd['tags'][Tag.ImageWidth.value]['data'][0]
                original_image_height = original_ifd['tags'][Tag.ImageHeight.value]['data'][0]

                # create redacted image
                original_image = pyvips.Image.tiffload(input_filename, page=i)
                if (original_image_width, original_image_height) != (width, height):
                    resized_svg = svg_image.resize(original_image_width / width)
                else:
                    resized_svg = svg_image
                redacted_image = original_image.composite([resized_svg], pyvips.BlendMode.OVER)

                with tempfile.NamedTemporaryFile(suffix=f'{i}_out.tiff') as tmp:
                    # write redacted image to temporary file
                    if verbose:
                        print('creating redacted image')
                    redacted_image.tiffsave(
                        tmp.name,
                        tile=False,
                        pyramid=False,
                        bigtiff=True,
                    )

                    # extract redacted image ifd properties
                    redacted_info = read_tiff(tmp.name)
                    redacted_ifd = redacted_info['ifds'][0]

                    # write missing tags
                    for tag in original_ifd['tags'].keys():
                        if tag not in redacted_ifd['tags']:
                            redacted_ifd['tags'][tag] = original_ifd['tags'][tag]

                    # construct combined ifd
                    if verbose:
                        print('writing to output image')
                    ifdPtr = write_ifd(dest, bom, True, redacted_ifd, ifdPtr)
            else:
                if verbose:
                    print('writing to output image')
                ifdPtr = write_ifd(dest, bom, True, original_ifd, ifdPtr)


def get_args():
    parser = argparse.ArgumentParser(description='Redact a tiff file using annotation polygons.')
    parser.add_argument('source', type=str, help='Source image filename')
    parser.add_argument('--out', '-o', type=str, required=True, help='Output image filename')
    parser.add_argument('--annotation', '-a', type=str, required=True, help='Annotation filename')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    return parser.parse_args()


def main(args):
    input_filename = args.source
    output_filename = args.out
    annotation_filename = args.annotation
    verbose = args.verbose

    if input_filename == output_filename:
        sys.exit('error: output filename cannot be the same as the source filename')

    polygons = get_polygons(annotation_filename)
    redact_tiff(input_filename, output_filename, polygons, verbose)


if __name__ == '__main__':
    args = get_args()
    main(args)
