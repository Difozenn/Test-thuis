"""Mockup v5: Edgeband visible on top face AND side faces."""
from PIL import Image, ImageDraw, ImageFont
import math
import random

BG = '#f5f5f5'
W, H = 900, 700

EDGEBAND_STYLES = {
    'eik': {
        'fill': '#c9a96e',
        'fill_side': '#b8955c',
        'fill_top': '#c4a468',
        'grain': True,
        'grain_color': '#b08840',
        'grain_color_top': '#b59550',
    },
    'noot': {
        'fill': '#7a5c3a',
        'fill_side': '#6b4e30',
        'fill_top': '#725838',
        'grain': True,
        'grain_color': '#5e3f28',
        'grain_color_top': '#5a3d26',
    },
    'wit': {
        'fill': '#f0f0f0',
        'fill_side': '#e0e0e0',
        'fill_top': '#ebebeb',
        'grain': False,
    },
    'zwart': {
        'fill': '#2a2a2a',
        'fill_side': '#1e1e1e',
        'fill_top': '#252525',
        'grain': False,
    },
}
DEFAULT_STYLE = EDGEBAND_STYLES['eik']


def get_eb_style(label_text):
    text_lower = label_text.lower()
    for keyword, style in EDGEBAND_STYLES.items():
        if keyword in text_lower:
            return style
    return DEFAULT_STYLE


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


def lerp(p1, p2, t):
    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))


