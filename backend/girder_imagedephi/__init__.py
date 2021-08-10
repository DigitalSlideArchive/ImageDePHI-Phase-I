from girder import plugin


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = "ImageDePHI"

    def load(self, info):
        plugin.getPlugin("large_image").load(info)
