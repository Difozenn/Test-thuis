"""Mockup: Bold edges + arrow callouts pointing to edges with edge type."""
from PIL import Image, ImageDraw, ImageFont
import math

BG = '#f5f5f5'
W, H = 800, 650


def get_font(size, bold=False):
    try:
        if bold:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()


def draw_iso_box(draw, ox, oy, dl, dw, dh):
    """Draw the standard iso box and return corner points."""
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

    # Back edges dashed
    for start, end in [(b_bl, b_br), (b_bl, b_tl)]:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx**2 + dy**2)
        if length < 1:
            continue
        segments = int(length / 8)
        for i in range(0, segments, 2):
            t1 = i / segments
            t2 = min((i + 1) / segments, 1)
            draw.line(
                [(start[0] + dx*t1, start[1] + dy*t1),
                 (start[0] + dx*t2, start[1] + dy*t2)],
                fill='#aaaaaa', width=2
            )

    # Top face
    draw.polygon([f_tl, f_tr, b_tr, b_tl], fill='#e0e0e0', outline='#555555', width=2)
    # Right face
    draw.polygon([f_br, b_br, b_tr, f_tr], fill='#d0d0d0', outline='#555555', width=2)
    # Front face
    draw.polygon([f_bl, f_br, f_tr, f_tl], fill='#eeeeee', outline='#555555', width=2)

    return {
        'f_bl': f_bl, 'f_br': f_br, 'f_tr': f_tr, 'f_tl': f_tl,
        'b_bl': b_bl, 'b_br': b_br, 'b_tr': b_tr, 'b_tl': b_tl
    }


def draw_dim_arrows(draw, corners, length, width, height, dl, dw, dh):
    """Draw dimension arrows."""
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


def draw_arrowhead(draw, tip_x, tip_y, from_x, from_y, color='#000000', size=8):
    """Draw an arrowhead at (tip_x, tip_y) coming from direction (from_x, from_y)."""
    dx = tip_x - from_x
    dy = tip_y - from_y
    length = math.sqrt(dx**2 + dy**2) or 1
    ux, uy = dx / length, dy / length
    # Perpendicular
    px, py = -uy, ux

    # Triangle points
    base_x = tip_x - ux * size
    base_y = tip_y - uy * size
    p1 = (base_x + px * size * 0.4, base_y + py * size * 0.4)
    p2 = (base_x - px * size * 0.4, base_y - py * size * 0.4)
    draw.polygon([(tip_x, tip_y), p1, p2], fill=color)


# ============================================================
# Concept: Bold edges + arrow callouts
# ============================================================
img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)

title_font = get_font(20, bold=True)
d.rectangle([(0, 0), (W, 50)], fill='#333333')
d.text((W/2, 25), 'Bold Edges + Arrow Callouts', fill='white', font=title_font, anchor='mm')

# Iso box - centered with room for callouts
ox, oy = 180, 380
dl, dw, dh = 280, 110, 70
corners = draw_iso_box(d, ox, oy, dl, dw, dh)
draw_dim_arrows(d, corners, 1922, 441, 19, dl, dw, dh)

f_bl = corners['f_bl']
f_br = corners['f_br']
f_tr = corners['f_tr']
f_tl = corners['f_tl']
b_bl = corners['b_bl']
b_br = corners['b_br']
b_tr = corners['b_tr']
b_tl = corners['b_tl']

eb_color = '#000000'
eb_font = get_font(11, bold=True)
callout_color = '#333333'

# === Edgeband data ===
edgebands = {
    'boven': 'Fineer eik 1mm',
    'onder': 'Fineer eik 1mm',
    'links': 'Fineer eik 1mm',
    'rechts': 'Fineer eik 1mm',
}

# Top face edges for edgeband
edge_defs = {
    'boven':  {'p1': b_tl, 'p2': b_tr},
    'onder':  {'p1': f_tl, 'p2': f_tr},
    'links':  {'p1': f_tl, 'p2': b_tl},
    'rechts': {'p1': f_tr, 'p2': b_tr},
}

