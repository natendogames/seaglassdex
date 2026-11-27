"""Build Seaglass Completion Dex data files from Pokémon Emerald Seaglass 3.0.

Usage: python3 -I build_seaglass.py <seaglass-src-dir> <app-data-dir>

<seaglass-src-dir> is the pokeemerald-shaped tree that tools/make_src.py writes from the ROM dumps: maps, scripts,
layouts, tilesets and wild encounters in decomp layout, plus seaglass/tables.json (species, moves, items, trainers,
trades, rematches, type chart) read straight out of the patched ROM. Seaglass is built on pokeemerald-expansion 1.9,
so moves have their own physical/special category, Fairy is a type, Pokémon have up to three abilities and the
Pokédex follows Seaglass's own numbering (Gen 1-3 plus cross-generation evolutions, 430 entries) with Alolan forms
and Spiky-eared Pichu as extra entries.
"""
import json, re, sys, os, glob, collections

SRC, OUT = sys.argv[1], sys.argv[2]
P = lambda *a: os.path.join(SRC, *a)
SOURCE_URL = 'https://mrwalkthroughs.com/pokemon-emerald-seaglass/'
read = lambda *a: open(P(*a), encoding='utf-8').read()
TB = json.load(open(P('seaglass/tables.json')))

def title(s):
    s = s.replace('POKéMON', 'Pokémon').replace('POKé', 'Poké')
    return ' '.join(w if w in ('Pokémon', 'TM', 'HM', 'PP', 'HP', 'S.S.', 'SS', 'TV', 'PC') or re.match(r'^(TM|HM)\d+$', w) else w.capitalize()
                    for w in s.split(' '))

# ---------- names ----------
# Pokédex numbers come from the ROM (Seaglass's own order). Forms that only change looks share their base entry;
# Alolan forms and Spiky-eared Pichu are real extra Pokémon (Pinball egg prizes, Professor Elm) and get their own rows.
FORM_NAME = {'ALOLAN': 'Alolan {}', 'SPIKY_EARED': 'Spiky-eared {}'}
species_rec = {s['const']: s for s in TB['species']}
base_of_dex = {}
for s in sorted(TB['species'], key=lambda s: s['id']):
    base_of_dex.setdefault(s['dex'], s['const'])
EXTRA_FORMS = [s['const'] for s in sorted(TB['species'], key=lambda s: (s['dex'], s['id']))
               if s['const'] != base_of_dex[s['dex']] and re.search(r'_(ALOLAN|SPIKY_EARED)$', s['const'])]
natdex, species_const = {}, {}
MAX_DEX = max(base_of_dex)
for s in TB['species']:
    k = s['const']
    natdex[k] = s['dex']; species_const[k] = s['name']
for i, k in enumerate(EXTRA_FORMS):
    natdex[k] = MAX_DEX + 1 + i
    form = next(f for f in FORM_NAME if k.endswith(f))
    species_const[k] = FORM_NAME[form].format(species_rec[k]['name'])
hoenn = {}
FORM_OF = {natdex[k]: natdex[base_of_dex[species_rec[k]['dex']]] for k in EXTRA_FORMS}

def mon(const):
    key = const.replace('SPECIES_', '')
    return {'dex': natdex[key], 'name': species_const[key]}

# items
items = TB['items']
ITEM_FIX = {'ITEM_POKEMON_BOX_LINK': 'Pokémon Box Link', 'ITEM_POKEBLOCK_CASE': 'Pokéblock Case'}
def item_name(c):
    if c in ITEM_FIX: return ITEM_FIX[c]
    if c in items and items[c]['english'] and '?' not in items[c]['english']: return items[c]['english']
    return title(c.replace('ITEM_', '').replace('_', ' '))
TM_ITEM = {c: i['english'] for c, i in items.items() if i['pocket'] == 'POCKET_TM_HM' and re.match(r'^(TM|HM)\d+$', i['english'])}

# moves: Seaglass (expansion) stores the physical/special split per move
MV = TB['moves']
move_names = {k: v['name'] for k, v in MV.items()}
move_types = {k: v['type'] for k, v in MV.items() if v['type']}
move_power = {k: v['power'] for k, v in MV.items() if v['power']}
move_effects = {k: v['effect'] for k, v in MV.items()}
move_cat = {k: v['category'] for k, v in MV.items()}

# ---------- pokedex ----------
info = {}
GENDER = lambda g: 'genderless' if g == 255 else 'male' if g == 0 else 'female' if g == 254 else f'{round(g * 100 / 256, 1):g}% F'
for k, s in species_rec.items():
    info[k] = {'types': s['types'], 'eggGroups': s['eggGroups'], 'gender': GENDER(s['gender']), 'eggCycles': s['eggCycles']}

def evo_param(method, p):
    if 'ITEM' in method: return item_name(items_by_id.get(p, f'ITEM_{p}'))
    if method in ('MOVE',): return move_names.get(moves_by_num.get(p), p)
    if method in ('SPECIFIC_MON_IN_PARTY', 'TRADE_SPECIFIC_MON'): return species_const.get(species_by_num.get(p), p)
    if method in ('FRIENDSHIP_MOVE_TYPE',): return ['None', 'Normal', 'Fighting', 'Flying', 'Poison', 'Ground', 'Rock', 'Bug', 'Ghost', 'Steel', 'Mystery', 'Fire', 'Water', 'Grass', 'Electric', 'Psychic', 'Ice', 'Dragon', 'Dark', 'Fairy'][p]
    return p
items_by_id = {i['id']: c for c, i in items.items()}
moves_by_num = {v['id']: k for k, v in MV.items()}
species_by_num = {s['id']: s['const'] for s in TB['species']}
evos = collections.defaultdict(list)
for k, s in species_rec.items():
    for e in s['evos']:
        if e['into'] not in natdex: continue
        evos[k].append({'method': e['method'].lower().replace('_', '-'), 'param': evo_param(e['method'], e['param']), 'into': natdex[e['into']]})

dex_key = {}
for d, k in base_of_dex.items(): dex_key[d] = k
for k in EXTRA_FORMS: dex_key[natdex[k]] = k
pokedex = []
for dex in sorted(dex_key):
    if dex == 0: continue
    key = dex_key[dex]; i = info.get(key, {}); s = species_rec[key]
    st = s['stats']  # HP Atk Def Spe SpA SpD
    pokedex.append({'dex': dex, 'name': species_const[key], 'types': i.get('types'),
                    'stats': [st[0], st[1], st[2], st[4], st[5], st[3]],
                    'eggGroups': i.get('eggGroups'), 'gender': i.get('gender'), 'eggCycles': i.get('eggCycles'),
                    'evolutions': evos.get(key, []),
                    **({'hoenn': dex} if dex <= MAX_DEX else {}),  # the in-game Seaglass dex (430); forms come after it
                    **({'form': True, 'baseDex': FORM_OF[dex]} if dex in FORM_OF else {}),
                    **({'legendary': True} if s['legendary'] else {})})
prevo = {}
for p in pokedex:
    for e in p['evolutions']: prevo.setdefault(e['into'], p['dex'])
for p in pokedex:
    if p['dex'] in prevo: p['evolvesFrom'] = prevo[p['dex']]

# ---------- type chart (read from the ROM: Gen 6 Fairy chart, but Ghost and Dark stay not very effective on Steel) ----------
type_chart = collections.defaultdict(dict)
for a, row in TB['typeChart'].items():
    for d, mul in row.items(): type_chart[a][d] = mul

# ---------- locations ----------
mapsec_name = {s['id']: s.get('name') for s in json.load(open(P('src/data/region_map/region_map_sections.json')))['map_sections']}
maps = {}
for f in glob.glob(P('data/maps/*/map.json')):
    m = json.load(open(f)); m['_dir'] = os.path.dirname(f)
    if re.search(r'Unused|Prototype', m['name']): continue
    maps[m['name']] = m
by_const = {m['id']: m for m in maps.values()}

SKIP = {'MAPSEC_DYNAMIC', 'MAPSEC_SECRET_BASE', 'MAPSEC_TRAINER_HILL', 'MAPSEC_NONE'}
LEAGUE_MAPS = re.compile(r'^EverGrandeCity_(\w+sRoom|Hall\d|HallOfFame|PokemonLeague_\w+)$')
# The Battle Frontier and Battle Tents run their own randomised battles; only their gifts and items are listed.
NO_TRAINERS = re.compile(r'^BattleFrontier_|BattleTent|^TrainerHill')

def map_loc(mapname):
    """App location id for a map. Underwater maps belong to the route or place above them; the League is its own place."""
    if LEAGUE_MAPS.match(mapname): return 'pokemon-league'
    if mapname == 'InsideOfTruck': return 'littleroot-town'
    if mapname.startswith('SSTidal'): return 'ss-tidal'
    m = re.match(r'Underwater_Route(\d+)$', mapname)
    if m: return f'route-{m.group(1)}'
    sec = maps[mapname]['region_map_section']
    fixed = {'MAPSEC_UNDERWATER_SEAFLOOR_CAVERN': 'seafloor-cavern', 'MAPSEC_UNDERWATER_SEALED_CHAMBER': 'sealed-chamber',
             'MAPSEC_UNDERWATER_MARINE_CAVE': 'marine-cave', 'MAPSEC_UNDERWATER_SOOTOPOLIS': 'sootopolis-city'}
    if sec in fixed: return fixed[sec]
    return sec.replace('MAPSEC_', '').lower().replace('_', '-')

def map_skipped(mapname):
    return maps[mapname]['region_map_section'] in SKIP and not mapname.startswith('SSTidal')

def area_name(map_name):
    """Human name for a sub-map, e.g. GraniteCave_B1F -> 'B1F', RustboroCity_Gym -> 'Gym'."""
    if map_name.startswith('Underwater_'): return 'Underwater'
    if map_name == 'InsideOfTruck': return 'Moving truck'
    parts = map_name.split('_')
    words = [re.sub(r'(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Z][a-z])', ' ', p) for p in parts[1:]] if len(parts) > 1 else []
    s = ' '.join(words).replace('Pokemon', 'Pokémon')
    s = re.sub(r'\b(B?\d) F\b', r'\1F', s)
    # possessives the map names drop: CuttersHouse -> Cutter's House (Stevens -> Steven's)
    s = re.sub(r"\b(Cutter|Cozmo|Berry Master|Brendan|May|Fossil Maniac|Scott|Steven|Wally|Winstrate Family|Captain|Champion|Drake|Glacia|Phoebe|Sidney|Professor Birch|Mr Briney|Lanette|Rydel)s\b(?= (House|Lab|Room|Office|Cottage|Cycles))", r"\1's", s)
    return s or 'Outside'

NAME_FIX = {'ss-tidal': 'S.S. Tidal', 'pokemon-league': 'Pokémon League', 'mt-chimney': 'Mt. Chimney', 'mt-pyre': 'Mt. Pyre',
            'sealed-chamber': 'Sealed Chamber', 'marine-cave': 'Marine Cave', 'seafloor-cavern': 'Seafloor Cavern', 'roaming': 'Roaming Legendary'}
locs = {}
def L(lid):
    if lid not in locs:
        sec = 'MAPSEC_' + lid.upper().replace('-', '_')
        nm = NAME_FIX.get(lid) or title(mapsec_name.get(sec) or lid.replace('-', ' ').upper())
        locs[lid] = {'id': lid, 'name': nm, 'encounters': [], 'items': [], 'gifts': [], '_enc': {}}
    return locs[lid]

# wild encounters. Emerald fills extra tables for Altering Cave that only Mystery Events switch on, so only the first counts.
we = json.load(open(P('src/data/wild_encounters.json')))['wild_encounter_groups'][0]
rates = {f['type']: f for f in we['fields']}
ROD = {'old_rod': 'old-rod', 'good_rod': 'good-rod', 'super_rod': 'super-rod'}
SG_TYPES = {'SPECIES_' + x['const'].replace('SPECIES_', ''): tuple('TYPE_' + t.upper() for t in x['types']) for x in TB['species']}
METH = {'land_mons': 'grass', 'water_mons': 'surf', 'rock_smash_mons': 'rock-smash', 'hidden_mons': 'dexnav'}
# Parts of a place you can only reach later than your first visit: location id that opens them, and why.
AREA_AFTER = {
    ('route-111', 'grass'): ('lavaridge-town', 'The desert needs the Go-Goggles from your rival in Lavaridge Town.'),
    'MirageTower_1F': ('lavaridge-town', 'In the desert (Go-Goggles from Lavaridge Town). Gone once you take a fossil.'),
    'MirageTower_2F': ('lavaridge-town', 'Needs the Mach Bike.'), 'MirageTower_3F': ('lavaridge-town', 'Needs Rock Smash and the Mach Bike.'),
    'MirageTower_4F': ('lavaridge-town', 'Needs Rock Smash and the Mach Bike.'),
    'SafariZone_Northeast': ('pokemon-league', 'Safari Zone expansion: opens after you enter the Hall of Fame.'),
    'SafariZone_Southeast': ('pokemon-league', 'Safari Zone expansion: opens after you enter the Hall of Fame.'),
    'MeteorFalls_1F_2R': ('ever-grande-city', 'Needs Waterfall.'), 'MeteorFalls_B1F_1R': ('ever-grande-city', 'Needs Waterfall.'),
    'MeteorFalls_B1F_2R': ('ever-grande-city', 'Needs Waterfall.'),
    'AbandonedShip_HiddenFloorCorridors': ('seafloor-cavern', 'Below deck: needs Dive.'),
}
NOTES_FOR = {('route-130', 'grass'): 'Mirage Island only: it appears on random days.'}
for e in we['encounters']:
    if re.search(r'AlteringCave[2-9]|Unused', e['base_label']): continue
    m = by_const.get(e['map'])
    if not m or m['name'] not in maps or map_skipped(m['name']): continue
    lid = map_loc(m['name']); loc = L(lid)
    area = area_name(m['name'])
    under = m['name'].startswith('Underwater_')
    scuba = 'ScubaSafari' in m['name']
    for field, data in e.items():
        if not field.endswith('_mons'): continue
        slots = data['mons']; r = rates[field]['encounter_rates']
        if field == 'hidden_mons': r = [round(100 / len(slots))] * len(slots)  # DexNav: hidden Pokémon you search for, any slot
        for idx, slot in enumerate(slots):
            method = 'dive' if under and field == 'water_mons' else 'scuba' if scuba else METH.get(field)
            if field == 'hidden_mons':  # DexNav finds water Pokémon only while you surf
                land = {x['species'] for x in (e.get('land_mons') or {}).get('mons', [])}
                wet = {x['species'] for f_ in ('water_mons', 'fishing_mons') for x in (e.get(f_) or {}).get('mons', [])}
                if slot['species'] not in land and (slot['species'] in wet or not land or 'TYPE_WATER' in SG_TYPES.get(slot['species'], ())): method = 'dexnav-surf'
            if field == 'fishing_mons':
                method = next(ROD[k] for k, v in rates[field]['groups'].items() if idx in v)
            sp = slot['species'].replace('SPECIES_', '')
            key = (area, method, sp, m['name'])
            agg = loc['_enc'].setdefault(key, {'rate': 0, 'min': 999, 'max': 0})
            agg['rate'] += r[idx]; agg['min'] = min(agg['min'], slot['min_level']); agg['max'] = max(agg['max'], slot['max_level'])

