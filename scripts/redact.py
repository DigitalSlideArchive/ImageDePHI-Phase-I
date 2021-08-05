import argparse
import json
import time
import os
import shutil
import struct
from typing import Any, Dict, List, BinaryIO, TypedDict
from contextlib import contextmanager

import numpy as np
import matplotlib.pyplot as plt

import pyvips
import tifftools
from tqdm import tqdm, trange

import tiff_utils
from models import Polygon, IFDType


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

    vips_image.set_progress(True)
    vips_image.signal_connect('preeval', progress_print)
    vips_image.signal_connect('eval', progress_print)
    vips_image.signal_connect('posteval', progress_print)
    try:
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
    # get tiff information
    original_info = tifftools.read_tiff(input_filename)
    width = original_info['ifds'][0]['tags'][tifftools.Tag.ImageWidth.value]['data'][0]
    height = original_info['ifds'][0]['tags'][tifftools.Tag.ImageHeight.value]['data'][0]
    tile_width = original_info['ifds'][0]['tags'][tifftools.Tag.TileWidth.value]['data'][0]
    tile_height = original_info['ifds'][0]['tags'][tifftools.Tag.TileHeight.value]['data'][0]
    photometric = original_info['ifds'][0]['tags'][tifftools.Tag.Photometric.value]['data'][0]
    jpeg_tables = original_info['ifds'][0]['tags'][tifftools.Tag.JPEGTables.value]['data']
    jpeg_quality = tifftools.constants.EstimateJpegQuality(jpeg_tables)

    # create svg image
    svg_image = create_svg(width, height, polygons)

    # create redacted image
    original_image = pyvips.Image.tiffload(input_filename)
    redacted_image = original_image.composite([svg_image], pyvips.BlendMode.OVER)

    ### TODO: replace with real tempfile and using block
    tempfile = output_filename.replace('svs', 'tif')
    print(f'outputing to file: {tempfile}')
    with vips_progress(redacted_image):
        redacted_image.tiffsave(
            tempfile,
            tile=True,
            tile_width=tile_width,
            tile_height=tile_height,
            pyramid=True,
            bigtiff=True,
            rgbjpeg=(photometric == 2),
            compression='jpeg',
            Q=jpeg_quality,
        )

    redacted_info = tifftools.read_tiff(tempfile)
    # write to combined tiff output
    tiff_utils.write_tiff_conditional(
        original_ifds=original_info['ifds'],
        redacted_ifds=redacted_info['ifds'],
        input_filename=input_filename,
        output_filename=output_filename,
        svg=svg_image,
        allowExisting=True,
    )


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
