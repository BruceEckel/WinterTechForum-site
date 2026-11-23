# Winter Tech Forum web site

The source of [WinterTechForum.com](https://www.wintertechforum.com), generated from Markdown by one Python script.

## Edit

- Each page is `content/<name>.md`.
  The file name is the page's address: `content/schedule.md` becomes `/schedule/`.
  Use lowercase letters, digits, and hyphens in the name.
- A page starts with its settings between two lines of `---`:

  | Setting | Meaning |
  |---|---|
  | `title` | The page's heading. Required. Put it in quotes if it contains a colon. |
  | `description` | One or two sentences for search results. Without it, the page's opening words serve. |
  | `weight` | A whole number that sets the page's place in the Previous and Next links. A page without one stays out of that chain. |
  | `type: index` | Shows the page on the home page as well. |

- The dates, price, and navigation menu are in `site.toml`.
  A page shows a value from that file where its text has the setting's name in double braces: `{{ site.price }}`.
- Write a link to another page from the site root: `[Schedule](/schedule)`.
- The build stops with a message that states the file and the problem
  when a page has a mistake in its settings or a link that matches no page.

## Build

Install [uv](https://docs.astral.sh/uv/), then:

```
uv run build.py --serve    # Preview at http://localhost:8000, rebuilds when a file changes
uv run build.py            # Build into dist/
uv run pytest              # Check the build
```

## Deploy

Netlify builds and publishes the site on every push to `main`, using the command in `netlify.toml`.
That command runs the tests first, so a failing test stops the deploy and the previous version stays up.
A GitHub Actions workflow runs the tests on the same push.

## Checks

- **Links to other sites.**
  `uv run tools/check_links.py` requests every link that leaves the site.
  It reports a broken link and a link that now leads to a different site.
  A GitHub Actions workflow runs it each Monday and opens an issue when it finds one.
  Many sites refuse a request from a program; the report lists those under "Could not check", and a person has to open them.

## Images

The artwork is in `art/`, which the site does not publish.
`uv run tools/make_images.py` makes the copies the pages use, in `static/images/`:
the banner, the logo in the menu bar, and the picture a shared link shows.
Run it after replacing a file in `art/`.

## Each year

These are the places that hold a fact about one year's conference.

1. `site.toml`: `dates`, `price`, `welcome_dinner`, and `saturday_breakfast`.
2. `content/registration.md`: the payment link.
   Open it and confirm that the checkout shows this year's dates and price.
3. The Slack invite in `content/registration.md`, `content/lodging.md`, and `content/welcome-letter.md`.
   Open it and confirm that it still offers to join.
4. `content/conference-theme.md`: the theme.
5. `content/welcome-letter.md`: the number of years in "for 25 years".
6. `content/travel.md`: the bus times, gate, and fare; the train fare and timetable; the flights.
   The bus and train operators change these during the year, so check them again a month before the conference.
7. `content/health.md`: the clinic's hours. `content/lodging.md`: the phone number and the lodgings it describes.
8. `content/schedule.md` and `content/cta.md`: the session times, the banquet's location, and the rooms booked at the Center for the Arts.
9. Run `uv run tools/check_links.py`.

## Layout

| Path | Contents |
|---|---|
| `build.py` | The generator |
| `site.toml` | Settings and navigation |
| `content/` | The pages, in Markdown, one file each |
| `templates/` | Jinja2 page templates |
| `static/` | CSS, JavaScript, and images, copied as they are |
| `art/` | The original artwork |
| `tools/` | Scripts for the link check, the images, and the welcome email |
| `tests/` | Checks on the built site |

## Domain

The Netlify site `wintertechforum-site` serves `www.wintertechforum.com`, and Netlify DNS holds the domain's records.
`netlify.toml` redirects the site's `netlify.app` address to the custom domain.
Setting `preview = true` in `site.toml` adds a `noindex` tag to every page, for a trial copy that search engines should skip.
