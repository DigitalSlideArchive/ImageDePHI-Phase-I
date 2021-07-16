import json
import time
from typing import List, BinaryIO
from contextlib import contextmanager

import pyvips
import tifftools
from tqdm import tqdm


class Polygon:
    def __init__(self, points, fill_color, line_color, line_width):
        self.points = points
        self.fill_color = fill_color
        self.line_color = line_color
        self.line_width = line_width


@contextmanager
def vips_progress(vips_image: pyvips.Image):
    def progress_print(image: pyvips.Image, progress):
        run = time.strftime('%M:%S', time.gmtime(progress.run))
        eta = time.strftime('%M:%S', time.gmtime(progress.eta))
        percent = progress.percent
        print(f'{percent:>3}% |{("=" * int(percent / 2)):<50}| [{run}<{eta}]', end='\r')

    vips_image.set_progress(True)
    vips_image.signal_connect('preeval', progress_print)
    vips_image.signal_connect('eval', progress_print)
    vips_image.signal_connect('posteval', progress_print)
    try:
        yield None
    finally:
        print()
        vips_image.set_progress(False)


def get_tiff_tag(info, tag):
    return info['ifds'][0]['tags'][tag]['data']


def write_redacted_svs(
    dest: BinaryIO,
    original: BinaryIO,
    original_offsets: List[int],
    original_lengths: List[int],
    original_srclen: int,
    redacted: BinaryIO,
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

    for olidx in tqdm(range(len(original_offsetList))):
        if is_redacted[olidx]:
            offset, idx = redacted_offsetList[olidx]
            length = redacted_lengths[idx]
            if not tifftools.tifftools.check_offset(redacted_srclen, offset, length):
                continue
            src = redacted
        else:
            offset, idx = original_offsetList[olidx]
            length = original_lengths[idx]
            if not tifftools.tifftools.check_offset(original_srclen, offset, length):
                continue
            src = original
        
        src.seek(offset)
        destOffsets[idx] = dest.tell()
        
        while length > 0:
            data = src.read(min(length, COPY_CHUNKSIZE))
            dest.write(data)
            length -= len(data)
    
    return destOffsets



def remove_polygons(input_filename: str, output_filename: str, polygons: List[Polygon]):
    sourceImage = pyvips.Image.new_from_file(input_filename)
    height, width = sourceImage.height, sourceImage.width

    original_info = tifftools.read_tiff(input_filename)
    original_tile_height = get_tiff_tag(original_info, tifftools.Tag.TileHeight.value)[0]
    original_tile_width = get_tiff_tag(original_info, tifftools.Tag.TileWidth.value)[0]
    original_compression = get_tiff_tag(original_info, tifftools.Tag.Compression.value)[0]
    original_jpeg_tables = get_tiff_tag(original_info, tifftools.Tag.JPEGTables.value)
    original_tile_offsets = get_tiff_tag(original_info, tifftools.Tag.TileOffsets.value)['data']
    original_tile_byte_counts = get_tiff_tag(original_info, tifftools.Tag.TileByteCounts.value)['data']

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
    redacted_tile_offsets = get_tiff_tag(redacted_info, tifftools.Tag.TileOffsets.value)['data']
    redacted_tile_byte_counts = get_tiff_tag(redacted_info, tifftools.Tag.TileByteCounts.value)['data']
    
    if (original_tile_height, original_tile_width) != (redacted_tile_height, redacted_tile_width):
        raise ValueError('Original tile size does not match redacted tile size')
    if original_compression != redacted_compression:
        raise ValueError('Original compression does not match redacted compression')
    if original_jpeg_tables != redacted_jpeg_tables:
        raise ValueError('Original JPEG Tables do not match redacted JPEG Tables')

    is_redacted = []
    for offset, length in zip(original_tile_offsets, original_tile_byte_counts):
        # TODO: calculate x, y coordinates from tile offset
        x, y = None, None
        tile_max = overlayImage.extract_area(x, y, original_tile_width, original_tile_height).extract_band(3).max()
        is_redacted.append(tile_max > 0)
    
    with open(output_filename, 'wb') as dest, open(input_filename, 'rb') as original, open(tempfile, 'rb') as redacted:
        write_redacted_svs(
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


if __name__ == '__main__':
    base = './downloads/21912px'
    input_filename = './downloads/21912px.svs'
    output_filename = './downloads/21912px_out.svs'
    annotation_filename = './downloads/21912px.json'

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
