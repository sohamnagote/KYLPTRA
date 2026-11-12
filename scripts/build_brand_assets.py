import os
from PIL import Image, ImageDraw, ImageFilter

def generate_brand_assets(out_dir="public/brand", build_dir="build"):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)

    # 1. Generate SVG Logo
    svg_mark = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" fill="none">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#22252C"/>
      <stop offset="100%" stop-color="#14161A"/>
    </linearGradient>
    <linearGradient id="stemGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#F8FAFC"/>
      <stop offset="100%" stop-color="#CBD5E1"/>
    </linearGradient>
    <linearGradient id="upperArmGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="100%" stop-color="#E2E8F0"/>
    </linearGradient>
    <linearGradient id="lowerArmGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#E2E8F0"/>
      <stop offset="100%" stop-color="#94A3B8"/>
    </linearGradient>
    <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3B82F6"/>
      <stop offset="100%" stop-color="#1D4ED8"/>
    </linearGradient>
  </defs>

  <!-- Squircle Base Container -->
  <rect x="32" y="32" width="448" height="448" rx="104" fill="url(#bgGrad)" stroke="rgba(255,255,255,0.12)" stroke-width="3"/>
  <rect x="35" y="35" width="442" height="442" rx="101" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>

  <!-- Left Vertical Stem (Timeline Playhead Pillar) -->
  <rect x="144" y="128" width="56" height="256" rx="16" fill="url(#stemGrad)"/>
  
  <!-- Precision Cut Indicator Notch on Stem -->
  <rect x="194" y="244" width="6" height="24" rx="3" fill="url(#accentGrad)"/>

  <!-- Upper Diagonal Arm (Precision Cutting Blade) -->
  <path d="M 236 244 L 328 152 C 336 144 348 144 356 152 L 364 160 C 372 168 372 180 364 188 L 292 260 C 286 266 278 266 272 260 Z" fill="url(#upperArmGrad)"/>

  <!-- Precision Edit Negative Gap Notch & Accent Blade -->
  <polygon points="304,136 320,120 336,136 320,152" fill="url(#accentGrad)"/>

  <!-- Lower Diagonal Arm (Timeline Playback Track) -->
  <path d="M 236 268 L 328 360 C 336 368 348 368 356 360 L 364 352 C 372 344 372 332 364 324 L 292 252 C 286 246 278 246 272 252 Z" fill="url(#lowerArmGrad)"/>
</svg>'''

    with open(os.path.join(out_dir, "klyptra-logo.svg"), "w", encoding="utf-8") as f:
        f.write(svg_mark)

    # 2. SVG Wordmark
    svg_wordmark = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 128" fill="none">
  <defs>
    <linearGradient id="wmStem" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#334155"/>
    </linearGradient>
    <linearGradient id="wmAccent" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563EB"/>
      <stop offset="100%" stop-color="#1D4ED8"/>
    </linearGradient>
  </defs>

  <!-- Mini Logo Mark (80x80) -->
  <g transform="translate(16, 24)">
    <rect x="0" y="0" width="80" height="80" rx="20" fill="#181A20" stroke="rgba(0,0,0,0.1)" stroke-width="1"/>
    <rect x="20" y="20" width="10" height="40" rx="3" fill="#F8FAFC"/>
    <polygon points="34,38 48,24 54,30 40,44" fill="#E2E8F0"/>
    <polygon points="46,22 50,18 54,22 50,26" fill="url(#wmAccent)"/>
    <polygon points="34,42 48,56 54,50 40,36" fill="#94A3B8"/>
  </g>

  <!-- Typography Wordmark -->
  <text x="116" y="74" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="34" font-weight="800" letter-spacing="4" fill="#0F172A">KLYPTRA</text>
  <text x="362" y="72" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="12" font-weight="600" letter-spacing="3" fill="#64748B">STUDIO</text>
</svg>'''

    with open(os.path.join(out_dir, "klyptra-wordmark.svg"), "w", encoding="utf-8") as f:
        f.write(svg_wordmark)

    # 3. High-res Raster PNG Generation using Pillow
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Base drop shadow
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([32, 40, 480, 488], radius=104, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    img.paste(shadow, (0, 0), shadow)

    # Base Squircle Card
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(base)

    # Architectural Graphite Gradient (Dark Slate #262930 to #14161A)
    for y in range(size):
        ratio = y / size
        r = int(38 * (1 - ratio) + 18 * ratio)
        g = int(41 * (1 - ratio) + 20 * ratio)
        b = int(48 * (1 - ratio) + 26 * ratio)
        bdraw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([32, 32, 480, 480], radius=104, fill=255)
    img.paste(base, (0, 0), mask)

    # Metallic / Glass Rim Highlight
    rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(rim)
    rdraw.rounded_rectangle([32, 32, 480, 480], radius=104, outline=(255, 255, 255, 38), width=3)
    rdraw.arc([32, 32, 480, 480], start=180, end=0, fill=(255, 255, 255, 75), width=2)
    img = Image.alpha_composite(img, rim)

    # Foreground Emblem (The KLYPTRA Architectural K)
    emblem = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    edraw = ImageDraw.Draw(emblem)

    # Vertical Stem (Timeline Pillar)
    edraw.rounded_rectangle([144, 128, 200, 384], radius=16, fill=(245, 247, 250, 255))
    # Bevel highlight on stem
    edraw.line([(147, 144), (147, 368)], fill=(255, 255, 255, 180), width=2)

    # Active Cut Notch Indicator on stem
    edraw.rounded_rectangle([192, 244, 198, 268], radius=3, fill=(37, 99, 235, 255))

    # Upper Diagonal Arm (Precision Blade)
    upper_blade = [
        (236, 244),
        (328, 152),
        (364, 188),
        (272, 280)
    ]
    edraw.polygon(upper_blade, fill=(240, 244, 248, 255))
    # Upper edge bevel
    edraw.line([(236, 244), (328, 152)], fill=(255, 255, 255, 240), width=2)

    # Precision Edit Diamond Marker in Notch
    diamond = [
        (332, 118),
        (350, 136),
        (332, 154),
        (314, 136)
    ]
    edraw.polygon(diamond, fill=(37, 99, 235, 255))
    edraw.polygon(diamond, outline=(96, 165, 250, 220))

    # Lower Diagonal Arm (Timeline Playback Track)
    lower_blade = [
        (236, 268),
        (328, 360),
        (364, 324),
        (272, 232)
    ]
    edraw.polygon(lower_blade, fill=(180, 190, 205, 255))
    edraw.line([(236, 268), (328, 360)], fill=(210, 220, 235, 200), width=2)

    img = Image.alpha_composite(img, emblem)

    # Save 512x512
    p512 = os.path.join(out_dir, "klyptra-icon-512.png")
    img.save(p512, "PNG")

    # Generate multi-scale assets
    scales = [256, 128, 64, 48, 32, 24, 16]
    for s in scales:
        resized = img.resize((s, s), Image.Resampling.LANCZOS)
        resized.save(os.path.join(out_dir, f"klyptra-icon-{s}.png"), "PNG")

    # Save build icons for Windows application & installer
    build_png = os.path.join(build_dir, "icon.png")
    img.save(build_png, "PNG")
    build_ico = os.path.join(build_dir, "icon.ico")
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(build_ico, format="ICO", sizes=icon_sizes)

    print("Successfully generated all KLYPTRA brand assets, SVG sources, and Windows ICO.")

if __name__ == "__main__":
    generate_brand_assets()

