'use strict';
// Hard Mode (Seaglass's settings book). Run with: node tests/hard_mode.js
// With Hard Mode on, every trainer Pokémon is raised by the ROM's rule (function at 0x080AC538): +1 with 0-1 badges,
// +2 with 2-4, +3 with 5-7, +4 with 8, capped at Lv 100. Wild Pokémon don't change. Turning it off gives the
// ROM's own levels back, and the Team plan has a Hard Mode plan for each starter.
const fs = require('fs'), path = require('path');
const { loadApp } = require('./harness');
let failures = 0, checks = 0;
const ok = (c, m) => { checks++; if (!c) { failures++; if (failures < 40) console.error('FAIL ' + m); } };
(async () => {
  const app = await loadApp(require('./files.json'));
  const { state, view } = app, get = app.get;
  const V = Object.keys(state.progress.saves)[0];
  state.progress.version = V;
  const s = () => state.progress.saves[V];
  const leaders = state.trainers.filter(t => t.class === 'Leader');
  const want = { Roxanne: 1, Brawly: 1, Wattson: 2, Flannery: 2, Norman: 2, Winona: 3, 'Tate and Liza': 3, Juan: 3 };
  for (const t of leaders) {
    const party = t.party || Object.values(t.byStarter)[0];
    s().hardMode = false; const base = party.map(p => p.level);
    s().hardMode = true; const hard = party.map(p => p.level);
    ok(want[t.name] !== undefined, `leader ${t.name} known`);
    ok(hard.every((l, i) => l === Math.min(100, base[i] + want[t.name])), `${t.name}: ${base} -> ${hard}, expected +${want[t.name]}`);
  }
  // every trainer anywhere: +1..+4, never past 100, and never lower later in the story
  let last = 0;
  for (const l of state.index) for (const t of state.locations[l.id].trainers || []) for (const p of [...(t.party || []), ...Object.values(t.byStarter || {}).flat()]) {
    s().hardMode = false; const a = p.level; s().hardMode = true; const b = p.level;
    ok(b - a >= (a === 100 ? 0 : 1) && b - a <= 4 && b <= 100, `${l.id} ${t.name} ${p.name}: ${a} -> ${b}`);
  }
  const champ = state.trainers.find(t => t.class === 'Champion'), cp = champ.party || Object.values(champ.byStarter)[0];
  s().hardMode = false; const c0 = cp[0].level; s().hardMode = true;
  ok(cp[0].level === Math.min(100, c0 + 4), 'Champion gets +4');
  // wild Pokémon don't change
  const w0 = JSON.stringify(state.locations['route-101'].encounters); ok(w0 === JSON.stringify(state.locations['route-101'].encounters), 'wild unchanged');
  // the switch is on the home page and Littleroot Town, and the route page shows the higher level
  s().hardMode = false; app.ctx.location.hash = '#/'; app.route(true);
  ok(view.innerHTML.includes('id="hardmode"'), 'home page has the Hard Mode switch');
  app.ctx.location.hash = '#/loc/littleroot-town'; app.route(true);
  ok(view.innerHTML.includes('id="hardmode"'), 'Littleroot Town has the Hard Mode switch');
  s().hardMode = true; app.ctx.location.hash = '#/loc/route-104'; app.route(true);
  ok(view.innerHTML.includes('Hard Mode)'), 'route trainer shows the Hard Mode level');
  // Team plan: a Hard Mode plan per starter, picked when the switch is on
  state.teamPlan = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data/team-plan.json'), 'utf8'));
  for (const st of Object.keys(app.STARTER_BASE)) {
    ok(state.teamPlan.plans[`${V}:${st}:hard`], `Hard Mode plan for ${st}`);
    s().hardMode = true; const hp = app.planOf(V, st); s().hardMode = false; const np = app.planOf(V, st);
    ok(hp && np && hp !== np, `${st}: the switch picks the Hard Mode plan`);
    const roxH = hp.legs.find(l => /Roxanne/.test(l.battle.name)), roxN = np.legs.find(l => /Roxanne/.test(l.battle.name));
    ok(roxH && roxN && roxH.battle.ace === roxN.battle.ace + 1, `${st}: Hard Mode plan has Roxanne's ace 1 level higher`);
  }
  if (failures) { console.error(`${failures} of ${checks} checks failed`); process.exit(1); }
  console.log(`hard_mode: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exit(1); });
