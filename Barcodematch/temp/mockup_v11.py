"""Mockup v11: Dotted leader lines — engineering drawing style callouts."""
from PIL import Image, ImageDraw, ImageFont
import math
import random

BG = '#f5f5f5'
W, H = 900, 650

EDGEBAND_STYLES = {
    'eik': {'fill': '#c9a96e', 'fill_side': '#b8955c', 'edge': '#c9a96e',
            'grain': True, 'grain_color': '#b08840', 'grain_color_side': '#a07a35'},
    'noot': {'fill': '#7a5c3a', 'fill_side': '#6b4e30', 'edge': '#7a5c3a',
             'grain': True, 'grain_color': '#5e3f28', 'grain_color_side': '#503520'},
    'wit': {'fill': '#f0f0f0', 'fill_side': '#e0e0e0', 'edge': '#e8e8e8',
            'grain': False},
    'zwart': {'fill': '#2a2a2a', 'fill_side': '#1e1e1e', 'edge': '#2a2a2a',
              'grain': False},
}

def get_eb_style(t):
    for kw, s in EDGEBAND_STYLES.items():
        if kw in t.lower(): return kw, s
    return 'eik', EDGEBAND_STYLES['eik']

def get_font(size, bold=False):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()

def draw_wavy_grain(draw, corners, grain_color, seed=42):
    rng = random.Random(seed)
    tl,tr,br,bl = corners
    for i in range(rng.randint(4,7)):
        t=(i+1)/(rng.randint(4,7)+1)
        sx=bl[0]+t*(tl[0]-bl[0]);sy=bl[1]+t*(tl[1]-bl[1])
        ex=br[0]+t*(tr[0]-br[0]);ey=br[1]+t*(tr[1]-br[1])
        pdx,pdy=tl[0]-bl[0],tl[1]-bl[1];pl=math.sqrt(pdx**2+pdy**2)or 1
        amp=pl*0.04;freq=1.5+(i%3)*0.7;phase=i*2.3
        pts=[]
        for p in range(21):
            f=p/20;bx=sx+f*(ex-sx);by=sy+f*(ey-sy)
            w=math.sin(f*math.pi*freq+phase)*amp
            pts.append((bx+w*(pdx/pl),by+w*(pdy/pl)))
        for j in range(len(pts)-1):
            draw.line([pts[j],pts[j+1]],fill=grain_color,width=1)

def draw_dotted_line(draw, p1, p2, color='#555555', width=1, dash_len=4, gap_len=3):
    """Draw a dotted/dashed line between two points."""
    dx, dy = p2[0]-p1[0], p2[1]-p1[1]
    length = math.sqrt(dx**2 + dy**2)
    if length < 1:
        return
    ux, uy = dx/length, dy/length
    pos = 0
    while pos < length:
        end = min(pos + dash_len, length)
        draw.line([
            (p1[0]+ux*pos, p1[1]+uy*pos),
            (p1[0]+ux*end, p1[1]+uy*end)
        ], fill=color, width=width)
        pos = end + gap_len

