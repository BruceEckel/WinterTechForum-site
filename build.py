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
from typing import NoReturn

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
DESCRIPTION_LIMIT = 155  # Search results show about this many characters
PAGE_SETTINGS = ("title", "weight", "type", "description")  # What a page's front matter can hold
SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
SITE_VALUE = re.compile(r"\{\{\s*site\.(\w+)\s*\}\}")


@dataclass
class Page:
    slug: str
    title: str
    html: str
    description: str = ""
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


def stop(source: Path, problem: str) -> NoReturn:
    """End the build with a message that states the page and what is wrong."""
    sys.exit(f"content/{source.name}: {problem}")


def plain(inline) -> str:
    """The words of a heading or paragraph, with the Markdown marks removed."""
    parts = []
    for child in inline.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return " ".join("".join(parts).split())


def summary(tokens) -> str:
    """The opening words of a page, for its description in search results."""
    words = ""
    for before, token in zip(tokens, tokens[1:]):
        if before.type == "paragraph_open" and token.type == "inline":
            words = f"{words} {plain(token)}".strip()
            if len(words) >= DESCRIPTION_LIMIT // 2:
                break
    if len(words) <= DESCRIPTION_LIMIT:
        return words
    return words[:DESCRIPTION_LIMIT].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def front_matter(source: Path) -> tuple[dict, str]:
    """Split a page into its settings and its Markdown, checking the settings."""
    if not SLUG.fullmatch(source.stem):
        stop(
            source,
            "rename the file using lowercase letters, digits, and hyphens. "
            "The file name becomes the page's address.",
        )
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        stop(
            source,
            "the file must start with its settings: a line of ---, "
            "then title: and any other settings, then another line of ---",
        )
    closing = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if closing is None:
        stop(source, "the settings at the top have no closing line of ---")
    try:
        meta = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        where = f"line {mark.line + 2}" if mark else "the settings at the top"
        stop(
            source,
            f"{where} is not a valid setting ({getattr(error, 'problem', error)}). "
            'A value that contains a colon needs quotes, as in title: "Wednesday: Hackathon"',
        )
    if not isinstance(meta, dict) or meta.get("title") is None:
        stop(source, "the settings at the top need a title: line")
    unknown = sorted(str(name) for name in set(meta) - set(PAGE_SETTINGS))
    if unknown:
        stop(source, f"unknown setting {', '.join(unknown)}. The settings are {', '.join(PAGE_SETTINGS)}")
    weight = meta.get("weight")
    if weight is not None and (isinstance(weight, bool) or not isinstance(weight, int)):
        stop(source, "weight must be a whole number, as in weight: 40")
    if meta.get("type") not in (None, "index"):
        stop(source, "type can be index, which puts the page on the home page, or be left out")
    return meta, "\n".join(lines[closing + 1 :])


def load_page(source: Path, md: MarkdownIt, site: dict) -> Page:
    meta, body = front_matter(source)

    def site_value(match: re.Match) -> str:
        name = match.group(1)
        if isinstance(site.get(name), (str, int, float)):
            return str(site[name])
        stop(source, f"{match.group(0)} matches no setting in site.toml")

    tokens = md.parse(SITE_VALUE.sub(site_value, body))
    toc = [
        (str(token.attrGet("id")), plain(tokens[i + 1]))
        for i, token in enumerate(tokens)
        if token.type == "heading_open" and token.tag == "h2"
    ]
    return Page(
        slug=source.stem,
        title=str(meta["title"]),
        html=md.renderer.render(tokens, md.options, {}),
        description=" ".join(str(meta.get("description") or summary(tokens)).split()),
        weight=meta.get("weight"),
        on_home=meta.get("type") == "index",
        toc=toc if len(toc) >= TOC_MINIMUM else [],
    )


def load_pages(site: dict) -> list[Page]:
    md = markdown()
    pages = [load_page(p, md, site) for p in sorted(CONTENT.glob("*.md"))]
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
    pages = load_pages(site)
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
        write(
            f"{page.slug}/index.html",
            "page.html",
            page=page,
            current=page.url,
            description=page.description,
        )

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
    # A trial copy asks search engines to stay away; the live site points
    # them to the sitemap.
    rules = "Disallow: /\n" if site.get("preview") else f"Allow: /\n\nSitemap: {root}/sitemap.xml\n"
    (out / "robots.txt").write_text(f"User-agent: *\n{rules}", encoding="utf-8", newline="\n")
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
