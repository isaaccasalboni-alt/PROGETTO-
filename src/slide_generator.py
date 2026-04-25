import io
import os
import random
import time
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
    {"bg": "#1c0a2e", "bg2": "#2d1060", "accent": "#c084fc", "overlay": (28,10,46,190)},
    {"bg": "#0f2318", "bg2": "#1a4a2e", "accent": "#34d399", "overlay": (15,35,24,185)},
]

# 8 layout distinti — scelti casualmente per ogni slide
LAYOUTS = [
    "full_bleed",   # foto piena + overlay scuro
    "split_right",  # testo sx / foto dx
    "split_left",   # foto sx / testo dx
    "top_photo",    # foto in alto, testo sotto
    "bottom_strip", # testo sopra, striscia foto in basso
    "magazine",     # foto grande + banda testo in basso
    "frame_inset",  # foto incorniciata al centro, testo sopra e sotto
    "minimal",      # solo tipografia, numero gigante, no foto
]

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


# ── Utility ────────────────────────────────────────────────────────────────────
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


def _crop_to(img, w, h):
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    img = img.resize((int(iw*scale), int(ih*scale)), Image.LANCZOS)
    iw, ih = img.size
    return img.crop(((iw-w)//2, (ih-h)//2, (iw-w)//2+w, (ih-h)//2+h))


def _crop_square(img, w, h):
    return _crop_to(img, w, h)


# ── Akool (generazione immagine AI) ────────────────────────────────────────────
def _fetch_photo_akool(prompt: str) -> Image.Image | None:
    key = os.getenv("AKOOL_API_KEY", "")
    if not key:
        return None
    try:
        r = requests.post(
            "https://openapi.akool.com/api/open/v3/content/image/createbyprompt",
            headers={"x-api-key": key, "Content-Type": "application/json"},
            json={"prompt": prompt, "scale": "1:1"},
            timeout=30,
        )
        data = r.json()
        if data.get("code") != 1000:
            print(f"[Akool] Errore creazione: {data.get('message')}")
            return None

        image_id = data["data"]["_id"]
        poll_url = "https://openapi.akool.com/api/open/v3/content/image/infobymodelid"

        for _ in range(30):  # max 90 secondi
            time.sleep(3)
            sr = requests.get(
                poll_url,
                headers={"x-api-key": key},
                params={"image_model_id": image_id},
                timeout=15,
            )
            sd = sr.json()
            if sd.get("code") != 1000:
                return None
            status = sd["data"].get("image_status", 0)
            if status == 3:
                img_url = sd["data"]["image"]
                img_data = requests.get(img_url, timeout=20).content
                return Image.open(io.BytesIO(img_data)).convert("RGBA")
            if status == 4:
                print("[Akool] Generazione fallita")
                return None
    except Exception as e:
        print(f"[Akool] Eccezione: {e}")
    return None


def _akool_prompt(image_description: str, title: str) -> str:
    subject = image_description or title
    return (
        f"Professional architectural photography: {subject}. "
        "Italian modern building exterior or elegant interior design, "
        "geometric clean composition, high quality photorealistic, no text, no people."
    )


# ── Pexels (fallback) ──────────────────────────────────────────────────────────
def _fetch_photo(query: str, fallback_idx: int, image_description: str = "") -> Image.Image | None:
    # 1. Prova Akool (AI generativa) se configurata
    if os.getenv("AKOOL_API_KEY"):
        result = _fetch_photo_akool(_akool_prompt(image_description, query))
        if result:
            print("[Akool] Immagine AI generata ✅")
            return result

    # 2. Fallback: Pexels (foto stock)
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
    draw.text((tx, ty),    "Studio Tecnico",  font=_font(18),       fill=(210,210,210))
    draw.text((tx, ty+22), "CASALBONI",       font=_font(24, True), fill=(255,255,255))


def _draw_footer(draw, accent):
    a = _hex(accent)
    draw.text((54, SIZE[1]-90), "STUDIO TECNICO CASALBONI  —  Geom. Isac Casalboni",
              font=_font(24, True), fill=(*a, 235))
    draw.text((54, SIZE[1]-58), "Via Viole 55 int.1, Gambettola (FC)  ·  393 230 9508  ·  0547 54095",
              font=_font(20), fill=(200,200,200,210))


def _draw_accent_bar(draw, accent):
    draw.rectangle([(0, 0), (SIZE[0], 8)], fill=(*_hex(accent), 255))


def _shadow_text(draw, pos, text, font, fill=(255,255,255,255)):
    x, y = pos
    draw.text((x+2, y+2), text, font=font, fill=(0,0,0,150))
    draw.text((x, y),     text, font=font, fill=fill)


def _gradient(theme):
    img = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(img)
    t, b = _hex(theme["bg2"]), _hex(theme["bg"])
    for y in range(SIZE[1]):
        draw.line([(0, y), (SIZE[0], y)], fill=(*_lerp(t, b, y/SIZE[1]), 255))
    return img


def _dark_band(draw, y_start, y_end, bg_color):
    for y in range(y_start, y_end):
        draw.line([(0, y), (SIZE[0], y)], fill=(*bg_color, 255))


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 1: Full bleed — foto piena con overlay scuro
# ══════════════════════════════════════════════════════════════════════════════
def _layout_full_bleed(title, content, theme, photo, n):
    bg = photo if photo else _gradient(theme)
    bg = _crop_to(bg.convert("RGBA"), *SIZE)

    overlay = Image.new("RGBA", SIZE, theme["overlay"])
    bg = Image.alpha_composite(bg, overlay)

    grad = Image.new("RGBA", SIZE, (0,0,0,0))
    gd = ImageDraw.Draw(grad)
    for y in range(SIZE[1]-300, SIZE[1]):
        a = int(210*(y-(SIZE[1]-300))/300)
        gd.line([(0,y),(SIZE[0],y)], fill=(0,0,0,a))
    bg = Image.alpha_composite(bg, grad)

    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 44)
    draw.text((54, 34), f"{n}/3", font=_font(30, True), fill=(*acc, 220))
    draw.rectangle([(54, 90), (200, 96)], fill=(*acc, 200))

    y = 130
    for line in _wrap(title.upper(), _font(70, True), SIZE[0]-420, draw)[:3]:
        _shadow_text(draw, (54, y), line, _font(70, True))
        y += 82
    y += 24
    draw.rectangle([(54, y), (134, y+4)], fill=(*acc, 200))
    y += 36
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(42), SIZE[0]-108, draw):
            if y > SIZE[1]-220: break
            _shadow_text(draw, (54, y), line, _font(42), fill=(230,230,230,255))
            y += 54
        y += 8

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 2: Split right — testo sx, foto dx
# ══════════════════════════════════════════════════════════════════════════════
def _layout_split_right(title, content, theme, photo, n):
    bg = _gradient(theme)
    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    if photo:
        try:
            right = _crop_to(photo.convert("RGBA"), 500, SIZE[1])
            ov = Image.new("RGBA", (500, SIZE[1]), (*_hex(theme["bg"]), 80))
            right = Image.alpha_composite(right, ov)
            bg.paste(right.convert("RGB"), (580, 0))
        except Exception:
            pass

    draw.rectangle([(570, 0), (578, SIZE[1])], fill=(*acc, 180))
    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 44)
    draw.text((48, 34), f"{n}/3", font=_font(30, True), fill=(*acc, 220))
    draw.rectangle([(48, 90), (180, 96)], fill=(*acc, 200))

    y = 140
    max_w = 490
    for line in _wrap(title.upper(), _font(64, True), max_w, draw)[:4]:
        _shadow_text(draw, (48, y), line, _font(64, True))
        y += 76
    y += 20
    draw.rectangle([(48, y), (128, y+4)], fill=(*acc, 200))
    y += 34
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(38), max_w, draw):
            if y > SIZE[1]-220: break
            draw.text((48, y), line, font=_font(38), fill=(225,225,225,255))
            y += 50
        y += 8

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 3: Split left — foto sx, testo dx
# ══════════════════════════════════════════════════════════════════════════════
def _layout_split_left(title, content, theme, photo, n):
    bg = _gradient(theme)
    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    if photo:
        try:
            left = _crop_to(photo.convert("RGBA"), 500, SIZE[1])
            ov = Image.new("RGBA", (500, SIZE[1]), (*_hex(theme["bg"]), 80))
            left = Image.alpha_composite(left, ov)
            bg.paste(left.convert("RGB"), (0, 0))
        except Exception:
            pass

    draw.rectangle([(502, 0), (510, SIZE[1])], fill=(*acc, 180))
    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 44)
    draw.text((530, 34), f"{n}/3", font=_font(30, True), fill=(*acc, 220))
    draw.rectangle([(530, 90), (670, 96)], fill=(*acc, 200))

    y = 140
    max_w = SIZE[0] - 530 - 40
    for line in _wrap(title.upper(), _font(58, True), max_w, draw)[:4]:
        _shadow_text(draw, (530, y), line, _font(58, True))
        y += 70
    y += 20
    draw.rectangle([(530, y), (610, y+4)], fill=(*acc, 200))
    y += 34
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(36), max_w, draw):
            if y > SIZE[1]-220: break
            draw.text((530, y), line, font=_font(36), fill=(225,225,225,255))
            y += 48
        y += 8

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 4: Top photo — foto in alto 400px, testo sotto
# ══════════════════════════════════════════════════════════════════════════════
def _layout_top_photo(title, content, theme, photo, n):
    bg = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])
    bg_solid = _hex(theme["bg"])

    for y in range(SIZE[1]):
        draw.line([(0, y), (SIZE[0], y)], fill=(*bg_solid, 255))

    PHOTO_H = 400
    if photo:
        try:
            top = photo.convert("RGBA").copy()
            top = top.resize((SIZE[0], int(top.height * SIZE[0] / top.width)), Image.LANCZOS)
            if top.height < PHOTO_H:
                top = _crop_to(top, SIZE[0], PHOTO_H)
            top = top.crop((0, 0, SIZE[0], PHOTO_H))
            grad = Image.new("RGBA", (SIZE[0], PHOTO_H), (0,0,0,0))
            gd = ImageDraw.Draw(grad)
            for y in range(PHOTO_H//2, PHOTO_H):
                a = int(255*(y-PHOTO_H//2)/(PHOTO_H//2))
                gd.line([(0,y),(SIZE[0],y)], fill=(*bg_solid, a))
            top = Image.alpha_composite(top, grad)
            bg.paste(top.convert("RGB"), (0, 0))
        except Exception:
            pass

    draw.rectangle([(0, PHOTO_H), (SIZE[0], PHOTO_H+6)], fill=(*acc, 255))
    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 20)
    draw.text((48, 16), f"{n}/3", font=_font(28, True), fill=(*acc, 220))

    y = PHOTO_H + 36
    for line in _wrap(title.upper(), _font(68, True), SIZE[0]-108, draw)[:3]:
        _shadow_text(draw, (54, y), line, _font(68, True))
        y += 78
    y += 16
    draw.rectangle([(54, y), (134, y+4)], fill=(*acc, 200))
    y += 32
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(40), SIZE[0]-108, draw):
            if y > SIZE[1]-220: break
            draw.text((54, y), line, font=_font(40), fill=(225,225,225,255))
            y += 52
        y += 8

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 5: Bottom strip — testo sopra, striscia foto sotto
# ══════════════════════════════════════════════════════════════════════════════
def _layout_bottom_strip(title, content, theme, photo, n):
    STRIP_H = 320
    STRIP_Y = SIZE[1] - STRIP_H  # y=760

    bg = _gradient(theme)
    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 44)
    draw.text((54, 34), f"{n}/3", font=_font(30, True), fill=(*acc, 220))
    draw.rectangle([(54, 90), (200, 96)], fill=(*acc, 200))

    y = 140
    for line in _wrap(title.upper(), _font(70, True), SIZE[0]-108, draw)[:3]:
        _shadow_text(draw, (54, y), line, _font(70, True))
        y += 82
    y += 20
    draw.rectangle([(54, y), (134, y+4)], fill=(*acc, 200))
    y += 32
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(40), SIZE[0]-108, draw):
            if y > STRIP_Y - 60: break
            draw.text((54, y), line, font=_font(40), fill=(225,225,225,255))
            y += 52
        y += 8

    # Striscia foto con overlay dark al fondo (per leggibilità footer)
    draw.rectangle([(0, STRIP_Y-5), (SIZE[0], STRIP_Y+1)], fill=(*acc, 220))

    if photo:
        try:
            strip = _crop_to(photo.convert("RGBA"), SIZE[0], STRIP_H)
            # Gradient scuro nella metà bassa della strip (per footer)
            ov_grad = Image.new("RGBA", (SIZE[0], STRIP_H), (0,0,0,0))
            gd = ImageDraw.Draw(ov_grad)
            fade_start = STRIP_H // 2
            for fy in range(fade_start, STRIP_H):
                a = int(180 * (fy - fade_start) / (STRIP_H - fade_start))
                gd.line([(0,fy),(SIZE[0],fy)], fill=(0,0,0,a))
            strip = Image.alpha_composite(strip, ov_grad)
            bg.paste(strip.convert("RGB"), (0, STRIP_Y))
        except Exception:
            pass

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 6: Magazine — foto grande + banda testo in basso
# ══════════════════════════════════════════════════════════════════════════════
def _layout_magazine(title, content, theme, photo, n):
    PHOTO_H = 580
    bg = Image.new("RGBA", SIZE)
    bg_color = _hex(theme["bg"])

    # Riempie tutto di colore scuro
    solid = Image.new("RGBA", SIZE, (*bg_color, 255))
    bg.paste(solid)

    if photo:
        try:
            top = _crop_to(photo.convert("RGBA"), SIZE[0], PHOTO_H)
            # Sfumatura in basso sulla foto verso il colore bg
            fade = Image.new("RGBA", (SIZE[0], PHOTO_H), (0,0,0,0))
            gd = ImageDraw.Draw(fade)
            fade_start = PHOTO_H - 140
            for fy in range(fade_start, PHOTO_H):
                a = int(255 * (fy - fade_start) / (PHOTO_H - fade_start))
                gd.line([(0,fy),(SIZE[0],fy)], fill=(*bg_color, a))
            top = Image.alpha_composite(top, fade)
            bg.paste(top.convert("RGB"), (0, 0))
        except Exception:
            pass

    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    draw.rectangle([(0, PHOTO_H), (SIZE[0], PHOTO_H+8)], fill=(*acc, 255))
    _draw_accent_bar(draw, theme["accent"])
    draw.text((48, 20), f"{n}/3", font=_font(28, True), fill=(*acc, 230))
    _draw_logo(draw, bg, SIZE[0]-310, 16)

    y = PHOTO_H + 28
    for line in _wrap(title.upper(), _font(72, True), SIZE[0]-108, draw)[:2]:
        _shadow_text(draw, (54, y), line, _font(72, True))
        y += 84
    y += 12
    draw.rectangle([(54, y), (134, y+4)], fill=(*acc, 200))
    y += 28
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(38), SIZE[0]-108, draw):
            if y > SIZE[1]-220: break
            draw.text((54, y), line, font=_font(38), fill=(225,225,225,255))
            y += 50
        y += 6

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 7: Frame inset — foto incorniciata al centro, testo sopra e sotto
# ══════════════════════════════════════════════════════════════════════════════
def _layout_frame_inset(title, content, theme, photo, n):
    bg = _gradient(theme)
    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    FRAME_X, FRAME_Y = 90, 310
    FRAME_W, FRAME_H = 900, 400
    BORDER = 6

    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 44)
    draw.text((54, 34), f"{n}/3", font=_font(30, True), fill=(*acc, 220))

    # Titolo sopra il frame
    y = 90
    for line in _wrap(title.upper(), _font(66, True), SIZE[0]-108, draw)[:2]:
        _shadow_text(draw, (54, y), line, _font(66, True))
        y += 78
    draw.rectangle([(54, y+8), (SIZE[0]-54, y+12)], fill=(*acc, 180))

    # Foto incorniciata
    draw.rectangle(
        [(FRAME_X-BORDER, FRAME_Y-BORDER), (FRAME_X+FRAME_W+BORDER, FRAME_Y+FRAME_H+BORDER)],
        fill=(*acc, 200)
    )
    if photo:
        try:
            framed = _crop_to(photo.convert("RGBA"), FRAME_W, FRAME_H)
            bg.paste(framed.convert("RGB"), (FRAME_X, FRAME_Y))
        except Exception:
            # Placeholder con gradiente scuro
            ph = Image.new("RGBA", (FRAME_W, FRAME_H), (*_hex(theme["bg2"]), 255))
            bg.paste(ph.convert("RGB"), (FRAME_X, FRAME_Y))

    # Testo sotto il frame
    y = FRAME_Y + FRAME_H + BORDER + 28
    draw.rectangle([(54, y), (134, y+4)], fill=(*acc, 200))
    y += 28
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(40), SIZE[0]-108, draw):
            if y > SIZE[1]-220: break
            draw.text((54, y), line, font=_font(40), fill=(225,225,225,255))
            y += 52
        y += 8

    _draw_footer(draw, theme["accent"])
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT 8: Minimal — solo tipografia, numero gigante decorativo
# ══════════════════════════════════════════════════════════════════════════════
def _layout_minimal(title, content, theme, n):
    bg = _gradient(theme)
    draw = ImageDraw.Draw(bg)
    acc = _hex(theme["accent"])

    big_num = _font(420, True)
    num_str = str(n)
    bbox = draw.textbbox((0, 0), num_str, font=big_num)
    nx = SIZE[0] - (bbox[2]-bbox[0]) - 20
    ny = (SIZE[1] - (bbox[3]-bbox[1])) // 2 - 80
    draw.text((nx, ny), num_str, font=big_num, fill=(*acc, 22))

    draw.rectangle([(48, 100), (58, 520)], fill=(*acc, 200))

    _draw_accent_bar(draw, theme["accent"])
    _draw_logo(draw, bg, SIZE[0]-310, 44)
    draw.text((80, 34), f"{n}/3", font=_font(30, True), fill=(*acc, 220))

    y = 140
    max_w = SIZE[0] - 180
    for line in _wrap(title.upper(), _font(76, True), max_w, draw)[:3]:
        draw.text((80, y), line, font=_font(76, True), fill=(255,255,255,255))
        y += 88
    y += 28
    draw.rectangle([(80, y), (200, y+5)], fill=(*acc, 220))
    y += 40
    for para in content.split("\n"):
        for line in _wrap(para.strip(), _font(44), max_w, draw):
            if y > SIZE[1]-220: break
            draw.text((80, y), line, font=_font(44), fill=(220,220,220,255))
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

    needs_photo = layout != "minimal"
    photo = _fetch_photo(image_description or title, index, image_description) if needs_photo else None

    if layout == "full_bleed":
        img = _layout_full_bleed(title, content, theme, photo, index+1)
    elif layout == "split_right":
        img = _layout_split_right(title, content, theme, photo, index+1)
    elif layout == "split_left":
        img = _layout_split_left(title, content, theme, photo, index+1)
    elif layout == "top_photo":
        img = _layout_top_photo(title, content, theme, photo, index+1)
    elif layout == "bottom_strip":
        img = _layout_bottom_strip(title, content, theme, photo, index+1)
    elif layout == "magazine":
        img = _layout_magazine(title, content, theme, photo, index+1)
    elif layout == "frame_inset":
        img = _layout_frame_inset(title, content, theme, photo, index+1)
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
