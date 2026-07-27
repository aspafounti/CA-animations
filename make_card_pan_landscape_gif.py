"""
Landscape (565x465) panning card animation — the button-interaction card.
Native landscape states C1–C4 (no square re-layout needed). Mirrors the flow +
look of button-pan-square.gif EXACTLY: Show in Home (outline) → muted-gold hover
→ Remove from Home (gold filled) → Share-with-Team tooltip → team icon gold, then
a one-pitch pan that loops seamlessly. Crisp orbital thumbnail, "Dashboard 1"
title (matching the square final), subtle rounded-rect outline.
Matches the section1 standard: flat 1px grey outline, section1-size cursor
drawn at output resolution.
"""
from PIL import Image, ImageDraw, ImageFont, ImageChops
import os

SVG_W, SVG_H = 565, 465
SCALE = 2260 / SVG_W                       # 4.0
def S(v): return int(round(v * SCALE))
W, H = 2260, S(SVG_H)                       # 2260 x 1860
OUT_W, OUT_H = 900, round(SVG_H * 900 / SVG_W)   # 900 x 741
FRAME_BG = (26, 26, 25)
CARD_BG  = (41, 41, 41)
CARD_X   = S(16)
PITCH    = S(396)

print("Loading states…")
def load(nm): return Image.open(f"/tmp/landL/clean/{nm}.svg.png").convert("RGB").crop((0,0,W,H))
C1, C2, C3, C4 = load("C1"), load("C2"), load("C3"), load("C4")

# ── base = C2 (dates "22 May 26" match the square) retitled "Dashboard 1" ─────
HBOLD = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 73, index=1)
BASE = C2.copy()
_d = ImageDraw.Draw(BASE)
_d.rectangle([S(34), S(274), S(34)+S(215), S(293)], fill=CARD_BG)          # erase "Dashboard Name"
_d.text((S(38), S(289)), "Dashboard 1", font=HBOLD, anchor="ls", fill=(204,204,204))

# per-state button rows are pasted from the native renders. C1 (Show in Home) is
# exported 7svg LEFT of C2/C3/C4, so it gets a +7svg nudge to align the button and
# the card's right edge with the base (otherwise: a notch + a size-mismatch look).
TOOLTIP_R = S(418)                          # tooltip's true right edge is ~S(414.5); this clears its rounded corner
CROP = (S(24), S(336), TOOLTIP_R, S(396))  # tooltip top → button bottom, hero card width (widened to clear the tooltip's right rounded corner)
def with_row(src, dx=0):
    img = BASE.copy()
    img.paste(src.crop(CROP), (CROP[0] + dx, CROP[1]))
    return img

# muted-gold hover on the "Show in Home" button: a filled rounded-rect reaching the
# outline, with the original gold outline/text/icon composited back on top.
BTN = (S(35), S(361.5), S(342.8), S(393.2))          # Show-in-Home button outer bounds (aligned)
def hover_fill(img):
    im = img.copy()
    reg = im.crop(BTN)                                # original outline + text + icon on card bg
    R,G,B = reg.split()
    gold = ImageChops.multiply(ImageChops.multiply(
        R.point(lambda v: 255 if v > 120 else 0),
        G.point(lambda v: 255 if v > 85  else 0)),
        B.point(lambda v: 255 if v < 95  else 0))     # gold pixels only
    d = ImageDraw.Draw(im)
    # button outer corner radius ≈3svg, outline ≈1.5svg → inner corner radius ≈1.5svg
    d.rounded_rectangle([BTN[0]+S(1.5), BTN[1]+S(1.5), BTN[2]-S(1.5), BTN[3]-S(1.5)],
                        radius=S(1.5), fill=(145,115,0))  # fill up to the inside of the outline
    im.paste(reg, (BTN[0], BTN[1]), gold)             # restore gold outline/text/icon on top
    return im

DEF  = with_row(C1, dx=S(7))                          # align Show-in-Home to the base
RENDERS = {"DEF":DEF, "HOV":hover_fill(DEF), "HON":with_row(C2),
           "SHOV":with_row(C3), "SON":with_row(C4)}

# ── tiles + carousel worlds (neighbors are the DEFAULT card) ──────────────────
def tile(name): return RENDERS[name].crop((CARD_X, 0, max(CARD_X + PITCH, TOOLTIP_R), H))
TILES = {k: tile(k) for k in RENDERS}
DEFAULT_TILE = TILES["DEF"]
WORLD_W = CARD_X + 5 * PITCH
def build_world(active):
    w = Image.new("RGB", (WORLD_W, H), FRAME_BG)
    for k in (-1, 1, 2):
        w.paste(DEFAULT_TILE, (CARD_X + (k+1)*PITCH, 0))
    w.paste(TILES[active], (CARD_X + 1*PITCH, 0))
    return w
print("Building worlds…")
WORLDS = {k: build_world(k) for k in RENDERS}
BASE_SCROLL = PITCH

