"""Real Picard plugin loader and option-page lifecycle; isolated settings only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication, QTabWidget
from PyQt6.QtGui import QFont, QFontDatabase
from picard import config
import picard.options
from picard.plugin3.plugin import Plugin


class LifecycleTests(unittest.TestCase):
    def test_enable_options_and_disable(self):
        app = QApplication.instance() or QApplication([])
        app.window = None
        app.albums = {}
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='picard-borunzio-test-') as tmp:
            config.setup_config(app, str(Path(tmp) / 'settings.ini'))
            plugin = Plugin(root.parent, root.name)
            plugin.read_manifest()
            module = plugin.load_module()
            plugin.enable(app)
            from importlib import import_module
            options = import_module(module.__name__ + '.options')
            with patch('picard.ui.options.tagger_instance', return_value=app):
                page = options.Settings()
            page.load()
            self.assertTrue(page.controls['automatic'].isChecked())
            self.assertEqual(page.combos['artist_separator'].currentData(), 'space')
            self.assertEqual(page.combos['album_separator'].currentData(), 'space')
            self.assertEqual(page.combos['track_separator'].currentData(), 'space')
            self.assertEqual(page.language.text(), 'eng')
            page.combos['artist_separator'].setCurrentIndex(page.combos['artist_separator'].findData('parentheses'))
            page.combos['album_separator'].setCurrentIndex(page.combos['album_separator'].findData('hyphen'))
            page.combos['track_separator'].setCurrentIndex(page.combos['track_separator'].findData('dash'))
            page.language.setText('ita')
            page.controls['automatic'].setChecked(False)
            page.check()  # Picard calls this zero-argument hook before saving.
            page.save()
            self.assertFalse(module._controller.api.plugin_config['automatic'])
            self.assertEqual(module._controller.api.plugin_config['artist_separator'], 'parentheses')
            self.assertEqual(module._controller.api.plugin_config['album_separator'], 'hyphen')
            self.assertEqual(module._controller.api.plugin_config['track_separator'], 'dash')
            self.assertEqual(module._controller.api.plugin_config['track_language'], 'ita')
            page.restore_defaults()
            self.assertEqual(page.language.text(), 'eng')
            self.assertEqual(page.combos['artist_separator'].currentData(), 'space')
            self.assertTrue(page.controls['automatic'].isChecked())
            snapshot_dir = os.environ.get('BILINGUAL_OPTIONS_SCREENSHOTS')
            if snapshot_dir:
                folder = Path(snapshot_dir)
                folder.mkdir(parents=True, exist_ok=True)
                for font_file in ('segoeui.ttf', 'msyh.ttc', 'msjh.ttc', 'YuGothM.ttc'):
                    font_path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / font_file
                    if font_path.is_file():
                        QFontDatabase.addApplicationFont(str(font_path))
                app.setFont(QFont('Segoe UI', 10))
                page.language.setFont(QFont('Segoe UI', 10))
                page.language.setText(page.language.text())
                page.resize(1000, 850)
                page.show()
                tabs = page.findChild(QTabWidget)
                for index in range(tabs.count()):
                    tabs.setCurrentIndex(index)
                    app.processEvents()
                    page.grab().save(str(folder / f'options-{index}.png'))
            controller = module._controller
            page.close()
            plugin.disable()
            self.assertFalse(controller.active)
            self.assertIsNone(module._controller)


if __name__ == '__main__':
    unittest.main(verbosity=2)
