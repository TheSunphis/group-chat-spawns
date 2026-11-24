"""Generate regular and shiny composites for every PokeAPI Pokémon form.

Image downloads are processed by a bounded worker pool and saved immediately as JPEGs. Original
PokeAPI artwork is never cached; only the final spawn images and a compact manifest remain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Callable, Iterable, Iterator, TypeVar

from PIL import Image

from generate import BACKDROP_DIR, ROOT, SIZE, _compose

API = "https://pokeapi.co/api/v2"
USER_AGENT = "PikaBot-GroupSpawnArt/1.0 (+https://github.com/TheSunphis/group-chat-spawns)"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
JPEG_QUALITY = 88
BACKDROP_NAMES = ("forest", "meadow", "cave", "snowy-mountain", "coast", "starry-ruins")
RARITY_FOLDERS = {"normal", "shiny-normal", "legendary", "shiny-legendary", "mythical", "shiny-mythical"}
HABITAT_BACKDROPS = {
    "forest": "forest",
    "grassland": "meadow",
    "cave": "cave",
    "mountain": "snowy-mountain",
    "sea": "coast",
    "water-edge": "coast",
    "waters-edge": "coast",
    "urban": "starry-ruins",
    "rare": "starry-ruins",
    "rough-terrain": "cave",
}
TYPE_BACKDROPS = {
    "water": "coast", "ice": "snowy-mountain", "grass": "forest", "bug": "forest",
    "normal": "meadow", "fairy": "meadow", "electric": "meadow", "flying": "meadow",
    "fire": "meadow", "fighting": "cave", "rock": "cave", "ground": "cave",
    "steel": "cave", "poison": "cave", "ghost": "starry-ruins",
    "psychic": "starry-ruins", "dark": "starry-ruins", "dragon": "starry-ruins",
}
T = TypeVar("T")
U = TypeVar("U")


def fetch_bytes(url: str) -> bytes:
    """Fetch one API response or artwork file with bounded size and transient retries."""
    for attempt in range(6):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
                if len(data) > MAX_RESPONSE_BYTES:
                    raise ValueError(f"response exceeds size limit: {url}")
                return data
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 5:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 30)
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 5:
                raise
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"request retries exhausted: {url}")


def fetch_json(url: str) -> dict:
    return json.loads(fetch_bytes(url))


def bounded_map(function: Callable[[T], U], items: Iterable[T], workers: int) -> Iterator[U]:
    """Map without queuing the full catalog: at most 2×workers futures are alive."""
    iterator = iter(items)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pokeapi") as pool:
        pending = set()
        for _ in range(workers * 2):
            try:
                pending.add(pool.submit(function, next(iterator)))
            except StopIteration:
                break
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                result = future.result()
                yield result
                try:
                    pending.add(pool.submit(function, next(iterator)))
                except StopIteration:
                    pass


def _report_collect(label: str, function: Callable[[T], U], items: list[T], workers: int) -> list[U]:
    results: list[U] = []
    for index, value in enumerate(bounded_map(function, items, workers), start=1):
        results.append(value)
        if index % 250 == 0 or index == len(items):
            print(f"{label}: {index}/{len(items)}", flush=True)
    return results


def list_resource(resource: str) -> tuple[int, list[dict]]:
    payload = fetch_json(f"{API}/{resource}/?limit=10000")
    return int(payload["count"]), payload["results"]


def read_form(url_row: dict) -> dict:
    payload = fetch_json(url_row["url"])
    sprites = payload.get("sprites") or {}
    official = ((sprites.get("other") or {}).get("official-artwork") or {})
    return {
        "form_id": int(payload["id"]),
        "form_name": str(payload["name"]),
        "form_label": str(payload.get("form_name") or ""),
        "pokemon_name": str((payload.get("pokemon") or {}).get("name") or ""),
        "is_default": bool(payload.get("is_default")),
        "is_battle_only": bool(payload.get("is_battle_only")),
        "is_mega": bool(payload.get("is_mega")),
        "form_official_normal": official.get("front_default"),
        "form_official_shiny": official.get("front_shiny"),
        "form_sprite_normal": sprites.get("front_default"),
        "form_sprite_shiny": sprites.get("front_shiny"),
    }


def read_pokemon(name: str) -> dict:
    payload = fetch_json(f"{API}/pokemon/{name}/")
    sprites = payload.get("sprites") or {}
    official = ((sprites.get("other") or {}).get("official-artwork") or {})
    species = payload.get("species") or {}
    return {
        "pokemon_name": str(payload["name"]),
        "species_name": str(species.get("name") or ""),
        "species_url": species.get("url"),
        "types": [entry["type"]["name"] for entry in sorted(payload.get("types", []), key=lambda x: x["slot"])],
        "pokemon_official_normal": official.get("front_default"),
        "pokemon_official_shiny": official.get("front_shiny"),
        "pokemon_sprite_normal": sprites.get("front_default"),
        "pokemon_sprite_shiny": sprites.get("front_shiny"),
    }


def read_species(url: str) -> dict:
    payload = fetch_json(url)
    habitat = payload.get("habitat") or {}
    return {
        "species_id": int(payload["id"]),
        "species_name": str(payload["name"]),
        "is_legendary": bool(payload.get("is_legendary")),
        "is_mythical": bool(payload.get("is_mythical")),
        "habitat": str(habitat.get("name") or ""),
    }


def choose_artwork(form: dict, pokemon: dict, shiny: bool) -> tuple[str | None, str | None, bool]:
    suffix = "shiny" if shiny else "normal"
    candidates = (
        (form.get(f"form_official_{suffix}"), "form-official-artwork", False),
        (form.get(f"form_sprite_{suffix}"), "form-sprite", True),
        (pokemon.get(f"pokemon_official_{suffix}"), "pokemon-official-artwork-fallback", False),
        (pokemon.get(f"pokemon_sprite_{suffix}"), "pokemon-sprite-fallback", True),
    )
    for url, source, pixel_sprite in candidates:
        if url:
            return str(url), source, pixel_sprite
    return None, None, False


def choose_backdrop(species: dict, pokemon: dict, form_name: str, overrides: dict) -> str:
    key = (species["species_id"], form_name)
    if key in overrides:
        return overrides[key]
    habitat = species.get("habitat", "").lower().replace("'", "").replace("_", "-")
    if habitat in HABITAT_BACKDROPS:
        return HABITAT_BACKDROPS[habitat]
    for type_name in pokemon.get("types", []):
        if type_name in TYPE_BACKDROPS:
            return TYPE_BACKDROPS[type_name]
    digest = hashlib.sha256(f"{species['species_id']}:{form_name}".encode()).digest()
    return BACKDROP_NAMES[digest[0] % len(BACKDROP_NAMES)]


def safe_slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return value or "unknown-form"


def output_file(output_root: Path, species: dict, form_name: str, shiny: bool) -> Path:
    rarity = "mythical" if species["is_mythical"] else "legendary" if species["is_legendary"] else "normal"
    folder = f"shiny-{rarity}" if shiny else rarity
    if folder not in RARITY_FOLDERS:
        raise ValueError(f"unexpected rarity folder: {folder}")
    name = f"{species['species_id']:04d}-{safe_slug(form_name)}{'-shiny' if shiny else ''}.jpg"
    return output_root / folder / name


def load_artwork(url: str) -> Image.Image:
    from io import BytesIO

    with Image.open(BytesIO(fetch_bytes(url))) as source:
        source.load()
        image = source.convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox:
        cropped = image.crop(bbox)
        image.close()
        image = cropped
    return image


def render_one(form: dict, pokemon_map: dict, species_map: dict, overrides: dict,
               output_root: Path, force: bool) -> dict:
    pokemon = pokemon_map[form["pokemon_name"]]
    species = species_map[pokemon["species_name"]]
    backdrop_name = choose_backdrop(species, pokemon, form["form_name"], overrides)
    rows = []
    errors = []
    for shiny in (False, True):
        url, source_kind, pixel_sprite = choose_artwork(form, pokemon, shiny)
        path = output_file(output_root, species, form["form_name"], shiny)
        row = {
            "form_id": form["form_id"], "form": form["form_name"],
            "pokemon": pokemon["pokemon_name"], "species_id": species["species_id"],
            "species": species["species_name"], "rarity": "mythical" if species["is_mythical"] else "legendary" if species["is_legendary"] else "normal",
            "shiny": shiny, "backdrop": backdrop_name,
            "file": path.relative_to(output_root).as_posix(),
            "artwork_url": url, "artwork_source": source_kind,
            "used_pokemon_sprite_fallback": bool(pixel_sprite),
            "is_default_form": form["is_default"],
            "is_battle_only": form["is_battle_only"], "is_mega": form["is_mega"],
            "size": list(SIZE),
        }
        if not url:
            row["available"] = False
            row["error"] = "PokeAPI has no artwork or sprite for this variant"
            rows.append(row)
            continue
        if path.is_file() and not force:
            row["available"] = True
            row["status"] = "already-present"
            rows.append(row)
            continue
        try:
            artwork = load_artwork(url)
            try:
                with Image.open(BACKDROP_DIR / f"{backdrop_name}.png") as source:
                    backdrop = source.convert("RGBA")
                try:
                    composite = _compose(backdrop, artwork, pixel_sprite=bool(pixel_sprite))
                    path.parent.mkdir(parents=True, exist_ok=True)
                    temp = path.with_name(f".{path.stem}.{os.getpid()}.tmp.jpg")
                    try:
                        composite.save(temp, format="JPEG", quality=JPEG_QUALITY,
                                       optimize=True, progressive=True)
                        os.replace(temp, path)
                    finally:
                        if temp.exists():
                            temp.unlink()
                finally:
                    backdrop.close()
            finally:
                artwork.close()
            composite.close()
            row["available"] = True
            row["status"] = "generated"
            rows.append(row)
        except Exception as exc:  # report per variant and continue the full catalog
            row["available"] = False
            row["error"] = f"{type(exc).__name__}: {exc}"
            rows.append(row)
            errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
    return {"form": form["form_name"], "rows": rows, "errors": errors}


def load_overrides() -> dict:
    spawns_path = ROOT / "spawns.json"
    if not spawns_path.exists():
        return {}
    overrides = {}
    for entry in json.loads(spawns_path.read_text(encoding="utf-8")):
        if "backdrop" in entry:
            overrides[(int(entry["id"]), str(entry["name"]).lower())] = str(entry["backdrop"])
    return overrides


def atomic_json(path: Path, data: dict) -> None:
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4,
                        help="bounded concurrent workers (default: 4; max: 12)")
    parser.add_argument("--limit", type=int,
                        help="process only the first N forms (useful for a test run)")
    parser.add_argument("--output-root", type=Path, default=ROOT,
                        help="destination root; defaults to the repository directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="enumerate availability without downloading image files")
    parser.add_argument("--force", action="store_true",
                        help="regenerate files even if an output already exists")
    args = parser.parse_args(argv)
    if args.workers < 1 or args.workers > 12:
        parser.error("--workers must be between 1 and 12")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    output_root = args.output_root.resolve()
    for name in BACKDROP_NAMES:
        path = BACKDROP_DIR / f"{name}.png"
        if not path.is_file():
            raise FileNotFoundError(f"missing backdrop: {path}")

    form_count, form_list = list_resource("pokemon-form")
    if args.limit:
        form_list = form_list[:args.limit]
    print(f"PokeAPI lists {form_count} Pokémon forms; processing {len(form_list)}.", flush=True)
    forms = _report_collect("Form metadata", read_form, form_list, args.workers)
    pokemon_names = sorted({form["pokemon_name"] for form in forms if form["pokemon_name"]})
    pokemon_data = _report_collect("Pokémon metadata", read_pokemon, pokemon_names, args.workers)
    pokemon_map = {item["pokemon_name"]: item for item in pokemon_data}
    species_urls = sorted({item["species_url"] for item in pokemon_data if item["species_url"]})
    species_data = _report_collect("Species rarity/habitat metadata", read_species, species_urls, args.workers)
    species_map = {item["species_name"]: item for item in species_data}
    missing_map = [form["form_name"] for form in forms if form["pokemon_name"] not in pokemon_map]
    if missing_map:
        raise RuntimeError(f"PokeAPI forms with no Pokémon metadata: {', '.join(missing_map[:10])}")

    # Resolve the metadata in advance so every render task needs only one form record.
    overrides = load_overrides()
    prepared = []
    missing_species = []
    for form in forms:
        pokemon = pokemon_map[form["pokemon_name"]]
        if pokemon["species_name"] not in species_map:
            missing_species.append(form["form_name"])
            continue
        prepared.append(form)
    if missing_species:
        raise RuntimeError(f"PokeAPI species metadata missing for forms: {', '.join(missing_species[:10])}")

    missing_normal = missing_shiny = 0
    for form in forms:
        pokemon = pokemon_map[form["pokemon_name"]]
        species = species_map[pokemon["species_name"]]
        missing_normal += choose_artwork(form, pokemon, False)[0] is None
        missing_shiny += choose_artwork(form, pokemon, True)[0] is None
    print(f"Resolved {len(species_data)} species and {len(pokemon_data)} Pokémon records; "
          f"missing PokeAPI art URLs — normal: {missing_normal}, shiny: {missing_shiny}.", flush=True)
    if args.dry_run:
        return 0

    progress_path = output_root / ".bulk-progress.jsonl"
    output_root.mkdir(parents=True, exist_ok=True)
    output_rows: list[dict] = []
    errors: list[str] = []
    generated = 0
    with progress_path.open("w", encoding="utf-8") as progress:
        for index, result in enumerate(
            bounded_map(lambda form: render_one(form, pokemon_map, species_map, overrides,
                                                output_root, args.force), forms, args.workers),
            start=1,
        ):
            output_rows.extend(result["rows"])
            errors.extend(result["errors"])
            generated += sum(row.get("status") == "generated" for row in result["rows"])
            progress.write(json.dumps(result, ensure_ascii=False) + "\n")
            progress.flush()
            if index % 25 == 0 or index == len(forms):
                print(f"Rendered {index}/{len(forms)} forms; wrote {generated} new JPEGs.", flush=True)

    output_rows.sort(key=lambda row: (row["file"], row["shiny"]))
    available = sum(row.get("available", False) for row in output_rows)
    missing = [row for row in output_rows if not row.get("available", False)]
    manifest = {
        "version": 1,
        "source": "PokeAPI",
        "canvas": list(SIZE),
        "format": f"JPEG quality {JPEG_QUALITY}",
        "form_count": len(forms),
        "available_image_count": available,
        "missing_image_count": len(missing),
        "generated_in_this_run": generated,
        "workers": args.workers,
        "images": output_rows,
        "errors": errors,
    }
    atomic_json(output_root / "manifest-all.json", manifest)
    progress_path.unlink(missing_ok=True)
    print(f"Finished: {len(forms)} forms, {available} images, {len(missing)} unavailable, "
          f"{generated} newly generated; manifest-all.json updated.", flush=True)
    if errors:
        print(f"Warning: {len(errors)} image download/composite errors; see manifest-all.json.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
