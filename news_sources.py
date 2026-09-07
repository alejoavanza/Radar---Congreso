"""Bounded news discovery, with independent name queries and explicit coverage."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from html import unescape
from time import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
import re
import unicodedata
import logging

import feedparser
import requests

TIMEOUT = (3, 8)
UA = {'User-Agent': 'Radar-Politico/2.1 (public-news-monitor)'}
MAX_NAMES = 6
MAX_BYTES = 2_000_000
SOCIAL_HOSTS = ('facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'tiktok.com',
                'reddit.com', 'bsky.app', 'youtube.com', 'youtu.be', 'threads.com', 'threads.net')
SOCIAL_LABELS = {'facebook', 'instagram', 'twitter', 'x', 'tiktok', 'reddit', 'bluesky', 'youtube', 'threads'}


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


def social_result(link, source):
    label = source.get('title', '') if isinstance(source, dict) else str(source or '')
    href = source.get('href', '') if isinstance(source, dict) else ''
    if normalize(label) in SOCIAL_LABELS:
        return True
    for value in (link, href, label if '.' in label and ' ' not in label else ''):
        try:
            host = (urlsplit(value if '://' in value else 'https://' + value).hostname or '').lower()
        except ValueError:
            continue
        if any(host == domain or host.endswith('.' + domain) for domain in SOCIAL_HOSTS):
            return True
    return False


def url_key(value):
    parsed = urlsplit(value)
    tracking = {'fbclid', 'gclid', 'oc', 'hl', 'gl', 'ceid'}
    query = [(k, v) for k, v in parse_qsl(parsed.query) if not k.lower().startswith('utm_') and k.lower() not in tracking]
    return urlunsplit(('', parsed.netloc.lower().removeprefix('www.'), parsed.path.rstrip('/'), urlencode(sorted(query)), ''))


def get_bytes(url, **kwargs):
    response = requests.get(url, timeout=kwargs.pop('timeout', TIMEOUT), headers=UA, **kwargs)
    response.raise_for_status()
    if len(response.content) > MAX_BYTES:
        raise ValueError('Source response exceeds the retrieval limit')
    return response.content


@lru_cache(maxsize=64)
def cached_source(url, bucket):
    # Cached index URLs use fixed hosts and encoded search parameters.
    timeout = (3, 20) if urlsplit(url).hostname == 'api.gdeltproject.org' else TIMEOUT
    return get_bytes(url, timeout=timeout)


def source_bytes(url):
    return cached_source(url, int(time() // 300))


def feed_items(raw, start, end, *, source=None, terms=(), territory=''):
    feed = feedparser.parse(raw)
    if not feed.get('version'):
        raise ValueError('The source did not return a news feed')
    items, skipped = [], 0
    for entry in feed.entries[:100]:
        if social_result(entry.get('link', ''), entry.get('source') or {}):
            continue
        title = unescape(entry.get('title', '')).strip()
        text = ' '.join([title, entry.get('author', ''), entry.get('summary', ''),
                         *[c.get('value', '') for c in entry.get('content', [])]])
        if terms and not matches(text, terms):
            continue
        published = publication_date(entry.get('published'))
        link = safe_url(entry.get('link'))
        if not published or not link or not title:
            skipped += 1
            continue
        if not start <= published < end:
            continue
        publisher = source or (entry.get('source') or {}).get('title', '')
        if not source and publisher and title.endswith(' - ' + publisher):
            title = title[:-len(' - ' + publisher)]
        items.append({'title': title, 'url': link, 'link': link, 'published': iso(published),
                      'source': publisher, 'publisher_domain': (urlsplit((entry.get('source') or {}).get('href', '')).hostname or '').removeprefix('www.'), 'discovery': 'publisher' if source else 'google_news'})
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


def search_news(query, start, end, limit=100):
    from web_discovery import bing_web, gdelt_web, verify_candidates
    if isinstance(query, str):
        query = NewsQuery((query,), '')
    terms = list(dict.fromkeys(t.replace('"', ' ').strip() for t in query.terms if t.strip()))
    jobs = [('Google Noticias', google_news, (term, query.territory, start, end)) for term in terms[:MAX_NAMES]]
    jobs.extend([('Bing web', bing_web, (terms[:MAX_NAMES], query.territory, start, end)),
                 ('GDELT', gdelt_web, (terms[:MAX_NAMES], query.territory, start, end))])
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
            except (requests.RequestException, ValueError, TypeError, AttributeError) as error:
                status = getattr(getattr(error, 'response', None), 'status_code', None)
                logging.getLogger(__name__).warning('News source unavailable: %s; %s; HTTP %s', name, type(error).__name__, status)
                sources.append({'source': name, 'status': 'unavailable', 'retrieved': None})
    candidates = [item for item in items if item.get('candidate')]
    items = [item for item in items if not item.get('candidate')]
    if candidates:
        verified, skipped, capped = verify_candidates(candidates, terms, start, end)
        items.extend(verified)
        missing += skipped
        limited |= capped or bool(skipped)
    logging.getLogger(__name__).warning('Search indexes: %s', [(s['source'], s['status'], s['retrieved']) for s in sources])
    active = sorted({s['source'] for s in sources if s['status'] == 'available'})
    failed = sorted({s['source'] for s in sources if s['status'] == 'unavailable'})
    if not active:
        return {'status': 'unavailable', 'count': None, 'items': [], 'limited': True,
                'sources': sources, 'message': 'No fue posible consultar las fuentes. Intenta de nuevo.'}
    # Prefer publisher URLs when the same headline also arrives through Google.
    items.sort(key=lambda i: i['discovery'] == 'google_news')
    unique, urls, titles = [], set(), set()
    for item in items:
        key = url_key(item['url'])
        title_key = (normalize(item['title']), normalize(item.get('publisher_domain') or item['source']), item['published'][:10])
        if key in urls or title_key in titles:
            continue
        urls.add(key)
        titles.add(title_key)
        unique.append(item)
    unique.sort(key=lambda i: i['published'], reverse=True)
    limited |= len(unique) > limit or bool(failed)
    message = 'Búsqueda en noticias y páginas web. Cobertura parcial; no incluye redes sociales.'
    if failed:
        message = 'Consulta parcial: no se completó la búsqueda en todos los buscadores. Se muestran los resultados disponibles.'
    if missing:
        message += ' Algunas páginas se omitieron por falta de fecha o contenido verificable.'
    if len(unique) > limit:
        message += f' Se muestran las {limit} publicaciones más recientes recuperadas.'
    return {'status': 'available', 'count': len(unique[:limit]), 'items': unique[:limit], 'limited': limited,
            'sources': sources, 'message': message, 'start_time': iso(start), 'end_time': iso(end)}
