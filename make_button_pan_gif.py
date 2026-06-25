"""
Button-toggle animation with a PANNING loop (separate from the other GIFs).
Flow: cursor clicks "Show in Home" (toggles ON) → clicks the Share-with-Team icon
(toggles ON) → the camera pans right to the next (identical) card and repeats.

Because every card is identical, panning exactly one card-pitch lands on a fresh
default card that looks pixel-identical to the start → seamless infinite loop with
no button reverting.

Pipeline matches the other animations: 4x SVG render → tiled card "world" →
panning camera → brand-safe palette → transparent rounded corners → delta GIF.
"""
from PIL import Image, ImageDraw
import os

# ── geometry / scale ──────────────────────────────────────────────────────────
SVG_W = 563
RENDER_W = 2240
SCALE = RENDER_W / SVG_W
def S(v): return int(round(v * SCALE))

SRC_W, SRC_H = 2238, 1420                # frame viewport (tight crop, no white sliver)
FRAME_BG = (26, 26, 25)                  # #1A1A19
CARD_LEFT = S(23)                        # first card container left edge
PITCH     = S(396)                       # distance between cards

# ── load crisp, cursor-stripped state renders ────────────────────────────────
print("Loading state renders…")
def base(name):
    return Image.open(f"/tmp/btn/clean/{name}.svg.png").convert("RGB").crop((0,0,SRC_W,SRC_H))
RENDERS = {
    "DEF":  base("F1"), "HOV": base("F1_hover"), "HON": base("F2"),
    "SHOV": base("F3"), "SON": base("F4"),
}

# ── extract one card+gap tile per state (world-x CARD_LEFT … CARD_LEFT+PITCH) ─
def tile(name): return RENDERS[name].crop((CARD_LEFT, 0, CARD_LEFT + PITCH, SRC_H))
TILES = {k: tile(k) for k in RENDERS}
DEFAULT_TILE = TILES["DEF"]

# ── build one "world" strip per active-card state ────────────────────────────
# Carousel of identical cards: a default card on each side so the row looks
# continuous and panning one pitch lands on a pixel-identical framing (seamless).
# Slot 0 (the active card) sits one pitch in; the camera's base scroll = PITCH.
WORLD_W = CARD_LEFT + 5 * PITCH
def build_world(active_state):
    w = Image.new("RGB", (WORLD_W, SRC_H), FRAME_BG)
    for k in (-1, 1, 2):                                    # default neighbours
        w.paste(DEFAULT_TILE, (CARD_LEFT + (k+1)*PITCH, 0))
    w.paste(TILES[active_state], (CARD_LEFT + 1*PITCH, 0))  # slot 0 (active)
    return w
print("Building card worlds…")
WORLDS = {k: build_world(k) for k in RENDERS}
BASE_SCROLL = PITCH                       # slot 0 sits one pitch into the world

# ── helpers ───────────────────────────────────────────────────────────────────
def lerp(a, b, t):  return a + (b - a) * max(0.0, min(1.0, t))
def ease(t):        t = max(0,min(1,t)); return t*t*(3-2*t)
def ease_out(t):    t = max(0,min(1,t)); return 1-(1-t)**3

# ── cursor ────────────────────────────────────────────────────────────────────
CURSOR_PTS = [(0,0),(0,68),(16,52),(26,79),(37,74),(26,47),(48,47)]
def draw_cursor(img, cx, cy, pressing=False):
    s = 0.88 if pressing else 1.0
    shd = Image.new("RGBA", img.size, (0,0,0,0))
    ImageDraw.Draw(shd).polygon([(cx+p[0]*s+5, cy+p[1]*s+6) for p in CURSOR_PTS], fill=(0,0,0,90))
    img.paste(Image.alpha_composite(img.convert("RGBA"), shd).convert("RGB"))
    d = ImageDraw.Draw(img)
    d.polygon([(cx+p[0]*s, cy+p[1]*s) for p in CURSOR_PTS], fill=(0,0,0), outline=(0,0,0))
    d.polygon([(cx+p[0]*s*0.84+2, cy+p[1]*s*0.84+2) for p in CURSOR_PTS], fill=(255,255,255))

# cursor key positions (screen / viewport coords, 1x → render px)
START = (S(347), S(34))
HOME  = (S(175), S(302))
SHARE = (S(373), S(303))

# ── timeline (186 frames @ 24 fps base) ──────────────────────────────────────
TOTAL = 174; FPS = 24
PAN_START = 150                          # actions occupy 0..150, pan occupies 150..end
PAN_END = TOTAL - 2                       # pan completes on the last rendered frame (≡ frame 0)
# Pan spans 150..174 = 24 base frames → 12 unique slides (faster pan = smaller file).

