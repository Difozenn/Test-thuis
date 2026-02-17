"""Mockup v3: Realistic edgeband look - wood-toned face sections with grain."""
from PIL import Image, ImageDraw, ImageFont
import math
import random

BG = '#f5f5f5'
W, H = 800, 650


def get_font(size, bold=False):
    try:
        if bold:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()


def draw_arrowhead(draw, tip_x, tip_y, from_x, from_y, color='#000000', size=8):
    dx = tip_x - from_x
    dy = tip_y - from_y
    length = math.sqrt(dx**2 + dy**2) or 1
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    base_x = tip_x - ux * size
    base_y = tip_y - uy * size
    p1 = (base_x + px * size * 0.4, base_y + py * size * 0.4)
    p2 = (base_x - px * size * 0.4, base_y - py * size * 0.4)
    draw.polygon([(tip_x, tip_y), p1, p2], fill=color)


def draw_wood_grain_on_face(draw, corners, direction='horizontal', seed=42):
    """Draw subtle wood grain lines on a quadrilateral face.
    corners: list of 4 points [(x,y), ...] in order (tl, tr, br, bl)
    direction: 'horizontal' for lines along length, 'vertical' for along height
    """
    rng = random.Random(seed)
    tl, tr, br, bl = corners

    if direction == 'horizontal':
        # Grain lines run left-to-right (along the length)
        num_lines = rng.randint(3, 6)
        for i in range(num_lines):
            t = (i + 1) / (num_lines + 1) + rng.uniform(-0.05, 0.05)
            t = max(0.1, min(0.9, t))
            # Interpolate start (left edge) and end (right edge)
            sx = bl[0] + t * (tl[0] - bl[0])
            sy = bl[1] + t * (tl[1] - bl[1])
            ex = br[0] + t * (tr[0] - br[0])
            ey = br[1] + t * (tr[1] - br[1])
            draw.line([(sx, sy), (ex, ey)], fill='#b89968', width=1)
    else:
        # Grain lines run top-to-bottom
        num_lines = rng.randint(3, 6)
        for i in range(num_lines):
            t = (i + 1) / (num_lines + 1) + rng.uniform(-0.05, 0.05)
            t = max(0.1, min(0.9, t))
            sx = tl[0] + t * (tr[0] - tl[0])
            sy = tl[1] + t * (tr[1] - tl[1])
            ex = bl[0] + t * (br[0] - bl[0])
            ey = bl[1] + t * (br[1] - bl[1])
            draw.line([(sx, sy), (ex, ey)], fill='#b89968', width=1)


