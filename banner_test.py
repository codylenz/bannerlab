from PIL import Image
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRIM_DIR = os.path.join(SCRIPT_DIR, "banner")
BASE_TEXTURE = "base.png"
PATTERN_TEXTURE = "border.png"


FRONT_X, FRONT_Y = 1, 1
FRONT_W, FRONT_H = 20, 40
FRONT_BOX = (FRONT_X, FRONT_Y, FRONT_X + FRONT_W, FRONT_Y + FRONT_H)


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


def colorize_mask(img: Image.Image, rgb):
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    colored = Image.new("RGBA", img.size, rgb + (255,))
    colored.putalpha(a)
    return colored

def main():
    # 1. Load the raw textures
    base_tex = Image.open(f"{PRIM_DIR}/{BASE_TEXTURE}").convert("RGBA")
    border_tex = Image.open(f"{PRIM_DIR}/{PATTERN_TEXTURE}").convert("RGBA")

    # 2. Crop just the front panel from both
    base_front = base_tex.crop(FRONT_BOX)
    border_front = border_tex.crop(FRONT_BOX)

    # 3. Pick colors
    base_color   = DYE_COLORS["magenta"]   # banner base color
    border_color = DYE_COLORS["yellow"]     # pattern color

    # 4. Colorize using alpha as mask
    colored_base   = colorize_mask(base_front, base_color)
    colored_border = colorize_mask(border_front, border_color)

    # 5. Composite base + border into final 20x40
    # Start with transparent canvas
    result = Image.new("RGBA", (FRONT_W, FRONT_H), (0, 0, 0, 0))

    # Order matters: base first, then pattern
    result = Image.alpha_composite(result, colored_base)
    result = Image.alpha_composite(result, colored_border)

    # 6. Save test result
    out_path = os.path.join(SCRIPT_DIR, "banner_test.png")
    result.save(out_path)
    print("Saved to:", out_path)


if __name__ == "__main__":
    main()

# placeholder