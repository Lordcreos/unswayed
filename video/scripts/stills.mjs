// Bundles once and renders the given frames as PNG stills into out/stills/ (for visual checks).
// Usage: node scripts/stills.mjs 60 300 520 ...
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const frames = process.argv.slice(2).map(Number);
const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.ts'), publicDir: path.join(root, 'public')});
const composition = await selectComposition({serveUrl, id: 'UnswayedDemo'});
for (const frame of frames) {
  const output = path.join(root, 'out/stills', 'f' + String(frame).padStart(4, '0') + '.png');
  await renderStill({composition, serveUrl, output, frame});
  console.log(output);
}
