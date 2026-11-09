# Manual GitHub publication

Repository name: **picard-bilingual-names**
Owner: **NunzioLangiulli**
Release tag: **v0.2.2**

The local project is prepared for publication. These instructions do not mean that the repository is already online.

## Publish without Git installed

1. Sign in to GitHub and create a public repository named `picard-bilingual-names` under `NunzioLangiulli`. Do not initialize an extra README, license or .gitignore; this project already contains them.
2. Use **uploading an existing file** (or **Add file → Upload files** in an initialized repository). Upload the **contents** of this project folder, including Python files, `MANIFEST.toml`, README, LICENSE, guides, changelog and `tests/`. Do not put them inside another enclosing folder. Do not upload `.git`, caches, temporary files or music.
3. Commit the uploaded files to the default branch. Check that `MANIFEST.toml` and `__init__.py` appear at the repository root and that README links resolve.
4. Open **Releases → Draft a new release**. Create tag **v0.2.2** from the uploaded default branch. Use the same version in the release title, summarize the latest changelog entry and retain the documented limitations. Mark it as a pre-release while installed-application verification is outstanding.
5. Install the plugin in Picard using `https://github.com/NunzioLangiulli/picard-bilingual-names` and select **v0.2.2**. Confirm options, Lookup/manual behavior as applicable, and saving on disposable files.
6. Add the repository description from `MANIFEST.toml` and topics such as `musicbrainz`, `picard`, `picard-plugin`, `audio-metadata` and `python`.

Uploading through the browser does not transfer local Git history or tags: step 4 creates the public release tag. If you later publish using Git instead, push the local branch **and** tag; do not move a tag that has already been published.

## Optional repository metadata

After the repository exists, these optional fields may be added to `MANIFEST.toml` in a subsequent version:

```toml
homepage = "https://github.com/NunzioLangiulli/picard-bilingual-names"
report_bugs_to = "https://github.com/NunzioLangiulli/picard-bilingual-names/issues"
```

They are intentionally absent from the current manifest because the repository URL had not yet been verified as public during preparation.

## Related collection

The planned `NunzioLangiulli/picard-toolkit` repository contains the script packages and brief introductions linking to the separate plugins. Publish the two new plugin repositories before the collection, or retain the collection's note that their links are pending publication.
