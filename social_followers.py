"""Public follower observations, never search snippets or generated measurements.

Phase one supports the official YouTube API. Other networks explicitly remain
unavailable. A discovered link is a candidate, not a verified personal account.
"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit, urljoin
import json
import os
import re

import requests
from flask import Blueprint, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from comparisons import members
import follower_store

followers_api = Blueprint('followers', __name__)
PLATFORMS = ('instagram', 'facebook', 'tiktok', 'youtube', 'x')
LABELS = {'instagram': 'Instagram', 'facebook': 'Facebook', 'tiktok': 'TikTok', 'youtube': 'YouTube', 'x': 'X'}
ROOT = Path(__file__).parent
OFFICIAL_HOSTS = {'www.camara.gov.co', 'camara.gov.co', 'www.senado.gov.co', 'senado.gov.co'}
API_URL = 'https://www.googleapis.com/youtube/v3/channels'
_CACHE, _LOCK = {}, Lock()


def now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def safe_https(value):
    try:
        parsed = urlsplit(value)
        return bool(parsed.scheme == 'https' and parsed.hostname and parsed.port in (None, 443)
                    and not parsed.username and not parsed.password and not re.search(r'\s', value))
    except (ValueError, TypeError):
        return False


@lru_cache(maxsize=1)
def registry():
    data = json.loads((ROOT / 'social_accounts.json').read_text(encoding='utf-8'))
    return data.get('accounts', [])


def reviewed_accounts(member_id):
    result = {}
    for item in registry():
        if item.get('member_id') != member_id or item.get('status') != 'reviewed':
            continue
        platform = item.get('platform')
        if platform not in PLATFORMS or not safe_https(item.get('evidence_url')):
            continue
        try:
            checked = datetime.fromisoformat(item['reviewed_at'].replace('Z', '+00:00'))
            if not timedelta(0) <= now() - checked <= timedelta(days=30):
                continue
        except (KeyError, ValueError, TypeError):
            continue
        # Permanent IDs, not names/handles, identify measured YouTube accounts.
        if platform == 'youtube' and not re.fullmatch(r'UC[A-Za-z0-9_-]{22}', item.get('account_id', '')):
            continue
        if platform in result:
            # Ambiguous editorial entries must not silently select one account.
            result[platform] = None
        else:
            result[platform] = item
    return {key: value for key, value in result.items() if value is not None}


def missing(status, message, **extra):
    return {'status': status, 'followers': None, 'observed_at': None,
            'source_kind': None, 'message': message, **extra}


def youtube_observation(account):
    key = os.environ.get('YOUTUBE_API_KEY', '').strip()
    if not key:
        return missing('not_configured', 'Falta habilitar la conexión oficial de YouTube en Radar.')
    account_id = account['account_id']
    # Lock suppresses simultaneous requests in one worker. Provider quota remains
    # the global safeguard; this bounded cache is not durable historical storage.
    with _LOCK:
        cached = _CACHE.get(account_id)
        if cached and monotonic() < cached[0]:
            return dict(cached[1], reused=True)
        if len(_CACHE) > 600:
            _CACHE.clear()
        result = None
        try:
            with requests.get(API_URL, params={'part': 'statistics', 'id': account_id,
                               'fields': 'items(id,statistics(subscriberCount,hiddenSubscriberCount))'},
                              headers={'X-Goog-Api-Key': key}, timeout=(3, 7),
                              allow_redirects=False, stream=True) as response:
                if response.status_code != 200:
                    status = 'quota_limited' if response.status_code in (403, 429) else 'provider_unavailable'
                    result = missing(status, 'YouTube no permitió esta consulta. No se sustituye el dato por cero.')
                else:
                    raw = bytearray()
                    for chunk in response.iter_content(8192):
                        raw.extend(chunk)
                        if len(raw) > 64000:
                            raise ValueError('Response too large')
                    items = json.loads(raw).get('items', [])
                    if len(items) != 1 or items[0].get('id') != account_id:
                        result = missing('account_unavailable', 'No se pudo confirmar el canal registrado.')
                    else:
                        stats = items[0].get('statistics', {})
                        value = stats.get('subscriberCount')
                        if stats.get('hiddenSubscriberCount') is True or value is None:
                            result = missing('not_public', 'El número de suscriptores no está disponible públicamente.')
                        elif not isinstance(value, str) or not re.fullmatch(r'\d{1,13}', value):
                            raise ValueError('Invalid subscriber count')
                        else:
                            observed = now()
                            result = {'status': 'available', 'followers': int(value),
                                      'member_id': account['member_id'], 'platform': 'youtube',
                                      'account_id': account_id,
                                      'account_url': 'https://www.youtube.com/channel/' + account_id,
                                      'observed_at': iso(observed),
                                      'expires_at': iso(observed + timedelta(days=29)),
                                      'source_kind': 'official_api', 'source_name': 'YouTube Data API',
                                      'precision': 'rounded_down_3_significant_figures',
                                      'message': 'Conteo público de YouTube: redondeado hacia abajo a tres cifras significativas.'}
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
            result = missing('provider_unavailable', 'No se pudo obtener una medición válida de YouTube.')
        # Cache failures briefly; a cached response retains its original timestamp.
        _CACHE[account_id] = (monotonic() + (900 if result['status'] == 'available' else 60), result)
        return dict(result, reused=False)


def payload_member():
    request.max_content_length = 4096
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('member_id'), str):
        raise ValueError('Selecciona una persona del directorio.')
    member = members().get(data['member_id'])
    if member is None:
        raise ValueError('La persona no está en el directorio.')
    return member


@followers_api.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@followers_api.errorhandler(RequestEntityTooLarge)
def too_large(error):
    return jsonify({'error': 'La solicitud supera el límite permitido.'}), 413


@followers_api.get('/api/social/status')
def status():
    return jsonify({'schema_version': 1, 'simulated_data': False,
                    'youtube_configured': bool(os.environ.get('YOUTUBE_API_KEY', '').strip()),
                    'history_configured': follower_store.configured(),
                    'history_active': False if not follower_store.configured() else None,
                    'automatic_collection': False,
                    'supported_providers': ['youtube'],
                    'message': 'Las claves y la base deben configurarse por el administrador. No hay rastreo diario automático activo.'})


@followers_api.post('/api/social/followers')
def followers():
    try:
        member = payload_member()
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    accounts = reviewed_accounts(member['id'])
    results = []
    for platform in PLATFORMS:
        account = accounts.get(platform)
        entry = {'platform': platform, 'label': LABELS[platform], 'account': account,
                 'history': [], 'history_status': 'not_configured', 'persisted': False,
                 'growth': None}
        if platform != 'youtube':
            entry.update(missing('connection_pending', 'La consulta automática de esta red todavía no está habilitada.'))
        elif not os.environ.get('YOUTUBE_API_KEY', '').strip():
            entry.update(missing('not_configured', 'Falta habilitar la conexión oficial de YouTube en Radar.'))
        elif not account:
            entry.update(missing('account_pending', 'Falta corroborar y registrar el canal de esta persona.'))
        else:
            observation = youtube_observation(account)
            entry.update(observation)
            if follower_store.configured():
                try:
                    if observation['status'] == 'available':
                        entry['persisted'] = follower_store.save({key: observation[key] for key in
                            ('member_id', 'platform', 'account_id', 'account_url', 'followers',
                             'observed_at', 'expires_at', 'source_kind', 'source_name', 'precision')})
                    entry['history'] = follower_store.history(member['id'], platform, account['account_id'])
                    entry['history_status'] = 'available'
                except follower_store.StoreUnavailable:
                    entry['history_status'] = 'unavailable'
                # A previous measurement remains historical, never today's count.
            entry['comparison_note'] = ('Se muestran observaciones fechadas sin rellenar huecos. '
                'Los porcentajes e índices derivados de YouTube quedan pendientes de la revisión y permisos aplicables.')
        results.append(entry)
    return jsonify({'member_id': member['id'], 'checked_at': iso(now()), 'results': results,
                    'automatic_collection': False, 'simulated_data': False,
                    'history_configured': follower_store.configured(),
                    'note': 'Sólo fuentes habilitadas y cuentas corroboradas. No se consultan todas las redes ni se infieren seguidores desde noticias.'})


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if safe_https(href):
                self.urls.add(href)


def account_link(url):
    parsed = urlsplit(url)
    host = parsed.hostname.removeprefix('www.')
    platform = {'instagram.com': 'instagram', 'facebook.com': 'facebook', 'tiktok.com': 'tiktok',
                'youtube.com': 'youtube', 'twitter.com': 'x', 'x.com': 'x'}.get(host)
    path = parsed.path.strip('/')
    if not platform or not path:
        return None
    if platform == 'youtube':
        valid = bool(re.fullmatch(r'(?:channel/UC[A-Za-z0-9_-]{22}|@[A-Za-z0-9_.-]{3,100})', path))
    elif platform == 'tiktok':
        valid = bool(re.fullmatch(r'@[A-Za-z0-9_.]{2,100}', path))
    else:
        valid = bool(re.fullmatch(r'[A-Za-z0-9_.-]{2,100}', path))
    if not valid or path.lower().lstrip('@') in {'share', 'sharer', 'intent', 'login', 'explore', 'watch', 'reel', 'reels'}:
        return None
    return {'platform': platform, 'url': 'https://' + host + '/' + path,
            'status': 'candidate', 'followers': None}


@lru_cache(maxsize=128)
def discover_links(profile, bucket):
    # The URL comes exclusively from the reviewed congressional catalog.
    # No arbitrary URL, proxy, login, social scraping or redirect bypass exists.
    if not safe_https(profile) or urlsplit(profile).hostname not in OFFICIAL_HOSTS:
        return []
    if len(profile) > 1000:
        return []
    with requests.get(profile, headers={'User-Agent': 'Radar-Politico/3.0 (official-profile-links)'},
                      timeout=(3, 7), allow_redirects=False, stream=True) as response:
        if response.status_code != 200:
            raise ValueError('Profile unavailable')
        if 'text/html' not in response.headers.get('Content-Type', ''):
            raise ValueError('Not HTML')
        raw = bytearray()
        for chunk in response.iter_content(8192):
            raw.extend(chunk)
            if len(raw) > 1000000:
                raise ValueError('Response too large')
    parser = Links()
    parser.feed(raw.decode('utf-8', errors='replace'))
    found = [account_link(url) for url in sorted(parser.urls)]
    return [item for item in found if item is not None][:30]


@followers_api.post('/api/social/discover')
def discover():
    try:
        member = payload_member()
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    profile = member.get('profile_url')
    try:
        candidates = discover_links(profile, int(now().timestamp() // 3600)) if profile else []
        state = 'candidates' if candidates else 'not_found'
    except (requests.RequestException, ValueError, TypeError):
        candidates, state = [], 'source_unavailable'
    return jsonify({'member_id': member['id'], 'source_url': profile,
                    'checked_at': iso(now()), 'status': state, 'candidates': candidates,
                    'message': 'Enlaces hallados en la ficha institucional, no cuentas personales verificadas. '
                               'Pueden pertenecer al Congreso u otras entidades. Requieren revisión antes de medir.'})
