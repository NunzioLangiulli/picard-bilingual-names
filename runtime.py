"""Shared asynchronous scaffolding, bundled locally so each plugin is independent."""
from weakref import WeakKeyDictionary
from PyQt6.QtCore import QTimer


def files(album):
    return [file for track in album.tracks for file in track.files]


def snapshot(album):
    items = [album] + list(album.tracks) + files(album)
    return tuple((id(item), tuple(sorted((k, tuple(item.metadata.getall(k)))
                                        for k in item.metadata.keys()))) for item in items)


class Runtime:
    def __init__(self, api):
        self.api = api
        self.active = True
        self.nodes = WeakKeyDictionary()
        self.tokens = WeakKeyDictionary()
        self.done = WeakKeyDictionary()
        self.manual_tokens = WeakKeyDictionary()
        self.cache = {}
        self.tasks = []

    def capture(self, album, node):
        self.nodes[album] = node
        self.done.pop(album, None)
        self.tokens[album] = object()
        album.run_when_loaded(lambda: self.schedule(album))

    def schedule(self, album, manual=False):
        if not self.active or (not manual and not self.api.plugin_config['automatic']):
            return
        if not manual and album in self.nodes and getattr(album, 'loaded', False):
            stamp = (id(self.nodes[album]), tuple(id(f) for f in files(album)))
            if self.done.get(album) == stamp:
                return
        token = object()
        self.tokens[album] = token
        if manual:
            self.manual_tokens[album] = token
        def run():
            if (self.valid(album, token) and getattr(album, 'loaded', False)
                    and files(album) and album in self.nodes):
                stamp = (id(self.nodes[album]), tuple(id(f) for f in files(album)))
                if manual or self.done.get(album) != stamp:
                    self.done[album] = stamp
                    self.start(album, token)
        QTimer.singleShot(0 if manual else 1000, run)

    def valid(self, album, token):
        return (self.active and (self.api.plugin_config['automatic'] or self.manual_tokens.get(album) is token)
                and self.tokens.get(album) is token
                and self.api.tagger.albums.get(album.id) is album)

    def message(self, text):
        self.api.logger.info(text)
        window = getattr(self.api.tagger, 'window', None)
        if window:
            window.set_statusbar_message(text, timeout=8000)

    def request(self, path, query, callback):
        key = (path, tuple(sorted(query.items())))
        if key in self.cache:
            QTimer.singleShot(0, lambda: callback(self.cache[key], None) if self.active else None)
            return
        holder = []
        def received(document, reply, error):
            if holder and holder[0] in self.tasks:
                self.tasks.remove(holder[0])
            if not self.active:
                return
            if error or not isinstance(document, dict):
                callback(None, str(error or 'Invalid MusicBrainz response'))
                return
            self.cache[key] = document
            callback(document, None)
        try:
            task = self.api.mb_api.get(path, received, unencoded_queryargs=dict(query, fmt='json'),
                parse_response_type='json', priority=False, important=False, mblogin=False)
            holder.append(task)
            self.tasks.append(task)
        except Exception as error:
            callback(None, str(error))

    def remove(self, album):
        self.manual_tokens.pop(album, None)
        self.tokens.pop(album, None)
        self.nodes.pop(album, None)
        self.done.pop(album, None)

    def disable(self):
        self.active = False
        for task in list(self.tasks):
            self.api.tagger.webservice.abort_task(task)
        self.tasks.clear()
        self.manual_tokens.clear()
        self.tokens.clear()
        self.nodes.clear()
        self.cache.clear()
