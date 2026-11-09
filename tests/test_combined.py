"""Run both controllers through an automatic edition switch and bilingual update.

This development test expects the two independent repositories to be siblings.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EARLIEST = ROOT.parent / 'picard-earliest-compatible-release'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(EARLIEST.is_dir(), 'Sibling Earliest Compatible Release repository required')
class CombinedTests(unittest.TestCase):
    def test_switch_then_bilingual_without_manual_action(self):
        self.run_case()

    def test_manual_action_waits_for_edition_with_automatic_disabled(self):
        self.run_case(manual=True)

    def run_case(self, manual=False):
        b = load('bilingual_fixtures', ROOT / 'tests/test_plugin.py')
        e = load('earliest_fixtures', EARLIEST / 'tests/test_plugin.py')
        from PyQt6.QtTest import QTest
        fixture = e.AutomaticTests()
        fixture.setUp()
        earliest = fixture.controller
        album = fixture.album
        api = b.SimpleNamespace(plugin_config=dict(b.DEFAULTS), logger=b.Mock(),
                                tagger=fixture.api.tagger, mb_api=b.Mock())
        if manual:
            api.plugin_config['automatic'] = False
        names = b.Controller(api)
        requests = []
        api.mb_api.get.side_effect = lambda path, cb, **kw: requests.append((path, cb)) or object()
        def node(identifier, date):
            value = e.release(identifier, date)
            value.update(title='執迷不悔', **{'release-group': {'id': b.RG}, 'artist-credit': b.CREDITS})
            return value
        def capture(value):
            for track in album.tracks:
                names.credits[track] = b.CREDITS
            earliest.capture(album, value)
            names.capture(album, value)
        def switch(identifier):
            fixture.api.tagger.albums.pop(album.id)
            album.id = identifier
            fixture.api.tagger.albums[identifier] = album
            capture(node(identifier, '1993-02-05'))
        album.switch_release_version.side_effect = switch
        try:
            capture(node('current', '2003'))
            if manual:
                names.run_manual(album)
            QTest.qWait(1200)
            self.assertFalse(requests, 'Bilingual requests must wait for edition selection')
            fixture.respond_list([node('older', '1993')])
            fixture.requests.pop(0)[1](node('older', '1993'), None, None)
            QTest.qWait(2400)
            self.assertTrue(requests)
            while requests:
                path, callback = requests.pop(0)
                callback(b.ARTIST if '/artist/' in path else {'id': b.RG, 'title': '執迷不悔'}, None, None)
            self.assertEqual(album.id, 'older')
            self.assertEqual(album.metadata['date'], '1993')
            self.assertEqual(album.metadata['album'], 'No Regrets 執迷不悔')
            album.switch_release_version.assert_called_once_with('older')
            self.assertFalse(fixture.requests, 'A selected older release must not trigger a switch loop')
        finally:
            names.disable()
            fixture.tearDown()


if __name__ == '__main__':
    unittest.main(verbosity=2)
