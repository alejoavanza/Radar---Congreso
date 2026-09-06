import {readFile, writeFile, cp, mkdir, rm} from 'node:fs/promises';
import {dirname, resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {build} from 'esbuild';

const mobile = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(mobile, '..');
const out = join(mobile, 'www');
const config = JSON.parse(await readFile(join(mobile, 'capacitor.config.json'), 'utf8'));
if (config.server?.url || config.server?.allowNavigation || config.server?.cleartext) throw new Error('Release builds must load bundled assets, with no live-reload origin.');
await rm(out, {recursive: true, force: true});
await mkdir(out, {recursive: true});
await cp(join(root, 'static'), join(out, 'static'), {recursive: true});

let html = await readFile(join(root, 'templates/index.html'), 'utf8');
if (/\{\{|\{%/.test(html)) throw new Error('Render any server template variables before packaging.');
const scripts = [];
for (const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
  const src = match[1].match(/\bsrc=["']([^"']+)["']/i)?.[1];
  if (src) {
    const path = src.split('?')[0];
    if (!/^\/static\/[a-zA-Z0-9_-]+\.js$/.test(path)) throw new Error('Bundle only reviewed local scripts: ' + src);
    scripts.push(await readFile(join(root, path), 'utf8'));
  } else scripts.push(match[2]);
}
if (scripts.length !== 4) throw new Error('The source script list changed; review bootstrap order before building.');
html = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '');
html = html.replace('</head>', '<link rel="stylesheet" href="/mobile.css"></head>');
html = html.replace('<main class="wrap">', `<main class="wrap">
<p id="native-starting" class="native-notice" role="status">Abriendo Radar…</p>
<p id="native-offline" class="native-notice" role="status" hidden>Sin conexión. Puedes revisar la última consulta guardada; para actualizarla necesitas internet.</p>
<p id="native-message" class="native-notice" role="status" hidden></p>`);
html = html.replace('</footer>', `<details id="native-settings"><summary>Soporte, privacidad y datos guardados</summary>
<p>Se conserva el último reporte y el último comparativo en este iPhone. Las búsquedas nuevas requieren internet.</p>
<a href="/support.html">Ayuda y contacto</a><a href="/privacy.html">Privacidad</a></details></footer>`);
html = html.replace('</body>', '<script src="/native.js"></script></body>');
await writeFile(join(out, 'index.html'), html);
await writeFile(join(out, 'app.js'), scripts.join('\n;\n'));
await cp(join(mobile, 'src/mobile.css'), join(out, 'mobile.css'));
for (const page of ['support', 'privacy']) {
  const source = await readFile(join(root, `templates/${page}.html`), 'utf8');
  await writeFile(join(out, `${page}.html`), source.replaceAll('href="/privacy"', 'href="/privacy.html"').replaceAll('href="/support"', 'href="/support.html"').replace('</head>', '<link rel="stylesheet" href="/mobile.css"></head>'));
}
await build({entryPoints: [join(mobile, 'src/main.js')], bundle: true, outfile: join(out, 'native.js'),
  format: 'iife', platform: 'browser', target: 'safari15', minify: true, legalComments: 'eof'});
await writeFile(join(out, 'build-info.json'), JSON.stringify({
  app: config.appName, version: JSON.parse(await readFile(join(mobile, 'package.json'), 'utf8')).version,
  interfaceSHA256: createHash('sha256').update(await readFile(join(root, 'templates/index.html'))).digest('hex')
}, null, 2) + '\n');
console.log('Bundled Radar, Comparativos, directory, native integrations, support and privacy.');
