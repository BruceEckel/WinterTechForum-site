Run each script from the repository root.

## The welcome letter as email

`uv run tools/convert_to_html.py`

- This converts `content/welcome-letter.md` into html which it places on your clipboard.
- Use [this utility](https://chromewebstore.google.com/detail/insert-and-send-html-with/bcflbfdlpegakpncdgmejelcolhmfkjh) for pasting HTML into Gmail.
- [Instructions for installing uv](https://docs.astral.sh/uv/getting-started/installation/)

## Links to other sites

`uv run tools/check_links.py`

- This requests every link from the site's pages to another site and prints what it finds.

## Images

`uv run tools/make_images.py`

- This makes the banner, the menu-bar logo, and the shared-link picture in `static/images/` from the artwork in `art/`.
