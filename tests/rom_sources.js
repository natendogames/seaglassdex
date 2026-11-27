'use strict';
// Every gift the app lists must come from the ROM. Run with: node tests/rom_sources.js
// The build (scripts/build_seaglass.py) writes data/verify/rom-sources.json with the ROM script each gift comes from,
// and fails if a hand-added gift has no evidence in the ROM's scripts. This test fails if a gift reaches the app
// without a source, so nothing typed in by hand (like vanilla Emerald's Potion or Running Shoes) can slip back in.
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const src = JSON.parse(fs.readFileSync(path.join(root, 'data/verify/rom-sources.json'), 'utf8'));
let failures = 0, checks = 0;
const ok = (c, m) => { checks++; if (!c) { failures++; console.error('FAIL ' + m); } };
for (const f of fs.readdirSync(path.join(root, 'data/locations'))) {
  const loc = JSON.parse(fs.readFileSync(path.join(root, 'data/locations', f), 'utf8')), id = f.replace(/\.json$/, '');
  for (const g of loc.gifts || []) ok(src[id]?.[g.id], `${id}: gift "${g.name}" (${g.from}) has no ROM source`);
}
// known vanilla leftovers stay out
const all = fs.readdirSync(path.join(root, 'data/locations')).map(f => fs.readFileSync(path.join(root, 'data/locations', f), 'utf8')).join('\n');
ok(!/"name": "Running Shoes"/.test(all), 'no Running Shoes gift (you can run from the start)');
ok(!/"name": "Potion \(in your PC\)"/.test(all), 'no vanilla Potion in the PC');
ok(!fs.existsSync(path.join(root, 'data/locations/roaming.json')), 'no roaming Latias/Latios');
if (failures) { console.error(`${failures} of ${checks} checks failed`); process.exit(1); }
console.log(`rom_sources: ${checks} checks passed`);
