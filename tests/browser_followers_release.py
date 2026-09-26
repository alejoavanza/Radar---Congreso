"""Real application in local CI; synthetic catalog and mocked external providers.
No fixture is written to the production registry, API or persistent database.
"""
from pathlib import Path
import json
import os
import sys
import threading
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import app
import social_followers as sf
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

MEMBERS = [dict(id='fixture-ana', full_name='Ana Ejemplo Prueba', display_name='Ejemplo Prueba, Ana',
 search_name='Ana Ejemplo', aliases=['Ana Ejemplo'], chamber='camara', constituency='Prueba', party='Pruebas',
 profile_url='https://www.camara.gov.co/representantes/fixture-ana/'),
 dict(id='fixture-andres', full_name='Andrés Ejemplo Prueba', display_name='Ejemplo Prueba, Andrés',
 search_name='Andrés Ejemplo', aliases=['Andrés Ejemplo'], chamber='senado', constituency='Prueba', party='Pruebas',
 profile_url='https://www.senado.gov.co/fixture-andres/')]
CHANNEL = 'UC' + 'a' * 22
OUT = ROOT / 'release-evidence'

class Reply:
    status_code = 200
    headers = {'Content-Type': 'application/json'}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def iter_content(self, size):
        yield json.dumps({'items':[{'id':CHANNEL,'statistics':{'subscriberCount':'12000','hiddenSubscriberCount':False}}]}).encode()


