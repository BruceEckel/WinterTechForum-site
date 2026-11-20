"""Build the Winter Tech Forum site from Markdown.

    uv run build.py            Build into dist/
    uv run build.py --serve    Build, serve on localhost, rebuild on change
"""

import argparse
import hashlib
import os
import re
import shutil
import sys
import time
import tomllib
from dataclasses import dataclass, field
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import yaml
from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
SETTINGS = ROOT / "site.toml"
TOC_MINIMUM = 3  # A page shows "On this page" when it has this many H2s


@dataclass
class Page:
    slug: str
    title: str
    html: str
    weight: int | None = None
    on_home: bool = False
    toc: list[tuple[str, str]] = field(default_factory=list)
    previous: "Page | None" = None
    next: "Page | None" = None

    @property
    def url(self) -> str:
        return f"/{self.slug}/"


def markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "typographer": True})
    md.enable(["table", "replacements", "smartquotes"])
    md.use(anchors_plugin, max_level=3)
    return md


def load_page(source: Path, md: MarkdownIt) -> Page:
    text = source.read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    meta = yaml.safe_load(front)
    tokens = md.parse(body)
    toc = [
        (str(token.attrGet("id")), tokens[i + 1].content)
        for i, token in enumerate(tokens)
        if token.type == "heading_open" and token.tag == "h2"
    ]
    return Page(
        slug=source.parent.name,
        title=meta["title"],
        html=md.renderer.render(tokens, md.options, {}),
        weight=meta.get("weight"),
        on_home=meta.get("type") == "index",
        toc=toc if len(toc) >= TOC_MINIMUM else [],
    )


def load_pages() -> list[Page]:
    md = markdown()
    pages = [load_page(p, md) for p in sorted(CONTENT.glob("*/index.md"))]
    ordered = sorted(
        (p for p in pages if p.weight is not None), key=lambda p: p.weight or 0
    )
    for before, after in zip(ordered, ordered[1:]):
        before.next, after.previous = after, before
    unordered = [p for p in pages if p.weight is None]
    return ordered + unordered


LINK = re.compile(r'(href|src)="(/[^"/][^"]*|/)"')


def finish(html: str, base: str, slugs: set[str], where: str) -> str:
    """Check each root-relative link, then put the base path before it."""

    def rewrite(match: re.Match) -> str:
        attribute, target = match.groups()
        path, mark, fragment = target.partition("#")
        path, query_mark, query = path.partition("?")
        first = path.strip("/").split("/")[0]
        if first in slugs and not path.endswith("/"):
            path += "/"
        known = first in slugs or first == "" or (STATIC / path[1:]).is_file()
        if not known:
            sys.exit(f"{where}: broken internal link {target}")
        return f'{attribute}="{base}{path}{query_mark}{query}{mark}{fragment}"'

    return LINK.sub(rewrite, html)


def build(out: Path = ROOT / "dist", base: str | None = None) -> None:
    site = tomllib.loads(SETTINGS.read_text(encoding="utf-8"))
    if base is not None:
        site["base"] = base
    site["origin"] = os.environ.get("URL", site["origin"]).rstrip("/")
    prefix: str = site["base"].rstrip("/")
    # A new address for the stylesheet and script each time one changes, so a
    # browser holding the previous copy fetches the current one.
    assets = b"".join(p.read_bytes() for p in sorted(STATIC.rglob("*.[cj]s*")))
    site["version"] = hashlib.sha256(assets).hexdigest()[:10]
    pages = load_pages()
    slugs = {p.slug for p in pages}
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=False)

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(STATIC, out)

    def write(path: str, template: str, **context) -> None:
        html = env.get_template(template).render(site=site, **context)
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            finish(html, prefix, slugs, path), encoding="utf-8", newline="\n"
        )

    home = [p for p in pages if p.on_home]
    write("index.html", "home.html", sections=home, current="/")
    write("404.html", "404.html", current="")
    for page in pages:
        write(f"{page.slug}/index.html", "page.html", page=page, current=page.url)

    root = site["origin"] + prefix
    locations = [f"{root}/"] + [f"{root}{p.url}" for p in pages]
    entries = "".join(f"  <url><loc>{loc}</loc></url>\n" for loc in locations)
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Built {len(pages)} pages into {out}")


def snapshot() -> dict[Path, float]:
    watched = [SETTINGS, *CONTENT.rglob("*"), *TEMPLATES.rglob("*"), *STATIC.rglob("*")]
    return {p: p.stat().st_mtime for p in watched if p.is_file()}


def serve(port: int) -> None:
    out = ROOT / "dist"
    build(out, base="")
    handler = partial(SimpleHTTPRequestHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    Thread(target=server.serve_forever, daemon=True).start()
    print(f"Serving http://localhost:{port}/  (Ctrl+C to stop)")
    seen = snapshot()
    try:
        while True:
            time.sleep(0.5)
            now = snapshot()
            if now != seen:
                seen = now
                try:
                    build(out, base="")
                except (SystemExit, Exception) as error:
                    print(f"Build failed: {error}")
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the Winter Tech Forum site")
    parser.add_argument("--serve", action="store_true", help="serve and rebuild")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--base", help='base path, such as "" or "/WinterTechForum-site"')
    args = parser.parse_args()
    if args.serve:
        serve(args.port)
    else:
        build(base=args.base)
