"""Translated track source discovery and independent output settings."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('names_fixtures', ROOT / 'tests/test_plugin.py')
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)
from bilingual_test_plugin.rules import pair, album_title, artist_name, track_artists
from bilingual_test_plugin.track_titles import compatible, format_title, TrackSearch
from bilingual_test_plugin.options import DEFAULTS as PLUGIN_DEFAULTS
DEFAULTS = dict(PLUGIN_DEFAULTS, track_language='ita')


def release(identifier='current', titles=('原曲一', '原曲二'), lang='zho', ids=('a', 'b'), status='Official'):
    return {'id': identifier, 'title': '原文', 'status': status, 'release-group': {'id': f.RG},
            'text-representation': {'language': lang}, 'media': [{'track-count': 2,
            'tracks': [{'id': identifier + '-track-' + str(i), 'title': title, 'recording': {'id': recording}}
                       for i, (title, recording) in enumerate(zip(titles, ids))]}]}


class FormattingTests(unittest.TestCase):
    def test_separators_order_and_identical_names(self):
        for style, expected in [('space', 'English 原文'), ('parentheses', 'English (原文)'),
                                ('hyphen', 'English - 原文'), ('dash', 'English — 原文')]:
            self.assertEqual(pair('English', '原文', style), expected)
        self.assertEqual(pair('English', '原文', 'parentheses', 'original_first'), '原文 (English)')
        self.assertEqual(pair('Same', 'same'), 'same')
        self.assertEqual(pair('Italiano', 'English'), 'Italiano English')

    def test_old_format_is_replaced_without_duplication(self):
        self.assertEqual(album_title({'title': '執迷不悔'}, {'id': f.RG}, {f.RG: 'No Regrets'},
                                    'No Regrets (執迷不悔) (Deluxe Edition)', 'hyphen'),
                         'No Regrets - 執迷不悔 (Deluxe Edition)')
        self.assertEqual(track_artists('Ryuichi Sakamoto (坂本龍一); Guest', f.CREDITS,
                                       {'artist-1': f.ARTIST}, 'space'), 'Ryuichi Sakamoto 坂本龍一; Guest')

    def test_independent_formats_and_features(self):
        cfg = dict(DEFAULTS, track_separator='hyphen', track_order='original_first')
        self.assertEqual(format_title('Titolo italiano (feat. Guest)', '原曲', '原曲', cfg), '原曲 - Titolo italiano')
        self.assertEqual(format_title('Italian', 'Original', 'Italian (Original)', dict(DEFAULTS)), 'Italian Original')
        self.assertEqual(format_title('Titolo italiano', '原曲', 'English alias', dict(DEFAULTS)), 'Titolo italiano 原曲')
        self.assertIsNone(format_title('Same', 'same', 'same', cfg))
        self.assertIsNone(format_title('', 'Original', 'Original', cfg))

    def test_language_and_recording_constraints(self):
        current = release()
        self.assertTrue(compatible(current, release('it', lang='ita'), DEFAULTS))
        self.assertFalse(compatible(current, release('wrong', lang='eng'), DEFAULTS))
        self.assertFalse(compatible(current, release('wrong', lang='ita', ids=('b','a')), DEFAULTS))
        self.assertFalse(compatible(current, release('unknown', lang=''), DEFAULTS))
        pseudo = release('pseudo', lang='ita', status='Pseudo-Release')
        self.assertTrue(compatible(current, pseudo, DEFAULTS))
        self.assertFalse(compatible(current, pseudo, dict(DEFAULTS, track_pseudo=False)))


class DiscoveryTests(unittest.TestCase):
    def run_search(self, documents, cfg=None, error_id=None):
        current = release()
        results = []
        calls = []
        class Controller:
            def request(self, path, query, callback):
                calls.append((path, query))
                if path == '/release':
                    offset = query['offset']
                    # One item per page exercises pagination, even with the requested limit of 100.
                    callback({'releases': documents[offset:offset+1], 'release-count': len(documents)}, None)
                else:
                    identifier = path.rsplit('/',1)[1]
                    callback(next(d for d in documents if d['id'] == identifier),
                             'Unavailable' if identifier == error_id else None)
        TrackSearch(Controller(), current, cfg or dict(DEFAULTS), lambda: True,
                    lambda *args: results.append(args)).start()
        return results[0], calls

    def test_all_pages_and_best_source_without_mixing(self):
        one = release('one', ('Uno', '原曲二'), 'ita')
        two = release('two', ('Primo', 'Secondo'), 'ita', status='Pseudo-Release')
        english = release('eng', ('First', 'Second'), 'eng')
        result, calls = self.run_search([one, english, two])
        self.assertEqual(result[1], 'two')
        self.assertEqual(result[0]['current-track-0'][0], 'Primo')
        self.assertEqual(result[0]['current-track-1'][0], 'Secondo')
        self.assertEqual(sum(path == '/release' for path, query in calls), 3)
        self.assertFalse(any(path == '/release/eng' for path, query in calls))
        result, _ = self.run_search([one, two], dict(DEFAULTS, track_preference='official'))
        self.assertEqual(result[1], 'one')

    def test_no_language_no_match_and_failure(self):
        unknown = release('unknown', ('Uno','Due'), '')
        result, _ = self.run_search([unknown])
        self.assertEqual(result[0], {})
        result, _ = self.run_search([release('it',('Uno','Due'),'ita')], error_id='it')
        self.assertEqual(result[0], {})
        self.assertIn('failed', result[2])

    def test_default_language_is_english(self):
        self.assertEqual(PLUGIN_DEFAULTS['track_language'], 'eng')
        result, _ = self.run_search([release('eng', ('First', 'Second'), 'eng')], dict(PLUGIN_DEFAULTS))
        self.assertEqual(result[1], 'eng')

    def test_language_is_configurable(self):
        english = release('eng', ('First', 'Second'), 'eng')
        result, _ = self.run_search([english], dict(DEFAULTS, track_language='eng'))
        self.assertEqual(result[1], 'eng')


class IntegrationTests(f.IntegrationTests):
    # Inherit the existing regression checks and add end-to-end controller coverage.
    def test_track_titles_apply_automatically_without_release_switch(self):
        self.api.plugin_config.update(artists=False, titles=False, track_language='ita')
        self.node = release()
        self.node['id'] = self.album.id
        self.album.tracks = []
        for raw in self.node['media'][0]['tracks']:
            item = f.Item(title=raw['title'], album='Original album', date='2000')
            item.files = [f.Item(title=raw['title'], album='Original album', date='2000')]
            self.album.tracks.append(item)
            self.controller.track_nodes[item] = raw
        self.controller.capture(self.album, self.node)
        f.QTest.qWait(1150)
        italian = release('it', ('Uno', 'Due'), 'ita')
        path, callback = self.requests.pop(0)
        self.assertEqual(path, '/release')
        callback({'releases': [italian], 'release-count': 1}, None, None)
        self.requests.pop(0)[1](italian, None, None)
        self.assertEqual(self.album.tracks[0].files[0].metadata['title'], 'Uno 原曲一')
        self.assertEqual(self.album.tracks[1].files[0].metadata['title'], 'Due 原曲二')
        self.assertEqual(self.album.id, 'release-1')
        self.assertEqual(self.album.tracks[0].files[0].metadata['album'], 'Original album')
        self.assertEqual(self.album.tracks[0].files[0].metadata['date'], '2000')


if __name__ == '__main__':
    unittest.main(verbosity=2)
