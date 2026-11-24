# Group chat spawn art

A Pokémon group-spawn image set for PikaBot. Each output combines **full-colour PokeAPI artwork** with a soft-focus habitat backdrop and a black oval ground shadow. Composites are JPEGs so a complete forms-and-shinies catalog stays practical to store and send.

The image is sent as a plain Telegram photo. The caption is separate:

> **A wild Pokémon has appeared!**
>
> Guess the Pokémon and type `@pikaplayrobot catch <name>` or `/catch@pikaplayrobot <name>`.

## Layout

- `normal/` — regular, non-shiny Pokémon
- `shiny-normal/` — shiny regular Pokémon
- `legendary/` and `shiny-legendary/`
- `mythical/` and `shiny-mythical/`
- `assets/backdrops/` — illustrated scenery for forests, meadows, caves, snowy mountains, coasts, and starry ruins
- `spawns.json` — the six-image starter batch
- `generate_all.py` — bounded-memory catalog generator for all PokeAPI Pokémon forms and shiny variants
- `manifest.json` / `manifest-all.json` — starter and complete-catalog indexes, including artwork sources and unavailable variants

Backdrops are selected by habitat, not just by region. A region can use several scenes, and the same scene type can serve Pokémon from different regions.

## Generate

```bash
python -m pip install -r requirements.txt
python generate.py --workers 4                 # six-image starter set
python generate_all.py --workers 4             # every PokeAPI form, normal + shiny
```

The full run discovers every entry in PokeAPI's Pokémon-form catalog, assigns habitat and rarity folders, and builds normal and shiny composites concurrently. It keeps only a small bounded worker queue in memory, saves each JPEG immediately, and discards downloaded source art instead of caching it. Form-specific artwork is preferred; if PokeAPI has no asset for a form, the species' default artwork is used and recorded in `manifest-all.json`. Variants with no usable source are explicitly marked unavailable. Existing output files are reused on a resumed run; pass `--force` to regenerate them. `--limit N` is available for a small test run.

PokeAPI provides the Pokémon artwork, not the scenery. The habitat backdrops are AI-generated original scenes with a soft-focus encounter-game look; they are not Pokétwo assets. Pokémon artwork remains the property of its respective rights holders; this is a fan-project asset set.
