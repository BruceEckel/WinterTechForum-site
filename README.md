# Winter Tech Forum web site

The source of [WinterTechForum.com](https://www.wintertechforum.com), generated from Markdown by one Python script.

## Edit

- Each page is `content/<name>.md`, with a `title` and a `weight` in its front matter.
  The file name is the page's address: `content/schedule.md` becomes `/schedule/`.
  `weight` sets the order of the Previous and Next links.
  A page with `type: index` also appears on the home page.
- The dates, price, and navigation menu are in `site.toml`.
- Write a link to another page from the site root: `[Schedule](/schedule)`.
  The build stops with an error if a link matches no page.

## Build

Install [uv](https://docs.astral.sh/uv/), then:

```
uv run build.py --serve    # Preview at http://localhost:8000, rebuilds when a file changes
uv run build.py            # Build into dist/
uv run pytest              # Check the build
```

## Deploy

Netlify builds and publishes the site on every push to `main`, using the command in `netlify.toml`.
A GitHub Actions workflow runs the tests on the same push.

## Layout

| Path | Contents |
|---|---|
| `build.py` | The generator |
| `site.toml` | Settings and navigation |
| `content/` | The pages, in Markdown, one file each |
| `tools/` | A script that copies the welcome letter to the clipboard as HTML for email |
| `templates/` | Jinja2 page templates |
| `static/` | CSS, JavaScript, and images, copied as they are |

## Domain

The Netlify site `wintertechforum-site` serves `www.wintertechforum.com`, and Netlify DNS holds the domain's records.
`netlify.toml` redirects the site's `netlify.app` address to the custom domain.
Setting `preview = true` in `site.toml` adds a `noindex` tag to every page, for a trial copy that search engines should skip.
