"""Discover pages across indexes, then verify original publication metadata."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from html.parser import HTMLParser
from ipaddress import ip_address
from itertools import zip_longest
import json
import logging
import socket
from time import time
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

import certifi
import feedparser
import urllib3

from news_sources import UA, matches, publication_date, safe_url, social_result, source_bytes, iso, url_key

MAX_CANDIDATES = 24
PAGE_BYTES = 512_000


def indexed_query(terms, territory):
    phrases = ['"' + term.replace('"', ' ').strip() + '"' for term in terms]
    query = phrases[0] if len(phrases) == 1 else '(' + ' OR '.join(phrases) + ')'
    return query + (' "' + territory.replace('"', ' ').strip() + '"' if territory else '')


def candidates(rows, engine):
    result = []
    for row in rows:
        link = safe_url(row.get('url') or row.get('link'))
        if not link or social_result(link, row.get('source') or row.get('domain') or {}):
            continue
        result.append({'url': link, 'title': row.get('title', ''),
                       'summary': row.get('summary', ''), 'engine': engine, 'candidate': True})
    return result


def bing_web(term, territory, start, end):
    # General web search: no publisher allowlist and no dependence on Google News.
    # Keep variants independent: complex OR expressions can return unrelated pages.
    query = indexed_query([term], territory)
    # Index freshness is a discovery hint only; verify the original date on the page.
    first_day, last_day = int(start.timestamp() // 86400), int(end.timestamp() // 86400)
    url = 'https://www.bing.com/search?' + urlencode({'q': query, 'format': 'rss', 'count': 30, 'mkt': 'es-CO',
                                                    'filters': f'ex1:"ez5_{first_day}_{last_day}"'})
    feed = feedparser.parse(source_bytes(url))
    if not feed.get('version'):
        raise ValueError('Web search did not return a feed')
    return candidates(feed.entries[:30], 'Bing web'), 0, len(feed.entries) >= 30


def gdelt_web(terms, territory, start, end):
    url = 'https://api.gdeltproject.org/api/v2/doc/doc?' + urlencode({
        'query': indexed_query(terms[:1], territory), 'mode': 'artlist', 'format': 'json',
        'maxrecords': 30, 'sort': 'datedesc', 'startdatetime': start.strftime('%Y%m%d%H%M%S'),
        'enddatetime': end.strftime('%Y%m%d%H%M%S')})
    data = json.loads(source_bytes(url))
    if not isinstance(data, dict) or not isinstance(data.get('articles'), list):
        raise ValueError('News index did not return articles')
    # seendate is an index timestamp. Never use it as the publication date.
    return candidates(data['articles'][:30], 'GDELT'), 0, len(data['articles']) >= 30


def public_target(url):
    if not safe_url(url) or social_result(url, {}):
        raise ValueError('Not a public web article')
    parsed = urlsplit(url)
    if parsed.port not in (None, 80, 443) or '%' in parsed.hostname or any(ord(c) < 33 for c in url):
        raise ValueError('Unsafe article address')
    host = parsed.hostname.encode('idna').decode('ascii')
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    addresses = list(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))
    if not addresses or any(not ip_address(address).is_global for address in addresses):
        raise ValueError('Article address is not public')
    # Pin the validated address so a second DNS lookup cannot reach a private host.
    address = next((address for address in addresses if ':' not in address), addresses[0])
    return parsed, host, port, address


@lru_cache(maxsize=96)
def cached_page(url, bucket):
    for _ in range(4):
        parsed, host, port, address = public_target(url)
        if parsed.scheme == 'https':
            pool = urllib3.HTTPSConnectionPool(address, port=port, server_hostname=host,
                                              assert_hostname=host, cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        else:
            pool = urllib3.HTTPConnectionPool(address, port=port)
        response = None
        try:
            path = urlunsplit(('', '', parsed.path or '/', parsed.query, ''))
            response = pool.urlopen('GET', path, headers={**UA, 'Host': parsed.netloc, 'Accept-Encoding': 'identity'},
                                    timeout=urllib3.Timeout(connect=2, read=5), redirect=False, retries=False,
                                    preload_content=False, assert_same_host=False)
            if response.status in (301, 302, 303, 307, 308) and response.headers.get('Location'):
                url = urljoin(url, response.headers['Location'])
                continue  # Every redirect is validated independently, including social domains.
            if response.status != 200:
                raise ValueError('Article response unavailable')
            if 'html' not in response.headers.get('Content-Type', '').lower():
                raise ValueError('Article is not HTML')
            # Metadata normally appears in the head; never download an unbounded page.
            return url, response.read(PAGE_BYTES, decode_content=True).decode('utf-8', errors='replace')
        finally:
            if response is not None:
                response.close()
            pool.close()
    raise ValueError('Too many redirects')


class ArticlePage(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.meta, self.structured, self.article_text = {}, [], []
        self.canonical, self.depth, self.script, self.buffer = '', 0, False, []
        self.ignored = 0
        self.feed(raw)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('property', attrs.get('name', '')).lower()] = attrs.get('content', '')
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs.get('href', '')
        if tag in ('article', 'main'):
            self.depth += 1
        if tag in ('script', 'style', 'nav', 'footer', 'aside'):
            self.ignored += 1
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.script, self.buffer = True, []

    def handle_data(self, value):
        if self.script:
            self.buffer.append(value)
        elif self.depth and not self.ignored:
            self.article_text.append(value)

    def handle_endtag(self, tag):
        if tag == 'script' and self.script:
            try:
                self.structured.append(json.loads(''.join(self.buffer)))
            except (ValueError, TypeError):
                pass
            self.script = False
        if tag in ('article', 'main'):
            self.depth = max(0, self.depth - 1)
        if tag in ('script', 'style', 'nav', 'footer', 'aside'):
            self.ignored = max(0, self.ignored - 1)


def article_objects(value):
    if isinstance(value, list):
        for child in value:
            yield from article_objects(child)
    elif isinstance(value, dict):
        types = value.get('@type', [])
        types = [types] if isinstance(types, str) else types
        if any(t in ('Article', 'NewsArticle', 'BlogPosting', 'OpinionNewsArticle', 'ReportageNewsArticle') for t in types):
            yield value
        if '@graph' in value:
            yield from article_objects(value['@graph'])
        if 'mainEntity' in value:
            yield from article_objects(value['mainEntity'])


def verify_page(candidate, terms, start, end):
    url, raw = cached_page(candidate['url'], int(time() // 300))
    page = ArticlePage(raw)
    objects = list(article_objects(page.structured))
    # The first article describes the main page; never choose a sidebar article's date.
    article = objects[0] if objects else {}
    published = publication_date(page.meta.get('article:published_time') or article.get('datePublished'))
    if not published:
        logging.getLogger(__name__).warning('Page omitted: host=%s; reason=publication_date', urlsplit(url).hostname)
        return None, 1
    if not start <= published < end:
        logging.getLogger(__name__).warning('Page omitted: host=%s; reason=outside_window', urlsplit(url).hostname)
        return None, 0
    title = page.meta.get('og:title') or article.get('headline') or candidate['title']
    text = ' '.join([title, candidate.get('summary', ''), page.meta.get('description', ''),
                     page.meta.get('og:description', ''), page.meta.get('author', ''),
                     json.dumps(article.get('author', ''), ensure_ascii=False),
                     article.get('articleBody', ''), *page.article_text])
    if not title or not matches(text, terms):
        return None, 0
    canonical = urljoin(url, page.canonical)
    if safe_url(canonical) and urlsplit(canonical).hostname == urlsplit(url).hostname:
        url = canonical
    if social_result(url, {}):
        return None, 0
    domain = urlsplit(url).hostname.removeprefix('www.')
    return {'title': ' '.join(title.split()), 'url': url, 'link': url, 'published': iso(published),
            'source': page.meta.get('og:site_name') or domain, 'publisher_domain': domain,
            'discovery': candidate['engine']}, 0


def verify_candidates(found, terms, start, end):
    groups = {}
    for candidate in found:
        groups.setdefault(candidate['engine'], []).append(candidate)
    # Give each index a share of the bounded page-verification budget.
    ordered, seen = [], set()
    for row in zip_longest(*groups.values()):
        for candidate in row:
            if candidate is not None and url_key(candidate['url']) not in seen:
                seen.add(url_key(candidate['url']))
                ordered.append(candidate)
    items, skipped = [], 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(verify_page, candidate, terms, start, end) for candidate in ordered[:MAX_CANDIDATES]]
        for candidate, future in zip(ordered[:MAX_CANDIDATES], futures):
            try:
                item, missing = future.result()
                skipped += missing
                if item:
                    items.append(item)
            except (ValueError, TypeError, AttributeError, RecursionError, OSError, urllib3.exceptions.HTTPError) as error:
                logging.getLogger(__name__).warning('Page omitted: host=%s; reason=%s', urlsplit(candidate['url']).hostname, type(error).__name__)
                skipped += 1
    logging.getLogger(__name__).warning('Web verification: candidates=%s; verified=%s; unavailable=%s', len(ordered), len(items), skipped)
    return items, skipped, len(ordered) > MAX_CANDIDATES
