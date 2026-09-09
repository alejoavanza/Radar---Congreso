"""Discover pages across indexes, then verify original publication metadata."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from html.parser import HTMLParser
from ipaddress import ip_address
from itertools import zip_longest
import base64
import json
import logging
import re
import socket
from time import time
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlsplit, urlunsplit

import certifi
import requests
import urllib3

from news_sources import UA, matches, publication_date, safe_url, social_result, source_bytes, iso, url_key
from source_catalog import matching_source, site_query

MAX_CANDIDATES = 24
MAX_FOCUSED_CANDIDATES = 76
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


class SearchPage(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.rows, self.current, self.capture = [], None, False
        self.feed(raw)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'result__a' in attrs.get('class', '').split():
            link = urljoin('https://html.duckduckgo.com/', attrs.get('href', ''))
            if urlsplit(link).hostname in ('duckduckgo.com', 'html.duckduckgo.com'):
                link = parse_qs(urlsplit(link).query).get('uddg', [''])[0]
            self.current = {'url': link, 'title': ''}
            self.rows.append(self.current)
            self.capture = True

    def handle_data(self, text):
        if self.capture:
            self.current['title'] += text

    def handle_endtag(self, tag):
        if tag == 'a':
            self.capture = False


def web_query(query, start, end):
    url = 'https://html.duckduckgo.com/html/?' + urlencode({'q': query,
                                                         'df': 'd' if (end-start).days <= 1 else 'w' if (end-start).days <= 7 else 'm' if (end-start).days <= 30 else 'y'}, quote_via=quote)
    raw = source_bytes(url).decode('utf-8', errors='replace')
    if 'anomaly.js' in raw or 'challenge-form' in raw:
        raise ValueError('Web search requires an interactive challenge')
    page = SearchPage(raw)
    if not page.rows and 'no-results' not in raw:
        raise ValueError('Web search did not return results')
    return page.rows[:30], len(page.rows) >= 30


def duckduckgo_web(terms, territory, start, end):
    rows, capped = web_query(indexed_query(terms[:1], territory), start, end)
    return candidates(rows, 'DuckDuckGo web'), 0, capped


def focused_web(terms, territory, start, end, batch):
    rows, capped = web_query(indexed_query(terms, territory) + ' ' + site_query(batch), start, end)
    found = []
    for item in candidates(rows, 'DuckDuckGo fuentes'):
        source = matching_source(item['url'], batch)
        if source:
            item['catalog_source'] = source.id
            item['engine'] = 'DuckDuckGo · ' + source.name
            found.append(item)
    return found, 0, capped


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


@lru_cache(maxsize=256)
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
            # Google places its public link metadata after ~650 KB of UI scripts.
            # Keep article reads small and bound the fixed Google host separately.
            byte_limit = 2_000_000 if host == 'news.google.com' else PAGE_BYTES
            return url, response.read(byte_limit, decode_content=True).decode('utf-8', errors='replace')
        finally:
            if response is not None:
                response.close()
            pool.close()
    raise ValueError('Too many redirects')


class ArticlePage(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.meta, self.structured, self.article_text, self.published_times = {}, [], [], []
        self.canonical, self.depth, self.script, self.buffer = '', 0, False, []
        self.ignored = 0
        self.feed(raw)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[(attrs.get('property') or attrs.get('name') or attrs.get('itemprop') or '').lower()] = attrs.get('content', '')
        if tag == 'time' and (attrs.get('itemprop') == 'datePublished' or 'published' in attrs.get('class', '').split()):
            self.published_times.append(attrs.get('datetime', ''))
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


class GoogleLinkPage(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.signature, self.timestamp = '', ''
        self.feed(raw)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('data-n-a-sg') and attrs.get('data-n-a-ts'):
            self.signature, self.timestamp = attrs['data-n-a-sg'], attrs['data-n-a-ts']


@lru_cache(maxsize=256)
def google_article(url, bucket):
    """Resolve a public Google News link, then read its original article.

    The public garturlreq protocol is documented by
    github.com/SSujitX/google-news-url-decoder. No authenticated content,
    retries, proxy rotation or challenge handling is used.
    """
    parsed = urlsplit(url)
    token = parsed.path.rstrip('/').rsplit('/', 1)[-1]
    if parsed.hostname != 'news.google.com' or not re.fullmatch(r'[A-Za-z0-9_-]{8,2048}', token):
        raise ValueError('Invalid Google News article link')
    # Older feeds encode a direct URL; modern links use the public redirect RPC.
    decoded = base64.urlsafe_b64decode(token + '=' * (-len(token) % 4))
    embedded = re.search(rb'https?://[^\x00-\x20\x7f-\xff]+', decoded)
    if embedded:
        return cached_page(embedded.group().decode('ascii'), bucket)
    final, raw = cached_page('https://news.google.com/articles/' + token, bucket)
    if urlsplit(final).hostname != 'news.google.com':
        return final, raw
    page = GoogleLinkPage(raw)
    if not page.timestamp.isdigit() or not page.signature or len(page.signature) > 1024:
        raise ValueError('Google News did not provide an original article URL')
    context = [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
                None, None, None, None, None, 0, 1], "X", "X", 1, [1, 1, 1],
               1, 1, None, 0, 0, None, 0]
    payload = json.dumps([[['Fbv4je', json.dumps([
        'garturlreq', context, token, int(page.timestamp), page.signature])]]])
    # The POST target is fixed, redirects are disabled, and the response is bounded.
    with requests.post('https://news.google.com/_/DotsSplashUi/data/batchexecute',
                       data={'f.req': payload}, headers=UA, timeout=(2, 4),
                       allow_redirects=False, stream=True) as response:
        response.raise_for_status()
        chunks, size = [], 0
        for chunk in response.iter_content(8192):
            size += len(chunk)
            if size > PAGE_BYTES:
                raise ValueError('Google article response exceeds the retrieval limit')
            chunks.append(chunk)
        raw = b''.join(chunks).decode('utf-8', errors='replace')
    for line in raw.splitlines():
        try:
            rows = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, list) and len(row) > 2 and row[0:2] == ['wrb.fr', 'Fbv4je']:
                result = json.loads(row[2])
                if isinstance(result, list) and len(result) > 1 and result[0] == 'garturlres':
                    return cached_page(result[1], bucket)
    raise ValueError('Google News original article URL unavailable')


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


def verify_page(candidate, terms, start, end, territory=''):
    loader = google_article if urlsplit(candidate['url']).hostname == 'news.google.com' else cached_page
    url, raw = loader(candidate['url'], int(time() // 300))
    if candidate.get('catalog_source'):
        source = matching_source(url)
        if not source or source.id != candidate['catalog_source']:
            return None, 0
    page = ArticlePage(raw)
    objects = list(article_objects(page.structured))
    # The first article describes the main page; never choose a sidebar article's date.
    article = objects[0] if objects else {}
    published = next((value for raw_date in [page.meta.get('article:published_time'), article.get('datePublished'),
                                            page.meta.get('datepublished'), page.meta.get('parsely-pub-date'), *page.published_times]
                      if (value := publication_date(raw_date))), None)
    if not published:
        logging.getLogger(__name__).info('Page omitted: host=%s; reason=publication_date', urlsplit(url).hostname)
        return None, 1
    if not start <= published < end:
        logging.getLogger(__name__).info('Page omitted: host=%s; reason=outside_window', urlsplit(url).hostname)
        return None, 0
    title = page.meta.get('og:title') or article.get('headline') or ''
    text = ' '.join([title, page.meta.get('description', ''),
                     page.meta.get('og:description', ''), page.meta.get('author', ''),
                     json.dumps(article.get('author', ''), ensure_ascii=False),
                     article.get('articleBody', ''), *page.article_text])
    if not matches(text, terms):
        return None, 0
    if territory and not matches(text, (territory,)):
        return None, 0
    canonical = urljoin(url, page.canonical)
    same_section = not candidate.get('catalog_source') or (
        (canonical_source := matching_source(canonical)) is not None and
        canonical_source.id == candidate['catalog_source'])
    if safe_url(canonical) and urlsplit(canonical).hostname == urlsplit(url).hostname and same_section:
        url = canonical
    if social_result(url, {}):
        return None, 0
    domain = urlsplit(url).hostname.removeprefix('www.')
    title = title or candidate['title']
    if not title:
        return None, 1
    return {'title': ' '.join(title.split()), 'url': url, 'link': url, 'published': iso(published),
            'source': page.meta.get('og:site_name') or domain, 'publisher_domain': domain,
            'discovery': candidate['engine'], **({'catalog_source': candidate['catalog_source']} if candidate.get('catalog_source') else {})}, 0


def verify_candidates(found, terms, start, end, territory=''):
    groups, by_url = {}, {}
    for candidate in found:
        key = url_key(candidate['url'])
        if key not in by_url or candidate.get('catalog_source'):
            by_url[key] = candidate
    for candidate in by_url.values():
        # Round-robin publishers, so a large outlet cannot consume the budget.
        groups.setdefault((bool(candidate.get('catalog_source')), candidate.get('publisher_domain') or urlsplit(candidate['url']).hostname), []).append(candidate)
    # Give each index a share of the bounded page-verification budget.
    ordered, seen = [], set()
    for row in zip_longest(*groups.values()):
        for candidate in row:
            if candidate is not None and url_key(candidate['url']) not in seen:
                seen.add(url_key(candidate['url']))
                ordered.append(candidate)
    general = [c for c in ordered if not c.get('catalog_source')]
    focused = [c for c in ordered if c.get('catalog_source')]
    selected = general[:MAX_CANDIDATES] + focused[:MAX_FOCUSED_CANDIDATES]
    items, skipped = [], 0
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(verify_page, candidate, terms, start, end, territory) for candidate in selected]
        for candidate, future in zip(selected, futures):
            try:
                item, missing = future.result()
                skipped += missing
                if item:
                    items.append(item)
            except (ValueError, TypeError, AttributeError, RecursionError, OSError, urllib3.exceptions.HTTPError, requests.RequestException) as error:
                logging.getLogger(__name__).info('Page omitted: host=%s; reason=%s; %s', urlsplit(candidate['url']).hostname, type(error).__name__, str(error)[:120] if isinstance(error, ValueError) else '')
                skipped += 1
    logging.getLogger(__name__).info('Web verification: candidates=%s; verified=%s; unavailable=%s', len(ordered), len(items), skipped)
    return items, skipped, len(general) > MAX_CANDIDATES or len(focused) > MAX_FOCUSED_CANDIDATES
