import argparse
import json
import time
import os
import shutil
import struct
from typing import Any, Dict, List, BinaryIO
from contextlib import contextmanager

import numpy as np
import matplotlib.pyplot as plt

import pyvips
import tifftools
from tqdm import tqdm, trange

import tiff_utils


class Polygon:
    def __init__(self, points, fill_color, line_color, line_width):
        self.points = points
        self.fill_color = fill_color
        self.line_color = line_color
        self.line_width = line_width


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


def get_tiff_tag(info: dict, tag: int):
    return info['ifds'][0]['tags'][tag]['data']


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


def remove_polygons(input_filename: str, output_filename: str, polygons: List[Polygon]):
    # sourceImage = pyvips.Image.new_from_file(input_filename)
    sourceImage = pyvips.Image.tiffload(input_filename)
    height, width = sourceImage.height, sourceImage.width

    original_info = tifftools.read_tiff(input_filename)
    original_tile_height = get_tiff_tag(original_info, tifftools.Tag.TileHeight.value)[0]
    original_tile_width = get_tiff_tag(original_info, tifftools.Tag.TileWidth.value)[0]
    original_photometric = get_tiff_tag(original_info, tifftools.Tag.Photometric.value)[0]
    original_compression = get_tiff_tag(original_info, tifftools.Tag.Compression.value)[0]
    original_jpeg_tables = get_tiff_tag(original_info, tifftools.Tag.JPEGTables.value)
    original_tile_offsets = get_tiff_tag(original_info, tifftools.Tag.TileOffsets.value)
    original_tile_byte_counts = get_tiff_tag(original_info, tifftools.Tag.TileByteCounts.value)

    original_jpeg_quality = tifftools.constants.EstimateJpegQuality(original_jpeg_tables)

    svgStr = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
    for polygon in polygons:
        points = ' '.join([f'{pt[0]},{pt[1]}' for pt in polygon.points])
        svgStr += f'<polygon points="{points}" stroke="none" fill="{polygon.fill_color}" />'
    svgStr += '</svg>'
 
    overlayImage = pyvips.Image.svgload_buffer(svgStr.encode())
    outputImage = sourceImage.composite([overlayImage], pyvips.BlendMode.OVER)

    # TODO: replace with real tempfile and using block
    tempfile = output_filename.replace('svs', 'tif')

    print(f'outputing to file: {tempfile}')
    with vips_progress(outputImage):
        # outputImage.write_to_file(
        #     tempfile,
        #     tile=True,
        #     tile_width=original_tile_width,
        #     tile_height=original_tile_height,
        #     pyramid=True,
        #     bigtiff=True,
        #     rgbjpeg=True,
        #     compression='jpeg',
        #     Q=original_jpeg_quality
        # )
        outputImage.tiffsave(
            tempfile,
            tile=True,
            tile_width=original_tile_width,
            tile_height=original_tile_height,
            # pyramid=True,
            bigtiff=True,
            rgbjpeg=(original_photometric == 2),
            compression='jpeg',
            Q=original_jpeg_quality
        )
    
    redacted_info = tifftools.read_tiff(tempfile)
    redacted_tile_height = get_tiff_tag(redacted_info, tifftools.Tag.TileHeight.value)[0]
    redacted_tile_width = get_tiff_tag(redacted_info, tifftools.Tag.TileWidth.value)[0]
    redacted_compression = get_tiff_tag(redacted_info, tifftools.Tag.Compression.value)[0]
    redacted_jpeg_tables = get_tiff_tag(redacted_info, tifftools.Tag.JPEGTables.value)
    redacted_tile_offsets = get_tiff_tag(redacted_info, tifftools.Tag.TileOffsets.value)
    redacted_tile_byte_counts = get_tiff_tag(redacted_info, tifftools.Tag.TileByteCounts.value)
    
    if (original_tile_height, original_tile_width) != (redacted_tile_height, redacted_tile_width):
        raise ValueError('Original tile size does not match redacted tile size')
    if original_compression != redacted_compression:
        raise ValueError('Original compression does not match redacted compression')
    # if original_jpeg_tables != redacted_jpeg_tables:
    #     raise ValueError('Original JPEG Tables do not match redacted JPEG Tables')

    tiff_utils.write_tiff_conditional(original_info['ifds'], redacted_info['ifds'], output_filename, overlayImage, True)


def get_args():
    parser = argparse.ArgumentParser(description='Redact tiff file')
    parser.add_argument('--input', '--src', type=str, required=True, help='Input image filename')
    parser.add_argument('--output', '--dest', type=str, required=True, help='Output image filename')
    parser.add_argument('--annotation', '-a', type=str, required=True, help='Annotation filename')
    return parser.parse_args()


def write_all(input_filename):
    info = tifftools.read_tiff(input_filename)
    for i, ifd in enumerate(info['ifds']):
        tifftools.write_tiff(ifd, f'./downloads/temp/small_ifd{i}.tiff')


def main(args):
    input_filename = args.input
    output_filename = args.output
    annotation_filename = args.annotation

    start = time.time()

    polygons = get_polygons(annotation_filename)
    remove_polygons(input_filename, output_filename, polygons)
    # write_all(input_filename)

    end = time.time()
    elapsed = time.strftime('%M:%S', time.gmtime(end - start))
    print(f'total time: {elapsed}')


if __name__ == '__main__':
    args = get_args()
    main(args)
