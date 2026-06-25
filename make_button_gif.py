"""
Button-toggle animation (separate from the tab animation).
Flow: cursor clicks "Show in Home" → toggles ON ("Remove from Home") →
hovers the share icon (tooltip) → clicks → toggles ON. Then a creative reset:
cursor glides back to start while the card crossfades back to default. Loops.

Same pipeline as tab-animation: 4x SVG render → brand-safe palette →
transparent rounded corners → delta-compressed GIF.
"""
from PIL import Image, ImageDraw
import os

# ── geometry / scale ──────────────────────────────────────────────────────────
SVG_W = 563
RENDER_W = 2240
SCALE = RENDER_W / SVG_W                 # qlmanage capped at 2240 (≈3.979x)
def S(v): return int(round(v * SCALE))

SRC_W, SRC_H = 2238, 1420                # tight crop to the frame (no white sliver)
FRAME_BG = (26, 26, 25)                  # #1A1A19

# ── base states (cursors already stripped) ───────────────────────────────────
print("Loading base states…")
def base(name):
    return Image.open(f"/tmp/btn/clean/{name}.svg.png").convert("RGB").crop((0,0,SRC_W,SRC_H))
BASES = {
    "DEF":  base("F1"),        # default — "Show in Home" outline, share default
    "HOV":  base("F1_hover"),  # home hover — muted-gold fill
    "HON":  base("F2"),        # home ON — "Remove from Home", share default
    "SHOV": base("F3"),        # share hover — tooltip "Share with Team"
    "SON":  base("F4"),        # share ON — gold icon button
}

# ── helpers ───────────────────────────────────────────────────────────────────
def lerp(a, b, t):  return a + (b - a) * max(0.0, min(1.0, t))
def ease(t):        t = max(0,min(1,t)); return t*t*(3-2*t)
def ease_out(t):    t = max(0,min(1,t)); return 1-(1-t)**3

# ── cursor ────────────────────────────────────────────────────────────────────
CURSOR_PTS = [(0,0),(0,68),(16,52),(26,79),(37,74),(26,47),(48,47)]   # ~tip-anchored
def draw_cursor(img, cx, cy, pressing=False):
    s = 0.88 if pressing else 1.0
    shd = Image.new("RGBA", img.size, (0,0,0,0))
    ImageDraw.Draw(shd).polygon([(cx+p[0]*s+5, cy+p[1]*s+6) for p in CURSOR_PTS], fill=(0,0,0,90))
    img.paste(Image.alpha_composite(img.convert("RGBA"), shd).convert("RGB"))
    d = ImageDraw.Draw(img)
    d.polygon([(cx+p[0]*s, cy+p[1]*s) for p in CURSOR_PTS], fill=(0,0,0), outline=(0,0,0))
    d.polygon([(cx+p[0]*s*0.84+2, cy+p[1]*s*0.84+2) for p in CURSOR_PTS], fill=(255,255,255))

# ── cursor key positions (1x SVG → render px) ────────────────────────────────
START = (S(347), S(34))
HOME  = (S(175), S(302))
SHARE = (S(373), S(303))

# ── timeline (180 frames @ 24 fps base) ──────────────────────────────────────
TOTAL = 180; FPS = 24

