"""Mockup v2: Bold edges + arrow callouts + textured face strips."""
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


def draw_hatching(draw, polygon_points, spacing=6, color='#999999', width=1):
    """Draw diagonal hatching lines inside a polygon (clipped manually)."""
    # Get bounding box
    xs = [p[0] for p in polygon_points]
    ys = [p[1] for p in polygon_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Generate diagonal lines (45 degrees)
    total = max_x - min_x + max_y - min_y
    for offset in range(0, int(total), spacing):
        # Line from top-left to bottom-right direction
        x_start = min_x + offset
        y_start = min_y
        x_end = min_x + offset - (max_y - min_y)
        y_end = max_y

        # Clip line to polygon using simple edge intersection
        intersections = []
        n = len(polygon_points)
        for i in range(n):
            p1 = polygon_points[i]
            p2 = polygon_points[(i + 1) % n]
            result = line_segment_intersect(x_start, y_start, x_end, y_end, p1[0], p1[1], p2[0], p2[1])
            if result:
                intersections.append(result)

        if len(intersections) >= 2:
            intersections.sort()
            for j in range(0, len(intersections) - 1, 2):
                draw.line([intersections[j], intersections[j + 1]], fill=color, width=width)


def line_segment_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    """Find intersection of two line segments."""
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    if 0 <= t <= 1 and 0 <= u <= 1:
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)
        return (ix, iy)
    return None


def draw_iso_box_with_edgebands(draw, ox, oy, dl, dw, dh, edgebands):
    """Draw iso box with optional textured strips on faces for edgebands."""
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
    draw.polygon([f_tl, f_tr, b_tr, b_tl], fill='#e0e0e0', outline='#555555', width=2)
    # Right face
    draw.polygon([f_br, b_br, b_tr, f_tr], fill='#d0d0d0', outline='#555555', width=2)
    # Front face
    draw.polygon([f_bl, f_br, f_tr, f_tl], fill='#eeeeee', outline='#555555', width=2)

    # Edgeband strip thickness (fraction of dikte for the strip on the face)
    strip_frac = 0.25  # 25% of the face height as edgeband strip
    hatch_color = '#aaaaaa'

    # Boven edgeband: strip along TOP of front face
    if 'boven' in edgebands:
        # Thin strip at top of front face
        strip_h = dh * strip_frac
        s_tl = f_tl
        s_tr = f_tr
        s_br = (f_tr[0], f_tr[1] + strip_h)
        s_bl = (f_tl[0], f_tl[1] + strip_h)
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill='#ddd5c8', outline=None)
        draw_hatching(draw, [s_tl, s_tr, s_br, s_bl], spacing=5, color=hatch_color)
        draw.line([s_bl, s_br], fill='#888888', width=1)

    # Onder edgeband: strip along BOTTOM of front face
    if 'onder' in edgebands:
        strip_h = dh * strip_frac
        s_bl = f_bl
        s_br = f_br
        s_tr = (f_br[0], f_br[1] - strip_h)
        s_tl = (f_bl[0], f_bl[1] - strip_h)
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill='#ddd5c8', outline=None)
        draw_hatching(draw, [s_tl, s_tr, s_br, s_bl], spacing=5, color=hatch_color)
        draw.line([s_tl, s_tr], fill='#888888', width=1)

    # Rechts edgeband: strip along RIGHT face (left edge of right face = shared with front)
    if 'rechts' in edgebands:
        # Strip on right side face near the front edge
        strip_depth = iso_x * strip_frac
        s_bl = f_br
        s_tl = f_tr
        # Offset along the depth direction
        depth_ux = (b_br[0] - f_br[0]) / (math.sqrt((b_br[0]-f_br[0])**2 + (b_br[1]-f_br[1])**2) or 1)
        depth_uy = (b_br[1] - f_br[1]) / (math.sqrt((b_br[0]-f_br[0])**2 + (b_br[1]-f_br[1])**2) or 1)
        s_br = (f_br[0] + depth_ux * strip_depth, f_br[1] + depth_uy * strip_depth)
        s_tr = (f_tr[0] + depth_ux * strip_depth, f_tr[1] + depth_uy * strip_depth)
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill='#c8c5be', outline=None)
        draw_hatching(draw, [s_tl, s_tr, s_br, s_bl], spacing=5, color=hatch_color)
        draw.line([s_tr, s_br], fill='#888888', width=1)

    # Links edgeband: strip on the left side of front face (not really a separate visible face)
    if 'links' in edgebands:
        strip_w_px = dl * strip_frac * 0.3  # narrow strip on left of front face
        s_tl = f_tl
        s_bl = f_bl
        s_br = (f_bl[0] + strip_w_px, f_bl[1])
        s_tr = (f_tl[0] + strip_w_px, f_tl[1])
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill='#ddd5c8', outline=None)
        draw_hatching(draw, [s_tl, s_tr, s_br, s_bl], spacing=5, color=hatch_color)
        draw.line([s_tr, s_br], fill='#888888', width=1)

    # Redraw front face outline and right face outline on top
    draw.polygon([f_bl, f_br, f_tr, f_tl], fill=None, outline='#555555', width=2)
    draw.polygon([f_br, b_br, b_tr, f_tr], fill=None, outline='#555555', width=2)

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
            draw.line([p1, p2], fill='#000000', width=4)

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


