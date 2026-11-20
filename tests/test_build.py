import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

BASE = "/WinterTechForum-site"


@pytest.fixture(scope="module")
def dist(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("site") / "dist"
    build.build(out, base=BASE)
    return out


def pages(dist: Path) -> list[Path]:
    return sorted(dist.rglob("*.html"))


def test_every_content_page_is_built(dist):
    sources = list(build.CONTENT.glob("*/index.md"))
    assert len(sources) == 19
    for source in sources:
        assert (dist / source.parent.name / "index.html").is_file()
    assert (dist / "index.html").is_file()
    assert (dist / "404.html").is_file()


def test_no_hugo_shortcode_survives(dist):
    for page in pages(dist):
        assert "{{<" not in page.read_text(encoding="utf-8"), page


def test_internal_links_carry_the_base_and_resolve(dist):
    for page in pages(dist):
        html = page.read_text(encoding="utf-8")
        for target in re.findall(r'(?:href|src)="(/[^"]*)"', html):
            assert target.startswith(BASE + "/"), (page, target)
            path = target.removeprefix(BASE).split("#")[0]
            found = dist / path.lstrip("/")
            assert found.is_file() or (found / "index.html").is_file(), (page, target)


def test_home_page_shows_the_index_pages_and_the_dates(dist):
    html = (dist / "index.html").read_text(encoding="utf-8")
    assert "March 2-6 2026" in html
    assert html.index(">Overview</h2>") < html.index("Welcome to the Winter Tech Forum!</h2>")


def test_only_markdown_pages_are_published(dist):
    assert not (dist / "welcome-letter" / "convert_to_html.py").exists()
