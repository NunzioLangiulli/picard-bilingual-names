# Contributing

Use English for documentation, comments and interface text. Preserve the plugin UUID when making compatible updates.

## Report an issue

Include Picard and plugin versions, operating system, relevant options, steps to reproduce, expected/actual results and a minimal MusicBrainz example. Copy the relevant **View Error/Debug Log** excerpt (Ctrl+G on Windows), removing personal paths. Do not upload music files.

## Develop and test

Use Python 3.12+ with PyQt6, the official Picard 3.0.2 source and its dependencies importable. Run the test files listed in README in separate processes. They use temporary settings and synthetic music metadata; they do not write audio files. Add regression coverage for behavioral changes, update the changelog and keep interface labels consistent with the README.

State whether checks use simulated data, real Picard components, live requests or actual audio saves. Do not describe isolated tests as end-to-end validation. Review generated contributions before release. Use disposable audio copies for manual Lookup, settings and save verification.

## Release

Follow [PUBLISHING.md](PUBLISHING.md). Update the manifest, visible version and documentation together. Keep published tags immutable; create a new version for changes. The project uses the [MIT License](LICENSE); imported Picard components retain their own license.
