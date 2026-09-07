"""Bounded news discovery, with independent name queries and explicit coverage."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
from time import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
import re
import unicodedata

import feedparser
import requests

TIMEOUT = (3, 8)
UA = {'User-Agent': 'Radar-Politico/2.1 (public-news-monitor)'}
MAX_NAMES = 6
MAX_BYTES = 2_000_000
CONF_FEED = 'https://confidencialnoticias.com/feed/'
CHIVA_HOME = 'https://www.lachivadeuraba.com/'


@dataclass(frozen=True)
class NewsQuery:
    terms: tuple
    territory: str = 'Colombia'


def normalize(text):
    text = unicodedata.normalize('NFKD', unescape(str(text or ''))).lower()
    return ' '.join(re.findall(r'[a-z0-9]+', ''.join(c for c in text if not unicodedata.combining(c))))


def matches(text, terms):
    text = ' ' + normalize(text) + ' '
    return any(' ' + normalize(term) + ' ' in text for term in terms if normalize(term))


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def publication_date(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError):
        try:
            parsed = parsedate_to_datetime(value)
        except (ValueError, TypeError, IndexError):
            return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def safe_url(value):
    try:
        parsed = urlsplit(value or '')
        return value if parsed.scheme in ('https', 'http') and parsed.hostname and not parsed.username and not parsed.password else None
    except ValueError:
        return None


def url_key(value):
    parsed = urlsplit(value)
    tracking = {'fbclid', 'gclid', 'oc', 'hl', 'gl', 'ceid'}
    query = [(k, v) for k, v in parse_qsl(parsed.query) if not k.lower().startswith('utm_') and k.lower() not in tracking]
    return urlunsplit(('', parsed.netloc.lower().removeprefix('www.'), parsed.path.rstrip('/'), urlencode(sorted(query)), ''))


def get_bytes(url, **kwargs):
    response = requests.get(url, timeout=TIMEOUT, headers=UA, **kwargs)
    response.raise_for_status()
    if len(response.content) > MAX_BYTES:
        raise ValueError('Source response exceeds the retrieval limit')
    return response.content


@lru_cache(maxsize=16)
def cached_source(url, bucket):
    # The fixed publisher URLs and same-host article links never come from user URLs.
    return get_bytes(url)


def source_bytes(url):
    return cached_source(url, int(time() // 300))


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.meta, self.links, self.article_text = {}, [], []
        self.anchor, self.article_depth, self.skip = None, 0, 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('property', attrs.get('name', ''))] = attrs.get('content', '')
        if tag == 'a' and attrs.get('href'):
            self.anchor = [attrs['href'], '']
        if tag == 'article':
            self.article_depth += 1
        if tag in ('script', 'style'):
            self.skip += 1

    def handle_data(self, text):
        if self.skip:
            return
        if self.anchor is not None:
            self.anchor[1] += ' ' + text
        if self.article_depth:
            self.article_text.append(text)

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor is not None:
            self.links.append(self.anchor)
            self.anchor = None
        if tag == 'article':
            self.article_depth = max(0, self.article_depth - 1)
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)


def in_zone(text, territory):
    # These feeds belong to Colombian publishers. Requiring the word Colombia
    # would discard local reporting that already has this country context.
    return not territory or normalize(territory) == 'colombia' or matches(text, [territory])


def feed_items(raw, start, end, *, source=None, terms=(), territory=''):
    feed = feedparser.parse(raw)
    if not feed.get('version'):
        raise ValueError('The source did not return a news feed')
    items, skipped = [], 0
    for entry in feed.entries[:100]:
        title = unescape(entry.get('title', '')).strip()
        text = ' '.join([title, entry.get('author', ''), entry.get('summary', ''),
                         *[c.get('value', '') for c in entry.get('content', [])]])
        if terms and (not matches(text, terms) or not in_zone(text, territory)):
            continue
        published = publication_date(entry.get('published'))
        link = safe_url(entry.get('link'))
        if not published or not link or not title:
            skipped += 1
            continue
        if not start <= published < end:
            continue
        publisher = source or (entry.get('source') or {}).get('title', '')
        if source and urlsplit(link).hostname not in ('confidencialnoticias.com', 'www.confidencialnoticias.com'):
            skipped += 1
            continue
        if not source and publisher and title.endswith(' - ' + publisher):
            title = title[:-len(' - ' + publisher)]
        items.append({'title': title, 'url': link, 'link': link, 'published': iso(published),
                      'source': publisher, 'discovery': 'publisher' if source else 'google_news'})
    return items, skipped, len(feed.entries) >= 100


def google_news(term, territory, start, end):
    # Do not join alternate names with OR: observed RSS queries with an
    # unindexed full-name variant returned an empty feed despite short-name hits.
    query = '"' + term.replace('"', ' ').strip() + '"'
    if territory:
        query += ' "' + territory.replace('"', ' ').strip() + '"'
    query += f' after:{(start-timedelta(days=1)):%Y-%m-%d} before:{(end+timedelta(days=1)):%Y-%m-%d}'
    raw = get_bytes('https://news.google.com/rss/search', params={'q': query, 'hl': 'es-419', 'gl': 'CO', 'ceid': 'CO:es-419'})
    return feed_items(raw, start, end)


def confidencial_news(terms, territory, start, end):
    return feed_items(source_bytes(CONF_FEED), start, end, source='Confidencial Noticias', terms=terms, territory=territory)


def chiva_news(terms, territory, start, end):
    page = Page(source_bytes(CHIVA_HOME).decode('utf-8', errors='replace'))
    if not page.links:
        raise ValueError('The publisher did not return an article listing')
    links = []
    for href, title in page.links:
        link = urljoin(CHIVA_HOME, href)
        parsed = urlsplit(link)
        if parsed.scheme != 'https' or parsed.netloc != 'www.lachivadeuraba.com' or not parsed.path.startswith('/articulo/'):
            continue
        if matches(parsed.path + ' ' + title, terms) and link not in links:
            links.append(link)

    def read_article(link):
        article = Page(source_bytes(link).decode('utf-8', errors='replace'))
        title = article.meta.get('og:title', '')
        text = ' '.join([title, article.meta.get('og:description', ''), *article.article_text])
        if not matches(text, terms) or not in_zone(text, territory):
            return None, 0
        published = publication_date(article.meta.get('article:published_time'))
        # Never substitute dateModified or sitemap lastmod for publication time.
        if not published or not title:
            return None, 1
        if not start <= published < end:
            return None, 0
        return {'title': ' '.join(title.split()), 'url': link, 'link': link,
                'published': iso(published), 'source': 'La Chiva de Urabá', 'discovery': 'publisher'}, 0

    items, skipped = [], 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(read_article, link) for link in links[:5]]
        for future in futures:
            try:
                item, missing = future.result()
                skipped += missing
                if item:
                    items.append(item)
            except (requests.RequestException, ValueError, TypeError):
                skipped += 1
    return items, skipped, len(links) > 5


def search_news(query, start, end, limit=100):
    if isinstance(query, str):
        query = NewsQuery((query,), '')
    terms = list(dict.fromkeys(t.replace('"', ' ').strip() for t in query.terms if t.strip()))
    jobs = [('Google Noticias', google_news, (term, query.territory, start, end)) for term in terms[:MAX_NAMES]]
    jobs.extend([('Confidencial Noticias', confidencial_news, (terms, query.territory, start, end)),
                 ('La Chiva de Urabá', chiva_news, (terms, query.territory, start, end))])
    items, sources, missing = [], [], 0
    limited = len(terms) > MAX_NAMES
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [(name, pool.submit(fn, *args)) for name, fn, args in jobs]
        for name, future in futures:
            try:
                found, skipped, capped = future.result()
                items.extend(found)
                missing += skipped
                limited |= capped or bool(skipped)
                sources.append({'source': name, 'status': 'available', 'retrieved': len(found)})
            except (requests.RequestException, ValueError, TypeError, AttributeError):
                sources.append({'source': name, 'status': 'unavailable', 'retrieved': None})
    active = sorted({s['source'] for s in sources if s['status'] == 'available'})
    failed = sorted({s['source'] for s in sources if s['status'] == 'unavailable'})
    if not active:
        return {'status': 'unavailable', 'count': None, 'items': [], 'limited': True,
                'sources': sources, 'message': 'No fue posible consultar las fuentes. Intenta de nuevo.'}
    # Prefer publisher URLs when the same headline also arrives through Google.
    items.sort(key=lambda i: i['discovery'] != 'publisher')
    unique, urls, titles = [], set(), set()
    for item in items:
        key = url_key(item['url'])
        title_key = (normalize(item['title']), normalize(item['source']), item['published'][:10])
        if key in urls or title_key in titles:
            continue
        urls.add(key)
        titles.add(title_key)
        unique.append(item)
    unique.sort(key=lambda i: i['published'], reverse=True)
    limited |= len(unique) > limit or bool(failed)
    message = 'Fuentes consultadas: ' + ', '.join(active) + '. Cobertura parcial de la web; pueden existir otras publicaciones.'
    if failed:
        message += ' No se completaron todas las consultas de: ' + ', '.join(failed) + '.'
    if missing:
        message += f' Se omitieron {missing} registros sin fecha, enlace o respuesta verificable.'
    if len(unique) > limit:
        message += f' Se muestran las {limit} publicaciones más recientes recuperadas.'
    return {'status': 'available', 'count': len(unique[:limit]), 'items': unique[:limit], 'limited': limited,
            'sources': sources, 'message': message, 'start_time': iso(start), 'end_time': iso(end)}
