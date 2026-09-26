"""Offline UI regression checks. All identities and import responses are fixtures.

Run: python tests/browser_social_clarity.py
Requires Playwright and Chromium (CHROMIUM_PATH or /usr/bin/chromium).
Exercises real social template/model/controller; not the server CSV validator,
production directory, external data sources, native apps or PNG exporter.
"""
from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
MEMBERS = [
    dict(id='fixture-ana', full_name='Ana Ejemplo Prueba', display_name='Ejemplo Prueba, Ana',
         search_name='Ana Ejemplo', aliases=['Ana Ejemplo'], chamber='camara', constituency='Prueba'),
    dict(id='fixture-andres', full_name='Andrés Ejemplo Prueba', display_name='Ejemplo Prueba, Andrés',
         search_name='Andrés Ejemplo', aliases=['Andrés Ejemplo'], chamber='senado', constituency='Prueba'),
]
# The existing directory's pure matching functions, with a synthetic catalog.
DIRECTORY = r"""
function normalize(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es').replace(/[^a-z0-9]+/g, ' ').trim();
}
function createIndex(members) {
  const collator = new Intl.Collator('es', {sensitivity:'base'});
  return [...members].sort((a,b) => collator.compare(a.display_name,b.display_name))
    .map(member => ({member,words:[...new Set(normalize([member.full_name,member.search_name,...member.aliases].join(' ')).split(' '))]}));
}
function findMatches(index,value,limit=8) {
  const query=normalize(value);
  if(query.replace(/ /g,'').length<2) return {members:[],total:0};
  const tokens=query.split(' ');
  const matches=index.filter(entry=>tokens.every(token=>entry.words.some(word=>word.startsWith(token))));
  return {members:matches.slice(0,limit).map(entry=>entry.member),total:matches.length};
}
window.RadarCongress={normalize,createIndex,findMatches,selectedId:()=>null,
  catalogReady:Promise.resolve({members:MEMBERS,checked_at:'2026-09-25'})};
window.showTab=()=>{};
""".replace('members:MEMBERS', 'members:' + json.dumps(MEMBERS, ensure_ascii=False))
BASE = '''
:root{--line:#ccd8d8;--panel:#fff;--text:#173c3c;--muted:#526568;--tactika-teal:#075056}
*{box-sizing:border-box}body{font-family:Arial,sans-serif;margin:0;padding:20px;color:var(--text);background:white}
main{max-width:980px;margin:auto}label{display:block;font-size:14px;margin:12px 0 7px}
input,select,button{font:inherit;padding:12px;border:1px solid var(--line);border-radius:6px;width:100%;min-height:44px}
input[type=hidden]{display:none}button{background:#075056;color:white;cursor:pointer;margin:8px 0}.secondary{background:#fff;color:#075056}
.subtle,.note{font-size:13px;color:#526568}.methodology{border:1px solid #ccd8d8;border-radius:6px;margin:14px 0;padding:12px}.methodology-body{padding-top:10px}summary{cursor:pointer}
'''


