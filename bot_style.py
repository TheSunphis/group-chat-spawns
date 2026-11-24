"""PikaBot-themed frame for group-spawn images.

The palette, 5x7 glyphs, frame and doubled 480x320 layout follow the bot's /guess cards. The pixel
font is vendored here so this asset generator remains standalone from the bot runtime.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageOps

FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"),
    "J": ("..##", "...#", "...#", "...#", "...#", "#..#", ".##."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#...#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".###.", "#....", "#....", "#....", ".###."),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#...", "###..", ".#...", ".#...", ".#...", ".#..."),
    "g": (".....", ".....", ".###.", "#...#", "#...#", ".####", "....#", "###.."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..",".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", "...#.", "##..."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#...#", "#...#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "####.", "#....", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#", "....#"),
    "r": (".....", ".....", "#.##.", "##...", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "###..", ".#...", ".#...", ".#...", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", "#...#", ".####", "....#", "###.."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "#": (".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".....", "....."),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    " ": ("...", "...", "...", "...", "...", "...", "..."),
    ".": (".....", ".....", ".....", ".....", ".....", ".....", "..#.."),
    ",": (".....", ".....", ".....", ".....", ".....", "..#..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ":": (".....", "..#..", ".....", ".....", "..#..", ".....", "....."),
    ";": (".....", "..#..", ".....", ".....", "..#..", ".#...", "....."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "*": (".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "%": ("##..#", "##.#.", "..#..", ".#...", "#..##", "...##", "....."),
    "^": ("..#..", ".###.", "#...#", ".....", ".....", ".....", "....."),
    # the ones a quest name actually uses. "Catching 101 & Field Supplies" was drawn as
    # "Catching 101 Field Supplies" because the font had no ampersand and the sanitiser dropped it.
    "&": (".##..", "#..#.", "#..#.", ".##..", "#..#.", "#...#", ".##.#"),
    "=": (".....", "#####", ".....", "#####", ".....", ".....", "....."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "#": (".....", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", "....."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
}
TRACKING = 1
_FOLD = str.maketrans({
    "\u2014": "-", "\u2013": "-", "\u2212": "-", "\u2012": "-", "\u2015": "-",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2026": "...",
    "\u00d7": "x", "\u00b7": "-", "\u2022": "-",
})


def fold(text: str) -> str:
    return text.translate(_FOLD)


def text_width(text: str, scale: int = 1) -> int:
    text = fold(text)
    if not text:
        return 0
    return (sum(len(FONT.get(char, FONT["?"])[0]) + TRACKING for char in text) - TRACKING) * scale


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
              fill, scale: int = 1) -> None:
    x, y = xy
    for char in fold(text):
        glyph = FONT.get(char, FONT["?"])
        for row, bits in enumerate(glyph):
            for column, bit in enumerate(bits):
                if bit == "#":
                    left, top = x + column * scale, y + row * scale
                    if scale == 1:
                        draw.point((left, top), fill=fill)
                    else:
                        draw.rectangle((left, top, left + scale - 1, top + scale - 1), fill=fill)
        x += (len(glyph[0]) + TRACKING) * scale


# Same palette as pika/theme.py.
PAPER = (30, 34, 45)
CREAM = (38, 43, 58)
PANEL_DEEP = (26, 30, 40)
INK = (235, 240, 248)
DIM = (150, 162, 186)
BORDER = (76, 201, 240)
BORDER_LIGHT = (62, 72, 96)
ACCENT = (76, 201, 240)
GOLD = (233, 188, 97)

NATIVE = (480, 320)
SCALE = 2
SIZE = (NATIVE[0] * SCALE, NATIVE[1] * SCALE)
BODY = (8, 8, 471, 311)
INNER = (14, 14, 465, 305)
LEFT, RIGHT = 22, 456
RIGHT_EDGE = 452
PANEL = (18, 63, 461, 282)
ART_BOX = (24, 66, 455, 279)

SPECIAL_NAMES = {
    "mr-mime": "MR. MIME", "mime-jr": "MIME JR.", "ho-oh": "HO-OH",
    "porygon-z": "PORYGON-Z", "type-null": "TYPE: NULL",
    "farfetchd": "FARFETCH'D", "sirfetchd": "SIRFETCH'D",
    "flabebe": "FLABEBE", "nidoran-f": "NIDORAN FEMALE",
    "nidoran-m": "NIDORAN MALE", "jangmo-o": "JANGMO-O",
    "hakamo-o": "HAKAMO-O", "kommo-o": "KOMMO-O",
}
REGION_FORM_LABELS = {
    "alola": ("ALOLAN", "ALOLA"), "galar": ("GALARIAN", "GALAR"),
    "hisui": ("HISUIAN", "HISUI"), "paldea": ("PALDEAN", "PALDEA"),
}
REGION_RANGES = (
    (151, "KANTO"), (251, "JOHTO"), (386, "HOENN"), (493, "SINNOH"),
    (649, "UNOVA"), (721, "KALOS"), (809, "ALOLA"), (905, "GALAR"),
    (1025, "PALDEA"),
)
RARITY_LABELS = {"normal": "NORMAL", "legendary": "LEGENDARY", "mythical": "MYTHICAL"}


def _pretty(slug: str) -> str:
    slug = str(slug or "").lower().replace("_", "-")
    if slug in SPECIAL_NAMES:
        return SPECIAL_NAMES[slug]
    return " ".join(part.upper() for part in slug.split("-") if part)


def pokemon_display_name(*, form: str = "", pokemon: str = "", species: str = "") -> str:
    """Humanize a PokeAPI form slug, keeping Mega and regional names natural on the card."""
    base_slug = str(species or pokemon or form).lower()
    base = _pretty(base_slug)
    suffix = ""
    for candidate in (pokemon, form):
        candidate = str(candidate or "").lower()
        if candidate.startswith(base_slug + "-"):
            suffix = candidate[len(base_slug) + 1:]
            break
    if not suffix:
        return base
    if suffix == "mega":
        return f"MEGA {base}"
    if suffix in {"mega-x", "mega-y"}:
        return f"MEGA {base} {suffix[-1].upper()}"
    if suffix == "gmax":
        return f"GIGANTAMAX {base}"
    if suffix == "primal":
        return f"PRIMAL {base}"
    if suffix in REGION_FORM_LABELS:
        return f"{REGION_FORM_LABELS[suffix][0]} {base}"
    return f"{base} {_pretty(suffix)}"


def pokemon_region(*, species_id: int = 0, form: str = "", pokemon: str = "",
                   fallback: str = "") -> str:
    """Use a regional form's region first, otherwise the species' National-Dex generation."""
    if fallback:
        return str(fallback).replace("-", " ").upper()
    joined = f"-{form.lower()}-{pokemon.lower()}-"
    for slug, (_, label) in REGION_FORM_LABELS.items():
        if f"-{slug}-" in joined:
            return label
    if 899 <= int(species_id or 0) <= 905:
        return "HISUI"
    dex = int(species_id or 0)
    for last_id, label in REGION_RANGES:
        if dex and dex <= last_id:
            return label
    return "POKEMON"


def _fit(text: str, width: int, scale: int = 1) -> str:
    text = fold(str(text)).upper()
    if text_width(text, scale) <= width:
        return text
    while text and text_width(text + "...", scale) > width:
        text = text[:-1].rstrip()
    return text + "..." if text else "..."


def render_spawn_card(scene: Image.Image, *, species_id: int = 0, form: str = "",
                      pokemon: str = "", species: str = "", rarity: str = "normal",
                      shiny: bool = False, region: str = "", display_name: str | None = None,
                      catch_name: str | None = None) -> Image.Image:
    """Frame a habitat composite in the same dark pixel-card style used by `/guess`."""
    label = display_name or pokemon_display_name(form=form, pokemon=pokemon, species=species)
    region_label = pokemon_region(species_id=species_id, form=form, pokemon=pokemon,
                                  fallback=region)
    rarity_label = RARITY_LABELS.get(str(rarity).lower(), str(rarity).upper())
    detail = f"{'SHINY ' if shiny else ''}{label} - {rarity_label}"
    catch = str(catch_name or species or pokemon or form or label).replace("_", "-")
    footer = f"TYPE @PIKAPLAYROBOT CATCH {catch}"

    canvas = Image.new("RGB", NATIVE, PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(BODY, fill=CREAM, outline=BORDER, width=2)
    draw.rectangle(INNER, outline=BORDER_LIGHT, width=1)

    title = "WILD POKEMON"
    draw_text(draw, (LEFT, 16), _fit(title, 282, scale=2), INK, scale=2)
    draw_text(draw, (RIGHT_EDGE - text_width(region_label), 20), region_label, ACCENT)
    draw.line((LEFT, 44, RIGHT, 44), fill=BORDER_LIGHT, width=1)
    draw_text(draw, (LEFT, 51), _fit(detail, RIGHT - LEFT), GOLD)
    draw.rectangle(PANEL, fill=PANEL_DEEP, outline=BORDER_LIGHT, width=1)
    draw.line((LEFT, 286, RIGHT, 286), fill=BORDER_LIGHT, width=1)
    draw_text(draw, (LEFT, 294), _fit(footer, RIGHT - LEFT), DIM)

    x1, y1, x2, y2 = ART_BOX
    target = ((x2 - x1 + 1) * SCALE, (y2 - y1 + 1) * SCALE)
    art = ImageOps.fit(scene.convert("RGB"), target, method=Image.Resampling.LANCZOS,
                       centering=(0.5, 0.58))
    card = canvas.resize(SIZE, Image.Resampling.NEAREST)
    card.paste(art, (x1 * SCALE, y1 * SCALE))
    high = ImageDraw.Draw(card)
    high.rectangle((x1 * SCALE, y1 * SCALE, (x2 + 1) * SCALE - 1,
                    (y2 + 1) * SCALE - 1), outline=BORDER, width=SCALE)
    return card
