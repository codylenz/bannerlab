import os
from PIL import Image

# 20x40 region starting at (1,1)
FRONT_X, FRONT_Y = 1, 1
FRONT_W, FRONT_H = 20, 40
FRONT_BOX = (FRONT_X, FRONT_Y, FRONT_X + FRONT_W, FRONT_Y + FRONT_H)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir  = os.path.join(script_dir, "banner")
    output_dir = os.path.join(script_dir, "banner_cropped")

    # Make output folder if missing
    os.makedirs(output_dir, exist_ok=True)

    # List all PNG files in banner/
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(".png")]

    print(f"Found {len(files)} primitives to crop.")

    for filename in files:
        in_path  = os.path.join(input_dir, filename)
        out_path = os.path.join(output_dir, filename)

        img = Image.open(in_path).convert("RGBA")
        cropped = img.crop(FRONT_BOX)
        cropped.save(out_path)

        print(f"Cropped {filename} → {out_path}")

    print("Done! Cropped primitives saved to banner_cropped/")

if __name__ == "__main__":
    main()
