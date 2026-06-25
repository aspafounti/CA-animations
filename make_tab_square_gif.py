"""
Square (1:1) tab-switch animation — framed like 01-Frame 3 / 01-Frame 4.
Tabs are drawn DYNAMICALLY (baked tabs stripped) so they never shift between views
(reserved badge width) and so the hovered tab brightens before the click.
Crisp My Dashboards orbital + light-blur ExTrac thumbnails. Reference text kept.
"""
from PIL import Image, ImageDraw, ImageFont
import os

SVG_SQ = 565
SCALE = 2260 / SVG_SQ                     # 4.0
def S(v): return int(round(v * SCALE))
SQ = 2260
FRAME_BG = (26, 26, 25)

# ── content frames (baked tabs stripped) ─────────────────────────────────────
print("Loading frames…")
F3 = Image.open("/tmp/tab/sq/F3.svg.png").convert("RGB").crop((0,0,SQ,SQ))   # My Dashboards
F4 = Image.open("/tmp/tab/sq/F4.svg.png").convert("RGB").crop((0,0,SQ,SQ))   # ExTrac Curated
for im in (F3, F4):
    ImageDraw.Draw(im).rectangle([S(15), S(27), S(345), S(72)], fill=FRAME_BG)  # strip tab strip

# fix typo on the ExTrac cards: "EXTRC" → "EXTRAC" (baked vector text, so overpaint)
_HBOLD = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72, index=1)
_d4 = ImageDraw.Draw(F4)
for _tx in (S(37), S(441)):                       # card 1 + peek card title left edges
    _d4.rectangle([_tx-S(3), S(398), _tx+S(212), S(418)], fill=(41,41,41))
    _d4.text((_tx, S(414)), "EXTRAC–Dashboard 01", font=_HBOLD, anchor="ls", fill=(204,204,204))

CONTENT = {"F3": F3, "F4": F4}

# ── tab styling (matches the reference / other gifs) ─────────────────────────
US850 = "/Users/aspa.founti/Library/Fonts/UniversalSans-v1-1-0-100-20-111111121121-850.ttf"
F_LABEL = ImageFont.truetype(US850, S(12))
F_BADGE = ImageFont.truetype(US850, S(10))
SEL_BG=(41,41,41); SEL_TEXT=(204,204,204); SEL_BADGE_BG=(86,71,2); SEL_BADGE_TXT=(255,204,0)
DEF_TEXT=(115,115,115); DEF_BADGE_BG=(71,71,71); DEF_BADGE_TXT=(204,204,204)
HOV_TEXT=(158,158,158)
TAB_Y=S(38); TAB_H=S(25); TAB_R=S(6); BADGE_H=S(18); BADGE_R=S(3)
PAD_L=S(9); GAP=S(9); PAD_R=S(8); TAB_GAP=S(11); TAB_X0=S(23)
TABS=[{"label":"My Dashboards","sel_b":"8","def_b":"21"},
      {"label":"ExTrac Curated","sel_b":"12","def_b":"12"}]

def text_wh(font,s): bb=font.getbbox(s); return bb[2]-bb[0],bb[3]-bb[1],bb[0],bb[1]
def badge_w(txt): w,_,_,_=text_wh(F_BADGE,txt); return max(S(13), w+S(7))
x=TAB_X0
for t in TABS:
    lw,_,_,_=text_wh(F_LABEL,t["label"]); t["labelW"]=lw; t["tx"]=x; t["labelX"]=x+PAD_L
    t["badgeX"]=t["labelX"]+lw+GAP
    wmax=max(badge_w(t["sel_b"]),badge_w(t["def_b"]))      # reserve wider badge → no shift
    t["fullW"]=(t["badgeX"]+wmax+PAD_R)-t["tx"]
    x=t["tx"]+t["fullW"]+TAB_GAP
def tab_center(i): t=TABS[i]; return t["tx"]+t["fullW"]//2, TAB_Y+TAB_H//2