def get_state(f):
    state = "DEF"; cx, cy = START; press = 0.0; bt = None

    if f < 14:                                   # idle
        cx, cy = START

    elif f < 46:                                 # glide → home button
        t = ease((f-14)/32)
        cx = lerp(START[0], HOME[0], t); cy = lerp(START[1], HOME[1], t)
        if t > 0.8: state = "HOV"

    elif f < 62:                                 # hover home
        cx, cy = HOME; state = "HOV"

    elif f < 68:                                 # click home → toggle ON
        cx, cy = HOME
        pf = f-62; press = ease(pf/3) if pf < 3 else ease(1-(pf-3)/3)
        state = "HOV" if pf < 3 else "HON"

    elif f < 84:                                 # pause (home on)
        cx, cy = HOME; state = "HON"

    elif f < 114:                                # glide → share button
        t = ease((f-84)/30)
        cx = lerp(HOME[0], SHARE[0], t); cy = lerp(HOME[1], SHARE[1], t)
        state = "SHOV" if t > 0.8 else "HON"

    elif f < 130:                                # hover share (tooltip)
        cx, cy = SHARE; state = "SHOV"

    elif f < 136:                                # click share → toggle ON
        cx, cy = SHARE
        pf = f-130; press = ease(pf/3) if pf < 3 else ease(1-(pf-3)/3)
        state = "SHOV" if pf < 3 else "SON"

    elif f < 156:                                # pause (final, both on)
        cx, cy = SHARE; state = "SON"

    else:                                        # creative reset
        t = ease_out((f-156)/(TOTAL-156))        # cursor glides back to start…
        cx = lerp(SHARE[0], START[0], t); cy = lerp(SHARE[1], START[1], t)
        # …and the buttons reset behind it once the cursor has left the button row
        state = "SON" if t < 0.62 else "DEF"

    return state, cx, cy, press, bt

# ── render full-res frames ────────────────────────────────────────────────────
print("Rendering frames…")
frames = []; states = []
for f in range(TOTAL):
    state, cx, cy, press, bt = get_state(f)
    img = BASES[state].copy()
    draw_cursor(img, int(cx), int(cy), press > 0.12)
    frames.append(img); states.append(state)
    if f % 36 == 0: print(f"  {f}/{TOTAL}")

# ── thin to 12 fps, downscale to 2x ──────────────────────────────────────────
OUT_W = 1120; OUT_H = round(OUT_W * SRC_H / SRC_W)
idx   = list(range(0, TOTAL, 2))
small = [frames[i].resize((OUT_W, OUT_H), Image.LANCZOS) for i in idx]

# ── brand-safe palette (+ transparent sentinel) ──────────────────────────────
BRAND = [
    (26,26,25),(26,26,26),(255,204,0),(0,0,0),(145,115,0),
    (73,73,73),(100,100,100),(204,204,204),(71,71,71),(86,71,2),
    (255,255,255),(41,41,41),(115,115,115),(158,158,158),(17,17,17),(56,56,56),
]
SENTINEL = (255, 0, 255)
montage = Image.new("RGB", (OUT_W, OUT_H*2))
montage.paste(small[0], (0, 0))
montage.paste(small[len(small)//2], (0, OUT_H))
n_adapt = 256 - len(BRAND) - 1
adapt = montage.quantize(colors=n_adapt, method=Image.MEDIANCUT, dither=Image.NONE)
apal  = adapt.getpalette()[:3*n_adapt]
pal_bytes = []
for c in BRAND: pal_bytes += list(c)
pal_bytes += apal
pal_bytes = (pal_bytes + [0]*765)[:765]
pal_bytes += list(SENTINEL)
PAL = Image.new("P", (1,1)); PAL.putpalette(pal_bytes)
# No dither: the preview rings are crisp (not a smooth wash), so there's no banding
# to fix, and skipping dither keeps the UI razor-sharp and the file ~3x smaller.
pframes = [s.quantize(palette=PAL, dither=Image.NONE) for s in small]

# ── transparent rounded corners ──────────────────────────────────────────────
rad  = round(15 * OUT_W / SVG_W)
keep = Image.new("L", (OUT_W, OUT_H), 0)
ImageDraw.Draw(keep).rounded_rectangle([0,0,OUT_W-1,OUT_H-1], radius=rad, fill=255)
corners = keep.point(lambda v: 255 if v < 128 else 0)
stray = sum(1 for p in pframes[0].getdata() if p == 255)
print(f"content pixels on sentinel index: {stray} (want 0)")
for pf in pframes:
    pf.paste(255, (0, 0), corners)

out = "/Users/aspa.founti/Claude/button-animation.gif"
pframes[0].save(out, save_all=True, append_images=pframes[1:],
                duration=int(1000/(FPS//2)), loop=0,
                optimize=True, transparency=255, disposal=1)
print(f"\nSaved → {out}  ({OUT_W}x{OUT_H}, {len(pframes)} frames, {os.path.getsize(out)//1024} KB)")
