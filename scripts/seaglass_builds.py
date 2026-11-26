"""Rework data/builds.json (Smogon's ADV sets, from the Emerald app) for Seaglass.

Seaglass numbers its Pokédex its own way, renames moves, items and abilities the modern way, gives Pokémon new
abilities and learnsets, and adds Alolan forms. This keeps Smogon's sets as a starting point but checks every part
against Seaglass's own data (data/pokedex.json, moves.json, items.json, tms.json, extras.json from the ROM):
- keyed by the Seaglass dex number, matched by name;
- a move option stays only if the Pokémon (or a pre-evolution) learns it in Seaglass: level-up, TM/HM, tutor or egg
  move; an emptied slot is refilled with the strongest legal attack of a type the set doesn't cover yet;
- abilities and items are renamed to Seaglass's spelling; an ability the Pokémon no longer has is swapped for its
  first Seaglass ability;
- Alolan forms and Spiky-eared Pichu get one set built from their own Seaglass moves and stats.
Everything is marked Draft: these are Gen 3 singles sets and Seaglass's mechanics differ (Fairy type, a per-move
physical/special split, new abilities), so a set needs a check before you rely on it.

Run: python3 scripts/seaglass_builds.py data/builds.json data
"""
import json, os, re, sys

src, data = sys.argv[1], sys.argv[2]
J = lambda f: json.load(open(os.path.join(data, f), encoding='utf-8'))
B = json.load(open(src, encoding='utf-8'))
dex = J('pokedex.json'); moves = J('moves.json'); items = J('items.json'); tms = J('tms.json'); extras = J('extras.json')
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
ALIAS = {'faintattack': 'feintattack', 'hijumpkick': 'highjumpkick', 'smellingsalt': 'smellingsalts', 'vicegrip': 'visegrip',
         'compoundeyes': 'compoundeyes', 'lightningrod': 'lightningrod'}
key = lambda s: ALIAS.get(norm(s), norm(s))
MOVE = {key(m): m for m in moves}
ITEM = {key(i): i for i in items}
by_name = {p['name']: p for p in dex}
by_dex = {p['dex']: p for p in dex}
prevo = {}
for p in dex:
    for e in p.get('evolutions') or []:
        prevo.setdefault(e['into'] if isinstance(e.get('into'), int) else by_name.get(e.get('into') or e.get('name'), {}).get('dex'), p['dex'])
tm_move = {k: t['move'] for k, t in tms.items()}
tutor_moves = {t['move'] for t in extras.get('tutors', [])}

def line(p):
    out, d = [], p['dex']
    while d and d not in out:
        out.append(d); d = prevo.get(d)
    return [by_dex[x] for x in out if x in by_dex]

def legal(p):
    """Seaglass move name -> learn letters (L level-up, M TM/HM, T tutor, E egg)."""
    got = {}
    for q in line(p):
        for _, m in q.get('learnset') or []: got.setdefault(m, set()).add('L')
        for t in q.get('tmhm') or []:
            if t in tm_move: got.setdefault(tm_move[t], set()).add('M')
        for m in q.get('tutor') or []:
            if m in tutor_moves: got.setdefault(m, set()).add('T')
        for m in q.get('eggMoves') or []: got.setdefault(m, set()).add('E')
    if p['name'] == 'Smeargle':  # Sketch copies any move it sees (K)
        for m, i in moves.items():
            if m not in ('Struggle', 'Chatter') and not m.startswith('Max ') and not m.endswith(' Z'): got.setdefault(m, set()).add('K')
    return {m: ''.join(sorted(v)) for m, v in got.items()}

def power(m):
    i = moves.get(m) or {}
    return (i.get('power') or 0) * ((i.get('accuracy') or i.get('acc') or 100) / 100)

