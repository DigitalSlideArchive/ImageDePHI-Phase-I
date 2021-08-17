from functools import lru_cache

import pyvips
from bson.objectid import ObjectId
from girder.api import access, rest
from girder.api.describe import Description, autoDescribeRoute
from girder.constants import AccessType
from girder.models.file import File
from girder.models.item import Item

TILESIZE = 256
LEVELS = 7


@lru_cache
def makeSourceClosure(item):
    file = next(Item().childFiles({"_id": ObjectId(item)}))
    fd = File().open(file)

    def read_handler(size):
        return fd.read(size)

    def seek_handler(*args):
        fd.seek(*args)
        return fd.tell()

    source = pyvips.SourceCustom()
    source.on_read(read_handler)
    source.on_seek(seek_handler)
    return source


@lru_cache
def makeImageRegion(source, ifd, subifd, z):
    if subifd:
        image = pyvips.Image.tiffload_source(source, page=ifd, subifd=subifd)
    elif ifd:
        image = pyvips.Image.tiffload_source(source, page=ifd)
    else:
        image = pyvips.Image.new_from_source(source, "")
    if z:
        assert z < LEVELS
        region = pyvips.Region.new(image.resize(1 / (z ** 0.3)))
    else:
        region = pyvips.Region.new(image)
    return (region, image.bands, image.format, image.width, image.height)


@lru_cache
def getCachedTile(region, x, y, image_bands, image_format):
    tile_buf = region.fetch(x, y, TILESIZE, TILESIZE)
    raw_tile = pyvips.Image.new_from_memory(
        tile_buf,
        TILESIZE,
        TILESIZE,
        image_bands,
        image_format,
    )
    return pyvips.Image.jpegsave_buffer(raw_tile)


@access.public
@rest.rawResponse
@autoDescribeRoute(
    Description("Retrieve a tile from the TIFF.")
    .modelParam(
        "id",
        "The item ID",
        paramType="path",
        model=Item,
        level=AccessType.READ,
    )
    .param(
        "ifd",
        "",
        paramType="path",
        dataType="integer",
    )
    .param(
        "tag",
        "",
        paramType="query",
        required=False,
        dataType="integer",
    )
    .param(
        "subifd",
        "",
        paramType="query",
        required=False,
        dataType="integer",
    )
    .param(
        "z",
        "The layer number of the tile (0 is the most zoomed-out layer).",
        paramType="path",
        dataType="integer",
    )
    .param(
        "x",
        "The X coordinate of the tile (0 is the left side).",
        paramType="path",
        dataType="integer",
    )
    .param(
        "y",
        "The Y coordinate of the tile (0 is the top).",
        paramType="path",
        dataType="integer",
    )
    .errorResponse()
)
def getTile(item, ifd, z, x, y, tag=None, subifd=None):
    source = makeSourceClosure(item["_id"])
    (
        region,
        image_bands,
        image_format,
        _,
        _,
    ) = makeImageRegion(source, ifd, subifd, z)
    tile = getCachedTile(region, x, y, image_bands, image_format)
    rest.setResponseHeader("Content-Type", "image/jpeg")
    return tile


@access.public
@autoDescribeRoute(
    Description("Retrieve tile size information.")
    .modelParam(
        "id",
        "The item ID",
        paramType="path",
        model=Item,
        level=AccessType.READ,
    )
    .param(
        "ifd",
        "",
        paramType="path",
        dataType="integer",
    )
    .param(
        "tag",
        "",
        paramType="query",
        required=False,
        dataType="integer",
    )
    .param(
        "subifd",
        "",
        paramType="query",
        required=False,
        dataType="integer",
    )
    .param(
        "z",
        "The layer number of the tile (0 is the most zoomed-out layer).",
        paramType="path",
        dataType="integer",
    )
    .errorResponse()
)
def getTileSizes(item, ifd, z, tag=None, subifd=None):
    source = makeSourceClosure(item["_id"])
    (
        _,
        _,
        _,
        image_width,
        image_height,
    ) = makeImageRegion(source, ifd, subifd, z)
    return {
        "sizeX": image_width,
        "sizeY": image_height,
        "tilesize": TILESIZE,
        "levels": LEVELS,
    }


@access.public
@rest.rawResponse
@autoDescribeRoute(
    Description("Get thumbnail of item.")
    .modelParam(
        "id",
        "The item ID",
        paramType="path",
        model=Item,
        level=AccessType.READ,
    )
    .param(
        "ifd",
        "",
        paramType="path",
        dataType="integer",
    )
    .param(
        "tag",
        "",
        paramType="query",
        required=False,
        dataType="integer",
    )
    .param(
        "subifd",
        "",
        paramType="query",
        required=False,
        dataType="integer",
    )
    .param(
        "size",
        "",
        paramType="query",
        required=False,
        dataType="integer",
    )
    .errorResponse()
)
def getTumbnail(item, ifd, tag=None, subifd=None, size=250):
    source = makeSourceClosure(item["_id"])
    vips_image = pyvips.Image.thumbnail_source(source, size=size)
    rest.setResponseHeader("Content-Type", "image/jpeg")
    return pyvips.Image.jpegsave_buffer(vips_image)
