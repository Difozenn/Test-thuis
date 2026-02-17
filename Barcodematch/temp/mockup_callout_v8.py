"""Mockup v8: Single inner line on top face for edgeband edges."""
from PIL import Image, ImageDraw, ImageFont
import math
import random

BG = '#f5f5f5'
W, H = 900, 700

EDGEBAND_STYLES = {
    'eik': {'fill': '#c9a96e', 'fill_side': '#b8955c', 'grain': True, 'grain_color': '#b08840', 'grain_color_side': '#a07a35'},
    'noot': {'fill': '#7a5c3a', 'fill_side': '#6b4e30', 'grain': True, 'grain_color': '#5e3f28', 'grain_color_side': '#503520'},
    'wit': {'fill': '#f0f0f0', 'fill_side': '#e0e0e0', 'grain': False},
    'zwart': {'fill': '#2a2a2a', 'fill_side': '#1e1e1e', 'grain': False},
}
DEFAULT_STYLE = EDGEBAND_STYLES['eik']


def get_eb_style(t):
    for kw, s in EDGEBAND_STYLES.items():
        if kw in t.lower(): return s
    return DEFAULT_STYLE


def get_font(size, bold=False):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()


def draw_arrowhead(draw, tx, ty, fx, fy, color='#000000', size=8):
    dx,dy = tx-fx, ty-fy; l=math.sqrt(dx**2+dy**2)or 1
    ux,uy = dx/l,dy/l; px,py = -uy,ux
    bx,by = tx-ux*size, ty-uy*size
    draw.polygon([(tx,ty),(bx+px*size*0.4,by+py*size*0.4),(bx-px*size*0.4,by-py*size*0.4)], fill=color)


def lerp(p1,p2,t):
    return (p1[0]+t*(p2[0]-p1[0]), p1[1]+t*(p2[1]-p1[1]))


def draw_wavy_grain(draw, corners, grain_color, seed=42):
    rng = random.Random(seed)
    tl,tr,br,bl = corners
    for i in range(rng.randint(4,7)):
        t = (i+1)/(rng.randint(4,7)+1)
        sx=bl[0]+t*(tl[0]-bl[0]);sy=bl[1]+t*(tl[1]-bl[1])
        ex=br[0]+t*(tr[0]-br[0]);ey=br[1]+t*(tr[1]-br[1])
        pdx,pdy=tl[0]-bl[0],tl[1]-bl[1]; pl=math.sqrt(pdx**2+pdy**2)or 1
        amp=pl*0.04; freq=1.5+(i%3)*0.7; phase=i*2.3
        pts=[]
        for p in range(21):
            f=p/20; bx=sx+f*(ex-sx);by=sy+f*(ey-sy)
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

    onder_s = get_eb_style(edgebands['onder']) if 'onder' in edgebands else None
    rechts_s = get_eb_style(edgebands['rechts']) if 'rechts' in edgebands else None

    # Back edges dashed
    for s,e in [(b_bl,b_br),(b_bl,b_tl)]:
        dx,dy=e[0]-s[0],e[1]-s[1]; l=math.sqrt(dx**2+dy**2)
        if l<1: continue
        segs=int(l/8)
        for i in range(0,segs,2):
            t1,t2=i/segs,min((i+1)/segs,1)
            draw.line([(s[0]+dx*t1,s[1]+dy*t1),(s[0]+dx*t2,s[1]+dy*t2)],fill='#aaa',width=2)

    # Top face — plain
    draw.polygon([f_tl,f_tr,b_tr,b_tl], fill='#e0e0e0', outline=oc, width=2)

    # Inner lines on top face: one line inset from the edge
    inset = 0.06  # fraction inward from edge
    edge_inner = {
        'boven':  (lerp(b_tl, f_tl, inset), lerp(b_tr, f_tr, inset)),
        'onder':  (lerp(f_tl, b_tl, inset), lerp(f_tr, b_tr, inset)),
        'links':  (lerp(f_tl, f_tr, inset), lerp(b_tl, b_tr, inset)),
        'rechts': (lerp(f_tr, f_tl, inset), lerp(b_tr, b_tl, inset)),
    }
    for side in edgebands:
        if side in edge_inner:
            p1, p2 = edge_inner[side]
            draw.line([p1, p2], fill='#555555', width=2)

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

    return {'f_bl':f_bl,'f_br':f_br,'f_tr':f_tr,'f_tl':f_tl,'b_bl':b_bl,'b_br':b_br,'b_tr':b_tr,'b_tl':b_tl}


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


def draw_callouts(draw, c, edgebands):
    ft,ftr,fbl,btl,btr=c['f_tl'],c['f_tr'],c['f_bl'],c['b_tl'],c['b_tr']
    ef=get_font(11,True);cc='#333'
    ed={'boven':(btl,btr),'onder':(ft,ftr),'links':(ft,btl),'rechts':(ftr,btr)}
    cp={
        'boven':{'lx':(btl[0]+btr[0])/2,'ly':btl[1]-55,'a':'ms'},
        'onder':{'lx':fbl[0]-30,'ly':fbl[1]+55,'a':'rm'},
        'links':{'lx':ft[0]-70,'ly':(ft[1]+btl[1])/2-25,'a':'rm'},
        'rechts':{'lx':btr[0]+70,'ly':(ftr[1]+btr[1])/2,'a':'lm'},
    }
    for side,txt in edgebands.items():
        if side not in ed: continue
        p1,p2=ed[side];mx,my=(p1[0]+p2[0])/2,(p1[1]+p2[1])/2
        c2=cp[side];lx,ly=c2['lx'],c2['ly']
        draw.text((lx,ly),txt,fill=cc,font=ef,anchor=c2['a'])
        bb=draw.textbbox((lx,ly),txt,font=ef,anchor=c2['a'])
        if side=='boven': ast=((bb[0]+bb[2])/2,bb[3]+2)
        elif side=='onder': ast=(bb[2]+4,(bb[1]+bb[3])/2)
        elif side=='links': ast=(bb[2]+4,(bb[1]+bb[3])/2)
        else: ast=(bb[0]-4,(bb[1]+bb[3])/2)
        draw.line([ast,(mx,my)],fill=cc,width=1)
        draw_arrowhead(draw,mx,my,ast[0],ast[1],cc,8)


tf=get_font(16,True); ox,oy,dl,dw,dh=220,370,260,100,65

for name,title,eb in [
    ('v8_eik','All eik',{'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm','links':'Fineer eik 1mm','rechts':'Fineer eik 1mm'}),
    ('v8_mixed','Mixed: eik boven/onder, wit links, zwart rechts',{'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm','links':'ABS wit 1mm','rechts':'ABS zwart 2mm'}),
    ('v8_partial','Partial: eik boven + onder',{'boven':'Fineer eik 1mm','onder':'Fineer eik 1mm'}),
    ('v8_none','No edgebands',{}),
]:
    img=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(img)
    d.rectangle([(0,0),(W,40)],fill='#333')
    d.text((W/2,20),f'V8: {title}',fill='white',font=tf,anchor='mm')
    c=draw_iso_box(d,ox,oy,dl,dw,dh,eb)
    draw_dim_arrows(d,c,1922,441,19,dl,dw,dh)
    if eb: draw_callouts(d,c,eb)
    img.save(f'/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_{name}.png')
    print(f"Saved {name}")

print("\nDone!")