def best_attacks(p, learn, avoid_types=(), n=4):
    phys = p['stats'][1] >= p['stats'][3]
    scored = []
    for m in learn:
        i = moves.get(m) or {}
        if not i.get('power') or i.get('power', 0) < 40 or m in ('Explosion', 'Self-Destruct', 'Hyper Beam', 'Giga Impact', 'Focus Punch'): continue
        cat = i.get('category')
        fit = 1.0 if cat == ('physical' if phys else 'special') or cat is None else 0.6
        stab = 1.5 if i.get('type') in p['types'] else 1.0
        scored.append((power(m) * stab * fit, m, i.get('type')))
    out, seen = [], set(avoid_types)
    for sc, m, ty in sorted(scored, reverse=True):
        if ty in seen: continue
        out.append(m); seen.add(ty)
        if len(out) == n: break
    return out

def rework_set(p, st, learn, abilities):
    st = dict(st, draft=True)
    slots, used = [], set()
    for slot in st['moves']:
        keep = []
        for mv in slot:
            base = 'Hidden Power' if mv.startswith('Hidden Power') else mv
            sg = MOVE.get(key(base))
            if sg and sg in learn and sg not in used:
                keep.append(mv if base == 'Hidden Power' else sg)
        if keep: slots.append(keep); used.update('Hidden Power' if k.startswith('Hidden Power') else k for k in keep)
    have_types = {(moves.get(s[0]) or {}).get('type') for s in slots}
    for m in best_attacks(p, [m for m in learn if m not in used], have_types, 4 - len(slots)):
        slots.append([m]); used.add(m)
    st['moves'] = slots[:4]
    hp_kept = {m[13:] for s in st['moves'] for m in s if m.startswith('Hidden Power ')}
    if st.get('hiddenPower'): st['hiddenPower'] = {k: v for k, v in st['hiddenPower'].items() if k in hp_kept}
    st['items'] = [ITEM[key(i)] for i in st['items'] if key(i) in ITEM] or (['Leftovers'] if 'Leftovers' in items else [])
    ab = [a for a in (next((x for x in abilities if key(x) == key(a)), None) for a in st['abilities']) if a]
    st['abilities'] = ab or abilities[:1]
    return st

out = {}
for p in dex:
    abilities = (p.get('abilities') or []) + ([p['hiddenAbility']] if p.get('hiddenAbility') else [])
    learn = legal(p)
    if 'Hidden Power' in learn: learn['Hidden Power'] = learn['Hidden Power']
    old = None
    for k, entries in B['species'].items():
        if entries and entries[0]['name'].split('-')[0] in (p['name'], p['name'].replace('♀', '-F').replace('♂', '-M')):
            old = entries; break
    if old and not p.get('form'):
        new = []
        for e in old:
            sets = [rework_set(p, st, learn, abilities) for st in e['sets']]
            new.append(dict(e, draft=True, sets=sets, learn={m: v for m, v in learn.items()}))
        out[str(p['dex'])] = new
    else:
        mv = best_attacks(p, list(learn), (), 4)
        phys = p['stats'][1] >= p['stats'][3]
        st = {'format': 'ingame', 'name': 'Seaglass attacker', 'level': 100, 'draft': True, 'moves': [[m] for m in mv],
              'items': ['Leftovers'] if 'Leftovers' in items else [], 'abilities': abilities[:1],
              'natures': ['Adamant' if phys else 'Modest'], 'evs': [4, 252, 0, 0, 0, 252] if phys else [4, 0, 0, 252, 0, 252]}
        if p['stats'][5] < 50: st['evs'] = [252, 252, 4, 0, 0, 0] if phys else [252, 0, 4, 252, 0, 0]; st['natures'] = ['Brave' if phys else 'Quiet']
        out[str(p['dex'])] = [{'name': p['name'], 'smogon': None, 'draft': True, 'sets': [st], 'learn': learn}]
B['species'] = out
B['about'] = ("Starting points from Smogon's ADV (Gen 3) strategy dex (smogon.com/dex/rs), reworked for Seaglass by "
              "scripts/seaglass_builds.py: every move, ability and item was checked against Seaglass's own data, and illegal ones "
              "swapped out. All sets are Draft: Seaglass's mechanics (Fairy type, per-move physical/special split, new abilities) "
              "differ from Gen 3 singles, so check a set before relying on it.")
json.dump(B, open(os.path.join(data, 'builds.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(len(out), 'Pokémon;', sum(len(st['sets']) for e in out.values() for st in e), 'sets')
