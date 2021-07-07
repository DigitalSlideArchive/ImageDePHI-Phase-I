import json
import time
from typing import List
import pyvips
import large_image
from contextlib import contextmanager


class Polygon:
    def __init__(self, points, fill_color, line_color, line_width):
        self.points = points
        self.fill_color = fill_color
        self.line_color = line_color
        self.line_width = line_width


def progress_print(image, progress):
    run = time.strftime('%M:%S', time.gmtime(progress.run))
    eta = time.strftime('%M:%S', time.gmtime(progress.eta))
    percent = progress.percent
    total = progress.tpels
    current = progress.npels
    print(f'{percent:>3}% |{("=" * int(percent / 5)):<20}| [{run}<{eta}]', end='\r')


@contextmanager
def vips_progress(vips_image):
    vips_image.set_progress(True)
    vips_image.signal_connect('preeval', progress_print)
    vips_image.signal_connect('eval', progress_print)
    vips_image.signal_connect('posteval', progress_print)
    try:
        yield None
    finally:
        print()
        vips_image.set_progress(False)


def remove_polygon(input_filename: str, output_filename: str, polygons: List[Polygon]):
    sourceImage = pyvips.Image.new_from_file(input_filename)
    width, height = sourceImage.width, sourceImage.height

    meta = large_image.open(input_filename)
    tile_width = meta.tileWidth
    tile_height = meta.tileHeight
    jpeg_quality = meta.jpegQuality

    svgStr = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
    for polygon in polygons:
        points = ' '.join([f'{pt[0]},{pt[1]}' for pt in polygon.points])
        svgStr += f'<polygon points="{points}" stroke="none" fill="{polygon.fill_color}" />'
    svgStr += '</svg>'
 
    overlayImage = pyvips.Image.svgload_buffer(svgStr.encode())
    outputImage= sourceImage.composite([overlayImage], pyvips.BlendMode.OVER)

    with vips_progress(outputImage):
        outputImage.write_to_file(
            output_filename,
            tile=True,
            tile_width=tile_width,
            tile_height=tile_height,
            pyramid=True,
            bigtiff=True,
            compression='jpeg',
            Q=jpeg_quality
        )


if __name__ == '__main__':
    base = './data/21912px'
    input_filename =  base + '.svs'
    output_filename = base + '.tif'
    annotation_filename = base + '.json'

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
    remove_polygon(input_filename, output_filename, polygons)
    end = time.time()
    elapsed = time.strftime('%M:%S', time.gmtime(end - start))
    print(f'total time: {elapsed}')
