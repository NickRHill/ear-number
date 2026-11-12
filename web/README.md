# Ear Number web page

A static page, in thirteen languages, that explains Ear Number, draws the two
audiograms a pair decodes to, and re-encodes as the visitor drags points or
enters a hearing test. Everything runs in the browser; links carry the pair
after the `#`.

## Files

This folder is what GitHub Pages publishes; the pages in it are generated.

| File | What |
|---|---|
| `index.html` | English, the canonical page (generated) |
| `<code>/index.html` | one page per language: `zh-hans`, `hi`, `es`, `ar`, `fr`, `bn`, `pt`, `ru`, `id`, `ur`, `ja`, `tr` (generated) |
| `style.css` | styles for every language, right-to-left included |
| `app.js` | charts, dragging, entry grid, links, sharing, language menu |
| `earnumber.js` | JavaScript port of `../earnumber.py` (no dependencies; browser and Node) |
| `earnumber-v1.json` | byte-identical copy of `../earnumber-v1.json`; CI fails if they differ |

## Editing text

Never edit the generated pages; change the sources and rebuild.

- `../web-src/page.html` is the template; `../web-src/i18n/<code>.json` holds
  each language's text (`page` for the HTML, `js` for messages the script
  shows). Every language file must have exactly the keys of `en.json`.
- `python3 build/build_web.py` (from the repository root) writes the pages;
  `--check` fails if any is out of date, and the unit tests run it.
- Translations other than English are machine translations marked
  `"reviewed": false`; each page says so in its footer. When a native
  speaker has checked one, set `reviewed` to true and change its
  `translation_note` to say how it was checked (or empty it after a
  specialist review). Urdu: read through by a native speaker, 2026-11-12.

## Preview and tests

Preview from the repository root with `python3 -m http.server 8000 -d web`, then
open http://localhost:8000/ (or `/es/`, `/ar/` and so on). Use `localhost`, not
a LAN address: the table's SHA-256 check needs a secure context.

Conformance of the port: `node --test tests/js/*.test.mjs` from the repository
root. `.github/workflows/pages.yml` publishes this folder only.
