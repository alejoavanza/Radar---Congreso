import {readFile, writeFile, mkdir, readdir, rm} from 'node:fs/promises';
import {dirname, resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';

const mobile = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const res = join(mobile, 'android/app/src/main/res');
// Derive Android sizes from the existing approved artwork; never regenerate iOS assets.
const logo = await readFile(join(mobile, '../static/icons/radar-politico-512-v1.png'));
for (const [density, scale] of Object.entries({mdpi:1, hdpi:1.5, xhdpi:2, xxhdpi:3, xxxhdpi:4})) {
  const dir = join(res, 'mipmap-'+density);
  await mkdir(dir, {recursive:true});
  for (const name of ['ic_launcher', 'ic_launcher_round']) {
    await sharp(logo).resize(48*scale, 48*scale).png().toFile(join(dir, name+'.png'));
  }
  const inset = Math.floor(21*scale), oppositeInset = Math.ceil(21*scale);
  await sharp(logo).resize(66*scale,66*scale)
    .extend({top:inset,bottom:oppositeInset,left:inset,right:oppositeInset,background:'#075056'})
    .png().toFile(join(dir, 'ic_launcher_foreground.png'));
}
const adaptive = '<?xml version="1.0" encoding="utf-8"?>\n<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@color/ic_launcher_background"/><foreground android:drawable="@mipmap/ic_launcher_foreground"/></adaptive-icon>\n';
for (const name of ['ic_launcher','ic_launcher_round']) await writeFile(join(res,'mipmap-anydpi-v26',name+'.xml'), adaptive);
await writeFile(join(res,'values/ic_launcher_background.xml'), '<?xml version="1.0" encoding="utf-8"?>\n<resources><color name="ic_launcher_background">#075056</color></resources>\n');
// Replace Capacitor's placeholder splash images with one density-independent layer list.
for (const dir of await readdir(res)) {
  if (dir.startsWith('drawable')) await rm(join(res,dir,'splash.png'), {force:true});
}
await rm(join(res,'drawable-v24/ic_launcher_foreground.xml'), {force:true});
await rm(join(res,'drawable/ic_launcher_background.xml'), {force:true});
await mkdir(join(res,'drawable-nodpi'),{recursive:true});
await sharp(logo).resize(288,288).png().toFile(join(res,'drawable-nodpi/radar_splash.png'));
await writeFile(join(res,'drawable/splash.xml'), '<?xml version="1.0" encoding="utf-8"?>\n<layer-list xmlns:android="http://schemas.android.com/apk/res/android"><item android:drawable="@color/radar_canvas"/><item android:gravity="center" android:width="160dp" android:height="160dp" android:drawable="@drawable/radar_splash"/></layer-list>\n');
console.log('Exported Android icons and splash from the existing Radar artwork.');