def draw_iso_box(draw, ox, oy, dl, dw, dh, edgebands):
    iso_x,iso_y = dw*0.5, dw*0.3
    f_bl=(ox,oy);f_br=(ox+dl,oy);f_tr=(ox+dl,oy-dh);f_tl=(ox,oy-dh)
    b_bl=(ox+iso_x,oy-iso_y);b_br=(ox+dl+iso_x,oy-iso_y)
    b_tr=(ox+dl+iso_x,oy-dh-iso_y);b_tl=(ox+iso_x,oy-dh-iso_y)
    oc='#555555'

    onder_kw, onder_s = get_eb_style(edgebands['onder']) if 'onder' in edgebands else (None, None)
    rechts_kw, rechts_s = get_eb_style(edgebands['rechts']) if 'rechts' in edgebands else (None, None)

    # Back edges dashed
    for s,e in [(b_bl,b_br),(b_bl,b_tl)]:
        dx,dy=e[0]-s[0],e[1]-s[1];l=math.sqrt(dx**2+dy**2)
        if l<1: continue
        segs=int(l/8)
        for i in range(0,segs,2):
            t1,t2=i/segs,min((i+1)/segs,1)
            draw.line([(s[0]+dx*t1,s[1]+dy*t1),(s[0]+dx*t2,s[1]+dy*t2)],fill='#aaa',width=2)

    # Top face
    draw.polygon([f_tl,f_tr,b_tr,b_tl], fill='#e0e0e0', outline=oc, width=2)

    # Colored edge lines on top face
    edge_map = {'boven':(b_tl,b_tr),'onder':(f_tl,f_tr),'links':(f_tl,b_tl),'rechts':(f_tr,b_tr)}
    for side, txt in edgebands.items():
        if side in edge_map:
            kw, s = get_eb_style(txt)
            p1, p2 = edge_map[side]
            draw.line([p1, p2], fill=s['edge'], width=5)

    # Redraw top face outline
    draw.polygon([f_tl,f_tr,b_tr,b_tl], fill=None, outline=oc, width=2)

    # Right face
    if rechts_s:
        draw.polygon([f_br,b_br,b_tr,f_tr], fill=rechts_s['fill_side'], outline=oc, width=2)
        if rechts_s['grain']:
            draw_wavy_grain(draw,[f_tr,b_tr,b_br,f_br],rechts_s.get('grain_color_side',rechts_s['grain_color']),seed=99)
        draw.polygon([f_br,b_br,b_tr,f_tr], fill=None, outline=oc, width=2)
    else:
        draw.polygon([f_br,b_br,b_tr,f_tr], fill='#d0d0d0', outline=oc, width=2)

    # Front face
    if onder_s:
        draw.polygon([f_bl,f_br,f_tr,f_tl], fill=onder_s['fill'], outline=oc, width=2)
        if onder_s['grain']:
            draw_wavy_grain(draw,[f_tl,f_tr,f_br,f_bl],onder_s['grain_color'],seed=42)
        draw.polygon([f_bl,f_br,f_tr,f_tl], fill=None, outline=oc, width=2)
    else:
        draw.polygon([f_bl,f_br,f_tr,f_tl], fill='#eeeeee', outline=oc, width=2)

    return {'f_bl':f_bl,'f_br':f_br,'f_tr':f_tr,'f_tl':f_tl,
            'b_bl':b_bl,'b_br':b_br,'b_tr':b_tr,'b_tl':b_tl}

def draw_dim_arrows(draw, c, length, width, height, dl, dw, dh):
    ox,oy=c['f_bl'];font=get_font(12,True);ac='#555555';gap=14
    if length>0:
        ay=oy+gap;draw.line([(ox,ay),(ox+dl,ay)],fill=ac,width=2)
        draw.text(((2*ox+dl)/2,ay+6),f"{length:g} mm",fill='#333',font=font,anchor='mt')
    if height>0:
        ax=ox-gap;draw.line([(ax,oy),(ax,oy-dh)],fill=ac,width=2)
        draw.text((ax-4,oy-dh/2),f"{height:g}",fill='#333',font=font,anchor='rm')
    if width>0:
        fb,bb=c['f_br'],c['b_br'];dx,dy=bb[0]-fb[0],bb[1]-fb[1]
        rl=math.sqrt(dx**2+dy**2)or 1;ru,rv=-dy/rl,dx/rl
        draw.line([(fb[0]+ru*gap,fb[1]+rv*gap),(bb[0]+ru*gap,bb[1]+rv*gap)],fill=ac,width=2)
        mx=(fb[0]+bb[0])/2+ru*(gap+14);my=(fb[1]+bb[1])/2+rv*(gap+14)
        draw.text((mx+10,my),f"{width:g} mm",fill='#333',font=font,anchor='lm')

