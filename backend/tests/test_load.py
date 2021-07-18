import pytest
from girder.plugin import loadedPlugins


@pytest.mark.plugin("imagedephi")
def test_import(server):
    assert "imagedephi" in loadedPlugins()
