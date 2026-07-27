"""
menu-selection — sidebar menu (Home / Libraries / Alerts) animation.
Flow: rest -> cursor glides to Libraries -> hover (white 15% highlight) -> click ->
selected (gold on #262003, others dim) -> swoop: the selected menu slides out left
on a diagonal, wraps off-screen, a fresh normal menu swoops in from the right and
settles to centre -> loops seamlessly.
Same series pipeline as the landscape gifs: 565x465 -> 900x741, animated cursor,
brand palette, transparent rounded corners.
"""
from PIL import Image, ImageDraw
import os, math

CLEAN = "/tmp/menuL/clean"
SVG_W, SVG_H = 565, 465
SCALE = 2260 / SVG_W                       # 4.0
def S(v): return int(round(v * SCALE))
W, H = 2260, S(SVG_H)                       # 2260 x 1860
OUT_W, OUT_H = 900, round(SVG_H * 900 / SVG_W)   # 900 x 741
FRAME_BG = (26, 26, 25)

print("Loading states…")
def load(nm): return Image.open(f"{CLEAN}/{nm}.svg.png").convert("RGB").crop((0,0,W,H))
S1, S2, S3 = load("S1"), load("S2"), load("S3")   # normal, hover, selected

# ── row bands (svg y), chosen in the gaps between items so slicing is seamless ─
BANDS_SVG = [(118, 190), (190, 289), (289, 352)]   # Home, Libraries, Alerts
BANDS = [(S(a), S(b)) for a, b in BANDS_SVG]
def slice_bands(img): return [img.crop((0, y0, W, y1)) for (y0, y1) in BANDS]
S1_BANDS = slice_bands(S1)     # normal  (swoop-in)
S3_BANDS = slice_bands(S3)     # selected (swoop-out)
# base = the real normal frame with only the row strips cleared, so swoop_frame(1.0)
# reconstructs S1 pixel-perfectly (frame edges/corners stay identical → seamless loop)
BG = S1.copy()
for (y0, y1) in BANDS: ImageDraw.Draw(BG).rectangle((0, y0, W, y1), fill=FRAME_BG)

# ── swoop: per-row horizontal offset (svg units). Lower rows lead → diagonal.
#    base = Libraries-row offset; tilt shears the rows (Home right, Alerts left). ─
OFF = 540.0        # off-screen travel
TILT = 38.0        # per-row shear (matches storyboard Step4/Step5)
def swoop_offsets(sw):
    # car-like: accelerate out (ease-in cubic), then swoop in fast and brake (ease-out cubic)
    if sw < 0.5:  base = -OFF * (sw/0.5)**3
    else:         base =  OFF * (1 - (sw-0.5)/0.5)**3
    tilt = -TILT * math.sin(math.pi * sw)
    return [base - tilt, base, base + tilt]           # Home, Libraries, Alerts
def swoop_frame(sw):
    canvas = BG.copy()
    bands = S3_BANDS if sw < 0.5 else S1_BANDS        # selected out, normal in
    offs = swoop_offsets(sw)
    for i, (y0, y1) in enumerate(BANDS):
        canvas.paste(bands[i], (int(round(offs[i]*SCALE)), y0))
    return canvas

# ── cursor (same as the rest of the series) ──────────────────────────────────
def lerp(a,b,t): return a+(b-a)*max(0.0,min(1.0,t))
def ease(t):     t=max(0,min(1,t)); return t*t*(3-2*t)
def ease_out(t): t=max(0,min(1,t)); return 1-(1-t)**3
def blend(a,b,t): return Image.blend(a,b,max(0.0,min(1.0,t)))
CURSOR_PTS=[(0,0),(0,68),(16,52),(26,79),(37,74),(26,47),(48,47)]
def draw_cursor(img,cx,cy,press=False):
    s=0.88 if press else 1.0
    shd=Image.new("RGBA",img.size,(0,0,0,0))
    ImageDraw.Draw(shd).polygon([(cx+p[0]*s+5,cy+p[1]*s+6) for p in CURSOR_PTS],fill=(0,0,0,90))
    img.paste(Image.alpha_composite(img.convert("RGBA"),shd).convert("RGB"))
    d=ImageDraw.Draw(img)
    d.polygon([(cx+p[0]*s,cy+p[1]*s) for p in CURSOR_PTS],fill=(0,0,0),outline=(0,0,0))
    d.polygon([(cx+p[0]*s*0.84+2,cy+p[1]*s*0.84+2) for p in CURSOR_PTS],fill=(255,255,255))

REST = (518.3, 42.0)        # top-right rest (storyboard Step1/Step5 cursor)
LAND = (340.0, 230.0)       # cursor lands inside the Libraries item

# hover/selected surface (Step2/Step3 highlight rect) — hover triggers on entering it
HRECT = (S(129.203), S(203.723), S(436.76), S(261.277))
def _in_rect(pt):
    x, y = S(pt[0]), S(pt[1])
    return HRECT[0] <= x <= HRECT[2] and HRECT[1] <= y <= HRECT[3]
def clamp(x, lo, hi): return max(lo, min(hi, x))