def main():
    checks = []
    def check(condition, description):
        assert condition, description
        checks.append(description)

    template = (ROOT / 'templates/social_history.html').read_text()
    html = '<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>' + BASE + (ROOT / 'static/social-history.css').read_text() + '</style></head><body><main><h1>Prueba de interfaz · datos ficticios</h1>' + template + '</main></body></html>'
    result = {'records': [], 'as_of': '2026-09-25'}
    error_mode = [False]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), args=['--no-sandbox'], headless=True)
        page = browser.new_page(viewport={'width':390,'height':844}, device_scale_factor=1)
        page.set_default_timeout(5000)
        errors=[]
        page.on('pageerror', lambda error: errors.append(str(error)))
        # Entirely offline DOM: no browser navigation or network requests.
        page.expose_function('__fixtureImport', lambda: {'ok': not error_mode[0], 'body': {'error': 'CSV inválido de prueba'} if error_mode[0] else result})
        page.set_content(html)
        page.add_script_tag(content="window.fetch=async(url)=>{if(url!=='/api/social/import')throw new Error('Unexpected fetch in offline test');const result=await window.__fixtureImport();return {ok:result.ok,json:async()=>result.body};};")
        page.add_script_tag(content=DIRECTORY)
        page.add_script_tag(path=str(ROOT/'static/social-history-model.js'))
        page.add_script_tag(path=str(ROOT/'static/social-history.js'))
        page.wait_for_function("!document.getElementById('social-search').disabled")
        check(page.locator('#social-member').get_attribute('type')=='hidden', 'Only one visible person picker')
        check(page.locator('#social-member').input_value()=='', 'No politician is silently preselected')
        check(page.locator('#social-total-value').inner_text()=='N/D', 'Missing observations are not shown as zero')
        check(not page.locator('#social-charts').is_visible(), 'No empty five-chart grid without records')
        check(page.locator('.social-publishing').get_attribute('open') is None, 'Image creation starts collapsed')
        search=page.locator('#social-search')
        search.fill('Ejemplo')
        check(page.locator('#social-options [role=option]').count()==2,'Partial search exposes both matching identities')
        check(page.locator('#social-member').input_value()=='','Partial search does not choose the first identity')
        search.press('ArrowDown');search.press('Enter')
        check(page.locator('#social-member').input_value()=='fixture-ana','Keyboard explicitly selects one identity')
        check(search.get_attribute('aria-expanded')=='false','Selection closes suggestions accessibly')
        search.fill('Andres')
        check(page.locator('#social-member').input_value()=='','Editing clears the prior person immediately')
        check(page.locator('#social-total-value').inner_text()=='N/D','Editing never retains the prior person count')
        page.locator('#social-options [role=option]').click()
        check(page.locator('#social-member').input_value()=='fixture-andres','Click selects the accent-insensitive match')
        page.locator('#social-search-clear').click()
        check(search.input_value()=='' and page.locator('#social-member').input_value()=='','Clear removes both label and identity')
        search.fill('ZZZ desconocido')
        check('Sin coincidencias' in page.locator('#social-search-status').inner_text(),'Unknown person is explicit, no fallback identity')
        search.fill('Ejemplo');search.press('Escape')
        check(search.get_attribute('aria-expanded')=='false','Escape closes the suggestion popup')
        # Emulate an accepted server import. This deliberately does not test CSV parsing.
        end=page.evaluate('RadarSocialModel.bogotaToday()')
        start=page.evaluate("new Date(Date.parse(RadarSocialModel.bogotaToday())-3*86400000).toISOString().slice(0,10)")
        result['as_of']=end
        result['records']=[dict(member_id='fixture-ana',platform='instagram',account='fixture',date=date,
            followers=value,views=views,interactions=None,posts=None,impressions=None,reach=10,
            source='https://example.org/fixture') for date,value,views in [(start,1000,100),(end,1250,200)]]
        page.get_by_text('Importar registros y conservar una copia', exact=True).click()
        upload=page.locator('#social-file')
        upload.set_input_files({'name':'fixture.csv','mimeType':'text/csv','buffer':b'fixture'})
        page.wait_for_function("document.getElementById('social-import-status').textContent.includes('2 registros importados')")
        check(page.locator('#social-member').input_value()=='fixture-ana','Import selects its recorded identity explicitly')
        for platform in ['facebook','tiktok','youtube','x']:
            page.locator(f'.social-networks input[value={platform}]').uncheck()
        check(page.locator('#social-total-value').inner_text().replace('.','')=='1250','Prominent figure is latest follower balance, not growth')
        change=page.locator('#social-total-change').inner_text()
        check('+250' in change and '25 %' in change,'Growth shown separately as net observed change and percentage')
        check('entre' in change and start[-2:] in change,'Growth uses the actual observation dates')
        check('Origen no verificado' in page.locator('#social-data-state').inner_text(),'Imported origin never labelled verified or automatic')
        check('Valores absolutos'==page.locator('#social-piece-scale option[value=absolute]').text_content(),'Absolute scale is not labelled real data')
        page.locator('#social-metric').select_option('views')
        check(page.locator('#social-total-value').inner_text()=='200','Daily metric shows last day, not sum of the period')
        check('no al acumulado' in page.locator('#social-total-change').inner_text(),'Daily units are explicitly explained')
        page.locator('#social-metric').select_option('reach')
        check(page.locator('#social-total-value').inner_text()=='N/D','Reach never summed across platforms')
        page.locator('#social-metric').select_option('followers')
        error_mode[0]=True
        upload.set_input_files({'name':'bad.csv','mimeType':'text/csv','buffer':b'bad'})
        page.wait_for_function("document.getElementById('social-import-status').textContent.includes('No se reemplazó')")
        check(page.locator('#social-total-value').inner_text().replace('.','')=='1250','Rejected import preserves previous records')
        error_mode[0]=False
        # Measured zero is a valid balance; percent must not divide by zero.
        result['records'][0]['followers']=0
        result['records'][1]['followers']=0
        upload.set_input_files({'name':'zero.csv','mimeType':'text/csv','buffer':b'zero'})
        page.wait_for_function("document.getElementById('social-total-value').textContent==='0'")
        check('base cero' in page.locator('#social-total-change').inner_text(),'Measured zero is retained, percentage remains N/D')
        # One observation cannot establish growth.
        result['records']=result['records'][1:]
        result['records'][0]['followers']=1250
        upload.set_input_files({'name':'one.csv','mimeType':'text/csv','buffer':b'one'})
        page.wait_for_function("document.getElementById('social-import-status').textContent.includes('1 registros importados')")
        check('Crecimiento: N/D' in page.locator('#social-total-change').inner_text(),'One observation never invents a growth rate')
        search.fill('Andres')
        check(page.locator('#social-total-value').inner_text()=='N/D','Changing person also clears already-imported visible totals')
        page.locator('#social-options [role=option]').click()
        check('Sin registros para esta persona' in page.locator('#social-data-state').inner_text(),'Records from another person do not leak into the selected report')
        page.locator('#social-clear').click()
        check('Sin datos importados' in page.locator('#social-data-state').inner_text(),'Clear updates provenance and missing-data state')
        check(page.locator('#social-export').is_disabled(),'Cleared records cannot be exported')
        page.locator('#social-search-clear').click()
        for width in [360,390,768,1200]:
            page.set_viewport_size({'width':width,'height':900})
            check(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'No horizontal overflow at {width}px')
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(ROOT/'social-clarity-mobile.png'),full_page=True)
        check(not errors,'No browser JavaScript exceptions: '+repr(errors))
        browser.close()
    report={'passed':len(checks),'checks':checks,'limits':'Offline browser test, synthetic directory and import API. No production/native/backend/export claims.'}
    (ROOT/'social-clarity-test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
