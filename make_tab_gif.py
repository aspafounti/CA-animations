"""
Tab-switch animation built on the real SVG-rendered frames.
Only the tab area + cursor are drawn dynamically; the rest of the design is the
untouched SVG. Rendered at 4x for crisp, consistent corners, then downscaled.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

# ── supersample / geometry (all base measurements in 1x SVG units) ───────────
SS = 4
def S(v): return int(round(v * SS))

SRC_W, SRC_H = 2240, 1428          # 4x render, cropped to content
FRAME_BG = (26, 26, 25)            # #1A1A19

# ── fonts ─────────────────────────────────────────────────────────────────────
US850 = "/Users/aspa.founti/Library/Fonts/UniversalSans-v1-1-0-100-20-111111121121-850.ttf"
F_LABEL = ImageFont.truetype(US850, S(13))   # matches SVG label scale
F_BADGE = ImageFont.truetype(US850, S(10))

# ── colours ───────────────────────────────────────────────────────────────────
SEL_BG        = (41,  41,  41)     # #292929
SEL_TEXT      = (204, 204, 204)    # #CCCCCC
SEL_BADGE_BG  = (86,  71,  2)      # #564702
SEL_BADGE_TXT = (255, 204, 0)      # #FFCC00

DEF_TEXT      = (115, 115, 115)    # #737373
DEF_BADGE_BG  = (71,  71,  71)     # #474747
DEF_BADGE_TXT = (204, 204, 204)    # #CCCCCC

HOV_TEXT      = (158, 158, 158)    # #9E9E9E (only label colour changes on hover)

# ── tab layout (1x SVG units, laid out dynamically with a generous gap) ──────
TAB_Y   = S(24); TAB_H = S(30); TAB_R = S(6)
BADGE_H = S(18); BADGE_R = S(3)
PAD_L   = S(9)        # tab-left  → label
GAP     = S(15)       # label → badge  (was ~8 in SVG; widened so they breathe)
PAD_R   = S(10)       # badge → tab-right
TAB_GAP = S(11)       # between the two tabs
TAB_X0  = S(23)       # first tab left edge (matches SVG)

TABS = [
    {"label": "My Dashboards",  "b1": "8",  "b2": "21", "sel_badge": "8"},
    {"label": "ExTrac Curated", "b1": "12", "b2": "12", "sel_badge": "12"},
]

def text_wh(font, s):
    bb = font.getbbox(s)
    return bb[2]-bb[0], bb[3]-bb[1], bb[0], bb[1]   # w, h, left-bearing, top

def badge_w(txt):
    w,_,_,_ = text_wh(F_BADGE, txt)
    return max(S(14), w + S(8))

# pre-compute positions
x = TAB_X0
for t in TABS:
    lw,_,_,_ = text_wh(F_LABEL, t["label"])
    t["labelW"] = lw
    t["tx"]     = x
    t["labelX"] = x + PAD_L
    t["badgeX"] = t["labelX"] + lw + GAP
    # full box width sized to the WIDER of its two badge states (prevents overlap)
    wmax = max(badge_w(t["b1"]), badge_w(t["b2"]))
    t["fullW"] = (t["badgeX"] + wmax + PAD_R) - t["tx"]
    x = t["tx"] + t["fullW"] + TAB_GAP

def tab_center(i):
    t = TABS[i]
    return t["tx"] + t["fullW"]//2, TAB_Y + TAB_H//2

# clear box: covers both tabs + Frame-2's baked cursor, inset from frame corners
CLEAR_BOX = [S(15), S(18), TABS[-1]["tx"] + TABS[-1]["fullW"] + S(20), S(65)]

# ── helpers ───────────────────────────────────────────────────────────────────
def lerp(a, b, t):  return a + (b - a) * max(0.0, min(1.0, t))
def ease(t):        t = max(0,min(1,t)); return t*t*(3-2*t)
def ease_out(t):    t = max(0,min(1,t)); return 1-(1-t)**3

# ── draw one tab ──────────────────────────────────────────────────────────────
def draw_tab(draw, idx, state, fi):
    t   = TABS[idx]
    bdg = t[f"b{fi}"]

    if state == "selected":
        bg, tc, bbg, btc = SEL_BG, SEL_TEXT, SEL_BADGE_BG, SEL_BADGE_TXT
    elif state == "hover":
        bg, tc, bbg, btc = None, HOV_TEXT, DEF_BADGE_BG, DEF_BADGE_TXT
    else:
        bg, tc, bbg, btc = None, DEF_TEXT, DEF_BADGE_BG, DEF_BADGE_TXT

    bw = badge_w(bdg)

    # selected background — hugs the actual badge, consistent rounded corners
    if bg:
        x0 = t["tx"]
        x1 = t["badgeX"] + bw + PAD_R
        draw.rounded_rectangle([x0, TAB_Y, x1, TAB_Y + TAB_H],
                               radius=TAB_R, fill=bg)

    # label (left-aligned at labelX, vertically centred)
    lw, lh, lbx, lby = text_wh(F_LABEL, t["label"])
    ly = TAB_Y + (TAB_H - lh)//2 - lby
    draw.text((t["labelX"] - lbx, ly), t["label"], font=F_LABEL, fill=tc)

    # badge
    bx = t["badgeX"]
    by = TAB_Y + (TAB_H - BADGE_H)//2
    draw.rounded_rectangle([bx, by, bx + bw, by + BADGE_H],
                           radius=BADGE_R, fill=bbg)
    tw, th, tbx, tby = text_wh(F_BADGE, bdg)
    draw.text((bx + (bw - tw)//2 - tbx, by + (BADGE_H - th)//2 - tby),
              bdg, font=F_BADGE, fill=btc)

def draw_tabs(draw, t0_state, t1_state, fi):
    # Clear ONLY the inner tab box (never the frame's rounded corners)
    draw.rectangle(CLEAR_BOX, fill=FRAME_BG)
    draw_tab(draw, 0, t0_state, fi)
    draw_tab(draw, 1, t1_state, fi)

# ── cursor ────────────────────────────────────────────────────────────────────
CURSOR_PTS = [(0,0),(0,52),(12,40),(20,60),(28,56),(20,36),(36,36)]
def draw_cursor(img, cx, cy, pressing=False):
    s = 0.88 if pressing else 1.0
    shd = Image.new("RGBA", img.size, (0,0,0,0))
    ImageDraw.Draw(shd).polygon(
        [(cx+p[0]*s+4, cy+p[1]*s+5) for p in CURSOR_PTS], fill=(0,0,0,80))
    img.paste(Image.alpha_composite(img.convert("RGBA"), shd).convert("RGB"))
    d = ImageDraw.Draw(img)
    d.polygon([(cx+p[0]*s, cy+p[1]*s) for p in CURSOR_PTS],
              fill=(0,0,0), outline=(0,0,0))
    d.polygon([(cx+p[0]*s*0.84+2, cy+p[1]*s*0.84+2) for p in CURSOR_PTS],
              fill=(255,255,255))

# ── base images ───────────────────────────────────────────────────────────────
print("Loading 4x base frames…")
B1 = Image.open('/tmp/ss4/01-Frame 1.svg.png').convert('RGB').crop((0,0,SRC_W,SRC_H))
B2 = Image.open('/tmp/ss4/01-Frame 2.svg.png').convert('RGB').crop((0,0,SRC_W,SRC_H))

# Erase Frame-1's baked cursor (sits in empty space, below the description)
ImageDraw.Draw(B1).rectangle([S(472), S(108), S(503), S(140)], fill=FRAME_BG)

# ── progressive thumbnail blur (Frame 2) ─────────────────────────────────────
# The thumbnails render sharp; apply a LIGHT progressive blur so the content is
# illegible but the image still looks crisp/clear. Blur eases from top→bottom.
def progressive_blur(img, box, r_top, r_bot):
    x0, y0, x1, y1 = box
    pad = int(max(r_top, r_bot) * 3)
    cx0, cy0 = max(0, x0-pad), max(0, y0-pad)
    cx1, cy1 = min(img.width, x1+pad), min(img.height, y1+pad)
    region = img.crop((cx0, cy0, cx1, cy1))
    lo = region.filter(ImageFilter.GaussianBlur(r_top))   # lighter (top)
    hi = region.filter(ImageFilter.GaussianBlur(r_bot))   # heavier (bottom)
    w, h = region.size
    grad = Image.new("L", (1, h))
    gp = grad.load()
    for y in range(h):
        t = (cy0 + y - y0) / max(1, (y1 - y0))
        gp[0, y] = int(255 * max(0.0, min(1.0, t)))
    mask = grad.resize((w, h))
    blended = Image.composite(hi, lo, mask)
    bx0, by0 = x0-cx0, y0-cy0
    img.paste(blended.crop((bx0, by0, bx0+(x1-x0), by0+(y1-y0))), (x0, y0))

# Thumbnail rects (1x → 4x). Right card runs off-canvas, so clip x1 to SRC_W.
# 4x-space radii. Lightened vs before (esp. the heavy bottom) but held at the
# point where operational text (dates, place names) stays illegible.
R_TOP, R_BOT = 2.8, 4.2
_lt = (S(38.776), S(157.037), S(387.224), S(333.964))
_rt = (S(442.776), S(157.037), min(SRC_W, S(791.224)), S(333.964))
progressive_blur(B2, _lt, R_TOP, R_BOT)
progressive_blur(B2, _rt, R_TOP, R_BOT)

# ── animation timeline (196 frames @ 24 fps base — snappier than before) ─────
TOTAL = 196; FPS = 24
REST_X, REST_Y = S(481), S(112)      # matches the SVG's resting cursor

def get_state(f):
    """Returns tab states, cursor pos, press amounts, and screen (1 or 2).
    Content swaps INSTANTLY on click — no dissolve (a real tab switch)."""
    ec = tab_center(1); md = tab_center(0)
    t0, t1 = "selected", "default"
    cx, cy = REST_X, REST_Y
    p0 = p1 = 0.0
    screen = 1

    if   f < 16:                                   # idle (frame 1)
        cx, cy = REST_X, REST_Y

    elif f < 50:                                   # glide → ExTrac
        t = ease((f-16)/34)
        cx = lerp(REST_X, ec[0]-S(2), t)
        cy = lerp(REST_Y, ec[1]-S(2), t)
        if t > 0.85: t1 = "hover"

    elif f < 70:                                   # hover pause
        cx, cy = ec[0]-S(2), ec[1]-S(2); t1 = "hover"

    elif f < 76:                                   # click ExTrac (down→up)
        cx, cy = ec[0]-S(2), ec[1]-S(2)
        pf = f-70
        p1 = ease(pf/3) if pf < 3 else ease(1-(pf-3)/3)
        if pf < 4:                                 # before release: still hovering frame 1
            t1 = "hover"
        else:                                      # release → INSTANT switch to frame 2
            t0, t1, screen = "default", "selected", 2

    elif f < 110:                                  # view frame 2
        cx, cy = ec[0]-S(2), ec[1]-S(2)
        t0, t1, screen = "default", "selected", 2

    elif f < 144:                                  # glide → My Dashboards
        t = ease((f-110)/34)
        cx = lerp(ec[0]-S(2), md[0]-S(2), t)
        cy = lerp(ec[1]-S(2), md[1]-S(2), t)
        t0, t1, screen = "default", "selected", 2
        if t > 0.85: t0 = "hover"

    elif f < 164:                                  # hover pause
        cx, cy = md[0]-S(2), md[1]-S(2)
        t0, t1, screen = "hover", "selected", 2

    elif f < 170:                                  # click My Dashboards
        cx, cy = md[0]-S(2), md[1]-S(2)
        pf = f-164
        p0 = ease(pf/3) if pf < 3 else ease(1-(pf-3)/3)
        if pf < 4:
            t0, t1, screen = "hover", "selected", 2
        else:                                      # release → INSTANT switch to frame 1
            t0, t1, screen = "selected", "default", 1

    else:                                          # glide back to rest + idle (frame 1)
        t = ease_out((f-170) / (TOTAL-170))
        cx = lerp(md[0]-S(2), REST_X, t)
        cy = lerp(md[1]-S(2), REST_Y, t)
        t0, t1 = "selected", "default"

    return t0, t1, cx, cy, p0, p1, screen

# ── render full-res frames ────────────────────────────────────────────────────
print("Rendering frames…")
frames = []; screens = []
for f in range(TOTAL):
    t0, t1, cx, cy, p0, p1, screen = get_state(f)
    img = (B1 if screen == 1 else B2).copy()
    draw = ImageDraw.Draw(img)
    draw_tabs(draw, t0, t1, screen)
    draw_cursor(img, int(cx), int(cy), p0 > 0.12 or p1 > 0.12)
    frames.append(img); screens.append(screen)
    if f % 48 == 0: print(f"  {f}/{TOTAL}")

frames[0].crop((0, 0, S(360), S(72))).resize((S(360)//2, S(72)//2), Image.LANCZOS)\
        .save('/tmp/diag_tabs.png')

# ── thin to 12 fps, downscale to 2x ──────────────────────────────────────────
OUT_W = 1120; OUT_H = round(OUT_W * SRC_H / SRC_W)        # 1120 x 714 (2x)
idx      = list(range(0, TOTAL, 2))
small    = [frames[i].resize((OUT_W, OUT_H), Image.LANCZOS) for i in idx]
sscreens = [screens[i] for i in idx]

# Build ONE palette: RESERVE the exact UI/brand colours (so the gold never gets
# quantized away) + a transparent sentinel at index 255.
BRAND = [
    (26,26,25),(41,41,41),(204,204,204),(86,71,2),(255,204,0),
    (115,115,115),(71,71,71),(158,158,158),(255,255,255),(0,0,0),
    (32,32,32),(24,24,24),(46,46,46),(56,56,56),(38,38,38),(25,25,24),
]
SENTINEL = (255, 0, 255)                    # index 255 → transparent (no magenta in UI)
# adaptive palette from BOTH screens (so all thumbnails are represented)
montage = Image.new("RGB", (OUT_W, OUT_H*2))
montage.paste(small[next(i for i,s in enumerate(sscreens) if s==1)], (0, 0))
montage.paste(small[next(i for i,s in enumerate(sscreens) if s==2)], (0, OUT_H))
n_adapt = 256 - len(BRAND) - 1              # leave index 255 free for transparency
adapt = montage.quantize(colors=n_adapt, method=Image.MEDIANCUT, dither=Image.NONE)
apal  = adapt.getpalette()[:3*n_adapt]
pal_bytes = []
for c in BRAND: pal_bytes += list(c)
pal_bytes += apal
pal_bytes = (pal_bytes + [0]*765)[:765]
pal_bytes += list(SENTINEL)                 # index 255
PAL = Image.new("P", (1,1)); PAL.putpalette(pal_bytes)

pframes = [s.quantize(palette=PAL, dither=Image.NONE) for s in small]

# ── make outside-the-rounded-corners transparent (index 255) ─────────────────
rad  = round(15 * OUT_W / (SRC_W // SS))     # SVG frame corner radius (15 @ 1x) at output scale
keep = Image.new("L", (OUT_W, OUT_H), 0)
ImageDraw.Draw(keep).rounded_rectangle([0, 0, OUT_W-1, OUT_H-1], radius=rad, fill=255)
corners = keep.point(lambda v: 255 if v < 128 else 0)   # 255 OUTSIDE the rounded rect
stray = sum(1 for p in pframes[next(i for i,s in enumerate(sscreens) if s==2)].getdata() if p == 255)
print(f"content pixels accidentally on sentinel index: {stray} (want 0)")
for pf in pframes:
    pf.paste(255, (0, 0), corners)           # corner nubs → transparent

# ── export: delta-encode (optimize) + 1-bit transparency on the corners ──────
out = "/Users/aspa.founti/Claude/tab-animation.gif"
pframes[0].save(out, save_all=True, append_images=pframes[1:],
                duration=int(1000/(FPS//2)), loop=0,
                optimize=True, transparency=255, disposal=1)
import os
print(f"\nSaved → {out}  ({OUT_W}x{OUT_H}, {len(pframes)} frames, "
      f"{os.path.getsize(out)//1024} KB)")