def draw_iso_box_with_edgebands(draw, ox, oy, dl, dw, dh, edgebands):
    iso_x = dw * 0.5
    iso_y = dw * 0.3

    f_bl = (ox, oy)
    f_br = (ox + dl, oy)
    f_tr = (ox + dl, oy - dh)
    f_tl = (ox, oy - dh)
    b_bl = (ox + iso_x, oy - iso_y)
    b_br = (ox + dl + iso_x, oy - iso_y)
    b_tr = (ox + dl + iso_x, oy - dh - iso_y)
    b_tl = (ox + iso_x, oy - dh - iso_y)

    # Colors
    face_default = '#eeeeee'
    face_default_side = '#d0d0d0'
    face_top = '#e0e0e0'
    eb_face_color = '#c9a96e'          # warm wood tone for edgeband
    eb_face_color_side = '#b8955c'     # slightly darker for right side
    eb_glue_line = '#8B7355'           # dark line = glue/separator
    outline_color = '#555555'

    # Back edges dashed
    for start, end in [(b_bl, b_br), (b_bl, b_tl)]:
        ddx = end[0] - start[0]
        ddy = end[1] - start[1]
        length = math.sqrt(ddx**2 + ddy**2)
        if length < 1:
            continue
        segments = int(length / 8)
        for i in range(0, segments, 2):
            t1 = i / segments
            t2 = min((i + 1) / segments, 1)
            draw.line(
                [(start[0] + ddx*t1, start[1] + ddy*t1),
                 (start[0] + ddx*t2, start[1] + ddy*t2)],
                fill='#aaaaaa', width=2
            )

    # Top face
    draw.polygon([f_tl, f_tr, b_tr, b_tl], fill=face_top, outline=outline_color, width=2)

    # === RIGHT SIDE FACE ===
    has_rechts = 'rechts' in edgebands
    if has_rechts:
        # Full right face is edgebanded
        draw.polygon([f_br, b_br, b_tr, f_tr], fill=eb_face_color_side, outline=outline_color, width=2)
        draw_wood_grain_on_face(draw, [f_tr, b_tr, b_br, f_br], direction='vertical', seed=99)
        # Redraw outline
        draw.polygon([f_br, b_br, b_tr, f_tr], fill=None, outline=outline_color, width=2)
    else:
        draw.polygon([f_br, b_br, b_tr, f_tr], fill=face_default_side, outline=outline_color, width=2)

    # === FRONT FACE ===
    has_boven = 'boven' in edgebands
    has_onder = 'onder' in edgebands

    if has_boven and has_onder:
        # Both top and bottom edgebanded - full face is edgeband
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=eb_face_color, outline=outline_color, width=2)
        draw_wood_grain_on_face(draw, [f_tl, f_tr, f_br, f_bl], direction='horizontal', seed=42)
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=None, outline=outline_color, width=2)
    elif has_boven:
        # Top portion edgebanded, bottom is core
        mid_y_frac = 0.5
        mid_l = (f_bl[0], f_bl[1] - dh * mid_y_frac)
        mid_r = (f_br[0], f_br[1] - dh * mid_y_frac)
        # Bottom part = core
        draw.polygon([f_bl, f_br, mid_r, mid_l], fill=face_default, outline=None)
        # Top part = edgeband
        draw.polygon([mid_l, mid_r, f_tr, f_tl], fill=eb_face_color, outline=None)
        draw_wood_grain_on_face(draw, [f_tl, f_tr, mid_r, mid_l], direction='horizontal', seed=42)
        # Glue line
        draw.line([mid_l, mid_r], fill=eb_glue_line, width=2)
        # Outline
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=None, outline=outline_color, width=2)
    elif has_onder:
        # Bottom portion edgebanded, top is core
        mid_y_frac = 0.5
        mid_l = (f_bl[0], f_bl[1] - dh * mid_y_frac)
        mid_r = (f_br[0], f_br[1] - dh * mid_y_frac)
        # Top part = core
        draw.polygon([mid_l, mid_r, f_tr, f_tl], fill=face_default, outline=None)
        # Bottom part = edgeband
        draw.polygon([f_bl, f_br, mid_r, mid_l], fill=eb_face_color, outline=None)
        draw_wood_grain_on_face(draw, [mid_l, mid_r, f_br, f_bl], direction='horizontal', seed=55)
        # Glue line
        draw.line([mid_l, mid_r], fill=eb_glue_line, width=2)
        # Outline
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=None, outline=outline_color, width=2)
    else:
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=face_default, outline=outline_color, width=2)

    # Links edgeband: thin strip on left edge of front face
    if 'links' in edgebands:
        strip_w = max(dl * 0.06, 4)
        s_tl = f_tl
        s_bl = f_bl
        s_br = (f_bl[0] + strip_w, f_bl[1])
        s_tr = (f_tl[0] + strip_w, f_tl[1])
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill=eb_face_color, outline=None)
        # Glue line on the right side of the strip
        draw.line([s_tr, s_br], fill=eb_glue_line, width=1)
        # Left outline
        draw.line([s_tl, s_bl], fill=outline_color, width=2)

    # Bold edges on top face where edgeband present
    edge_lines = {
        'boven':  (b_tl, b_tr),
        'onder':  (f_tl, f_tr),
        'links':  (f_tl, b_tl),
        'rechts': (f_tr, b_tr),
    }
    for side in edgebands:
        if side in edge_lines:
            p1, p2 = edge_lines[side]
            draw.line([p1, p2], fill='#000000', width=3)

    return {
        'f_bl': f_bl, 'f_br': f_br, 'f_tr': f_tr, 'f_tl': f_tl,
        'b_bl': b_bl, 'b_br': b_br, 'b_tr': b_tr, 'b_tl': b_tl
    }


def draw_dim_arrows(draw, corners, length, width, height, dl, dw, dh):
    ox = corners['f_bl'][0]
    oy = corners['f_bl'][1]
    font = get_font(12, bold=True)
    arrow_color = '#555555'
    gap = 14

    if length > 0:
        ay = oy + gap
        draw.line([(ox, ay), (ox + dl, ay)], fill=arrow_color, width=2)
        draw.text(((ox + ox + dl) / 2, ay + 6), f"{length:g} mm", fill='#333333', font=font, anchor='mt')

    if height > 0:
        ax = ox - gap
        draw.line([(ax, oy), (ax, oy - dh)], fill=arrow_color, width=2)
        draw.text((ax - 4, oy - dh / 2), f"{height:g}", fill='#333333', font=font, anchor='rm')

    if width > 0:
        f_br = corners['f_br']
        b_br = corners['b_br']
        re_dx = b_br[0] - f_br[0]
        re_dy = b_br[1] - f_br[1]
        re_len = math.sqrt(re_dx**2 + re_dy**2) or 1
        rp_ux = -re_dy / re_len
        rp_uy = re_dx / re_len
        ax1 = f_br[0] + rp_ux * gap
        ay1 = f_br[1] + rp_uy * gap
        ax2 = b_br[0] + rp_ux * gap
        ay2 = b_br[1] + rp_uy * gap
        draw.line([(ax1, ay1), (ax2, ay2)], fill=arrow_color, width=2)
        mx = (ax1 + ax2) / 2 + rp_ux * 14
        my = (ay1 + ay2) / 2 + rp_uy * 14
        draw.text((mx + 10, my), f"{width:g} mm", fill='#333333', font=font, anchor='lm')