def exercise(pw, engine, device, origin):
    checks, errors = [], []
    def check(condition, description):
        assert condition, description
        checks.append(description)
    browser = getattr(pw, engine).launch(headless=True)
    context = browser.new_context(**pw.devices[device])
    page = context.new_page(); page.set_default_timeout(10000)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/static/congress-members.json*', lambda route: route.fulfill(json={'members':MEMBERS,'checked_at':sf.now().date().isoformat()}))
    try:
        page.goto(origin, wait_until='networkidle')
        page.locator('#social-tab').tap()
        check(page.locator('#followers-search').is_visible(), 'Real follower UI opens')
        check(page.locator('#social-piece-example').count() == 0, 'No public demo button')
        check(not page.evaluate("[...document.scripts].some(s=>s.src.includes('social-export.js'))"), 'Demo exporter is not loaded')
        check(page.locator('#followers-results .social-network').count() == 0, 'No automatically preselected person or data')
        check('pendiente' in page.locator('#followers-service').inner_text().lower(), 'Missing connection is disclosed')
        search = page.locator('#followers-search'); search.fill('Ejemplo')
        page.locator('#followers-options [role=option]').first.wait_for()
        check(page.locator('#followers-options [role=option]').count() == 2, 'Same catalog exposes both matching names')
        search.press('ArrowDown'); search.press('Enter')
        page.wait_for_function("document.getElementById('followers-progress').textContent.includes('terminada')")
        check(page.locator('#followers-results .social-network').count() == 5, 'Each platform reports its own availability')
        check(page.locator('#followers-results .social-empty').count() == 5, 'No credentials means no fabricated values')
        check(page.locator('#followers-results strong').count() == 0, 'Unavailable counts are not zeros')
        search.fill('Andres')
        check(page.locator('#followers-results .social-network').count() == 0, 'Editing immediately clears old identity data')
        page.locator('#followers-options [role=option]').tap()
        page.wait_for_function("document.getElementById('followers-progress').textContent.includes('terminada')")
        check('Andrés' in search.input_value(), 'Accent-insensitive touch selection')
        page.locator('#followers-clear').tap()
        check(search.input_value() == '' and page.locator('#followers-results').inner_text() == '', 'Clear removes identity and all data')
        search.fill('ZZZdesconocido')
        check('Sin coincidencias' in page.locator('#followers-search-status').inner_text(), 'Unknown names never silently select a person')
        os.environ['YOUTUBE_API_KEY'] = 'test-only-key'
        sf._CACHE.clear()
        reviewed = dict(member_id='fixture-ana',platform='youtube',account_id=CHANNEL,status='reviewed',
                        evidence_url=MEMBERS[0]['profile_url'],reviewed_at=sf.iso(sf.now()))
        with patch('social_followers.registry', return_value=[reviewed]), patch('social_followers.requests.get', return_value=Reply()):
            search.fill('Ana Ejemplo'); page.locator('#followers-options [role=option]').tap()
            page.wait_for_function("document.getElementById('followers-progress').textContent.includes('terminada')")
            check(page.locator('#followers-results strong').inner_text().replace('.','') == '12000', 'Mock official API value is displayed verbatim')
            check('YouTube Data API' in page.locator('#followers-results').inner_text(), 'Source attribution is visible')
            check('obtenido' in page.locator('#followers-results').inner_text(), 'Observation timestamp is visible')
            check('redondeado' in page.locator('#followers-results').inner_text(), 'Public count precision is disclosed')
            check('no se guardó' in page.locator('#followers-results').inner_text(), 'No false durable-history claim')
            for days in ['1','7','28']:
                page.locator('#followers-period').select_option(days)
                check(page.locator('#followers-results strong').count() == 1, 'History filter preserves current observation: ' + days)
            page.locator('#followers-refresh').tap()
            page.wait_for_function("document.getElementById('followers-progress').textContent.includes('terminada')")
            check('reutilizada' in page.locator('#followers-results').inner_text(), 'Cached measurement keeps its original acquisition time')
        os.environ.pop('YOUTUBE_API_KEY', None); sf._CACHE.clear()
        # A stale response which ignores AbortController must still be discarded.
        page.evaluate("""() => { const original = window.fetch; window.fetch = (url,options) => {
          if(url === '/api/social/followers') return new Promise(resolve => setTimeout(() => resolve({ok:true,json:async()=>({member_id:'fixture-ana',simulated_data:false,checked_at:new Date().toISOString(),results:[]})}),500));
          return original(url,options);
        }; }""")
        page.locator('#followers-refresh').tap(); page.locator('#followers-clear').tap()
        page.wait_for_timeout(650)
        check(page.locator('#followers-results').inner_text() == '' and search.input_value() == '', 'Late response cannot resurrect cleared selection')
        page.locator('#compare-tab').tap(); check(page.locator('#comparetab').is_visible(), 'Comparativos still opens')
        page.locator('#report-tab').tap(); check(page.locator('#reporttab').is_visible(), 'Radar still opens')
        page.locator('#social-tab').tap()
        for width in [360,390,768,1200]:
            page.set_viewport_size({'width':width,'height':900})
            check(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'No horizontal overflow at {width}px')
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(OUT/f'{engine}-followers.png'), full_page=True)
        check(not errors, 'No JavaScript exceptions: ' + repr(errors))
        return {'engine':engine,'device_profile':device,'passed':len(checks),'checks':checks}
    except Exception:
        page.screenshot(path=str(OUT/f'{engine}-failure.png'),full_page=True)
        raise
    finally:
        os.environ.pop('YOUTUBE_API_KEY', None); sf._CACHE.clear()
        context.close(); browser.close()


def main():
    OUT.mkdir(exist_ok=True)
    server = make_server('127.0.0.1', 0, app)
    worker = threading.Thread(target=server.serve_forever,daemon=True); worker.start()
    try:
        with patch.dict(os.environ, {}, clear=True), patch('social_followers.members',return_value={m['id']:m for m in MEMBERS}), sync_playwright() as pw:
            results = [exercise(pw,engine,device,f'http://127.0.0.1:{server.server_port}/')
                       for engine,device in [('chromium','Pixel 7'),('webkit','iPhone 13')]]
        report = {'results':results,'limits':'Real application in local CI with synthetic identities and mocked provider. Not physical-device, live provider, production database or native/store verification.'}
        (OUT/'follower-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:
        server.shutdown(); worker.join(timeout=5)


if __name__ == '__main__': main()