def draw_wavy_grain(draw, corners, grain_color, direction='horizontal', seed=42):
    rng = random.Random(seed)
    tl, tr, br, bl = corners

    if direction == 'horizontal':
        num_lines = rng.randint(4, 7)
        num_points = 20
        for i in range(num_lines):
            t = (i + 1) / (num_lines + 1)
            sx = bl[0] + t * (tl[0] - bl[0])
            sy = bl[1] + t * (tl[1] - bl[1])
            ex = br[0] + t * (tr[0] - br[0])
            ey = br[1] + t * (tr[1] - br[1])
            perp_dx = (tl[0] - bl[0])
            perp_dy = (tl[1] - bl[1])
            perp_len = math.sqrt(perp_dx**2 + perp_dy**2) or 1
            amplitude = perp_len * 0.04
            freq = 1.5 + (i % 3) * 0.7
            phase = i * 2.3
            points = []
            for p in range(num_points + 1):
                frac = p / num_points
                bx = sx + frac * (ex - sx)
                by = sy + frac * (ey - sy)
                wave = math.sin(frac * math.pi * freq + phase) * amplitude
                bx += wave * (perp_dx / perp_len)
                by += wave * (perp_dy / perp_len)
                points.append((bx, by))
            for j in range(len(points) - 1):
                draw.line([points[j], points[j + 1]], fill=grain_color, width=1)
    elif direction == 'vertical':
        num_lines = rng.randint(3, 5)
        num_points = 15
        for i in range(num_lines):
            t = (i + 1) / (num_lines + 1)
            sx = tl[0] + t * (tr[0] - tl[0])
            sy = tl[1] + t * (tr[1] - tl[1])
            ex = bl[0] + t * (br[0] - bl[0])
            ey = bl[1] + t * (br[1] - bl[1])
            perp_dx = (tr[0] - tl[0])
            perp_dy = (tr[1] - tl[1])
            perp_len = math.sqrt(perp_dx**2 + perp_dy**2) or 1
            amplitude = perp_len * 0.05
            freq = 1.2 + (i % 3) * 0.5
            phase = i * 1.8
            points = []
            for p in range(num_points + 1):
                frac = p / num_points
                bx = sx + frac * (ex - sx)
                by = sy + frac * (ey - sy)
                wave = math.sin(frac * math.pi * freq + phase) * amplitude
                bx += wave * (perp_dx / perp_len)
                by += wave * (perp_dy / perp_len)
                points.append((bx, by))
            for j in range(len(points) - 1):
                draw.line([points[j], points[j + 1]], fill=grain_color, width=1)
    elif direction == 'iso_lengte':
        # Grain along lengte direction on top face (isometric)
        num_lines = rng.randint(2, 4)
        num_points = 15
        for i in range(num_lines):
            t = (i + 1) / (num_lines + 1)
            sx = tl[0] + t * (bl[0] - tl[0])
            sy = tl[1] + t * (bl[1] - tl[1])
            ex = tr[0] + t * (br[0] - tr[0])
            ey = tr[1] + t * (br[1] - tr[1])
            perp_dx = bl[0] - tl[0]
            perp_dy = bl[1] - tl[1]
            perp_len = math.sqrt(perp_dx**2 + perp_dy**2) or 1
            amplitude = perp_len * 0.06
            freq = 1.3 + (i % 3) * 0.5
            phase = i * 2.1
            points = []
            for p in range(num_points + 1):
                frac = p / num_points
                bx = sx + frac * (ex - sx)
                by = sy + frac * (ey - sy)
                wave = math.sin(frac * math.pi * freq + phase) * amplitude
                bx += wave * (perp_dx / perp_len)
                by += wave * (perp_dy / perp_len)
                points.append((bx, by))
            for j in range(len(points) - 1):
                draw.line([points[j], points[j + 1]], fill=grain_color, width=1)
    elif direction == 'iso_breedte':
        # Grain along breedte direction on top face (isometric)
        num_lines = rng.randint(2, 4)
        num_points = 12
        for i in range(num_lines):
            t = (i + 1) / (num_lines + 1)
            sx = tl[0] + t * (tr[0] - tl[0])
            sy = tl[1] + t * (tr[1] - tl[1])
            ex = bl[0] + t * (br[0] - bl[0])
            ey = bl[1] + t * (br[1] - bl[1])
            perp_dx = tr[0] - tl[0]
            perp_dy = tr[1] - tl[1]
            perp_len = math.sqrt(perp_dx**2 + perp_dy**2) or 1
            amplitude = perp_len * 0.06
            freq = 1.2 + (i % 2) * 0.6
            phase = i * 1.9
            points = []
            for p in range(num_points + 1):
                frac = p / num_points
                bx = sx + frac * (ex - sx)
                by = sy + frac * (ey - sy)
                wave = math.sin(frac * math.pi * freq + phase) * amplitude
                bx += wave * (perp_dx / perp_len)
                by += wave * (perp_dy / perp_len)
                points.append((bx, by))
            for j in range(len(points) - 1):
                draw.line([points[j], points[j + 1]], fill=grain_color, width=1)


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

    face_default = '#eeeeee'
    face_default_side = '#d0d0d0'
    face_top = '#e0e0e0'
    glue_line_color = '#8B7355'
    outline_color = '#555555'

    # Strip fraction on top face (how wide the edgeband strip appears from above)
    top_strip_frac = 0.12

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

    # === TOP FACE ===
    # First draw default top face
    draw.polygon([f_tl, f_tr, b_tr, b_tl], fill=face_top, outline=outline_color, width=2)

    # Now draw edgeband strips on top face edges
    # Boven strip: along back edge (b_tl -> b_tr), inward toward front
    boven_style = get_eb_style(edgebands.get('boven', '')) if 'boven' in edgebands else None
    if boven_style:
        s_tl = b_tl
        s_tr = b_tr
        s_br = lerp(b_tr, f_tr, top_strip_frac)
        s_bl = lerp(b_tl, f_tl, top_strip_frac)
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill=boven_style['fill_top'], outline=None)
        if boven_style['grain']:
            draw_wavy_grain(draw, [s_tl, s_tr, s_br, s_bl],
                           boven_style.get('grain_color_top', boven_style['grain_color']),
                           direction='iso_lengte', seed=10)
        draw.line([s_bl, s_br], fill=glue_line_color, width=1)

    # Onder strip: along front edge (f_tl -> f_tr), inward toward back
    onder_style = get_eb_style(edgebands.get('onder', '')) if 'onder' in edgebands else None
    if onder_style:
        s_bl = f_tl
        s_br = f_tr
        s_tr = lerp(f_tr, b_tr, top_strip_frac)
        s_tl = lerp(f_tl, b_tl, top_strip_frac)
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill=onder_style['fill_top'], outline=None)
        if onder_style['grain']:
            draw_wavy_grain(draw, [s_tl, s_tr, s_br, s_bl],
                           onder_style.get('grain_color_top', onder_style['grain_color']),
                           direction='iso_lengte', seed=20)
        draw.line([s_tl, s_tr], fill=glue_line_color, width=1)

    # Links strip: along left edge (f_tl -> b_tl), inward toward right
    links_style = get_eb_style(edgebands.get('links', '')) if 'links' in edgebands else None
    if links_style:
        s_tl = b_tl
        s_bl = f_tl
        s_br = lerp(f_tl, f_tr, top_strip_frac)
        s_tr = lerp(b_tl, b_tr, top_strip_frac)
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill=links_style['fill_top'], outline=None)
        if links_style['grain']:
            draw_wavy_grain(draw, [s_tl, s_tr, s_br, s_bl],
                           links_style.get('grain_color_top', links_style['grain_color']),
                           direction='iso_breedte', seed=30)
        draw.line([s_tr, s_br], fill=glue_line_color, width=1)

    # Rechts strip: along right edge (f_tr -> b_tr), inward toward left
    rechts_style = get_eb_style(edgebands.get('rechts', '')) if 'rechts' in edgebands else None
    if rechts_style:
        s_tr = b_tr
        s_br = f_tr
        s_bl = lerp(f_tr, f_tl, top_strip_frac)
        s_tl = lerp(b_tr, b_tl, top_strip_frac)
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill=rechts_style['fill_top'], outline=None)
        if rechts_style['grain']:
            draw_wavy_grain(draw, [s_tl, s_tr, s_br, s_bl],
                           rechts_style.get('grain_color_top', rechts_style['grain_color']),
                           direction='iso_breedte', seed=40)
        draw.line([s_tl, s_bl], fill=glue_line_color, width=1)

    # Redraw top face outline
    draw.polygon([f_tl, f_tr, b_tr, b_tl], fill=None, outline=outline_color, width=2)

    # === RIGHT SIDE FACE ===
    if rechts_style:
        draw.polygon([f_br, b_br, b_tr, f_tr], fill=rechts_style['fill_side'], outline=outline_color, width=2)
        if rechts_style['grain']:
            draw_wavy_grain(draw, [f_tr, b_tr, b_br, f_br],
                           rechts_style['grain_color'], direction='vertical', seed=99)
        draw.polygon([f_br, b_br, b_tr, f_tr], fill=None, outline=outline_color, width=2)
    else:
        draw.polygon([f_br, b_br, b_tr, f_tr], fill=face_default_side, outline=outline_color, width=2)

    # === FRONT FACE ===
    if boven_style and onder_style:
        mid_l = (f_bl[0], f_bl[1] - dh * 0.5)
        mid_r = (f_br[0], f_br[1] - dh * 0.5)
        draw.polygon([f_tl, f_tr, mid_r, mid_l], fill=boven_style['fill'], outline=None)
        if boven_style['grain']:
            draw_wavy_grain(draw, [f_tl, f_tr, mid_r, mid_l],
                           boven_style['grain_color'], direction='horizontal', seed=42)
        draw.polygon([mid_l, mid_r, f_br, f_bl], fill=onder_style['fill'], outline=None)
        if onder_style['grain']:
            draw_wavy_grain(draw, [mid_l, mid_r, f_br, f_bl],
                           onder_style['grain_color'], direction='horizontal', seed=55)
        draw.line([mid_l, mid_r], fill=glue_line_color, width=1)
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=None, outline=outline_color, width=2)
    elif boven_style:
        mid_l = (f_bl[0], f_bl[1] - dh * 0.5)
        mid_r = (f_br[0], f_br[1] - dh * 0.5)
        draw.polygon([f_bl, f_br, mid_r, mid_l], fill=face_default, outline=None)
        draw.polygon([mid_l, mid_r, f_tr, f_tl], fill=boven_style['fill'], outline=None)
        if boven_style['grain']:
            draw_wavy_grain(draw, [f_tl, f_tr, mid_r, mid_l],
                           boven_style['grain_color'], direction='horizontal', seed=42)
        draw.line([mid_l, mid_r], fill=glue_line_color, width=1)
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=None, outline=outline_color, width=2)
    elif onder_style:
        mid_l = (f_bl[0], f_bl[1] - dh * 0.5)
        mid_r = (f_br[0], f_br[1] - dh * 0.5)
        draw.polygon([mid_l, mid_r, f_tr, f_tl], fill=face_default, outline=None)
        draw.polygon([f_bl, f_br, mid_r, mid_l], fill=onder_style['fill'], outline=None)
        if onder_style['grain']:
            draw_wavy_grain(draw, [mid_l, mid_r, f_br, f_bl],
                           onder_style['grain_color'], direction='horizontal', seed=55)
        draw.line([mid_l, mid_r], fill=glue_line_color, width=1)
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=None, outline=outline_color, width=2)
    else:
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=face_default, outline=outline_color, width=2)

    # Links: thin strip on left edge of front face
    if links_style:
        strip_w = max(dl * 0.06, 4)
        s_tl = f_tl
        s_bl = f_bl
        s_br = (f_bl[0] + strip_w, f_bl[1])
        s_tr = (f_tl[0] + strip_w, f_tl[1])
        draw.polygon([s_tl, s_tr, s_br, s_bl], fill=links_style['fill'], outline=None)
        if links_style['grain']:
            draw_wavy_grain(draw, [s_tl, s_tr, s_br, s_bl],
                           links_style['grain_color'], direction='vertical', seed=77)
        draw.line([s_tr, s_br], fill=glue_line_color, width=1)
        draw.line([s_tl, s_bl], fill=outline_color, width=2)

    # Bold edges on top face
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
    ac = '#555555'
    gap = 14
    if length > 0:
        ay = oy + gap
        draw.line([(ox, ay), (ox + dl, ay)], fill=ac, width=2)
        draw.text(((ox + ox + dl) / 2, ay + 6), f"{length:g} mm", fill='#333333', font=font, anchor='mt')
    if height > 0:
        ax = ox - gap
        draw.line([(ax, oy), (ax, oy - dh)], fill=ac, width=2)
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
        draw.line([(ax1, ay1), (ax2, ay2)], fill=ac, width=2)
        mx = (ax1 + ax2) / 2 + rp_ux * 14
        my = (ay1 + ay2) / 2 + rp_uy * 14
        draw.text((mx + 10, my), f"{width:g} mm", fill='#333333', font=font, anchor='lm')


