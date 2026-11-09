"""Pure rules for bilingual MusicBrainz names; no machine translation."""
import json
import unicodedata
from uuid import UUID

DEFAULT_OVERRIDES = '{\n  "5214f8d2-138a-333f-b50f-814a61856934": "No Regrets"\n}'


def parse_overrides(text):
    values = json.loads(text)
    if not isinstance(values, dict):
        raise ValueError('Overrides must be a JSON object mapping MusicBrainz IDs to English titles.')
    for key, value in values.items():
        UUID(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Each title must be a nonempty string.')
    return values


def non_latin(text):
    return any(c.isalpha() and 'LATIN' not in unicodedata.name(c, '') for c in text)


def english_alias(node):
    aliases = [a for a in node.get('aliases', [])
               if str(a.get('locale', '')).lower().split('_')[0].split('-')[0] == 'en'
               and a.get('name') and not non_latin(a['name']) and not a.get('ended')]
    aliases.sort(key=lambda a: (not a.get('primary', False), a['name'].casefold()))
    return aliases[0]['name'] if aliases else ''


def pair(english, original, separator='space', order='translated_first'):
    if not english or not original:
        return original or english
    if english.casefold() == original.casefold():
        return original
    first, second = (original, english) if order == 'original_first' else (english, original)
    if separator == 'parentheses':
        return f'{first} ({second})'
    return first + {'space': ' ', 'hyphen': ' - ', 'dash': ' — '}.get(separator, ' ') + second


def artist_name(credit, details, separator='space', order='translated_first'):
    artist = credit.get('artist', {})
    node = details.get(artist.get('id'), artist)
    credited = credit.get('name', '')
    canonical = node.get('name', artist.get('name', ''))
    original = credited if non_latin(credited) else canonical
    if not non_latin(original):
        native = [a for a in node.get('aliases', []) if a.get('name') and non_latin(a['name'])
                  and a.get('primary') and not a.get('ended')]
        native.sort(key=lambda a: (a.get('locale') not in ('ja', 'zh', 'ko'), a['name']))
        if native:
            original = native[0]['name']
    english = english_alias(node)
    if not english and canonical and not non_latin(canonical):
        english = canonical
    if not english and credited and not non_latin(credited):
        english = credited
    if not non_latin(original):
        return credited or canonical
    return pair(english, original, separator, order)


def artist_list(credits, details, separator='space', order='translated_first'):
    return [artist_name(c, details, separator, order) for c in credits if isinstance(c, dict) and c.get('artist')]


def track_artists(current, credits, details, separator='space', order='translated_first'):
    """Use MusicBrainz credits while retaining additional semicolon-separated guests."""
    names = artist_list(credits, details, separator, order)
    known = set(names)
    # Recognize previous output styles when formatting preferences change.
    for style in ('space', 'parentheses', 'hyphen', 'dash'):
        for direction in ('translated_first', 'original_first'):
            known.update(artist_list(credits, details, style, direction))
    for c in credits:
        node = details.get(c.get('artist', {}).get('id'), c.get('artist', {}))
        known.update(filter(None, [c.get('name'), node.get('name'), node.get('sort-name')]))
        known.update(a.get('name', '') for a in node.get('aliases', []))
    joined = ''.join((c.get('name') or c.get('artist', {}).get('name', '')) + c.get('joinphrase', '') for c in credits)
    known.add(joined)
    for variant in ('canonical', 'english', 'bilingual'):
        parts = []
        for c in credits:
            node = details.get(c.get('artist', {}).get('id'), c.get('artist', {}))
            if variant == 'bilingual':
                name = artist_name(c, details, separator, order)
            elif variant == 'english':
                name = english_alias(node) or node.get('name', '')
            else:
                name = node.get('name', '')
            parts.append(name + c.get('joinphrase', ''))
        known.add(''.join(parts))
    known_lower = {n.casefold() for n in known}
    for value in current.split(';'):
        value = value.strip()
        if value and value.casefold() not in known_lower:
            names.append(value)
            known_lower.add(value.casefold())
    return '; '.join(dict.fromkeys(names))


def album_title(release, group, overrides, current, separator='space', order='translated_first'):
    original = release.get('title', '')
    if not non_latin(original):
        original = group.get('title', original)
    if not non_latin(original):
        return None
    english = overrides.get(group.get('id')) or english_alias(release) or english_alias(group)
    if not english:
        return None
    result = pair(english, original, separator, order)
    # Preserve an edition subtitle already appended by the user's tagging script.
    bases = [result, release.get('title', ''), original, english]
    bases.extend(pair(english, original, style, direction)
                 for style in ('space', 'parentheses', 'hyphen', 'dash')
                 for direction in ('translated_first', 'original_first'))
    for base in sorted(filter(None, bases), key=len, reverse=True):
        if current.casefold().startswith(base.casefold()):
            suffix = current[len(base):].strip()
            if not suffix:
                return result
            if suffix.startswith('(') and suffix.endswith(')'):
                return result + ' ' + suffix
    return result
