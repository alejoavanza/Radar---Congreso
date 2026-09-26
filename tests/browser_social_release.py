"""Release smoke tests: real Flask app and UI, synthetic identities and records.

Runs Chromium/Android and WebKit/iPhone profiles. Does not claim physical-device,
native Capacitor, third-party social-account or app-store verification.
"""
from pathlib import Path
import csv
import io
import json
import struct
import sys
import threading
from datetime import timedelta
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import app
from social_history import COLUMNS, today
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

MEMBERS = [
    dict(id='fixture-ana', full_name='Ana Ejemplo Prueba', display_name='Ejemplo Prueba, Ana',
         search_name='Ana Ejemplo', aliases=['Ana Ejemplo'], chamber='camara',
         constituency='Prueba', party='Datos ficticios'),
    dict(id='fixture-andres', full_name='Andrés Ejemplo Prueba', display_name='Ejemplo Prueba, Andrés',
         search_name='Andrés Ejemplo', aliases=['Andrés Ejemplo'], chamber='senado',
         constituency='Prueba', party='Datos ficticios'),
]
OUT = ROOT / 'release-evidence'


def fixture_csv():
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=COLUMNS)
    writer.writeheader()
    for date, followers in [(today() - timedelta(days=3), 1000), (today(), 1250)]:
        writer.writerow(dict(member_id='fixture-ana', platform='instagram', account='fixture',
                             date=date.isoformat(), followers=followers, views=200,
                             source='https://example.org/synthetic-test'))
    return stream.getvalue().encode('utf-8')


