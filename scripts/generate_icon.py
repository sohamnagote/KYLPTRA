import os
from PIL import Image, ImageDraw, ImageFilter

def create_klyptra_icon(output_dir="build"):
    os.makedirs(output_dir, exist_ok=True)
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Subtle drop shadow
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([24, 28, 488, 492], radius=110, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    img.paste(shadow, (0, 0), shadow)

    # 2. Base Squircle with Apple-style deep violet gradient
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([32, 32, 480, 480], radius=105, fill=255)

    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(base)
    # Vertical gradient from #7C4DFF (124, 77, 255) to #4527A0 (69, 39, 160)
    for y in range(size):
        ratio = y / size
        r = int(124 * (1 - ratio) + 55 * ratio)
        g = int(77 * (1 - ratio) + 28 * ratio)
        b = int(255 * (1 - ratio) + 150 * ratio)
        bdraw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    img.paste(base, (0, 0), mask)

    # 3. Inner border / glass highlight
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle([32, 32, 480, 480], radius=105, outline=(255, 255, 255, 60), width=4)
    # Top subtle specular rim
    odraw.arc([32, 32, 480, 480], start=180, end=0, fill=(255, 255, 255, 120), width=3)
    img = Image.alpha_composite(img, overlay)

    # 4. Draw Center Emblem: Stylized Video Slate / Play Clapper + AI Sparkle
    emblem = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    edraw = ImageDraw.Draw(emblem)

    # Rounded slate body (film frame)
    edraw.rounded_rectangle([140, 160, 372, 350], radius=36, fill=(255, 255, 255, 240), outline=(255, 255, 255, 255), width=2)
    
    # Play triangle inside slate
    tri = [(235, 215), (235, 295), (305, 255)]
    edraw.polygon(tri, fill=(79, 55, 139, 255))

    # Top film perforations / clapper bars
    edraw.rounded_rectangle([155, 180, 180, 195], radius=6, fill=(124, 77, 255, 180))
    edraw.rounded_rectangle([195, 180, 220, 195], radius=6, fill=(124, 77, 255, 180))
    edraw.rounded_rectangle([292, 180, 317, 195], radius=6, fill=(124, 77, 255, 180))
    edraw.rounded_rectangle([332, 180, 357, 195], radius=6, fill=(124, 77, 255, 180))

    # 4-point AI Star / Sparkle at upper right
    star_center = (376, 150)
    sx, sy = star_center
    star_poly = [
        (sx, sy - 34),
        (sx + 7, sy - 7),
        (sx + 34, sy),
        (sx + 7, sy + 7),
        (sx, sy + 34),
        (sx - 7, sy + 7),
        (sx - 34, sy),
        (sx - 7, sy - 7)
    ]
    edraw.polygon(star_poly, fill=(255, 255, 255, 255))

    # Smaller sparkle
    sx2, sy2 = (146, 335)
    star_poly2 = [
        (sx2, sy2 - 16),
        (sx2 + 4, sy2 - 4),
        (sx2 + 16, sy2),
        (sx2 + 4, sy2 + 4),
        (sx2, sy2 + 16),
        (sx2 - 4, sy2 + 4),
        (sx2 - 16, sy2),
        (sx2 - 4, sy2 - 4)
    ]
    edraw.polygon(star_poly2, fill=(255, 255, 255, 200))

    img = Image.alpha_composite(img, emblem)

    # Save PNGs
    png_path = os.path.join(output_dir, "icon.png")
    img.save(png_path, "PNG")
    print(f"Saved {png_path}")

    # Generate multi-resolution ICO file for Windows
    ico_path = os.path.join(output_dir, "icon.ico")
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"Saved {ico_path} with sizes: {icon_sizes}")

if __name__ == "__main__":
    create_klyptra_icon()
