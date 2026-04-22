import io
import os
import random
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Temi colore ────────────────────────────────────────────────────────────────
THEMES = [
    {"bg": "#0d2137", "bg2": "#1a3a5c", "accent": "#f0a500", "overlay": (13,33,55,185)},
    {"bg": "#1a3a1b", "bg2": "#2c5f2e", "accent": "#f0a500", "overlay": (26,58,27,185)},
    {"bg": "#1e1510", "bg2": "#3d2b1f", "accent": "#f0a500", "overlay": (30,21,16,185)},
    {"bg": "#1a1a2e", "bg2": "#16213e", "accent": "#e94560", "overlay": (22,22,46,190)},
    {"bg": "#0a1628", "bg2": "#1a2f4a", "accent": "#00d4aa", "overlay": (10,22,40,185)},
]

LAYOUTS = ["full_bleed", "split_right", "top_photo", "minimal"]

SIZE = (1080, 1080)
LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo.png"

FALLBACK_QUERIES = [
    "modern architecture house exterior Italy",
    "interior design living room luxury",
    "construction blueprint architect desk",
    "real estate property building",
    "renovation home elegant",
    "urban architecture geometric",
]


# ── Font ───────────────────────────────────────────────────────────────────────
def _font(size: int, bold: bool = False):
    paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/freefont/FreeSans{'Bold' if bold else ''}.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _wrap(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _crop_square(img, w, h):
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    img = img.resize((int(iw*scale), int(ih*scale)), Image.LANCZOS)
    iw, ih = img.size
    return img.crop(((iw-w)//2, (ih-h)//2, (iw-w)//2+w, (ih-h)//2+h))


# ── Pexels ─────────────────────────────────────────────────────────────────────
def _fetch_photo(query: str, fallback_idx: int) -> Image.Image | None:
    key = os.getenv("PEXELS_API_KEY", "")
    if not key or key.startswith("metti_"):
        return None
    for q in [query, FALLBACK_QUERIES[fallback_idx % len(FALLBACK_QUERIES)]]:
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": key},
                params={"query": q, "per_page": 5, "orientation": "square"},
                timeout=10,
            )
            photos = r.json().get("photos", []) if r.ok else []
            if photos:
                pick = random.choice(photos)
                data = requests.get(pick["src"]["large2x"], timeout=15).content
                return Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception:
            pass
    return None


# ── Logo ───────────────────────────────────────────────────────────────────────
def _draw_logo(draw, img, x, y, w=260):
    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo = logo.resize((w, int(logo.height * w / logo.width)), Image.LANCZOS)
            img.paste(logo, (x, y), logo)
            return
        except Exception:
            pass
    sq, gap = 30, 4
    draw.rectangle([x, y, x+sq, y+sq], fill=(52,152,219))
    draw.rectangle([x+sq+gap, y, x+sq*2+gap, y+sq], fill=(26,82,118))
    draw.rectangle([x, y+sq+gap, x+sq, y+sq*2+gap], fill=(255,255,255))
    draw.ellipse([x-sq//2, y+sq+gap, x+sq//2, y+sq*2+gap], fill=(26,82,118))
    draw.rectangle([x+sq+gap, y+sq+gap, x+sq*2+gap, y+sq*2+gap], fill=(52,152,219))
    tx, ty = x+sq*2+gap+12, y+2
    draw.text((tx, ty),    "Studio Tecnico",  font=_font(18),         fill=(210,210,210))
    draw.text((tx, ty+22), "CASALBONI",       font=_font(24, True),   fill=(255,255,255))


def _draw_footer(draw, accent):
    a = _hex(accent)
    draw.text((54, SIZE[1]-90), "STUDIO TECNICO CASALBONI  —  Geom. Isac Casalboni",
              font=_font(24, True), fill=(*a, 235))
    draw.text((54, SIZE[1]-58), "Via Viole 55 int.1, Gambettola (FC)  ·  📱 393 230 9508  ·  ☎ 0547 54095",
              font=_font(20), fill=(200,200,200,210))


def _draw_accent_bar(draw, accent):
    draw.rectangle([(0,0),(SIZE[0],8)], fill=(*_hex(accent),255))


def _shadow_text(draw, pos, text, font, fill=(255,255,255,255)):
    x, y = pos
    draw.text((x+2, y+2), text, font=font, fill=(0,0,0,150))
    draw.text((x, y),     text, font=font, fill=fill)


# ── Sfondo sfumato ─────────────────────────────────────────────────────────────
def _gradient(theme):
    img = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(img)
    t, b = _hex(theme["bg2"]), _hex(theme["bg"])
    for y in range(SIZE[1]):
        draw.line([(0,y),(SIZE[0],y)], fill=(*_lerp(t,b,y/SIZE[1]),255))
    return img


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 1: Full bleed — foto piena con overlay scuro
# ══════════════════════════════════════════════════════════════════════════════
def _layout_full_bleed(title, content, theme, photo, slide_num):
    bg = photo if photo else _gradient(theme)
    bg = _crop_square(bg.convert("RGBA"), *SIZE)

    overlay = Image.new("RGBA", SIZE, theme["overlay"])
    bg = Image.alpha_composite(bg, overlay)

    grad = Image.new("RGBA", SIZE, (0,0,0,0))
    gd = ImageDraw.Draw(grad)
    for y in range(SIZE[1]-280, SIZE[1]):
        a = int(200*(y-(SIZE[1]-280))/280)
        gd.line([(0,y),(SIZE[0],y)], fill=(0,0,0,a))
    bg = Image.alpha_composite(bg, grad)

    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 44)
    draw.text((54,34), f"{slide_num}/3", font=_font(30,True), fill=(*acc,220))
    draw.rectangle([(54,90),(200,96)], fill=(*acc,200))

    y = 130
    for line in _wrap(title.upper(), _font(70,True), SIZE[0]-420, draw)[:3]:
        _shadow_text(draw, (54,y), line, _font(70,True))
        y += 82
    y += 24
    draw.rectangle([(54,y),(134,y+4)], fill=(*acc,200))
    y += 36
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(42), SIZE[0]-108, draw):
            if y > SIZE[1]-220: break
            _shadow_text(draw, (54,y), line, _font(42), fill=(230,230,230,255))
            y += 54
        y += 8

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 2: Split — testo a sinistra, foto a destra
# ══════════════════════════════════════════════════════════════════════════════
def _layout_split(title, content, theme, photo, slide_num):
    bg = _gradient(theme)
    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    # Pannello sinistro (testo) già nel gradiente
    # Foto a destra: colonna da x=580
    if photo:
        try:
            right = _crop_square(photo.convert("RGBA"), 500, SIZE[1])
            # Overlay leggero sul lato foto
            ov = Image.new("RGBA", (500, SIZE[1]), (*_hex(theme["bg"]), 80))
            right = Image.alpha_composite(right, ov)
            bg.paste(right.convert("RGB"), (580, 0))
        except Exception:
            pass

    # Linea verticale divisoria in oro
    draw.rectangle([(570,0),(578,SIZE[1])], fill=(*acc,180))

    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 44)
    draw.text((48,34), f"{slide_num}/3", font=_font(30,True), fill=(*acc,220))
    draw.rectangle([(48,90),(180,96)], fill=(*acc,200))

    y = 140
    max_w = 490
    for line in _wrap(title.upper(), _font(64,True), max_w, draw)[:4]:
        _shadow_text(draw, (48,y), line, _font(64,True))
        y += 76
    y += 20
    draw.rectangle([(48,y),(128,y+4)], fill=(*acc,200))
    y += 34
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(38), max_w, draw):
            if y > SIZE[1]-220: break
            draw.text((48,y), line, font=_font(38), fill=(225,225,225,255))
            y += 50
        y += 8

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 3: Top photo — foto in alto, testo in basso
# ══════════════════════════════════════════════════════════════════════════════
def _layout_top_photo(title, content, theme, photo, slide_num):
    bg = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])
    bg_solid = _hex(theme["bg"])

    # Riempi tutto di colore scuro
    for y in range(SIZE[1]):
        draw.line([(0,y),(SIZE[0],y)], fill=(*bg_solid,255))

    # Foto in alto (400px)
    PHOTO_H = 400
    if photo:
        try:
            top = photo.convert("RGBA").copy()
            top = top.resize((SIZE[0], int(top.height * SIZE[0] / top.width)), Image.LANCZOS)
            if top.height < PHOTO_H:
                top = _crop_square(top, SIZE[0], PHOTO_H)
            top = top.crop((0, 0, SIZE[0], PHOTO_H))
            # Sfumatura in basso sulla foto
            grad = Image.new("RGBA", (SIZE[0], PHOTO_H), (0,0,0,0))
            gd = ImageDraw.Draw(grad)
            for y in range(PHOTO_H//2, PHOTO_H):
                a = int(255*(y-PHOTO_H//2)/(PHOTO_H//2))
                gd.line([(0,y),(SIZE[0],y)], fill=(*bg_solid, a))
            top = Image.alpha_composite(top, grad)
            bg.paste(top.convert("RGB"), (0,0))
        except Exception:
            pass

    # Linea accent sotto la foto
    draw.rectangle([(0,PHOTO_H),(SIZE[0],PHOTO_H+6)], fill=(*acc,255))

    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 20)
    draw.text((48, 16), f"{slide_num}/3", font=_font(28,True), fill=(*acc,220))

    # Testo nella parte bassa
    y = PHOTO_H + 36
    for line in _wrap(title.upper(), _font(68,True), SIZE[0]-108, draw)[:3]:
        _shadow_text(draw, (54,y), line, _font(68,True))
        y += 78
    y += 16
    draw.rectangle([(54,y),(134,y+4)], fill=(*acc,200))
    y += 32
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(40), SIZE[0]-108, draw):
            if y > SIZE[1]-220: break
            draw.text((54,y), line, font=_font(40), fill=(225,225,225,255))
            y += 52
        y += 8

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 4: Minimal — niente foto, grande numero decorativo, tipografia forte
# ══════════════════════════════════════════════════════════════════════════════
def _layout_minimal(title, content, theme, slide_num):
    bg = _gradient(theme)
    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    # Grande numero decorativo in sfondo (semitrasparente)
    big_num = _font(420, True)
    num_str = str(slide_num)
    bbox = draw.textbbox((0,0), num_str, font=big_num)
    nx = SIZE[0] - (bbox[2]-bbox[0]) - 20
    ny = (SIZE[1] - (bbox[3]-bbox[1])) // 2 - 80
    draw.text((nx, ny), num_str, font=big_num, fill=(*acc, 22))

    # Rettangolo accent decorativo verticale a sinistra
    draw.rectangle([(48,100),(58,520)], fill=(*acc,200))

    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 44)
    draw.text((80,34), f"{slide_num}/3", font=_font(30,True), fill=(*acc,220))

    y = 140
    max_w = SIZE[0] - 180
    for line in _wrap(title.upper(), _font(76,True), max_w, draw)[:3]:
        draw.text((80,y), line, font=_font(76,True), fill=(255,255,255,255))
        y += 88
    y += 28
    draw.rectangle([(80,y),(200,y+5)], fill=(*acc,220))
    y += 40
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(44), max_w, draw):
            if y > SIZE[1]-220: break
            draw.text((80,y), line, font=_font(44), fill=(220,220,220,255))
            y += 56
        y += 10

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def create_slide(title: str, content: str, index: int, image_description: str = "") -> bytes:
    theme = random.choice(THEMES)
    layout = random.choice(LAYOUTS)

    photo = _fetch_photo(image_description or title, index) if layout != "minimal" else None

    if layout == "full_bleed":
        img = _layout_full_bleed(title, content, theme, photo, index+1)
    elif layout == "split_right":
        img = _layout_split(title, content, theme, photo, index+1)
    elif layout == "top_photo":
        img = _layout_top_photo(title, content, theme, photo, index+1)
    else:
        img = _layout_minimal(title, content, theme, index+1)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def generate_slides(slide_sections: list[dict]) -> list[dict]:
    slides = []
    for i, section in enumerate(slide_sections[:3]):
        img_bytes = create_slide(
            title=section.get("title", f"Slide {i+1}"),
            content=section.get("content", ""),
            index=i,
            image_description=section.get("image_description", ""),
        )
        slides.append({"filename": f"slide_{i+1}.png", "bytes": img_bytes})
    return slides
