import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {JSDOM} from 'jsdom';
import sharp from 'sharp';

const mobile = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read = path => readFile(resolve(mobile,path),'utf8');
const config = JSON.parse(await read('capacitor.config.json'));
const generated = JSON.parse(await read('android/app/src/main/assets/capacitor.config.json'));
assert.equal(generated.appId,config.appId);
assert.equal(generated.server?.url,undefined);
assert.equal(generated.server?.allowNavigation,undefined);
assert.equal(generated.android?.allowMixedContent,false);
assert.equal(generated.android?.webContentsDebuggingEnabled,false);
const deps = JSON.parse(await read('package.json')).dependencies;
assert.equal(deps['@capacitor/android'],deps['@capacitor/ios']);
const bridge = await read('node_modules/@capacitor/android/capacitor/src/main/java/com/getcapacitor/MessageHandler.java');
assert.ok(bridge.includes('javaScriptReplyProxy = replyProxy;\n                    postMessage(message.getData());'),
  'Apply the Android reply-proxy patch with npm run postinstall before building.');
const plugins = JSON.parse(await read('android/app/src/main/assets/capacitor.plugins.json'));
for (const name of ['app','browser','network','preferences','share']) assert.ok(plugins.some(p=>p.pkg==='@capacitor/'+name),`Missing ${name}`);
for (const asset of ['index.html','native.js','app.js','mobile.css','support.html','privacy.html','static/congress-members.json']) {
  assert.equal(await read('www/'+asset),await read('android/app/src/main/assets/public/'+asset),`Unsynced ${asset}`);
}
const html = new JSDOM(await read('www/index.html'));
assert.equal(html.window.document.querySelectorAll('#source-catalog li').length,38);
const manifest = new JSDOM(await read('android/app/src/main/AndroidManifest.xml'),{contentType:'text/xml'}).window.document;
const permissions = [...manifest.querySelectorAll('uses-permission')].map(p=>p.getAttribute('android:name'));
assert.deepEqual(permissions,['android.permission.INTERNET']);
assert.equal(manifest.querySelector('application').getAttribute('android:allowBackup'),'false');
assert.equal(manifest.querySelector('application').getAttribute('android:usesCleartextTraffic'),'false');
const variables = await read('android/variables.gradle');
assert.match(variables,/targetSdkVersion\s*=\s*36/);
const gradle = await read('android/app/build.gradle');
assert.ok(gradle.includes('applicationId "'+config.appId+'"'));
const icon = await sharp(resolve(mobile,'android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png')).metadata();
assert.equal(icon.width,192);
console.log('Verified Android identity, bundled resources, 38 sources, plugins, icons, API 36 and release configuration.');
