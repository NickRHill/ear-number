"""Build the web page in every language from web-src/page.html and web-src/i18n/<code>.json.

Writes web/index.html (English, the canonical page) and web/<code>/index.html for each other
language. The generated pages are committed, so publishing needs no build step;
`--check` fails if any page differs from what the sources would produce (run by the tests).

Template placeholders:
  {{key}}          page string, HTML-escaped (keys ending in _html are inserted as written,
                   after checking they use only <strong>, <em>, <code> and <a href>)
  {{meta:key}}     value from the language's "meta" block
  {{build:name}}   generated here: root, canonical, alternates, langnav, js_strings,
                   translation_note

Every language file must have exactly the keys of en.json. Standard library only.
Usage: python3 build/build_web.py [--check]
"""
import argparse
import html
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(ROOT, "web-src")
OUT = os.path.join(ROOT, "web")
SITE = "https://nickrhill.github.io/ear-number/"
# Order of the language menu: English first, then by number of speakers.
ORDER = ["en", "zh-hans", "hi", "es", "ar", "fr", "bn", "pt", "ru", "id", "ur", "ja", "tr"]
ALLOWED_TAGS = re.compile(r"</?(strong|em|code)>|<a href=\"https://[^\"<>]+\">|</a>")


def load_languages():
    langs = {}
    for name in os.listdir(os.path.join(SRC, "i18n")):
        if name.endswith(".json"):
            with open(os.path.join(SRC, "i18n", name), encoding="utf-8") as f:
                d = json.load(f)
            langs[d["meta"]["code"]] = d
    missing = [c for c in ORDER if c not in langs]
    extra = [c for c in langs if c not in ORDER]
    if missing or extra:
        sys.exit(f"language files and ORDER differ: missing {missing}, not in ORDER {extra}")
    return langs


def check_keys(langs):
    en = langs["en"]
    problems = []
    for code, d in langs.items():
        for part in ("meta", "page", "js"):
            want, got = set(en[part]), set(d.get(part, {}))
            if want != got:
                problems.append(f"{code}.{part}: missing {sorted(want - got)}, extra {sorted(got - want)}")
        for k, v in d.get("page", {}).items():
            if k.endswith("_html") and re.sub(ALLOWED_TAGS, "", v).count("<"):
                problems.append(f"{code}.page.{k}: markup other than strong, em, code, a href")
        for k, v in d.get("js", {}).items():
            want_vars = set(re.findall(r"\{(\w+)\}", en["js"][k])) if k in en["js"] else set()
            if set(re.findall(r"\{(\w+)\}", v)) != want_vars:
                problems.append(f"{code}.js.{k}: placeholders must be {sorted(want_vars)}")
    if problems:
        sys.exit("phrase files are not consistent:\n  " + "\n  ".join(problems))


def url_of(code):
    return SITE if code == "en" else f"{SITE}{code}/"


def langnav(code, langs):
    root = "" if code == "en" else "../"
    opts = []
    for c in ORDER:
        href = root if c == "en" else f"{root}{c}/"
        sel = " selected" if c == code else ""
        m = langs[c]["meta"]
        opts.append(f'          <option value="{href or "./"}" lang="{m["html_lang"]}"{sel}>'
                    f'{html.escape(m["native_name"])}</option>')
    label = html.escape(langs[code]["page"]["language"])
    en_link = "" if code == "en" else (
        '        <a class="lang-en" href="../" hreflang="en" lang="en" title="English">EN</a>\n')
    return (en_link +
            f'        <label class="lang-pick"><span class="visually-hidden">{label}</span>\n'
            f'        <select id="lang" aria-label="{label}">\n' + "\n".join(opts) +
            "\n        </select></label>")


def alternates(langs):
    lines = [f'<link rel="alternate" hreflang="{langs[c]["meta"]["html_lang"]}" href="{url_of(c)}">'
             for c in ORDER]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}">')
    return "\n".join(lines)


def render(code, langs, template):
    d = langs[code]
    js = json.dumps(d["js"], ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    note = d["page"]["translation_note"]
    build = {
        "root": "" if code == "en" else "../",
        "canonical": url_of(code),
        "alternates": alternates(langs),
        "langnav": langnav(code, langs),
        "js_strings": js,
        "translation_note": f'    <p class="translation-note">{html.escape(note)}</p>' if note else "",
    }

    def sub(m):
        key = m.group(1)
        if key.startswith("build:"):
            return build[key[6:]]
        if key.startswith("meta:"):
            return html.escape(str(d["meta"][key[5:]]))
        value = d["page"][key]
        return value if key.endswith("_html") else html.escape(value, quote=True)

    out = re.sub(r"\{\{([a-z_:0-9]+)\}\}", sub, template)
    left = re.findall(r"\{\{[^}]*\}\}", out)
    if left:
        sys.exit(f"{code}: unreplaced placeholders {left}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="fail if a generated page is out of date")
    a = ap.parse_args()
    langs = load_languages()
    check_keys(langs)
    with open(os.path.join(SRC, "page.html"), encoding="utf-8") as f:
        template = f.read()
    stale = []
    for code in ORDER:
        path = os.path.join(OUT, "index.html") if code == "en" else os.path.join(OUT, code, "index.html")
        page = render(code, langs, template)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old == page:
            continue
        if a.check:
            stale.append(os.path.relpath(path, ROOT))
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
            print("wrote", os.path.relpath(path, ROOT))
    if stale:
        sys.exit("out of date (run python3 build/build_web.py): " + ", ".join(stale))
    if a.check:
        print(f"all {len(ORDER)} pages up to date")


if __name__ == "__main__":
    main()
