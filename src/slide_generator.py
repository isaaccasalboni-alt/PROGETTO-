import io
import os
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Temi cromatici — overlay scuro sopra le foto
SLIDE_THEMES = [
    {"overlay": (15, 30, 60, 190),  "accent": "#f0a500"},   # blu navy
    {"overlay": (20, 50, 20, 185),  "accent": "#f0a500"},   # verde scuro
    {"overlay": (40, 25, 15, 190),  "accent": "#f0a500"},   # marrone scuro
]

# Parole chiave di fallback per ricerche Pexels per topic geometra
FALLBACK_QUERIES = [
    "modern architecture house exterior",
    "interior design living room",
    "construction building blueprint",
    "real estate property aerial",
    "renovation home design",
    "architect blueprint plans",
]

SIZE = (1080, 1080)
LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo.png"


def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _get_font(size: int, bold: bool = False):
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


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _crop_center(img: Image.Image, w: int, h: int) -> Image.Image:
    """Ritaglia al centro mantenendo proporzioni."""
    img_w, img_h = img.size
    scale = max(w / img_w, h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))


def _fetch_background(query: str, index: int) -> Image.Image | None:
    """Scarica foto da Pexels. Ritorna None se non configurato."""
    api_key = os.getenv("PEXELS_API_KEY", "")
    if not api_key or api_key.startswith("metti_"):
        return None
    try:
        # Usa le prime parole della descrizione come query
        clean_q = " ".join(query.replace(",", " ").split()[:6])
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": clean_q, "per_page": 3, "orientation": "square"},
            timeout=10,
        )
        if not resp.ok:
            return None
        photos = resp.json().get("photos", [])
        if not photos:
            # Fallback: cerca topic generico edilizia/architettura
            fallback = FALLBACK_QUERIES[index % len(FALLBACK_QUERIES)]
            resp2 = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": api_key},
                params={"query": fallback, "per_page": 1, "orientation": "square"},
                timeout=10,
            )
            if not resp2.ok:
                return None
            photos = resp2.json().get("photos", [])
        if not photos:
            return None
        img_url = photos[0]["src"]["large2x"]
        img_data = requests.get(img_url, timeout=15).content
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        return _crop_center(img, SIZE[0], SIZE[1])
    except Exception:
        return None


def _make_gradient_bg(theme: dict) -> Image.Image:
    """Sfondo sfumato di fallback (usato senza Pexels)."""
    # Riusa i colori dell'overlay come sfondo solido sfumato
    r, g, b, _ = theme["overlay"]
    top = (max(r + 30, 0), max(g + 30, 0), max(b + 30, 0))
    bot = (max(r - 10, 0), max(g - 10, 0), max(b - 10, 0))
    img = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(img)
    for y in range(SIZE[1]):
        t = y / SIZE[1]
        color = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (SIZE[0], y)], fill=(*color, 255))
    return img


