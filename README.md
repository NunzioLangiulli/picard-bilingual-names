# Bilingual Names for MusicBrainz Picard

Format artist names, album titles and translated track titles in two languages, with independent separators and language order for each field.

**Version:** 0.2.2 · **Author:** Borunzio · **License:** MIT

Targets **Picard 3.0.2**. Automated tests use actual Picard components with simulated albums and network callbacks. Verify the result in your installed Picard before saving your library.

## Examples

| Input | Output when the required alias is available |
| --- | --- |
| 坂本龍一 | Ryuichi Sakamoto 坂本龍一 |
| 執迷不悔 | No Regrets 執迷不悔 |
| 執迷不悔 (Deluxe Edition) | No Regrets 執迷不悔 (Deluxe Edition) |

No machine translation is performed. Missing translations preserve the original title or name. Existing Latin-script names are unchanged unless a primary native-script alias is available.

## Installation

From GitHub, open **Options → Plugins → Install Plugin**, choose repository URL installation and enter `https://github.com/NunzioLangiulli/picard-bilingual-names`. Select **v0.2.2**, enable the plugin and restart Picard. This URL becomes available after the repository and tag are published. Installing from `main` may show the branch name as the installed version.

### Local installation

In **Options → Plugins → Install Plugin → Local repository**, select this repository folder and the **v0.2.2** tag. Keep the `.git` directory. Enable the plugin and restart Picard. A GitHub Download ZIP is not a local Git repository.

Open **Options → Plugins → Bilingual Names**. Automatic processing and artist, album and track-title formatting start enabled. All three separators default to a simple space. Track-title search defaults to English (`eng`). Refresh albums that were loaded before enabling the plugin.

Run Lookup as usual. Processing starts after the release is loaded and files are matched, following the tagging scripts. MusicBrainz alias requests are asynchronous. Wait for the **Bilingual Names: finished** log/status message, review the new values, then save in Picard. The plugin never saves audio files automatically.

## Run manually from an album

Right-click a matched album and choose **Plugins → Apply bilingual names now**. The action works even when **Run automatically after Lookup and file matching** is disabled, and does not turn that setting on. It uses the saved artist, album, track and formatting options. Multiple selected albums are processed separately.

After changing and saving options, run the action again to apply them without repeating Lookup. An already processed album can be processed again; cached MusicBrainz responses are reused. Pending older runs are invalidated. No audio files are saved automatically.

If the album is still loading, wait for it to finish. Albums loaded before plugin activation can use their retained MusicBrainz data; if the original track mapping is unavailable, the log asks for one refresh. With Earliest Compatible Release active, manual and automatic name processing both wait for edition selection to settle.

### Options save error in 0.2.0

Version **0.2.1** fixes `Settings.check() missing 3 required positional arguments`. A checkbox-building helper accidentally replaced Picard's zero-argument options validation hook. The helper now has a separate name, and the lifecycle test explicitly checks the hook before saving settings. Existing options and plugin identity are preserved.

## Independent formatting

Under **Names and formatting**, artists, album titles and track titles each have their own enable checkbox, separator, language order and live example. Artist settings apply to both `artist` and `albumartist`.

| Separator | Example |
| --- | --- |
| Space (default) | `English Original` |
| Parentheses | `English (Original)` |
| Hyphen | `English - Original` |
| Dash | `English — Original` |

**Translated / romanized first** is the default order. **Original first** reverses the two language versions; parentheses then surround the translated version. Identical versions are not repeated. Separating two languages is independent of joining multiple artists: album artists still use ` & ` and track artists still use `; `.

For example, you can select `Ryuichi Sakamoto (坂本龍一)` for artists, `No Regrets 執迷不悔` for albums, and `English title - 原曲名` for tracks. Changing an output style does not nest the previous bilingual formatting. Use **Plugins → Apply bilingual names now** after saving options, or refresh the matched album.

## Artist rules

- Retrieve aliases for the credited MusicBrainz artists using Picard's MusicBrainz request queue.
- Prefer an active English alias marked primary; otherwise use an available active English alias. Regional English locales are accepted. A Latin canonical or credited name can supply the English/romanized form.
- Keep a native-script credited name when present, otherwise use the canonical native name. If both are Latin, a primary native-script alias can supply the original; Japanese, Chinese and Korean locales take precedence, followed by a deterministic name ordering.
- Format each qualifying name using its chosen separator and language order without translating it yourself or using a reversed sort name as a display name.
- Join album artists with ` & ` and track artists with `; `. MusicBrainz track credits provide the artist list; additional semicolon-separated guests already present in `artist` are retained.
- Do not create or restore `artists`, `albumartists` or MusicBrainz identifier tags. Track titles are handled separately by the optional translated track-list search below.

Formatting runs only for credits containing a non-Latin name or a suitable native alias. This is not an artist-nationality detector. Alias quality and the credited identity depend on MusicBrainz data.

## Album rules and editable overrides

Priority: a verified override for the release group, an English release alias, then an English release-group alias. The original is the native release title, falling back to the native release-group title. The default output is `English Title Original Title`; the album formatting controls can change this.

A trailing parenthesized edition subtitle produced by an existing script is retained when it follows a recognized title. The bilingual result replaces unrelated manual title rewrites on a fresh Lookup; it does not attempt to infer the meaning of arbitrary text. Repeated processing does not append the original title again.

The options page contains an editable JSON object mapping release-group IDs to preferred English titles:

```json
{
  "5214f8d2-138a-333f-b50f-814a61856934": "No Regrets"
}
```

Use **Validate overrides** after editing. Empty `{}` disables all explicit overrides while retaining alias lookup. Invalid JSON or identifiers stop processing without writing tags. Run the manual album action or refresh the album after changing the rules.

