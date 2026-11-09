"""Independent output formatting and translated track-list discovery options."""
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)
from picard.plugin3.api import OptionsPage
from .rules import DEFAULT_OVERRIDES, parse_overrides, pair

DEFAULTS = dict(automatic=True, artists=True, titles=True, tracks=True, overrides=DEFAULT_OVERRIDES,
    artist_separator='space', album_separator='space', track_separator='space',
    artist_order='translated_first', album_order='translated_first', track_order='translated_first',
    track_language='eng', track_pseudo=True, track_unofficial=False,
    track_preference='most_different', track_strip_features=True)

STYLES = [('Space', 'space'), ('Parentheses', 'parentheses'), ('Hyphen ( - )', 'hyphen'), ('Dash ( — )', 'dash')]
ORDERS = [('Translated / romanized first', 'translated_first'), ('Original first', 'original_first')]


class Settings(OptionsPage):
    NAME = 'bilingual_names'
    TITLE = 'Bilingual Names'
    PARENT = 'plugins'

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Bilingual Names 0.2.2 | Author: Borunzio'))
        self.controls = {}
        self.combos = {}
        self.previews = {}
        self.add_checkbox(layout, 'automatic', 'Run automatically after Lookup and file matching')
        tabs = QTabWidget()
        layout.addWidget(tabs)
        formatting = QWidget()
        form_layout = QVBoxLayout(formatting)
        tabs.addTab(formatting, 'Names and formatting')
        for prefix, title, toggle, text in [
            ('artist', 'Artists', 'artists', 'Format artist and album artist names'),
            ('album', 'Album titles', 'titles', 'Format album titles'),
            ('track', 'Track titles', 'tracks', 'Find translated track titles in other releases'),
        ]:
            box = QGroupBox(title)
            box_layout = QVBoxLayout(box)
            self.add_checkbox(box_layout, toggle, text)
            form = QFormLayout()
            box_layout.addLayout(form)
            for suffix, label, items in [('separator', 'Separate the two languages with:', STYLES),
                                         ('order', 'Language order:', ORDERS)]:
                combo = QComboBox()
                for text, value in items:
                    combo.addItem(text, value)
                self.combos[prefix + '_' + suffix] = combo
                combo.currentIndexChanged.connect(self.preview)
                form.addRow(label, combo)
            self.previews[prefix] = QLabel()
            self.previews[prefix].setWordWrap(True)
            box_layout.addWidget(self.previews[prefix])
            form_layout.addWidget(box)
        self.label(form_layout, 'Artists and albums use English aliases. Missing translations keep the original. '
            'Album artists are joined with &; track artists with semicolon and space. '
            'The separators above only separate the two language versions of a name.')
        form_layout.addStretch()

        search = QWidget()
        search_layout = QVBoxLayout(search)
        tabs.addTab(search, 'Track title sources')
        form = QFormLayout()
        self.language = QLineEdit()
        self.language.setPlaceholderText('eng')
        form.addRow('Target language (three-letter MusicBrainz code):', self.language)
        search_layout.addLayout(form)
        self.label(search_layout, 'Examples: eng = English, ita = Italian, jpn = Japanese, zho = Chinese. '
            'The source release must explicitly declare this language. No machine translation or language guessing is used.')
        self.add_checkbox(search_layout, 'track_pseudo', 'Include pseudo-releases (often used for translated track lists)')
        self.add_checkbox(search_layout, 'track_unofficial', 'Include other release statuses, including bootlegs and unknown status')
        preference = QComboBox()
        for text, value in [('Most differing titles, then official releases', 'most_different'),
                            ('Official releases first', 'official'), ('Pseudo-releases first', 'pseudo')]:
            preference.addItem(text, value)
        self.combos['track_preference'] = preference
        ranking = QFormLayout()
        ranking.addRow('Prefer a compatible source:', preference)
        search_layout.addLayout(ranking)
        self.add_checkbox(search_layout, 'track_strip_features', 'Remove trailing feat., ft. or featuring credits from track titles')
        self.label(search_layout, 'Searches all pages of releases in the same release group. Detailed checks require the same '
            'recording IDs in the same order on every disc. Titles come from one compatible source release; the selected '
            'edition, dates and cover art do not change. A source with more differing titles is not necessarily a better translation. '
            'Missing, identical or unverified translations leave the current track title unchanged. '
            'No track list is applied if its search fails. This search can take time for albums with many editions.')
        search_layout.addStretch()

        overrides = QWidget()
        override_layout = QVBoxLayout(overrides)
        tabs.addTab(overrides, 'Verified album titles')
        self.label(override_layout, 'JSON mapping release-group MusicBrainz IDs to preferred English titles. '
            'These entries take priority over aliases. Disambiguation comments are never automatically treated as translations.')
        self.overrides = QPlainTextEdit()
        override_layout.addWidget(self.overrides)
        test = QPushButton('Validate overrides')
        test.setMaximumWidth(180)
        test.clicked.connect(self.validate_rules)
        override_layout.addWidget(test)
        self.result = QLabel()
        self.result.setWordWrap(True)
        override_layout.addWidget(self.result)
        self.label(layout, 'Save these options, then use the album menu: Plugins > Apply bilingual names now, or refresh the album. '
            'Wait for Bilingual Names to finish before saving audio files. No files are saved automatically.')

    def add_checkbox(self, layout, key, text):
        self.controls[key] = QCheckBox(text)
        layout.addWidget(self.controls[key])

    @staticmethod
    def label(layout, text):
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)

    def preview(self, *args):
        for prefix, label in self.previews.items():
            if prefix + '_order' in self.combos:
                first, second = {'artist': ('Ryuichi Sakamoto', '坂本龍一'),
                                 'album': ('No Regrets', '執迷不悔'),
                                 'track': ('English title', '原曲名')}[prefix]
                label.setText('Example: ' + pair(first, second,
                    self.combos[prefix + '_separator'].currentData(),
                    self.combos[prefix + '_order'].currentData()))

    def validate_rules(self):
        try:
            parsed = parse_overrides(self.overrides.toPlainText())
            self.result.setText(f'{len(parsed)} valid overrides.')
            return True
        except (ValueError, TypeError) as error:
            self.result.setText('Invalid overrides: ' + str(error))
            return False

    def populate(self, values):
        for key, control in self.controls.items():
            control.setChecked(values[key])
        for key, combo in self.combos.items():
            combo.setCurrentIndex(max(0, combo.findData(values[key])))
        self.language.setText(values['track_language'])
        self.overrides.setPlainText(values['overrides'])
        self.preview()

    def load(self):
        self.populate(self.api.plugin_config)

    def save(self):
        for key, control in self.controls.items():
            self.api.plugin_config[key] = control.isChecked()
        for key, combo in self.combos.items():
            self.api.plugin_config[key] = combo.currentData()
        self.api.plugin_config['track_language'] = self.language.text().strip().lower()
        self.api.plugin_config['overrides'] = self.overrides.toPlainText()

    def restore_defaults(self):
        self.populate(DEFAULTS)
