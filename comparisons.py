"""Comparable, bounded web counts. Missing data is never a zero."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
import json

import requests
from news_sources import NewsQuery, search_news
from flask import Blueprint, jsonify, request
from search_state import SearchCache

comparison_api = Blueprint('comparison', __name__)
PERIODS = (90, 60, 30, 7, 1)


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


def count_news(query, start, end):
    return search_news(query, start, end, limit=100)


def source_count(name, fn, query, start, end):
    try:
        return fn(query, start, end)
    except requests.Timeout:
        return unavailable(f'{name} no respondió a tiempo.')
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
        return unavailable(f'No se pudo verificar la respuesta de {name}.')


def _collect(member_id, days, end_time, territory):
    member = members()[member_id]
    end = date(end_time)
    start = end - timedelta(days=days)
    query = query_for(member, territory)
    # Social comparisons are paused. Even older clients only trigger a web query.
    counts = {'Web': source_count('Web', count_news, query, start, end)}
    return {'member': public_member(member), 'sources': counts,
            'start_time': iso(start), 'end_time': end_time, 'days': days, 'territory': territory}


_results = SearchCache(128)


def collect(member_id, days, end_time, territory):
    return _results.call((member_id, days, end_time, territory),
                         lambda: _collect(member_id, days, end_time, territory),
                         accept=lambda row: row['sources']['Web']['status'] == 'available')


collect.cache_clear = _results.clear


def search_end(value=None):
    if value is None:
        return (now() - timedelta(seconds=45)).replace(second=0, microsecond=0)
    end = date(value)
    if not end or not now() - timedelta(minutes=15) <= end <= now():
        raise ValueError('La ventana de consulta venció. Actualiza la búsqueda.')
    return end


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
        end = search_end(payload.get('end_time'))
        ids = payload.get('member_ids')
        if not isinstance(ids, list) or not 2 <= len(ids) <= 10 or any(not isinstance(mid, str) or mid not in members() for mid in ids):
            raise ValueError('Selecciona entre 2 y 10 congresistas del directorio.')
        if len(set(ids)) != len(ids):
            raise ValueError('Cada congresista debe aparecer una sola vez.')
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    # Every member uses the same immutable window. Minute buckets also permit cache reuse.
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
