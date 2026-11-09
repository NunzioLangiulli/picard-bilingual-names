"""Apply bilingual artist and album names after scripts and file matching."""
from weakref import WeakKeyDictionary
from PyQt6.QtCore import QTimer
from .runtime import Runtime, snapshot
from .rules import album_title, artist_list, non_latin, parse_overrides, track_artists
from .track_titles import TrackSearch, format_title
from .options import DEFAULTS


class Controller(Runtime):
    def __init__(self, api):
        super().__init__(api)
        self.credits = WeakKeyDictionary()
        self.track_nodes = WeakKeyDictionary()

    def run_manual(self, album):
        if not self.active:
            return
        if not getattr(album, 'loaded', False):
            self.message('Bilingual Names: wait for the album to finish loading, then retry.')
            return
        if album not in self.nodes:
            # Support albums loaded before the plugin was enabled, without reloading metadata.
            node = getattr(album, '_release_node', None)
            if not isinstance(node, dict):
                self.message('Bilingual Names: refresh this album once to load its MusicBrainz source data.')
                return
            raw_tracks = [t for m in node.get('media', []) for t in m.get('tracks', [])]
            if (len(raw_tracks) != len(album.tracks)
                    or any(getattr(t, 'id', None) != raw.get('recording', {}).get('id')
                           for t, raw in zip(album.tracks, raw_tracks))):
                self.message('Bilingual Names: refresh this album once to capture its track mapping.')
                return
            self.nodes[album] = node
            for track, raw in zip(album.tracks, raw_tracks):
                self.track_nodes[track] = raw
                self.credits[track] = raw.get('artist-credit') or raw.get('recording', {}).get('artist-credit', [])
        if not any(track.files for track in album.tracks):
            self.message('Bilingual Names: match audio files to this album before applying names.')
            return
        self.message('Bilingual Names: applying rules to the selected album.')
        self.schedule(album, manual=True)

    def start(self, album, token):
        manual = self.manual_tokens.get(album) is token
        def defer_for_edition():
            other = getattr(album, '_borunzio_earliest_pending', None)
            if other and other.active and other.api.plugin_config['automatic']:
                self.done.pop(album, None)
                QTimer.singleShot(1000, lambda: self.schedule(album, manual=manual) if self.active else None)
                return True
            return False
        if defer_for_edition():
            return
        cfg = self.api.plugin_config
        if not (cfg['artists'] or cfg['titles'] or cfg['tracks']):
            return
        node = self.nodes[album]
        release_id = album.id
        original_snapshot = snapshot(album)
        config_snapshot = tuple(cfg[key] for key in DEFAULTS)
        try:
            overrides = parse_overrides(cfg['overrides']) if cfg['titles'] else {}
        except (ValueError, TypeError) as error:
            self.message('Bilingual Names: invalid title overrides: ' + str(error))
            return
        group_id = node.get('release-group', {}).get('id')
        details = {}
        group = dict(node.get('release-group', {}))
        all_credits = list(node.get('artist-credit', []))
        for track in album.tracks:
            all_credits.extend(self.credits.get(track, []))
        ids = sorted({c.get('artist', {}).get('id') for c in all_credits if c.get('artist', {}).get('id')})
        queue = ([('release-group', group_id)] if cfg['titles'] and group_id else [])
        if cfg['artists']:
            queue.extend(('artist', identifier) for identifier in ids)

        def valid():
            return (self.valid(album, token) and not defer_for_edition() and album.id == release_id
                    and getattr(album, 'loaded', False)
                    and tuple(cfg[key] for key in DEFAULTS) == config_snapshot)

        def finish(track_titles=None, source='', notice=''):
            if not valid():
                return
            if snapshot(album) != original_snapshot:
                self.message('Bilingual Names: metadata changed during retrieval; refresh the album to retry.')
                return
            if notice:
                self.message('Bilingual Names: ' + notice)
            self.apply(album, node, group, details, overrides, track_titles or {})

        def step():
            if not valid():
                return
            if not queue:
                if cfg['tracks']:
                    TrackSearch(self, node, dict((key, cfg[key]) for key in DEFAULTS), valid, finish).start()
                else:
                    finish()
                return
            entity, identifier = queue.pop(0)
            def received(document, error):
                if not valid():
                    return
                if error:
                    self.message('Bilingual Names: lookup failed; tags left unchanged. ' + error)
                    return
                if entity == 'artist':
                    details[identifier] = document
                else:
                    group.update(document)
                step()
            self.request('/' + entity + '/' + identifier, {'inc': 'aliases'}, received)
        step()

    def apply(self, album, node, group, details, overrides, translated_tracks=None):
        cfg = self.api.plugin_config
        credits = node.get('artist-credit', [])
        artist_format = (cfg['artist_separator'], cfg['artist_order'])
        album_names = artist_list(credits, details, *artist_format)
        bilingual_album_artists = any(non_latin(n) for n in album_names)
        for item in [album] + list(album.tracks):
            targets = [item] + list(getattr(item, 'files', []))
            for target in targets:
                metadata = target.metadata
                if cfg['titles']:
                    title = album_title(node, group, overrides, metadata.get('album', ''),
                                        cfg['album_separator'], cfg['album_order'])
                    if title:
                        metadata['album'] = title
                if cfg['artists'] and album_names and bilingual_album_artists:
                    metadata['albumartist'] = ' & '.join(album_names)
                track_credits = self.credits.get(item, [])
                if cfg['artists'] and track_credits:
                    names = artist_list(track_credits, details, *artist_format)
                    if any(non_latin(n) for n in names):
                        metadata['artist'] = track_artists(metadata.get('artist', ''), track_credits, details, *artist_format)
                raw_track = self.track_nodes.get(item, {})
                values = (translated_tracks or {}).get(raw_track.get('id'))
                if cfg['tracks'] and values:
                    title = format_title(*values, metadata.get('title', ''), cfg)
                    if title:
                        metadata['title'] = title
                if target is not album:
                    target.update()
        album.update()
        self.message('Bilingual Names: finished for ' + album.metadata.get('album', album.id))
