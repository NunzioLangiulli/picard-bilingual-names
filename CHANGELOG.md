# Changelog

## 0.2.2

- Default translated track-title discovery to English (`eng`) for new installations and restored defaults. Existing saved language choices are retained.
- Align examples, installation instructions and public documentation with the default and current behavior.
- Add publication and contribution guides.

## 0.2.1

- Fix options saving by renaming the checkbox helper that shadowed Picard's `check()` validation hook.
- Add the album context action **Plugins > Apply bilingual names now**, including use with automatic processing disabled and repeated application after changing options.
- Recover retained source data for already loaded albums when possible, and preserve manual execution while waiting for automatic edition selection.
- Extend regression coverage for options validation, manual execution, repeated formatting and disable cancellation.

## 0.2.0

- Add independent artist, album and track language separators: space (default), parentheses, hyphen or dash, plus independent language order and live examples.
- Search all release-list pages for a compatible translated track list without changing the selected edition. Default target language: Italian (`ita`).
- Add source language, release status, source preference and featured-credit cleanup options. Require identical recording sequences and disc layout; never infer a translation from script alone.
- Organize options into three tabs, retaining editable verified album-title overrides.
- Preserve existing enable flags and overrides; new separators default to space and track-title discovery defaults to enabled.
- Extend automated coverage for formatting migration, source discovery and options persistence.

## 0.1.0

- Initial implementation for Picard 3.0.2.
- Experimental release; live Lookup and audio-save validation remain necessary.
