# Third-party notices

The root MIT license covers original ClassLens code, documentation, synthetic
assessment fixtures, learning material, and original mascot/hero imagery. The
maintainer confirmed publication rights for these original materials on
2026-11-25. It does not replace the licenses or trademarks of third parties.

## Bundled Graphify instructions

`.agents/skills/graphify/` contains the official skill and reference documents
installed from `graphifyy==0.9.77`. Upstream:
<https://github.com/Graphify-Labs/graphify>.

Copyright 2026 Safi Shamsi and the Graphify contributors.

These files retain their upstream terms. The installed distribution declares
Apache-2.0 and includes a notice for earlier MIT contributions. Its original
[Apache license](licenses/Graphify-Apache-2.0.txt),
[MIT license](licenses/Graphify-MIT.txt), and
[NOTICE](licenses/Graphify-NOTICE.txt) are preserved verbatim here.
The installed skill includes a marked ClassLens wrapper-only guard. ClassLens's
wrapper and validation scripts are separate original project code.

## Installed dependencies and downloaded models

Dependencies are installed separately through `frontend/package-lock.json` and
`backend/requirements.lock`; their upstream license files remain authoritative.
The [release dependency inventory](docs/releases/dependency-licenses.md) records
the declarations observed during release preparation, including transitive
packages. ClassLens does not redistribute installed environments or model weights.

Not all dependencies use MIT: Psycopg and its pool/binary distributions declare
LGPL-3.0-only; certifi declares MPL-2.0; tqdm declares MPL-2.0 AND MIT; NumPy and
binary scientific packages carry additional bundled-component notices. Preserve
their notices and comply with their terms if distributing environments, binaries,
containers, or modified copies. The source release is not a blanket license for
those components.

The pinned `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` model
declares Apache-2.0 in its [model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/tree/e8f8c211226b894fcb81acc59f3b34ba3efd5f42).
The model is downloaded on first use and cached, not committed. Gemini is a
separate hosted service governed by your Google account's applicable terms.

## Template assets

Unused React/Vite template SVGs and the unused template social-icon sprite were
removed from the release tree. They remain in preserved Git history under their
upstream terms; they are not original ClassLens artwork. Historical third-party
material is not relicensed by the root MIT file.

## Web fonts

The frontend CSS requests DM Sans and Manrope from Google Fonts. Both declare
SIL Open Font License 1.1; their upstream [DM Sans](licenses/DM-Sans-OFL.txt) and
[Manrope](licenses/Manrope-OFL.txt) license files are included. Font binaries are
served externally rather than bundled; the interface has local fallback fonts.
See the upstream [DM Sans](https://github.com/google/fonts/tree/main/ofl/dmsans)
and [Manrope](https://github.com/google/fonts/tree/main/ofl/manrope) directories.
These external requests also mean loading the interface can contact Google Fonts.
