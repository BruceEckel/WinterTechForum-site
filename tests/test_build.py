import re
import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

BASE = "/WinterTechForum-site"
SITE = tomllib.loads(build.SETTINGS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def dist(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("site") / "dist"
    build.build(out, base=BASE)
    return out


def pages(dist: Path) -> list[Path]:
    return sorted(dist.rglob("*.html"))


def test_every_content_page_is_built(dist):
    sources = list(build.CONTENT.glob("*.md"))
    assert sources
    assert not [p for p in build.CONTENT.iterdir() if p.is_dir()]
    for source in sources:
        assert (dist / source.stem / "index.html").is_file()
    assert (dist / "index.html").is_file()
    assert (dist / "404.html").is_file()


def test_no_template_mark_survives(dist):
    for page in pages(dist):
        html = page.read_text(encoding="utf-8")
        assert "{{" not in html and "{%" not in html, page


def test_internal_links_carry_the_base_and_resolve(dist):
    for page in pages(dist):
        html = page.read_text(encoding="utf-8")
        for target in re.findall(r'(?:href|src)="(/[^"]*)"', html):
            assert target.startswith(BASE + "/"), (page, target)
            path = target.removeprefix(BASE).split("#")[0].split("?")[0]
            found = dist / path.lstrip("/")
            assert found.is_file() or (found / "index.html").is_file(), (page, target)


def test_home_page_shows_the_index_pages_and_the_dates(dist):
    html = (dist / "index.html").read_text(encoding="utf-8")
    assert SITE["dates"] in html
    assert SITE["price"] in html
    assert html.index(">Overview</h2>") < html.index("Welcome to the Winter Tech Forum!</h2>")


def test_a_page_shows_values_from_the_settings(dist):
    html = (dist / "overview" / "index.html").read_text(encoding="utf-8")
    assert SITE["welcome_dinner"] in html
    assert SITE["saturday_breakfast"] in html


def test_only_markdown_pages_are_published(dist):
    assert not list(dist.rglob("*.py"))
    assert not list(dist.rglob("*.md"))


def test_no_published_file_exposes_an_email_address(dist):
    address = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}|mailto:", re.IGNORECASE)
    texts = [p for p in dist.rglob("*") if p.suffix in {".html", ".js", ".css", ".xml", ".txt"}]
    assert len(texts) > 20
    for path in texts:
        assert not address.search(path.read_text(encoding="utf-8")), path
    for slug in ("contact", "registration"):
        html = (dist / slug / "index.html").read_text(encoding="utf-8")
        assert 'class="email-button"' in html


def test_stylesheet_and_script_addresses_carry_a_version(dist):
    html = (dist / "contact" / "index.html").read_text(encoding="utf-8")
    assert re.search(r'/css/site\.css\?v=[0-9a-f]{10}"', html)
    assert re.search(r'/js/site\.js\?v=[0-9a-f]{10}"', html)


def test_each_page_has_its_own_description_and_address(dist):
    seen = {}
    for page in pages(dist):
        if page.name == "404.html":
            continue
        html = page.read_text(encoding="utf-8")
        description = re.search(r'<meta name="description" content="([^"]+)">', html)
        canonical = re.search(r'<link rel="canonical" href="([^"]+)">', html)
        assert description and len(description.group(1)) > 30, page
        assert canonical, page
        where = page.parent.relative_to(dist).as_posix().strip(".")
        assert canonical.group(1).rstrip("/").endswith((BASE + "/" + where).rstrip("/")), page
        assert description.group(1) not in seen, (page, seen.get(description.group(1)))
        seen[description.group(1)] = page
        assert 'property="og:image" content="http' in html


def test_headings_go_down_one_level_at_a_time(dist):
    for page in pages(dist):
        html = page.read_text(encoding="utf-8")
        levels = [int(n) for n in re.findall(r"<h([1-6])[ >]", html)]
        assert levels and levels[0] == 1, page
        for before, after in zip(levels, levels[1:]):
            assert after <= before + 1, (page, before, after)


def test_robots_file_points_to_the_sitemap(dist):
    robots = (dist / "robots.txt").read_text(encoding="utf-8")
    sitemap = re.search(r"^Sitemap: (\S+)$", robots, re.MULTILINE)
    assert sitemap and sitemap.group(1).endswith(BASE + "/sitemap.xml")
    assert (dist / "sitemap.xml").is_file()
    assert (dist / "favicon.ico").is_file()


MISTAKES = {
    "colon-in-title.md": ("---\ntitle: Wednesday: Hackathon day\n---\n\nText.\n", "line 2"),
    "no-closing-line.md": ("---\ntitle: Missing line\nweight: 5\n\nText.\n", "closing line"),
    "no-settings.md": ("Just some text.\n", "must start with its settings"),
    "no-title.md": ("---\nweight: 5\n---\n\nText.\n", "title:"),
    "text-weight.md": ("---\ntitle: Text weight\nweight: last\n---\n\nText.\n", "whole number"),
    "misspelled.md": ("---\ntitle: Misspelled\nwieght: 5\n---\n\nText.\n", "wieght"),
    "wrong-type.md": ("---\ntitle: Wrong type\ntype: home\n---\n\nText.\n", "index"),
    "Spaces In Name.md": ("---\ntitle: Spaces\n---\n\nText.\n", "rename the file"),
    "no-such-value.md": ("---\ntitle: Value\n---\n\nIt is {{ site.nonesuch }}.\n", "site.toml"),
}


@pytest.mark.parametrize("name", MISTAKES)
def test_a_mistake_in_a_page_is_reported_with_its_file(tmp_path, name):
    text, expected = MISTAKES[name]
    source = tmp_path / name
    source.write_text(text, encoding="utf-8")
    with pytest.raises(SystemExit) as stopped:
        build.load_page(source, build.markdown(), SITE)
    message = str(stopped.value)
    assert message.startswith(f"content/{name}: "), message
    assert expected in message, message


def test_a_page_saved_with_windows_marks_still_loads(tmp_path):
    source = tmp_path / "from-notepad.md"
    source.write_bytes("﻿---\r\ntitle: \"From: Notepad\"\r\nweight: 7\r\n---\r\n\r\nPrice {{ site.price }}.\r\n".encode("utf-8"))
    page = build.load_page(source, build.markdown(), SITE)
    assert (page.title, page.weight) == ("From: Notepad", 7)
    assert SITE["price"] in page.html
