# Seaglass Completion Dex

A phone-friendly, offline-capable 100% completion guide for **Pokémon Emerald Seaglass 3.0**, the ROM hack built on
pokeemerald-expansion. It uses the same code as the [Emerald Completion Dex](https://github.com/natendogames/emeralddex)
and the [FireRed/LeafGreen Completion Dex](https://github.com/natendogames/frlgdex). Every number in it comes from
Seaglass itself, not from vanilla Emerald.

- **Routes**: every Hoenn location in Seaglass's story order, plus the post-game areas. Each location has:
  - walkthrough steps
  - every trainer, with their party, levels, moves, weaknesses and rewards, and a damage estimate for each of your Pokémon against each of theirs
  - wild Pokémon, including DexNav hidden Pokémon and the Scuba Safari
  - items on the ground and hidden items
  - NPC gifts, in-game trades and shops, including the badge-tiered TM clerk and the Petalburg merchant stand

  All of these are checklists.
- **Story progress**: anything you can't get on the first visit sits under "come back later" with what it needs (Surf, Cut, a badge, a story event).
- **Pokédex**: Seaglass's own 430-entry dex plus its Alolan forms, with where to catch each one.
- **Battle plan and Team plan**: who to send out against every key battle, and the best team at each point of the game for your starter. These use Seaglass's types, stats, moves, the Fairy type and the per-move physical/special split.
- **Catch plan, reference pages, trackers and tools** as in the Emerald app.
- Progress is stored on the device, with backup export and import, and optional cloud sync keyed by email. It uses the shared sync worker under a separate `seaglass:` key, so it never overwrites the Emerald or FireRed/LeafGreen apps.

The app is plain HTML, CSS and JS with no build step, hosted on GitHub Pages. To run it locally, use `python3 -m http.server` in this folder and open http://localhost:8000.

No Pokémon sprites, and no part of the ROM, are included. Only data derived from it is.

## Data

`data/` is generated from the Seaglass ROM. The ROM never leaves the owner's computer: dump scripts read it there and
produce JSON, and `make_src.py` turns that JSON into a pokeemerald-shaped source tree (maps, scripts, layouts, tables).
Then:

```
python3 -I scripts/build_seaglass.py /path/to/seaglass-src data
python3 scripts/seaglass_builds.py scripts/src/smogon_adv_builds.json data
```

- `scripts/build_seaglass.py` is the Emerald builder adapted to Seaglass: its gift givers, story gates (`SG_LATER`), shop tiers, Scuba Safari and DexNav encounters.
- `scripts/reach.py` walks the real map tiles to decide what's reachable on the first visit.
- `scripts/seaglass_builds.py` reworks Smogon's Gen 3 sets for Seaglass's learnsets, items and abilities. Every set is marked Draft.
- `docs/changes.md` / `docs/changes.json` compare every move and Pokémon three ways: vanilla Emerald, pokeemerald-expansion defaults, and Seaglass.

`data/walkthrough.json` holds the story steps. They started from the Emerald app's walkthrough and were re-checked against Seaglass's event scripts. All of them show Draft, because Bulbapedia only covers vanilla Emerald.

## Team planner

```
node scripts/team_planner.js --out docs/team-guide.md --stages-out docs/team-stages.md --app-json data/team-plan.json
```

This scores candidate teams against every trainer up to the Champion using the Battle plan's damage engine. Run it again after any change to the data or the engine.

## Tests

GitHub Actions runs these on every push and pull request:
- `tests/audit_battles.js`: catch suggestions vs a brute-force search, Seaglass's type chart (Gen 3 plus Fairy) and move values, and the ability maths (Strong Jaw, Technician, Scrappy, Lightning Rod, Soundproof).
- `tests/team_plan.js`: the Team plan.
- `tests/features.js`: every page renders, shop and ball timing, catch plans, save import, search, calculators.
- `tests/walkthrough.js`: every `{gift:}`, `{trainer:}`, `{loc:}`, `{mon:}` and `{item:}` link points at real data.
- `tests/builds.js`: every competitive set uses moves the Pokémon learns in Seaglass.
- `tests/generation.js`: the dex is Seaglass's (430, numbered as in the ROM), the starters are right, and no FRLG-only items or Kanto places leak in.
- `tests/item_reach.js`: first-visit vs "come back later" for items, gifts, shops and tutors.
- `tests/caught_link.js`: caught status is shared across pages.

Progress keys are `dex:<number>` for Pokémon and `<location-id>:item:<id>` or `<location-id>:gift:<id>` for checklists, so keep ids stable.
