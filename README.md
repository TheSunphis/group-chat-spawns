# Group chat spawn art

A small, code-generated image set for PikaBot's group Pokémon spawns. Each output combines a **full-colour PokeAPI official artwork** PNG with an original, procedural habitat backdrop. The Pokémon stays visible (no silhouette), and a soft black oval shadow sits underneath it, following the spawn-image layout we discussed.

The image is sent as a plain Telegram photo. The caption is separate:

> **A wild Pokémon has appeared!**
>
> Guess the Pokémon and type `@pikaplayrobot catch <name>`.

## Layout

- `normal/` — regular, non-shiny Pokémon
- `shiny-normal/` — shiny regular Pokémon
- `legendary/` and `shiny-legendary/`
- `mythical/` and `shiny-mythical/`
- `assets/backdrops/` — procedural scenery for forests, meadows, caves, snowy mountains, coasts, and starry ruins
- `spawns.json` — the small starter batch; add entries here to generate more
- `manifest.json` — generated index with species, rarity folder, backdrop, and artwork source URL

Backdrops are selected by habitat, not just by region. A region can use several scenes, and the same scene type can serve Pokémon from different regions.

## Generate

```bash
python -m pip install -r requirements.txt
python generate.py --workers 4
```

The starter catalog deliberately contains only **six outputs (one per rarity folder)**. Each Pokémon artwork is fetched from PokeAPI while jobs run concurrently; source artwork is not kept in a separate cache. Only the final composed images, generated backdrop PNGs, and manifest are written to this repository. Re-run after editing `spawns.json` to add entries; use `--force-backdrops` to redraw the procedural scenes.

PokeAPI provides the Pokémon artwork, not the scenery. The backdrops here are drawn by the script and do not copy Pokétwo's assets. Pokémon artwork remains the property of its respective rights holders; this is a fan-project asset set.
