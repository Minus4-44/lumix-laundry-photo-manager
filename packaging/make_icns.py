"""Build a macOS .icns from the same LUMIX wordmark design; run on macOS from the project root."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SIZE = 1024
INSET = 100  # macOS grid: 824px content inside a 1024px canvas
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def font(size):
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_icon():
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    card = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    left, top = INSET, INSET
    right, bottom = SIZE - INSET, SIZE - INSET
    draw.rounded_rectangle((left, top, right, bottom), radius=185, fill=(16, 17, 20, 255))
    # Keep the Windows-proportioned wordmark inside the rounded card.
    scale = (right - left) / 512
    draw.text(
        ((left + right) / 2, top + 250 * scale),
        "LUMIX",
        font=font(int(118 * scale)),
        fill="#f4f4f5",
        anchor="mm",
        stroke_width=2,
    )
    draw.rounded_rectangle(
        (
            left + 47 * scale,
            top + 330 * scale,
            left + 465 * scale,
            top + 345 * scale,
        ),
        radius=int(6 * scale),
        fill="#da4444",
    )
    image.alpha_composite(card)
    return image


def main():
    icns = ROOT / "pianji" / "ui" / "lumix.icns"
    icon = draw_icon()
    work = Path(tempfile.mkdtemp(prefix="lumix-icns-"))
    try:
        iconset = work / "lumix.iconset"
        iconset.mkdir()
        for base in (16, 32, 64, 128, 256, 512):
            icon.resize((base, base), Image.Resampling.LANCZOS).save(
                iconset / f"icon_{base}x{base}.png"
            )
            icon.resize((base * 2, base * 2), Image.Resampling.LANCZOS).save(
                iconset / f"icon_{base}x{base}@2x.png"
            )
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(icns)], check=True
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(icns, icns.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
