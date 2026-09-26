"""Optional Supabase storage. Never treat a Vercel /tmp file as durable history.

Only the backend calls the restricted SQL RPCs. Configuration does not provision
or purchase a database. Historical YouTube public snapshots expire after 29 days.
"""
from datetime import datetime, timezone
import os
import re

import requests


class StoreUnavailable(Exception):
    """A controlled storage failure; never expose provider bodies or secrets."""


def configuration():
    url = os.environ.get('SOCIAL_SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SOCIAL_SUPABASE_SERVICE_KEY', '')
    valid = bool(re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', url) and key)
    return url, key, valid


def configured():
    return configuration()[2]


def rpc(name, payload):
    url, key, valid = configuration()
    if not valid:
        raise StoreUnavailable('El historial central no está configurado.')
    try:
        with requests.post(url + '/rest/v1/rpc/' + name, json=payload,
                           headers={'apikey': key, 'Authorization': 'Bearer ' + key},
                           timeout=(3, 8), allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise StoreUnavailable('No se pudo acceder al historial central.')
            raw = bytearray()
            for chunk in response.iter_content(8192):
                raw.extend(chunk)
                if len(raw) > 256000:
                    raise StoreUnavailable('La respuesta del historial excede el límite.')
            import json
            result = json.loads(raw)
            if not isinstance(result, list):
                raise StoreUnavailable('El historial no devolvió registros válidos.')
            return result
    except (requests.RequestException, ValueError, TypeError) as error:
        raise StoreUnavailable('El historial no está disponible en este momento.') from None


def history(member_id, platform, account_id):
    if not configured():
        return []
    rows = rpc('radar_follower_history', {'p_member_id': member_id,
               'p_platform': platform, 'p_account_id': account_id})
    now = datetime.now(timezone.utc)
    valid = []
    for row in rows:
        try:
            observed = datetime.fromisoformat(row['observed_at'].replace('Z', '+00:00'))
            expires = datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00'))
            age = (now - observed).total_seconds()
            if (row['member_id'] != member_id or row['platform'] != platform
                    or row['account_id'] != account_id or not 0 <= age < 29 * 86400
                    or expires <= now or row.get('source_kind') != 'official_api'
                    or type(row.get('followers')) is not int or row['followers'] < 0):
                continue
            valid.append(row)
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
    return sorted(valid, key=lambda row: row['observed_at'])


def save(observation):
    if not configured():
        return False
    rows = rpc('radar_record_followers', {'p_observation': observation})
    if not rows or not all(row.get('account_id') == observation['account_id'] for row in rows):
        raise StoreUnavailable('No se confirmó el guardado de la medición.')
    return True
