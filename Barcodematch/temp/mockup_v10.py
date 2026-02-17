"""Mockup v10: Edge text ON the colored faces and edges."""
from PIL import Image, ImageDraw, ImageFont
import math
import random

BG = '#f5f5f5'
W, H = 900, 650

EDGEBAND_STYLES = {
    'eik': {'fill': '#c9a96e', 'fill_side': '#b8955c', 'edge': '#c9a96e',
            'text_color': '#5a3d1a', 'text_color_side': '#4a3015',
            'grain': True, 'grain_color': '#b08840', 'grain_color_side': '#a07a35'},
    'noot': {'fill': '#7a5c3a', 'fill_side': '#6b4e30', 'edge': '#7a5c3a',
             'text_color': '#ffffff', 'text_color_side': '#e0e0e0',
             'grain': True, 'grain_color': '#5e3f28', 'grain_color_side': '#503520'},
    'wit': {'fill': '#f0f0f0', 'fill_side': '#e0e0e0', 'edge': '#e8e8e8',
            'text_color': '#555555', 'text_color_side': '#444444',
            'grain': False},
    'zwart': {'fill': '#2a2a2a', 'fill_side': '#1e1e1e', 'edge': '#2a2a2a',
              'text_color': '#cccccc', 'text_color_side': '#bbbbbb',
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

    # Text on top face edges (boven/links)
    edge_font = get_font(9, bold=True)
    if 'boven' in edgebands:
        kw, s = get_eb_style(edgebands['boven'])
        mx = (b_tl[0]+b_tr[0])/2; my = (b_tl[1]+b_tr[1])/2
        draw.text((mx, my-10), edgebands['boven'], fill='#333333', font=edge_font, anchor='ms')

    if 'links' in edgebands:
        kw, s = get_eb_style(edgebands['links'])
        mx = (f_tl[0]+b_tl[0])/2; my = (f_tl[1]+b_tl[1])/2
        # Calculate angle for text along the edge
        dx = b_tl[0]-f_tl[0]; dy = b_tl[1]-f_tl[1]
        # Place text offset to the left of the edge
        draw.text((mx-12, my), edgebands['links'], fill='#333333', font=edge_font, anchor='rm')

    # Right face
    if rechts_s:
        draw.polygon([f_br,b_br,b_tr,f_tr], fill=rechts_s['fill_side'], outline=oc, width=2)
        if rechts_s['grain']:
            draw_wavy_grain(draw,[f_tr,b_tr,b_br,f_br],rechts_s.get('grain_color_side',rechts_s['grain_color']),seed=99)
        draw.polygon([f_br,b_br,b_tr,f_tr], fill=None, outline=oc, width=2)
        # Text centered on right face
        rcx = (f_br[0]+b_br[0]+b_tr[0]+f_tr[0])/4
        rcy = (f_br[1]+b_br[1]+b_tr[1]+f_tr[1])/4
        draw.text((rcx, rcy), edgebands['rechts'], fill=rechts_s['text_color_side'],
                  font=edge_font, anchor='mm')
    else:
        draw.polygon([f_br,b_br,b_tr,f_tr], fill='#d0d0d0', outline=oc, width=2)

    # Front face
    if onder_s:
        draw.polygon([f_bl,f_br,f_tr,f_tl], fill=onder_s['fill'], outline=oc, width=2)
        if onder_s['grain']:
            draw_wavy_grain(draw,[f_tl,f_tr,f_br,f_bl],onder_s['grain_color'],seed=42)
        draw.polygon([f_bl,f_br,f_tr,f_tl], fill=None, outline=oc, width=2)
        # Text centered on front face
        fcx = (f_bl[0]+f_br[0]+f_tr[0]+f_tl[0])/4
        fcy = (f_bl[1]+f_br[1]+f_tr[1]+f_tl[1])/4
        draw.text((fcx, fcy), edgebands['onder'], fill=onder_s['text_color'],
                  font=edge_font, anchor='mm')
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

tf = get_font(16, True)
ox,oy,dl,dw,dh = 200,370,260,100,65

for name,title,eb in [
    ('v10_eik','All eik',{'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm','links':'Fineer eik 1mm','rechts':'Fineer eik 1mm'}),
    ('v10_mixed','Mixed',{'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm','links':'ABS wit 1mm','rechts':'ABS zwart 2mm'}),
    ('v10_partial','Partial: boven + onder',{'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm'}),
    ('v10_none','No edgebands',{}),
]:
    img=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(img)
    d.rectangle([(0,0),(W,40)],fill='#333')
    d.text((W/2,20),f'V10: {title}',fill='white',font=tf,anchor='mm')
    c=draw_iso_box(d,ox,oy,dl,dw,dh,eb)
    draw_dim_arrows(d,c,1922,441,19,dl,dw,dh)
    img.save(f'/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_{name}.png')
    print(f"Saved {name}")

print("\nDone!")
