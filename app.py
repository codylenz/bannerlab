
from flask import Flask, render_template, request, jsonify
from pathlib import Path
from PIL import Image
import io
import base64
import random
import uuid

app = Flask(__name__)

# --- Config ---

NUM_PATTERN_LAYERS = 6  # layers on top of base

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

primitive_cache: dict[str, Image.Image] = {}


# --- Image helpers ---

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


def generate_random_banner(
    excluded_patterns: list[str] | None = None,
    allowed_colors: list[str] | None = None,
) -> tuple[Image.Image, list[dict]]:
    """
    Generate a single random banner:
      - base.png with random dye from allowed_colors (or all colors)
      - up to NUM_PATTERN_LAYERS random pattern layers with random dyes
        from allowed_colors, excluding any patterns in excluded_patterns.

    Returns:
      (PIL.Image, layers)
      where layers is a list of dicts:
        { "kind": "base"|"pattern", "pattern": "file.png", "color": "magenta" }
    """
    primitive_files = list_primitive_files()
    base_filename = "base.png"

    # Patterns = all primitives except base
    pattern_files = [f for f in primitive_files if f != base_filename]

    # Apply pattern exclusions
    if excluded_patterns:
        excluded_set = set(excluded_patterns)
        pattern_files = [f for f in pattern_files if f not in excluded_set]

    # Color pool
    all_color_names = list(DYE_COLORS.keys())
    if allowed_colors:
        color_pool = [c for c in allowed_colors if c in DYE_COLORS]
        if not color_pool:
            color_pool = all_color_names
    else:
        color_pool = all_color_names

    base_img = load_primitive(base_filename)
    width, height = base_img.size
    result = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    layers: list[dict] = []

    # Base layer
    base_color = random.choice(color_pool)
    base_rgb = DYE_COLORS[base_color]
    base_colored = colorize_mask(base_img, base_rgb)
    result.alpha_composite(base_colored)
    layers.append({
        "kind": "base",
        "pattern": base_filename,
        "color": base_color,
    })

    # Pattern layers (skip if no patterns available after exclusions)
    for _ in range(NUM_PATTERN_LAYERS):
        if not pattern_files:
            break
        pat_file = random.choice(pattern_files)
        dye_name = random.choice(color_pool)
        rgb = DYE_COLORS[dye_name]

        pat_img = load_primitive(pat_file)
        pat_colored = colorize_mask(pat_img, rgb)
        result.alpha_composite(pat_colored)

        layers.append({
            "kind": "pattern",
            "pattern": pat_file,
            "color": dye_name,
        })

    return result, layers


def pil_to_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/patterns")
def api_patterns():
    """Return list of pattern filenames (excluding base.png)."""
    primitive_files = list_primitive_files()
    base_filename = "base.png"
    pattern_files = [f for f in primitive_files if f != base_filename]
    return jsonify({"patterns": pattern_files})


@app.route("/api/colors")
def api_colors():
    """Return list of dye color names."""
    return jsonify({"colors": list(DYE_COLORS.keys())})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """
    Expect JSON:
      {
        "count": <int>,
        "exclude_patterns": [ "border.png", ... ],
        "exclude_colors": [ "red", "lime", ... ]
      }

    Returns:
      {
        "banners": [
          {
            "slug": "abcd1234",
            "src": "data:image/png;base64,...",
            "layers": [
              {"kind": "base", "pattern": "base.png", "color": "magenta"},
              {"kind": "pattern", "pattern": "gradient.png", "color": "black"},
              ...
            ]
          },
          ...
        ]
      }
    """
    data = request.get_json() or {}
    count = int(data.get("count", 1))
    if count < 1:
        count = 1
    if count > 1000:
        count = 1000  # soft cap

    # Patterns
    exclude_patterns = data.get("exclude_patterns", []) or []
    exclude_patterns = [str(p) for p in exclude_patterns]

    # Colors
    exclude_colors = data.get("exclude_colors", []) or []
    exclude_colors = [str(c) for c in exclude_colors]

    all_color_names = list(DYE_COLORS.keys())
    allowed_colors = [c for c in all_color_names if c not in exclude_colors]
    if not allowed_colors:
        allowed_colors = all_color_names

    banners = []
    for _ in range(count):
        img, layers = generate_random_banner(
            excluded_patterns=exclude_patterns,
            allowed_colors=allowed_colors,
        )
        slug = uuid.uuid4().hex[:8]
        banners.append({
            "slug": slug,
            "src": pil_to_data_url(img),
            "layers": layers,
        })

    return jsonify({"banners": banners})


if __name__ == "__main__":
    app.run(debug=True)
