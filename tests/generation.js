'use strict';
// Guards against vanilla Emerald (and FireRed/LeafGreen) data leaking into the Seaglass app, which was forked from them.
// Checks the Pokédex is Seaglass's own 430-entry dex (plus its Alolan forms), the either/or picks are Seaglass's,
// every Pokémon you can meet or be given is in Seaglass's dex, every listed item is in Seaglass's item table, and no
// Kanto/Sevii places or people appear in the app's text. Run: node tests/generation.js
const fs = require('fs'), path = require('path');
const { loadApp } = require('./harness');
const ROOT = path.join(__dirname, '..');
const J = f => JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'));
let failures = 0;
const fail = msg => { failures++; console.log('FAIL', msg); };

// FRLG-only key items that Emerald's item table carried for link compatibility
const FRLG_ITEMS = ["Oak's Parcel", 'Poké Flute', 'Secret Key', 'Bike Voucher', 'Gold Teeth', 'Card Key', 'Lift Key', 'Silph Scope',
  'Fame Checker', 'TM Case', 'Berry Pouch', 'Teachy TV', 'Tri-pass', 'Rainbow Pass', 'Tea', 'Ruby', 'Sapphire'];

// Kanto and Sevii places and people. Kanto Pokémon are fine: Seaglass's dex has many of them.
const KANTO = /\b(Pallet|Viridian|Pewter|Cerulean|Vermilion|Lavender Town|Celadon|Saffron|Fuchsia|Cinnabar|Indigo Plateau|Sevii|Prof\.? Oak|Professor Oak|Oak's|Giovanni|Team Rocket|Silph|Lt\. Surge|Sabrina|Blaine|Koga|Lorelei|Agatha|Tanoby|One Island|Two Island|Seafoam|Pokémon Tower)\b/;
// genuine game text that names a Kanto thing
const KANTO_OK = [/A peculiar box made by Silph Co\./, /Pewter Crunchies/];

(async () => {
  const dex = J('data/pokedex.json');
  const byDex = Object.fromEntries(dex.map(p => [p.dex, p])), byName = Object.fromEntries(dex.map(p => [p.name, p]));
  const main = dex.filter(p => p.hoenn).sort((a, b) => a.hoenn - b.hoenn);
  if (main.length !== 430 || main.some((p, i) => p.hoenn !== i + 1 || p.dex !== i + 1)) fail(`Seaglass dex is not numbered 1-430 (${main.length} entries)`);
  if (dex.some(p => !p.hoenn && !p.form)) fail(`Pokémon past #430 that aren't forms: ${dex.filter(p => !p.hoenn && !p.form).map(p => p.name).slice(0, 5)}`);
  // spot checks against Seaglass's own dex order, as read from the ROM
  const expect = { Bulbasaur: 1, Chikorita: 186, Cyndaquil: 189, Totodile: 192, Treecko: 283, Torchic: 286, Mudkip: 289, Latias: 416, Latios: 417 };
  for (const [name, n] of Object.entries(expect)) if (byName[name]?.dex !== n) fail(`${name} is #${byName[name]?.dex}, expected #${n}`);
  if (!dex.some(p => /Alolan/.test(p.name))) fail('no Alolan forms in the dex');
  if (!byName['Fairy'] && !dex.some(p => p.types.includes('Fairy'))) fail('no Fairy-type Pokémon: the Seaglass type list is missing');

  const app = await loadApp(['features.js', 'tools.js', 'trackers.js', 'modes.js']);
  const CHOICES = app.get('CHOICES');
  const opts = id => CHOICES.find(c => c.id === id).options.map(o => o.key).join(',');
  if (opts('starter') !== 'Treecko,Torchic,Mudkip') fail(`starter options are ${opts('starter')}`);
  if (JSON.stringify(app.STARTER_BASE) !== JSON.stringify({ Treecko: 283, Torchic: 286, Mudkip: 289 })) fail(`STARTER_BASE is ${JSON.stringify(app.STARTER_BASE)}`);
  if (opts('fossil') !== 'Root,Claw') fail(`fossil options are ${opts('fossil')}`);
  if (app.get('HOENN_COUNT') !== 430) fail('HOENN_COUNT is not 430');
  if (app.state.dexFilter.scope !== 'hoenn') fail('the Pokédex does not open on the Hoenn dex');
  const plans = Object.keys(J('data/team-plan.json').plans).sort().join(',');
  if (plans !== 'E:Mudkip,E:Torchic,E:Treecko') fail(`team plans are ${plans}`);

  // every Pokémon you can meet, battle or be given
  const seen = new Map();
  const note = (n, where) => { if (!byDex[n]) seen.set(`#${n}`, where); };
  for (const l of J('data/locations.json').locations) {
    const loc = J('data/' + l.file);
    for (const e of loc.encounters || []) note(e.dex, `${loc.id} wild`);
    for (const g of loc.gifts || []) if (g.dex) note(g.dex, `${loc.id} gift ${g.name}`);
    for (const t of loc.trainers || []) {
      for (const m of t.party || []) note(m.dex, `${loc.id} trainer ${t.name}`);
      for (const party of Object.values(t.byStarter || {}).concat(Object.values(t.byStarterBrendan || {}))) for (const m of party || []) note(m.dex, `${loc.id} rival`);
    }
    for (const row of [...(loc.items || []), ...(loc.gifts || [])]) {
      const nm = row.name.replace(/ ×\d+$/, '');
      if (FRLG_ITEMS.includes(nm)) fail(`${loc.id} lists the FRLG item ${row.name}`);
    }
  }
  for (const plan of Object.values(J('data/team-plan.json').plans)) for (const leg of plan.legs) for (const m of leg.team) note(m.dex, 'team plan');
  for (const [name, where] of seen) fail(`${name} (not in Seaglass's dex) appears at ${where}`);

  const items = J('data/items.json');
  for (const it of FRLG_ITEMS) if (items[it]) fail(`items.json has the FRLG-only item ${it}`);
  for (const [loc, shops] of Object.entries(J('data/extras.json').shops)) for (const sh of shops) for (const it of sh.items) if (FRLG_ITEMS.includes(it.name)) fail(`${loc} shop sells ${it.name}`);
  for (const t of J('data/extras.json').tutors || []) if (!t.loc && !t.where) fail(`tutor ${JSON.stringify(t).slice(0, 60)} has no place`);

  // Kanto names in data text and in the app's own strings (comments are skipped)
  const scan = (file, text) => text.split('\n').forEach((line, i) => {
    if (/^\s*(\/\/|#)/.test(line)) return;
    const m = line.match(KANTO);
    if (m && !KANTO_OK.some(re => re.test(line))) fail(`${file}:${i + 1} mentions "${m[0]}": ${line.trim().slice(0, 100)}`);
  });
  const dataFiles = ['data/walkthrough.json', 'data/extras.json', 'data/items.json', 'data/trainers.json', 'data/tms.json', 'data/team-plan.json', 'data/locations.json']
    .concat(J('data/locations.json').locations.map(l => 'data/' + l.file));
  for (const f of dataFiles) scan(f, fs.readFileSync(path.join(ROOT, f), 'utf8'));
  for (const f of ['app.js', 'features.js', 'tools.js', 'trackers.js', 'modes.js', 'map.js', 'catchplan.js', 'saveimport.js', 'index.html', 'manifest.webmanifest']) {
    // drop trailing // comments too, so notes about the sister app don't count
    scan(f, fs.readFileSync(path.join(ROOT, f), 'utf8').split('\n').map(l => l.replace(/\s\/\/ .*$/, '')).join('\n'));
  }

  // Seaglass's new-game PC holds a Shiny Charm (vanilla Emerald's is a Potion)
  const pc = J('data/locations/littleroot-town.json').gifts.filter(g => /in your PC/.test(g.name)).map(g => g.name);
  if (pc.join() !== 'Shiny Charm (in your PC)') fail(`Littleroot bedroom PC should hold a Shiny Charm, got: ${pc.join(', ') || 'nothing'}`);

  if (failures) { console.log(`${failures} generation check(s) failed`); process.exit(1); }
  console.log('Generation checks passed: Seaglass dex, picks, Pokémon, items and text');
})().catch(e => { console.error(e); process.exit(1); });
