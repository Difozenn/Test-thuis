"""Mockup v6: Solid color faces, no edge strips. Horizontal grain on right panel."""
from PIL import Image, ImageDraw, ImageFont
import math
import random

BG = '#f5f5f5'
W, H = 900, 700

EDGEBAND_STYLES = {
    'eik': {'fill': '#c9a96e', 'fill_side': '#b8955c', 'fill_top': '#c4a468',
            'grain': True, 'grain_color': '#b08840', 'grain_color_side': '#a07a35', 'grain_color_top': '#b59550'},
    'noot': {'fill': '#7a5c3a', 'fill_side': '#6b4e30', 'fill_top': '#725838',
             'grain': True, 'grain_color': '#5e3f28', 'grain_color_side': '#503520', 'grain_color_top': '#5a3d26'},
    'wit': {'fill': '#f0f0f0', 'fill_side': '#e0e0e0', 'fill_top': '#ebebeb', 'grain': False},
    'zwart': {'fill': '#2a2a2a', 'fill_side': '#1e1e1e', 'fill_top': '#252525', 'grain': False},
}
DEFAULT_STYLE = EDGEBAND_STYLES['eik']


def get_eb_style(label_text):
    for kw, style in EDGEBAND_STYLES.items():
        if kw in label_text.lower():
            return style
    return DEFAULT_STYLE


def get_font(size, bold=False):
    try:
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()


def draw_arrowhead(draw, tx, ty, fx, fy, color='#000000', size=8):
    dx, dy = tx - fx, ty - fy
    l = math.sqrt(dx**2 + dy**2) or 1
    ux, uy = dx/l, dy/l
    px, py = -uy, ux
    bx, by = tx - ux*size, ty - uy*size
    draw.polygon([(tx, ty), (bx+px*size*0.4, by+py*size*0.4), (bx-px*size*0.4, by-py*size*0.4)], fill=color)


def lerp(p1, p2, t):
    return (p1[0] + t*(p2[0]-p1[0]), p1[1] + t*(p2[1]-p1[1]))


def draw_wavy_grain(draw, corners, grain_color, direction='horizontal', seed=42):
    rng = random.Random(seed)
    tl, tr, br, bl = corners

    if direction == 'horizontal':
        num_lines = rng.randint(4, 7)
        num_points = 20
        for i in range(num_lines):
            t = (i+1) / (num_lines+1)
            sx = bl[0] + t*(tl[0]-bl[0]); sy = bl[1] + t*(tl[1]-bl[1])
            ex = br[0] + t*(tr[0]-br[0]); ey = br[1] + t*(tr[1]-br[1])
            pdx, pdy = tl[0]-bl[0], tl[1]-bl[1]
            pl = math.sqrt(pdx**2+pdy**2) or 1
            amp = pl * 0.04; freq = 1.5+(i%3)*0.7; phase = i*2.3
            pts = []
            for p in range(num_points+1):
                f = p/num_points
                bx = sx+f*(ex-sx); by = sy+f*(ey-sy)
                w = math.sin(f*math.pi*freq+phase)*amp
                pts.append((bx+w*(pdx/pl), by+w*(pdy/pl)))
            for j in range(len(pts)-1):
                draw.line([pts[j], pts[j+1]], fill=grain_color, width=1)
    elif direction == 'iso_lengte':
        num_lines = rng.randint(2, 4)
        num_points = 15
        for i in range(num_lines):
            t = (i+1) / (num_lines+1)
            sx = tl[0]+t*(bl[0]-tl[0]); sy = tl[1]+t*(bl[1]-tl[1])
            ex = tr[0]+t*(br[0]-tr[0]); ey = tr[1]+t*(br[1]-tr[1])
            pdx, pdy = bl[0]-tl[0], bl[1]-tl[1]
            pl = math.sqrt(pdx**2+pdy**2) or 1
            amp = pl*0.06; freq = 1.3+(i%3)*0.5; phase = i*2.1
            pts = []
            for p in range(num_points+1):
                f = p/num_points
                bx = sx+f*(ex-sx); by = sy+f*(ey-sy)
                w = math.sin(f*math.pi*freq+phase)*amp
                pts.append((bx+w*(pdx/pl), by+w*(pdy/pl)))
            for j in range(len(pts)-1):
                draw.line([pts[j], pts[j+1]], fill=grain_color, width=1)
    elif direction == 'iso_breedte':
        num_lines = rng.randint(2, 4)
        num_points = 12
        for i in range(num_lines):
            t = (i+1) / (num_lines+1)
            sx = tl[0]+t*(tr[0]-tl[0]); sy = tl[1]+t*(tr[1]-tl[1])
            ex = bl[0]+t*(br[0]-bl[0]); ey = bl[1]+t*(br[1]-bl[1])
            pdx, pdy = tr[0]-tl[0], tr[1]-tl[1]
            pl = math.sqrt(pdx**2+pdy**2) or 1
            amp = pl*0.06; freq = 1.2+(i%2)*0.6; phase = i*1.9
            pts = []
            for p in range(num_points+1):
                f = p/num_points
                bx = sx+f*(ex-sx); by = sy+f*(ey-sy)
                w = math.sin(f*math.pi*freq+phase)*amp
                pts.append((bx+w*(pdx/pl), by+w*(pdy/pl)))
            for j in range(len(pts)-1):
                draw.line([pts[j], pts[j+1]], fill=grain_color, width=1)


