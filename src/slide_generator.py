import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Temi cromatici professionali — Studio Tecnico Casalboni
SLIDE_THEMES = [
    {"bg_top": "#1a3a5c", "bg_bottom": "#0d2137", "accent": "#f0a500"},  # blu navy + oro
    {"bg_top": "#2c5f2e", "bg_bottom": "#1a3a1b", "accent": "#f0a500"},  # verde scuro + oro
    {"bg_top": "#3d2b1f", "bg_bottom": "#1e1510", "accent": "#f0a500"},  # marrone scuro + oro
]

SIZE = (1080, 1080)
LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo.png"


def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


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


def _draw_logo(draw: ImageDraw.ImageDraw, img: Image.Image) -> None:
    """
    Se assets/logo.png esiste lo usa, altrimenti disegna il logo vettoriale dello studio.
    Posizione: angolo in alto a destra.
    """
    margin = 44
    logo_w = 300

    # Prova a usare il file PNG se disponibile
    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            ratio = logo_w / logo.width
            new_size = (logo_w, int(logo.height * ratio))
            logo = logo.resize(new_size, Image.LANCZOS)
            img.paste(logo, (SIZE[0] - logo_w - margin, margin), logo)
            return
        except Exception:
            pass

    # Fallback: disegna il logo geometrico dello studio con Pillow
    x = SIZE[0] - logo_w - margin
    y = margin + 8

    # --- Marchio geometrico 2x2 (ispirato al logo Casalboni) ---
    sq = 36   # dimensione quadrante
    gap = 5   # spazio tra quadranti
    white = (255, 255, 255)
    blue_light = (52, 152, 219)   # azzurro
    blue_dark  = (26, 82, 118)    # blu scuro

    # quadrante alto-sinistra: blu chiaro pieno
    draw.rectangle([x, y, x+sq, y+sq], fill=blue_light)
    # quadrante alto-destra: blu scuro pieno
    draw.rectangle([x+sq+gap, y, x+sq*2+gap, y+sq], fill=blue_dark)
    # quadrante basso-sinistra: bianco con arco interno (effetto C)
    draw.rectangle([x, y+sq+gap, x+sq, y+sq*2+gap], fill=white)
    draw.ellipse(
        [x - sq//2, y+sq+gap, x + sq//2, y+sq*2+gap],
        fill=blue_dark,
    )
    # quadrante basso-destra: blu chiaro
    draw.rectangle([x+sq+gap, y+sq+gap, x+sq*2+gap, y+sq*2+gap], fill=blue_light)
    # piccolo quadrato bianco in basso-destra (dettaglio logo)
    inner = sq // 3
    draw.rectangle(
        [x+sq+gap+sq-inner, y+sq+gap+sq-inner, x+sq*2+gap, y+sq*2+gap],
        fill=white,
    )

    # --- Testo del logo ---
    tx = x + sq * 2 + gap + 14
    ty = y + 2
    font_small = _get_font(20)
    font_bold  = _get_font(28, bold=True)
    draw.text((tx, ty),      "Studio Tecnico", font=font_small, fill=(210, 210, 210))
    draw.text((tx, ty + 26), "CASALBONI",      font=font_bold,  fill=white)


def create_slide(title: str, content: str, index: int) -> bytes:
    theme = SLIDE_THEMES[index % len(SLIDE_THEMES)]
    img = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(img)

    # Sfondo sfumato verticale
    top = _hex(theme["bg_top"])
    bot = _hex(theme["bg_bottom"])
    for y in range(SIZE[1]):
        color = _lerp(top, bot, y / SIZE[1])
        draw.line([(0, y), (SIZE[0], y)], fill=(*color, 255))

    # Barra accent in alto
    accent = _hex(theme["accent"])
    draw.rectangle([(0, 0), (SIZE[0], 8)], fill=(*accent, 255))

    # Logo in alto a destra
    _draw_logo(draw, img)

    # Numero slide (badge)
    badge_font = _get_font(32, bold=True)
    badge_text = f"{index + 1} / 3"
    draw.text((54, 34), badge_text, font=badge_font, fill=(*accent, 220))

    # Linea decorativa
    draw.rectangle([(54, 90), (200, 96)], fill=(*accent, 180))

    # Titolo
    title_font = _get_font(72, bold=True)
    margin = 54
    max_w = SIZE[0] - margin - 360   # lascia spazio al logo
    title_lines = _wrap_text(title.upper(), title_font, max_w, draw)
    y = 130
    for line in title_lines[:3]:
        draw.text((margin, y), line, font=title_font, fill=(255, 255, 255, 255))
        y += 84

    # Separatore
    y += 20
    draw.rectangle([(margin, y), (margin + 80, y + 4)], fill=(*accent, 180))
    y += 40

    # Contenuto
    body_font = _get_font(44)
    full_max_w = SIZE[0] - margin * 2
    for para in content.split("\n"):
        lines = _wrap_text(para.strip(), body_font, full_max_w, draw)
        for line in lines:
            if y > SIZE[1] - 200:
                break
            draw.text((margin, y), line, font=body_font, fill=(230, 230, 230, 255))
            y += 56
        y += 10

    # Footer — nome studio + contatto
    footer_font = _get_font(28, bold=True)
    draw.text(
        (margin, SIZE[1] - 80),
        "STUDIO TECNICO CASALBONI",
        font=footer_font,
        fill=(*accent, 230),
    )
    footer_sub = _get_font(24)
    draw.text(
        (margin, SIZE[1] - 44),
        "Gambettola (FC)  ·  393 230 9508",
        font=footer_sub,
        fill=(200, 200, 200, 180),
    )

    img_rgb = img.convert("RGB")
    buf = io.BytesIO()
    img_rgb.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def generate_slides(slide_sections: list[dict]) -> list[dict]:
    """Genera le 3 immagini slide. Ritorna lista di dict: {"filename": str, "bytes": bytes}"""
    slides = []
    for i, section in enumerate(slide_sections[:3]):
        img_bytes = create_slide(
            title=section.get("title", f"Slide {i+1}"),
            content=section.get("content", ""),
            index=i,
        )
        slides.append({
            "filename": f"slide_{i+1}.png",
            "bytes": img_bytes,
        })
    return slides