# item balls
balls = {}
cur = None
for line in open(P('data/scripts/item_ball_scripts.inc')):
    m = re.match(r'(\w+)::', line)
    if m: cur = m.group(1)
    m = re.match(r'\s*finditem (ITEM_\w+)(?:,\s*(\d+))?', line)
    if m and cur: balls[cur] = (m.group(1), int(m.group(2) or 1))

item_flags = {}  # checklist key -> the save flag set when you pick it up (for save file import)
item_pos = {}  # (location id, item id) -> where it sits on the map, for the reachability walk
def add_item(loc, name, qty, hidden, where, ident, flag=None, pos=None):
    loc['items'].append({'id': ident, 'name': name + (f' ×{qty}' if qty > 1 else ''), 'hidden': hidden, 'where': where})
    if pos: item_pos[(loc['id'], ident)] = pos
    if flag: item_flags[f"{loc['id']}:item:{ident}"] = flag

seen_ids = collections.Counter()
def uid(loc, base):
    base = re.sub(r'[^a-z0-9]+', '-', base.lower()).strip('-')
    seen_ids[(loc['id'], base)] += 1
    c = seen_ids[(loc['id'], base)]
    return base if c == 1 else f'{base}-{c}'

for name in sorted(maps):
    m = maps[name]
    if map_skipped(name): continue
    loc = L(map_loc(name)); area = area_name(name)
    for ev in m.get('object_events') or []:
        if ev.get('script') in balls:
            it, q = balls[ev['script']]
            add_item(loc, item_name(it), q, False, area, uid(loc, f'{area}-{item_name(it)}'), ev.get('flag'), (name, ev['x'], ev['y'], ev.get('elevation') or 0, False))
    for ev in m.get('bg_events') or []:
        if ev.get('type') == 'hidden_item':
            add_item(loc, item_name(ev['item']), int(ev.get('quantity') or 1), True,
                     area + (' (underfoot)' if ev.get('underfoot') else ''), uid(loc, f'hidden-{area}-{item_name(ev["item"])}'), ev.get('flag'),
                     (name, ev['x'], ev['y'], ev.get('elevation') or 0, bool(ev.get('underfoot'))))

# NPC gifts, static encounters, trades
trades = {}
for t in TB['trades']:
    trades[t['const']] = (t['species'], t['requested'], t['nick'])

LEADERS = {'RustboroCity_Gym': 'Roxanne', 'DewfordTown_Gym': 'Brawly', 'MauvilleCity_Gym': 'Wattson', 'LavaridgeTown_Gym_1F': 'Flannery',
           'PetalburgCity_Gym': 'Norman', 'FortreeCity_Gym': 'Winona', 'MossdeepCity_Gym': 'Tate and Liza', 'SootopolisCity_Gym_1F': 'Juan'}
GFX_WHO = {'MAN_1': 'Man', 'MAN_2': 'Man', 'MAN_3': 'Man', 'MAN_4': 'Man', 'MAN_5': 'Man', 'WOMAN_1': 'Woman', 'WOMAN_2': 'Woman', 'WOMAN_3': 'Woman',
           'WOMAN_4': 'Woman', 'WOMAN_5': 'Woman', 'OLD_MAN': 'Old man', 'OLD_WOMAN': 'Old woman', 'BOY_1': 'Boy', 'BOY_2': 'Boy', 'BOY_3': 'Boy',
           'GIRL_1': 'Girl', 'GIRL_2': 'Girl', 'GIRL_3': 'Girl', 'LITTLE_BOY': 'Little boy', 'LITTLE_GIRL': 'Little girl', 'FAT_MAN': 'Fat man',
           'GENTLEMAN': 'Gentleman', 'SCIENTIST_1': 'Scientist', 'SCIENTIST_2': 'Scientist', 'MART_EMPLOYEE': 'Clerk', 'NURSE': 'Nurse',
           'PROF_BIRCH': 'Professor Birch', 'MOM': 'Mom', 'STEVEN': 'Steven', 'WALLACE': 'Wallace', 'WALLY': 'Wally', 'MR_BRINEY': 'Mr. Briney',
           'AQUA_MEMBER_M': 'Aqua Grunt', 'AQUA_MEMBER_F': 'Aqua Grunt', 'MAGMA_MEMBER_M': 'Magma Grunt', 'MAGMA_MEMBER_F': 'Magma Grunt',
           'ITEM_BALL': 'On the ground', 'EXPERT_F': 'Old woman', 'EXPERT_M': 'Old man', 'COOK': 'Cook', 'SAILOR': 'Sailor', 'HIKER': 'Hiker'}
def npc_of(label, mapname):
    m = maps.get(mapname) or {}
    evs = m.get('object_events') or []
    def reaches(start, depth=6):
        seen, todo = set(), [start]
        for _ in range(depth):
            nxt = []
            for l_ in todo:
                if l_ == label: return True
                if l_ in seen or l_ not in labels_raw: continue
                seen.add(l_); nxt += re.findall(r'\b(\w+_EventScript_\w+)\b', labels_raw[l_])
            todo = nxt
        return label in todo
    hit = [e for e in evs if e.get('script') == label] or [e for e in evs if e.get('script') and reaches(e['script'])]
    if not hit: return None
    g = hit[0]['graphics_id'].replace('OBJ_EVENT_GFX_', '')
    return GFX_WHO.get(g) or g.replace('_', ' ').capitalize().replace(' 1', '').replace(' 2', '').replace(' 3', '')
labels_raw = {}
for f_ in glob.glob(P('data/maps/*/scripts.inc')):
    for l_, b_ in re.findall(r'^(\w+)::\n(.*?)(?=^\w+:|\Z)', open(f_, encoding='utf-8').read(), re.S | re.M): labels_raw[l_] = b_
def who(label, mapname):
    if mapname in LEADERS: return LEADERS[mapname] + ' (after winning)'
    if re.search(r'_EventScript_[0-9A-F]{7}$', label):
        return npc_of(label, mapname) or 'Someone here'
    s = label.split('EventScript_')[-1] if 'EventScript_' in label else label
    s = re.sub(r'(?<=[a-z])(?=[A-Z0-9])', ' ', s)
    return s

gifts = collections.OrderedDict()  # (lid, kind, name, area, from, species?) -> True
gift_src = {}  # gift key -> (map, script label) it comes from, to find the giver on the map
gift_pos = {}  # (location id, gift id) -> (map, script label)
def add_gift(k, name, label):
    gifts.setdefault(k, True); gift_src.setdefault(k, (name, label))
statics = collections.OrderedDict()
for name in sorted(maps):
    m = maps[name]
    if map_skipped(name) or name == 'Route110_TrickHouseEntrance': continue  # the entrance only re-offers Trick House prizes your bag had no room for
    f = os.path.join(m['_dir'], 'scripts.inc')
    if not os.path.exists(f): continue
    lid = map_loc(name); area = area_name(name)
    label = ''
    for line in open(f, encoding='utf-8'):
        lm = re.match(r'(\w+)::', line)
        if lm: label = lm.group(1); continue
        s = line.strip()
        gm = re.match(r'(?:giveitem|giveitem_msg)\s+(ITEM_\w+)(?:,\s*(\d+))?', s)
        if gm:
            it, q = gm.group(1), int(gm.group(2) or 1)
            nm = item_name(it) + (f' ×{q}' if q > 1 else '')
            add_gift((lid, 'item', nm, area, who(label, name)), name, label); continue
        mm = re.match(r'givemon SPECIES_(\w+), (\d+)', s)
        if mm:
            add_gift((lid, 'mon', f'{species_const[mm.group(1)]} (Lv {mm.group(2)})', area, who(label, name), mm.group(1)), name, label); continue
        mm = re.match(r'giveegg SPECIES_(\w+)', s)
        if mm:
            add_gift((lid, 'mon', f'{species_const[mm.group(1)]} Egg', area, who(label, name), mm.group(1)), name, label); continue
        mm = re.match(r'(?:setwildbattle|seteventmon) SPECIES_(\w+), (\d+)', s)
        if mm:
            statics.setdefault((lid, area, mm.group(1), mm.group(2)), True); continue
        mm = re.match(r'setvar VAR_0x8008, (INGAME_TRADE_\w+)', s)
        if mm:
            get, give, nick = trades[mm.group(1)]
            add_gift((lid, 'trade', f'Trade: give {species_const[give]}, get {species_const[get]} ("{title(nick)}")', area, who(label, name), get), name, label)
# Seaglass: a sailor in the Game Corner hands out a random Alolan egg for 2 Pinball points (giveegg VAR_RESULT after a
# random pick of setorcopyvar VAR_RESULT, <species id>)
SP_BY_ID = {x['id']: x['const'].replace('SPECIES_', '') for x in TB['species']}
RANDOM_EGGS = []  # (location id, area, [species consts])
for name in sorted(maps):
    f = os.path.join(maps[name]['_dir'], 'scripts.inc')
    if map_skipped(name) or not os.path.exists(f): continue
    txt = open(f, encoding='utf-8').read()
    if 'giveegg VAR_RESULT' not in txt: continue
    pool = [SP_BY_ID[int(n)] for n in re.findall(r'setorcopyvar VAR_RESULT, (\d+)', txt) if SP_BY_ID.get(int(n), '').endswith('_ALOLAN')]
    if not pool: continue
    lid = map_loc(name); area = area_name(name)
    RANDOM_EGGS.append((lid, area, pool))
    add_gift((lid, 'mon', f'Alolan Egg (random: one of {len(pool)})', area, 'Sailor (2 Pinball points per egg)'), name, '')
# Kecleon hiding on Routes 119 and 120 share one script in data/scripts/kecleon.inc
for lid in ('route-119', 'route-120'):
    statics.setdefault((lid, 'Outside', 'KECLEON', '30'), True)

