"""Check every link from the site's pages to another site.

    uv run tools/check_links.py                    Print a report
    uv run tools/check_links.py --report links.md  Also write the report as Markdown

The build checks the links between the site's own pages. This script builds
the site, collects the links that leave it, and requests each one. It exits
with status 1 when a link is broken or now leads to a different site, which
is what a domain does after someone else buys it.

Many sites refuse a request that comes from a program. The report lists
those under "Could not check", and they do not change the exit status.
"""

import argparse
import html
import re
import socket
import sys
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
TIMEOUT = 25
HREF = re.compile(r'href="(https?://[^"]+)"')

# A link that ends on another site is reported, unless the pair is here:
# (the site in the link, the site that answers).
EXPECTED_MOVES = {
    ("a.co", "amazon.com"),
    ("g.co", "google.com"),
    ("goo.gl", "google.com"),
    ("youtu.be", "youtube.com"),
}

BROKEN, MOVED, UNCHECKED, FINE = "Broken", "Leads to a different site", "Could not check", "Fine"


def site_of(url: str) -> str:
    """The last two labels of the host: www.example.com and example.com match."""
    return ".".join((urlsplit(url).hostname or "").lower().split(".")[-2:])


def collect() -> dict[str, list[str]]:
    """Each outside link, with the pages that hold it."""
    links: dict[str, list[str]] = {}
    own = site_of(build.tomllib.loads(build.SETTINGS.read_text(encoding="utf-8"))["origin"])
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "dist"
        build.build(out, base="")
        for page in sorted(out.rglob("*.html")):
            name = "/" + page.parent.relative_to(out).as_posix().strip(".")
            name = name if name.endswith("/") else name + "/"
            if page.name == "404.html":
                continue
            for link in HREF.findall(page.read_text(encoding="utf-8")):
                link = html.unescape(link)
                if site_of(link) != own and name not in links.setdefault(link, []):
                    links[link].append(name)
    return links


def request(url: str) -> tuple[str, str]:
    """Request one link and say what came back."""
    asked = urllib.request.Request(url.split("#")[0], headers={"User-Agent": AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(asked, timeout=TIMEOUT) as response:
            final = response.geturl()
    except urllib.error.HTTPError as error:
        if error.code in (404, 410):
            return BROKEN, f"the site answers {error.code}"
        return UNCHECKED, f"the site answers {error.code}"
    except urllib.error.URLError as error:
        if isinstance(error.reason, socket.gaierror):
            return BROKEN, "no site exists at that name"
        return UNCHECKED, f"no answer ({error.reason})"
    except (TimeoutError, ConnectionError, OSError) as error:
        return UNCHECKED, f"no answer ({error})"
    before, after = site_of(url), site_of(final)
    if before != after and (before, after) not in EXPECTED_MOVES:
        return MOVED, f"it now opens {final}"
    return FINE, ""


def check(url: str) -> tuple[str, str]:
    kind, detail = request(url)
    if kind == UNCHECKED and "answers" not in detail:
        kind, detail = request(url)  # One more try for a slow or dropped connection
    return kind, detail


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the site's links to other sites")
    parser.add_argument("--report", type=Path, help="write the report to this Markdown file")
    args = parser.parse_args()

    links = collect()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(zip(links, pool.map(check, links)))

    lines = [f"Checked {len(links)} links to other sites."]
    for kind in (BROKEN, MOVED, UNCHECKED):
        found = [(url, detail) for url, (k, detail) in results.items() if k == kind]
        if not found:
            continue
        lines += ["", f"## {kind}", ""]
        for url, detail in sorted(found):
            lines.append(f"- <{url}>: {detail}. On {', '.join(links[url])}")
    failed = any(kind in (BROKEN, MOVED) for kind, _ in results.values())
    if not failed:
        lines += ["", "No link is broken, and none leads to a different site."]
    report = "\n".join(lines) + "\n"
    print(report)
    if args.report:
        args.report.write_text(report, encoding="utf-8", newline="\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