def _draw_logo(draw: ImageDraw.ImageDraw, img: Image.Image) -> None:
    """Incolla logo in alto a destra: usa PNG se disponibile, altrimenti disegna."""
    margin = 44
    logo_w = 300

    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            ratio = logo_w / logo.width
            logo = logo.resize((logo_w, int(logo.height * ratio)), Image.LANCZOS)
            img.paste(logo, (SIZE[0] - logo_w - margin, margin), logo)
            return
        except Exception:
            pass

    # Fallback: marchio geometrico disegnato
    x = SIZE[0] - logo_w - margin
    y = margin + 8
    sq, gap = 36, 5
    white = (255, 255, 255)
    blue_light, blue_dark = (52, 152, 219), (26, 82, 118)

    draw.rectangle([x, y, x+sq, y+sq], fill=blue_light)
    draw.rectangle([x+sq+gap, y, x+sq*2+gap, y+sq], fill=blue_dark)
    draw.rectangle([x, y+sq+gap, x+sq, y+sq*2+gap], fill=white)
    draw.ellipse([x - sq//2, y+sq+gap, x + sq//2, y+sq*2+gap], fill=blue_dark)
    draw.rectangle([x+sq+gap, y+sq+gap, x+sq*2+gap, y+sq*2+gap], fill=blue_light)
    inner = sq // 3
    draw.rectangle([x+sq+gap+sq-inner, y+sq+gap+sq-inner, x+sq*2+gap, y+sq*2+gap], fill=white)

    tx, ty = x + sq*2 + gap + 14, y + 2
    draw.text((tx, ty),      "Studio Tecnico", font=_get_font(20),          fill=(210, 210, 210))
    draw.text((tx, ty + 26), "CASALBONI",      font=_get_font(28, bold=True), fill=white)


def create_slide(title: str, content: str, index: int, image_description: str = "") -> bytes:
    theme = SLIDE_THEMES[index % len(SLIDE_THEMES)]
    accent = _hex(theme["accent"])

    # 1. Sfondo: foto Pexels oppure gradiente
    query = image_description or title
    bg = _fetch_background(query, index) or _make_gradient_bg(theme)
    bg = bg.convert("RGBA")

    # 2. Overlay scuro semitrasparente sopra la foto
    overlay = Image.new("RGBA", SIZE, theme["overlay"])
    bg = Image.alpha_composite(bg, overlay)

    # 3. Sfumatura extra in basso per leggibilità footer
    grad = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(grad)
    for y in range(SIZE[1] - 250, SIZE[1]):
        alpha = int(180 * (y - (SIZE[1] - 250)) / 250)
        grad_draw.line([(0, y), (SIZE[0], y)], fill=(0, 0, 0, alpha))
    bg = Image.alpha_composite(bg, grad)

    draw = ImageDraw.Draw(bg)

    # 4. Barra accent in alto
    draw.rectangle([(0, 0), (SIZE[0], 8)], fill=(*accent, 255))

    # 5. Logo in alto a destra
    _draw_logo(draw, bg)

    # 6. Numero slide
    draw.text((54, 34), f"{index + 1} / 3", font=_get_font(32, bold=True), fill=(*accent, 220))

    # 7. Linea decorativa
    draw.rectangle([(54, 90), (200, 96)], fill=(*accent, 200))

    # 8. Titolo
    margin, max_w = 54, SIZE[0] - 54 - 360
    title_font = _get_font(72, bold=True)
    y = 130
    for line in _wrap_text(title.upper(), title_font, max_w, draw)[:3]:
        # Ombra testo per leggibilità su foto
        draw.text((margin + 2, y + 2), line, font=title_font, fill=(0, 0, 0, 160))
        draw.text((margin, y), line, font=title_font, fill=(255, 255, 255, 255))
        y += 84

    # 9. Separatore
    y += 20
    draw.rectangle([(margin, y), (margin + 80, y + 4)], fill=(*accent, 200))
    y += 40

    # 10. Contenuto
    body_font = _get_font(44)
    for para in content.split("\n"):
        for line in _wrap_text(para.strip(), body_font, SIZE[0] - margin * 2, draw):
            if y > SIZE[1] - 220:
                break
            draw.text((margin + 2, y + 2), line, font=body_font, fill=(0, 0, 0, 140))
            draw.text((margin, y), line, font=body_font, fill=(230, 230, 230, 255))
            y += 56
        y += 10

    # 11. Footer
    draw.text((margin, SIZE[1] - 90), "STUDIO TECNICO CASALBONI  —  Geom. Isac Casalboni",
              font=_get_font(26, bold=True), fill=(*accent, 235))
    draw.text((margin, SIZE[1] - 58), "Via Viole 55 int.1, Gambettola (FC)  ·  📱 393 230 9508  ·  ☎ 0547 54095",
              font=_get_font(22), fill=(210, 210, 210, 210))

    buf = io.BytesIO()
    bg.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def generate_slides(slide_sections: list[dict]) -> list[dict]:
    """Genera le 3 immagini slide. Ritorna lista di dict: {"filename": str, "bytes": bytes}"""
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
