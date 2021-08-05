from typing import Dict

from tifftools import Tag
from tifftools.constants import EstimateJpegQuality

from models import IFDType


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


def check_compatible_ifds(
    original_ifd: Dict[str, dict],
    redacted_ifd: Dict[str, dict],
) -> bool:
    original_tile_width = original_ifd['tags'][Tag.TileWidth.value]['data'][0]
    original_tile_height = original_ifd['tags'][Tag.TileHeight.value]['data'][0]
    original_compression = original_ifd['tags'][Tag.Compression.value]['data'][0]
    original_photometric = original_ifd['tags'][Tag.Photometric.value]['data'][0]
    original_jpeg_tables = original_ifd['tags'][Tag.JPEGTables.value]['data']
    original_jpeg_quality = EstimateJpegQuality(original_jpeg_tables)

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
    
    return True