def draw_tab(draw, idx, state):
    t=TABS[idx]; bdg=t["sel_b"] if state=="selected" else t["def_b"]
    if   state=="selected": bg,tc,bbg,btc=SEL_BG,SEL_TEXT,SEL_BADGE_BG,SEL_BADGE_TXT
    elif state=="hover":    bg,tc,bbg,btc=None,HOV_TEXT,DEF_BADGE_BG,DEF_BADGE_TXT
    else:                   bg,tc,bbg,btc=None,DEF_TEXT,DEF_BADGE_BG,DEF_BADGE_TXT
    bw=badge_w(bdg)
    if bg: draw.rounded_rectangle([t["tx"],TAB_Y,t["badgeX"]+bw+PAD_R,TAB_Y+TAB_H],radius=TAB_R,fill=bg)
    lw,lh,lbx,lby=text_wh(F_LABEL,t["label"]); ly=TAB_Y+(TAB_H-lh)//2-lby
    draw.text((t["labelX"]-lbx,ly),t["label"],font=F_LABEL,fill=tc)
    bx=t["badgeX"]; by=TAB_Y+(TAB_H-BADGE_H)//2
    draw.rounded_rectangle([bx,by,bx+bw,by+BADGE_H],radius=BADGE_R,fill=bbg)
    tw,th,tbx,tby=text_wh(F_BADGE,bdg)
    draw.text((bx+(bw-tw)//2-tbx,by+(BADGE_H-th)//2-tby),bdg,font=F_BADGE,fill=btc)

# ── helpers / cursor ─────────────────────────────────────────────────────────
def lerp(a,b,t): return a+(b-a)*max(0.0,min(1.0,t))
def ease(t):     t=max(0,min(1,t)); return t*t*(3-2*t)
def ease_out(t): t=max(0,min(1,t)); return 1-(1-t)**3
CURSOR_PTS=[(0,0),(0,68),(16,52),(26,79),(37,74),(26,47),(48,47)]
def draw_cursor(img,cx,cy,press=False):
    s=0.88 if press else 1.0
    shd=Image.new("RGBA",img.size,(0,0,0,0))
    ImageDraw.Draw(shd).polygon([(cx+p[0]*s+5,cy+p[1]*s+6) for p in CURSOR_PTS],fill=(0,0,0,90))
    img.paste(Image.alpha_composite(img.convert("RGBA"),shd).convert("RGB"))
    d=ImageDraw.Draw(img)
    d.polygon([(cx+p[0]*s,cy+p[1]*s) for p in CURSOR_PTS],fill=(0,0,0),outline=(0,0,0))
    d.polygon([(cx+p[0]*s*0.84+2,cy+p[1]*s*0.84+2) for p in CURSOR_PTS],fill=(255,255,255))

START=(S(480),S(115))
EXTRAC=tab_center(1); MYDASH=tab_center(0)

# ── timeline ──────────────────────────────────────────────────────────────────
TOTAL=204; FPS=24
def get_state(f):
    content="F3"; md="selected"; ex="default"; cx,cy=START; pr=0.0
    if f<14: pass
    elif f<44:
        t=ease((f-14)/30); cx=lerp(START[0],EXTRAC[0],t); cy=lerp(START[1],EXTRAC[1],t)
        if t>0.85: ex="hover"
    elif f<58: cx,cy=EXTRAC; ex="hover"
    elif f<64:
        cx,cy=EXTRAC; pf=f-58; pr=ease(pf/3) if pf<3 else ease(1-(pf-3)/3)
        if pf<4: ex="hover"
        else: content,md,ex="F4","default","selected"
    elif f<92: cx,cy=EXTRAC; content,md,ex="F4","default","selected"
    elif f<122:
        t=ease((f-92)/30); cx=lerp(EXTRAC[0],MYDASH[0],t); cy=lerp(EXTRAC[1],MYDASH[1],t)
        content,md,ex="F4","default","selected"
        if t>0.85: md="hover"
    elif f<136: cx,cy=MYDASH; content,md,ex="F4","hover","selected"
    elif f<142:
        cx,cy=MYDASH; pf=f-136; pr=ease(pf/3) if pf<3 else ease(1-(pf-3)/3)
        if pf<4: content,md,ex="F4","hover","selected"
        else: content,md,ex="F3","selected","default"
    elif f<170: cx,cy=MYDASH; content,md,ex="F3","selected","default"
    else:
        t=ease_out((f-170)/(TOTAL-170)); cx=lerp(MYDASH[0],START[0],t); cy=lerp(MYDASH[1],START[1],t)
        content,md,ex="F3","selected","default"
    return content,md,ex,cx,cy,pr

# ── render (thinned 12 fps) ──────────────────────────────────────────────────
print("Rendering…")
OUT=900
frames=[]
for f in range(0,TOTAL,2):
    content,md,ex,cx,cy,pr=get_state(f)
    img=CONTENT[content].copy()
    d=ImageDraw.Draw(img); draw_tab(d,0,md); draw_tab(d,1,ex)
    draw_cursor(img,int(cx),int(cy),pr>0.12)
    frames.append(img.resize((OUT,OUT),Image.LANCZOS))
    if f%48==0: print(f"  {f}/{TOTAL}")

# ── palette + transparent corners ────────────────────────────────────────────
BRAND=[(26,26,25),(26,26,26),(255,204,0),(0,0,0),(145,115,0),(73,73,73),(100,100,100),
       (204,204,204),(71,71,71),(86,71,2),(255,255,255),(41,41,41),(115,115,115),
       (158,158,158),(17,17,17),(56,56,56),(74,74,74)]
SENT=(255,0,255)
montage=Image.new("RGB",(OUT,OUT*2)); montage.paste(frames[0],(0,0)); montage.paste(frames[len(frames)//2],(0,OUT))
n_adapt=256-len(BRAND)-1
adapt=montage.quantize(colors=n_adapt,method=Image.MEDIANCUT,dither=Image.NONE)
pal=[]; [pal.extend(c) for c in BRAND]; pal+=adapt.getpalette()[:3*n_adapt]
pal=(pal+[0]*765)[:765]; pal+=list(SENT)
PAL=Image.new("P",(1,1)); PAL.putpalette(pal)
pframes=[s.quantize(palette=PAL,dither=Image.NONE) for s in frames]
RAD=round(15*OUT/SVG_SQ)
keep=Image.new("L",(OUT,OUT),0); ImageDraw.Draw(keep).rounded_rectangle([0,0,OUT-1,OUT-1],radius=RAD,fill=255)
corners=keep.point(lambda v:255 if v<128 else 0)
print("sentinel collisions:", sum(1 for p in pframes[0].getdata() if p==255))
for pf in pframes: pf.paste(255,(0,0),corners)

out="/Users/aspa.founti/Claude/tab-square.gif"
pframes[0].save(out,save_all=True,append_images=pframes[1:],duration=int(1000/(FPS//2)),
                loop=0,optimize=True,transparency=255,disposal=1)
print(f"\nSaved → {out} ({OUT}x{OUT}, {len(pframes)} frames, {os.path.getsize(out)//1024} KB)")