Disambiguation comments are never blindly treated as translations. In a live API check on 2026-11-05, the example release group supplied **No Regrets** as its primary English alias, so it also works without the explicit override. The override makes this particular spelling an intentional preference.

## Translated track titles from other releases

Enable **Find translated track titles in other releases** and open **Track title sources** to configure the search.

1. Browse every page of releases in the same MusicBrainz release group.
2. Filter out explicitly different languages, disallowed statuses and incompatible disc/track counts. Entries with missing summary language/count information receive detailed checks rather than being guessed.
3. Fetch the remaining release details. A usable source must explicitly declare the selected language and have the same recording IDs in the same order on every disc as the current release.
4. Select one coherent source track list using the configured preference. Do not mix titles from different releases. Ties are resolved by MusicBrainz ID for repeatability.
5. Combine each nonempty, different translated title with the original title from the selected release, using the track-specific separator and order.

**The selected edition does not change.** Only the track `title` fields change; release identifiers, dates and artwork are untouched by this search. Disc layouts with pregaps, data tracks or missing recording IDs are skipped rather than matched by track count alone. Duplicate recordings in a track list are handled by disc and track position, not collapsed into one recording ID entry.

### Track source options

| Option | Default | Meaning |
| --- | --- | --- |
| Target language | `eng` (English) | A three-letter MusicBrainz language code, such as `ita`, `jpn` or `zho`. This setting affects tracks, not the English artist/album aliases. |
| Include pseudo-releases | Enabled | Allows translated track lists represented as pseudo-releases in MusicBrainz. |
| Include other release statuses | Disabled | Also allows bootlegs, promotional releases and unknown statuses when enabled. |
| Source preference | Most differing titles, then official releases | Prefer more titles differing from the original; ties favor official releases. Alternatively, prefer official or pseudo-releases first. |
| Remove trailing feat., ft. or featuring credits | Enabled | Removes these suffixes from the translated and original titles when forming a bilingual result. It does not add those guests to artist credits. |

When a source-type preference is selected, it takes priority over the number of differing titles. A source with no differing nonempty titles is not used. More differing titles do **not** establish translation quality: review the result.

A source release's language label is the evidence for its language; the plugin cannot prove each individual title is translated correctly. Titles are not machine-translated or inferred from the use of Latin characters. Missing language metadata, missing translations and identical titles leave the existing title unchanged. If any required search request fails, no track-title result from that search is applied; independently retrieved artist and album names can still be applied.

The original side comes from the current release's raw MusicBrainz title, not from a translated title already displayed by Picard. Existing script capitalization is retained when it still represents that same original title. Other rewrites are not re-executed over the translated source titles. Removing featured-artist suffixes is optional and deliberately limited to trailing `feat.`, `ft.` and `featuring` patterns.

## Options and upgrades

The options page has three tabs: **Names and formatting**, **Track title sources**, and **Verified album titles**. All labels and comments are in English. The general Picard restore-defaults mechanism restores the defaults.

When upgrading from 0.1.0, existing enable flags and verified title overrides remain. Newly introduced separators use **Space**, and the new track-title search starts enabled. New installations of 0.2.2 use English (`eng`); an existing saved choice such as Italian (`ita`) is preserved. Set the language to `eng` or restore defaults if you want to change an existing installation. Disable it if you only want artist/album formatting. Save settings and use the manual album action or refresh already loaded albums to apply changes. Subsequent Lookups remain automatic when the automatic option is enabled.

## Compatibility with other processing

The plugin captures raw MusicBrainz identities before cleanup processors and changes the final display tags after scripts and file matching. Keep Only Tags does not need to retain writable MusicBrainz IDs for this plugin. Existing smart-capitalization and edition-subtitle scripts can remain enabled; this plugin preserves alias spelling and does not capitalize the newly appended names itself.

When **Earliest Compatible Release** is enabled, Bilingual Names waits for its edition selection to finish before retrieving/applying names. Each plugin can also run independently. Alias-request failures leave all fields unchanged; a track-source failure leaves track titles unchanged while independently retrieved artist/album names can still be applied. Manual metadata changes made while alias requests are pending cancel that update; refresh to retry. Disabling or removing an album invalidates pending updates.

MusicBrainz alias and release responses are cached for the plugin session. Restart Picard to retrieve data changed online during that session. Searching albums with many editions can take time; requests use Picard's MusicBrainz queue. There is no automatic saving and no artwork modification.

## Validation

Run each file in a separate Python process with PyQt6, Picard 3.0.2 source and its dependencies importable:

```sh
python -B tests/test_plugin.py
python -B tests/test_track_titles.py
python -B tests/test_lifecycle.py
python -B tests/test_combined.py
```

The combined test requires the sibling `picard-earliest-compatible-release` repository; otherwise it is skipped. Tests cover independent separators/order, guest preservation, format migration, repeated formatting, paginated track discovery, language/status preferences, strict recording matching, automatic title updates without release changes, disabled settings, network failure, user edits, actual plugin loading/options persistence/disabling, and coordination after an edition switch. They do not write audio files or prove live installed-application behavior.

## Reporting issues and license

Include Picard/plugin versions, an example MusicBrainz link, expected/output tags and the relevant **Ctrl+G** log excerpt. Remove private paths. Do not upload audio files.

[MIT License](LICENSE) · [Changelog](CHANGELOG.md). Independent community plugin by Borunzio.

See [CONTRIBUTING.md](CONTRIBUTING.md) for reports and development, and [PUBLISHING.md](PUBLISHING.md) for the manual GitHub publication steps.
