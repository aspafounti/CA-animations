"""
"tabs" animation v2 — tab-bar interaction sequence (03-Frame 1..6).

Flow: idle (DB1 active) -> hover caret -> click (caret PRESSED, dropdown opens with
DB1 selected/gold) -> cursor glides down the list, each row lighting to hover as it
passes -> lands on Dashboard 10 -> click -> DB10 appears as a temp tab after the
divider with a little jump -> hover Dashboard 1 -> reset. Loops seamlessly.

Square + gradient outline + transparent corners + animated cursor.
"""
from PIL import Image, ImageDraw, ImageChops
import os, math

CLEAN = "/tmp/tabs4/clean"
SVG_SQ = 565
SCALE  = 2260 / SVG_SQ                       # 4.0
def S(v): return int(round(v * SCALE))
SQ = 2260
OUT = 900
FRAME_BG = (26, 26, 25)

print("Loading clean states…")
ST = {n: Image.open(f"{CLEAN}/S{n}.svg.png").convert("RGB").crop((0, 0, SQ, SQ))
      for n in range(1, 7)}

# ── final-layout fixups: show full "Dashboard 10" in the temp tab (design
#    truncates it to "Dashboard…") and remove the "+" button entirely ─────────
def _db10_gold_stamp():
    src = ST[3].crop((S(54), S(415), S(133), S(430))).convert("L")   # dropdown "Dashboard 10" (gray)
    alpha = src.point(lambda v: max(0, min(255, int((v - 37) * 255 / 116))))
    stamp = Image.new("RGBA", src.size, (255, 204, 0, 0)); stamp.putalpha(alpha)
    return stamp
DB10_STAMP = _db10_gold_stamp()

TAB_BG = (41, 41, 39)                                                # #292927 active tab
EXT = 26                                                             # widen DB10 to DB3's right edge (506 -> 532)
def fix_final(img):
    d = ImageDraw.Draw(img)
    d.rectangle((S(393), S(184), S(472), S(206)), fill=TAB_BG)       # erase "Dashboard…"
    rgba = img.convert("RGBA")
    rgba.alpha_composite(DB10_STAMP, (S(396.667), S(188.059)))       # stamp gold "Dashboard 10"
    img.paste(rgba.convert("RGB"))
    d = ImageDraw.Draw(img)
    d.rectangle((S(510), S(172), S(545), S(238)), fill=FRAME_BG)     # remove "+"
    # widen the DB10 tab so its right edge + "•••" align with Dashboard 3
    edge = img.crop((S(500), S(177), S(508), S(211)))               # right edge + rounded corner
    dots = img.crop((S(477), S(189), S(497), S(201)))               # "•••" cluster
    d.rectangle((S(477), S(189), S(497), S(201)), fill=TAB_BG)       # clear old dots
    d.rectangle((S(503), S(180), S(529), S(210)), fill=TAB_BG)       # fill the extension
    img.paste(edge, (S(500 + EXT), S(177)))                         # slide edge/corner +26
    img.paste(dots, (S(477 + EXT), S(189)))                         # slide "•••" +26

for _n in (5, 6):
    fix_final(ST[_n])

# ── colour-key recolour (vectorised via point/chops) ─────────────────────────
def near(ch, v, tol): return ch.point(lambda p: 255 if abs(p - v) <= tol else 0)
def color_mask(img, color, tol):
    r, g, b = img.split()
    return ImageChops.multiply(ImageChops.multiply(near(r, color[0], tol),
                                                    near(g, color[1], tol)),
                               near(b, color[2], tol))
def recolor(img, box, src, dst, tol):
    """Within box, repaint pixels ~=src to dst (preserves text/handles)."""
    x0, y0, x1, y1 = box
    crop = img.crop((x0, y0, x1, y1))
    m = color_mask(crop, src, tol)
    crop.paste(dst, (0, 0), m)
    img.paste(crop, (x0, y0))

DEF_BG   = (38, 38, 38)     # default dropdown row
HOVER_BG = (56, 56, 53)     # hovered dropdown row

# dropdown region + row boundaries (1x SVG)
DD_X0, DD_X1 = 26, 249
ROW_Y = [218.941, 248.941, 278.941, 310.941, 342.941, 374.941, 406.941, 438.941, 470.941]
# rows: 0 DB1(gold-sel) 1 DB2 2 DB3 3 DB4 4 DB5 5 DB6 6 DB10 7 DB8

# ── build dropdown-open base (caret PRESSED, DB1 gold, no hover) ──────────────
print("Building dropdown base…")
DD_BOX = (S(DD_X0), S(ROW_Y[0]), S(DD_X1), S(ROW_Y[-1]))
clean_base = ST[3].copy()
recolor(clean_base, DD_BOX, HOVER_BG, DEF_BG, tol=14)   # neutralise baked DB2 hover

def row_box(i):
    return (S(DD_X0) + 2, S(ROW_Y[i]) + 3, S(DD_X1) - 2, S(ROW_Y[i + 1]) - 3)