def exercise(pw, engine, device, origin):
    checks, errors = [], []
    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    browser = getattr(pw, engine).launch(headless=True)
    context = browser.new_context(**pw.devices[device], accept_downloads=True)
    page = context.new_page()
    page.set_default_timeout(12000)
    page.on('pageerror', lambda error: errors.append(str(error)))
    catalog = {'members': MEMBERS, 'checked_at': today().isoformat()}
    page.route('**/static/congress-members.json*', lambda route: route.fulfill(json=catalog))
    try:
        page.goto(origin, wait_until='networkidle')
        page.wait_for_function('window.RadarSocialModel && window.RadarCongress')
        page.locator('#name').fill('Ejemplo')
        page.locator('#congress-options [role=option]').first.wait_for()
        radar_names = page.locator('#congress-options .congress-option-name').all_text_contents()
        page.locator('#social-tab').click()
        search = page.locator('#social-search')
        search.fill('Ejemplo')
        page.locator('#social-options [role=option]').first.wait_for()
        plus_names = page.locator('#social-options .congress-option-name').all_text_contents()
        check(plus_names == radar_names and len(plus_names) == 2, 'Radar and Plus use identical matching names')
        check(page.locator('#social-member').input_value() == '', 'No implicit identity selection')
        search.press('ArrowDown')
        search.press('Enter')
        check(page.locator('#social-member').input_value() == 'fixture-ana', 'Keyboard selection')
        search.fill('Andres')
        check(page.locator('#social-member').input_value() == '', 'Editing clears old identity')
        page.locator('#social-options [role=option]').tap()
        check(page.locator('#social-member').input_value() == 'fixture-andres', 'Touch selection and accent-insensitive matching')
        page.locator('#social-search-clear').tap()
        check(search.input_value() == '' and page.locator('#social-member').input_value() == '', 'Clear both name and identity')
        search.fill('ZZZ desconocido')
        check('Sin coincidencias' in page.locator('#social-search-status').inner_text(), 'Unknown names do not select another person')
        search.fill('Ana Ejemplo')
        page.locator('#social-options [role=option]').tap()
        page.get_by_text('Importar registros y conservar una copia', exact=True).click()
        with page.expect_download() as pending:
            page.locator('#social-template').click()
        path = OUT / f'{engine}-template.csv'
        pending.value.save_as(path)
        template = path.read_bytes()
        check(b'\r\n' in template and b'fixture-ana' in template, 'Template CSV download with CRLF and selected identity')
        upload = page.locator('#social-file')
        upload.set_input_files({'name': 'synthetic-test.csv', 'mimeType': 'text/csv', 'buffer': fixture_csv()})
        page.wait_for_function("document.getElementById('social-import-status').textContent.includes('2 registros importados')")
        for platform in ['facebook', 'tiktok', 'youtube', 'x']:
            page.locator(f'.social-networks input[value={platform}]').uncheck()
        check(page.locator('#social-total-value').inner_text().replace('.', '') == '1250', 'Real Flask CSV validation and latest follower value')
        check('+250' in page.locator('#social-total-change').inner_text(), 'Growth separate from follower balance')
        check('Origen no verificado' in page.locator('#social-data-state').inner_text(), 'Imported provenance is explicit')
        for value in page.locator('#social-period option').evaluate_all('(options) => options.map(o => o.value)'):
            page.locator('#social-period').select_option(value)
            check(bool(page.locator('#social-window').inner_text()), 'Period renders: ' + value)
        page.locator('#social-period').select_option('7d')
        page.locator('#social-metric').select_option('reach')
        check(page.locator('#social-total-value').inner_text() == 'N/D', 'Reach is not summed across platforms')
        page.locator('#social-metric').select_option('followers')
        upload.set_input_files({'name': 'invalid.csv', 'mimeType': 'text/csv', 'buffer': b'not,a,valid,file\n'})
        page.wait_for_function("document.getElementById('social-import-status').textContent.includes('No se reemplazó')")
        check(page.locator('#social-total-value').inner_text().replace('.', '') == '1250', 'Rejected CSV preserves prior import')
        with page.expect_download() as pending:
            page.locator('#social-export').click()
        exported = OUT / f'{engine}-records.csv'
        pending.value.save_as(exported)
        check(b'1250' in exported.read_bytes(), 'Imported records can be exported')
        page.locator('#social-clear').click()
        check(page.locator('#social-total-value').inner_text() == 'N/D', 'Clearing data restores N/D')
        check(page.locator('#social-export').is_disabled(), 'No export after clearing data')
        page.locator('.social-publishing > summary').click()
        for format_name, dimensions in [('portrait', (1080, 1350)), ('landscape', (1600, 900)), ('story', (1080, 1920))]:
            page.locator('#social-piece-format').select_option(format_name)
            page.locator('#social-piece-example').click()
            page.locator('#social-piece-dialog[open]').wait_for()
            with page.expect_download() as pending:
                page.locator('#social-piece-download').click()
            png = OUT / f'{engine}-{format_name}-SIMULATED.png'
            pending.value.save_as(png)
            raw = png.read_bytes()
            check(raw[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', raw[16:24]) == dimensions, 'Simulated PNG export: ' + format_name)
            page.locator('#social-piece-close').click()
        page.locator('#compare-tab').click()
        check(page.locator('#comparetab').is_visible(), 'Comparativos still opens')
        page.locator('#report-tab').click()
        check(page.locator('#reporttab').is_visible(), 'Radar still opens')
        page.locator('#social-tab').click()
        for width in [360, 390, 768, 1200]:
            page.set_viewport_size({'width': width, 'height': 900})
            check(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'No horizontal overflow at {width}px')
        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=str(OUT / f'{engine}-plus.png'), full_page=True)
        check(not errors, 'No JavaScript exceptions: ' + repr(errors))
        return {'engine': engine, 'device_profile': device, 'passed': len(checks), 'checks': checks}
    except Exception:
        page.screenshot(path=str(OUT / f'{engine}-failure.png'), full_page=True)
        raise
    finally:
        context.close()
        browser.close()


def main():
    OUT.mkdir(exist_ok=True)
    app.config.update(TESTING=True)
    server = make_server('127.0.0.1', 0, app)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with patch('social_history.members', return_value={m['id']: m for m in MEMBERS}), sync_playwright() as pw:
            results = [exercise(pw, engine, device, f'http://127.0.0.1:{server.server_port}/')
                       for engine, device in [('chromium', 'Pixel 7'), ('webkit', 'iPhone 13')]]
        report = {'results': results, 'limitations': 'Local real app and CSV validator; synthetic identities and measurements. Emulated browser profiles, not physical devices, native Capacitor builds, social-account access or store publication.'}
        (OUT / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()
        worker.join(timeout=5)


if __name__ == '__main__':
    main()
