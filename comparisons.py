"""Comparable, bounded web counts. Missing data is never a zero."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode, urlparse
import json
import os

import feedparser
import requests
from news_sources import NewsQuery, search_news
from flask import Blueprint, jsonify, request

comparison_api = Blueprint('comparison', __name__)
PERIODS = (90, 60, 30, 7, 1)
UA = {'User-Agent': 'RADAR-Congreso/2.0 (public-source-comparison)'}
TIMEOUT = (3, 6)


def now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.replace(microsecond=0).isoformat().replace('+00:00', 'Z')


@lru_cache(maxsize=1)
def members():
    data = json.loads((Path(__file__).parent / 'static/congress-members.json').read_text())
    return {member['id']: member for member in data['members']}


def public_member(member):
    return {key: member[key] for key in ('id', 'display_name', 'search_name', 'chamber', 'constituency')}


def query_for(member, territory):
    terms = tuple(dict.fromkeys([member['search_name'], *member['aliases'], member['full_name']]))
    return NewsQuery(terms, territory)


def unavailable(message):
    return {'status': 'unavailable', 'count': None, 'limited': False, 'message': message}


def available(count, message, *, limited=False, **extra):
    return {'status': 'available', 'count': count, 'limited': limited, 'message': message, **extra}


def http_error(source, response):
    messages = {401: 'requiere credenciales válidas', 402: 'requiere créditos o facturación activa',
                403: 'no permite esta consulta con el acceso actual', 429: 'alcanzó el límite temporal de consultas'}
    return unavailable(f'{source} {messages.get(response.status_code, "no pudo responder a la consulta")}.')


def date(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, TypeError, AttributeError):
        return None


def safe_url(value):
    try:
        parsed = urlparse(value or '')
        return value if parsed.scheme in ('http', 'https') and parsed.netloc and not parsed.username and not parsed.password else None
    except ValueError:
        return None


def count_news(query, start, end):
    return search_news(query, start, end, limit=100)


def count_x(query, start, end):
    token = os.getenv('X_BEARER_TOKEN', '').strip()
    if not token:
        return unavailable('X requiere configurar el acceso a su API.')
    # A frozen seven-day window starts outside the moving recent-search boundary.
    endpoint = 'recent' if start > now() - timedelta(days=7) else 'all'
    params = {'query': query, 'start_time': iso(start), 'end_time': iso(end), 'granularity': 'day'}
    headers = {**UA, 'Authorization': f'Bearer {token}'}
    buckets, pages = {}, set()
    for _ in range(4):
        response = requests.get(f'https://api.x.com/2/tweets/counts/{endpoint}', params=params, headers=headers, timeout=TIMEOUT)
        if not response.ok:
            return http_error('X', response)
        payload = response.json()
        if payload.get('errors') or not isinstance(payload.get('data'), list):
            return unavailable('X no devolvió un conteo completo para el periodo.')
        for bucket in payload['data']:
            value = bucket.get('tweet_count', bucket.get('post_count'))
            if type(value) is not int or value < 0 or not bucket.get('start') or not bucket.get('end'):
                return unavailable('X devolvió un conteo que no se pudo verificar.')
            buckets[(bucket['start'], bucket['end'])] = value
        meta = payload.get('meta') or {}
        if not payload['data'] and meta.get('total_tweet_count', meta.get('total_post_count')) != 0:
            return unavailable('X no devolvió un conteo verificable.')
        next_token = meta.get('next_token')
        if not next_token:
            return available(sum(buckets.values()), 'Conteo de publicaciones coincidentes informado por X.',
                             url='https://x.com/search?' + urlencode({'q': query + f' since:{start:%Y-%m-%d} until:{(end+timedelta(days=1)):%Y-%m-%d}', 'f': 'live'}))
        if next_token in pages:
            break
        pages.add(next_token)
        params['next_token'] = next_token
    return unavailable('X no completó el conteo del periodo dentro del límite de consulta.')


def count_bluesky(query, start, end):
    params = {'q': query, 'sort': 'latest', 'limit': 100, 'since': iso(start), 'until': iso(end)}
    seen, cursors, skipped = set(), set(), 0
    for _ in range(3):
        response = requests.get('https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts', params=params, headers=UA, timeout=TIMEOUT)
        if not response.ok:
            return http_error('Bluesky', response)
        payload = response.json()
        if not isinstance(payload.get('posts'), list):
            return unavailable('Bluesky no devolvió un listado verificable.')
        for post in payload['posts']:
            created = date((post.get('record') or {}).get('createdAt'))
            if not created or not post.get('uri'):
                skipped += 1
            elif start <= created < end:
                seen.add(post['uri'])
        cursor = payload.get('cursor')
        if not cursor or not payload['posts']:
            return available(len(seen), 'Publicaciones recuperadas en Bluesky.', limited=bool(skipped),
                             url='https://bsky.app/search?' + urlencode({'q': query}))
        if cursor in cursors:
            break
        cursors.add(cursor)
        params['cursor'] = cursor
    return available(len(seen), 'Muestra de hasta 300 publicaciones recuperadas en Bluesky; puede haber más.', limited=True,
                     url='https://bsky.app/search?' + urlencode({'q': query}))


def count_reddit(query, start, end):
    params = {'q': query, 'sort': 'new', 'limit': 100, 'raw_json': 1, 'restrict_sr': 'false'}
    seen, cursors, skipped = set(), set(), 0
    for _ in range(3):
        response = requests.get('https://www.reddit.com/search.json', params=params, headers=UA, timeout=TIMEOUT)
        if not response.ok:
            return http_error('Reddit', response)
        payload = response.json().get('data') or {}
        if not isinstance(payload.get('children'), list):
            return unavailable('Reddit no devolvió un listado verificable.')
        old = False
        for child in payload['children']:
            post = child.get('data') or {}
            created = post.get('created_utc')
            if not isinstance(created, (int, float)) or not post.get('name'):
                skipped += 1
            elif created < start.timestamp():
                old = True
            elif created < end.timestamp():
                seen.add(post['name'])
        cursor = payload.get('after')
        if old or not cursor or not payload['children']:
            return available(len(seen), 'Publicaciones recuperadas en Reddit.', limited=bool(skipped),
                             url='https://www.reddit.com/search/?' + urlencode({'q': query, 'sort': 'new'}))
        if cursor in cursors:
            break
        cursors.add(cursor)
        params['after'] = cursor
    return available(len(seen), 'Muestra de hasta 300 publicaciones recuperadas en Reddit; puede haber más.', limited=True,
                     url='https://www.reddit.com/search/?' + urlencode({'q': query, 'sort': 'new'}))


def source_count(name, fn, query, start, end):
    try:
        return fn(query, start, end)
    except requests.Timeout:
        return unavailable(f'{name} no respondió a tiempo.')
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
        return unavailable(f'No se pudo verificar la respuesta de {name}.')


@lru_cache(maxsize=128)
def collect(member_id, days, end_time, territory):
    member = members()[member_id]
    end = date(end_time)
    start = end - timedelta(days=days)
    query = query_for(member, territory)
    # Social comparisons are paused. Even older clients only trigger a web query.
    counts = {'Web': source_count('Web', count_news, query, start, end)}
    return {'member': public_member(member), 'sources': counts,
            'start_time': iso(start), 'end_time': end_time, 'days': days, 'territory': territory}


def criteria(payload):
    if not isinstance(payload, dict) or type(payload.get('days')) is not int or payload['days'] not in PERIODS:
        raise ValueError('Elige un periodo de 90, 60, 30, 7 o 1 día.')
    territory = payload.get('territory', 'Colombia')
    if not isinstance(territory, str) or len(territory) > 100:
        raise ValueError('La zona debe tener como máximo 100 caracteres.')
    return payload['days'], territory.strip()


@comparison_api.post('/api/compare/start')
def start_comparison():
    payload = request.get_json(silent=True)
    try:
        days, territory = criteria(payload)
        ids = payload.get('member_ids')
        if not isinstance(ids, list) or not 2 <= len(ids) <= 10 or any(not isinstance(mid, str) or mid not in members() for mid in ids):
            raise ValueError('Selecciona entre 2 y 10 congresistas del directorio.')
        if len(set(ids)) != len(ids):
            raise ValueError('Cada congresista debe aparecer una sola vez.')
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    # Every member uses the same immutable window. Minute buckets also permit cache reuse.
    end = (now() - timedelta(seconds=45)).replace(second=0, microsecond=0)
    return jsonify({'members': [public_member(members()[mid]) for mid in ids], 'days': days,
                    'territory': territory, 'start_time': iso(end - timedelta(days=days)), 'end_time': iso(end)})


@comparison_api.post('/api/compare/member')
def compare_member():
    payload = request.get_json(silent=True)
    try:
        days, territory = criteria(payload)
        member_id = payload.get('member_id')
        if not isinstance(member_id, str) or member_id not in members():
            raise ValueError('El congresista no está en el directorio.')
        end = date(payload.get('end_time'))
        if not end or not now() - timedelta(minutes=15) <= end <= now():
            raise ValueError('La ventana de consulta venció. Genera el comparativo de nuevo.')
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify(collect(member_id, days, iso(end), territory))
