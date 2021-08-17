import tifftools
from bson.objectid import ObjectId
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.constants import AccessType
from girder.models.file import File
from girder.models.item import Item


@access.public
@autoDescribeRoute(
    Description("Descructure TIFF.")
    .modelParam(
        "id",
        "The item ID",
        paramType="path",
        model=Item,
        level=AccessType.READ,
    )
    .errorResponse()
)
def getIfds(item):
    file = next(Item().childFiles(item))
    with File().open(file) as image_fd:
        info = tifftools.read_tiff(image_fd)
        ifds = []
        for ifd, ifd_record in enumerate(info.get("ifds")):
            ifds.append(
                {
                    "item": item["_id"],
                    "ifd": ifd,
                    "tag": 0,
                    "subifd": 0,
                }
            )
            for tag, tag_record in ifd_record["tags"].items():
                for subifd in tag_record.get("ifds", []):
                    ifds.append(
                        {
                            "item": item["_id"],
                            "ifd": ifd,
                            "tag": tag,
                            "subifd": subifd,
                        }
                    )
        return ifds


@access.public
@autoDescribeRoute(
    Description("Get metadata.")
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
        required=True,
        dataType="integer",
    )
    .param(
        "tag",
        "",
        paramType="path",
        required=False,
        dataType="integer",
    )
    .param(
        "subifd",
        "",
        paramType="path",
        required=False,
        dataType="integer",
    )
    .errorResponse()
)
def getMetadata(item, ifd, tag=None, subifd=None):
    file = next(Item().childFiles(item))
    with File().open(file) as image_fd:
        return tifftools.read_tiff(image_fd)["ifds"][ifd]