def draw_callouts(draw, corners, edgebands):
    f_tl, f_tr, f_bl = corners['f_tl'], corners['f_tr'], corners['f_bl']
    b_tl, b_tr = corners['b_tl'], corners['b_tr']
    eb_font = get_font(11, bold=True)
    cc = '#333333'
    edge_defs = {
        'boven': (b_tl, b_tr), 'onder': (f_tl, f_tr),
        'links': (f_tl, b_tl), 'rechts': (f_tr, b_tr),
    }
    callout_pos = {
        'boven':  {'lx': (b_tl[0] + b_tr[0]) / 2, 'ly': b_tl[1] - 55, 'anchor': 'ms'},
        'onder':  {'lx': f_bl[0] - 30, 'ly': f_bl[1] + 55, 'anchor': 'rm'},
        'links':  {'lx': f_tl[0] - 70, 'ly': (f_tl[1] + b_tl[1]) / 2 - 25, 'anchor': 'rm'},
        'rechts': {'lx': b_tr[0] + 70, 'ly': (f_tr[1] + b_tr[1]) / 2, 'anchor': 'lm'},
    }
    for side, label_text in edgebands.items():
        if side not in edge_defs:
            continue
        p1, p2 = edge_defs[side]
        mid_x, mid_y = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
        cp = callout_pos[side]
        lx, ly = cp['lx'], cp['ly']
        draw.text((lx, ly), label_text, fill=cc, font=eb_font, anchor=cp['anchor'])
        bbox = draw.textbbox((lx, ly), label_text, font=eb_font, anchor=cp['anchor'])
        if side == 'boven':
            ast = ((bbox[0]+bbox[2])/2, bbox[3]+2)
        elif side == 'onder':
            ast = (bbox[2]+4, (bbox[1]+bbox[3])/2)
        elif side == 'links':
            ast = (bbox[2]+4, (bbox[1]+bbox[3])/2)
        else:
            ast = (bbox[0]-4, (bbox[1]+bbox[3])/2)
        draw.line([ast, (mid_x, mid_y)], fill=cc, width=1)
        draw_arrowhead(draw, mid_x, mid_y, ast[0], ast[1], cc, 8)


