import argparse
import json
import time
import os
import shutil
import struct
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, BinaryIO, TypedDict

import numpy as np
import matplotlib.pyplot as plt

import pyvips
import tifftools
from tifftools.constants import Tag, EstimateJpegQuality
from tifftools.path_or_fobj import OpenPathOrFobj
from tifftools.tifftools import write_tag_data, check_offset, write_ifd, write_sub_ifds
from tqdm import tqdm, trange

import tiff_utils
from models import Polygon, IFDType
from utils import get_ifd_type, check_compatible_ifds


@contextmanager
def vips_progress(vips_image: pyvips.Image):
    pbar = tqdm(total=100)
    percent = 0

    def progress_print(image: pyvips.Image, progress):
        nonlocal percent
        current = progress.percent
        if current > percent:
            pbar.update(current - percent)
            percent = current

    try:
        vips_image.set_progress(True)
        vips_image.signal_connect('preeval', progress_print)
        vips_image.signal_connect('eval', progress_print)
        vips_image.signal_connect('posteval', progress_print)
        yield None
    finally:
        pbar.close()
        vips_image.set_progress(False)


def get_polygons(annotation_filename: str):
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


def create_svg(width: int, height: int, polygons: List[Polygon]):
    svg_str = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
    for polygon in polygons:
        points = ' '.join([f'{pt[0]},{pt[1]}' for pt in polygon.points])
        svg_str += f'<polygon points="{points}" stroke="none" fill="{polygon.fill_color}" />'
    svg_str += '</svg>'
    svg_image = pyvips.Image.svgload_buffer(svg_str.encode())

    return svg_image


def apply_redaction(input_filename: str, output_filename: str, polygons: List[Polygon]):
    original_info = tifftools.read_tiff(input_filename)
    original_ifds = original_info['ifds']
    width = original_ifds[0]['tags'][tifftools.Tag.ImageWidth.value]['data'][0]
    height = original_ifds[0]['tags'][tifftools.Tag.ImageHeight.value]['data'][0]
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
            if ifd_type == IFDType.tile:
                original_image = pyvips.Image.tiffload(input_filename, page=i)
                is_redacted, resized_svg = tiff_utils.redacted_list(svg_image, original_ifd)
                redacted_image = original_image.composite([resized_svg], pyvips.BlendMode.OVER)

                original_tile_width = original_ifd['tags'][Tag.TileWidth.value]['data'][0]
                original_tile_height = original_ifd['tags'][Tag.TileHeight.value]['data'][0]
                original_compression = original_ifd['tags'][Tag.Compression.value]['data'][0]
                original_photometric = original_ifd['tags'][Tag.Photometric.value]['data'][0]
                original_jpeg_tables = original_ifd['tags'][Tag.JPEGTables.value]['data']
                original_jpeg_quality = EstimateJpegQuality(original_jpeg_tables)

                with NamedTemporaryFile(suffix='{i}_out.tiff') as tmp:
                    with vips_progress(redacted_image):
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
                    
                    redacted_info = tifftools.read_tiff(tmp.name)
                    redacted_ifd = redacted_info['ifds'][0]
                    redacted_tile_width = redacted_ifd['tags'][Tag.TileWidth.value]['data'][0]
                    redacted_tile_height = redacted_ifd['tags'][Tag.TileHeight.value]['data'][0]
                    redacted_compression = redacted_ifd['tags'][Tag.Compression.value]['data'][0]
                    redacted_photometric = redacted_ifd['tags'][Tag.Photometric.value]['data'][0]
                    redacted_jpeg_tables = redacted_ifd['tags'][Tag.JPEGTables.value]['data']
                    redacted_jpeg_quality = EstimateJpegQuality(redacted_jpeg_tables)

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
                    
                    modified_ifd = tiff_utils.conditional_ifd(original_ifd, redacted_ifd, is_redacted)
                    ifdPtr = tiff_utils.write_ifd_conditional(
                        dest=dest,
                        bom=bom,
                        ifd=modified_ifd,
                        original_ifd=original_ifd,
                        redacted_ifd=redacted_ifd,
                        ifdPtr=ifdPtr,
                        is_redacted=is_redacted,
                    )
            else:
                ifdPtr = write_ifd(dest, bom, True, original_ifd, ifdPtr)


def get_args():
    parser = argparse.ArgumentParser(description='Redact tiff file')
    parser.add_argument('--input', '--src', type=str, required=True, help='Input image filename')
    parser.add_argument('--output', '--dest', type=str, required=True, help='Output image filename')
    parser.add_argument('--annotation', '-a', type=str, required=True, help='Annotation filename')
    return parser.parse_args()


def main(args):
    input_filename = args.input
    output_filename = args.output
    annotation_filename = args.annotation

    start = time.time()
    polygons = get_polygons(annotation_filename)
    apply_redaction(input_filename, output_filename, polygons)
    end = time.time()
    elapsed = time.strftime('%M:%S', time.gmtime(end - start))
    print(f'total time: {elapsed}')


if __name__ == '__main__':
    args = get_args()
    main(args)
