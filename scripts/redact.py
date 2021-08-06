import argparse
import json
import time
import struct
from dataclasses import dataclass
from enum import Enum
from tempfile import NamedTemporaryFile
from typing import Dict, List, Tuple

import pyvips
from tifftools.constants import Tag, EstimateJpegQuality
from tifftools.path_or_fobj import OpenPathOrFobj
from tifftools.tifftools import read_tiff, write_ifd

from tiff_utils import conditional_ifd, redacted_list, write_ifd_conditional


@dataclass
class Polygon:
    points: List[Tuple[float]]
    fill_color: str
    line_color: str
    line_width: float


class IFDType(str, Enum):
    tile = 'tile'
    thumbnail = 'thumbnail'
    label = 'label'
    macro = 'macro'
    other = 'other'


def get_polygons(annotation_filename: str) -> List[Polygon]:
    with open(annotation_filename, 'r') as f:
        data = json.load(f)
    elements = data['annotation']['elements']
    polygons: List[Polygon] = []
    for e in elements:
        if e['type'] == 'polyline':
            points = e['points']
            fill_color = e['fillColor']
            line_color = e['lineColor']
            line_width = e['lineWidth']
            polygon = Polygon(points, fill_color, line_color, line_width)
            polygons.append(polygon)
    return polygons


def get_ifd_type(ifd: Dict[str, dict]) -> IFDType:
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
    svg_str = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
    for polygon in polygons:
        points = ' '.join([f'{pt[0]},{pt[1]}' for pt in polygon.points])
        svg_str += f'<polygon points="{points}" stroke="none" fill="{polygon.fill_color}" />'
    svg_str += '</svg>'
    svg_image = pyvips.Image.svgload_buffer(svg_str.encode())
    return svg_image


def apply_redaction(input_filename: str, output_filename: str, polygons: List[Polygon], verbose: bool):
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
                original_compression = original_ifd['tags'][Tag.Compression.value]['data'][0]
                original_photometric = original_ifd['tags'][Tag.Photometric.value]['data'][0]
                original_jpeg_tables = original_ifd['tags'][Tag.JPEGTables.value]['data']
                original_jpeg_quality = EstimateJpegQuality(original_jpeg_tables)

                # create redacted image
                original_image = pyvips.Image.tiffload(input_filename, page=i)
                if (original_image_width, original_image_height) != (width, height):
                    resized_svg = svg_image.resize(original_image_width / width)
                else:
                    resized_svg = svg_image
                redacted_image = original_image.composite([resized_svg], pyvips.BlendMode.OVER)

                with NamedTemporaryFile(suffix='{i}_out.tiff') as tmp:
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
                        rgbjpeg=(original_photometric == 2),
                        compression='jpeg',
                        Q=original_jpeg_quality,
                    )

                    # extract redacted image ifd properties
                    redacted_info = read_tiff(tmp.name)
                    redacted_ifd = redacted_info['ifds'][0]
                    redacted_tile_width = redacted_ifd['tags'][Tag.TileWidth.value]['data'][0]
                    redacted_tile_height = redacted_ifd['tags'][Tag.TileHeight.value]['data'][0]
                    redacted_compression = redacted_ifd['tags'][Tag.Compression.value]['data'][0]
                    redacted_photometric = redacted_ifd['tags'][Tag.Photometric.value]['data'][0]
                    redacted_jpeg_tables = redacted_ifd['tags'][Tag.JPEGTables.value]['data']
                    redacted_jpeg_quality = EstimateJpegQuality(redacted_jpeg_tables)

                    # check if can redacted image is compatible
                    if original_tile_width != redacted_tile_width:
                        raise ValueError('Original tile width does not match redacted tile width')
                    if original_tile_height != redacted_tile_height:
                        raise ValueError('Original tile height does not match redacted tile height')
                    if original_compression != redacted_compression:
                        raise ValueError('Original compression does not match redacted compression')
                    if original_photometric != redacted_photometric:
                        raise ValueError('Original photometric does not match redacted photometric')
                    if original_jpeg_quality != redacted_jpeg_quality:
                        raise ValueError('Original JPEG quality do not match redacted JPEG quality')
                    
                    # construct combined ifd
                    if verbose:
                        print('creating combined image')
                    is_redacted = redacted_list(svg_image, original_ifd)
                    modified_ifd = conditional_ifd(original_ifd, redacted_ifd, is_redacted)
                    ifdPtr = write_ifd_conditional(
                        dest=dest,
                        bom=bom,
                        ifd=modified_ifd,
                        original_ifd=original_ifd,
                        redacted_ifd=redacted_ifd,
                        is_redacted=is_redacted,
                        ifdPtr=ifdPtr,
                    )
            elif ifd_type == IFDType.thumbnail:
                # extract tiff properties
                original_image_width = original_ifd['tags'][Tag.ImageWidth.value]['data'][0]
                original_image_height = original_ifd['tags'][Tag.ImageHeight.value]['data'][0]
                original_compression = original_ifd['tags'][Tag.Compression.value]['data'][0]
                original_photometric = original_ifd['tags'][Tag.Photometric.value]['data'][0]
                original_jpeg_tables = original_ifd['tags'][Tag.JPEGTables.value]['data']
                original_jpeg_quality = EstimateJpegQuality(original_jpeg_tables)

                # create redacted image
                original_image = pyvips.Image.tiffload(input_filename, page=i)
                if (original_image_width, original_image_height) != (width, height):
                    resized_svg = svg_image.resize(original_image_width / width)
                else:
                    resized_svg = svg_image
                redacted_image = original_image.composite([resized_svg], pyvips.BlendMode.OVER)

                with NamedTemporaryFile(suffix='{i}_out.tiff') as tmp:
                    # write redacted image to temporary file
                    if verbose:
                        print('creating redacted image')
                    redacted_image.tiffsave(
                        tmp.name,
                        tile=False,
                        pyramid=False,
                        bigtiff=True,
                        rgbjpeg=(original_photometric == 2),
                        compression='jpeg',
                        Q=original_jpeg_quality,
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
                        print('creating combined image')
                    ifdPtr = write_ifd(dest, bom, True, redacted_ifd, ifdPtr)
            else:
                if verbose:
                    print('creating combined image')
                ifdPtr = write_ifd(dest, bom, True, original_ifd, ifdPtr)


def get_args():
    parser = argparse.ArgumentParser(description='Redact tiff file')
    parser.add_argument('--input', '--src', type=str, required=True, help='Input image filename')
    parser.add_argument('--output', '--dest', type=str, required=True, help='Output image filename')
    parser.add_argument('--annotation', '-a', type=str, required=True, help='Annotation filename')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    return parser.parse_args()


def main(args):
    input_filename = args.input
    output_filename = args.output
    annotation_filename = args.annotation
    verbose = args.verbose

    start = time.time()
    polygons = get_polygons(annotation_filename)
    apply_redaction(input_filename, output_filename, polygons, verbose)
    end = time.time()
    elapsed = time.strftime('%M:%S', time.gmtime(end - start))
    if verbose:
        print(f'total time: {elapsed}')


if __name__ == '__main__':
    args = get_args()
    main(args)
