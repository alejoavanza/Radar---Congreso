import assert from 'node:assert/strict';
import {readFile, access} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname, resolve} from 'node:path';
import sharp from 'sharp';
import {JSDOM} from 'jsdom';
const mobile = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read = path => readFile(resolve(mobile, path), 'utf8');
const config = JSON.parse(await read('capacitor.config.json'));
assert.equal(config.appId, 'com.tactikacomunicaciones.radarpolitico');
assert.equal(config.server?.url, undefined);
assert.equal(config.server?.allowNavigation, undefined);
assert.equal(config.server?.cleartext, undefined);
assert.equal(config.ios.webContentsDebuggingEnabled, false);
const html = await read('www/index.html');
const doc = new JSDOM(html).window.document;
assert.equal(doc.querySelector('title').textContent, 'Radar Político');
assert.equal(doc.querySelectorAll('script').length, 1);
assert.equal(doc.querySelector('script').getAttribute('src'), '/native.js');
for (const element of doc.querySelectorAll('[src],link[href]')) {
  const value = element.getAttribute('src') || element.getAttribute('href');
  assert.ok(value.startsWith('/'), `Unexpected remote asset: ${value}`);
  await access(resolve(mobile, 'www', value.slice(1).split('?')[0]));
}
for (const page of ['support', 'privacy']) {
  const pageDoc = new JSDOM(await read(`www/${page}.html`)).window.document;
  assert.equal(pageDoc.querySelector('.back').getAttribute('href'), '/');
  assert.ok(pageDoc.body.textContent.includes('TACTIKA COMUNICACIONES S.A.S'));
}
const manifest = await read('ios/App/App/PrivacyInfo.xcprivacy');
assert.ok(manifest.includes('NSPrivacyAccessedAPICategoryUserDefaults') && manifest.includes('CA92.1'));
const project = await read('ios/App/App.xcodeproj/project.pbxproj');
assert.ok(project.includes('A10200000000000000000001 /* PrivacyInfo.xcprivacy in Resources */,'));
const appConfigurations = [...project.matchAll(/isa = XCBuildConfiguration;[\s\S]*?buildSettings = \{([\s\S]*?)\n\s*};/g)]
  .map(match => match[1]).filter(settings => settings.includes(`PRODUCT_BUNDLE_IDENTIFIER = ${config.appId};`));
assert.equal(appConfigurations.length, 2, 'Debug and Release must use the app Bundle ID');
for (const settings of appConfigurations) assert.match(settings, /TARGETED_DEVICE_FAMILY = 1;/, 'The app targets iPhone');
const icon = await sharp(resolve(mobile, 'ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png')).metadata();
assert.equal(icon.width, 1024); assert.equal(icon.height, 1024); assert.equal(icon.hasAlpha, false);
const generated = JSON.parse(await read('ios/App/App/capacitor.config.json'));
assert.equal(generated.server?.url, undefined);
assert.equal(generated.appId, config.appId);
for (const name of ['AppPlugin', 'CAPBrowserPlugin', 'CAPNetworkPlugin', 'PreferencesPlugin', 'SharePlugin']) {
  assert.ok(generated.packageClassList.includes(name), `Missing native plugin ${name}`);
}
assert.equal(await read('ios/App/App/public/index.html'), html, 'Run npm run sync after source changes');
console.log('Verified bundled interface, local assets, native plugins, app identity, privacy resource and opaque 1024px icon.');