title_font = get_font(16, bold=True)
ox, oy = 220, 370
dl, dw, dh = 260, 100, 65

# All eik
img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)
d.rectangle([(0, 0), (W, 40)], fill='#333333')
d.text((W/2, 20), 'V5: Top + side edgeband strips — All eik', fill='white', font=title_font, anchor='mm')
eb = {'boven': 'Fineer eik 1mm', 'onder': 'Fineer eik 1mm', 'links': 'Fineer eik 1mm', 'rechts': 'Fineer eik 1mm'}
c = draw_iso_box_with_edgebands(d, ox, oy, dl, dw, dh, eb)
draw_dim_arrows(d, c, 1922, 441, 19, dl, dw, dh)
draw_callouts(d, c, eb)
img.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_v5_eik.png')
print("Saved v5_eik")

# Mixed
img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)
d.rectangle([(0, 0), (W, 40)], fill='#333333')
d.text((W/2, 20), 'V5: Mixed — eik boven/onder, wit links, zwart rechts', fill='white', font=title_font, anchor='mm')
eb = {'boven': 'Fineer eik 1mm', 'onder': 'Fineer eik 1mm', 'links': 'ABS wit 1mm', 'rechts': 'ABS zwart 2mm'}
c = draw_iso_box_with_edgebands(d, ox, oy, dl, dw, dh, eb)
draw_dim_arrows(d, c, 1922, 441, 19, dl, dw, dh)
draw_callouts(d, c, eb)
img.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_v5_mixed.png')
print("Saved v5_mixed")

