"""Build PikaBot-styled group-spawn cards from PokeAPI artwork and scenic backdrops.

The committed background plates are high-resolution habitat illustrations. This script fetches
PokeAPI artwork into memory, composites it over a chosen plate with a soft black ground shadow, then
frames the scene in the bot's dark pixel-card style. Per-Pokemon jobs run concurrently (default: four
workers).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from bot_style import SIZE, render_spawn_card

ROOT = Path(__file__).resolve().parent
SCENE_SIZE = (960, 600)
ARTWORK_LIMIT = 12 * 1024 * 1024
USER_AGENT = "PikaBot-GroupSpawnArt/0.2 (+https://github.com/TheSunphis/group-chat-spawns)"
RARITY_FOLDERS = {
    "normal", "shiny-normal", "legendary", "shiny-legendary", "mythical", "shiny-mythical",
}
BACKDROP_DIR = ROOT / "assets" / "backdrops"


def validate_backdrops(spawns: list[dict]) -> None:
    """Fail early if a spawn refers to a missing or unreadable scenic background."""
    scenes = sorted({str(row["backdrop"]) for row in spawns})
    for scene in scenes:
        path = BACKDROP_DIR / f"{scene}.png"
        if not path.is_file():
            raise FileNotFoundError(f"backdrop is missing: {path.relative_to(ROOT)}")
        with Image.open(path) as image:
            if image.width < 800 or image.height < 500:
                raise ValueError(f"backdrop is too small for a spawn image: {path.name} ({image.size})")
            image.verify()


def _request(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(ARTWORK_LIMIT + 1)
    if len(data) > ARTWORK_LIMIT:
        raise ValueError(f"download too large: {url}")
    return data


def fetch_artwork(pokemon_id: int, *, shiny: bool) -> tuple[Image.Image, str, bool]:
    """Fetch this form's PokeAPI official artwork, falling back only to its PokeAPI sprite."""
    payload = json.loads(_request(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}/"))
    sprites = payload.get("sprites") or {}
    official = ((sprites.get("other") or {}).get("official-artwork") or {})
    source_url = official.get("front_shiny" if shiny else "front_default")
    pixel_sprite = False
    if not source_url:
        source_url = sprites.get("front_shiny" if shiny else "front_default")
        pixel_sprite = bool(source_url)
    if not source_url:
        kind = "shiny" if shiny else "normal"
        raise ValueError(f"PokeAPI has no {kind} artwork or sprite for #{pokemon_id}")
    data = _request(source_url)
    with Image.open(BytesIO(data)) as picture:
        picture.load()
        image = picture.convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox:
        image = image.crop(bbox)
    return image, source_url, pixel_sprite


def _compose(backdrop: Image.Image, artwork: Image.Image, *, pixel_sprite: bool) -> Image.Image:
    """Compose the cutout with a clear ground-contact shadow."""
    canvas = ImageOps.fit(backdrop.convert("RGBA"), SCENE_SIZE, method=Image.Resampling.LANCZOS,
                          centering=(0.5, 0.5))
    subject = artwork.convert("RGBA")
    max_width, max_height = 480, 430
    ratio = min(max_width / subject.width, max_height / subject.height)
    dimensions = (max(1, round(subject.width * ratio)), max(1, round(subject.height * ratio)))
    resample = Image.Resampling.NEAREST if pixel_sprite else Image.Resampling.LANCZOS
    subject = subject.resize(dimensions, resample)
    x = (SCENE_SIZE[0] - subject.width) // 2

    ground_y = 514
    y = ground_y - subject.height
    shadow_width = max(120, min(280, round(subject.width * 0.56)))
    shadow_height, cy, alpha, blur = 28, ground_y + 14, 205, 7

    shadow_layer = Image.new("RGBA", SCENE_SIZE, (0, 0, 0, 0))
    shadow = ImageDraw.Draw(shadow_layer)
    cx = SCENE_SIZE[0] // 2
    shadow.ellipse((cx - shadow_width // 2, cy - shadow_height // 2,
                    cx + shadow_width // 2, cy + shadow_height // 2),
                   fill=(0, 0, 0, alpha))
    canvas.alpha_composite(shadow_layer.filter(ImageFilter.GaussianBlur(blur)))
    canvas.alpha_composite(subject, (x, y))
    return canvas.convert("RGB")


def _filename(entry: dict) -> str:
    safe = re.sub(r"[^a-z0-9-]+", "-", str(entry["name"]).lower()).strip("-")
    suffix = "-shiny" if entry.get("shiny", False) else ""
    return f"{int(entry['id']):04d}-{safe}{suffix}.jpg"


def render_spawn(entry: dict) -> dict:
    folder = str(entry["folder"])
    if folder not in RARITY_FOLDERS:
        raise ValueError(f"invalid rarity folder: {folder}")
    shiny = bool(entry.get("shiny", False))
    if shiny != folder.startswith("shiny-"):
        raise ValueError(f"shiny flag and folder disagree for {entry['name']}")
    backdrop_path = BACKDROP_DIR / f"{entry['backdrop']}.png"
    with Image.open(backdrop_path) as source:
        backdrop = source.convert("RGBA")
    artwork, source_url, pixel_sprite = fetch_artwork(int(entry["id"]), shiny=shiny)
    scene = _compose(backdrop, artwork, pixel_sprite=pixel_sprite)
    rarity = folder.removeprefix("shiny-")
    image = render_spawn_card(
        scene, species_id=int(entry["id"]), form=str(entry["name"]),
        pokemon=str(entry["name"]), species=str(entry.get("species", entry["name"])),
        rarity=rarity, shiny=shiny, region=str(entry.get("region", "")),
        catch_name=str(entry.get("catch_name", entry.get("name", ""))),
    )
    scene.close()

    output = ROOT / folder / _filename(entry)
    output.parent.mkdir(parents=True, exist_ok=True)
    image_size = list(image.size)
    image.save(output, format="JPEG", quality=88, optimize=True, progressive=True)
    image.close()
    artwork.close()
    backdrop.close()
    return {
        "id": int(entry["id"]), "name": str(entry["name"]),
        "folder": folder, "shiny": shiny, "region": str(entry.get("region", "")),
        "backdrop": str(entry["backdrop"]), "file": output.relative_to(ROOT).as_posix(),
        "artwork_url": source_url, "used_pokemon_sprite_fallback": pixel_sprite,
        "size": image_size,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4,
                        help="parallel species downloads/composites (default: 4)")
    args = parser.parse_args(argv)
    if args.workers < 1 or args.workers > 16:
        parser.error("--workers must be between 1 and 16")

    spawns = json.loads((ROOT / "spawns.json").read_text(encoding="utf-8"))
    validate_backdrops(spawns)
    results: list[dict] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="spawn-art") as pool:
        futures = {pool.submit(render_spawn, row): row for row in spawns}
        for future in as_completed(futures):
            row = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"generated {result['file']}")
            except Exception as exc:  # noqa: BLE001 — report each failed species, keep other jobs
                failures.append(f"{row.get('name', row.get('id'))}: {exc}")
                print(f"failed {row.get('name', row.get('id'))}: {exc}", file=sys.stderr)

    results.sort(key=lambda row: (row["folder"], row["id"]))
    manifest = {"version": 1, "canvas": list(SIZE), "image_style": "pikabot-guess-card",
                "count": len(results), "spawns": results}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nGenerated {len(results)} of {len(spawns)} starter images with {args.workers} worker(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
