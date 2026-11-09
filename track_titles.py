"""Discover translated track lists without changing the selected release."""
import re
from .rules import pair


def tracks(release):
    return [track for medium in release.get('media', []) for track in medium.get('tracks', [])]


def signature(release):
    media = release.get('media') or []
    if not media:
        return None
    result = []
    for medium in media:
        values = medium.get('tracks') or []
        if (not values or len(values) != medium.get('track-count')
                or medium.get('pregap') or medium.get('data-tracks')):
            return None
        ids = tuple(t.get('recording', {}).get('id') for t in values)
        if not all(ids):
            return None
        result.append(ids)
    return tuple(result)


def language(release):
    return (release.get('text-representation') or {}).get('language', '') or ''


def allowed(release, cfg):
    status = release.get('status', '')
    return (status == 'Official' or (status == 'Pseudo-Release' and cfg['track_pseudo'])
            or (status not in ('Official', 'Pseudo-Release') and cfg['track_unofficial']))


def compatible(current, candidate, cfg):
    identity = signature(current)
    return (identity is not None and signature(candidate) == identity
            and current.get('release-group', {}).get('id') == candidate.get('release-group', {}).get('id')
            and language(candidate) == cfg['track_language'].strip().lower()
            and allowed(candidate, cfg))


def clean_title(title, strip_features):
    if strip_features:
        title = re.sub(r"\s+(?:[\[(]\s*)?(?:feat\.?|ft\.?|featuring)\s+.*$", '', title, flags=re.IGNORECASE)
    return title.strip()


def format_title(translated, original, current, cfg):
    translated = clean_title(translated, cfg['track_strip_features'])
    original = clean_title(original, cfg['track_strip_features'])
    if not translated or not original or translated.casefold() == original.casefold():
        return None
    # Use the raw release title as the original, not Picard's translated display title.
    # Preserve script capitalization when it still represents that same original text.
    current_clean = clean_title(current, cfg['track_strip_features'])
    base = current_clean if current_clean.casefold() == original.casefold() else original
    for style in ('space', 'parentheses', 'hyphen', 'dash'):
        for direction in ('translated_first', 'original_first'):
            previous = pair(translated, original, style, direction)
            if current.casefold() == previous.casefold():
                base = original
    return pair(translated, base, cfg['track_separator'], cfg['track_order'])


class TrackSearch:
    def __init__(self, controller, current, cfg, valid, callback):
        self.controller = controller
        self.current = current
        self.cfg = cfg
        self.valid = valid
        self.callback = callback
        self.listing = {}
        self.matches = []
        self.expected = signature(current)
        self.group_id = current.get('release-group', {}).get('id')

    def start(self):
        if not self.expected or not self.group_id:
            self.callback({}, '', 'Track translations skipped: incomplete recording or disc data.')
            return
        target = self.cfg['track_language'].strip().lower()
        if not re.fullmatch('[a-z]{3}', target):
            self.callback({}, '', 'Track translations skipped: use a three-letter MusicBrainz language code.')
            return
        self.browse()

    def failed(self, error):
        self.callback({}, '', 'Track translation search failed; track titles unchanged. ' + str(error))

    def browse(self, offset=0):
        def received(document, error):
            if not self.valid():
                return
            if error:
                self.failed(error)
                return
            page = document.get('releases', [])
            if not isinstance(page, list):
                self.failed('Invalid release list.')
                return
            self.listing.update((r['id'], r) for r in page if r.get('id'))
            total = document.get('release-count', offset + len(page))
            if offset + len(page) < total:
                if not page:
                    self.failed('Incomplete release list.')
                else:
                    self.browse(offset + len(page))
                return
            queue = []
            for candidate in self.listing.values():
                candidate_language = language(candidate)
                counts = tuple(m.get('track-count') for m in candidate.get('media', []))
                if (allowed(candidate, self.cfg)
                        and (not candidate_language or candidate_language == self.cfg['track_language'].strip().lower())
                        and (not counts or counts == tuple(len(m) for m in self.expected))):
                    queue.append(candidate['id'])
            self.details(sorted(queue))
        self.controller.request('/release', {'release-group': self.group_id, 'inc': 'media',
                                           'limit': 100, 'offset': offset}, received)

    def details(self, queue):
        if not self.valid():
            return
        if not queue:
            self.finish()
            return
        identifier = queue.pop(0)
        def received(document, error):
            if not self.valid():
                return
            if error:
                self.failed(error)
                return
            if compatible(self.current, document, self.cfg):
                values = tracks(document)
                originals = tracks(self.current)
                pairs = [(o, t.get('title', '')) for o, t in zip(originals, values)]
                count = sum(bool(t.strip()) and clean_title(t, True).casefold() !=
                            clean_title(o.get('title', ''), True).casefold() for o, t in pairs)
                # Use one coherent source list; never mix releases track by track.
                preference = self.cfg['track_preference']
                status_rank = (document.get('status') != 'Official' if preference == 'official'
                               else document.get('status') != 'Pseudo-Release')
                if preference == 'most_different':
                    score = (-count, document.get('status') != 'Official')
                else:
                    score = (status_rank, -count)
                if count:
                    self.matches.append((*score, identifier, pairs))
            self.details(queue)
        self.controller.request('/release/' + identifier,
                                {'inc': 'recordings+release-groups+media'}, received)

    def finish(self):
        if not self.matches:
            self.callback({}, '', 'No compatible track list with the selected language was found.')
            return
        _, _, identifier, pairs = min(self.matches, key=lambda m: m[:3])
        mapping = {o['id']: (translated, o.get('title', '')) for o, translated in pairs
                   if o.get('id') and translated.strip()}
        self.callback(mapping, identifier, 'Track title source: ' + identifier)
