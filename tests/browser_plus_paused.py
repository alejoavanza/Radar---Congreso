"""Verify temporary Plus withdrawal and unchanged Radar/Comparativos navigation.
Runs the real application with a synthetic directory; never writes production data.
"""
from pathlib import Path
import json
import os
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'release-evidence'
MEMBERS = [dict(id='fixture-ana', full_name='Ana Ejemplo Prueba', display_name='Ejemplo Prueba, Ana',
 search_name='Ana Ejemplo', aliases=['Ana Ejemplo'], chamber='camara', constituency='Prueba', party='Pruebas',
 profile_url='https://www.camara.gov.co/representantes/fixture-ana/'),
 dict(id='fixture-andres', full_name='Andrés Ejemplo Prueba', display_name='Ejemplo Prueba, Andrés',
 search_name='Andrés Ejemplo', aliases=['Andrés Ejemplo'], chamber='senado', constituency='Prueba', party='Pruebas',
 profile_url='https://www.senado.gov.co/fixture-andres/')]


def exercise(pw, engine, device, origin):
    checks, errors, social_requests = [], [], []
    def check(condition, description):
        assert condition, description
        checks.append(description)
    launch = {'headless': True}
    if engine == 'chromium' and os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
        launch['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
    browser = getattr(pw, engine).launch(**launch)
    context = browser.new_context(**pw.devices[device])
    context.add_init_script("""if (!sessionStorage.getItem('pause-test-initialized')) {
      sessionStorage.setItem('radar:tab:v1', 'social');
      sessionStorage.setItem('pause-test-initialized', '1');
    }""")
    page = context.new_page(); page.set_default_timeout(10000)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: social_requests.append(request.url) if '/api/social/' in request.url else None)
    page.route('**/static/congress-members.json*', lambda route: route.fulfill(json={'members': MEMBERS, 'checked_at': '2026-09-27'}))
    try:
        page.goto(origin, wait_until='networkidle')
        check(page.locator('[role=tab]').all_text_contents() == ['RADAR', 'COMPARATIVOS'], 'Only Radar and Comparativos are offered')
        check(page.locator('#social-tab, #socialtab, #followers-search').count() == 0, 'Plus tab and panel are absent, not merely hidden')
        check(page.locator('#reporttab').is_visible(), 'A previous Plus session opens Radar, not a blank screen')
        check(not page.evaluate("[...document.scripts].some(s=>/social-(followers|history|export)/.test(s.src))"), 'No Plus scripts are loaded')
        check(not page.evaluate("[...document.querySelectorAll('link[rel=stylesheet]')].some(s=>/social-/.test(s.href))"), 'No Plus-only styles affect the remaining tabs')
        name = page.locator('#name'); name.fill('Ejemplo')
        page.locator('#congress-options [role=option]').first.wait_for()
        check(page.locator('#congress-options [role=option]').count() == 2, 'Radar autocomplete retains matching names')
        name.press('ArrowDown'); name.press('Enter')
        check('Ana' in name.input_value(), 'Radar keyboard selection works')
        page.locator('#clear-name').tap()
        check(name.input_value() == '', 'Radar clear-name button works')
        page.locator('#days').select_option('7')
        page.locator('#territory').fill('Antioquia')
        page.locator('#compare-tab').tap()
        check(page.locator('#comparetab').is_visible() and not page.locator('#reporttab').is_visible(), 'Comparativos opens independently')
        compare = page.locator('#compare-name'); compare.fill('Ejemplo')
        page.locator('#compare-options [role=option]').first.wait_for()
        check(page.locator('#compare-options [role=option]').count() == 2, 'Comparativos autocomplete retains matching names')
        page.locator('#compare-options [role=option]').first.tap()
        check('Ana' in page.locator('#compare-selected').inner_text(), 'Comparativos touch selection works')
        compare.fill('Andres')
        page.locator('#compare-options [role=option]').tap()
        check('Andrés' in page.locator('#compare-selected').inner_text(), 'Accent-insensitive second selection works')
        check(page.locator('#compare-run').is_enabled(), 'Comparison remains available for two people')
        page.locator('#compare-days').select_option('30')
        page.locator('#compare-territory').fill('Colombia')
        page.locator('#report-tab').tap()
        check(page.locator('#days').input_value() == '7' and page.locator('#territory').input_value() == 'Antioquia', 'Radar filters survive switching tabs')
        page.locator('#compare-tab').tap()
        check(page.locator('#compare-days').input_value() == '30' and 'Andrés' in page.locator('#compare-selected').inner_text(), 'Comparison selection and filters survive switching tabs')
        page.reload(wait_until='networkidle')
        check(page.locator('#comparetab').is_visible(), 'Saved Comparativos tab is restored')
        page.evaluate("showTab('social')")
        check(page.locator('#reporttab').is_visible(), 'Stale Plus navigation safely falls back to Radar')
        check(page.evaluate("sessionStorage.getItem('radar:tab:v1')") == 'report', 'Stale tab preference is normalized without clearing other data')
        check(page.locator('.tactika-links a').count() == 3, 'Existing Táctika footer links are preserved')
        check(page.locator('#methodology').count() == 1, 'Existing methodology is preserved')
        for width in [360, 390, 768, 1200]:
            page.set_viewport_size({'width': width, 'height': 900})
            check(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'No horizontal overflow at {width}px')
            page.locator('#compare-tab').tap()
            check(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'Comparison fits at {width}px')
            page.locator('#report-tab').tap()
        page.set_viewport_size({'width': 390, 'height': 844})
        OUT.mkdir(exist_ok=True)
        page.screenshot(path=str(OUT / f'{engine}-plus-paused.png'), full_page=True)
        check(not social_requests, 'No social API requests are made')
        check(not errors, 'No JavaScript exceptions: ' + repr(errors))
        return {'engine': engine, 'device_profile': device, 'passed': len(checks), 'checks': checks}
    except Exception:
        OUT.mkdir(exist_ok=True)
        page.screenshot(path=str(OUT / f'{engine}-pause-failure.png'), full_page=True)
        raise
    finally:
        context.close(); browser.close()


def main():
    from app import app
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    OUT.mkdir(exist_ok=True)
    server = make_server('127.0.0.1', 0, app)
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    try:
        with sync_playwright() as pw:
            results = [exercise(pw, engine, device, f'http://127.0.0.1:{server.server_port}/')
                       for engine, device in [('chromium', 'Pixel 7'), ('webkit', 'iPhone 13')]]
        report = {'results': results, 'limits': 'Real app in local CI, synthetic directory. Not physical-device or native/store verification.'}
        (OUT / 'plus-paused-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        server.shutdown(); worker.join(timeout=5)


if __name__ == '__main__': main()