def draw_edge_callouts(draw, c, edgebands, dl):
    """Dotted leader lines with underlined edge type text."""
    cc = '#555555'
    ef = get_font(10, bold=True)
    diag = 30  # length of 45-degree diagonal segment

    # BOVEN: from midpoint of back top edge, 45deg up-right, then horizontal with text
    if 'boven' in edgebands:
        btl, btr = c['b_tl'], c['b_tr']
        mx, my = (btl[0]+btr[0])/2, (btl[1]+btr[1])/2
        # Small dot at startpoint
        r = 3
        draw.ellipse([(mx-r, my-r), (mx+r, my+r)], fill=cc)
        # 45 degrees up-right
        p2 = (mx + diag*0.707, my - diag*0.707)
        # Then horizontal to the right
        txt = edgebands['boven']
        bbox = draw.textbbox((0,0), txt, font=ef)
        tw = bbox[2] - bbox[0]
        p3 = (p2[0] + tw + 8, p2[1])
        # Draw dotted leader
        draw_dotted_line(draw, (mx, my), p2, color=cc, width=1)
        draw_dotted_line(draw, p2, p3, color=cc, width=1)
        # Text on the horizontal segment
        draw.text((p2[0]+4, p2[1]-12), txt, fill='#333', font=ef, anchor='ls')
        # Dotted underline
        draw_dotted_line(draw, (p2[0], p2[1]), (p2[0]+tw+8, p2[1]), color=cc, width=1)

    # LINKS: from midpoint of left top edge (like boven), straight left
    if 'links' in edgebands:
        ftl, btl = c['f_tl'], c['b_tl']
        sx = (ftl[0]+btl[0])/2
        sy = (ftl[1]+btl[1])/2
        # Small dot at startpoint
        r = 3
        draw.ellipse([(sx-r, sy-r), (sx+r, sy+r)], fill=cc)
        txt = edgebands['links']
        bbox = draw.textbbox((0,0), txt, font=ef)
        tw = bbox[2] - bbox[0]
        p2 = (sx - 50, sy)
        p3 = (p2[0] - tw - 8, p2[1])
        # Draw dotted leader going left
        draw_dotted_line(draw, (sx, sy), p2, color=cc, width=1)
        # Text to the left
        draw.text((p2[0]-4, p2[1]-12), txt, fill='#333', font=ef, anchor='rs')
        # Dotted underline under text
        draw_dotted_line(draw, (p3[0], p2[1]), (p2[0], p2[1]), color=cc, width=1)

    # RECHTS: center of right side plane, same height as bottom startpoint
    if 'rechts' in edgebands:
        ftr, fbr, btr, bbr = c['f_tr'], c['f_br'], c['b_tr'], c['b_br']
        # Center of right face polygon
        sx = (ftr[0]+fbr[0]+btr[0]+bbr[0])/4
        sy = (ftr[1]+fbr[1]+btr[1]+bbr[1])/4
        txt = edgebands['rechts']
        p2 = (sx + 50, sy)
        # Small dot at startpoint
        r = 3
        draw.ellipse([(sx-r, sy-r), (sx+r, sy+r)], fill=cc)
        # Draw dotted leader going right
        draw_dotted_line(draw, (sx, sy), p2, color=cc, width=1)
        # Text to the right
        draw.text((p2[0]+4, p2[1]-12), txt, fill='#333', font=ef, anchor='ls')
        bbox = draw.textbbox((0,0), txt, font=ef)
        tw = bbox[2] - bbox[0]
        # Dotted underline
        draw_dotted_line(draw, (p2[0], p2[1]), (p2[0]+tw+8, p2[1]), color=cc, width=1)

    # ONDER: start at 2/3 of workpiece length on front bottom edge,
    # 45deg down-right, then horizontal with text
    if 'onder' in edgebands:
        fbl, fbr, ftl, ftr = c['f_bl'], c['f_br'], c['f_tl'], c['f_tr']
        # Center height of front face
        mid_y = (ftl[1] + fbl[1]) / 2
        # Center length of front face
        sx = (fbl[0] + fbr[0]) / 2
        sy = mid_y
        # Small dot at startpoint
        r = 3
        draw.ellipse([(sx-r, sy-r), (sx+r, sy+r)], fill=cc)
        # 45 degrees down-right, pushed well below sizing
        diag_onder = 120
        p2 = (sx + diag_onder*0.707, sy + diag_onder*0.707)
        txt = edgebands['onder']
        bbox = draw.textbbox((0,0), txt, font=ef)
        tw = bbox[2] - bbox[0]
        p3 = (p2[0] + tw + 8, p2[1])
        # Draw dotted leader
        draw_dotted_line(draw, (sx, sy), p2, color=cc, width=1)
        # Text on the horizontal segment
        draw.text((p2[0]+4, p2[1]-12), txt, fill='#333', font=ef, anchor='ls')
        # Dotted underline
        draw_dotted_line(draw, (p2[0], p2[1]), (p3[0], p3[1]), color=cc, width=1)

tf = get_font(16, True)
ox,oy,dl,dw,dh = 200,370,260,100,65

for name,title,eb in [
    ('v11_eik','All eik',{'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm','links':'Fineer eik 1mm','rechts':'Fineer eik 1mm'}),
    ('v11_mixed','Mixed',{'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm','links':'ABS wit 1mm','rechts':'ABS zwart 2mm'}),
    ('v11_partial','Partial: boven + onder',{'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm'}),
    ('v11_none','No edgebands',{}),
]:
    img=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(img)
    d.rectangle([(0,0),(W,40)],fill='#333')
    d.text((W/2,20),f'V11: {title}',fill='white',font=tf,anchor='mm')
    c=draw_iso_box(d,ox,oy,dl,dw,dh,eb)
    draw_dim_arrows(d,c,1922,441,19,dl,dw,dh)
    if eb: draw_edge_callouts(d,c,eb,dl)
    img.save(f'/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_{name}.png')
    print(f"Saved {name}")

print("\nDone!")
