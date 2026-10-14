#!/usr/bin/env python3
"""Fetch configured RSS/Atom feeds and create combined, deduplicated RSS files."""
import hashlib, html, json, re, time
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from urllib.request import Request, urlopen
from io import BytesIO
import feedparser
from PIL import Image, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "feeds.json"
OUT = ROOT / "feeds"
MAX_PER_SOURCE = 100
USER_AGENT = "DailyPulse/1.0 (+RSS reader; respectful polling)"
IMAGE_TIMEOUT = 8
MIN_IMAGE_WIDTH = 400
MIN_IMAGE_HEIGHT = 225
# Laplacian-variance blur heuristic. This is an image-quality check, not an AI vision model.
MIN_SHARPNESS = 55.0
IMAGE_CHECK_CACHE = {}
CATEGORIES = {"top", "nigeria", "world", "entertainment", "sports", "technology", "science", "business", "gaming", "fashion", "other"}

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def canonical_url(url):
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.netloc:
            return ""
        query = [(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}]
        return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", urlencode(query), ""))
    except Exception:
        return ""

def text_html(value):
    # Escape untrusted source content so it remains text inside the generated XML.
    return html.escape(clean(value), quote=False)

def entry_images(entry):
    """Return candidate article image URLs, preferring larger RSS-provided images."""
    candidates = []
    seen = set()
    for key in ("media_content", "media_thumbnail"):
        for item in entry.get(key, []) or []:
            url = item.get("url")
            if url and str(url).startswith(("https://", "http://")) and url not in seen:
                try:
                    width = int(item.get("width") or 0)
                    height = int(item.get("height") or 0)
                except (TypeError, ValueError):
                    width, height = 0, 0
                candidates.append((width * height, url))
                seen.add(url)
    for item in entry.get("links", []) or []:
        url = item.get("href", "")
        if item.get("rel") == "enclosure" and str(item.get("type", "")).startswith("image/") and url not in seen:
            candidates.append((0, url)); seen.add(url)
    for key in ("summary", "description", "content"):
        val = entry.get(key, "")
        if isinstance(val, list):
            val = " ".join(str(x.get("value", "")) for x in val)
        for match in re.finditer(r'<img\b[^>]*?src=["\']([^"\']+)', str(val), re.I):
            url = html.unescape(match.group(1))
            if url.startswith(("https://", "http://")) and url not in seen:
                candidates.append((0, url)); seen.add(url)
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [url for _, url in candidates]

def image_is_usable(url):
    """Reject missing, inaccessible, tiny, or visibly soft images before publishing."""
    if not url or not str(url).startswith(("https://", "http://")):
        return False
    if url in IMAGE_CHECK_CACHE:
        return IMAGE_CHECK_CACHE[url]
    usable = False
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=IMAGE_TIMEOUT) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if not content_type.startswith("image/"):
                IMAGE_CHECK_CACHE[url] = False
                return False
            data = response.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            IMAGE_CHECK_CACHE[url] = False
            return False
        with Image.open(BytesIO(data)) as original:
            original.verify()
        with Image.open(BytesIO(data)) as original:
            if original.width < MIN_IMAGE_WIDTH or original.height < MIN_IMAGE_HEIGHT:
                IMAGE_CHECK_CACHE[url] = False
                return False
            gray = original.convert("L")
            gray.thumbnail((320, 180))
            # Edge energy: low variance after a Laplacian filter generally indicates blur.
            edges = gray.filter(ImageFilter.FIND_EDGES)
            sharpness = ImageStat.Stat(edges).var[0]
            usable = sharpness >= MIN_SHARPNESS
    except Exception:
        usable = False
    IMAGE_CHECK_CACHE[url] = usable
    return usable


def entry_description(entry):
    value = entry.get("summary", "") or entry.get("description", "")
    if not value and entry.get("content"):
        value = entry["content"][0].get("value", "")
    value = re.sub(r"<[^>]+>", " ", str(value))
    return clean(html.unescape(value))[:1000]

def entry_date(entry):
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime.fromtimestamp(time.mktime(parsed), timezone.utc)
            except Exception:
                pass
    for key in ("published", "updated", "pubDate"):
        val = entry.get(key)
        if val:
            try:
                dt = parsedate_to_datetime(val)
                return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)

def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    grouped = {c: [] for c in CATEGORIES}
    seen_urls, seen_titles = set(), set()
    enabled = [s for s in config.get("sources", []) if s.get("enabled", True) and s.get("url")]
    ok_sources, failed_sources, total = 0, 0, 0
    for source in enabled:
        name, url = clean(source.get("name")) or "Source", source["url"].strip()
        category = clean(source.get("category", "other")).lower()
        if category not in CATEGORIES or category == "top": category = "other" if category not in CATEGORIES else "world"
        try:
            parsed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENT}, resolve_relative_uris=True)
            if parsed.bozo and not parsed.entries:
                raise ValueError(str(getattr(parsed, "bozo_exception", "invalid feed")))
            if not parsed.entries:
                raise ValueError("feed returned no entries")
            ok_sources += 1
            for entry in parsed.entries[:MAX_PER_SOURCE]:
                link = canonical_url(entry.get("link", ""))
                title = clean(entry.get("title", ""))
                if not link or not title: continue
                # Prefer the highest-resolution RSS image, but try alternatives if the
                # first image is tiny, inaccessible, or blurry. Skip the article only
                # when none of its supplied image candidates passes the quality checks.
                image = next((candidate for candidate in entry_images(entry) if image_is_usable(candidate)), "")
                if not image:
                    continue
                title_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
                if link in seen_urls or (title_key and title_key in seen_titles): continue
                seen_urls.add(link); seen_titles.add(title_key)
                date = entry_date(entry)
                grouped[category].append({"title":title,"link":link,"source":name,"date":date,"description":entry_description(entry),"image":image,"category":category})
                total += 1
        except Exception as exc:
            failed_sources += 1
            print(f"WARN: {name}: {exc}")
    # Sort each category newest first; Top includes all categories and is deduplicated globally.
    all_items = [item for items in grouped.values() for item in items]
    all_items.sort(key=lambda x:x["date"], reverse=True)
    grouped["top"] = all_items
    def make_xml(items, title):
        parts=['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>', f'<title>{text_html(title)}</title>', '<link>https://example.com/</link>', '<description>Aggregated headlines linking to original publishers</description>']
        for x in items[:5000]:
            parts += ['<item>', f'<title>{text_html(x["title"])}</title>', f'<link>{html.escape(x["link"], quote=False)}</link>', f'<guid isPermaLink="false">{hashlib.sha256(x["link"].encode()).hexdigest()}</guid>', f'<source>{text_html(x["source"])}</source>', f'<category>{text_html(x["category"])}</category>', f'<pubDate>{format_datetime(x["date"])}</pubDate>', f'<description>{text_html(x["description"])}</description>']
            if x["image"]:
                img = html.escape(x["image"], quote=True)
                parts += [f'<enclosure url="{img}" type="image/jpeg"/>', f'<media:content url="{img}" medium="image"/>']
            parts += ['</item>']
        parts += ['</channel></rss>']
        return '\n'.join(parts) + '\n'
    for category, items in grouped.items():
        items.sort(key=lambda x:x["date"], reverse=True)
        (OUT/f"{category}.xml").write_text(make_xml(items, f"{category.title()} News"), encoding="utf-8")
    print(f"Collection complete: {ok_sources}/{len(enabled)} sources OK; {failed_sources} failed; {total} unique articles.")
    if not ok_sources:
        raise SystemExit("No configured RSS sources could be read; refusing to publish empty feeds.")

if __name__ == "__main__": main()
