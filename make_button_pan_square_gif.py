"""
Square (1:1) panning card animation — framed like sq.svg:
card lower-left with the next card peeking right, cursor space above, and a subtle
outline around the rounded square. Same toggle flow + seamless pan loop.

Source: /tmp/btn/sq/F*.svg.png — the landscape states re-laid-out into a 565² square
(content offset (-7,+110.5), full card top, no clip). Title retitled to "Dashboard 1".
"""
from PIL import Image, ImageDraw, ImageFont
import os

SVG_SQ = 565
SCALE  = 2248 / SVG_SQ                    # render scale (≈3.9787)
def S(v): return int(round(v * SCALE))

SQ      = 2248                            # square render side (4x)
FRAME_BG = (26, 26, 25)
PITCH    = S(396)
CARD_X   = S(16)                          # hero card left edge (screen, at pan=0)

# ── base = transformed F1 (the only square render that's filter-clean); the
#    toggled states' transformed renders had a filter flood, so instead paste the
#    button rows from the clean LANDSCAPE renders (same scale, offset by -7,+110.5).
print("Loading square base + pasting button states…")
HBOLD = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 73, index=1)
SQ_BASE = Image.open("/tmp/btn/sq/F1.svg.png").convert("RGB").crop((0,0,SQ,SQ))
_d = ImageDraw.Draw(SQ_BASE)
_d.rectangle([517, 1242, 719, 1310], fill=(41,41,41))              # "Name" → "1"
_d.text((520, 1303), "1", font=HBOLD, anchor="ls", fill=(204,204,204))

DX, DY = S(-7), S(110.5)
CROP = (S(28), S(262), S(415), S(328))                              # button row + tooltip
def with_buttons(land_name):
    img = SQ_BASE.copy()
    land = Image.open(f"/tmp/btn/clean/{land_name}.svg.png").convert("RGB")
    img.paste(land.crop(CROP), (CROP[0]+DX, CROP[1]+DY))
    return img
RENDERS = {"DEF":SQ_BASE, "HOV":with_buttons("F1_hover"), "HON":with_buttons("F2"),
           "SHOV":with_buttons("F3"), "SON":with_buttons("F4")}

# ── card tiles + carousel worlds ─────────────────────────────────────────────
def tile(name): return RENDERS[name].crop((CARD_X, 0, CARD_X + PITCH, SQ))
TILES = {k: tile(k) for k in RENDERS}
DEFAULT_TILE = TILES["DEF"]
WORLD_W = CARD_X + 5 * PITCH
def build_world(active):
    w = Image.new("RGB", (WORLD_W, SQ), FRAME_BG)
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
START = (S(347), S(34))                   # rest, in the space above the card
HOME  = (S(168), S(412.5))                # card buttons (translated -7,+110.5)
SHARE = (S(366), S(413.5))
CURSOR_PTS=[(0,0),(0,68),(16,52),(26,79),(37,74),(26,47),(48,47)]
def draw_cursor(img,cx,cy,press=False):
    s=0.88 if press else 1.0
    shd=Image.new("RGBA",img.size,(0,0,0,0))
    ImageDraw.Draw(shd).polygon([(cx+p[0]*s+5,cy+p[1]*s+6) for p in CURSOR_PTS],fill=(0,0,0,90))
    img.paste(Image.alpha_composite(img.convert("RGBA"),shd).convert("RGB"))
    d=ImageDraw.Draw(img)
    d.polygon([(cx+p[0]*s,cy+p[1]*s) for p in CURSOR_PTS],fill=(0,0,0),outline=(0,0,0))
    d.polygon([(cx+p[0]*s*0.84+2,cy+p[1]*s*0.84+2) for p in CURSOR_PTS],fill=(255,255,255))

# ── timeline ──────────────────────────────────────────────────────────────────
TOTAL=174; FPS=24; PAN_START=150; PAN_END=TOTAL-2
def get_state(f):
    st="DEF"; cx,cy=START; pr=0.0; pan=0
    if f<14: cx,cy=START
    elif f<46:
        t=ease((f-14)/32); cx=lerp(START[0],HOME[0],t); cy=lerp(START[1],HOME[1],t)
        if t>0.82: st="HOV"
    elif f<62: cx,cy=HOME; st="HOV"
    elif f<68:
        cx,cy=HOME; pf=f-62; pr=ease(pf/3) if pf<3 else ease(1-(pf-3)/3)
        st="HOV" if pf<3 else "HON"
    elif f<84: cx,cy=HOME; st="HON"
    elif f<114:
        t=ease((f-84)/30); cx=lerp(HOME[0],SHARE[0],t); cy=lerp(HOME[1],SHARE[1],t)
        st="SHOV" if t>0.82 else "HON"
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
OUT=900
frames=[]
for f in range(0,TOTAL,2):
    st,cx,cy,pr,pan=get_state(f)
    win=WORLDS[st].crop((BASE_SCROLL+pan,0,BASE_SCROLL+pan+SQ,SQ))
    draw_cursor(win,int(cx),int(cy),pr>0.12)
    frames.append(win.resize((OUT,OUT),Image.LANCZOS))
    if f%36==0: print(f"  {f}/{TOTAL}")

# ── outline (subtle rounded-rect stroke at the square edge) ──────────────────
RAD=round(15*OUT/SVG_SQ)
for fr in frames:
    ImageDraw.Draw(fr).rounded_rectangle([1,1,OUT-2,OUT-2], radius=RAD-1,
                                         outline=(74,74,74), width=2)

# ── brand-safe palette + transparent corners ─────────────────────────────────
BRAND=[(26,26,25),(26,26,26),(255,204,0),(0,0,0),(145,115,0),(73,73,73),(100,100,100),
       (204,204,204),(71,71,71),(86,71,2),(255,255,255),(41,41,41),(115,115,115),
       (158,158,158),(17,17,17),(56,56,56),(74,74,74)]
SENT=(255,0,255)
montage=Image.new("RGB",(OUT,OUT*2)); montage.paste(frames[0],(0,0)); montage.paste(frames[len(frames)*2//3],(0,OUT))
n_adapt=256-len(BRAND)-1
adapt=montage.quantize(colors=n_adapt,method=Image.MEDIANCUT,dither=Image.NONE)
pal=[]; [pal.extend(c) for c in BRAND]; pal+=adapt.getpalette()[:3*n_adapt]
pal=(pal+[0]*765)[:765]; pal+=list(SENT)
PAL=Image.new("P",(1,1)); PAL.putpalette(pal)
pframes=[s.quantize(palette=PAL,dither=Image.NONE) for s in frames]
keep=Image.new("L",(OUT,OUT),0)
ImageDraw.Draw(keep).rounded_rectangle([1,1,OUT-2,OUT-2],radius=RAD-1,fill=255)  # clip to the outline → no content leaks past the border
corners=keep.point(lambda v:255 if v<128 else 0)
print("sentinel collisions:", sum(1 for p in pframes[0].getdata() if p==255))
for pf in pframes: pf.paste(255,(0,0),corners)

out="/Users/aspa.founti/Claude/button-pan-square.gif"
pframes[0].save(out,save_all=True,append_images=pframes[1:],duration=int(1000/(FPS//2)),
                loop=0,optimize=True,transparency=255,disposal=1)
print(f"\nSaved → {out} ({OUT}x{OUT}, {len(pframes)} frames, {os.path.getsize(out)//1024} KB)")
