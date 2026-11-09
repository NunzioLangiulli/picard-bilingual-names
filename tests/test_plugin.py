"""Tests for names, editable translations and post-Lookup execution."""
import importlib.util
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bilingual_test_plugin', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)
from bilingual_test_plugin.rules import *
from bilingual_test_plugin.controller import Controller
from bilingual_test_plugin.options import DEFAULTS
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from picard.metadata import Metadata

APP = QApplication.instance() or QApplication([])
RG = '5214f8d2-138a-333f-b50f-814a61856934'
ARTIST = {'id': 'artist-1', 'name': '坂本龍一', 'aliases': [{'locale': 'en', 'name': 'Ryuichi Sakamoto', 'primary': True}]}
CREDITS = [{'artist': {'id': 'artist-1', 'name': '坂本龍一'}, 'name': '坂本龍一'}]


class Item:
    def __init__(self, **tags):
        self.metadata = Metadata(tags)
        self.update = Mock()


class RulesTests(unittest.TestCase):
    def test_artist_alias_and_original(self):
        self.assertEqual(artist_name(CREDITS[0], {'artist-1': ARTIST}), 'Ryuichi Sakamoto 坂本龍一')
        self.assertEqual(artist_name(CREDITS[0], {}), '坂本龍一')

    def test_english_unchanged_and_credited_native_preserved(self):
        self.assertEqual(artist_name({'name': 'Queen', 'artist': {'name': 'Queen'}}, {}), 'Queen')
        credit = {'name': '王靖雯', 'artist': {'id': 'faye'}}
        details = {'faye': {'name': '王菲', 'aliases': [{'name': 'Faye Wong', 'locale': 'en'}]}}
        self.assertEqual(artist_name(credit, details), 'Faye Wong 王靖雯')

    def test_native_alias_for_latin_canonical_name(self):
        artist = {'id': 'artist-1', 'name': 'Ryuichi Sakamoto', 'aliases': [
            {'locale': 'ja', 'name': '坂本龍一', 'primary': True}]}
        self.assertEqual(artist_name({'artist': artist}, {'artist-1': artist}), 'Ryuichi Sakamoto 坂本龍一')

    def test_translated_multiartist_credit_is_not_duplicated(self):
        credits = [dict(CREDITS[0], joinphrase=' & '), {'artist': {'name': 'David Sylvian'}}]
        self.assertEqual(track_artists('Ryuichi Sakamoto & David Sylvian', credits, {'artist-1': ARTIST}),
                         'Ryuichi Sakamoto 坂本龍一; David Sylvian')

    def test_track_guests_and_idempotence(self):
        value = track_artists('坂本龍一; Guest', CREDITS, {'artist-1': ARTIST})
        self.assertEqual(value, 'Ryuichi Sakamoto 坂本龍一; Guest')
        self.assertEqual(track_artists(value, CREDITS, {'artist-1': ARTIST}), value)

    def test_verified_override_and_subtitle(self):
        release = {'title': '執迷不悔'}
        group = {'id': RG, 'title': '執迷不悔', 'disambiguation': 'No Regrets'}
        overrides = parse_overrides(DEFAULT_OVERRIDES)
        expected = 'No Regrets 執迷不悔 (Deluxe Edition)'
        self.assertEqual(album_title(release, group, overrides, '執迷不悔 (Deluxe Edition)'), expected)
        self.assertEqual(album_title(release, group, overrides, expected), expected)
        self.assertIsNone(album_title(release, group, {}, '執迷不悔'))

    def test_alias_priority_and_validation(self):
        group = {'title': '原文', 'aliases': [{'name': 'English Title', 'locale': 'en'}]}
        self.assertEqual(album_title({'title': '原文'}, group, {}, '原文'), 'English Title 原文')
        for bad in ('[]', '{"wrong-id": "Title"}', '{'):
            with self.assertRaises(ValueError):
                parse_overrides(bad)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.api = SimpleNamespace(plugin_config=dict(DEFAULTS), logger=Mock(),
            tagger=SimpleNamespace(albums={}, window=None, webservice=Mock()), mb_api=Mock())
        self.controller = Controller(self.api)
        self.album = Item(album='執迷不悔')
        self.album.id = 'release-1'
        self.album.loaded = True
        self.album.run_when_loaded = lambda f: f()
        self.file = Item(album='執迷不悔', artist='坂本龍一', albumartist='坂本龍一', title='Track unchanged')
        self.track = Item(album='執迷不悔', artist='坂本龍一')
        self.track.files = [self.file]
        self.album.tracks = [self.track]
        self.api.tagger.albums[self.album.id] = self.album
        self.node = {'id': 'release-1', 'title': '執迷不悔', 'release-group': {'id': RG}, 'artist-credit': CREDITS}
        self.controller.credits[self.track] = CREDITS
        self.requests = []
        self.api.mb_api.get.side_effect = lambda path, cb, **kw: self.requests.append((path, cb)) or object()

    def tearDown(self):
        self.controller.disable()

    def respond(self):
        while self.requests:
            path, callback = self.requests.pop(0)
            callback(ARTIST if '/artist/' in path else {'id': RG, 'title': '執迷不悔'}, None, None)

    def test_automatic_after_matching(self):
        self.controller.capture(self.album, self.node)
        self.controller.schedule(self.album)
        QTest.qWait(1150)
        self.assertTrue(self.requests)
        self.respond()
        self.assertEqual(self.file.metadata['album'], 'No Regrets 執迷不悔')
        self.assertEqual(self.file.metadata['albumartist'], 'Ryuichi Sakamoto 坂本龍一')
        self.assertEqual(self.file.metadata['artist'], 'Ryuichi Sakamoto 坂本龍一')
        self.assertEqual(self.file.metadata['title'], 'Track unchanged')
        self.assertNotIn('artists', self.file.metadata)
        self.assertNotIn('albumartists', self.file.metadata)

    def test_independent_artist_and_album_settings(self):
        self.api.plugin_config.update(artist_separator='parentheses', album_separator='hyphen', tracks=False)
        self.controller.capture(self.album, self.node)
        QTest.qWait(1150)
        self.respond()
        self.assertEqual(self.file.metadata['albumartist'], 'Ryuichi Sakamoto (坂本龍一)')
        self.assertEqual(self.file.metadata['album'], 'No Regrets - 執迷不悔')
        self.assertEqual(self.file.metadata['title'], 'Track unchanged')

    def test_network_error_keeps_metadata(self):
        self.controller.capture(self.album, self.node)
        QTest.qWait(1150)
        self.requests.pop(0)[1](None, None, 'Network unavailable')
        self.assertEqual(self.file.metadata['album'], '執迷不悔')

    def test_manual_edit_cancels_write(self):
        self.controller.capture(self.album, self.node)
        QTest.qWait(1150)
        self.file.metadata['album'] = 'Manual album'
        self.respond()
        self.assertEqual(self.file.metadata['album'], 'Manual album')

    def test_manual_action_with_automatic_disabled_and_repeated_run(self):
        self.api.plugin_config['automatic'] = False
        self.controller.capture(self.album, self.node)
        plugin._controller = self.controller
        try:
            # Exercise the registered action callback without constructing a live menu.
            plugin.ApplyBilingualNames.callback(None, [self.album])
            QTest.qWait(25)
            self.assertTrue(self.requests)
            self.respond()
            self.assertEqual(self.file.metadata['album'], 'No Regrets 執迷不悔')
            self.api.plugin_config['album_separator'] = 'hyphen'
            plugin.ApplyBilingualNames.callback(None, [self.album])
            QTest.qWait(100)
            self.assertEqual(self.file.metadata['album'], 'No Regrets - 執迷不悔')
            self.assertFalse(self.api.plugin_config['automatic'])
        finally:
            plugin._controller = None

    def test_manual_on_album_loaded_before_plugin_activation(self):
        self.api.plugin_config['automatic'] = False
        raw = {'id': 'release-track', 'title': 'Track unchanged', 'artist-credit': CREDITS,
               'recording': {'id': 'recording-1'}}
        self.track.id = 'recording-1'
        self.api.plugin_config['tracks'] = False
        self.album._release_node = dict(self.node, media=[{'tracks': [raw], 'track-count': 1}])
        self.controller.run_manual(self.album)
        QTest.qWait(25)
        self.respond()
        QTest.qWait(25)
        self.respond()
        self.assertEqual(self.file.metadata['album'], 'No Regrets 執迷不悔')
        self.assertIs(self.controller.track_nodes[self.track], raw)

    def test_manual_request_cancelled_on_disable(self):
        self.api.plugin_config['automatic'] = False
        self.controller.capture(self.album, self.node)
        self.controller.run_manual(self.album)
        QTest.qWait(25)
        self.controller.disable()
        self.respond()
        self.assertEqual(self.file.metadata['album'], '執迷不悔')

    def test_disabled_automatic_makes_no_requests(self):
        self.api.plugin_config['automatic'] = False
        self.controller.capture(self.album, self.node)
        QTest.qWait(1150)
        self.assertFalse(self.requests)


if __name__ == '__main__':
    unittest.main(verbosity=2)