HOVER_VAR = {}                                          # row idx -> dropdown img with that row hovered
for i in range(0, 7):                                   # DB1..DB10
    v = clean_base.copy()
    recolor(v, row_box(i), DEF_BG, HOVER_BG, tol=6)
    HOVER_VAR[i] = v

def dropdown_for_tip(tip_y):
    """Return dropdown image with the row under the cursor tip hovered."""
    for i in range(7):
        if ROW_Y[i] <= tip_y < ROW_Y[i + 1]:
            return HOVER_VAR[i]
    return clean_base

# ── temp-tab appears with a drop-in + fade (matches the platform recording:
#    new tab enters ~8px high and eases down into its slot while fading in) ────
def blend(a, b, t):
    return Image.blend(a, b, max(0.0, min(1.0, t)))

DB10_BOX = (S(385), S(174), S(536), S(238))          # DB10 active tab only (widened)
db10_spr = ST[5].crop(DB10_BOX)                      # the tab that drops in
base_no10 = ST[5].copy()                             # final layout minus that tab
ImageDraw.Draw(base_no10).rectangle(DB10_BOX, fill=FRAME_BG)

def _eo(t):  t = max(0, min(1, t)); return 1 - (1 - t) ** 3   # cubic ease-out
def _eo2(t): t = max(0, min(1, t)); return 1 - (1 - t) ** 2   # quad  ease-out (gentler settle)

def appear(t):
    """t in 0..1 — temp tab becomes visible fast, then eases DOWN into its slot
    (mirrors the recording: tab is already gold while it drops ~9px and settles)."""
    bg = blend(HOVER_VAR[6], base_no10, _eo(min(1.0, t / 0.4)))    # dropdown -> final(minus tab)
    fade = min(1.0, t / 0.15)                                      # near-instant: visible while dropping
    drop = int(S(9) * (1 - _eo2(t)))                               # gradual settle, stays visible
    spr = db10_spr.convert("RGBA"); spr.putalpha(int(255 * fade))
    out = bg.convert("RGBA"); out.alpha_composite(spr, (DB10_BOX[0], DB10_BOX[1] - drop))
    return out.convert("RGB")

# ── cursor ───────────────────────────────────────────────────────────────────
def lerp(a, b, t): return a + (b - a) * max(0.0, min(1.0, t))
def ease(t):     t = max(0, min(1, t)); return t * t * (3 - 2 * t)
def ease_out(t): t = max(0, min(1, t)); return 1 - (1 - t) ** 3
CURSOR_PTS = [(0, 0), (0, 68), (16, 52), (26, 79), (37, 74), (26, 47), (48, 47)]
def draw_cursor(img, cx, cy, press=False):
    s = 0.9 if press else 1.0
    shd = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shd).polygon([(cx + p[0] * s + 5, cy + p[1] * s + 6) for p in CURSOR_PTS], fill=(0, 0, 0, 90))
    img.paste(Image.alpha_composite(img.convert("RGBA"), shd).convert("RGB"))
    d = ImageDraw.Draw(img)
    d.polygon([(cx + p[0] * s, cy + p[1] * s) for p in CURSOR_PTS], fill=(0, 0, 0), outline=(0, 0, 0))
    d.polygon([(cx + p[0] * s * 0.84 + 2, cy + p[1] * s * 0.84 + 2) for p in CURSOR_PTS], fill=(255, 255, 255))

# key cursor tips (1x SVG)
REST   = (333.4, 396.0)
CARET  = (42.0, 192.0)
DD_TOP = (169.0, 233.9)      # entering dropdown, over DB1
DB10_D = (179.0, 422.9)      # DB10 in dropdown
DB1_TB = (165.0, 197.7)      # DB1 tab (final layout)

