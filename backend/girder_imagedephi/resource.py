from typing import List, Optional, Union

import pydantic
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute, describeRoute
from girder.api.rest import filtermodel
from girder.models.file import File
from girder.models.item import Item

from girder_imagedephi import types


@describeRoute(
    Description("Retrieve the edits made to the redaction.")
    .param("id", "The item ID")
    .param(
        "associatedImageLabel",
        "The label of an associated image to retrieve. If not specified, "
        "the primary image is used.",
        required=False,
    )
    .errorResponse()
)
@access.admin
def getEdits(id, params) -> List[types.Edit]:
    print(params)
    ...


@describeRoute(
    Description("Push an update to the edit log.")
    .modelParam("id", "The item ID", model="item")
    .param(
        "associatedImageLabel",
        "The label of an associated image to retrieve. If not specified, "
        "the primary image is used.",
        required=False,
    )
    .param(
        "it",
        "The current edit iteration.",
        required=True,
        paramType="body",
        dataType="int",
    )
    .param(
        "metadataKey",
        "The metadata key to update.",
        required=False,
        paramType="body",
        dataType="int",
    )
    .param(
        "polygonId",
        "The ID of the polygon to edit.",
        required=False,
        paramType="body",
        dataType="int",
    )
    .param(
        "redactionReason",
        "The reason the redaction was commited.",
        required=False,
        paramType="body",
        dataType="string",
    )
    .param(
        "points",
        "A list of coordinates [{x: ..., y: ...}, ...] to form a polygon",
        required=False,
        paramType="body",
        dataType=None,
    )
    .errorResponse()
)
@access.admin
def createEdit(id, params: types.EditPost):
    ...


@describeRoute(
    Description("Download a redacted item.")
    .responseClass("Item")
    .modelParam("id", model=Item)
    .errorResponse("ID was invalid.")
    .errorResponse("Read access was denied for the item.", 403)
)
@access.admin
def downloadRedacted(id, params):
    item = Item().findOne(id=id)
    file = File().findOne(id=item["largeImage"]["fileId"])
    print(Item().findOne(id=id))
    return {}