EXTRA_GIFTS = [
    ('route-101', 'mon', 'Starter Pokémon (Treecko, Torchic or Mudkip)', 'Outside', "Professor Birch's bag", None),
    ('littleroot-town', 'item', 'Pokédex', "Professor Birch's Lab", 'Professor Birch (after your first rival battle)', None),
    # Seaglass's new-game PC holds a Shiny Charm, not vanilla's Potion: the ROM has no {Potion, 1} PC item table,
    # and {ITEM_SHINY_CHARM (691), 1}, {ITEM_NONE, 0} sits at 0x6bb92c
    ('littleroot-town', 'item', 'Shiny Charm (in your PC)', 'Your house 2F', 'Your bedroom PC', None),
    # gifts from shared scripts (data/scripts/*.inc), which the map pass doesn't see
    ('littleroot-town', 'item', 'Running Shoes', 'Outside', 'Mom (as you leave with the Pokédex)', None),
    ('littleroot-town', 'item', 'Amulet Coin', 'Your house 1F', "Mom (once you have Dad's badge, the fifth)", None),
    ('littleroot-town', 'item', 'S.S. Ticket', 'Your house 1F', 'Dad (after you enter the Hall of Fame)', None),
    ('lilycove-city', 'item', 'Pokéblock Case', 'Contest Lobby', 'Contest receptionist', None),
    ('route-111', 'item', 'TM43', 'Outside', 'Boy by the Secret Base tree', None),
    ('rustboro-city', 'item', 'PokéNav', 'Devon Corp 3F', 'Mr. Stone (return the Devon Goods)', None),
]
for k in EXTRA_GIFTS: gifts[k] = True
FROM_FIX = {'Give Red Scarf': 'Fan Club chairman (lead Pokémon with high Cool)', 'Give Blue Scarf': 'Fan Club chairman (lead Pokémon with high Beauty)',
    'Give Pink Scarf': 'Fan Club chairman (lead Pokémon with high Cute)', 'Give Green Scarf': 'Fan Club chairman (lead Pokémon with high Smart)',
    'Give Yellow Scarf': 'Fan Club chairman (lead Pokémon with high Tough)', 'Give Soothe Bell': 'Woman (if your lead Pokémon is very friendly)',
    **{f'Give {b} Berry': f"Berry Master's wife (tell her \"{p}\")" for b, p in (('Spelon', 'GREAT BATTLE'), ('Pamtre', 'CHALLENGE CONTEST'),
       ('Watmel', 'OVERWHELMING LATIAS'), ('Durin', 'COOL LATIOS'), ('Belue', 'SUPER HUSTLE'))},
    'Give Figy Berry': 'Kiri (daily berry)', 'Give Iapapa Berry': 'Kiri (daily berry)', 'Give Waterfall': 'Wallace (after Rayquaza calms Groudon and Kyogre)',
'Accept Trade': 'Trader (Harbor Mail for the Coin Case)', 'Attract Giver': 'Woman', 'Big Seedot': 'Man (show him a big Seedot)', 'Brick Break Black Belt': 'Black Belt',
    'Buy Soda Pop': 'Seashore House', 'Check Gold Symbols': 'Battle Frontier (all gold symbols)', 'Check Silver Symbols': 'Battle Frontier (all silver symbols)',
    'Claw Fossil': 'Top of Mirage Tower (choose one)', 'Root Fossil': 'Top of Mirage Tower (choose one)', 'Give Claw Fossil': 'The fossil you left behind (post-game)',
    'Give Root Fossil': 'The fossil you left behind (post-game)', 'Clear Tunnel Scene': "Wanda's boyfriend (once the tunnel is open)",
    'Completed New Mauville': 'Wattson (after you fix New Mauville)', 'Defeated Trainers': 'Seashore House owner (beat the three trainers)',
    'Devon Researcher Post Battle': 'Devon researcher (after you beat the Aqua Grunt)', 'Egg Woman': 'Old woman by the hot springs',
    'Expert F': 'Woman', 'Explain Pokemon Mart': 'Poké Mart employee', 'Familiar Grunt': 'Aqua Grunt (after you beat him)',
    'Get Acro Bike': 'Rydel (pick the Acro Bike; swap any time)', 'Get Mach Bike': 'Rydel (pick the Mach Bike; swap any time)',
    'Give Beldum': "Steven's house (after you enter the Hall of Fame)", 'Give Chikorita': 'Professor Birch (complete the Hoenn Pokédex; choose one)',
    'Give Cyndaquil': 'Professor Birch (complete the Hoenn Pokédex; choose one)', 'Give Totodile': 'Professor Birch (complete the Hoenn Pokédex; choose one)',
    'Give Exp Share': 'Mr. Stone (after you deliver the letter)', 'Give Fly HM': 'Your rival (after battling)', 'Give HMSurf': "Wally's father (after you beat Norman)",
    'Give Old Rod': 'Fisherman', 'Receive Good Rod': 'Fisherman', 'Super Rod Fisherman': 'Fisherman', 'Give Waterfall': 'Wallace', 'Steven Gives Dive': 'Steven',
    'Steven Give Decon Scope': 'Steven (after the Kecleon on the bridge)', 'May Give Go Goggles': 'Your rival', 'May Give Poke Balls': 'Your rival',
    'Receive Castform': 'Weather Institute scientist (after you beat Shelly)', 'Receive Lileep': 'Devon scientist (revives the Root Fossil)',
    'Receive Anorith': 'Devon scientist (revives the Claw Fossil)', 'Return Goods': 'Devon employee (return the Devon Goods)', 'Meet President': 'Mr. Stone',
    'Give Itemfinder': 'Your rival', 'Give Wailmer Pail': 'Flower shop owner', 'Give Repeat Ball': 'Devon researcher', 'Give Return': 'Woman (if your lead Pokémon is friendly)',
    'Give Frustration': 'Woman (if your lead Pokémon is unfriendly)', 'Wingull Returned': 'Girl (after her Wingull delivers the mail)',
    'Player Has Meteorite': 'Professor Cozmo (return the Meteorite)', 'Meteorite Machine': 'The machine at the summit (after Maxie leaves)',
    'Team Aqua Exits': 'Old couple at the summit (after Team Aqua leaves)', 'Shoal Salt 1': 'On the ground at low tide', 'Shoal Salt 3': 'On the ground at low tide',
    'Shoal Salt 4': 'On the ground at low tide', 'Shoal Shell 1': 'On the ground at low tide', 'Shell Bell Expert': 'Old man (bring 4 Shoal Salt and 4 Shoal Shells)',
    'Grunt': 'Aqua Grunt (after you beat him)', 'Victoria': 'Victoria (after you beat the Winstrate family)', 'Lava Cookie Lady': 'Lava Cookie seller (₽200)',
    'Wattson': 'Wattson', 'Hiker': 'Hiker', 'Steven': 'Steven', 'Trader': 'Trader', 'Deep Sea Tooth': 'Captain Stern (choose one; swap later)',
    'Deep Sea Scale': 'Captain Stern (choose one; swap later)', 'Fossil Maniacs Brother': "Fossil Maniac's brother", 'Kings Rock Boy': 'Boy (trade a Big Pearl)',
    'Cleanse Tag Woman': 'Old woman', 'Sun Stone Man': 'Scientist', 'Sludge Bomb Man': 'Man', 'Snatch Giver': 'Man in the cabin', 'Torment Giver': 'Man',
    'Roar Gentleman': 'Gentleman', 'Hidden Power Giver': 'Old woman (guess the coin)', 'Giga Drain Girl': 'Girl (if your lead knows a Grass move)',
    'Soft Sand Girl': 'Girl', 'Boy 2': 'Boy', 'White Herb Florist': 'Florist', 'Rock Smash Dude': 'Rock Smash Guy', 'Glass Worker': 'Glass Workshop (trade volcanic ash)'}
# Seaglass gifts whose script is new (hex label), named from the ROM's own dialogue
SG_FROM = {
    ('fallarbor-town', 'Spiky-eared Pichu (Lv 5)'): 'Professor Elm (catch 50 species; he checks your Pokédex)',
    ('fortree-city', 'Shiny Charm'): "The little shrines around Fortree (follow the glimmers from shrine to shrine)",
    ('lavaridge-town', 'Go-Goggles'): 'Your rival',
    ('littleroot-town', 'Catching Charm'): 'Professor Birch (after the Hall of Fame)',
    ('littleroot-town', 'Exp. Charm'): 'Professor Birch (with your Johto starter)',
    ('littleroot-town', 'Poké Ball ×5'): 'Your rival (after you get the Pokédex)',
    ('littleroot-town', 'Chikorita (Lv 5)'): 'Professor Birch (after the Hall of Fame; choose one)',
    ('littleroot-town', 'Cyndaquil (Lv 5)'): 'Professor Birch (after the Hall of Fame; choose one)',
    ('littleroot-town', 'Totodile (Lv 5)'): 'Professor Birch (after the Hall of Fame; choose one)',
    ('mauville-city', 'Mach Bike'): 'Rydel (pick the Mach Bike; swap any time)',
    ('mauville-city', 'Acro Bike'): 'Rydel (pick the Acro Bike; swap any time)',
    ('mossdeep-city', 'S.S. Ticket'): 'Old sailor (after the Mind Badge)',
    ('mossdeep-city', 'Eon Ticket'): 'Old sailor (clipped to the S.S. Ticket)',
    ('mossdeep-city', 'Old Sea Map'): 'Old sailor (show him a caught Rhydon)',
    ('mossdeep-city', 'Mystic Ticket'): 'Old sailor (show him a caught Octillery)',
    ('mossdeep-city', 'Aurora Ticket'): 'Old sailor (show him a caught Rayquaza)',
    ('mossdeep-city', 'Lucky Egg'): 'Game Corner prize',
    ('mossdeep-city', 'HM08'): 'Steven',
    ('pacifidlog-town', 'Big Pearl'): 'Scuba Safari (first place)',
    ('pacifidlog-town', 'HM07'): 'Scuba Safari (your first high score)',
    ('pacifidlog-town', 'Heart Scale ×5'): 'Scuba Safari (each new high score after that, plus a random rare item)',
    ('petalburg-city', 'HM03'): "Wally's father (after you beat Norman)",
    ('route-110', 'Itemfinder'): 'Your rival',
    ('route-119', 'HM02'): 'Your rival (after battling)',
    ('rustboro-city', 'Letter'): 'Mr. Stone',
    ('rusturf-tunnel', 'HM04'): "Wanda's boyfriend (once the tunnel is open)",
    ('verdanturf-town', 'Pecha Berry'): 'Contest Lobby',
    ('dewford-town', 'Silk Scarf'): 'Man in the house',
    ('slateport-city', 'TM41'): 'Battle Tent lobby',
    **{('route-110', n): 'Trick Master (finish a Trick House puzzle)' for n in ('Rare Candy', 'Timer Ball', 'Hard Stone', 'Smoke Ball', 'TM12', 'Magnet', 'PP Max')},
}
# Seaglass gifts gated by a story flag the map walk can't see: (location that opens them, why)
SG_LATER = {
    ('littleroot-town', 'Catching Charm'): ('pokemon-league', 'After the Hall of Fame'),
    ('littleroot-town', 'Exp. Charm'): ('pokemon-league', 'After the Hall of Fame (comes with your Johto starter)'),
    **{('littleroot-town', f'{n} (Lv 5)'): ('pokemon-league', 'After the Hall of Fame (choose one)') for n in ('Chikorita', 'Cyndaquil', 'Totodile')},
    ('littleroot-town', 'Amulet Coin'): ('lavaridge-town', "Norman's Balance Badge (your fifth)"),
    ('littleroot-town', 'S.S. Ticket'): ('pokemon-league', 'After the Hall of Fame'),
    ('mossdeep-city', 'Aurora Ticket'): ('sky-pillar', 'A caught Rayquaza to show the old sailor'),
    ('fallarbor-town', 'Spiky-eared Pichu (Lv 5)'): ('fallarbor-town', '50 species caught in your Pokédex'),
}
GIFT_AFTER = {'CHIKORITA': 'pokemon-league', 'CYNDAQUIL': 'pokemon-league', 'TOTODILE': 'pokemon-league', 'BELDUM': 'pokemon-league',
              'LILEEP': 'mirage-tower', 'ANORITH': 'mirage-tower'}
GIFT_NEED = {'pokemon-league': 'After the Hall of Fame', 'mirage-tower': 'After you bring a fossil from Mirage Tower'}
GMETHOD = {'mon': 'gift', 'trade': 'trade'}
seen_gift = set()
for k in gifts:
    lid, kind, nm, area, frm = k[:5]
    if (lid, nm, area) in seen_gift: continue
    seen_gift.add((lid, nm, area))
    loc = L(lid)
    frm = SG_FROM.get((lid, nm)) or FROM_FIX.get(frm) or re.sub(r'^(Give|Receive|Get) .*', 'Gift', frm)
    loc['gifts'].append({'id': uid(loc, f'{kind}-{area}-{nm}'), 'name': nm, 'from': frm, 'where': area})
    if k in gift_src: gift_pos[(lid, loc['gifts'][-1]['id'])] = gift_src[k]
    if kind in GMETHOD and len(k) > 5 and k[5]:
        lv = re.search(r'Lv (\d+)', nm)
        lvl = lv.group(1) if lv else '5' if 'Egg' in nm else None  # eggs hatch at Lv 5
        loc['encounters'].append({**mon('SPECIES_' + k[5]), 'method': GMETHOD[kind], 'area': area,
                                  **({'levels': lvl} if lvl else {}), 'notes': nm + ' · ' + frm,
                                  **({'after': GIFT_AFTER[k[5]]} if k[5] in GIFT_AFTER else {})})
for lid, area, pool in RANDOM_EGGS:
    for sp in pool:
        locs[lid]['encounters'].append({**mon('SPECIES_' + sp), 'method': 'gift', 'levels': '1', 'area': area,
                                        'notes': 'Random Alolan Egg from the sailor (2 Pinball points each; keep trading points in until you get this one)'})
for sp in ('TREECKO', 'TORCHIC', 'MUDKIP'):
    locs['route-101']['encounters'].append({**mon('SPECIES_' + sp), 'method': 'gift', 'levels': '5', 'area': 'Outside',
                                            'notes': "Starter: choose one from Professor Birch's bag. Get the other two by trading."})
STATIC_AFTER = {('route-119', 'KECLEON'): ('route-120', 'Invisible until you have the Devon Scope from Steven on Route 120.'),
               ('route-120', 'KECLEON'): ('route-120', 'Invisible until you have the Devon Scope from Steven on the bridge.'),
               'RAYQUAZA': ('sootopolis-city', 'Asleep at the top until the story wakes it; back at the top and catchable once it has calmed Groudon and Kyogre in Sootopolis. Needs the Mach Bike. Save first.')}
for (lid, area, sp, lvl) in statics:
    a = STATIC_AFTER.get((lid, sp)) or STATIC_AFTER.get(sp)
    locs[lid]['encounters'].append({**mon('SPECIES_' + sp), 'method': 'static', 'levels': lvl, 'area': area, 'notes': a[1] if a else 'One chance: save first',
                                    **({'after': a[0]} if a else {})})
# Feebas lives on six random water tiles of Route 119 (any rod); the tiles change when the trendy phrase changes.
if not any(k[2] == 'FEEBAS' for k in locs['route-119']['_enc']): locs['route-119']['encounters'].append({**mon('SPECIES_FEEBAS'), 'method': 'old-rod', 'levels': '20-25', 'area': 'Outside', 'rate': '50%',
                                        'notes': 'Feebas: only on 6 random water tiles along the river. Fish each tile a few times with any rod.'})

# collapse wild encounters
for loc in locs.values():
    wild = []
    for (area, method, sp, mapname), a in loc.pop('_enc').items():
        lv = str(a['min']) if a['min'] == a['max'] else f"{a['min']}-{a['max']}"
        row = {**mon('SPECIES_' + sp), 'method': method, 'levels': lv, 'rate': f"{a['rate']}%", 'area': area, '_map': mapname}
        gate = AREA_AFTER.get(mapname) or AREA_AFTER.get((loc['id'], method))
        if gate:
            row['after'] = gate[0]
            if gate[1]: row['notes'] = gate[1]
        if NOTES_FOR.get((loc['id'], method)): row['notes'] = NOTES_FOR[(loc['id'], method)]
        wild.append(row)
    order = ['grass', 'surf', 'old-rod', 'good-rod', 'super-rod', 'rock-smash', 'dive', 'scuba', 'dexnav', 'dexnav-surf']
    wild.sort(key=lambda e: (e['area'], order.index(e['method']), -int(e['rate'][:-1]), e['dex']))
    loc['encounters'] = wild + loc['encounters']

