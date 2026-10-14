# News Site V4 — scalable RSS aggregation

This version keeps the static website and GitHub Actions workflow, but replaces the hard-coded list of six feeds with `feeds.json`. The collector creates combined category feeds under `feeds/`.

## How to add sources

1. Open `feeds.json`.
2. Add an entry to `sources` with a readable `name`, the publisher's RSS/Atom `url`, a `category`, and `enabled: true`.
3. Commit and push the change to GitHub.
4. In GitHub, open **Actions → Update news → Run workflow** to test immediately. Otherwise, it runs on the 15-minute schedule.

Example:

```json
{
  "name": "Example Publisher",
  "url": "https://example.com/feed.xml",
  "category": "world",
  "enabled": true
}
```

Supported categories: `nigeria`, `world`, `entertainment`, `sports`, `technology`, `science`, `business`, `gaming`, `fashion`, `other`. The `top` feed is generated automatically from all categories.

## Run locally

Requires Python 3.12+, `feedparser`, and Pillow:

```bash
python -m pip install feedparser Pillow
python scripts/fetch_news.py
```

## Notes and limitations

- There is no fixed source count in the configuration. Practical throughput is limited by GitHub Actions runtime, network access, feed publisher rate limits, and the size of generated files. The collector processes up to 100 recent entries per source per run and outputs up to 5,000 items per generated feed.
- Feeds may be unavailable, invalid, blocked, or temporarily empty. A failed source is logged and does not stop other sources. If every configured source fails, the job fails instead of replacing feeds with empty results.
- Articles are deduplicated by canonical URL and normalized title across sources. This is intentionally conservative and may merge two stories with identical titles.
- DailyPulse only publishes articles whose RSS/Atom entry includes an image URL. Articles without a feed-provided image are skipped by the collector and filtered in the browser, including older generated XML feeds.
- The website links to original articles and displays metadata/short summaries rather than copying full article text. Respect publisher terms, robots policies, copyright, and feed/API terms.
- GitHub Actions schedules are not guaranteed to start at the exact minute. GitHub Pages may also take time to publish a commit.
- Keep the repository public/private as desired, but do not put API keys or secrets in `feeds.json`.


## DailyPulse responsive interface

The homepage now uses the DailyPulse brand and a responsive layout: stacked image-led cards on phones and a two-column article-card grid on desktop/tablet widths. The RSS category filters, refresh button, local generated feeds, original publisher links, and automatic refresh remain in place.


### Image quality filtering

Stories are only published when the RSS item includes an accessible image at least 400×225 pixels. The collector checks image sharpness using a lightweight edge-based heuristic and skips images that appear too blurry, inaccessible, invalid, or too small. This is an automated image-quality heuristic, not an AI vision model; it may occasionally reject a valid image or miss subtle blur.

## Expanded sports and science sources

The feed configuration includes additional sports coverage (BBC Sport, Sky Sports, The Athletic, Bleacher Report, Formula 1, Yahoo Sports) and science/space coverage (Science.org, New Scientist, Phys.org, Quanta Magazine, BBC Science, NYT Science, ESA, NASA, Space.com). The collector continues to publish only entries whose image URL is present and whose image passes its availability, minimum-dimension, and sharpness checks. RSS providers may change feed endpoints or omit images, so the workflow can skip entries even from enabled sources.


## Reduced RSS collection

This configuration uses 20 selected RSS sources instead of 85 and schedules collection hourly (at minute 17). This reduces routine feed requests and workflow runs, but does not guarantee compliance with GitHub's Terms or explain/resolve any account suspension. Review GitHub's notice and contact Support for account-specific decisions.

The collector skips stories without a usable RSS image and applies a basic image-quality heuristic; it is not an AI vision model. RSS endpoints and image availability can change, so check workflow logs after restoring repository access.


## Image quality and source selection

- BBC RSS sources have been removed from this configuration because their thumbnails appeared blurry in the site.
- The collector checks for an image at least 400×225 pixels and applies a sharpness heuristic. Articles with no usable image are skipped.
- If an RSS entry supplies several image candidates, the collector prefers the largest one and tries alternatives when an image fails the checks.
- The sharpness check is a lightweight heuristic, not an AI vision model, so some images may still look soft. Feed endpoints and image quality should be verified in GitHub Actions after upload.
