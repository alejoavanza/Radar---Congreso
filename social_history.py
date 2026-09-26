"""Validate user-supplied exports. No external calls, account tokens or storage."""
import csv
import io
import re
from datetime import date, datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from comparisons import members

social_api = Blueprint('social', __name__)
PLATFORMS = ('instagram', 'facebook', 'tiktok', 'youtube', 'x')
METRICS = ('followers', 'views', 'interactions', 'posts', 'impressions', 'reach')
COLUMNS = ('member_id', 'platform', 'account', 'date', *METRICS, 'source')
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 20000


def today():
    return datetime.now(ZoneInfo('America/Bogota')).date()


def parse_export(text, catalog, as_of=None):
    as_of = as_of or today()
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff'), newline=''))
    fields = reader.fieldnames or []
    required = {'member_id', 'platform', 'account', 'date', 'source'}
    if (not required.issubset(fields) or len(fields) != len(set(fields))
            or set(fields) - set(COLUMNS) or not set(METRICS).intersection(fields)):
        raise ValueError('Usa las columnas de la plantilla CSV; incluye al menos una métrica.')
    rows, seen, accounts = [], {}, {}
    for line, raw in enumerate(reader, 2):
        if len(rows) >= MAX_ROWS:
            raise ValueError('El archivo supera los 20.000 registros. Divídelo por congresista.')
        if None in raw or any(v is None for v in raw.values()):
            raise ValueError(f'Fila {line}: la cantidad de columnas no coincide con la plantilla.')
        row = {key: value.strip() for key, value in raw.items()}
        if row['member_id'] not in catalog or row['platform'] not in PLATFORMS:
            raise ValueError(f'Fila {line}: congresista o red desconocidos.')
        # A stable platform account identifier prevents fake growth on account switches.
        if not re.fullmatch(r'@?[A-Za-z0-9_.-]{1,100}', row['account']):
            raise ValueError(f'Fila {line}: usa el identificador de la cuenta, sin espacios ni enlaces.')
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['date']):
                raise ValueError
            observed = date.fromisoformat(row['date'])
            if observed > as_of:
                raise ValueError
        except ValueError:
            raise ValueError(f'Fila {line}: fecha inválida o futura; usa AAAA-MM-DD.') from None
        source = urlparse(row['source'])
        if (len(row['source']) > 1000 or source.scheme != 'https' or not source.hostname
                or source.username or source.password or re.search(r'\s', row['source'])):
            raise ValueError(f'Fila {line}: fuente inválida; usa una URL https sin credenciales.')
        for metric in METRICS:
            value = row.get(metric, '')
            if value and (not re.fullmatch(r'\d{1,15}', value) or int(value) > 10**12):
                raise ValueError(f'Fila {line}: {metric} debe ser un entero entre 0 y un billón, o vacío.')
            row[metric] = int(value) if value else None
        if all(row[m] is None for m in METRICS):
            raise ValueError(f'Fila {line}: incluye al menos una cifra; vacío significa no disponible.')
        account_key = (row['member_id'], row['platform'])
        account = row['account'].lstrip('@').lower()
        if account_key in accounts and accounts[account_key] != account:
            raise ValueError(f'Fila {line}: hay dos cuentas para una misma persona y red. Impórtalas por separado.')
        accounts[account_key] = account
        key = (*account_key, row['date'])
        if key in seen:
            raise ValueError(f'Fila {line}: fecha y red duplicadas; corrige el archivo antes de importarlo.')
        seen[key] = True
        rows.append(row)
    if not rows:
        raise ValueError('El archivo no tiene registros. Completa la plantilla con datos de tus exportaciones.')
    return rows


@social_api.post('/api/social/import')
def import_export():
    # Scope the upload limit to this endpoint; preserve existing report APIs.
    request.max_content_length = MAX_BYTES
    try:
        uploaded = request.files.get('file')
        if uploaded is None:
            raise ValueError('Selecciona un archivo CSV.')
        raw = uploaded.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise RequestEntityTooLarge()
        rows = parse_export(raw.decode('utf-8-sig'), members())
        response = jsonify({'records': rows, 'as_of': today().isoformat(),
                            'provenance': 'user_import', 'persisted': False})
    except (ValueError, UnicodeError, csv.Error) as error:
        # Validation text contains only row numbers and controlled field names.
        message = str(error) if type(error) is ValueError else 'El archivo debe ser CSV UTF-8 válido.'
        response = jsonify({'error': message})
        response.status_code = 400
    except RequestEntityTooLarge:
        response = jsonify({'error': 'El archivo supera el límite de 2 MB.'})
        response.status_code = 413
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response