# ---------- trainers ----------
tdefs = TB['trainers']
CLASS_FIX = {'POKéMON BREEDER': 'Pokémon Breeder', 'POKéMON RANGER': 'Pokémon Ranger', 'COOLTRAINER': 'Cool Trainer', 'ELITE FOUR': 'Elite Four',
             'POKéMANIAC': 'Poké Maniac', 'TEAM AQUA': 'Team Aqua', 'TEAM MAGMA': 'Team Magma', 'AQUA ADMIN': 'Aqua Admin', 'MAGMA ADMIN': 'Magma Admin',
             'AQUA LEADER': 'Aqua Leader', 'MAGMA LEADER': 'Magma Leader', 'POKéMON TRAINER': 'Pokémon Trainer', 'SIS AND BRO': 'Sis and Bro',
             'SR. AND JR.': 'Sr. and Jr.', 'HEX MANIAC': 'Hex Maniac', 'RICH BOY': 'Rich Boy', 'BUG MANIAC': 'Bug Maniac', 'RUIN MANIAC': 'Ruin Maniac',
             'PARASOL LADY': 'Parasol Lady', 'NINJA BOY': 'Ninja Boy', 'BATTLE GIRL': 'Battle Girl', 'DRAGON TAMER': 'Dragon Tamer', 'BIRD KEEPER': 'Bird Keeper',
             'BUG CATCHER': 'Bug Catcher', 'SCHOOL KID': 'School Kid', 'YOUNG COUPLE': 'Young Couple', 'OLD COUPLE': 'Old Couple'}
money_table = {}
learnsets = {k: [(l, mv) for l, mv in s['levelup']] for k, s in species_rec.items()}
learnset_ptr = {k: k for k in species_rec}

def default_moves(sp, lvl):
    """The game fills a trainer Pokémon's moves with the last four it learns by level up at or below its level."""
    moves = []
    for l, mv in learnsets[learnset_ptr[sp]]:
        if l > lvl: break
        if mv in moves: continue
        if len(moves) == 4: moves.pop(0)
        moves.append(mv)
    return moves

def move_info(x):
    return {'name': move_names[x], 'type': move_types.get(x), **({'power': move_power[x]} if move_power.get(x) else {}),
            'category': move_cat.get(x)}
ABILITY_NAME = {int(k): v for k, v in TB['abilities'].items()}

def unpack_ivs(v):
    """Expansion packs trainer IVs 5 bits each: HP, Atk, Def, Spe, SpA, SpD."""
    return [(v >> (5 * k)) & 31 for k in range(6)]

def trainer_party(tconst):
    mons = []
    for p in tdefs[tconst]['party']:
        sp, lvl = p['species'], p['level']
        moves = p['moves'] or default_moves(sp, lvl)
        ivs = unpack_ivs(p['iv'])
        mons.append({**mon('SPECIES_' + sp), 'level': lvl, 'iv': min(ivs),
                     'moves': [move_info(x) for x in moves if x and x != 'NONE'],
                     **({'ivs': [ivs[0], ivs[1], ivs[2], ivs[4], ivs[5], ivs[3]]} if len(set(ivs)) > 1 else {}),
                     **({'ability': ABILITY_NAME.get(p['ability'])} if p.get('ability') and ABILITY_NAME.get(p['ability']) else {}),
                     **({'item': item_name(p['item'])} if p.get('item') else {})})
    return mons

def trainer_record(tconst):
    t = tdefs[tconst]
    cls = t['class']
    pty = trainer_party(tconst)
    prize = 4 * pty[-1]['level'] * t['money'] * (2 if t['double'] else 1)
    used = [item_name(i) for i in t['items']]
    rec = {'class': CLASS_FIX.get(cls) or title(cls), 'name': title(re.sub(r'\s*&\s*', ' & ', t['name'])), 'prize': prize, 'party': pty}
    if t['double']: rec['double'] = True
    if used: rec['uses'] = [f'{n} ×{c}' if c > 1 else n for n, c in collections.Counter(used).items()]
    return rec

# Scan scripts: label -> lines, and which trainer battles each label starts.
labels, label_map = {}, {}
for f in glob.glob(P('data/maps/*/scripts.inc')):
    mapname = os.path.basename(os.path.dirname(f))
    cur_label = None
    for line in open(f, encoding='utf-8'):
        lm = re.match(r'(\w+)::', line)
        if lm:
            cur_label = lm.group(1); labels[cur_label] = []
            label_map[cur_label] = mapname
            continue
        if cur_label: labels[cur_label].append(line.strip())
# Gabby & Ty's battles live in a shared script; they first battle you on Route 111
# (later rounds move between Routes 111, 118 and 120 and count as rematches).
cur_label = None
for line in open(P('data/scripts/shared.inc'), encoding='utf-8'):
    lm = re.match(r'(\w+)::', line)
    if lm:
        cur_label = lm.group(1); labels[cur_label] = []
        continue
    if cur_label: labels[cur_label].append(line.strip())
for l, ls in labels.items():
    if l.startswith('Common_') and any('TRAINER_GABBY_AND_TY' in x for x in ls): label_map[l] = 'Route111'

# trainerbattle_single/double/no_intro TRAINER_X, ...  and  trainerbattle TRAINER_BATTLE_<kind>, TRAINER_X, ...
BATTLE_RE = re.compile(r'trainerbattle(?:_(single|double|no_intro)\s+|\s+TRAINER_BATTLE_(\w+),\s*)(TRAINER_\w+)(.*)')
BATTLE_KINDS = {'CONTINUE_SCRIPT_DOUBLE_NO_MUSIC', 'CONTINUE_SCRIPT', 'CONTINUE_SCRIPT_NO_MUSIC', 'SINGLE', 'DOUBLE', 'CONTINUE_SCRIPT_DOUBLE', 'SET_TRAINER_A', 'SET_TRAINER_B', 'SINGLE_NO_INTRO_TEXT'}
BADGE_NAMES = ['Stone', 'Knuckle', 'Dynamo', 'Heat', 'Balance', 'Feather', 'Mind', 'Rain']
def label_rewards(label, depth=0, seen=None):
    """Items handed over in a trainer's script and the scripts it jumps to (gym TMs and badges)."""
    seen = seen if seen is not None else set()
    if label in seen or label not in labels or depth > 2: return []
    seen.add(label)
    out = []
    for s in labels[label]:
        gm = re.match(r'(?:giveitem|giveitem_msg)\s+(ITEM_\w+)(?:,\s*(\d+))?', s)
        if gm: out.append(item_name(gm.group(1)) + (f' ×{gm.group(2)}' if gm.group(2) and gm.group(2) != '1' else ''))
        bm_ = re.match(r'setflag FLAG_BADGE0(\d)_GET', s)
        if bm_: out.append(BADGE_NAMES[int(bm_.group(1)) - 1] + ' Badge')
        for target in re.findall(r'(?:goto|call)(?:_if\w*)?\s+(?:[^,]+,\s*)*?(\w+_EventScript_\w+)', s):
            out += label_rewards(target, depth + 1, seen)
        bt = BATTLE_RE.match(s)
        if bt:
            for target in re.findall(r'(\w+_EventScript_\w+)', bt.group(4)):
                out += label_rewards(target, depth + 1, seen)
    return out

STARTERS = ('TREECKO', 'TORCHIC', 'MUDKIP')
RIVAL_RE = re.compile(r'TRAINER_(?:MAY|BRENDAN)_(\w+)_(TREECKO|TORCHIC|MUDKIP)$')  # suffix = the starter YOU picked
def is_rematch(c):
    """Later Match Call rematches (TRAINER_ROSE_2..5, TRAINER_WALLY_VR_2..5) aren't first battles."""
    m = re.match(r'(TRAINER_\w+?)_([2-9])$', c)
    return bool(m and (m.group(1) + '_1') in battled)  # TRAINER_MIKE_2 is a first battle: MIKE_1 is never used
battled = {b.group(3) for ls in labels.values() for x in ls for b in [BATTLE_RE.match(x)] if b}
WALK = {'Route101': 'N', 'Route103': 'N', 'Route102': 'W', 'Route104': 'N', 'Route116': 'E', 'Route105': 'S', 'Route106': 'E',
        'Route107': 'E', 'Route108': 'E', 'Route109': 'N', 'Route110': 'N', 'Route117': 'W', 'Route111': 'N', 'Route112': 'W',
        'Route113': 'W', 'Route114': 'N', 'Route115': 'N', 'Route118': 'E', 'Route119': 'N', 'Route120': 'S', 'Route121': 'E',
        'Route122': 'S', 'Route123': 'W', 'Route124': 'E', 'Route125': 'E', 'Route126': 'S', 'Route127': 'S', 'Route128': 'E',
        'Route129': 'W', 'Route130': 'W', 'Route131': 'W', 'Route132': 'W', 'Route133': 'W', 'Route134': 'W', 'PetalburgWoods': 'N',
        'JaggedPass': 'N'}
AREA_ORDER = {'pokemon-league': ['Sidneys Room', 'Phoebes Room', 'Glacias Room', 'Drakes Room', 'Champions Room']}
# Battles that happen later in the story than your first visit to the location.
STAGE = {'PetalburgCity_Gym': 'lavaridge-town', 'MeteorFalls_StevensCave': 'pokemon-league'}

found_battles = collections.OrderedDict()  # (map, key) -> info
for label, lines in labels.items():
    mapname = label_map.get(label)
    if not mapname or mapname not in maps or map_skipped(mapname) or NO_TRAINERS.search(mapname): continue
    for s in lines:
        bt = BATTLE_RE.match(s)
        if not bt or (bt.group(1) is None and bt.group(2) not in BATTLE_KINDS): continue
        tconst = bt.group(3)
        if tconst not in tdefs or is_rematch(tconst): continue
        rm = RIVAL_RE.match(tconst)
        key = 'RIVAL_' + rm.group(1) if rm else tconst
        if mapname == 'Route104' and key == 'RIVAL_RUSTBORO': continue  # the same battle, if you meet your rival on the way out of Rustboro
        b = found_battles.setdefault((mapname, key), {'consts': {}, 'labels': [], 'rival': bool(rm), 'multi': bt.group(2) in ('SET_TRAINER_A', 'SET_TRAINER_B')})
        if rm:
            if 'MAY' in tconst or rm.group(2) not in b['consts']: b['consts'][rm.group(2)] = tconst
        else:
            b['consts'][None] = tconst
        b['labels'].append(label)

def position(mapname, lbls):
    m = maps[mapname]
    for ev in (m.get('object_events') or []) + (m.get('coord_events') or []):
        if ev.get('script') in lbls: return ev['x'], ev['y']
    for ev in (m.get('object_events') or []) + (m.get('coord_events') or []):
        body = ' '.join(labels.get(ev.get('script'), []))
        if any(l in body for l in lbls): return ev['x'], ev['y']
    return None

ENTRY = {}
layout_info = {l['id']: l for l in json.load(open(P('data/layouts/layouts.json')))['layouts'] if l.get('id')}
_dist = {}
def walk_dist(mapname):
    """Walking distance from where you come in, on the map's own tile grid (collision and elevation from map.bin)."""
    if mapname in _dist: return _dist[mapname]
    m = maps[mapname]; lay = layout_info.get(m['layout'])
    if not lay: _dist[mapname] = None; return None
    w, h = lay['width'], lay['height']
    raw = open(P(lay['blockdata_filepath']), 'rb').read()
    cells = [int.from_bytes(raw[i:i + 2], 'little') for i in range(0, len(raw), 2)]
    col = lambda x, y: (cells[y * w + x] >> 10) & 3
    elev = lambda x, y: cells[y * w + x] >> 12
    d = WALK.get(mapname)
    if d:
        edge = {'N': [(x, h - 1) for x in range(w)], 'S': [(x, 0) for x in range(w)], 'E': [(0, y) for y in range(h)], 'W': [(w - 1, y) for y in range(h)]}[d]
    else:
        warps = m.get('warp_events') or []
        def other(wp):
            dm = by_const.get(wp['dest_map'])
            return dm and dm['name'] in maps and map_loc(dm['name']) != map_loc(mapname)
        outside = [wp for wp in warps if other(wp)] or warps
        edge = [ENTRY[mapname]] if mapname in ENTRY else [max(((wp['x'], wp['y']) for wp in outside), key=lambda p: p[1])] if outside else []
    start = [(x, y) for x, y in edge if 0 <= x < w and 0 <= y < h and col(x, y) == 0 and elev(x, y) not in (1,)] or [(x, y) for x, y in edge if 0 <= x < w and 0 <= y < h and col(x, y) == 0]
    dist = {p: 0 for p in start}
    q = collections.deque(start)
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in dist or col(nx, ny): continue
            e1, e2 = elev(x, y), elev(nx, ny)
            if e1 != e2 and e1 not in (0, 15) and e2 not in (0, 15): continue
            dist[(nx, ny)] = dist[(x, y)] + 1; q.append((nx, ny))
    _dist[mapname] = dist
    return dist