# ── helpers / cursor ─────────────────────────────────────────────────────────
def lerp(a,b,t): return a+(b-a)*max(0.0,min(1.0,t))
def ease(t):     t=max(0,min(1,t)); return t*t*(3-2*t)
def ease_out(t): t=max(0,min(1,t)); return 1-(1-t)**3
START = (S(347), S(34))                    # rest, above the card
HOME  = (S(168), S(377))                     # centre of the Show in Home button
SHARE = (S(373), S(377))                     # centre of the team / share icon
CURSOR_PTS=[(0,0),(0,68),(16,52),(26,79),(37,74),(26,47),(48,47)]
CS=0.62                                  # section1-matching cursor size (drawn at output scale)
def draw_cursor(img,cx,cy,press=False):
    s=CS*(0.9 if press else 1.0)
    shd=Image.new("RGBA",img.size,(0,0,0,0))
    ImageDraw.Draw(shd).polygon([(cx+p[0]*s+4,cy+p[1]*s+5) for p in CURSOR_PTS],fill=(0,0,0,90))
    img.paste(Image.alpha_composite(img.convert("RGBA"),shd).convert("RGB"))
    d=ImageDraw.Draw(img)
    d.polygon([(cx+p[0]*s,cy+p[1]*s) for p in CURSOR_PTS],fill=(0,0,0))
    d.polygon([(cx+p[0]*s*0.84+2,cy+p[1]*s*0.84+2) for p in CURSOR_PTS],fill=(255,255,255))

# ── timeline (identical to the square button-pan) ────────────────────────────
TOTAL=174; FPS=24; PAN_START=150; PAN_END=TOTAL-2
def get_state(f):
    st="DEF"; cx,cy=START; pr=0.0; pan=0
    if f<14: cx,cy=START
    elif f<46:
        t=ease((f-14)/32); cx=lerp(START[0],HOME[0],t); cy=lerp(START[1],HOME[1],t)
        # DEF while moving — hover lights up only on arrival (hold phase below)
    elif f<62: cx,cy=HOME; st="HOV"
    elif f<68:
        cx,cy=HOME; pf=f-62; pr=ease(pf/3) if pf<3 else ease(1-(pf-3)/3)
        st="HOV" if pf<3 else "HON"
    elif f<84: cx,cy=HOME; st="HON"
    elif f<114:
        t=ease((f-84)/30); cx=lerp(HOME[0],SHARE[0],t); cy=lerp(HOME[1],SHARE[1],t)
        st="HON"                                     # tooltip appears only on arrival (hold phase)
    elif f<130: cx,cy=SHARE; st="SHOV"
    elif f<136:
        cx,cy=SHARE; pf=f-130; pr=ease(pf/3) if pf<3 else ease(1-(pf-3)/3)
        st="SHOV" if pf<3 else "SON"
    elif f<PAN_START: cx,cy=SHARE; st="SON"
    else:
        t=ease_out((f-PAN_START)/(PAN_END-PAN_START))
        pan=int(round(PITCH*t)); cx=lerp(SHARE[0],START[0],t); cy=lerp(SHARE[1],START[1],t); st="SON"
    return st,cx,cy,pr,pan

# ── render frames (thinned 12 fps) ───────────────────────────────────────────
print("Rendering…")
frames=[]
RAD=round(14.5*OUT_W/SVG_W)
def add_outline(im):
    ImageDraw.Draw(im).rounded_rectangle([0,0,OUT_W-1,OUT_H-1], radius=RAD, outline=(74,74,74), width=1)
for f in range(0,TOTAL,2):
    st,cx,cy,pr,pan=get_state(f)
    win=WORLDS[st].crop((BASE_SCROLL+pan,0,BASE_SCROLL+pan+W,H))
    out=win.resize((OUT_W,OUT_H),Image.LANCZOS)
    draw_cursor(out,cx*OUT_W/W,cy*OUT_H/H,pr>0.12)   # cursor drawn at output scale, section1 size
    add_outline(out)
    frames.append(out)
    if f%36==0: print(f"  {f}/{TOTAL}")

# ── brand-safe palette + transparent corners ─────────────────────────────────
BRAND=[(26,26,25),(26,26,26),(255,204,0),(0,0,0),(145,115,0),(73,73,73),(100,100,100),
       (204,204,204),(71,71,71),(86,71,2),(255,255,255),(41,41,41),(115,115,115),
       (158,158,158),(17,17,17),(56,56,56),(74,74,74)]
SENT=(255,0,255)
montage=Image.new("RGB",(OUT_W,OUT_H*2)); montage.paste(frames[0],(0,0)); montage.paste(frames[len(frames)*2//3],(0,OUT_H))
n_adapt=256-len(BRAND)-1
adapt=montage.quantize(colors=n_adapt,method=Image.MEDIANCUT,dither=Image.NONE)
pal=[]; [pal.extend(c) for c in BRAND]; pal+=adapt.getpalette()[:3*n_adapt]
pal=(pal+[0]*765)[:765]; pal+=list(SENT)
PAL=Image.new("P",(1,1)); PAL.putpalette(pal)
pframes=[s.quantize(palette=PAL,dither=Image.NONE) for s in frames]
keep=Image.new("L",(OUT_W,OUT_H),0)
ImageDraw.Draw(keep).rounded_rectangle([0,0,OUT_W-1,OUT_H-1],radius=RAD,fill=255)
corners=keep.point(lambda v:255 if v<128 else 0)
print("sentinel collisions:", sum(1 for p in pframes[0].getdata() if p==255))
for pf in pframes: pf.paste(255,(0,0),corners)

out="/Users/aspa.founti/Claude/button-pan-landscape.gif"
pframes[0].save(out,save_all=True,append_images=pframes[1:],duration=int(1000/(FPS//2)),
                loop=0,optimize=True,transparency=255,disposal=1)
print(f"\nSaved → {out} ({OUT_W}x{OUT_H}, {len(pframes)} frames, {os.path.getsize(out)//1024} KB)")
