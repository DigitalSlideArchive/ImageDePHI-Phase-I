from typing import List, Optional, Union

import pydantic
from typing_extensions import Literal, TypedDict


class Point(TypedDict):
    x: pydantic.PositiveInt
    y: pydantic.PositiveInt


Points = pydantic.conlist(Point, min_items=3)
RedactionReason = Union[
    Literal["patient name"],
    Literal["date of birth"],
    Literal["social security number"],
    Literal["demographics"],
    Literal["facility/provider information"],
    str,
]


class PointsEdit(TypedDict):
    polygonId: int
    points: Union[Points, None]


class PolygonRedactReasonEdit(TypedDict):
    polygonId: int
    redactionReason: Union[RedactionReason, None]


class MetadataRedactReasonEdit(TypedDict):
    metadataKey: str
    redactionReason: Union[RedactionReason, None]


Edit = Union[PointsEdit, PolygonRedactReasonEdit, MetadataRedactReasonEdit]


class RedactionData(TypedDict):
    associatedImageLabel: Optional[str]
    redactions: List[Edit]


class ImageDePHIData(TypedDict):
    edits: List[RedactionData]


class PointsPost(PointsEdit):
    it: pydantic.PositiveInt
    associatedImageLabel: Optional[str]


class PolygonRedactReasonPost(PolygonRedactReasonEdit):
    it: pydantic.PositiveInt
    associatedImageLabel: Optional[str]


class MetadataRedactReasonPost(MetadataRedactReasonEdit):
    it: pydantic.PositiveInt
    associatedImageLabel: Optional[str]


EditPost = Union[PointsPost, PolygonRedactReasonPost, MetadataRedactReasonPost]