# Partial (boven + onder only)
img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)
d.rectangle([(0, 0), (W, 40)], fill='#333333')
d.text((W/2, 20), 'V5: Partial — eik boven + onder only', fill='white', font=title_font, anchor='mm')
eb = {'boven': 'Fineer eik 1mm', 'onder': 'Fineer eik 1mm'}
c = draw_iso_box_with_edgebands(d, ox, oy, dl, dw, dh, eb)
draw_dim_arrows(d, c, 1922, 441, 19, dl, dw, dh)
draw_callouts(d, c, eb)
img.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_v5_partial.png')
print("Saved v5_partial")

# Noot
img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)
d.rectangle([(0, 0), (W, 40)], fill='#333333')
d.text((W/2, 20), 'V5: All noot', fill='white', font=title_font, anchor='mm')
eb = {'boven': 'Fineer noot 1mm', 'onder': 'Fineer noot 1mm', 'links': 'Fineer noot 1mm', 'rechts': 'Fineer noot 1mm'}
c = draw_iso_box_with_edgebands(d, ox, oy, dl, dw, dh, eb)
draw_dim_arrows(d, c, 1922, 441, 19, dl, dw, dh)
draw_callouts(d, c, eb)
img.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_v5_noot.png')
print("Saved v5_noot")

# No edgebands
img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)
d.rectangle([(0, 0), (W, 40)], fill='#333333')
d.text((W/2, 20), 'V5: No edgebands (standard)', fill='white', font=title_font, anchor='mm')
c = draw_iso_box_with_edgebands(d, ox, oy, dl, dw, dh, {})
draw_dim_arrows(d, c, 1922, 441, 19, dl, dw, dh)
img.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_v5_none.png')
print("Saved v5_none")

print("\nDone!")
