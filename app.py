from flask import Flask, render_template, request, jsonify
from pathlib import Path
from PIL import Image
import io
import base64
import random
import uuid

app = Flask(__name__)

# --- Config ---------------------------------------------------------------

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

# --- Mirror mapping templates ---------------------------------------------
# HORIZONTAL_MIRROR_MAP:
#   - roles: "top", "bottom", "middle" (rows)
#   - used when axis == "horizontal" (top/bottom mirroring)
#
# VERTICAL_MIRROR_MAP:
#   - roles: "left", "right", "middle" (columns)
#   - used when axis == "vertical" (left/right mirroring)

HORIZONTAL_MIRROR_MAP = {
    # Top row banners (source side of a horizontal mirror).
    "top": {
        "border.png": "border.png",
        "circle.png": "circle.png",
        # Example: keep top as "half_horizontal.png"
        "half_horizontal.png": "half_horizontal.png",
    },
    # Bottom row banners (mirrored from the top row).
    "bottom": {
        "border.png": "border.png",
        "circle.png": "circle.png",
        # Your example:
        #   top:    half_horizontal.png
        #   bottom: half_horizontal_bottom.png
        "half_horizontal.png": "half_horizontal_bottom.png",
        "half_horizontal_bottom.png": "half_horizontal.png",
        "triangle_bottom.png": "triangle_top.png",
        "square_bottom_left.png": "square_top_left.png",
        "square_bottom_right.png": "square_top_right.png",
        "square_top_right.png": "square_bottom_right.png",
        "square_top_left.png": "square_bottom_left.png",
        "stripe_top.png": "stripe_bottom.png",
        "stripe_bottom.png": "stripe_top.png",
        "gradient_up.png": "gradient.png",
        "gradient.png": "gradient_up.png",
    },
    # Middle row when height is odd.
    "middle": {
        "border.png": "border.png",
        "circle.png": "circle.png",
        # Your example: a compromise between top and bottom stripes
        "half_horizontal.png": "stripe_middle.png",
        "stripe_top.png": "stripe_middle.png",
        "stripe_bottom.png": "stripe_middle.png",
    },
}

VERTICAL_MIRROR_MAP = {
    # Left column banners (source side of a vertical mirror).
    "left": {
        "border.png": "border.png",
        "circle.png": "circle.png",
        # Example: keep left as "half_vertical.png"
        "half_vertical.png": "half_vertical.png",
        "stripe_left.png": "stripe_left.png",
        "stripe_right.png": "stripe_right.png",
    },
    # Right column banners (mirrored from the left side).
    "right": {
        "border.png": "border.png",
        "circle.png": "circle.png",
        # Your example:
        #   left:  half_vertical.png
        #   right: half_vertical_right.png
        "half_vertical.png": "half_vertical_right.png",
        "stripe_left.png": "stripe_right.png",
        "stripe_right.png": "stripe_left.png",
        "square_bottom_left.png": "square_bottom_right.png",
        "square_bottom_right.png": "square_bottom_left.png",
        "square_top_left.png": "square_top_right.png",
        "square_top_right.png": "square_top_left.png",
        "half_vertical_right.png": "half_vertical.png",
        "half_vertical.png": "half_vertical_right.png",
    },
    # Middle column when width is odd.
    "middle": {
        "border.png": "border.png",
        "circle.png": "circle.png",
        # Your example: center compromise stripe
        "half_vertical.png": "stripe_center.png",
        "stripe_left.png": "stripe_center.png",
        "square_top_right.png": "stripe_top.png",
        "square_top_left.png": "stripe_top.png",
        "square_bottom_right.png": "stripe_bottom.png",
        "square_bottom_left.png": "stripe_bottom.png",
    },
}


# --- Image helpers --------------------------------------------------------