# ── timeline: quick decisive moves + clear holds so each step registers ──────
#   phase end-frames @24fps (walkthrough pace, ~7.3s loop)
IDLE1    = 10     # idle
TO_CARET = 26     # move REST -> caret (quick)
HOVER_C  = 40     # HOLD hover caret
CLICK_C  = 45     # click, dropdown opens
ENTER    = 54     # cursor caret -> dropdown top
HOLD_TOP = 62     # HOLD: dropdown open, DB1 selected
GLIDE    = 100    # glide down through rows to DB10
DWELL10  = 112    # HOLD hover DB10
CLICK10  = 117    # click DB10
APPEAR   = 133    # temp tab drops in
SETTLE   = 146    # HOLD final layout, cursor rises to DB1
HOVER1   = 158    # HOLD hover DB1 tab
RESET    = 168    # reset -> rest
TOTAL, FPS = 176, 24
def state(f):
    """return (image, cursor_tip_1x, press)"""
    if f < IDLE1:                                                # idle
        return ST[1], REST, False
    if f < TO_CARET:                                             # REST -> caret (decisive)
        t = ease_out((f - IDLE1) / (TO_CARET - IDLE1))
        img = ST[1] if t < 0.7 else ST[2]
        return img, (lerp(REST[0], CARET[0], t), lerp(REST[1], CARET[1], t)), False
    if f < HOVER_C:                                              # HOLD hover caret
        return ST[2], CARET, False
    if f < CLICK_C:                                              # click caret -> open
        pf = f - HOVER_C
        return (ST[2] if pf < 3 else clean_base), CARET, pf < 3
    if f < ENTER:                                                # caret -> dropdown top
        t = ease_out((f - CLICK_C) / (ENTER - CLICK_C))
        tip = (lerp(CARET[0], DD_TOP[0], t), lerp(CARET[1], DD_TOP[1], t))
        return dropdown_for_tip(tip[1]), tip, False
    if f < HOLD_TOP:                                             # HOLD: dropdown open, DB1 selected
        return dropdown_for_tip(DD_TOP[1]), DD_TOP, False
    if f < GLIDE:                                                # glide down to DB10 (even pace)
        t = ease((f - HOLD_TOP) / (GLIDE - HOLD_TOP))
        tip = (lerp(DD_TOP[0], DB10_D[0], t), lerp(DD_TOP[1], DB10_D[1], t))
        return dropdown_for_tip(tip[1]), tip, False
    if f < DWELL10:                                              # HOLD hover DB10
        return dropdown_for_tip(DB10_D[1]), DB10_D, False
    if f < CLICK10:                                              # click DB10
        return dropdown_for_tip(DB10_D[1]), DB10_D, (f - DWELL10) < 3
    if f < APPEAR:                                               # temp tab drops in + fades
        t = (f - CLICK10) / (APPEAR - CLICK10)
        return appear(t), DB10_D, False
    if f < SETTLE:                                               # HOLD final; cursor rises to DB1 tab
        ct = ease_out((f - APPEAR) / (SETTLE - APPEAR))
        tip = (lerp(DB10_D[0], DB1_TB[0], ct), lerp(DB10_D[1], DB1_TB[1], ct))
        return ST[5], tip, False
    if f < HOVER1:                                               # HOLD hover DB1 tab
        return ST[6], DB1_TB, False
    if f < RESET:                                                # reset -> rest (cut S6->S1)
        t = ease_out((f - HOVER1) / (RESET - HOVER1))
        img = ST[6] if t < 0.5 else ST[1]
        return img, (lerp(DB1_TB[0], REST[0], t), lerp(DB1_TB[1], REST[1], t)), False
    return ST[1], REST, False                                    # idle (== frame 0)

# ── render (full 24fps for smooth cursor) ────────────────────────────────────
print("Rendering…")
frames = []
for f in range(0, TOTAL):
    img, tip, press = state(f)
    im = img.copy()
    draw_cursor(im, S(tip[0]), S(tip[1]), press)
    frames.append(im.resize((OUT, OUT), Image.LANCZOS))
    if f % 40 == 0: print(f"  {f}/{TOTAL}")

# ── palette + transparent corners ───────────────────────────────────────────
BRAND = [(26, 26, 25), (26, 26, 26), (255, 204, 0), (0, 0, 0), (228, 228, 224),
         (56, 56, 53), (71, 71, 67), (41, 41, 39), (115, 115, 111), (204, 204, 204),
         (255, 255, 255), (41, 41, 41), (56, 56, 56), (73, 73, 71), (160, 160, 156),
         (90, 90, 88), (74, 74, 74), (38, 38, 38), (86, 71, 2), (71, 71, 67),
         (153, 153, 151), (41, 41, 39)]
SENT = (255, 0, 255)
montage = Image.new("RGB", (OUT, OUT * 2))
montage.paste(frames[0], (0, 0))
montage.paste(frames[len(frames) * 45 // 100], (0, OUT))
n_adapt = 256 - len(BRAND) - 1
adapt = montage.quantize(colors=n_adapt, method=Image.MEDIANCUT, dither=Image.NONE)
pal = []; [pal.extend(c) for c in BRAND]; pal += adapt.getpalette()[:3 * n_adapt]
pal = (pal + [0] * 765)[:765]; pal += list(SENT)
PAL = Image.new("P", (1, 1)); PAL.putpalette(pal)
pframes = [s.quantize(palette=PAL, dither=Image.NONE) for s in frames]
RAD = round(15 * OUT / SVG_SQ)
keep = Image.new("L", (OUT, OUT), 0)
ImageDraw.Draw(keep).rounded_rectangle([1, 1, OUT - 2, OUT - 2], radius=RAD - 1, fill=255)
corners = keep.point(lambda v: 255 if v < 128 else 0)
for pf in pframes: pf.paste(255, (0, 0), corners)

out = "/Users/aspa.founti/Claude/tabs.gif"
pframes[0].save(out, save_all=True, append_images=pframes[1:], duration=int(1000 / FPS),
                loop=0, optimize=True, transparency=255, disposal=1)
print(f"\nSaved -> {out} ({OUT}x{OUT}, {len(pframes)} frames, {os.path.getsize(out)//1024} KB)")