# gentle click: scale the Libraries area (pill + shadow) about its centre
CX0, CY0, CX1, CY1 = S(115), S(185), S(450), S(292)
def apply_click(img, sc):
    if sc >= 0.999: return img
    reg = img.crop((CX0, CY0, CX1, CY1)); w, h = reg.size
    nw, nh = max(1, int(round(w*sc))), max(1, int(round(h*sc)))
    reg = reg.resize((nw, nh), Image.LANCZOS)
    ImageDraw.Draw(img).rectangle((CX0, CY0, CX1, CY1), fill=FRAME_BG)
    img.paste(reg, (CX0 + (w-nw)//2, CY0 + (h-nh)//2))
    return img

# ── timeline @24fps ──────────────────────────────────────────────────────────
IDLE_END, MOVE_END, HOVER_END, CLICK_END, SELECT_END = 10, 38, 48, 52, 74
SWOOP_LEN = 40                                  # swoop motion frames (brakes to centre by then)
TOTAL, FPS = 128, 24                            # +10 frames holding centre before the loop
def _move_tip(f):
    t = ease_out((f-IDLE_END)/(MOVE_END-IDLE_END))
    return (lerp(REST[0], LAND[0], t), lerp(REST[1], LAND[1], t))
F_ENTER = MOVE_END                              # first move-frame the tip enters the item area
for _f in range(IDLE_END, MOVE_END):
    if _in_rect(_move_tip(_f)): F_ENTER = _f; break
FADE = 3                                        # quick hover fade (frames)

def state(f):
    press = False; sc = 1.0
    # cursor tip
    if   f < IDLE_END:   tip = REST
    elif f < MOVE_END:   tip = _move_tip(f)
    elif f < SELECT_END: tip = LAND
    else:                                        # retreat to rest during the swoop
        ct = ease_out((f-SELECT_END)/20); tip = (lerp(LAND[0],REST[0],ct), lerp(LAND[1],REST[1],ct))
    # menu image
    if f < MOVE_END:                             # hover fades in on entering the item area
        hv = clamp((f-F_ENTER)/FADE, 0, 1) if f >= F_ENTER else 0.0
        img = blend(S1, S2, hv)
    elif f < HOVER_END:                          # hold hover
        img = S2.copy()
    elif f < CLICK_END:                          # click: split-second press + snap to gold
        img = blend(S2, S3, clamp((f-HOVER_END)/2, 0, 1))
        sc = 1 - 0.05*math.sin(math.pi*clamp((f-HOVER_END)/(CLICK_END-HOVER_END), 0, 1))
        press = (f-HOVER_END) < 2
    elif f < SELECT_END:                         # hold selected
        img = S3.copy()
    else:                                        # swoop out+in, then hold centre (clamped to 1)
        img = swoop_frame(clamp((f-SELECT_END)/SWOOP_LEN, 0, 1))
    return apply_click(img, sc), tip, press

# ── render ───────────────────────────────────────────────────────────────────
print("Rendering…")
frames=[]
for f in range(TOTAL):
    img, tip, press = state(f)
    draw_cursor(img, S(tip[0]), S(tip[1]), press)
    frames.append(img.resize((OUT_W,OUT_H),Image.LANCZOS))
    if f%36==0: print(f"  {f}/{TOTAL}")

# ── brand palette + transparent corners ──────────────────────────────────────
BRAND=[(26,26,25),(158,158,158),(242,242,240),(255,204,0),(38,32,3),(171,171,167),
       (60,60,59),(52,52,51),(0,0,0),(255,255,255),(90,90,89),(45,45,44),(120,120,119),
       (73,73,71),(200,200,200),(115,115,111),(140,140,136)]
SENT=(255,0,255)
montage=Image.new("RGB",(OUT_W,OUT_H*2)); montage.paste(frames[0],(0,0)); montage.paste(frames[70],(0,OUT_H))
n_adapt=256-len(BRAND)-1
adapt=montage.quantize(colors=n_adapt,method=Image.MEDIANCUT,dither=Image.NONE)
pal=[]; [pal.extend(c) for c in BRAND]; pal+=adapt.getpalette()[:3*n_adapt]
pal=(pal+[0]*765)[:765]; pal+=list(SENT)
PAL=Image.new("P",(1,1)); PAL.putpalette(pal)
pframes=[s.quantize(palette=PAL,dither=Image.NONE) for s in frames]
RAD=round(7.64*OUT_W/SVG_W)
keep=Image.new("L",(OUT_W,OUT_H),0)
ImageDraw.Draw(keep).rounded_rectangle([1,1,OUT_W-2,OUT_H-2],radius=RAD-1,fill=255)
corners=keep.point(lambda v:255 if v<128 else 0)
print("sentinel collisions:", sum(1 for p in pframes[0].getdata() if p==255))
for pf in pframes: pf.paste(255,(0,0),corners)

out="/Users/aspa.founti/Claude/menu-selection.gif"
pframes[0].save(out,save_all=True,append_images=pframes[1:],duration=int(1000/FPS),
                loop=0,optimize=True,transparency=255,disposal=1)
print(f"\nSaved -> {out} ({OUT_W}x{OUT_H}, {len(pframes)} frames, {os.path.getsize(out)//1024} KB)")