# ============================================================
# All 4 sides with edgeband
# ============================================================
img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)

title_font = get_font(18, bold=True)
d.rectangle([(0, 0), (W, 45)], fill='#333333')
d.text((W/2, 22), 'V2: Textured Strips + Callouts (all 4 sides)', fill='white', font=title_font, anchor='mm')

ox, oy = 200, 360
dl, dw, dh = 260, 100, 65

edgebands = {
    'boven': 'Fineer eik 1mm',
    'onder': 'Fineer eik 1mm',
    'links': 'Fineer eik 1mm',
    'rechts': 'Fineer eik 1mm',
}

corners = draw_iso_box_with_edgebands(d, ox, oy, dl, dw, dh, edgebands)
draw_dim_arrows(d, corners, 1922, 441, 19, dl, dw, dh)

f_tl = corners['f_tl']
f_tr = corners['f_tr']
f_bl = corners['f_bl']
f_br = corners['f_br']
b_tl = corners['b_tl']
b_tr = corners['b_tr']

eb_font = get_font(11, bold=True)
callout_color = '#333333'

# Top face edges
edge_defs = {
    'boven':  (b_tl, b_tr),
    'onder':  (f_tl, f_tr),
    'links':  (f_tl, b_tl),
    'rechts': (f_tr, b_tr),
}

# Callout positions - "onder" moved to the left side to avoid lengte arrow
callout_positions = {
    'boven':  {'lx': (b_tl[0] + b_tr[0]) / 2, 'ly': b_tl[1] - 55, 'anchor': 'ms'},
    'onder':  {'lx': f_bl[0] - 30, 'ly': oy + 55, 'anchor': 'rm'},
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
    d.text((lx, ly), label_text, fill=callout_color, font=eb_font, anchor=cp['anchor'])
    bbox = d.textbbox((lx, ly), label_text, font=eb_font, anchor=cp['anchor'])
    if side == 'boven':
        arrow_start = ((bbox[0] + bbox[2]) / 2, bbox[3] + 2)
    elif side == 'onder':
        arrow_start = (bbox[2] + 4, (bbox[1] + bbox[3]) / 2)
    elif side == 'links':
        arrow_start = (bbox[2] + 4, (bbox[1] + bbox[3]) / 2)
    else:
        arrow_start = (bbox[0] - 4, (bbox[1] + bbox[3]) / 2)
    d.line([arrow_start, (mid_x, mid_y)], fill=callout_color, width=1)
    draw_arrowhead(d, mid_x, mid_y, arrow_start[0], arrow_start[1], callout_color, 8)

img.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_callout_v2_all.png')
print("Saved concept_callout_v2_all.png")


# ============================================================
# Only boven + onder (partial)
# ============================================================
img2 = Image.new('RGB', (W, H), BG)
d2 = ImageDraw.Draw(img2)

d2.rectangle([(0, 0), (W, 45)], fill='#333333')
d2.text((W/2, 22), 'V2: Textured Strips + Callouts (boven + onder only)', fill='white', font=title_font, anchor='mm')

edgebands2 = {
    'boven': 'Fineer eik 1mm',
    'onder': 'Fineer eik 1mm',
}

corners2 = draw_iso_box_with_edgebands(d2, ox, oy, dl, dw, dh, edgebands2)
draw_dim_arrows(d2, corners2, 1922, 441, 19, dl, dw, dh)

for side, label_text in edgebands2.items():
    if side not in edge_defs:
        continue
    p1, p2 = edge_defs[side]
    mid_x = (p1[0] + p2[0]) / 2
    mid_y = (p1[1] + p2[1]) / 2
    cp = callout_positions[side]
    lx, ly = cp['lx'], cp['ly']
    d2.text((lx, ly), label_text, fill=callout_color, font=eb_font, anchor=cp['anchor'])
    bbox = d2.textbbox((lx, ly), label_text, font=eb_font, anchor=cp['anchor'])
    if side == 'boven':
        arrow_start = ((bbox[0] + bbox[2]) / 2, bbox[3] + 2)
    elif side == 'onder':
        arrow_start = (bbox[2] + 4, (bbox[1] + bbox[3]) / 2)
    d2.line([arrow_start, (mid_x, mid_y)], fill=callout_color, width=1)
    draw_arrowhead(d2, mid_x, mid_y, arrow_start[0], arrow_start[1], callout_color, 8)

img2.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_callout_v2_partial.png')
print("Saved concept_callout_v2_partial.png")

print("\nDone!")