def get_state(f):
    state = "DEF"; cx, cy = START; press = 0.0; pan = 0

    if f < 14:                                   # idle
        cx, cy = START
    elif f < 46:                                 # glide → home
        t = ease((f-14)/32)
        cx = lerp(START[0], HOME[0], t); cy = lerp(START[1], HOME[1], t)
        if t > 0.8: state = "HOV"
    elif f < 62:                                 # hover home
        cx, cy = HOME; state = "HOV"
    elif f < 68:                                 # click home → ON
        cx, cy = HOME
        pf = f-62; press = ease(pf/3) if pf < 3 else ease(1-(pf-3)/3)
        state = "HOV" if pf < 3 else "HON"
    elif f < 84:                                 # pause
        cx, cy = HOME; state = "HON"
    elif f < 114:                                # glide → share
        t = ease((f-84)/30)
        cx = lerp(HOME[0], SHARE[0], t); cy = lerp(HOME[1], SHARE[1], t)
        state = "SHOV" if t > 0.8 else "HON"
    elif f < 130:                                # hover share (tooltip)
        cx, cy = SHARE; state = "SHOV"
    elif f < 136:                                # click share → ON
        cx, cy = SHARE
        pf = f-130; press = ease(pf/3) if pf < 3 else ease(1-(pf-3)/3)
        state = "SHOV" if pf < 3 else "SON"
    elif f < PAN_START:                          # pause (both on)
        cx, cy = SHARE; state = "SON"
    else:                                        # camera pans right to the next card
        t = ease_out((f - PAN_START) / (PAN_END - PAN_START))   # decelerate into place
        pan = int(round(PITCH * t))
        cx = lerp(SHARE[0], START[0], t); cy = lerp(SHARE[1], START[1], t)
        state = "SON"

    return state, cx, cy, press, pan

# ── render frames (thinned to 12 fps) ────────────────────────────────────────
print("Rendering frames…")
OUT_W = 1120; OUT_H = round(OUT_W * SRC_H / SRC_W)
frames = []
for f in range(0, TOTAL, 2):                 # 24 fps logic → keep every other = 12 fps
    state, cx, cy, press, pan = get_state(f)
    scroll = BASE_SCROLL + pan
    win = WORLDS[state].crop((scroll, 0, scroll + SRC_W, SRC_H))   # camera window (4x)
    draw_cursor(win, int(cx), int(cy), press > 0.12)
    frames.append(win.resize((OUT_W, OUT_H), Image.LANCZOS))
    if f % 36 == 0: print(f"  {f}/{TOTAL}")

# ── brand-safe palette (+ transparent sentinel) ──────────────────────────────
BRAND = [
    (26,26,25),(26,26,26),(255,204,0),(0,0,0),(145,115,0),
    (73,73,73),(100,100,100),(204,204,204),(71,71,71),(86,71,2),
    (255,255,255),(41,41,41),(115,115,115),(158,158,158),(17,17,17),(56,56,56),
]
SENTINEL = (255, 0, 255)
montage = Image.new("RGB", (OUT_W, OUT_H*2))
montage.paste(frames[0], (0, 0))
montage.paste(frames[len(frames)*2//3], (0, OUT_H))   # an action frame (tooltip/gold)
n_adapt = 256 - len(BRAND) - 1
adapt = montage.quantize(colors=n_adapt, method=Image.MEDIANCUT, dither=Image.NONE)
apal  = adapt.getpalette()[:3*n_adapt]
pal_bytes = []
for c in BRAND: pal_bytes += list(c)
pal_bytes += apal
pal_bytes = (pal_bytes + [0]*765)[:765]
pal_bytes += list(SENTINEL)
PAL = Image.new("P", (1,1)); PAL.putpalette(pal_bytes)
pframes = [s.quantize(palette=PAL, dither=Image.NONE) for s in frames]

# ── transparent rounded corners ──────────────────────────────────────────────
rad  = round(15 * OUT_W / SVG_W)
keep = Image.new("L", (OUT_W, OUT_H), 0)
ImageDraw.Draw(keep).rounded_rectangle([0,0,OUT_W-1,OUT_H-1], radius=rad, fill=255)
corners = keep.point(lambda v: 255 if v < 128 else 0)
print("content pixels on sentinel index:", sum(1 for p in pframes[0].getdata() if p == 255))
for pf in pframes:
    pf.paste(255, (0, 0), corners)

out = "/Users/aspa.founti/Claude/button-pan-animation.gif"
pframes[0].save(out, save_all=True, append_images=pframes[1:],
                duration=int(1000/(FPS//2)), loop=0,
                optimize=True, transparency=255, disposal=1)
print(f"\nSaved → {out}  ({OUT_W}x{OUT_H}, {len(pframes)} frames, {os.path.getsize(out)//1024} KB)")
