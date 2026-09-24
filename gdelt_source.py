"""On-demand GDELT DOC discovery. Original pages remain the source of evidence."""
from datetime import timezone
from html import unescape
import json
import re
from threading import Lock
from time import monotonic
from urllib.parse import urlencode, urlsplit

import requests
from search_state import SearchCache

API_URL = 'https://api.gdeltproject.org/api/v2/doc/doc'
MAX_RECORDS = 100
MAX_BYTES = 2_000_000
cache = SearchCache(128)
_lock = Lock()
_next_request = 0.0


def _retrieve(url):
    """Bounded transport, no retries. Rate limiting is per server process."""
    global _next_request
    if not _lock.acquire(blocking=False):
        raise ValueError('GDELT: consulta en curso; cobertura parcial')
    try:
        if monotonic() < _next_request:
            raise ValueError('GDELT: pausa temporal de consultas; cobertura parcial')
        _next_request = monotonic() + 5
        try:
            with requests.get(url, headers={'User-Agent': 'Radar-Politico/2.2'},
                              timeout=(2, 6), allow_redirects=False, stream=True) as response:
                if response.status_code != 200:
                    raise ValueError('GDELT: HTTP ' + str(response.status_code))
                chunks, size, started = [], 0, monotonic()
                for chunk in response.iter_content(8192):
                    size += len(chunk)
                    if size > MAX_BYTES or monotonic() - started > 8:
                        raise ValueError('GDELT: respuesta excede el límite')
                    chunks.append(chunk)
                payload = json.loads(b''.join(chunks))
                if not isinstance(payload, dict) or not isinstance(payload.get('articles'), list):
                    raise ValueError('GDELT: respuesta sin lista de noticias')
                return payload
        except (requests.RequestException, ValueError, TypeError):
            _next_request = monotonic() + 60
            raise
    finally:
        _lock.release()


def gdelt_news(terms, territory, start, end):
    # Search names across languages and countries. Apply territory to the
    # original article, not to the publisher's nationality or translated index.
    from news_sources import safe_url, social_result
    phrases = list(dict.fromkeys(' '.join(re.findall(r'[^\W_]+', term, re.UNICODE))
                                 for term in terms[:6]))
    phrases = [phrase for phrase in phrases if phrase]
    if not phrases:
        raise ValueError('GDELT: falta el nombre del político')
    quoted = ['"' + phrase + '"' for phrase in phrases]
    query = quoted[0] if len(quoted) == 1 else '(' + ' OR '.join(quoted) + ')'
    url = API_URL + '?' + urlencode({
        'query': query, 'mode': 'artlist', 'format': 'json', 'sort': 'datedesc',
        'maxrecords': MAX_RECORDS,
        'startdatetime': start.astimezone(timezone.utc).strftime('%Y%m%d%H%M%S'),
        'enddatetime': end.astimezone(timezone.utc).strftime('%Y%m%d%H%M%S'),
    })
    payload = cache.call(url, lambda: _retrieve(url))
    rows = payload['articles']
    found, skipped = [], 0
    for row in rows[:MAX_RECORDS]:
        if not isinstance(row, dict):
            skipped += 1
            continue
        link = safe_url(row.get('url')) if isinstance(row.get('url'), str) else None
        title = row.get('title')
        if not link or not isinstance(title, str) or not title.strip():
            skipped += 1
            continue
        if social_result(link, {}):
            continue
        found.append({'url': link, 'title': unescape(title).strip(), 'engine': 'GDELT',
                      'publisher_domain': urlsplit(link).hostname.removeprefix('www.'),
                      'candidate': True})
        # seendate is an indexing time, never a publication date. Country and
        # language labels from the index also do not establish article context.
    return found, skipped, len(rows) >= MAX_RECORDS
