# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow",
# ]
# ///
"""Make the images the site publishes from the artwork in art/.

    uv run tools/make_images.py

Run it after replacing a file in art/. The site publishes the copies in
static/images/, which are sized for the page and far smaller than the artwork.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent.parent
ART = ROOT / "art"
IMAGES = ROOT / "static" / "images"
EDGE = 2  # The banner artwork has a dark line around it


def save(image: Image.Image, name: str, **options) -> None:
    target = IMAGES / name
    image.save(target, **options)
    print(f"{target.relative_to(ROOT)}: {image.width}x{image.height}, {target.stat().st_size:,} bytes")


def main() -> None:
    banner = Image.open(ART / "WinterTechForumBanner.png").convert("RGB")
    logo = Image.open(ART / "wtf-web-nodate.jpg").convert("RGB")

    # The home page banner, at the artwork's size.
    save(banner, "wtf-banner.webp", quality=82, method=6)

    # The logo in the menu bar. It displays at 36 pixels; 108 keeps it sharp
    # on a phone screen with three device pixels to each CSS pixel.
    save(logo.resize((108, 108), Image.Resampling.LANCZOS), "wtf-logo.jpg", quality=85, optimize=True)

    # The picture a shared link shows: 1200x630, cut from the middle of the
    # banner so the lettering fills the card.
    height = banner.height - 2 * EDGE
    width = round(height * 1200 / 630)
    left = round(banner.width * 0.25)
    card = banner.crop((left, EDGE, left + width, EDGE + height))
    save(card.resize((1200, 630), Image.Resampling.LANCZOS), "wtf-card.jpg", quality=85, optimize=True)


if __name__ == "__main__":
    main()
