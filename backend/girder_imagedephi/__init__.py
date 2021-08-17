from girder import plugin
from girder_worker import GirderWorkerPluginABC

from .rest import getIfds, getMetadata
from .vips import getTile, getTileSizes, getTumbnail


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = "ImageDePHI"

    def load(self, info):
        plugin.getPlugin("large_image").load(info)
        plugin.getPlugin("large_image_annotation").load(info)
        info["apiRoot"].item.route("GET", (":id", "imagedephi", "descructure"), getIfds)
        info["apiRoot"].item.route(
            "GET", (":id", "imagedephi", "metadata", ":ifd"), getMetadata
        )
        info["apiRoot"].item.route(
            "GET", (":id", "imagedephi", "tile", ":ifd", ":z", ":x", ":y"), getTile
        )
        info["apiRoot"].item.route(
            "GET", (":id", "imagedephi", "tile", ":ifd", ":z"), getTileSizes
        )
        info["apiRoot"].item.route(
            "GET", (":id", "imagedephi", "thumbnail", ":ifd"), getTumbnail
        )


class GirderTaskPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        return ["girder_imagedephi.tasks"]
