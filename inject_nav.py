#!/usr/bin/env python3
"""
inject_nav.py  —  !bang!path! site patcher
============================================
What this does:
  1. Creates ./patched/ with updated copies of every HTML file
  2. Adds  <link rel="stylesheet" href="bangpath-nav.css">  to every <head>
  3. Injects the sticky nav HTML after every <body> tag
  4. Marks the correct nav link as active for each page
  5. Normalizes container max-widths to 960px
  6. For index.html and bangpath_setlist.html (which already have nav CSS inline):
     strips the inline nav CSS so it doesn't duplicate bangpath-nav.css

Run from inside your bangpath project folder (where all the .html files live):
    python3 inject_nav.py

Then review ./patched/, and when happy:
    cp patched/*.html .
    cp patched/bangpath-nav.css .
"""

import os, re, shutil

PROJECT_DIR = "."
OUTPUT_DIR  = "patched"

# These already have nav HTML — patch differently (strip inline CSS, add link tag)
ALREADY_HAVE_NAV = {"index.html", "bangpath_setlist.html"}

# Max-widths to normalize → 960px
WIDTHS_TO_NORMALIZE = ["1100px", "1000px"]

# ── <link> tag ───────────────────────────────────────────────────────────────
LINK_TAG = '  <link rel="stylesheet" href="bangpath-nav.css">\n'

# ── Nav HTML template ─────────────────────────────────────────────────────────
# Keys like {a_shout} resolve to "" or " active" depending on the current file
NAV_TEMPLATE = """\n<!-- ===== SITE NAV ===== -->
<nav class="site-nav">
  <div class="site-nav-inner">
    <a class="nav-home" href="index.html">!BANG!PATH!</a>
    <a class="nav-link{a_setlist}" href="bangpath_setlist.html">SETLIST</a>
    <div class="nav-sep"></div>
    <a class="nav-link phase{a_ph1}" href="bangpath-phase1.html">PH 01</a>
    <a class="nav-link phase{a_ph2}" href="bangpath_phase2.html">PH 02</a>
    <a class="nav-link phase{a_ph3}" href="bangpath_phase3.html">PH 03</a>
    <a class="nav-link phase{a_ph4}" href="bangpath_phase4.html">PH 04</a>
    <div class="nav-sep"></div>
    <a class="nav-link{a_corrosion}" href="bangpath_chart_this-corrosion.html">THIS CORROSION</a>
    <a class="nav-link{a_bigcountry}" href="bangpath_chart_in-a-big-country.html">BIG COUNTRY</a>
    <a class="nav-link{a_truefaith}" href="bangpath_chart_true-faith.html">TRUE FAITH</a>
    <a class="nav-link{a_taintedlove}" href="bangpath_chart_tainted-love.html">TAINTED LOVE</a>
    <a class="nav-link{a_groove}" href="bangpath_into_the_groove.html">INTO THE GROOVE</a>
    <a class="nav-link{a_strangelove}" href="bangpath_strangelove.html">STRANGELOVE</a>
    <a class="nav-link{a_milkyway}" href="bangpath_chart_under-the-milky-way.html">MILKY WAY</a>
    <a class="nav-link{a_lastnight}" href="bangpath_chart_last-night-i-dreamt.html">LAST NIGHT</a>
    <a class="nav-link{a_onlyyou}" href="bangpath_chart_only-you.html">ONLY YOU</a>
    <a class="nav-link{a_sunday}" href="bangpath_chart_everyday-is-like-sunday.html">SUNDAY</a>
    <a class="nav-link{a_shout}" href="bangpath_chart_shout.html">SHOUT</a>
    <a class="nav-link{a_wholemoon}" href="bangpath_chart_whole-of-the-moon.html">WHOLE MOON</a>
    <a class="nav-link{a_baby}" href="bangpath_baby_got_back.html">BABY GOT BACK</a>
    <a class="nav-link{a_suburbia}" href="bangpath_chart_suburbia.html">SUBURBIA</a>
    <a class="nav-link{a_broken}" href="bangpath_broken_wings.html">BROKEN WINGS</a>
    <a class="nav-link{a_illthere}" href="bangpath_ill_be_there_for_you.html">I'LL BE THERE</a>
  </div>
</nav>
<!-- ===== END SITE NAV ===== -->\n"""

ALL_KEYS = [
    "a_setlist","a_ph1","a_ph2","a_ph3","a_ph4",
    "a_corrosion","a_bigcountry","a_truefaith","a_taintedlove",
    "a_groove","a_strangelove","a_milkyway","a_lastnight",
    "a_onlyyou","a_sunday","a_shout","a_wholemoon",
    "a_baby","a_suburbia","a_broken","a_illthere",
]

# Which template key to mark active for each file (None = only home is active)
ACTIVE_KEY_MAP = {
    "index.html":                                  None,
    "bangpath_setlist.html":                       "a_setlist",
    "bangpath-phase1.html":                        "a_ph1",
    "bangpath_phase2.html":                        "a_ph2",
    "bangpath_phase3.html":                        "a_ph3",
    "bangpath_phase4.html":                        "a_ph4",
    "bangpath_chart_this-corrosion.html":          "a_corrosion",
    "bangpath_chart_in-a-big-country.html":        "a_bigcountry",
    "bangpath_chart_true-faith.html":              "a_truefaith",
    "bangpath_chart_tainted-love.html":            "a_taintedlove",
    "bangpath_into_the_groove.html":               "a_groove",
    "bangpath_strangelove.html":                   "a_strangelove",
    "bangpath_chart_under-the-milky-way.html":     "a_milkyway",
    "bangpath_chart_last-night-i-dreamt.html":     "a_lastnight",
    "bangpath_chart_only-you.html":                "a_onlyyou",
    "bangpath_chart_everyday-is-like-sunday.html": "a_sunday",
    "bangpath_chart_shout.html":                   "a_shout",
    "bangpath_chart_whole-of-the-moon.html":       "a_wholemoon",
    "bangpath_baby_got_back.html":                 "a_baby",
    "bangpath_chart_suburbia.html":                "a_suburbia",
    "bangpath_broken_wings.html":                  "a_broken",
    "bangpath_ill_be_there_for_you.html":          "a_illthere",
}