def sort_key(mapname, pos):
    if pos is None: return (1, 0, 0)
    dist = walk_dist(mapname)
    if dist:
        x, y = pos
        near = [dist[p] for p in ((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if p in dist]
        if near: return (0, min(near), 0)
    x, y = pos
    d = WALK.get(mapname, 'N')
    return (0, {'N': -y, 'S': y, 'E': x, 'W': -x}[d], {'N': x, 'S': x, 'E': y, 'W': y}[d])

def area_sort(lid, area):
    order = AREA_ORDER.get(lid)
    if order and area in order: return (0, order.index(area), '')
    if area == 'Outside': return (0, -1, '')
    m = re.match(r'(B?)(\d+)F', area)
    if m: return (1, (100 if m.group(1) else 0) + int(m.group(2)), area)
    return (2, 0, area)

def tid_of(key):
    k = key.replace('TRAINER_', '')
    if key in tdefs and re.search(r'_1$', key) and (key[:-2] + '_2') in tdefs: k = k[:-2]  # ROXANNE_1 -> roxanne
    return re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-')

per_loc = collections.defaultdict(list)
trainer_src = {}  # (location id, trainer id) -> (map, script labels)
trainer_consts = {}
rival_mismatch = []
for (mapname, key), b in found_battles.items():
    lid = map_loc(mapname); area = area_name(mapname)
    first = next(iter(b['consts'].values()))
    rec = trainer_record(first)
    if b['rival']:
        rec.pop('party'); rec['name'] = 'May or Brendan'; rec['class'] = 'Rival'
        rec['byStarter'] = {mine.capitalize(): trainer_party(c) for mine, c in sorted(b['consts'].items(), key=lambda kv: STARTERS.index(kv[0]))}
        # Brendan (your rival if you play as May) sometimes has a different team member
        bren = {mine.capitalize(): trainer_party(c.replace('MAY', 'BRENDAN')) for mine, c in b['consts'].items() if c.replace('MAY', 'BRENDAN') in tdefs}
        if any(bren[k] != rec['byStarter'][k] for k in bren):
            rec['byStarterBrendan'] = {k: bren[k] for k in rec['byStarter'] if k in bren}
            rival_mismatch.append(key)
        trainer_consts_extra = [c.replace('MAY', 'BRENDAN') for c in b['consts'].values() if c.replace('MAY', 'BRENDAN') in tdefs]
        rec['prize'] = 4 * max(p[-1]['level'] for p in rec['byStarter'].values()) * tdefs[first]['money']
    if rec['class'] == 'Rival' and not b['rival']: rec['class'] = 'Pokémon Trainer'  # Wally uses the rival class
    if b['multi']: rec['note'] = 'Multi battle: Steven fights alongside you.'
    rewards = list(dict.fromkeys(r for l in b['labels'] for r in label_rewards(l)))
    if rewards: rec['rewards'] = rewards
    rec['id'] = tid_of(key)
    trainer_consts[(lid, rec['id'])] = list(b['consts'].values()) + (trainer_consts_extra if b['rival'] else [])
    trainer_src[(lid, rec['id'])] = (mapname, b['labels'])
    rec['area'] = area
    st = STAGE.get(mapname)
    if st: rec['stage'] = st
    leader_last = rec['class'] in ('Leader', 'Elite Four', 'Champion')
    per_loc[lid].append((area_sort(lid, area), leader_last, sort_key(mapname, position(mapname, b['labels'])), rec))
print('rival parties that differ between May and Brendan:', rival_mismatch)
for lid, lst in per_loc.items():
    lst.sort(key=lambda t: t[:3])
    L(lid)['trainers'] = [t[3] for t in lst]
for loc in locs.values():
    loc.setdefault('trainers', [])
    if {t['area'] for t in loc['trainers']} <= {'Outside'} and len({e.get('area') for e in loc['encounters'] if e.get('area')}) <= 1:
        for t in loc['trainers']: t.pop('area', None)
    if all(e.get('area') in (None, 'Outside') for e in loc['encounters']) and all('area' not in t for t in loc['trainers']):
        for e in loc['encounters']: e.pop('area', None)

# ---------- key battles for the Battle plan tab (same records as the route pages) ----------
def find_trainer(lid, tid):
    found = [t for t in locs[lid]['trainers'] if t['id'] == tid]
    assert found, (lid, tid, [t['id'] for t in locs[lid]['trainers']])
    return found[0]
KEY_BATTLES = [
    ('route-103', 'rival-route-103', 'Rival (Route 103)', None, 'Mixed'),
    ('rustboro-city', 'roxanne', 'Roxanne', 'Stone Badge', 'Rock'),
    ('rustboro-city', 'rival-rustboro', 'Rival (Rustboro City)', None, 'Mixed'),
    ('dewford-town', 'brawly', 'Brawly', 'Knuckle Badge', 'Fighting'),
    ('route-110', 'rival-route-110', 'Rival (Route 110)', None, 'Mixed'),
    ('mauville-city', 'wally-mauville', 'Wally (Mauville City)', None, 'Mixed'),
    ('mauville-city', 'wattson', 'Wattson', 'Dynamo Badge', 'Electric'),
    ('mt-chimney', 'tabitha-mt-chimney', 'Tabitha (Mt. Chimney)', None, 'Mixed'),
    ('mt-chimney', 'maxie-mt-chimney', 'Maxie (Mt. Chimney)', None, 'Mixed'),
    ('lavaridge-town', 'flannery', 'Flannery', 'Heat Badge', 'Fire'),
    ('petalburg-city', 'norman', 'Norman', 'Balance Badge', 'Normal'),
    ('route-119', 'shelly-weather-institute', 'Shelly (Weather Institute)', None, 'Mixed'),
    ('route-119', 'rival-route-119', 'Rival (Route 119)', None, 'Mixed'),
    ('fortree-city', 'winona', 'Winona', 'Feather Badge', 'Flying'),
    ('lilycove-city', 'rival-lilycove', 'Rival (Lilycove City)', None, 'Mixed'),
    ('magma-hideout', 'tabitha-magma-hideout', 'Tabitha (Magma Hideout)', None, 'Mixed'),
    ('magma-hideout', 'maxie-magma-hideout', 'Maxie (Magma Hideout)', None, 'Mixed'),
    ('aqua-hideout', 'matt', 'Matt (Aqua Hideout)', None, 'Mixed'),
    ('mossdeep-city', 'tate-and-liza', 'Tate and Liza', 'Mind Badge', 'Psychic'),
    ('mossdeep-city', 'maxie-mossdeep', 'Maxie (Space Center)', None, 'Mixed'),
    ('seafloor-cavern', 'shelly-seafloor-cavern', 'Shelly (Seafloor Cavern)', None, 'Mixed'),
    ('seafloor-cavern', 'archie', 'Archie (Seafloor Cavern)', None, 'Mixed'),
    ('sootopolis-city', 'juan', 'Juan', 'Rain Badge', 'Water'),
    ('victory-road', 'wally-vr', 'Wally (Victory Road)', None, 'Mixed'),
    ('pokemon-league', 'sidney', 'Sidney', None, 'Dark'),
    ('pokemon-league', 'phoebe', 'Phoebe', None, 'Ghost'),
    ('pokemon-league', 'glacia', 'Glacia', None, 'Ice'),
    ('pokemon-league', 'drake', 'Drake', None, 'Dragon'),
    ('pokemon-league', 'wallace', 'Champion Wallace', None, 'Water'),
]
trainers = []
for lid, tid, nm, badge, spec in KEY_BATTLES:
    t = find_trainer(lid, tid)
    trainers.append({**t, 'id': tid, 'name': nm, 'trainerName': t['name'], 'where': (locs[lid]['name'] + (f" {t['area']}" if t.get('area') and t['area'] != 'Outside' else '')),
                     'badge': badge, 'specialty': spec, 'location': lid,
                     **({'note': 'Your rival takes the starter that beats yours.'} if 'byStarter' in t else {})})

# ---------- level-up learnsets, weights, moves ----------
for p in pokedex:
    s_ = species_rec[dex_key[p['dex']]]
    p['weight'] = s_['weight']
    p['learnset'] = [[l, move_names[mv]] for l, mv in learnsets[dex_key[p['dex']]]]
EFFECT_KEEP = {'LEVEL_DAMAGE': 'level', 'SUPER_FANG': 'half', 'OHKO': 'ohko', 'MULTI_HIT': 'multi', 'PSYWAVE': 'level', 'COUNTER': 'counter',
               'MIRROR_COAT': 'counter', 'EXPLOSION': 'explode', 'SOLAR_BEAM': 'charge', 'SEMI_INVULNERABLE': 'charge', 'FUTURE_SIGHT': 'charge',
               'TWO_TURNS_ATTACK': 'charge', 'DREAM_EATER': 'dream', 'FLAIL': 'varies', 'RETURN': 'varies', 'FRUSTRATION': 'varies',
               'MAGNITUDE': 'varies', 'PRESENT': 'varies', 'LOW_KICK': 'varies', 'SPIT_UP': 'varies', 'ERUPTION': 'varies', 'REVENGE': 'varies',
               'FOCUS_PUNCH': 'varies', 'FIRST_TURN_ONLY': 'fakeout', 'SNORE': 'dream', 'TRIPLE_KICK': 'triple', 'HEAT_CRASH': 'varies',
               'GYRO_BALL': 'varies', 'ENDEAVOR': 'varies', 'FINAL_GAMBIT': 'varies', 'STORED_POWER': 'varies', 'POPULATION_BOMB': 'multi',
               'PUNISHMENT': 'varies', 'NATURAL_GIFT': 'varies', 'FLING': 'varies', 'TRUMP_CARD': 'varies', 'WRING_OUT': 'varies', 'BEAT_UP': 'varies',
               'RAGE_FIST': 'varies', 'FOUL_PLAY': 'foulplay', 'BODY_PRESS': 'bodypress', 'PSYSHOCK': 'psyshock',
               'LAST_RESORT': 'lastresort', 'SUPER_EFFECTIVE_ON_ARG': 'freezedry'}
FIXED = {'SONIC_BOOM': 'fixed20', 'DRAGON_RAGE': 'fixed40'}
# The expansion keeps two-hit moves and recharge moves as plain hits with extra fields this dump doesn't read: list them by name.
DOUBLE = {'DOUBLE_KICK', 'TWINEEDLE', 'BONEMERANG', 'DOUBLE_HIT', 'DUAL_CHOP', 'GEAR_GRIND', 'DUAL_WINGBEAT', 'DRAGON_DARTS', 'DOUBLE_IRON_BASH',
          'TWIN_BEAM', 'TACHYON_CUTTER', 'TRIPLE_DIVE'}
RECHARGE = {'HYPER_BEAM', 'GIGA_IMPACT', 'BLAST_BURN', 'FRENZY_PLANT', 'HYDRO_CANNON', 'ROCK_WRECKER', 'ROAR_OF_TIME', 'PRISMATIC_LASER',
            'ETERNABEAM', 'METEOR_ASSAULT'}
# Moves that drop the user's Sp. Atk by 2 after each hit (an additional effect the dump doesn't read: listed by name)
SELF_DROP = {'OVERHEAT', 'LEAF_STORM', 'DRACO_METEOR', 'PSYCHO_BOOST', 'FLEUR_CANNON'}
VARIES_HIDDEN = {'HIDDEN_POWER'}  # 60 power in Seaglass; type depends on IVs
moves_out = {}
for k, nm in move_names.items():
    if k == 'NONE' or not nm or nm.startswith('-'): continue
    e = FIXED.get(k) or ('double' if k in DOUBLE else 'recharge' if k in RECHARGE else EFFECT_KEEP.get(move_effects.get(k)))
    if k == 'TRIPLE_DIVE': e = 'triple'
    if k in SELF_DROP: e = 'selfdrop'
    m_ = MV[k]
    # Freeze-Dry: super effective on the type in its argument (make_src's argType, read from the ROM)
    se_ = {'seType': m_['argType']} if e == 'freezedry' else {}
    moves_out[nm] = {'type': move_types.get(k), 'power': move_power.get(k, 0), 'category': move_cat.get(k), 'acc': m_['acc'], 'pp': m_['pp'],
                     **({'priority': m_['prio']} if m_['prio'] else {}), **({'effect': e} if e else {}), **se_,
                     **({'desc': m_['desc'].replace('\n', ' ')} if m_.get('desc') else {}),
                     # contact / punch / bite / pulse / sound / ballistic / powder / wind / slice, from the ROM's move flags
                     **({'flags': m_['flags']} if m_.get('flags') else {})}

# ---------- roaming legendary + story order ----------
locs['roaming'] = {'id': 'roaming', 'name': 'Roaming Legendary', 'encounters': [
    {**mon('SPECIES_LATIOS'), 'method': 'roaming', 'levels': '40', 'notes': 'If you answer "blue" about the TV report after the Hall of Fame'},
    {**mon('SPECIES_LATIAS'), 'method': 'roaming', 'levels': '40', 'notes': 'If you answer "red" about the TV report after the Hall of Fame'}],
    'notes': "After you enter the Hall of Fame, your mom asks what color the Pokémon on the TV was. Your answer decides whether Latias (red) or Latios (blue) roams Hoenn's routes.",
    'items': [], 'gifts': [], 'trainers': []}

ORDER = [('Hoenn: Badge 1', 'littleroot-town route-101 oldale-town route-103 route-102 petalburg-city route-104 petalburg-woods rustboro-city'),
         ('Hoenn: Badges 2–3', 'route-116 rusturf-tunnel dewford-town granite-cave route-109 slateport-city pacifidlog-town route-110 mauville-city'),
         ('Hoenn: Badge 4', 'route-117 verdanturf-town route-111 route-112 fiery-path route-113 fallarbor-town route-114 meteor-falls route-115 mt-chimney jagged-pass lavaridge-town'),
         ('Hoenn: Badges 5–6', 'mirage-tower route-105 route-106 route-107 route-108 abandoned-ship new-mauville route-118 route-119 fortree-city route-120 scorched-slab'),
         ('Hoenn: Badge 7', 'route-121 safari-zone lilycove-city route-122 mt-pyre route-123 magma-hideout aqua-hideout route-124 mossdeep-city route-125 shoal-cave'),
         ('Hoenn: Badge 8 & League', 'route-127 route-128 seafloor-cavern route-126 sootopolis-city cave-of-origin route-129 route-130 route-131 sky-pillar route-132 route-133 route-134 ever-grande-city victory-road pokemon-league'),
         ('Post-game', 'roaming ss-tidal battle-frontier artisan-cave desert-underpass altering-cave sealed-chamber desert-ruins island-cave ancient-tomb marine-cave terra-cave'),
         ('Event islands', 'southern-island faraway-island birth-island navel-rock')]
walk = json.load(open(os.path.join(OUT, 'walkthrough.json')))
index = []
for region, ids in ORDER:
    for i in ids.split():
        assert i in locs, i
        index.append({'id': i, 'name': locs[i]['name'], 'region': region, 'file': f'locations/{i}.json'})
missing = set(locs) - {x['id'] for x in index}
assert not missing, missing
for i in walk:
    assert i.startswith('_') or i in locs, i

# ---------- when you actually fight each trainer ----------
# Place each trainer at the first key battle whose ace is within 5 levels of the trainer's own ace, never before the
# location itself. Trainers placed past the next key battle after the location are 'later' (collapsed in the app).
order_pos = {x['id']: i for i, x in enumerate(index)}
def ace_of(t):
    ps = [t['party']] if 'party' in t else list(t['byStarter'].values())
    return max(p['level'] for pty in ps for p in pty)
keys = sorted(((order_pos[t.get('stage') or t['location']], ace_of(t), t.get('stage') or t['location']) for t in trainers))
# Route 103's east side is only reached from Route 110 (or by Surf), so its trainers wait until then
MIN_STAGE = {'route-103': 'route-110'}
for loc in locs.values():
    here = order_pos[loc['id']]
    nxt = next((k for k in keys if k[0] >= here), None)
    for t in loc['trainers']:
        if t.get('stage'):
            t['later'] = order_pos[t['stage']] > here
            continue
        ace = ace_of(t)
        base = order_pos[MIN_STAGE[loc['id']]] if loc['id'] in MIN_STAGE and t['class'] != 'Rival' else here
        fit = next((k for k in keys if k[0] >= base and k[1] >= ace - 5), None)
        nb = next((k for k in keys if k[0] >= base), None)
        if fit and nb and fit[0] > nb[0] and fit[2] != loc['id']:
            t['stage'], t['later'] = fit[2], True
        elif base > here:
            t['stage'], t['later'] = MIN_STAGE[loc['id']], True
        elif not fit and here < order_pos['pokemon-league']:
            t['stage'], t['later'] = 'pokemon-league', True  # stronger than anything before the League: a post-game battle
# Swimmers are out on the water: you can't reach them before Surf (after Norman), whatever their level
SURF_AT = order_pos['lavaridge-town']
for loc in locs.values():
    for t in loc['trainers']:
        if 'Swimmer' in t['class'] and order_pos[t.get('stage') or loc['id']] <= SURF_AT:
            t['stage'], t['later'], t['need'] = 'lavaridge-town', order_pos[loc['id']] <= SURF_AT, 'surf'

# ---------- when can you reach each item? ----------
# A walk over the real map tiles (scripts/reach.py): water, ledges, Cut trees, Rock Smash rocks, Strength boulders,
# bike slopes and rails, dive spots, warps and boats, with each map opening when the story reaches its location.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach
def stage_after(lid, plus=0.5): return order_pos[lid] + plus
# Field moves: when the HM and the badge to use it are both in hand (as a stage in the story order)
ABILITIES = {
    'cut': (stage_after('rustboro-city'), "Cut (HM01 from the Cutter's House in Rustboro City, used with the Stone Badge)"),
    'mach-bike': (stage_after('mauville-city', 0), 'the Mach Bike (from Rydel in Mauville City; he swaps it for the Acro Bike any time)'),
    'acro-bike': (stage_after('mauville-city', 0), 'the Acro Bike (from Rydel in Mauville City; he swaps it for the Mach Bike any time)'),
    'rock-smash': (stage_after('mauville-city'), 'Rock Smash (HM06 from the Rock Smash Guy in Mauville City, used with the Dynamo Badge)'),
    'strength': (stage_after('lavaridge-town'), 'Strength (HM04 from Rusturf Tunnel, used with the Heat Badge)'),
    'surf': (stage_after('lavaridge-town'), "Surf (HM03 from Wally's father after you beat Norman in Petalburg City)"),
    'devon-scope': (stage_after('route-120', 0), 'the Devon Scope (from Steven on the Route 120 bridge) to reveal the hidden Kecleon'),
    'dive': (stage_after('mossdeep-city'), 'Dive (HM08 from Steven in Mossdeep City, after the Mind Badge)'),
    'waterfall': (stage_after('sky-pillar'), 'Waterfall (HM07 from the Scuba Safari in Pacifidlog Town; usable outside battle once you have all 8 badges)'),
}
OBSTACLES = {'OBJ_EVENT_GFX_CUTTABLE_TREE': 'cut', 'OBJ_EVENT_GFX_BREAKABLE_ROCK': 'rock-smash',
             'OBJ_EVENT_GFX_PUSHABLE_BOULDER': 'strength', 'OBJ_EVENT_GFX_KECLEON': 'devon-scope'}
TILE_NEEDS = {'MB_MUDDY_SLOPE': 'mach-bike', 'MB_CRACKED_FLOOR': 'mach-bike', 'MB_BUMPY_SLOPE': 'acro-bike', 'MB_ISOLATED_VERTICAL_RAIL': 'acro-bike',
              'MB_ISOLATED_HORIZONTAL_RAIL': 'acro-bike', 'MB_VERTICAL_RAIL': 'acro-bike', 'MB_HORIZONTAL_RAIL': 'acro-bike'}
# Scripted blockers that live in coord events: the desert's sandstorm turns you back until the Go-Goggles.
GATES = [('Route111', 'Route111_EventScript_ViciousSandstormTriggerDown', stage_after('lavaridge-town'), 'the Go-Goggles from your rival in Lavaridge Town'),
         ('Route111', 'Route111_EventScript_ViciousSandstormTriggerLeft', stage_after('lavaridge-town'), 'the Go-Goggles from your rival in Lavaridge Town'),
         # Sootopolis keeps its houses and Gym locked until Rayquaza has calmed Groudon and Kyogre (FLAG_SOOTOPOLIS_ARCHIE_MAXIE_LEAVE)
         ('SootopolisCity', 'lock:SootopolisCity_EventScript_LockHouseDoors', stage_after('sky-pillar'), 'Rayquaza to calm Groudon and Kyogre: the houses stay locked until then'),
         ('SootopolisCity', 'lock:SootopolisCity_EventScript_LockGymDoor', stage_after('sky-pillar'), 'Rayquaza to calm Groudon and Kyogre: the Gym stays locked until then'),
         # Wailmer block the sea east of Lilycove until Team Aqua leaves in their submarine
         ('LilycoveCity', 'lock:LilycoveCity_EventScript_SetWailmerMetatiles', stage_after('aqua-hideout', 0), 'Team Aqua to leave the Aqua Hideout (Wailmer block the way until then)')]
# Mr. Briney's boat (Route 104 <-> Dewford <-> Route 109) sails rather than warps; the cable car is code, not script.
TRANSPORTS = [('Route104_MrBrineysHouse', 'DewfordTown', 12, 8), ('Route104', 'DewfordTown', 12, 8), ('DewfordTown', 'Route104', 12, 54),
              ('DewfordTown', 'Route109', 21, 26), ('Route109', 'DewfordTown', 12, 8),
              ('Route112_CableCarStation', 'MtChimney_CableCarStation', 6, 10), ('MtChimney_CableCarStation', 'Route112_CableCarStation', 6, 10),
              ('Route121_SafariZoneEntrance', 'SafariZone_South', 32, 32)]
# Maps that open at a different story point from the rest of their location, and why.
BADGE_AT = {3: stage_after('mauville-city'), 4: stage_after('lavaridge-town'), 5: stage_after('lavaridge-town'),
            6: stage_after('route-120'), 7: stage_after('mossdeep-city'), 8: stage_after('sky-pillar')}
BADGE_NAMES = {3: 'Dynamo Badge', 4: 'Heat Badge', 5: 'Balance Badge', 6: 'Feather Badge', 7: 'Mind Badge', 8: 'Rain Badge'}
MAP_OPEN = {
    # Granite Cave's entrance is on Route 106's beach, a short walk from Dewford; the rest of Route 106 is open sea.
    'Route106': (order_pos['dewford-town'], None),
    'SafariZone_Northeast': (order_pos['pokemon-league'], 'After the Hall of Fame (the Safari Zone expansion opens then)'),
    'SafariZone_Southeast': (order_pos['pokemon-league'], 'After the Hall of Fame (the Safari Zone expansion opens then)'),
    'AbandonedShip_HiddenFloorCorridors': (ABILITIES['dive'][0], ABILITIES['dive'][1]),
    'AbandonedShip_HiddenFloorRooms': (ABILITIES['dive'][0], ABILITIES['dive'][1]),
}
# Rooms whose battles belong to a later point: Norman waits for four badges, Steven's cave opens after the Hall of Fame
# (STAGE), and any building whose trainers all come later in the story opens with them.
MAP_REASON = {'PetalburgCity_Gym': 'four badges: your father won\'t battle you before then',
              'MeteorFalls_StevensCave': 'the Hall of Fame: the cave opens then'}
for k, v in STAGE.items():
    if k in maps: MAP_OPEN.setdefault(k, (order_pos[v], MAP_REASON.get(k)))
trainers_in_map = collections.defaultdict(list)
for (lid, tid), (mapname, _) in trainer_src.items():
    t = next((x for x in locs[lid]['trainers'] if x['id'] == tid), None)
    if t: trainers_in_map[mapname].append(t)
for mapname, ts in trainers_in_map.items():
    if mapname in MAP_OPEN or maps[mapname].get('map_type') != 'MAP_TYPE_INDOOR': continue
    if all(t.get('later') and t.get('stage') for t in ts):
        MAP_OPEN[mapname] = (min(order_pos[t['stage']] for t in ts), None)
# The Trick Master opens puzzle n (n >= 2) once you have badge n + 1 (Route110_TrickHouseEntrance scripts)
for n in range(2, 9):
    b = min(n + 1, 8)
    MAP_OPEN[f'Route110_TrickHousePuzzle{n}'] = (BADGE_AT[b], f'the {BADGE_NAMES[b]} (the Trick Master sets this puzzle once you have it)')
def map_stage(name):
    if map_skipped(name) or name not in maps: return None
    if name in MAP_OPEN: return MAP_OPEN[name][0]
    lid = map_loc(name)
    return order_pos.get(lid)
def _gate_ok(g):
    what = g[1]
    if isinstance(what, str) and what.startswith('lock:'):
        ok = re.search(r'^' + re.escape(what[5:]) + r'::', open(P('data/maps', g[0], 'scripts.inc'), encoding='utf-8').read(), re.M)
    elif isinstance(what, str):
        ok = any(c.get('script') == what for c in maps[g[0]].get('coord_events') or [])
    else: ok = True
    if not ok: print('Seaglass: gate no longer in the game:', g[0], what, file=sys.stderr)
    return ok
GATES = [g for g in GATES if _gate_ok(g)]
world = reach.World(SRC, 'emerald', maps, map_stage, ABILITIES, OBSTACLES, GATES, TRANSPORTS, TILE_NEEDS)
world.solve(('LittlerootTown', 5, 8))
key_stages = sorted({k[0] for k in keys})
def first_visit_until(lid):
    """Everything up to the next key battle at or after a place counts as the first visit (Route 104's north end
    via Petalburg Woods), so an item is 'later' only when it needs a later story point than that."""
    here = order_pos[lid]
    return next((k for k in key_stages if k >= here), here)
unreachable = []
def describe(loc, st, kind, what):
    if kind == 'after':  # someone who only turns up after a story event elsewhere
        return f"After {index[int(st)]['name']}", index[int(st)]['id']
    if kind == 'ability': return ABILITIES[what][1], index[int(ABILITIES[what][0])]['id']
    if kind == 'gate': return what, index[int(st)]['id']
    if what in MAP_OPEN and MAP_OPEN[what][1]: return MAP_OPEN[what][1], index[int(st)]['id']
    via = map_loc(what) if what in maps else what
    if via != loc['id'] and via in locs: return f"Come in from {locs[via]['name']}", via
    return f"After {index[int(st)]['name']}", index[int(st)]['id']
for loc in locs.values():
    for it in loc['items']:
        pos = item_pos.get((loc['id'], it['id']))
        if not pos: continue
        mapname, x, y, el, under = pos
        r = world.item_reach(mapname, x, y, el, under)
        if r is None:
            # puzzles the walk can't solve (Trick House switches, New Mauville doors, tides): open with the map
            unreachable.append(f"{loc['id']}: {it['name']} ({mapname} {x},{y})")
            st = map_stage(mapname)
            r = (st, ('map', mapname))
        st, (kind, what) = r
        if os.environ.get('REACH_DEBUG') == loc['id']: print('REACH', it['name'], pos, r, first_visit_until(loc['id']), order_pos[loc['id']])
        if st <= first_visit_until(loc['id']): continue
        it['later'] = True
        it['need'], it['after'] = describe(loc, st, kind, what)
        it['stage'] = st
# The same for everything else on a place's page: NPC gifts and trainers (where their script's NPC stands)
scripts_at = reach.Scripts(world)
map_first = reach.map_reach(world)
def time_thing(loc, mapname, positions):
    """(stage, reason) for something at these spots on a map; the map's own opening if it has no spot we can find."""
    r = scripts_at.reach(mapname, positions) if positions else None
    if r is None: r = map_first.get(mapname)
    if r is None and map_stage(mapname) is not None: r = (map_stage(mapname), ('map', mapname))
    return r
def mark_later(loc, thing, r):
    if not r: return False
    # someone who only turns up after you have been somewhere else is never there on the first trip
    away = r[1] and r[1][0] == 'after' and map_loc(r[1][1]) != loc['id']
    if r[0] <= (order_pos[loc['id']] if away else first_visit_until(loc['id'])): return False
    thing['later'] = True
    thing['need'], thing['after'] = describe(loc, r[0], *r[1])
    thing['stage'] = r[0]
    return True
for loc in locs.values():
    for g in loc['gifts']:
        src = gift_pos.get((loc['id'], g['id']))
        if src and mark_later(loc, g, time_thing(loc, src[0], scripts_at.positions(src[0], label=src[1]))):
            # the Pokémon row for a gift or trade waits too (the Pokédex counts it from then)
            for e in loc['encounters']:
                if e['method'] in ('gift', 'trade') and (e.get('notes') or '').startswith(g['name']) and not e.get('after'):
                    e['after'] = g['after']
    for g in loc['gifts']:
        sl = SG_LATER.get((loc['id'], g['name']))
        if sl and order_pos[sl[0]] + 0.5 > g.get('stage', -1):
            g.update({'later': True, 'need': sl[1], 'after': sl[0], 'stage': order_pos[sl[0]] + 0.5})
            for e in loc['encounters']:  # its Pokémon row waits too
                if e['method'] in ('gift', 'trade') and (e.get('notes') or '').startswith(g['name']): e['after'] = sl[0]
    # and the other way round: a gift Pokémon that only comes later (GIFT_AFTER: the Johto starters, Beldum, the
    # revived fossils) keeps its gift row under "come back later" too
    for e in loc['encounters']:
        if e['method'] != 'gift' or not e.get('after') or order_pos[e['after']] <= first_visit_until(loc['id']): continue
        for g in loc['gifts']:
            if not g.get('later') and (e.get('notes') or '').startswith(g['name']):
                g.update({'later': True, 'need': GIFT_NEED.get(e['after'], f"After {index[order_pos[e['after']]]['name']}"),
                          'after': e['after'], 'stage': order_pos[e['after']] + 0.5})
    for t in loc['trainers']:
        src = trainer_src.get((loc['id'], t['id']))
        if not src: continue
        r = time_thing(loc, src[0], [p for l in src[1] for p in scripts_at.positions(src[0], label=l)])
        if r and r[0] > first_visit_until(loc['id']) and (not t.get('stage') or order_pos[t['stage']] < int(r[0])):
            t['stage'], t['later'] = index[int(r[0])]['id'], True
            t['reach'] = describe(loc, r[0], *r[1])[0]
# Wild Pokémon on land only appear on encounter tiles (grass, cave floor, sand). Seaglass hides some new grass behind
# a Cut tree or other obstacle (Littleroot Town's patch needs Cut), so a grass row waits for the first such tile you can reach.
_mbc = read('src/metatile_behavior.c')
ENC_LAND = {world.mb[k] for k in re.findall(r'\[(MB_\w+)\]\s*=[^\n]*TILE_FLAG_HAS_ENCOUNTERS', _mbc) if k in world.mb} - world.surfable
_land_cache = {}
def land_reach(mapname):
    if mapname in _land_cache: return _land_cache[mapname]
    g = world.grid(mapname); r = None
    if g:
        w, h, cells = g
        for i, c in enumerate(cells):
            if c[2] in ENC_LAND:
                b_ = world.best.get((mapname, i % w, i // w))
                if b_ and (r is None or b_[0] < r[0]): r = b_
    _land_cache[mapname] = r
    return r
for loc in locs.values():
    for e in loc['encounters']:
        mapname = e.pop('_map', None)
        if not mapname or e['method'] not in ('grass', 'dexnav') or e.get('after') or mapname not in maps: continue
        r = land_reach(mapname)
        if r and r[0] > first_visit_until(loc['id']):
            need, after = describe(loc, r[0], *r[1])
            e['after'] = after
            e['notes'] = (e.get('notes') + ' ' if e.get('notes') else '') + (need if need.startswith(('After', 'Come')) else f'Needs {need}.')
# for tests/item_reach.js: when each field move opens, and where a location's first visit ends
json.dump({'_about': 'Written by scripts/build_data.py from the reachability walk (scripts/reach.py). Read by tests/item_reach.js.',
           'abilities': {k: {'stage': v[0], 'need': v[1]} for k, v in ABILITIES.items()},
           'firstVisitUntil': {x['id']: first_visit_until(x['id']) for x in index},
           'puzzles': unreachable},
          open(os.path.join(OUT, 'verify', 'item-reach.json'), 'w'), ensure_ascii=False, indent=1)
if unreachable:
    print(f'reach: {len(unreachable)} items behind puzzles the walk cannot solve (timed by their map):', *unreachable, sep='\n  ', file=sys.stderr)

# ---------- TMs and HMs ----------
tm_moves, tm_of_move = {}, {}
for c, i in items.items():
    if c in TM_ITEM and i.get('move') and i['move'] in move_names and i['move'] != 'NONE':
        tm_moves[TM_ITEM[c]] = move_names[i['move']]; tm_of_move.setdefault(i['move'], TM_ITEM[c])
for p in pokedex:
    p['tmhm'] = sorted({tm_of_move[mv] for mv in species_rec[dex_key[p['dex']]]['teach'] if mv in tm_of_move})
tms = {k: {'move': tm_moves[k], 'reusable': k.startswith('HM'), 'sources': []} for k in sorted(tm_moves)}
for x in index:
    for kind in ('items', 'gifts'):
        for it in locs[x['id']].get(kind, []):
            m = re.match(r'((?:TM|HM)\d+)\b', it['name'])
            if m and m.group(1) in tms:
                tms[m.group(1)]['sources'].append({'loc': x['id'], 'how': 'gift' if kind == 'gifts' else 'found', 'where': it.get('where'),
                                                   **({'from': it['from']} if it.get('from') else {}),
                                                   **({'stage': it['stage'], 'need': it['need']} if it.get('later') else {})})

# ---------- shops ----------
shops = collections.defaultdict(list)
SHOP_NOTE = {'OldaleTown_Mart_Pokemart_Basic': 'Before you get the Pokédex', 'OldaleTown_Mart_Pokemart_Expanded': 'Poké Mart',
             'PetalburgCity_Mart_Pokemart_Basic': 'Poké Mart', 'PetalburgCity_Mart_Pokemart_Expanded': 'After you earn four badges',
             'RustboroCity_Mart_Pokemart_Basic': 'Poké Mart', 'RustboroCity_Mart_Pokemart_Expanded': 'After you meet the Devon employee on Route 116',
             # Seaglass's ROM labels for the same two lists (goto_if_set FLAG_PETALBURG_MART_EXPANDED_ITEMS / FLAG_MET_DEVON_EMPLOYEE)
             'Pokemart_82A113C': 'After you earn four badges', 'Pokemart_82AEE2C': 'After you meet the Devon employee on Route 116',
             'SlateportCity_Pokemart_EnergyGuru': 'Market: Energy Guru (vitamins)', 'SlateportCity_Pokemart_PowerTMs': 'Market: TM stall',
             'LilycoveCity_DepartmentStore_2F_Pokemart1': 'Department Store 2F (left clerk)', 'LilycoveCity_DepartmentStore_2F_Pokemart2': 'Department Store 2F (right clerk)',
             'LilycoveCity_DepartmentStore_3F_Pokemart_Vitamins': 'Department Store 3F (vitamins)', 'LilycoveCity_DepartmentStore_3F_Pokemart_StatBoosters': 'Department Store 3F (battle items)',
             'LilycoveCity_DepartmentStore_4F_Pokemart_AttackTMs': 'Department Store 4F (TMs)', 'LilycoveCity_DepartmentStore_4F_Pokemart_DefenseTMs': 'Department Store 4F (TMs)',
             'LavaridgeTown_HerbShop_Pokemart': 'Herb Shop', 'EverGrandeCity_PokemonLeague_1F_Pokemart': 'Pokémon League Poké Mart'}
BADGE_GYM = {1: 'rustboro-city', 2: 'dewford-town', 3: 'mauville-city', 4: 'lavaridge-town', 5: 'petalburg-city', 6: 'fortree-city',
             7: 'mossdeep-city', 8: 'sootopolis-city'}
BADGE_NAMES_ALL = {i + 1: n for i, n in enumerate(['Stone', 'Knuckle', 'Dynamo', 'Heat', 'Balance', 'Feather', 'Mind', 'Rain'])}
FLAG_SHOP = {'After you earn four badges': ('lavaridge-town', 'the Heat Badge'),
             'After you meet the Devon employee on Route 116': ('rusturf-tunnel', 'the Devon Goods back from Rusturf Tunnel')}
def badge_tiers(raw):
    """Mart lists picked by badge count. 'goto_if_unset FLAG_BADGE0n_GET, L' sends you to L's list with n-1 badges;
    'goto_if_unset FLAG_IS_CHAMPION, L' to the 8-badge list; the list a champion check falls through to is post-game (9).
    The TM clerk's own body ends on its 7-badge list."""
    out = {}
    blocks = dict(re.findall(r'^(\w+)::\n(.*?)(?=^\w+:|\Z)', raw, re.S | re.M))
    def mart_of(lbl, depth=3):
        body = blocks.get(lbl, '')
        m = re.search(r'pokemart (\w+)', body)
        if m: return m.group(1)
        g = re.search(r'^\s*goto (\w+)', body, re.M)
        return mart_of(g.group(1), depth - 1) if g and depth else None
    for lbl, body in blocks.items():
        for n, tgt in re.findall(r'goto_if_unset FLAG_BADGE0(\d)_GET, (\w+)', body):
            m = mart_of(tgt)
            if m: out.setdefault(m, int(n) - 1)
        c = re.search(r'goto_if_unset FLAG_IS_CHAMPION, (\w+)\n\s*goto (\w+)', body)
        if c:
            if mart_of(c.group(1)): out.setdefault(mart_of(c.group(1)), 8)
            if mart_of(c.group(2)): out.setdefault(mart_of(c.group(2)), 9)
        steps = re.findall(r'goto_if_unset FLAG_BADGE0(\d)_GET, (\w+)', body)
        m = re.search(r'pokemart (\w+)', body)
        if len(steps) >= 3 and m: out.setdefault(m.group(1), max(int(n) for n, _ in steps))
    return out
for name in sorted(maps):
    f = os.path.join(maps[name]['_dir'], 'scripts.inc')
    if not os.path.exists(f) or map_skipped(name): continue
    raw = open(f, encoding='utf-8').read()
    tiers = badge_tiers(raw)
    for lbl in dict.fromkeys(re.findall(r'^\s*pokemart (\w+)', raw, re.M)):
        body = re.search(re.escape(lbl) + r':+(.*?)pokemartlistend', raw, re.S).group(1)
        lst = [{'name': item_name(c), 'price': items[c]['price']} for c in re.findall(r'(ITEM_\w+)', body) if c != 'ITEM_NONE']
        where = SHOP_NOTE.get(lbl) or (area_name(name) if area_name(name) != 'Mart' else 'Poké Mart')
        shop = {'id': re.sub(r'[^a-z0-9]+', '-', lbl.lower()), 'where': where, 'items': lst}
        tier = tiers.get(lbl)
        if tier is not None:
            # Seaglass's TM clerk and the Happy Trainer Merchant Stand (Pedro and Nico, Petalburg) sell more with each badge
            who_ = 'TM clerk' if all(re.match(r'(TM|HM)\d+$', x['name']) for x in lst) else 'Merchant stand'
            shop['where'] = f'{who_} · ' + ('no badges' if tier == 0 else 'after the Hall of Fame' if tier == 9 else f'{tier} badge' + ('s' if tier > 1 else ''))
            shop['badges'] = tier
        lid_ = map_loc(name)
        if tier:
            gym = 'pokemon-league' if tier == 9 else STAGE.get('PetalburgCity_Gym') if tier == 5 else BADGE_GYM[tier]
            if order_pos[gym] > first_visit_until(lid_) or (tier == 5 and lid_ == 'petalburg-city'):
                shop.update({'later': True, 'need': 'the Hall of Fame' if tier == 9 else f'the {BADGE_NAMES_ALL[tier]} Badge', 'after': gym, 'stage': order_pos[gym] + 0.5})
        elif where in FLAG_SHOP:
            aft, need = FLAG_SHOP[where]
            shop.update({'later': True, 'need': need, 'after': aft, 'stage': order_pos[aft] + 0.5})
        else:
            mark_later(locs[lid_], shop, time_thing(locs[lid_], name, scripts_at.positions(name, contains=r'pokemart ' + lbl + r'\b')))
        shops[map_loc(name)].append(shop)
        for it in lst:
            mm = re.match(r'((?:TM|HM)\d+)$', it['name'])
            if mm:
                tms[mm.group(1)]['reusable'] = True
                src_ = {'loc': map_loc(name), 'how': 'buy', 'where': shop['where'], 'cost': f"₽{it['price']:,}"}
                if tier:  # the badge-tiered clerk: from the badge on, wherever the clerk stands
                    src_['stage'] = max(order_pos[lid_], order_pos[gym] + 0.5); src_['badges'] = tier
                elif shop.get('later'): src_['stage'] = shop['stage']
                old_ = next((x for x in tms[mm.group(1)]['sources'] if x['loc'] == src_['loc'] and x['how'] == 'buy'), None)
                if old_ is None: tms[mm.group(1)]['sources'].append(src_)
                elif src_.get('stage', order_pos[lid_]) < old_.get('stage', order_pos[lid_]): old_.clear(); old_.update(src_)
shops['lilycove-city'].append({'id': 'rooftop-vending', 'where': 'Department Store Rooftop (vending machines)', 'items': [
    {'name': 'Fresh Water', 'price': 200}, {'name': 'Soda Pop', 'price': 300}, {'name': 'Lemonade', 'price': 350}]})
gc = read('data/maps/MauvilleCity_GameCorner/scripts.inc')
prize_items = [(item_name(it), int(c)) for c, it in re.findall(r'removecoins (\d+)\n\s*additem (ITEM_\w+)', gc)]
for tm, coins in prize_items:
    if tm not in tms: continue
    tms[tm]['reusable'] = True
    tms[tm]['sources'].append({'loc': 'mauville-city', 'how': 'prize', 'where': 'Game Corner prize counter', 'cost': f'{coins:,} coins'})
shops['mauville-city'].append({'id': 'game-corner-prizes', 'where': 'Game Corner prize counter', 'coins': True,
    'items': [{'name': tm, 'price': c} for tm, c in prize_items]})
for t in tms.values():
    t['sources'].sort(key=lambda s: order_pos[s['loc']])

# ---------- extra species data: abilities, catch rate, EXP, EV yield, growth rate, wild held items ----------
# Seaglass Pokémon have up to three abilities; the third is the hidden one.
for p in pokedex:
    x = species_rec[dex_key[p['dex']]]
    ab = x['abilities']
    p['abilities'] = list(dict.fromkeys(a for a in ab[:2] if a and a != '-------'))
    if len(ab) > 2 and ab[2] and ab[2] != '-------' and ab[2] not in p['abilities']: p['hiddenAbility'] = ab[2]
    p['catchRate'] = x['catchRate']; p['expYield'] = x['expYield']; p['growth'] = x['growth']
    e = x['ev']  # HP Atk Def Spe SpA SpD
    p['ev'] = [e[0], e[1], e[2], e[4], e[5], e[3]]
    held = {k: item_name(v) for k, v in zip(('common', 'rare'), x['held']) if v}
    if held: p['held'] = held
    if x.get('category'): p['category'] = x['category']
    if x.get('desc'): p['entry'] = x['desc'].replace('\n', ' ')
    p['eggMoves'] = [move_names[m] for m in x['egg'] if m in move_names]

# ---------- move tutors ----------
# A tutor script sets VAR_0x8005 to the move and calls the shared routine that runs ChooseMonForMoveTutor.
shared_src = read('data/scripts/shared.inc')
TUTOR_CALLS = {l for l, b in re.findall(r'^(\w+)::\n(.*?)(?=^\w+:|\Z)', shared_src, re.S | re.M) if 'special ChooseMonForMoveTutor' in b}
tutors, tutor_moves = [], set()
for name in sorted(maps):
    f = os.path.join(maps[name]['_dir'], 'scripts.inc')
    if not os.path.exists(f) or map_skipped(name): continue
    raw = open(f, encoding='utf-8').read()
    for lbl, body in re.findall(r'^(\w+)::\n(.*?)(?=^\w+:|\Z)', raw, re.S | re.M):
        for mid, call in re.findall(r'setvar VAR_0x8005, (\d+)\n\s*call (\w+)', body):
            if call not in TUTOR_CALLS: continue
            mv = moves_by_num.get(int(mid))
            if not mv or mv in tutor_moves: continue
            tutor_moves.add(mv)
            lid = map_loc(name)
            once = 'FLAG_MOVE_TUTOR_TAUGHT' in body or 'FLAG_MOVE_TUTOR_TAUGHT' in raw
            tutor = {'id': 'tutor-' + mv.lower().replace('_', '-'), 'move': move_names[mv], 'loc': lid, 'where': area_name(name),
                     'note': 'Teaches the move once.' if once else 'Teaches the move as often as you like.'}
            ps = scripts_at.positions(name, label=lbl, contains=r'\b' + lbl + r'\b')
            mark_later(locs[lid], tutor, time_thing(locs[lid], name, ps))
            tutors.append(tutor)
for p in pokedex:
    tm = {tm_of_move.get(m) for m in species_rec[dex_key[p['dex']]]['teach']}
    tt = [move_names[m] for m in species_rec[dex_key[p['dex']]]['teach'] if m in tutor_moves]
    if tt: p['tutor'] = tt
for t in tutors:
    t['learners'] = [p['dex'] for p in pokedex if t['move'] in p.get('tutor', [])]
tutors.sort(key=lambda t: order_pos[t['loc']])

rematches = collections.defaultdict(list)
TIER = ['First battle', 'Rematch 1', 'Rematch 2', 'Rematch 3', 'Rematch 4']
for rm in TB['rematches']:
    consts, mp = rm['trainers'], rm['map']
    m = by_const.get(mp)
    if not m or m['name'] not in maps: continue
    lid = map_loc(m['name'])
    base = tid_of(consts[0])
    tiers, seen_c = [], {consts[0]}
    for i, c in enumerate(consts[1:], 1):
        if c in seen_c or c not in tdefs: continue
        seen_c.add(c)
        tiers.append({'after': TIER[i], 'party': trainer_party(c)})
    if tiers: rematches[lid].append({'id': base, 'tiers': tiers})

# ---------- item descriptions ----------
KEEP_CAPS = {'HP', 'PP', 'TM', 'HM', 'S.S.', 'EXP.', 'EXP', 'PC', 'TV'}
def desc_text(d):
    d = d.replace('\\n', ' ').replace('POKéMON', 'Pokémon').replace('POKé', 'Poké').replace('{POKEBLOCK}', 'Pokéblock')
    return re.sub(r"\b[A-Zé][A-Zé'.\-]+\b\.?", lambda m: m.group(0) if m.group(0).rstrip('.') in KEEP_CAPS else m.group(0).capitalize(), d)
POCKET = {'POCKET_ITEMS': 'Items', 'POCKET_KEY_ITEMS': 'Key Items', 'POCKET_POKE_BALLS': 'Poké Balls', 'POCKET_BERRIES': 'Berries', 'POCKET_TM_HM': 'TMs & HMs'}
STATUS_CURE = {'CURE_PAR': 'paralysis', 'CURE_SLP': 'sleep', 'CURE_PSN': 'poison', 'CURE_BRN': 'a burn', 'CURE_FRZ': 'freezing', 'CURE_CONFUSION': 'confusion', 'CURE_STATUS': 'any status problem or confusion'}
PINCH = {'ATTACK_UP': 'Attack', 'DEFENSE_UP': 'Defense', 'SPEED_UP': 'Speed', 'SP_ATTACK_UP': 'Sp. Atk', 'SP_DEFENSE_UP': 'Sp. Def'}
def held_text(i):
    e, n = i['holdEffect'].replace('HOLD_EFFECT_', ''), i['holdEffectParam']
    if i['pocket'] != 'POCKET_BERRIES': return None
    if e == 'RESTORE_HP': return f'Held in battle: restores {n} HP once its HP falls below half.'
    # Sitrus Berry: a percentage of max HP in Seaglass (pokeemerald-expansion), 25%
    if e == 'RESTORE_PCT_HP': return f'Held in battle: restores {n}% of its max HP once its HP falls below half.'
    if e in STATUS_CURE: return f'Held in battle: cures {STATUS_CURE[e]} straight away.'
    if e == 'RESTORE_PP': return f'Held in battle: restores {n} PP to a move that runs out.'
    if e.startswith('CONFUSE_'): return 'Held in battle: restores 1/8 of max HP when HP is low, but confuses a Pokémon that dislikes the flavor.'
    if e in PINCH: return f'Held in battle: raises {PINCH[e]} when HP is low.'
    if e == 'CRITICAL_UP': return 'Held in battle: raises the critical-hit ratio when HP is low.'
    if e == 'RANDOM_STAT_UP': return 'Held in battle: sharply raises a random stat when HP is low.'
    if e == 'RESTORE_STATS': return 'Held in battle: restores lowered stats.'
    return None
# items.h keeps a "FireRed/LeafGreen key items" block (Oak's Parcel, Poké Flute, Tri-pass...) that Emerald never hands out.
# Leave those out of the item pages and search. Emerald does use three items from that block: the two event tickets
# and the Powder Jar (Berry Crush).
FRLG_ONLY_ITEMS = {'ITEM_' + x for x in ('OAKS_PARCEL PARCEL POKE_FLUTE SECRET_KEY BIKE_VOUCHER GOLD_TEETH CARD_KEY LIFT_KEY SILPH_SCOPE FAME_CHECKER '
                                          'TM_CASE BERRY_POUCH TEACHY_TV TRI_PASS RAINBOW_PASS TEA RUBY SAPPHIRE').split()}
# (Seaglass's scripts never give or sell any of these; tests/generation.js checks every location and shop)
item_info = {}
for c, i in items.items():
    if c in FRLG_ONLY_ITEMS: continue
    if c == 'ITEM_NONE' or not i['english'] or '?' in i['english'] or ('~' in i['english'] and c not in ITEM_FIX) or i['pocket'] == 'POCKET_TM_HM': continue
    x = {'desc': desc_text(i['description_english']), 'price': i['price'], 'pocket': POCKET.get(i['pocket'], '')}
    h = held_text(i)
    if h: x['held'] = h
    item_info[item_name(c)] = x

# ---------- save file import map ----------
def defines(*files):
    out = {}
    for f in files:
        for name, val in re.findall(r'^#define\s+(\w+)\s+(.+?)\s*(?://.*)?$', read(f), re.M): out[name] = val
    return out
DEF = defines('include/constants/flags.h', 'include/constants/opponents.h', 'include/constants/species.h', 'include/constants/moves.h')
_ev = {}
def ev(name):
    if name in _ev: return _ev[name]
    expr = DEF[name]
    expr = re.sub(r'\b([A-Za-z_]\w*)\b', lambda m: str(ev(m.group(1))) if m.group(1) in DEF else m.group(1), expr)
    _ev[name] = int(eval(expr.replace('/', '//'), {'__builtins__': {}}))
    return _ev[name]
flag_map = {}
for k, f in item_flags.items():
    if f in DEF: flag_map[k] = ev(f)
TFS = ev('TRAINER_FLAGS_START')
for (lid, tid), consts in trainer_consts.items():
    flag_map[f'{lid}:trainer:{tid}'] = [TFS + ev(c) for c in consts if c in DEF]
species_index = [0] * (max(ev(k) for k in DEF if k.startswith('SPECIES_') and re.match(r'^\d+$', DEF[k])) + 1)
for k in DEF:
    if k.startswith('SPECIES_') and k[8:] in natdex and re.match(r'^\d+$', DEF[k]): species_index[ev(k)] = natdex[k[8:]]
moves_by_id = {}
for k in DEF:
    if k.startswith('MOVE_') and k[5:] in move_names and re.match(r'^\d+$', DEF[k]): moves_by_id[ev(k)] = move_names[k[5:]]
move_list = [moves_by_id.get(i, '') for i in range(max(moves_by_id) + 1)]
badges = [ev(f'FLAG_BADGE0{i}_GET') for i in range(1, 9)]

# ---------- region map grid (for the tappable map) ----------
src = read('src/data/region_map/region_map_layout.h')
cells = []
for y, row in enumerate(re.findall(r'\{(MAPSEC_[^{}]*)\}', src)):
    for x, sec in enumerate(c.strip() for c in row.split(',') if c.strip()):
        if sec == 'MAPSEC_NONE': continue
        lid = sec.replace('MAPSEC_', '').lower().replace('_', '-')
        if lid in locs: cells.append([x, y, lid, 'map'])
# Caves and buildings aren't on the town-map grid; region_map_sections.json gives each one's square.
placed = {c[2] for c in cells}
for s_ in json.load(open(P('src/data/region_map/region_map_sections.json')))['map_sections']:
    lid = {'MAPSEC_UNDERWATER_SEALED_CHAMBER': 'sealed-chamber', 'MAPSEC_UNDERWATER_MARINE_CAVE': 'marine-cave'}.get(s_['id'], s_['id'].replace('MAPSEC_', '').lower().replace('_', '-'))
    if lid in locs and lid not in placed and 'x' in s_:
        cells.append([s_['x'], s_['y'], lid, 'dungeon']); placed.add(lid)
league = next(c for c in cells if c[2] == 'ever-grande-city')
cells.append([league[0], league[1], 'pokemon-league', 'dungeon'])
region_maps = {'Hoenn': cells}

# ---------- write ----------
os.makedirs(os.path.join(OUT, 'locations'), exist_ok=True)
for f in glob.glob(os.path.join(OUT, 'locations', '*.json')): os.remove(f)
for loc in locs.values():
    loc.setdefault('trainers', [])
    loc['verified'] = True
    loc['sources'] = [SOURCE_URL]
    json.dump(loc, open(os.path.join(OUT, 'locations', loc['id'] + '.json'), 'w'), ensure_ascii=False, indent=1)
json.dump({'locations': index}, open(os.path.join(OUT, 'locations.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(moves_out, open(os.path.join(OUT, 'moves.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(pokedex, open(os.path.join(OUT, 'pokedex.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(type_chart, open(os.path.join(OUT, 'types.json'), 'w'), indent=1)
json.dump(trainers, open(os.path.join(OUT, 'trainers.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(tms, open(os.path.join(OUT, 'tms.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(item_info, open(os.path.join(OUT, 'items.json'), 'w'), ensure_ascii=False, indent=0)
json.dump({'shops': shops, 'tutors': tutors, 'rematches': rematches, 'unown': {}},
          open(os.path.join(OUT, 'extras.json'), 'w'), ensure_ascii=False, indent=1)
json.dump({'flags': flag_map, 'species': species_index, 'moves': move_list, 'badges': badges},
          open(os.path.join(OUT, 'save-map.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(region_maps, open(os.path.join(OUT, 'region-map.json'), 'w'), separators=(',', ':'))
print(len(locs), 'locations;', sum(len(l['items']) for l in locs.values()), 'items;', sum(len(l['gifts']) for l in locs.values()), 'gifts;',
      sum(len(l['encounters']) for l in locs.values()), 'encounter rows;', sum(len(l['trainers']) for l in locs.values()), 'trainers')
print('shops', sum(len(v) for v in shops.values()), 'tutors', len(tutors), 'rematch trainers', sum(len(v) for v in rematches.values()))
print('tms', len(tms), 'without a source:', [k for k, v in tms.items() if not v['sources']])
print('items', len(item_info), '; save map:', len(flag_map), 'flags')
print('region map: unplaced locations', sorted(set(x['id'] for x in index) - {c[2] for c in cells}))
