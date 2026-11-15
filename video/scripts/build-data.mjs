// Converts ../demo/data.js (window.UNSWAYED = {...}) into src/data.json so the video
// shows the recorded model output verbatim. Nothing is edited here: fields are copied as they are.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const source = path.resolve(here, '../../demo/data.js');
const target = path.resolve(here, '../src/data.json');

const sandbox = {window: {}};
vm.runInNewContext(fs.readFileSync(source, 'utf8'), sandbox, {filename: source});
const D = sandbox.window.UNSWAYED;
if (!D) throw new Error('window.UNSWAYED not found in ' + source);

const sample = D.samples[0];
const expected = 'GHSA-2hxv-mx8x-mcj9|mal|prior_approval_signal';
if (sample.id !== expected) throw new Error('samples[0] is ' + sample.id + ', expected ' + expected);

const out = {
  recorded: D.recorded,
  reviewer: D.reviewer,
  benchmark: D.benchmark,
  runs: D.runs,
  stats: D.stats,
  sample,
};
fs.writeFileSync(target, JSON.stringify(out, null, 2) + '\n');
console.log('wrote', path.relative(process.cwd(), target), '(' + sample.id + ')');
