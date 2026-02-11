"""Generate mirror icon variations - closet door with 2/3 mirror panel."""
from PIL import Image, ImageDraw
import os

SIZE = 256
OUT = os.path.dirname(os.path.abspath(__file__))


def make_base():
    """Transparent background - the tkinter button provides the container."""
    return Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))


# Equal margin on both sides: door +-55, mirror +-30 => 25px margin each side
DOOR_L = -55
DOOR_R = 55
MIRROR_L = -30
MIRROR_R = 30
MARGIN = DOOR_R - MIRROR_R  # 25px, same on both sides


def closet_mirror_v1():
    """Clean flat style - centered mirror, handle beside it."""
    img = make_base()
    draw = ImageDraw.Draw(img)
    cx, cy = SIZE // 2, SIZE // 2

    # Door body
    draw.rounded_rectangle((cx+DOOR_L, cy-85, cx+DOOR_R, cy+85), radius=6,
                           fill='#d0c4b0', outline='#5a5a5a', width=5)

    # Mirror panel (top 2/3) - centered
    mirror_top = cy - 78
    mirror_bot = cy + 30
    draw.rounded_rectangle((cx+MIRROR_L, mirror_top, cx+MIRROR_R, mirror_bot), radius=4,
                           fill='#b0d0e8', outline='#6a8a9a', width=3)

    # Mirror shine
    draw.line((cx+MIRROR_L+10, mirror_top+12, cx+MIRROR_L+28, mirror_bot-15), fill='#dceef8', width=5)
    draw.line((cx+MIRROR_L+18, mirror_top+12, cx+MIRROR_L+36, mirror_bot-15), fill='#d0e8f5', width=3)

    # Subtle reflection hint
    draw.line((cx+MIRROR_R-18, mirror_top+20, cx+MIRROR_R-10, mirror_bot-30), fill='#c8e0f0', width=2)

    # Wood grain lines on bottom 1/3
    for y in [mirror_bot + 15, mirror_bot + 28, mirror_bot + 41]:
        draw.line((cx+DOOR_L+17, y, cx+DOOR_R-13, y), fill='#c0b49e', width=1)

    # Door handle beside mirror
    hx = cx + MIRROR_R + (MARGIN // 2)
    draw.ellipse((hx-6, cy-12, hx+6, cy), fill='#909080', outline='#5a5a5a', width=3)

    img.save(os.path.join(OUT, 'spiegel_closet_v1.png'))


def closet_mirror_v2():
    """Menu-matching style - centered mirror, handle beside it."""
    img = make_base()
    draw = ImageDraw.Draw(img)
    cx, cy = SIZE // 2, SIZE // 2

    # Door frame
    draw.rounded_rectangle((cx-58, cy-88, cx+58, cy+88), radius=8,
                           fill='#8a7a6a', outline='#5a5a5a', width=3)
    # Door body
    draw.rounded_rectangle((cx-52, cy-82, cx+52, cy+82), radius=5,
                           fill='#d8ccb8', outline='#6a6050', width=4)

    # Mirror panel (top 2/3) - centered
    mirror_top = cy - 75
    mirror_bot = cy + 28
    draw.rounded_rectangle((cx+MIRROR_L, mirror_top, cx+MIRROR_R, mirror_bot), radius=5,
                           fill='#a8c8e0', outline='#4a6a80', width=4)

    # Mirror glass inner
    draw.rounded_rectangle((cx+MIRROR_L+7, mirror_top+7, cx+MIRROR_R-7, mirror_bot-7), radius=3,
                           fill='#c0ddf0', outline=None)

    # Shine highlight
    draw.line((cx+MIRROR_L+10, mirror_top+15, cx+MIRROR_L+25, mirror_bot-18), fill='#e0f0ff', width=5)
    draw.line((cx+MIRROR_L+18, mirror_top+15, cx+MIRROR_L+33, mirror_bot-18), fill='#d5ebfa', width=3)

    # Bottom wood panel
    draw.rounded_rectangle((cx-40, mirror_bot+10, cx+40, cy+72), radius=3,
                           fill='#e0d4c0', outline='#8a7a6a', width=2)

    # Handle beside mirror
    hx = cx + MIRROR_R + (MARGIN // 2)
    draw.rounded_rectangle((hx-5, cy-10, hx+5, cy+10), radius=2,
                           fill='#a09888', outline='#5a5a5a', width=3)

    img.save(os.path.join(OUT, 'spiegel_closet_v2.png'))


def closet_mirror_v3():
    """3D/depth style - centered mirror, handle beside it."""
    img = make_base()
    draw = ImageDraw.Draw(img)
    cx, cy = SIZE // 2, SIZE // 2

    # Shadow behind door
    draw.rounded_rectangle((cx-48, cy-78, cx+58, cy+88), radius=6,
                           fill='#b0b0b0', outline=None)

    # Door body
    draw.rounded_rectangle((cx+DOOR_L, cy-85, cx+DOOR_R-3, cy+82), radius=6,
                           fill='#d5c9b5', outline='#5a5050', width=5)

    # Mirror panel (top 2/3) - centered
    mirror_top = cy - 76
    mirror_bot = cy + 26

    # Mirror bevel/frame
    draw.rounded_rectangle((cx+MIRROR_L-4, mirror_top-2, cx+MIRROR_R+2, mirror_bot+2), radius=4,
                           fill='#7a8a9a', outline=None)
    # Mirror surface
    draw.rounded_rectangle((cx+MIRROR_L, mirror_top+2, cx+MIRROR_R-2, mirror_bot-2), radius=3,
                           fill='#b5d5ec', outline='#5a7a90', width=2)

    # Gradient-like shine
    for i, xoff in enumerate(range(MIRROR_L+8, MIRROR_L+28, 4)):
        alpha_w = 5 - i
        if alpha_w > 0:
            draw.line((cx+xoff, mirror_top+10, cx+xoff+12, mirror_bot-12),
                      fill='#daeefa', width=alpha_w)

    # Wood bottom panel
    draw.rounded_rectangle((cx+DOOR_L+12, mirror_bot+8, cx+DOOR_R-15, cy+72), radius=3,
                           fill='#ddd0bc', outline='#8a7a68', width=2)
    draw.line((cx+DOOR_L+20, mirror_bot+20, cx+DOOR_R-23, mirror_bot+20), fill='#cec0aa', width=1)
    draw.line((cx+DOOR_L+20, mirror_bot+30, cx+DOOR_R-23, mirror_bot+30), fill='#cec0aa', width=1)

    # Handle beside mirror
    hx = cx + MIRROR_R + (MARGIN // 2)
    draw.ellipse((hx-7, cy-12, hx+7, cy+2), fill='#c0b8a8', outline='#5a5a5a', width=3)
    draw.ellipse((hx-3, cy-8, hx+3, cy-2), fill='#e0d8c8')

    img.save(os.path.join(OUT, 'spiegel_closet_v3.png'))


def closet_mirror_v4():
    """Technical/blueprint style - centered mirror, handle beside it."""
    img = make_base()
    draw = ImageDraw.Draw(img)
    cx, cy = SIZE // 2, SIZE // 2

    # Door outline
    draw.rounded_rectangle((cx+DOOR_L, cy-85, cx+DOOR_R, cy+85), radius=4,
                           fill=None, outline='#5a5a5a', width=5)

    # Mirror area (top 2/3) - centered
    mirror_top = cy - 78
    mirror_bot = cy + 28
    draw.rounded_rectangle((cx+MIRROR_L, mirror_top, cx+MIRROR_R, mirror_bot), radius=3,
                           fill='#c5ddef', outline='#4a6a80', width=4)

    # Cross-hatch pattern in mirror
    for offset in range(-80, 120, 14):
        x0 = cx + MIRROR_L + 3
        y0 = mirror_top + 5 + offset
        x1 = cx + MIRROR_R - 3
        y1 = y0 - 40
        draw.line((max(x0, cx+MIRROR_L+3), max(y0, mirror_top+5),
                   min(x1, cx+MIRROR_R-3), max(y1, mirror_top+5)),
                  fill='#d5e8f5', width=1)

    # Dimension arrow showing 2/3
    arr_x = cx + DOOR_R + 8
    draw.line((arr_x, mirror_top, arr_x, mirror_bot), fill='#e07050', width=2)
    draw.polygon([(arr_x-4, mirror_top+8), (arr_x+4, mirror_top+8), (arr_x, mirror_top)],
                 fill='#e07050')
    draw.polygon([(arr_x-4, mirror_bot-8), (arr_x+4, mirror_bot-8), (arr_x, mirror_bot)],
                 fill='#e07050')

    # Bottom wood area
    draw.rounded_rectangle((cx+MIRROR_L, mirror_bot+8, cx+MIRROR_R, cy+78), radius=3,
                           fill='#e8dcc8', outline='#6a6050', width=3)

    # Handle beside mirror
    hx = cx + MIRROR_R + (MARGIN // 2)
    draw.line((hx, cy-10, hx, cy+10), fill='#5a5a5a', width=4)

    img.save(os.path.join(OUT, 'spiegel_closet_v4.png'))


if __name__ == '__main__':
    closet_mirror_v1()
    closet_mirror_v2()
    closet_mirror_v3()
    closet_mirror_v4()
    print("Generated 4 closet mirror icon variants in:", OUT)
