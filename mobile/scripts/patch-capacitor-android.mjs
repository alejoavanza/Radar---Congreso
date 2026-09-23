import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';

// Capacitor dispatches on another thread. Save the current page's reply proxy
// before dispatch, so a fast Preferences.get cannot answer the previous page.
// Reproduced by the native help/privacy round-trip test; upstream: ionic-team/capacitor#8382.
const dependency = new URL('../node_modules/@capacitor/android/', import.meta.url);
const version = JSON.parse(await readFile(new URL('package.json', dependency), 'utf8')).version;
assert.equal(version, '8.5.1', 'Review the Android reply-proxy patch when upgrading Capacitor.');
const file = new URL('capacitor/src/main/java/com/getcapacitor/MessageHandler.java', dependency);
const before = '                    postMessage(message.getData());\n                    javaScriptReplyProxy = replyProxy;';
const after = '                    javaScriptReplyProxy = replyProxy;\n                    postMessage(message.getData());';
const source = await readFile(file, 'utf8');
if (!source.includes(after)) {
  assert.equal(source.split(before).length, 2, 'Capacitor bridge changed; review the targeted patch.');
  await writeFile(file, source.replace(before, after));
}
console.log('Verified Android reply proxy is assigned before native plugin dispatch.');