def draw_iso_box(draw, ox, oy, dl, dw, dh, edgebands):
    iso_x, iso_y = dw*0.5, dw*0.3
    f_bl = (ox, oy); f_br = (ox+dl, oy); f_tr = (ox+dl, oy-dh); f_tl = (ox, oy-dh)
    b_bl = (ox+iso_x, oy-iso_y); b_br = (ox+dl+iso_x, oy-iso_y)
    b_tr = (ox+dl+iso_x, oy-dh-iso_y); b_tl = (ox+iso_x, oy-dh-iso_y)

    oc = '#555555'
    top_strip_frac = 0.12

    # Back edges dashed
    for s, e in [(b_bl, b_br), (b_bl, b_tl)]:
        dx, dy = e[0]-s[0], e[1]-s[1]
        l = math.sqrt(dx**2+dy**2)
        if l < 1: continue
        segs = int(l/8)
        for i in range(0, segs, 2):
            t1, t2 = i/segs, min((i+1)/segs, 1)
            draw.line([(s[0]+dx*t1,s[1]+dy*t1),(s[0]+dx*t2,s[1]+dy*t2)], fill='#aaa', width=2)

    # Get styles
    onder_s = get_eb_style(edgebands['onder']) if 'onder' in edgebands else None
    rechts_s = get_eb_style(edgebands['rechts']) if 'rechts' in edgebands else None
    boven_s = get_eb_style(edgebands['boven']) if 'boven' in edgebands else None
    links_s = get_eb_style(edgebands['links']) if 'links' in edgebands else None

    # === TOP FACE (base) ===
    draw.polygon([f_tl, f_tr, b_tr, b_tl], fill='#e0e0e0', outline=oc, width=2)

    # Top face edge strips
    if boven_s:
        s = [b_tl, b_tr, lerp(b_tr, f_tr, top_strip_frac), lerp(b_tl, f_tl, top_strip_frac)]
        draw.polygon(s, fill=boven_s['fill_top'])
        if boven_s['grain']:
            draw_wavy_grain(draw, s, boven_s.get('grain_color_top', boven_s['grain_color']), 'iso_lengte', seed=10)
    if onder_s:
        s = [lerp(f_tl, b_tl, top_strip_frac), lerp(f_tr, b_tr, top_strip_frac), f_tr, f_tl]
        draw.polygon(s, fill=onder_s['fill_top'])
        if onder_s['grain']:
            draw_wavy_grain(draw, s, onder_s.get('grain_color_top', onder_s['grain_color']), 'iso_lengte', seed=20)
    if links_s:
        s = [b_tl, lerp(b_tl, b_tr, top_strip_frac), lerp(f_tl, f_tr, top_strip_frac), f_tl]
        draw.polygon(s, fill=links_s['fill_top'])
        if links_s['grain']:
            draw_wavy_grain(draw, s, links_s.get('grain_color_top', links_s['grain_color']), 'iso_breedte', seed=30)
    if rechts_s:
        s = [lerp(b_tr, b_tl, top_strip_frac), b_tr, f_tr, lerp(f_tr, f_tl, top_strip_frac)]
        draw.polygon(s, fill=rechts_s['fill_top'])
        if rechts_s['grain']:
            draw_wavy_grain(draw, s, rechts_s.get('grain_color_top', rechts_s['grain_color']), 'iso_breedte', seed=40)

    draw.polygon([f_tl, f_tr, b_tr, b_tl], fill=None, outline=oc, width=2)

    # === RIGHT FACE — solid color, horizontal grain ===
    if rechts_s:
        draw.polygon([f_br, b_br, b_tr, f_tr], fill=rechts_s['fill_side'], outline=oc, width=2)
        if rechts_s['grain']:
            draw_wavy_grain(draw, [f_tr, b_tr, b_br, f_br],
                           rechts_s.get('grain_color_side', rechts_s['grain_color']),
                           'horizontal', seed=99)
        draw.polygon([f_br, b_br, b_tr, f_tr], fill=None, outline=oc, width=2)
    else:
        draw.polygon([f_br, b_br, b_tr, f_tr], fill='#d0d0d0', outline=oc, width=2)

    # === FRONT FACE — solid color based on "onder" edge ===
    if onder_s:
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=onder_s['fill'], outline=oc, width=2)
        if onder_s['grain']:
            draw_wavy_grain(draw, [f_tl, f_tr, f_br, f_bl],
                           onder_s['grain_color'], 'horizontal', seed=42)
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill=None, outline=oc, width=2)
    else:
        draw.polygon([f_bl, f_br, f_tr, f_tl], fill='#eeeeee', outline=oc, width=2)

    # Bold edges on top face
    edge_lines = {'boven': (b_tl, b_tr), 'onder': (f_tl, f_tr), 'links': (f_tl, b_tl), 'rechts': (f_tr, b_tr)}
    for side in edgebands:
        if side in edge_lines:
            p1, p2 = edge_lines[side]
            draw.line([p1, p2], fill='#000000', width=3)

    return {'f_bl':f_bl,'f_br':f_br,'f_tr':f_tr,'f_tl':f_tl,'b_bl':b_bl,'b_br':b_br,'b_tr':b_tr,'b_tl':b_tl}


