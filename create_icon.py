#!/usr/bin/env python3
"""
Generate a professional app icon (app_icon.ico) for Realtime Game Translator.
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_app_icon(output_path="app_icon.ico"):
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for size in sizes:
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Rounded rectangle background: Deep Navy / Cyber Blue gradient feel
        pad = max(1, int(w * 0.05))
        corner_radius = int(w * 0.22)
        bg_color = (24, 28, 42, 255)  # Dark sleek slate
        border_color = (0, 200, 255, 230)  # Neon cyan border
        
        # Draw background rounded rect
        draw.rounded_rectangle(
            [pad, pad, w - pad, h - pad],
            radius=corner_radius,
            fill=bg_color,
            outline=border_color,
            width=max(1, int(w * 0.04))
        )

        # Draw a translation symbol / speech graphic
        # Left bubble / card: Cyan accent
        c_x, c_y = w // 2, h // 2
        bubble_w = int(w * 0.35)
        bubble_h = int(h * 0.32)
        
        # Draw stylized audio wave / translation indicator
        wave_color = (0, 220, 255, 255)
        bar_count = 5
        bar_max_h = int(h * 0.38)
        bar_w = max(2, int(w * 0.07))
        spacing = max(2, int(w * 0.04))
        total_bars_w = (bar_count * bar_w) + ((bar_count - 1) * spacing)
        start_x = c_x - (total_bars_w // 2)

        height_factors = [0.45, 0.85, 1.0, 0.75, 0.40]
        for i, factor in enumerate(height_factors):
            bx = start_x + i * (bar_w + spacing)
            bh = int(bar_max_h * factor)
            by1 = c_y - (bh // 2)
            by2 = c_y + (bh // 2)
            # Center bar is glowing gold/amber or cyan
            col = (255, 180, 50, 255) if i == 2 else wave_color
            draw.rounded_rectangle([bx, by1, bx + bar_w, by2], radius=bar_w // 2, fill=col)

        images.append(img)

    # Save multi-resolution ICO
    images[0].save(
        output_path,
        format="ICO",
        sizes=sizes,
        append_images=images[1:]
    )
    print(f"[*] Icon successfully created at: {output_path}")

if __name__ == "__main__":
    create_app_icon()
