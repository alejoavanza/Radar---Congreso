import {readFile, writeFile, mkdir, cp} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname, resolve} from 'node:path';
import sharp from 'sharp';

const mobile = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const assets = resolve(mobile, 'ios/App/App/Assets.xcassets');
// Export the existing vector logo; flatten its canvas onto the brand colour.
await sharp(await readFile(resolve(mobile, '../static/radar-icon.svg')), {density: 144})
  .resize(1024, 1024).flatten({background: '#075056'}).removeAlpha().png()
  .toFile(resolve(assets, 'AppIcon.appiconset/AppIcon-512@2x.png'));
await mkdir(resolve(assets, 'BrandMark.imageset'), {recursive: true});
await cp(resolve(mobile, '../static/icons/radar-politico-512-v1.png'), resolve(assets, 'BrandMark.imageset/radar.png'));
await writeFile(resolve(assets, 'BrandMark.imageset/Contents.json'), JSON.stringify({
  images: [{filename: 'radar.png', idiom: 'universal'}], info: {author: 'xcode', version: 1}
}, null, 2) + '\n');
console.log('Exported the existing Radar logo as an opaque 1024 × 1024 iOS icon.');
