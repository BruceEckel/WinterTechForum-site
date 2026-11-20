# Winter Tech Forum web site

A redesign of [WinterTechForum.com](https://www.wintertechforum.com), generated from Markdown by one Python script.
Trial site: <https://wintertechforum-site.netlify.app/>

## Edit

- Each page is `content/<name>/index.md`, with a `title` and a `weight` in its front matter.
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
| `content/` | The pages, in Markdown |
| `templates/` | Jinja2 page templates |
| `static/` | CSS, JavaScript, and images, copied as they are |

## Moving to the custom domain

The trial site carries a `noindex` tag. To go live:

1. Set `preview = false` in `site.toml` and push.
2. In Netlify, move the `www.wintertechforum.com` domain from the old site to this one.
