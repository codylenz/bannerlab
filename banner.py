import os
import random
import uuid
from pathlib import Path
from PIL import Image

# --- Config ---

NUM_PATTERN_LAYERS = 5
NUM_GENERATIONS = 100   # <-- how many banners you want each run

DYE_COLORS = {
    "white":      (255, 255, 255),
    "orange":     (216, 127, 51),
    "magenta":    (178, 76, 216),
    "light_blue": (102, 153, 216),
    "yellow":     (229, 229, 51),
    "lime":       (127, 204, 25),
    "pink":       (242, 127, 165),
    "gray":       (76, 76, 76),
    "light_gray": (153, 153, 153),
    "cyan":       (76, 127, 153),
    "purple":     (127, 63, 178),
    "blue":       (51, 76, 178),
    "brown":      (102, 76, 51),
    "green":      (102, 127, 51),
    "red":        (153, 51, 51),
    "black":      (25, 25, 25),
}

SCRIPT_DIR = Path(__file__).parent.resolve()
CROPPED_DIR = SCRIPT_DIR / "banner_cropped"
GENERATED_DIR = SCRIPT_DIR / "generated"

primitive_cache: dict[str, Image.Image] = {}


def colorize_mask(img: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    colored = Image.new("RGBA", img.size, rgb + (255,))
    colored.putalpha(a)
    return colored


def load_primitive(filename: str) -> Image.Image:
    if filename in primitive_cache:
        return primitive_cache[filename]

    path = CROPPED_DIR / filename
    img = Image.open(path).convert("RGBA")
    primitive_cache[filename] = img
    return img


def list_primitive_files() -> list[str]:
    return [
        f.name
        for f in CROPPED_DIR.iterdir()
        if f.is_file() and f.suffix.lower() == ".png"
    ]


def generate_random_banner() -> Image.Image:
    primitive_files = list_primitive_files()
    base_filename = "base.png"
    pattern_files = [f for f in primitive_files if f != base_filename]

    base_img = load_primitive(base_filename)
    width, height = base_img.size
    result = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    base_color = random.choice(list(DYE_COLORS.keys()))
    base_rgb = DYE_COLORS[base_color]

    print(f"Base: {base_filename} ({base_color})")

    base_colored = colorize_mask(base_img, base_rgb)
    result.alpha_composite(base_colored)

    for i in range(NUM_PATTERN_LAYERS):
        pat_file = random.choice(pattern_files)
        dye = random.choice(list(DYE_COLORS.keys()))
        rgb = DYE_COLORS[dye]

        print(f"Layer {i+1}: {pat_file} ({dye})")

        pat_img = load_primitive(pat_file)
        pat_colored = colorize_mask(pat_img, rgb)
        result.alpha_composite(pat_colored)

    return result


def main():
    GENERATED_DIR.mkdir(exist_ok=True)

    print(f"Generating {NUM_GENERATIONS} banners...\n")

    for i in range(NUM_GENERATIONS):
        print(f"=== Banner {i+1}/{NUM_GENERATIONS} ===")
        img = generate_random_banner()

        slug = uuid.uuid4().hex[:8]
        filename = f"banner_{slug}.png"
        out_path = GENERATED_DIR / filename
        img.save(out_path)

        print(f"Saved to: {out_path}\n")


if __name__ == "__main__":
    main()