def draw_dim_arrows(draw, c, length, width, height, dl, dw, dh):
    ox, oy = c['f_bl']
    font = get_font(12, True)
    ac = '#555555'; gap = 14
    if length > 0:
        ay = oy+gap
        draw.line([(ox,ay),(ox+dl,ay)], fill=ac, width=2)
        draw.text(((2*ox+dl)/2, ay+6), f"{length:g} mm", fill='#333', font=font, anchor='mt')
    if height > 0:
        ax = ox-gap
        draw.line([(ax,oy),(ax,oy-dh)], fill=ac, width=2)
        draw.text((ax-4, oy-dh/2), f"{height:g}", fill='#333', font=font, anchor='rm')
    if width > 0:
        fb, bb = c['f_br'], c['b_br']
        dx, dy = bb[0]-fb[0], bb[1]-fb[1]
        rl = math.sqrt(dx**2+dy**2) or 1
        ru, rv = -dy/rl, dx/rl
        draw.line([(fb[0]+ru*gap,fb[1]+rv*gap),(bb[0]+ru*gap,bb[1]+rv*gap)], fill=ac, width=2)
        mx = (fb[0]+bb[0])/2+ru*(gap+14); my = (fb[1]+bb[1])/2+rv*(gap+14)
        draw.text((mx+10, my), f"{width:g} mm", fill='#333', font=font, anchor='lm')


def draw_callouts(draw, c, edgebands):
    ft, ftr, fbl, btl, btr = c['f_tl'], c['f_tr'], c['f_bl'], c['b_tl'], c['b_tr']
    ef = get_font(11, True); cc = '#333'
    ed = {'boven':(btl,btr),'onder':(ft,ftr),'links':(ft,btl),'rechts':(ftr,btr)}
    cp = {
        'boven': {'lx':(btl[0]+btr[0])/2,'ly':btl[1]-55,'a':'ms'},
        'onder': {'lx':fbl[0]-30,'ly':fbl[1]+55,'a':'rm'},
        'links': {'lx':ft[0]-70,'ly':(ft[1]+btl[1])/2-25,'a':'rm'},
        'rechts':{'lx':btr[0]+70,'ly':(ftr[1]+btr[1])/2,'a':'lm'},
    }
    for side, txt in edgebands.items():
        if side not in ed: continue
        p1,p2 = ed[side]; mx,my = (p1[0]+p2[0])/2,(p1[1]+p2[1])/2
        c2 = cp[side]; lx,ly = c2['lx'],c2['ly']
        draw.text((lx,ly), txt, fill=cc, font=ef, anchor=c2['a'])
        bb = draw.textbbox((lx,ly), txt, font=ef, anchor=c2['a'])
        if side=='boven': ast=((bb[0]+bb[2])/2,bb[3]+2)
        elif side=='onder': ast=(bb[2]+4,(bb[1]+bb[3])/2)
        elif side=='links': ast=(bb[2]+4,(bb[1]+bb[3])/2)
        else: ast=(bb[0]-4,(bb[1]+bb[3])/2)
        draw.line([ast,(mx,my)], fill=cc, width=1)
        draw_arrowhead(draw, mx, my, ast[0], ast[1], cc, 8)


tf = get_font(16, True)
ox, oy, dl, dw, dh = 220, 370, 260, 100, 65

for name, title, eb in [
    ('v6_eik', 'All eik', {'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm','links':'Fineer eik 1mm','rechts':'Fineer eik 1mm'}),
    ('v6_noot', 'All noot', {'boven':'Fineer noot 1mm','onder':'Fineer noot 1mm','links':'Fineer noot 1mm','rechts':'Fineer noot 1mm'}),
    ('v6_mixed', 'Mixed: eik boven/onder, wit links, zwart rechts', {'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm','links':'ABS wit 1mm','rechts':'ABS zwart 2mm'}),
    ('v6_partial', 'Partial: eik boven + onder', {'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm'}),
    ('v6_none', 'No edgebands', {}),
]:
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([(0,0),(W,40)], fill='#333')
    d.text((W/2,20), f'V6: {title}', fill='white', font=tf, anchor='mm')
    c = draw_iso_box(d, ox, oy, dl, dw, dh, eb)
    draw_dim_arrows(d, c, 1922, 441, 19, dl, dw, dh)
    if eb:
        draw_callouts(d, c, eb)
    img.save(f'/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_{name}.png')
    print(f"Saved {name}")

print("\nDone!")
