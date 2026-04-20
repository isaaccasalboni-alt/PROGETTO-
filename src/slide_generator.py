import io
from PIL import Image, ImageDraw, ImageFont

# 3 temi cromatici per le 3 slide (Instagram aesthetic)
SLIDE_THEMES = [
    {"bg_top": "#833ab4", "bg_bottom": "#fd1d1d", "accent": "#fcb045"},
    {"bg_top": "#0f3460", "bg_bottom": "#16213e", "accent": "#e94560"},
    {"bg_top": "#134e5e", "bg_bottom": "#71b280", "accent": "#ffffff"},
]

SIZE = (1080, 1080)


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


def create_slide(title: str, content: str, index: int) -> bytes:
    theme = SLIDE_THEMES[index % len(SLIDE_THEMES)]
    img = Image.new("RGB", SIZE)
    draw = ImageDraw.Draw(img)

    # Sfondo sfumato verticale
    top = _hex(theme["bg_top"])
    bot = _hex(theme["bg_bottom"])
    for y in range(SIZE[1]):
        color = _lerp(top, bot, y / SIZE[1])
        draw.line([(0, y), (SIZE[0], y)], fill=color)

    # Barra accent in alto
    accent = _hex(theme["accent"])
    draw.rectangle([(0, 0), (SIZE[0], 8)], fill=accent)

    # Numero slide (badge)
    badge_font = _get_font(32, bold=True)
    badge_text = f"{index + 1} / 3"
    draw.text((54, 34), badge_text, font=badge_font, fill=(*accent, 220))

    # Linea decorativa
    draw.rectangle([(54, 90), (200, 96)], fill=(*accent, 180))

    # Titolo
    title_font = _get_font(72, bold=True)
    margin = 54
    max_w = SIZE[0] - margin * 2
    title_lines = _wrap_text(title.upper(), title_font, max_w, draw)
    y = 130
    for line in title_lines[:3]:
        draw.text((margin, y), line, font=title_font, fill=(255, 255, 255))
        y += 84

    # Separatore
    y += 20
    draw.rectangle([(margin, y), (margin + 80, y + 4)], fill=accent)
    y += 40

    # Contenuto
    body_font = _get_font(44)
    for para in content.split("\n"):
        lines = _wrap_text(para.strip(), body_font, max_w, draw)
        for line in lines:
            if y > SIZE[1] - 200:
                break
            draw.text((margin, y), line, font=body_font, fill=(230, 230, 230))
            y += 56
        y += 10

    # Footer
    footer_font = _get_font(28)
    draw.text(
        (margin, SIZE[1] - 70),
        "instagram agent · generato con AI",
        font=footer_font,
        fill=(255, 255, 255, 120),
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def generate_slides(slide_sections: list[dict]) -> list[dict]:
    """
    Genera le 3 immagini slide.
    Ritorna lista di dict: {"filename": str, "bytes": bytes}
    """
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
