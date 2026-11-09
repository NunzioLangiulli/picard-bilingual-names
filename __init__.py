"""MusicBrainz Picard 3 lifecycle entry points."""
from picard.plugin3.api import BaseAction

_controller = None


def album_metadata(api, album, metadata, release_node):
    _controller.capture(album, release_node)


def track_metadata(api, track, metadata, track_node, release_node=None):
    credits = track_node.get('artist-credit') or track_node.get('recording', {}).get('artist-credit', [])
    _controller.credits[track] = credits
    _controller.track_nodes[track] = track_node


def added(api, track, file):
    _controller.schedule(track.album)


def removed(api, album):
    _controller.remove(album)


class ApplyBilingualNames(BaseAction):
    NAME = 'Apply bilingual names now'
    TITLE = NAME

    def callback(self, albums):
        if _controller is not None:
            for album in albums:
                _controller.run_manual(album)


def enable(api):
    global _controller
    from .options import Settings, DEFAULTS
    from .controller import Controller
    for name, value in DEFAULTS.items():
        api.plugin_config.register_option(name, value)
    _controller = Controller(api)
    api.register_options_page(Settings)
    api.register_album_action(ApplyBilingualNames)
    api.register_album_metadata_processor(album_metadata, priority=1000)
    api.register_track_metadata_processor(track_metadata, priority=1000)
    api.register_file_post_addition_to_track_processor(added, priority=-1000)
    api.register_album_post_removal_processor(removed)


def disable():
    global _controller
    if _controller:
        _controller.disable()
        _controller = None