# ── Nav CSS selectors whose rule blocks we strip from already-nav files ───────
# Pattern matches:  .selector { ... }  including multi-line blocks
# We only strip the top-level rules — the @media mobile override stays
NAV_SELECTOR_PATTERNS = [
    r"\.site-nav\s*\{[^}]*\}",
    r"\.site-nav-inner\s*\{[^}]*\}",
    r"\.site-nav-inner::-webkit-scrollbar\s*\{[^}]*\}",
    r"\.nav-home\s*\{[^}]*\}",
    r"\.nav-home:hover\s*\{[^}]*\}",
    r"\.nav-link\s*\{[^}]*\}",
    r"\.nav-link:hover\s*\{[^}]*\}",
    r"\.nav-link\.active\s*\{[^}]*\}",
    r"\.nav-link\.phase\s*\{[^}]*\}",
    r"\.nav-link\.phase:hover\s*\{[^}]*\}",
    r"\.nav-sep\s*\{[^}]*\}",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_nav(filename: str) -> str:
    active_key = ACTIVE_KEY_MAP.get(filename)
    values = {k: (" active" if k == active_key else "") for k in ALL_KEYS}
    return NAV_TEMPLATE.format(**values)


def add_link_tag(html: str) -> str:
    if "bangpath-nav.css" in html:
        return html
    return html.replace("</head>", LINK_TAG + "</head>", 1)


def add_nav_html(html: str, filename: str) -> str:
    if 'class="site-nav"' in html:
        return html  # already present
    nav = build_nav(filename)
    return re.sub(
        r"(<body[^>]*>)",
        r"\1" + nav,
        html, count=1, flags=re.IGNORECASE,
    )


def normalize_widths(html: str) -> str:
    for old in WIDTHS_TO_NORMALIZE:
        html = re.sub(
            r"(max-width\s*:\s*)" + re.escape(old),
            r"\g<1>960px",
            html,
        )
    return html


def strip_inline_nav_css(html: str) -> str:
    """Remove nav rule blocks from inline <style> — they're now in bangpath-nav.css."""
    for pat in NAV_SELECTOR_PATTERNS:
        html = re.sub(pat, "", html, flags=re.DOTALL)
    # Clean up any resulting double blank lines inside <style>
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html


# ── Main ──────────────────────────────────────────────────────────────────────

def patch(filename: str, src_path: str) -> str:
    with open(src_path, "r", encoding="utf-8") as f:
        html = f.read()

    if filename in ALREADY_HAVE_NAV:
        # Strip duplicate inline nav CSS, then add the link tag
        html = strip_inline_nav_css(html)
        html = add_link_tag(html)
        html = normalize_widths(html)
    else:
        html = add_link_tag(html)
        html = add_nav_html(html, filename)
        html = normalize_widths(html)

    return html


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # All HTML files in the project directory
    project_files = sorted([
        f for f in os.listdir(PROJECT_DIR)
        if f.endswith(".html") and os.path.isfile(os.path.join(PROJECT_DIR, f))
    ])

    # index.html and bangpath_setlist.html live in /home/claude (our fresh builds)
    # Include them even if not yet in the project folder
    FRESH_BUILDS_DIR = "/home/claude"
    extra = {}
    for fname in ["index.html", "bangpath_setlist.html"]:
        if fname not in project_files:
            candidate = os.path.join(FRESH_BUILDS_DIR, fname)
            if os.path.isfile(candidate):
                extra[fname] = candidate

    total = len(project_files) + len(extra)
    print(f"\n!BANG!PATH! nav injector — processing {total} files → ./{OUTPUT_DIR}/\n")

    ok, err = [], []

    def process(fname, src):
        dest = os.path.join(OUTPUT_DIR, fname)
        try:
            result = patch(fname, src)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(result)
            ok.append(fname)
            tag = "(already had nav — stripped inline CSS)" if fname in ALREADY_HAVE_NAV else ""
            print(f"  ✓  {fname}  {tag}")
        except Exception as e:
            err.append(fname)
            print(f"  ✗  {fname}  ERROR: {e}")

    for fname in project_files:
        process(fname, os.path.join(PROJECT_DIR, fname))

    for fname, src in extra.items():
        process(fname, src)

    # Copy bangpath-nav.css into patched/
    css_src = os.path.join(FRESH_BUILDS_DIR, "bangpath-nav.css")
    if os.path.isfile(css_src):
        shutil.copy2(css_src, os.path.join(OUTPUT_DIR, "bangpath-nav.css"))
        print(f"  →  bangpath-nav.css  (copied)")

    print(f"\n{'='*52}")
    print(f"  {len(ok)} patched   {len(err)} errors")
    print(f"{'='*52}")

    print("""
Verification (run from your project folder after copying):

  # Should return nothing — every file must have the link tag:
  grep -rL 'bangpath-nav.css' patched/*.html

  # Should return nothing — every file must have the nav:
  grep -rL 'site-nav' patched/*.html

  # Should return nothing — no leftover wide containers:
  grep -rn 'max-width: 1100px\\|max-width: 1000px' patched/*.html

When you're satisfied:
  cp patched/*.html .
  cp patched/bangpath-nav.css .
  git add .
  git commit -m "add site-wide nav bar and normalize max-widths"
  git push
""")


if __name__ == "__main__":
    main()
