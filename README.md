# Group chat spawn art

A small image set for PikaBot's group Pokémon spawns. Each output is built by code from a **full-colour PokeAPI official artwork** PNG and a high-resolution scenic habitat backdrop. The Pokémon stays visible (no silhouette), and a soft black oval shadow sits underneath it, following the spawn-image layout we discussed.

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
- `spawns.json` — the small starter batch; add entries here to generate more
- `manifest.json` — generated index with species, rarity folder, backdrop, and artwork source URL

Backdrops are selected by habitat, not just by region. A region can use several scenes, and the same scene type can serve Pokémon from different regions.

## Generate

```bash
python -m pip install -r requirements.txt
python generate.py --workers 4
```

The starter catalog deliberately contains only **six outputs (one per rarity folder)**. Each Pokémon artwork is fetched from PokeAPI while jobs run concurrently; source artwork is not kept in a separate cache. The generator reads the committed backdrop plates, writes final composites and updates `manifest.json`. Re-run after editing `spawns.json` to add entries.

PokeAPI provides the Pokémon artwork, not the scenery. The habitat backdrops are AI-generated original scenes, using a soft-focus encounter-game look; they are not Pokétwo assets. Pokémon artwork remains the property of its respective rights holders; this is a fan-project asset set.
