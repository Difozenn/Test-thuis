"""Generate concept mockup images for edgeband visualization options."""
from PIL import Image, ImageDraw, ImageFont
import math

BG = '#f5f5f5'
W, H = 800, 700


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

    # Back edges dashed (simulate with short segments)
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

    # Lengte (bottom)
    if length > 0:
        ay = oy + gap
        draw.line([(ox, ay), (ox + dl, ay)], fill=arrow_color, width=2)
        draw.text(((ox + ox + dl) / 2, ay + 6), f"{length:g} mm", fill='#333333', font=font, anchor='mt')

    # Dikte (left)
    if height > 0:
        ax = ox - gap
        draw.line([(ax, oy), (ax, oy - dh)], fill=arrow_color, width=2)
        draw.text((ax - 4, oy - dh / 2), f"{height:g}", fill='#333333', font=font, anchor='rm')

    # Breedte (right)
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
# OPTION 1: Compact text legend below iso box
# ============================================================
img1 = Image.new('RGB', (W, H), BG)
d1 = ImageDraw.Draw(img1)

title_font = get_font(20, bold=True)
d1.rectangle([(0, 0), (W, 50)], fill='#333333')
d1.text((W/2, 25), 'Option 1: Compact Text Legend Below', fill='white', font=title_font, anchor='mm')

# Iso box
ox, oy = 150, 420
dl, dw, dh = 300, 120, 80
corners = draw_iso_box(d1, ox, oy, dl, dw, dh)
draw_dim_arrows(d1, corners, 1922, 441, 19, dl, dw, dh)

# Separator
d1.line([(30, 490), (W - 30, 490)], fill='#cccccc', width=1)

# Text legend
legend_font = get_font(13, bold=True)
legend_font_light = get_font(13)
label_color = '#333333'
val_color = '#000000'
no_val = '#aaaaaa'

y_base = 510
col1_x = 80
col2_x = W / 2 + 40

# Boven
d1.text((col1_x, y_base), "Boven:", fill=label_color, font=legend_font, anchor='lm')
d1.text((col1_x + 65, y_base), "Fineer eik 1mm", fill=val_color, font=legend_font_light, anchor='lm')

# Onder
d1.text((col2_x, y_base), "Onder:", fill=label_color, font=legend_font, anchor='lm')
d1.text((col2_x + 65, y_base), "Fineer eik 1mm", fill=val_color, font=legend_font_light, anchor='lm')

y_base2 = 540
# Links
d1.text((col1_x, y_base2), "Links:", fill=label_color, font=legend_font, anchor='lm')
d1.text((col1_x + 65, y_base2), "—", fill=no_val, font=legend_font_light, anchor='lm')

# Rechts
d1.text((col2_x, y_base2), "Rechts:", fill=label_color, font=legend_font, anchor='lm')
d1.text((col2_x + 65, y_base2), "—", fill=no_val, font=legend_font_light, anchor='lm')

# Title label
small_title = get_font(11, bold=True)
d1.text((W/2, 498), "Afplakband", fill='#666666', font=small_title, anchor='mt')

img1.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_option1.png')
print("Saved option 1")


# ============================================================
# OPTION 2: Thin strips on visible edge faces of iso box
# ============================================================
img2 = Image.new('RGB', (W, H), BG)
d2 = ImageDraw.Draw(img2)

d2.rectangle([(0, 0), (W, 50)], fill='#333333')
d2.text((W/2, 25), 'Option 2: Edge Strips on Iso Box Faces', fill='white', font=title_font, anchor='mm')

# Iso box
ox, oy = 150, 400
dl, dw, dh = 300, 120, 80
corners = draw_iso_box(d2, ox, oy, dl, dw, dh)
draw_dim_arrows(d2, corners, 1922, 441, 19, dl, dw, dh)

# Draw edgeband strips on the visible edges (front face edges + right face edges)
eb_color = '#D2691E'
strip_w = 4

