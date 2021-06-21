import pytest

from girder.plugin import loadedPlugins


@pytest.mark.plugin('girder_imagedephi')
def test_import(server):
    assert 'girder_imagedephi' in loadedPlugins()
