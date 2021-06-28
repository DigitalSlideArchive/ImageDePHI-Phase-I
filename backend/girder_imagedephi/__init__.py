from girder import plugin

from girder_imagedephi.resource import createEdit, downloadRedacted, getEdits


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = "ImageDePHI"

    def load(self, info):
        plugin.getPlugin("large_image").load(info)
        info["apiRoot"].item.route("GET", (":id", "edits"), getEdits)
        info["apiRoot"].item.route("POST", (":id", "edits"), createEdit)
        info["apiRoot"].item.route("GET", (":id", "redacted"), downloadRedacted)