f_bl = corners['f_bl']
f_br = corners['f_br']
f_tr = corners['f_tr']
f_tl = corners['f_tl']
b_br = corners['b_br']
b_tr = corners['b_tr']

# Boven = top edge of front face (f_tl -> f_tr) - has edgeband
d2.line([f_tl, f_tr], fill=eb_color, width=strip_w)
# Onder = bottom edge of front face (f_bl -> f_br) - has edgeband
d2.line([f_bl, f_br], fill=eb_color, width=strip_w)
# Rechts = right edge: front face right (f_br -> f_tr) + right face right (f_tr -> b_tr) - has edgeband
d2.line([f_br, f_tr], fill=eb_color, width=strip_w)
d2.line([f_tr, b_tr], fill=eb_color, width=strip_w)
# Links = left edge: not visible (back side), show nothing

# Small legend
d2.line([(30, 470), (W - 30, 470)], fill='#cccccc', width=1)
small_title = get_font(11, bold=True)
d2.text((W/2, 478), "Afplakband", fill='#666666', font=small_title, anchor='mt')

legend_font = get_font(11, bold=True)
legend_font_light = get_font(11)

# Color key
y = 500
d2.line([(col1_x, y), (col1_x + 25, y)], fill=eb_color, width=4)
d2.text((col1_x + 32, y), "= Afplakband aanwezig", fill='#666666', font=legend_font_light, anchor='lm')

y = 525
d2.text((col1_x, y), "Boven: Fineer eik 1mm", fill='#333', font=legend_font_light, anchor='lm')
d2.text((col1_x, y + 22), "Onder: Fineer eik 1mm", fill='#333', font=legend_font_light, anchor='lm')
d2.text((col2_x, y), "Rechts: Fineer eik 1mm", fill='#333', font=legend_font_light, anchor='lm')
d2.text((col2_x, y + 22), "Links: —", fill='#aaaaaa', font=legend_font_light, anchor='lm')

img2.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_option2.png')
print("Saved option 2")


# ============================================================
# OPTION 3: Current flat diagram (refined/compact)
# ============================================================
img3 = Image.new('RGB', (W, H), BG)
d3 = ImageDraw.Draw(img3)

d3.rectangle([(0, 0), (W, 50)], fill='#333333')
d3.text((W/2, 25), 'Option 3: Flat Diagram Below Iso Box', fill='white', font=title_font, anchor='mm')

# Iso box
ox, oy = 150, 380
dl, dw, dh = 300, 120, 80
corners = draw_iso_box(d3, ox, oy, dl, dw, dh)
draw_dim_arrows(d3, corners, 1922, 441, 19, dl, dw, dh)

# Separator
d3.line([(30, 450), (W - 30, 450)], fill='#cccccc', width=1)

# Flat panel rectangle
rx1, ry1 = 200, 480
rx2, ry2 = 600, 620
d3.rectangle([(rx1, ry1), (rx2, ry2)], fill='#eeeeee', outline='#888888', width=1)

eb_font = get_font(11, bold=True)

# Boven - bold black edge + label
d3.line([(rx1, ry1), (rx2, ry1)], fill='#000000', width=4)
d3.text(((rx1 + rx2) / 2, ry1 - 10), "Fineer eik 1mm", fill='#000000', font=eb_font, anchor='ms')

# Onder - bold black edge + label
d3.line([(rx1, ry2), (rx2, ry2)], fill='#000000', width=4)
d3.text(((rx1 + rx2) / 2, ry2 + 12), "Fineer eik 1mm", fill='#000000', font=eb_font, anchor='mt')

# Links - no edgeband, thin grey
d3.line([(rx1, ry1), (rx1, ry2)], fill='#cccccc', width=1)

# Rechts - no edgeband, thin grey
d3.line([(rx2, ry1), (rx2, ry2)], fill='#cccccc', width=1)

img3.save('/mnt/c/Users/Rob/Desktop/Test-thuis/Barcodematch/temp/concept_option3.png')
print("Saved option 3")

print("\nAll mockups saved to temp/ folder")
