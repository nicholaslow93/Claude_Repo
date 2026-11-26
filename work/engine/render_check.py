#!/usr/bin/env python3
"""A4 fit check for the one-pagers: renders with local IBM Plex fonts, checks the footer
bottom is <= 1111 px and nothing spills out of the 794x1123 page, and saves a PNG.

Usage: python3 render_check.py page.html [more.html ...]   (fonts: PLEX_DIR env or /tmp/ibm-plex-*)
"""
import sys, os, glob, re, asyncio
from playwright.async_api import async_playwright

FACES = [("IBM Plex Sans", "IBMPlexSans", [("Regular", 400), ("Medium", 500), ("SemiBold", 600)]),
         ("IBM Plex Serif", "IBMPlexSerif", [("Medium", 500), ("SemiBold", 600)])]


def font_css():
    css = []
    for fam, stem, ws in FACES:
        for name, w in ws:
            hits = glob.glob(f"{os.environ.get('PLEX_DIR', '/tmp')}/**/complete/woff2/{stem}-{name}.woff2", recursive=True)
            if not hits:
                sys.exit(f"font missing: {stem}-{name}")
            css.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('file://{hits[0]}') format('woff2')}}")
    return "".join(css)


async def check(page, path):
    html = open(path).read()
    html = re.sub(r'<script src="./support.js"></script>', "", html)
    html = re.sub(r"<link[^>]+fonts.googleapis[^>]+>", "", html)
    html = html.replace("<style>", f"<style>{font_css()}", 1)
    tmp = path + ".render.html"
    open(tmp, "w").write(html)
    await page.goto("file://" + os.path.abspath(tmp))
    await page.evaluate("document.fonts.ready")
    r = await page.evaluate("""() => {
      const pg = [...document.querySelectorAll('div')].find(d => d.style.width === '794px' && d.style.height === '1123px');
      const kids = [...pg.children];
      const foot = kids[kids.length - 1].getBoundingClientRect();
      const top = pg.getBoundingClientRect().top;
      let over = 0; for (const k of kids) { over = Math.max(over, k.getBoundingClientRect().bottom - top); }
      const clipped = [...pg.querySelectorAll('div')].filter(d => d.scrollWidth > d.clientWidth + 1 && getComputedStyle(d).whiteSpace !== 'nowrap' && d.children.length === 0).map(d => d.textContent.slice(0, 40));
      return {footer_bottom: Math.round(foot.bottom - top), content_bottom: Math.round(over), scroll: pg.scrollHeight, clipped: clipped.slice(0, 5),
              fonts: [...document.fonts].filter(f => f.status === 'loaded').length};
    }""")
    await page.screenshot(path=path.replace(".html", ".png"), clip={"x": 0, "y": 0, "width": 794, "height": 1123})
    os.remove(tmp)
    ok = r["footer_bottom"] <= 1111 and r["scroll"] <= 1123 and not r["clipped"]
    print(f"{'OK  ' if ok else 'FAIL'} {os.path.basename(path)}: footer bottom {r['footer_bottom']}px (limit 1111), page scroll {r['scroll']}px, fonts loaded {r['fonts']}"
          + (f", text overflowing: {r['clipped']}" if r["clipped"] else ""))
    return ok


def browser_path():
    """$CHROME_PATH if set, else the first browser found (Cowork: google-chrome;
    Claude Code cloud: /opt/pw-browsers/chromium). None = Playwright's own."""
    for p in (os.environ.get("CHROME_PATH"), "/usr/bin/google-chrome", "/opt/pw-browsers/chromium"):
        if p and os.path.exists(p):
            return p
    return None


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=browser_path(), args=["--allow-file-access-from-files"])
        page = await b.new_page(viewport={"width": 794, "height": 1123})
        res = [await check(page, f) for f in sys.argv[1:]]
        await b.close()
    sys.exit(0 if all(res) else 1)


asyncio.run(main())
