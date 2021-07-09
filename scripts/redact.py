import json
import shutil
import time
from typing import List, BinaryIO
import pyvips
import tifftools
from contextlib import contextmanager


class Polygon:
    def __init__(self, points, fill_color, line_color, line_width):
        self.points = points
        self.fill_color = fill_color
        self.line_color = line_color
        self.line_width = line_width


@contextmanager
def vips_progress(vips_image):
    def progress_print(image, progress):
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


def write_svs(dest: BinaryIO, src: BinaryIO, svg: pyvips.Image, offsets: List[int], lengths: List[int], srclen: int):
    COPY_CHUNKSIZE = 1024 ** 2

    if len(offsets) != len(lengths):
        raise Exception('Offsets and byte counts do not correspond')
    
    destOffsets = [0] * len(offsets)
    # We preserve the order of the chunks from the original file
    offsetList = sorted([(offset, idx) for idx, offset in enumerate(offsets)])
    olidx = 0
    while olidx < len(offsetList):
        offset, idx = offsetList[olidx]
        length = lengths[idx]
        if offset and tifftools.tifftools.check_offset(srclen, offset, length):
            src.seek(offset)
            destOffsets[idx] = dest.tell()

            while (olidx + 1 < len(offsetList) and
                   offsetList[olidx + 1][0] == offsetList[olidx][0] + lengths[idx] and
                   tifftools.tifftools.check_offset(srclen, offsetList[olidx + 1][0], lengths[offsetList[olidx + 1][1]])):
                destOffsets[offsetList[olidx + 1][1]] = destOffsets[idx] + lengths[idx]
                olidx += 1
                offset, idx = offsetList[olidx]
                length += lengths[idx]
            while length:
                data = src.read(min(length, COPY_CHUNKSIZE))
                dest.write(data)
                length -= len(data)
        olidx += 1
    return destOffsets



def remove_polygons(input_filename: str, output_filename: str, polygons: List[Polygon]):
    sourceImage = pyvips.Image.new_from_file(input_filename)
    height, width = sourceImage.height, sourceImage.width

    input_info = tifftools.read_tiff(input_filename)
    tile_height = get_tiff_tag(input_info, tifftools.Tag.TileHeight.value)[0]
    tile_width = get_tiff_tag(input_info, tifftools.Tag.TileWidth.value)[0]
    compression = get_tiff_tag(input_info, tifftools.Tag.Compression.value)[0]
    jpeg_tables = get_tiff_tag(input_info, tifftools.Tag.JPEGTables.value)
    jpeg_quality = tifftools.constants.EstimateJpegQuality(jpeg_tables)

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
            tile_width=tile_width,
            tile_height=tile_height,
            pyramid=True,
            bigtiff=True,
            compression='jpeg',
            Q=jpeg_quality
        )
    
    output_info = tifftools.read_tiff(tempfile)
    output_tile_height = get_tiff_tag(output_info, tifftools.Tag.TileHeight.value)[0]
    output_tile_width = get_tiff_tag(output_info, tifftools.Tag.TileWidth.value)[0]
    output_compression = get_tiff_tag(output_info, tifftools.Tag.Compression.value)[0]
    output_jpeg_tables = get_tiff_tag(output_info, tifftools.Tag.JPEGTables.value)
    
    if (tile_height, tile_width) != (output_tile_height, output_tile_width):
        raise ValueError('Input tile size does not match output tile size')
    if compression != output_compression:
        raise ValueError('Input compression does not match output compression')
    if jpeg_tables != output_jpeg_tables:
        raise ValueError('Input JPEG Tables do not match output JPEG Tables')
    
    output_tile_offsets = get_tiff_tag(output_info, tifftools.Tag.TileOffset.value)
    output_tile_byte_counts = get_tiff_tag(output_info, tifftools.Tag.TileByteCounts.value)

    print(f'copying input to file: {output_filename}')
    shutil.copyfile(input_filename, output_filename)
    
    with open(tempfile, 'rb') as input_file, open(output_filename, 'wb') as output_file:
        pass


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