def colorize_mask(img: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    """Apply an RGB color to an RGBA mask, preserving alpha."""
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    colored = Image.new("RGBA", img.size, rgb + (255,))
    colored.putalpha(a)
    return colored


def load_primitive(filename: str) -> Image.Image:
    """Load a primitive PNG from CROPPED_DIR with caching."""
    if filename in primitive_cache:
        return primitive_cache[filename]
    path = CROPPED_DIR / filename
    img = Image.open(path).convert("RGBA")
    primitive_cache[filename] = img
    return img


def list_primitive_files() -> list[str]:
    """Return all primitive filenames (PNG) in CROPPED_DIR."""
    if not CROPPED_DIR.exists():
        return []
    return sorted(
        f.name
        for f in CROPPED_DIR.iterdir()
        if f.is_file() and f.suffix.lower() == ".png"
    )


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
      where layers is a list of dicts like:
        { "kind": "base"|"pattern", "pattern": "file.png", "color": "magenta" }
    """
    primitive_files = list_primitive_files()
    if not primitive_files:
        # Failsafe: blank 20x40 image
        img = Image.new("RGBA", (20, 40), (0, 0, 0, 0))
        return img, []

    base_filename = "base.png"
    excluded_patterns = excluded_patterns or []

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
    layers.append(
        {
            "kind": "base",
            "pattern": base_filename,
            "color": base_color,
        }
    )

    # Pattern layers
    if pattern_files:
        num_layers = random.randint(0, NUM_PATTERN_LAYERS)
        for _ in range(num_layers):
            pat_file = random.choice(pattern_files)
            dye_name = random.choice(color_pool)
            rgb = DYE_COLORS[dye_name]
            pat_img = load_primitive(pat_file)
            pat_colored = colorize_mask(pat_img, rgb)
            result.alpha_composite(pat_colored)

            layers.append(
                {
                    "kind": "pattern",
                    "pattern": pat_file,
                    "color": dye_name,
                }
            )

    return result, layers


def render_banner_from_layers(layers: list[dict]) -> Image.Image:
    """
    Deterministically render a banner from a list of layer dicts
    like the ones returned by generate_random_banner.
    """
    # Find base layer if present
    base_layer = None
    for layer in layers:
        if layer.get("kind") == "base":
            base_layer = layer
            break

    if base_layer is None:
        # Fallback: assume base.png with white if no explicit base
        base_layer = {"kind": "base", "pattern": "base.png", "color": "white"}

    base_pattern = base_layer.get("pattern", "base.png")
    base_color_name = base_layer.get("color", "white")
    base_rgb = DYE_COLORS.get(base_color_name, (255, 255, 255))

    base_img = load_primitive(base_pattern)
    width, height = base_img.size
    result = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Draw base first
    base_colored = colorize_mask(base_img, base_rgb)
    result.alpha_composite(base_colored)

    # Draw the rest in order, skipping base since we already handled it
    for layer in layers:
        if layer is base_layer:
            continue
        if layer.get("kind") == "base":
            continue  # ignore any extra base layers

        pattern_name = layer.get("pattern")
        color_name = layer.get("color")
        if not pattern_name or not color_name:
            continue

        try:
            prim_img = load_primitive(pattern_name)
        except FileNotFoundError:
            continue

        rgb = DYE_COLORS.get(color_name, (255, 255, 255))
        colored = colorize_mask(prim_img, rgb)
        result.alpha_composite(colored)

    return result


def pil_to_data_url(img: Image.Image) -> str:
    """Encode a PIL image as a data: URL."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# --- Routes ---------------------------------------------------------------


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
    Generate a flat batch of random banners.

    JSON body:
      {
        "count": <int>,
        "exclude_patterns": [ "border.png", ... ],
        "exclude_colors": [ "red", "lime", ... ]
      }
    """
    data = request.get_json(silent=True) or {}

    count = int(data.get("count", 1))
    if count < 1:
        count = 1
    if count > 1000:
        count = 1000  # soft cap

    excluded_patterns = data.get("exclude_patterns") or []
    excluded_colors = data.get("exclude_colors") or []

    # Allowed colors = everything except excluded_colors
    all_colors = list(DYE_COLORS.keys())
    allowed_colors = [c for c in all_colors if c not in excluded_colors]
    if not allowed_colors:
        allowed_colors = all_colors

    banners: list[dict] = []

    for _ in range(count):
        img, layers = generate_random_banner(
            excluded_patterns=excluded_patterns,
            allowed_colors=allowed_colors,
        )
        slug = uuid.uuid4().hex[:8]
        banners.append(
            {
                "slug": slug,
                "src": pil_to_data_url(img),
                "layers": layers,
            }
        )

    return jsonify({"banners": banners})


@app.route("/api/generate_grid", methods=["POST"])
def api_generate_grid():
    """
    Generate a width x height grid of banners.

    JSON body:
      {
        "width": <int>,
        "height": <int>,
        "exclude_patterns": [...],
        "exclude_colors": [...]
      }

    Returns:
      {
        "width": <int>,
        "height": <int>,
        "banners": [ ... length = width*height ... ]
      }
    """
    data = request.get_json(silent=True) or {}

    width = int(data.get("width", 1))
    height = int(data.get("height", 1))

    if width < 1:
        width = 1
    if height < 1:
        height = 1

    # Soft caps
    if width > 32:
        width = 32
    if height > 32:
        height = 32

    total = width * height
    if total > 400:
        # clamp total but keep aspect roughly similar
        height = max(1, 400 // max(1, width))
        total = width * height

    excluded_patterns = data.get("exclude_patterns") or []
    excluded_colors = data.get("exclude_colors") or []

    all_colors = list(DYE_COLORS.keys())
    allowed_colors = [c for c in all_colors if c not in excluded_colors]
    if not allowed_colors:
        allowed_colors = all_colors

    banners: list[dict] = []

    for _ in range(total):
        img, layers = generate_random_banner(
            excluded_patterns=excluded_patterns,
            allowed_colors=allowed_colors,
        )
        slug = uuid.uuid4().hex[:8]
        banners.append(
            {
                "slug": slug,
                "src": pil_to_data_url(img),
                "layers": layers,
            }
        )

    return jsonify(
        {
            "width": width,
            "height": height,
            "banners": banners,
        }
    )


def _translate_pattern(pattern_name: str, role: str, axis: str) -> str:
    """
    Look up a mirrored pattern name for a given role and axis.

    axis: "horizontal" (top-bottom) or "vertical" (left-right)
    role:
      for horizontal -> "top" | "bottom" | "middle"   (rows)
      for vertical   -> "left" | "right" | "middle"   (columns)
    """
    if axis == "horizontal":
        mapping = HORIZONTAL_MIRROR_MAP.get(role, {})
    else:
        mapping = VERTICAL_MIRROR_MAP.get(role, {})
    return mapping.get(pattern_name, pattern_name)



def _transform_layers_for_role(layers: list[dict], role: str, axis: str) -> list[dict]:
    """
    Given a list of layer dicts and a role, return a new list of layers
    where pattern names have been translated according to the mirror maps.

    Base layers are kept unchanged.
    """
    new_layers: list[dict] = []
    for layer in layers:
        if layer.get("kind") == "base":
            # Keep base as-is
            new_layers.append(dict(layer))
            continue

        pattern_name = layer.get("pattern")
        if not pattern_name:
            new_layers.append(dict(layer))
            continue

        new_pattern = _translate_pattern(pattern_name, role=role, axis=axis)
        new_layer = dict(layer)
        new_layer["pattern"] = new_pattern
        new_layers.append(new_layer)

    return new_layers


@app.route("/api/mirror_grid", methods=["POST"])
def api_mirror_grid():
    """
    Mirror an existing grid horizontally (left/right) or vertically (top/bottom)
    using hand-defined mirror maps.

    JSON body:
      {
        "axis": "horizontal" | "vertical",
        "width": <int>,
        "height": <int>,
        "banners": [
          { "layers": [...] },
          ...
        ]
      }

    Returns the same shape:
      {
        "width": <int>,
        "height": <int>,
        "banners": [
          { "slug": "...", "src": "data:image/png;...", "layers": [...] },
          ...
        ]
      }
    """
    data = request.get_json(silent=True) or {}
    axis = data.get("axis", "horizontal")
    if axis not in ("horizontal", "vertical"):
        axis = "horizontal"

    width = int(data.get("width", 1))
    height = int(data.get("height", 1))
    banners_in = data.get("banners") or []

    if width < 1 or height < 1 or not banners_in:
        return jsonify({"width": width, "height": height, "banners": []})

    # Normalize sizes
    total = width * height
    if len(banners_in) < total:
        # Pad with empty banners if needed
        pad = total - len(banners_in)
        banners_in = list(banners_in) + [{}] * pad
    elif len(banners_in) > total:
        banners_in = banners_in[:total]

    # Build 2D array of layers (row-major)
    grid_layers: list[list[list[dict]]] = []
    for r in range(height):
        row_layers: list[list[dict]] = []
        for c in range(width):
            idx = r * width + c
            banner = banners_in[idx] or {}
            layers = banner.get("layers") or []
            row_layers.append(layers)
        grid_layers.append(row_layers)

    new_grid_layers: list[list[list[dict]]] = [[[] for _ in range(width)] for _ in range(height)]

    if axis == "horizontal":
        # Mirror top <-> bottom rows
        for c in range(width):
            for r in range(height):
                mirror_r = height - 1 - r
                if r > mirror_r:
                    continue

                top_r = r
                bottom_r = mirror_r

                if top_r == bottom_r:
                    # Middle row
                    role = "middle"
                    orig_layers = grid_layers[top_r][c]
                    new_layers = _transform_layers_for_role(
                        orig_layers, role=role, axis=axis
                    )
                    new_grid_layers[top_r][c] = new_layers
                else:
                    # Top is canonical source
                    top_layers = grid_layers[top_r][c]
                    new_top_layers = _transform_layers_for_role(
                        top_layers, role="top", axis=axis
                    )
                    new_bottom_layers = _transform_layers_for_role(
                        top_layers, role="bottom", axis=axis
                    )

                    new_grid_layers[top_r][c] = new_top_layers
                    new_grid_layers[bottom_r][c] = new_bottom_layers

    else:
        # axis == "vertical": mirror left <-> right columns
        for r in range(height):
            for c in range(width):
                mirror_c = width - 1 - c
                if c > mirror_c:
                    continue

                left_c = c
                right_c = mirror_c

                if left_c == right_c:
                    # Middle column
                    role = "middle"
                    orig_layers = grid_layers[r][left_c]
                    new_layers = _transform_layers_for_role(
                        orig_layers, role=role, axis=axis
                    )
                    new_grid_layers[r][left_c] = new_layers
                else:
                    # Left is canonical source
                    left_layers = grid_layers[r][left_c]
                    new_left_layers = _transform_layers_for_role(
                        left_layers, role="left", axis=axis
                    )
                    new_right_layers = _transform_layers_for_role(
                        left_layers, role="right", axis=axis
                    )

                    new_grid_layers[r][left_c] = new_left_layers
                    new_grid_layers[r][right_c] = new_right_layers


    # Flatten back to row-major and render images
    out_banners: list[dict] = []
    for r in range(height):
        for c in range(width):
            layers = new_grid_layers[r][c]
            if not layers:
                # Keep it blank if we somehow ended up with no layers
                img = Image.new("RGBA", (20, 40), (0, 0, 0, 0))
                rendered_layers: list[dict] = []
            else:
                img = render_banner_from_layers(layers)
                rendered_layers = layers

            slug = uuid.uuid4().hex[:8]
            out_banners.append(
                {
                    "slug": slug,
                    "src": pil_to_data_url(img),
                    "layers": rendered_layers,
                }
            )

    return jsonify({"width": width, "height": height, "banners": out_banners})


if __name__ == "__main__":
    app.run(debug=True)
