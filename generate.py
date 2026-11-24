"""Build small, full-colour group-spawn images from PokeAPI artwork and procedural scenes.

Only final images and reusable backdrops are written to this repository; source artwork is loaded
into memory. Per-Pokemon downloads/composites run concurrently (default: four workers).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
SIZE = (960, 600)
ARTWORK_LIMIT = 12 * 1024 * 1024
USER_AGENT = "PikaBot-GroupSpawnArt/0.1 (+https://github.com/TheSunphis/group-chat-spawns)"
RARITY_FOLDERS = {
    "normal", "shiny-normal", "legendary", "shiny-legendary", "mythical", "shiny-mythical",
}
BACKDROP_DIR = ROOT / "assets" / "backdrops"


def _gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(image)
    for y in range(SIZE[1]):
        t = y / max(1, SIZE[1] - 1)
        colour = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line((0, y, SIZE[0], y), fill=(*colour, 255))
    return image


def _soft_sun(image: Image.Image, xy: tuple[int, int], radius: int,
              colour: tuple[int, int, int, int]) -> None:
    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    x, y = xy
    d.ellipse((x - radius, y - radius, x + radius, y + radius), fill=colour)
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius // 2)))
    ImageDraw.Draw(image).ellipse((x - radius // 2, y - radius // 2,
                                   x + radius // 2, y + radius // 2),
                                  fill=colour[:3] + (min(255, colour[3] + 35),))


def _forest(seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = _gradient((76, 142, 201), (205, 230, 220))
    d = ImageDraw.Draw(image)
    _soft_sun(image, (733, 126), 96, (255, 226, 155, 70))
    d = ImageDraw.Draw(image)
    d.polygon([(0, 300), (170, 224), (360, 303), (560, 218), (790, 296),
               (960, 220), (960, 600), (0, 600)], fill=(74, 133, 91, 255))
    d.polygon([(0, 362), (205, 296), (438, 355), (657, 290), (960, 358),
               (960, 600), (0, 600)], fill=(84, 157, 95, 255))
    # Distant tree line: deliberately soft and varied, not a copied game background.
    for x in range(-25, 1010, 46):
        height = rng.randint(82, 148)
        width = rng.randint(42, 78)
        top = rng.randint(206, 262)
        colour = rng.choice([(40, 103, 75, 255), (47, 119, 79, 255),
                             (56, 132, 86, 255), (63, 145, 91, 255)])
        d.rectangle((x + width // 3, top + height // 2, x + width * 2 // 3, 392),
                    fill=(91, 75, 54, 255))
        d.ellipse((x, top, x + width, top + height), fill=colour)
        d.ellipse((x - 15, top + 22, x + width // 2, top + height + 8), fill=colour)
    # Framing trunks and canopy at the edges leave a clear stage for the creature.
    for x, direction in ((-40, 1), (930, -1)):
        trunk_w = rng.randint(62, 92)
        d.polygon([(x, 80), (x + direction * 48, 84),
                   (x + direction * 78, 493), (x, 530)], fill=(82, 61, 45, 255))
        for j in range(8):
            cx = x + direction * rng.randint(25, 150)
            cy = rng.randint(18, 168)
            r = rng.randint(48, 104)
            d.ellipse((cx - r, cy - r, cx + r, cy + r),
                      fill=rng.choice([(35, 91, 63, 245), (43, 111, 70, 245),
                                       (57, 130, 78, 245)]))
    d.polygon([(0, 441), (171, 400), (370, 427), (610, 391), (960, 433),
               (960, 600), (0, 600)], fill=(73, 143, 77, 255))
    for _ in range(120):
        x, y = rng.randrange(SIZE[0]), rng.randrange(428, SIZE[1])
        c = rng.choice([(106, 174, 83, 180), (47, 119, 67, 170), (151, 190, 91, 160)])
        d.line((x, y, x + rng.randint(-4, 4), y - rng.randint(5, 14)), fill=c, width=2)
    return image.filter(ImageFilter.GaussianBlur(1.1))


def _meadow(seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = _gradient((113, 187, 235), (226, 242, 228))
    _soft_sun(image, (190, 123), 89, (255, 234, 164, 75))
    d = ImageDraw.Draw(image)
    d.ellipse((625, 70, 762, 207), fill=(255, 228, 154, 220))
    d.ellipse((660, 98, 824, 211), fill=(224, 240, 247, 205))
    d.polygon([(0, 330), (164, 248), (350, 337), (555, 246), (765, 334),
               (960, 264), (960, 600), (0, 600)], fill=(112, 172, 114, 255))
    d.polygon([(0, 385), (220, 311), (425, 383), (662, 302), (960, 379),
               (960, 600), (0, 600)], fill=(133, 190, 112, 255))
    d.polygon([(0, 443), (232, 393), (490, 431), (724, 379), (960, 426),
               (960, 600), (0, 600)], fill=(111, 173, 81, 255))
    for _ in range(180):
        x, y = rng.randrange(SIZE[0]), rng.randrange(395, SIZE[1])
        colour = rng.choice([(255, 237, 179, 230), (250, 172, 183, 225),
                             (248, 248, 226, 235), (207, 181, 243, 225)])
        r = rng.randint(2, 5)
        d.ellipse((x - r, y - r, x + r, y + r), fill=colour)
    return image.filter(ImageFilter.GaussianBlur(0.7))


def _cave(seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = _gradient((45, 68, 98), (93, 105, 117))
    d = ImageDraw.Draw(image)
    # A luminous opening behind the character, framed by uneven rock.
    light = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    ld = ImageDraw.Draw(light)
    ld.ellipse((225, 92, 760, 458), fill=(112, 179, 210, 120))
    image.alpha_composite(light.filter(ImageFilter.GaussianBlur(72)))
    d = ImageDraw.Draw(image)
    d.polygon([(0, 0), (215, 0), (250, 84), (186, 149), (214, 219),
               (154, 298), (191, 390), (0, 455)], fill=(39, 48, 61, 255))
    d.polygon([(960, 0), (747, 0), (720, 91), (783, 151), (750, 244),
               (807, 332), (770, 410), (960, 467)], fill=(38, 48, 62, 255))
    for _ in range(13):
        x = rng.randrange(0, SIZE[0])
        w = rng.randint(18, 56)
        h = rng.randint(35, 112)
        base = rng.randint(60, 150)
        d.polygon([(x, 0), (x + w, 0), (x + w // 2, h)],
                  fill=rng.choice([(43, 53, 67, 255), (55, 65, 77, 255)]))
        d.polygon([(x, 600), (x + w, 600), (x + w // 2, 600 - base)],
                  fill=(53, 63, 74, 255))
    d.polygon([(0, 472), (172, 427), (350, 459), (560, 421), (774, 459),
               (960, 427), (960, 600), (0, 600)], fill=(60, 70, 79, 255))
    for x, y, r in ((164, 456, 26), (792, 467, 31), (856, 440, 22)):
        d.polygon([(x, y - r), (x + r, y + r), (x - r, y + r)],
                  fill=(111, 202, 218, 230))
        d.polygon([(x, y - r), (x, y + r), (x - r, y + r)],
                  fill=(165, 229, 225, 245))
    return image.filter(ImageFilter.GaussianBlur(0.7))


def _snowy_mountain(seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = _gradient((100, 174, 226), (218, 235, 242))
    d = ImageDraw.Draw(image)
    _soft_sun(image, (762, 123), 72, (255, 248, 225, 75))
    d = ImageDraw.Draw(image)
    d.polygon([(0, 365), (165, 190), (315, 354), (523, 145), (756, 356),
               (875, 222), (960, 328), (960, 600), (0, 600)], fill=(112, 149, 184, 255))
    d.polygon([(80, 282), (165, 190), (235, 285), (176, 258), (151, 271),
               (121, 252)], fill=(239, 247, 252, 255))
    d.polygon([(390, 275), (523, 145), (653, 276), (576, 246), (538, 258),
               (503, 232), (466, 260)], fill=(242, 249, 253, 255))
    d.polygon([(0, 389), (211, 319), (411, 375), (676, 306), (960, 373),
               (960, 600), (0, 600)], fill=(190, 218, 227, 255))
    # Pine silhouettes sit at the edges so the foreground art remains readable.
    for x in (45, 112, 851, 916):
        h = rng.randint(140, 220)
        base = rng.randint(431, 482)
        for tier in range(3):
            y = base - h + tier * h // 4
            half = (h - tier * h // 4) // 3
            d.polygon([(x, y), (x - half, y + half * 2), (x + half, y + half * 2)],
                      fill=(52, 103, 117, 255))
        d.rectangle((x - 5, base - 15, x + 5, base + 25), fill=(100, 86, 74, 255))
    d.polygon([(0, 471), (182, 436), (394, 473), (627, 429), (960, 468),
               (960, 600), (0, 600)], fill=(230, 241, 242, 255))
    return image.filter(ImageFilter.GaussianBlur(0.65))


def _coast(seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = _gradient((111, 190, 237), (244, 228, 184))
    d = ImageDraw.Draw(image)
    _soft_sun(image, (743, 111), 84, (255, 237, 171, 75))
    d = ImageDraw.Draw(image)
    d.ellipse((96, 168, 291, 215), fill=(245, 251, 253, 120))
    d.ellipse((150, 146, 355, 216), fill=(245, 251, 253, 170))
    d.rectangle((0, 288, 960, 472), fill=(62, 159, 196, 255))
    for i in range(7):
        y = 306 + i * 23
        d.arc((rng.randint(-80, 550), y, rng.randint(500, 1080), y + 42),
              start=180, end=355, fill=(188, 231, 226, 180), width=5)
    d.polygon([(0, 437), (166, 409), (347, 434), (524, 403), (711, 440),
               (960, 414), (960, 600), (0, 600)], fill=(222, 198, 143, 255))
    d.polygon([(0, 495), (245, 466), (476, 503), (702, 459), (960, 493),
               (960, 600), (0, 600)], fill=(213, 187, 128, 255))
    for _ in range(140):
        x, y = rng.randrange(SIZE[0]), rng.randrange(486, SIZE[1])
        d.ellipse((x, y, x + 3, y + 2), fill=(244, 225, 174, 200))
    return image.filter(ImageFilter.GaussianBlur(0.7))


def _starry_ruins(seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = _gradient((24, 35, 77), (90, 92, 133))
    d = ImageDraw.Draw(image)
    _soft_sun(image, (730, 147), 62, (225, 218, 255, 55))
    d = ImageDraw.Draw(image)
    for _ in range(115):
        x, y = rng.randrange(SIZE[0]), rng.randrange(0, 360)
        r = rng.choice((1, 2, 2, 3))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(224, 231, 255, rng.randint(120, 245)))
    d.polygon([(0, 398), (144, 329), (306, 387), (498, 312), (712, 383),
               (877, 329), (960, 370), (960, 600), (0, 600)], fill=(59, 73, 101, 255))
    d.polygon([(0, 449), (218, 404), (407, 439), (653, 397), (960, 445),
               (960, 600), (0, 600)], fill=(67, 77, 102, 255))
    # Ancient columns and broken lintels frame, rather than cover, the subject.
    for x, width, height in ((58, 54, 203), (850, 58, 248)):
        y = 514 - height
        d.rectangle((x, y, x + width, 517), fill=(93, 98, 123, 255))
        d.rectangle((x - 12, y + 9, x + width + 12, y + 28), fill=(125, 125, 148, 255))
        for yy in range(y + 42, 505, 47):
            d.line((x + 10, yy, x + width - 10, yy + rng.randint(-2, 2)),
                   fill=(129, 129, 151, 150), width=3)
    d.polygon([(0, 501), (180, 477), (421, 508), (683, 468), (960, 500),
               (960, 600), (0, 600)], fill=(77, 83, 108, 255))
    return image.filter(ImageFilter.GaussianBlur(0.8))


SCENES = {
    "forest": _forest,
    "meadow": _meadow,
    "cave": _cave,
    "snowy-mountain": _snowy_mountain,
    "coast": _coast,
    "starry-ruins": _starry_ruins,
}


def create_backdrops(spawns: list[dict], *, force: bool = False) -> None:
    BACKDROP_DIR.mkdir(parents=True, exist_ok=True)
    for scene in sorted({str(row["backdrop"]) for row in spawns}):
        draw_scene = SCENES.get(scene)
        if draw_scene is None:
            raise ValueError(f"unknown backdrop scene: {scene}")
        target = BACKDROP_DIR / f"{scene}.png"
        if force or not target.exists():
            image = draw_scene(seed=sum(map(ord, scene)))
            image.save(target, format="PNG", optimize=True)


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
    # Trim transparent padding from official art without flattening its alpha edges.
    bbox = image.getchannel("A").getbbox()
    if bbox:
        image = image.crop(bbox)
    return image, source_url, pixel_sprite


def _compose(backdrop: Image.Image, artwork: Image.Image, *, pixel_sprite: bool) -> Image.Image:
    canvas = backdrop.convert("RGBA").copy()
    subject = artwork.convert("RGBA")
    max_width, max_height = 480, 430
    ratio = min(max_width / subject.width, max_height / subject.height)
    dimensions = (max(1, round(subject.width * ratio)), max(1, round(subject.height * ratio)))
    resample = Image.Resampling.NEAREST if pixel_sprite else Image.Resampling.LANCZOS
    subject = subject.resize(dimensions, resample)
    x = (SIZE[0] - subject.width) // 2
    ground_y = 506
    y = ground_y - subject.height

    # The dark, soft-edged oval is intentionally visible below the full-colour artwork.
    shadow_layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    shadow = ImageDraw.Draw(shadow_layer)
    shadow_width = max(96, min(260, round(subject.width * 0.55)))
    shadow_height = 38
    cx = SIZE[0] // 2
    cy = ground_y + 8
    shadow.ellipse((cx - shadow_width // 2, cy - shadow_height // 2,
                    cx + shadow_width // 2, cy + shadow_height // 2),
                   fill=(0, 0, 0, 175))
    canvas.alpha_composite(shadow_layer.filter(ImageFilter.GaussianBlur(11)))
    canvas.alpha_composite(subject, (x, y))
    return canvas.convert("RGB")


def _filename(entry: dict) -> str:
    safe = re.sub(r"[^a-z0-9-]+", "-", str(entry["name"]).lower()).strip("-")
    suffix = "-shiny" if entry.get("shiny", False) else ""
    return f"{int(entry['id']):04d}-{safe}{suffix}.png"


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
    image = _compose(backdrop, artwork, pixel_sprite=pixel_sprite)

    output = ROOT / folder / _filename(entry)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)
    return {
        "id": int(entry["id"]), "name": str(entry["name"]),
        "folder": folder, "shiny": shiny, "region": str(entry.get("region", "")),
        "backdrop": str(entry["backdrop"]), "file": output.relative_to(ROOT).as_posix(),
        "artwork_url": source_url, "used_pokemon_sprite_fallback": pixel_sprite,
        "size": list(image.size),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4,
                        help="parallel species downloads/composites (default: 4)")
    parser.add_argument("--force-backdrops", action="store_true",
                        help="redraw the procedural background PNGs")
    args = parser.parse_args(argv)
    if args.workers < 1 or args.workers > 16:
        parser.error("--workers must be between 1 and 16")

    spawns = json.loads((ROOT / "spawns.json").read_text(encoding="utf-8"))
    create_backdrops(spawns, force=args.force_backdrops)
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
    manifest = {"version": 1, "canvas": list(SIZE), "count": len(results), "spawns": results}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nGenerated {len(results)} of {len(spawns)} starter images with {args.workers} worker(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