# Callout positions: where the label text sits (away from box)
callout_positions = {
    'boven':  {'lx': (b_tl[0] + b_tr[0]) / 2, 'ly': b_tl[1] - 70, 'anchor': 'ms'},
    'onder':  {'lx': (f_bl[0] + f_br[0]) / 2, 'ly': oy + 60, 'anchor': 'mt'},
    'links':  {'lx': f_tl[0] - 80, 'ly': (f_tl[1] + b_tl[1]) / 2 - 30, 'anchor': 'rm'},
    'rechts': {'lx': b_tr[0] + 80, 'ly': (f_tr[1] + b_tr[1]) / 2 - 10, 'anchor': 'lm'},
}

for side, label_text in edgebands.items():
    if side not in edge_defs:
        continue

    p1 = edge_defs[side]['p1']
    p2 = edge_defs[side]['p2']

    # Bold edge on the iso box
    d.line([p1, p2], fill=eb_color, width=4)

    # Midpoint of the edge (arrow target)
    mid_x = (p1[0] + p2[0]) / 2
    mid_y = (p1[1] + p2[1]) / 2

    # Label position
    cp = callout_positions[side]
    lx, ly = cp['lx'], cp['ly']

    # Draw label text
    d.text((lx, ly), label_text, fill=callout_color, font=eb_font, anchor=cp['anchor'])

    # Get text bbox for arrow start point
    bbox = d.textbbox((lx, ly), label_text, font=eb_font, anchor=cp['anchor'])
    # Arrow from label toward edge midpoint
    if side == 'boven':
        arrow_start = ((bbox[0] + bbox[2]) / 2, bbox[3] + 2)
    elif side == 'onder':
        arrow_start = ((bbox[0] + bbox[2]) / 2, bbox[1] - 2)
    elif side == 'links':
        arrow_start = (bbox[2] + 4, (bbox[1] + bbox[3]) / 2)
    else:  # rechts
        arrow_start = (bbox[0] - 4, (bbox[1] + bbox[3]) / 2)

    # Draw arrow line
    d.line([arrow_start, (mid_x, mid_y)], fill=callout_color, width=1)
    # Draw arrowhead at edge
    draw_arrowhead(d, mid_x, mid_y, arrow_start[0], arrow_start[1], callout_color, 8)

img.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_callout.png')
print("Saved concept_callout.png")


# ============================================================
# Same but with only 2 edges having edgeband (boven + onder)
# ============================================================
img2 = Image.new('RGB', (W, H), BG)
d2 = ImageDraw.Draw(img2)

d2.rectangle([(0, 0), (W, 50)], fill='#333333')
d2.text((W/2, 25), 'Callouts - Only Boven + Onder', fill='white', font=title_font, anchor='mm')

corners = draw_iso_box(d2, ox, oy, dl, dw, dh)
draw_dim_arrows(d2, corners, 1922, 441, 19, dl, dw, dh)

edgebands2 = {
    'boven': 'Fineer eik 1mm',
    'onder': 'Fineer eik 1mm',
}

for side, label_text in edgebands2.items():
    if side not in edge_defs:
        continue
    p1 = edge_defs[side]['p1']
    p2 = edge_defs[side]['p2']
    d2.line([p1, p2], fill=eb_color, width=4)
    mid_x = (p1[0] + p2[0]) / 2
    mid_y = (p1[1] + p2[1]) / 2
    cp = callout_positions[side]
    lx, ly = cp['lx'], cp['ly']
    d2.text((lx, ly), label_text, fill=callout_color, font=eb_font, anchor=cp['anchor'])
    bbox = d2.textbbox((lx, ly), label_text, font=eb_font, anchor=cp['anchor'])
    if side == 'boven':
        arrow_start = ((bbox[0] + bbox[2]) / 2, bbox[3] + 2)
    elif side == 'onder':
        arrow_start = ((bbox[0] + bbox[2]) / 2, bbox[1] - 2)
    d2.line([arrow_start, (mid_x, mid_y)], fill=callout_color, width=1)
    draw_arrowhead(d2, mid_x, mid_y, arrow_start[0], arrow_start[1], callout_color, 8)

img2.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_callout_partial.png')
print("Saved concept_callout_partial.png")

print("\nDone! Check temp/ folder")
