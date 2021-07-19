import json
import time
import os
import shutil
import struct
from typing import List, BinaryIO
from contextlib import contextmanager

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


def get_tiff_tag(info, tag):
    return info['ifds'][0]['tags'][tag]['data']



def remove_polygons(input_filename: str, output_filename: str, polygons: List[Polygon]):
    sourceImage = pyvips.Image.new_from_file(input_filename)
    height, width = sourceImage.height, sourceImage.width

    original_info = tifftools.read_tiff(input_filename)
    original_tile_height = get_tiff_tag(original_info, tifftools.Tag.TileHeight.value)[0]
    original_tile_width = get_tiff_tag(original_info, tifftools.Tag.TileWidth.value)[0]
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

    # TODO: remove saving svg
    with open(output_filename.replace('out.svs', 'mask.svg'), 'w') as f:
        f.write(svgStr)
 
    overlayImage = pyvips.Image.svgload_buffer(svgStr.encode())
    outputImage = sourceImage.composite([overlayImage], pyvips.BlendMode.OVER)

    # TODO: replace with real tempfile and using block
    tempfile = output_filename.replace('svs', 'tif')

    print(f'outputing to file: {tempfile}')
    with vips_progress(outputImage):
        outputImage.write_to_file(
            tempfile,
            tile=True,
            tile_width=original_tile_width,
            tile_height=original_tile_height,
            pyramid=True,
            bigtiff=True,
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
    if original_jpeg_tables != redacted_jpeg_tables:
        raise ValueError('Original JPEG Tables do not match redacted JPEG Tables')

    tiff_utils.write_tiff_conditional(original_info['ifds'], redacted_info['ifds'], output_filename, overlayImage, True)
    return

    print('finding which tiles to redact')
    is_redacted = []
    tiles_across = (width + original_tile_width - 1) // original_tile_width
    tiles_down = (height + original_tile_height - 1) // original_tile_height
    for i in trange(len(original_tile_offsets)):
        x = (i % tiles_across) * original_tile_width
        y = (i // tiles_across) * original_tile_height
        tile_width = min(original_tile_width, width - x)
        tile_height = min(original_tile_height, height - y)
        tile_max = overlayImage.extract_area(x, y, tile_width, tile_height).extract_band(3).max()
        is_redacted.append(tile_max > 0)
    
    print('writing to output svs')
    with open(output_filename, 'wb') as dest, open(input_filename, 'rb') as original, open(tempfile, 'rb') as redacted:
        write_tag_data(
            dest=dest,
            original=original,
            original_offsets=original_tile_offsets,
            original_lengths=original_tile_byte_counts,
            original_srclen=original_info['size'],
            redacted=redacted,
            redacted_offsets=redacted_tile_offsets,
            redacted_lengths=redacted_tile_byte_counts,
            redacted_srclen=redacted_info['size'],
            is_redacted=is_redacted,
        )


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

    for i in trange(len(num_tiles)):
        x = (i % tiles_across) * tile_width
        y = (i // tiles_across) * tile_height
        w = min(tile_width, width - x)
        h = min(tile_height, height - y)
        tile_max = svg.extract_area(x, y, w, h).extract_band(3).max()
        is_redacted.append(tile_max > 0)

    return is_redacted


if __name__ == '__main__':
    input_filename = './downloads/small.svs'
    output_filename = './downloads/small_out.svs'
    annotation_filename = './downloads/small.json'

    with open(annotation_filename, 'r') as f:
        data = json.load(f)
    elements = data['annotation']['elements']
    
    polygons = []
    for e in elements:
        if e['type'] == 'polyline':
            points = e['points']
            fill_color = e['fillColor']
            line_color = e['lineColor']
            line_width = e['lineWidth']
            polygon = Polygon(points, fill_color, line_color, line_width)
            polygons.append(polygon)
    
    start = time.time()
    remove_polygons(input_filename, output_filename, polygons)
    end = time.time()
    elapsed = time.strftime('%M:%S', time.gmtime(end - start))
    print(f'total time: {elapsed}')
