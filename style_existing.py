"""Frame an existing group-spawn dataset in the PikaBot `/guess` card style.

This migration reads the already-composited JPEGs, writes each styled file atomically, and never
redownloads Pokémon artwork. It is safe to resume: completed 960x640 cards are skipped.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Callable, Iterable, Iterator, TypeVar

from PIL import Image

from bot_style import SIZE, pokemon_display_name, pokemon_region, render_spawn_card

ROOT = Path(__file__).resolve().parent
T = TypeVar("T")
U = TypeVar("U")


def bounded_map(function: Callable[[T], U], items: Iterable[T], workers: int) -> Iterator[U]:
    iterator = iter(items)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="spawn-card") as pool:
        pending = set()
        for _ in range(workers * 2):
            try:
                pending.add(pool.submit(function, next(iterator)))
            except StopIteration:
                break
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                yield future.result()
                try:
                    pending.add(pool.submit(function, next(iterator)))
                except StopIteration:
                    pass


def transform(root: Path, row: dict) -> dict:
    if not row.get("available", True):
        return row
    path = root / row["file"]
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as source:
        source.load()
        current_size = source.size
        scene = source.convert("RGB")
    updated = dict(row)
    label = str(row.get("display_name") or pokemon_display_name(
        form=str(row.get("form") or ""), pokemon=str(row.get("pokemon") or ""),
        species=str(row.get("species") or "")))
    region = str(row.get("region") or pokemon_region(
        species_id=int(row.get("species_id") or 0), form=str(row.get("form") or ""),
        pokemon=str(row.get("pokemon") or "")))
    if current_size != SIZE:
        card = render_spawn_card(
            scene,
            species_id=int(row.get("species_id") or 0),
            form=str(row.get("form") or ""),
            pokemon=str(row.get("pokemon") or ""),
            species=str(row.get("species") or ""),
            rarity=str(row.get("rarity") or "normal"),
            shiny=bool(row.get("shiny", False)),
            region=region,
            display_name=label,
            catch_name=str(row.get("species") or row.get("pokemon") or row.get("form") or ""),
        )
        temp = path.with_name(f".{path.stem}.{os.getpid()}.tmp.jpg")
        try:
            card.save(temp, format="JPEG", quality=88, optimize=True, progressive=True)
            os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink()
            card.close()
    scene.close()
    updated["display_name"] = label
    updated["region"] = region
    updated["size"] = list(SIZE)
    return updated


def atomic_json(path: Path, data: dict) -> None:
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="dataset directory (default: repo root)")
    parser.add_argument("--workers", type=int, default=4, help="bounded concurrent image jobs (max 12)")
    args = parser.parse_args()
    if not 1 <= args.workers <= 12:
        parser.error("--workers must be between 1 and 12")
    root = args.root.resolve()
    manifest_path = root / "manifest-all.json"
    if not manifest_path.is_file():
        parser.error(f"missing {manifest_path}; run generate_all.py first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest.get("images") or []
    if not rows:
        parser.error("manifest-all.json has no image rows")

    transformed: list[dict] = []
    errors: list[str] = []
    for index, item in enumerate(bounded_map(lambda row: transform(root, row), rows, args.workers), 1):
        transformed.append(item)
        if index % 250 == 0 or index == len(rows):
            print(f"Styled {index}/{len(rows)} images", flush=True)
    transformed.sort(key=lambda row: (row["file"], row.get("shiny", False)))
    manifest["images"] = transformed
    manifest["canvas"] = list(SIZE)
    manifest["image_style"] = "pikabot-guess-card"
    atomic_json(manifest_path, manifest)

    starter_path = root / "manifest.json"
    if starter_path.is_file():
        starter = json.loads(starter_path.read_text(encoding="utf-8"))
        starter["canvas"] = list(SIZE)
        starter["image_style"] = "pikabot-guess-card"
        for row in starter.get("spawns", []):
            row["size"] = list(SIZE)
            if row.get("name"):
                row["display_name"] = pokemon_display_name(
                    form=str(row["name"]), pokemon=str(row["name"]), species=str(row["name"]))
        atomic_json(starter_path, starter)
    available = sum(bool(row.get("available", True)) for row in transformed)
    print(f"Done: {available} existing spawn images now use the PikaBot card style.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