def draw_callouts(draw, corners, edgebands):
    f_tl = corners['f_tl']
    f_tr = corners['f_tr']
    f_bl = corners['f_bl']
    b_tl = corners['b_tl']
    b_tr = corners['b_tr']

    eb_font = get_font(11, bold=True)
    callout_color = '#333333'

    edge_defs = {
        'boven':  (b_tl, b_tr),
        'onder':  (f_tl, f_tr),
        'links':  (f_tl, b_tl),
        'rechts': (f_tr, b_tr),
    }

    callout_positions = {
        'boven':  {'lx': (b_tl[0] + b_tr[0]) / 2, 'ly': b_tl[1] - 55, 'anchor': 'ms'},
        'onder':  {'lx': f_bl[0] - 30, 'ly': f_bl[1] + 55, 'anchor': 'rm'},
        'links':  {'lx': f_tl[0] - 70, 'ly': (f_tl[1] + b_tl[1]) / 2 - 25, 'anchor': 'rm'},
        'rechts': {'lx': b_tr[0] + 70, 'ly': (f_tr[1] + b_tr[1]) / 2, 'anchor': 'lm'},
    }

    for side, label_text in edgebands.items():
        if side not in edge_defs:
            continue
        p1, p2 = edge_defs[side]
        mid_x = (p1[0] + p2[0]) / 2
        mid_y = (p1[1] + p2[1]) / 2
        cp = callout_positions[side]
        lx, ly = cp['lx'], cp['ly']
        draw.text((lx, ly), label_text, fill=callout_color, font=eb_font, anchor=cp['anchor'])
        bbox = draw.textbbox((lx, ly), label_text, font=eb_font, anchor=cp['anchor'])
        if side == 'boven':
            arrow_start = ((bbox[0] + bbox[2]) / 2, bbox[3] + 2)
        elif side == 'onder':
            arrow_start = (bbox[2] + 4, (bbox[1] + bbox[3]) / 2)
        elif side == 'links':
            arrow_start = (bbox[2] + 4, (bbox[1] + bbox[3]) / 2)
        else:
            arrow_start = (bbox[0] - 4, (bbox[1] + bbox[3]) / 2)
        draw.line([arrow_start, (mid_x, mid_y)], fill=callout_color, width=1)
        draw_arrowhead(draw, mid_x, mid_y, arrow_start[0], arrow_start[1], callout_color, 8)


# ============================================================
# All 4 sides
# ============================================================
img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)

title_font = get_font(18, bold=True)
d.rectangle([(0, 0), (W, 45)], fill='#333333')
d.text((W/2, 22), 'V3: Wood-toned edgeband faces (all 4 sides)', fill='white', font=title_font, anchor='mm')

ox, oy = 200, 370
dl, dw, dh = 260, 100, 65
edgebands_all = {
    'boven': 'Fineer eik 1mm',
    'onder': 'Fineer eik 1mm',
    'links': 'Fineer eik 1mm',
    'rechts': 'Fineer eik 1mm',
}
corners = draw_iso_box_with_edgebands(d, ox, oy, dl, dw, dh, edgebands_all)
draw_dim_arrows(d, corners, 1922, 441, 19, dl, dw, dh)
draw_callouts(d, corners, edgebands_all)

img.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_v3_all.png')
print("Saved concept_v3_all.png")


# ============================================================
# Boven + onder only
# ============================================================
img2 = Image.new('RGB', (W, H), BG)
d2 = ImageDraw.Draw(img2)
d2.rectangle([(0, 0), (W, 45)], fill='#333333')
d2.text((W/2, 22), 'V3: Wood-toned edgeband faces (boven + onder)', fill='white', font=title_font, anchor='mm')

edgebands_partial = {
    'boven': 'Fineer eik 1mm',
    'onder': 'Fineer eik 1mm',
}
corners2 = draw_iso_box_with_edgebands(d2, ox, oy, dl, dw, dh, edgebands_partial)
draw_dim_arrows(d2, corners2, 1922, 441, 19, dl, dw, dh)
draw_callouts(d2, corners2, edgebands_partial)

img2.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_v3_partial.png')
print("Saved concept_v3_partial.png")


# ============================================================
# No edgebands at all (comparison)
# ============================================================
img3 = Image.new('RGB', (W, H), BG)
d3 = ImageDraw.Draw(img3)
d3.rectangle([(0, 0), (W, 45)], fill='#333333')
d3.text((W/2, 22), 'V3: No edgebands (standard iso box)', fill='white', font=title_font, anchor='mm')

corners3 = draw_iso_box_with_edgebands(d3, ox, oy, dl, dw, dh, {})
draw_dim_arrows(d3, corners3, 1922, 441, 19, dl, dw, dh)

img3.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_v3_none.png')
print("Saved concept_v3_none.png")

print("\nDone!")
