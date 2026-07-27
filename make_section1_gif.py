"""
section1 — menu -> tabs -> tab switch -> morph back, looping.
Combines the menu (Home/Libraries/Alerts) and the dashboard tabs into one story:
click Libraries, the menu items swoop out, the tabs view pushes in (tab bar + card as
separate staggered pieces), My Dashboards <-> ExTrac switch, then it reverses back to loop.
One motion language: accelerate out, brake in, staggered, no crossfade. Holds between beats.
Static grey frame outline (half weight). Real frames, cursor-free, EXTRC->EXTRAC fixed.
Click bounce scoped to the Libraries row only (Home/Alerts unaffected); cursor drifts
smoothly from Libraries to rest as the tabs push in, no jump-cut at the handoff.
"""
from PIL import Image, ImageDraw, ImageFont
import re, subprocess, os, math

SVG_W, SVG_H = 565, 465
OUT_W, OUT_H = 900, 741
SC = OUT_W / SVG_W                      # 1.5929  (svg -> output px)
def S(v): return v * SC
FRAME_BG = (26, 26, 25)
WORK = "/tmp/sec1gif"; os.makedirs(WORK, exist_ok=True)

# ── render + clean the 5 source frames at OUT resolution ─────────────────────
CURSOR = re.compile(r'<g filter="url\(#filter\d+_d_[^)]*\)">\s*<path d="[^"]*" fill="white"/>\s*<path d="[^"]*" fill="black"/>\s*</g>')
BORDER = re.compile(r'(<path\s+d="M15 0\.5H550[^"]*")\s+stroke="[^"]*"')   # tab frame outline
SRC = {'S1':'/Users/aspa.founti/Desktop/Menu animation/Step1.svg',
       'S2':'/Users/aspa.founti/Desktop/Menu animation/Step2.svg',
       'S3':'/Users/aspa.founti/Desktop/Menu animation/Step3.svg',
       'T1':'/Users/aspa.founti/Desktop/Tabs animation/Landscape gifs/01-Tab Animation.svg',
       'T2':'/Users/aspa.founti/Desktop/Tabs animation/Landscape gifs/02-Tab Animation.svg'}
HBOLD = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 73, index=1)

def hardcorners(im):                    # kill white corners (thumbnailer bg) -> flat dark
    W,H=im.size; d=ImageDraw.Draw(im); C=30
    for b in [(0,0,C,C),(W-C,0,W,C),(0,H-C,C,H),(W-C,H-C,W,H)]: d.rectangle(b,fill=FRAME_BG)

print("Rendering source frames…")
FR={}
for k,p in SRC.items():
    txt=open(p).read(); txt=CURSOR.sub("",txt); txt=BORDER.sub(r'\1',txt)
    sp=f"{WORK}/{k}.svg"; open(sp,"w").write(txt)
    subprocess.run(["qlmanage","-t","-s","2260","-o",WORK,sp],capture_output=True)
    big=Image.open(f"{WORK}/{k}.svg.png").convert("RGB").crop((0,0,2260,1860))
    if k=="T2":                          # EXTRC -> EXTRAC on both card titles (hero + peek), at 2260
        B=2260/565
        d=ImageDraw.Draw(big)
        f=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",int(20*B),index=1)
        d.rectangle([int(36*B),int(299*B),int((36+215)*B),int(318*B)],fill=big.getpixel((int(200*B),int(326*B))))
        d.text((int(38*B),int(314*B)),"EXTRAC–Dashboard 01",font=f,anchor="ls",fill=(228,228,224))
        d.rectangle([int(440*B),int(299*B),2260,int(318*B)],fill=big.getpixel((int(500*B),int(326*B))))
        d.text((int(442*B),int(314*B)),"EXTRAC–Dashboard 01",font=f,anchor="ls",fill=(228,228,224))
    im=big.resize((OUT_W,OUT_H),Image.LANCZOS); hardcorners(im); FR[k]=im

# ── slices ───────────────────────────────────────────────────────────────────
BANDS=[(round(S(118)),round(S(190))),(round(S(190)),round(S(289))),(round(S(289)),round(S(352)))]
def bands(img): return [img.crop((0,y0,OUT_W,y1)) for (y0,y1) in BANDS]
MB={k:bands(FR[k]) for k in ('S1','S2','S3')}
BARCUT=round(S(75))
def strips(img): return (img.crop((0,0,OUT_W,BARCUT)), img.crop((0,BARCUT,OUT_W,OUT_H)))
TB={k:strips(FR[k]) for k in ('T1','T2')}

# ── easings / helpers ────────────────────────────────────────────────────────
def clamp(x,a=0,b=1): return max(a,min(b,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def seg(lt,a,b): return clamp((lt-a)/(b-a))
def eOut(t): return 1-(1-clamp(t))**3
def eIn(t):  return clamp(t)**3
CURSOR_PTS=[(0,0),(0,68),(16,52),(26,79),(37,74),(26,47),(48,47)]
CS=0.62
def scale_center(img,sc):               # press bounce: scale a band about its own centre
    if sc>=0.999: return img
    w,h=img.size; nw,nh=max(1,round(w*sc)),max(1,round(h*sc))
    resized=img.resize((nw,nh),Image.LANCZOS)
    canvas=Image.new("RGB",(w,h),FRAME_BG)
    canvas.paste(resized,((w-nw)//2,(h-nh)//2))
    return canvas
def draw_cursor(img,cx,cy,press=False):
    s=CS*(0.9 if press else 1.0)
    shd=Image.new("RGBA",img.size,(0,0,0,0))
    ImageDraw.Draw(shd).polygon([(cx+p[0]*s+4,cy+p[1]*s+5) for p in CURSOR_PTS],fill=(0,0,0,90))
    img.paste(Image.alpha_composite(img.convert("RGBA"),shd).convert("RGB"))
    d=ImageDraw.Draw(img)
    d.polygon([(cx+p[0]*s,cy+p[1]*s) for p in CURSOR_PTS],fill=(0,0,0))
    d.polygon([(cx+p[0]*s*0.84+2,cy+p[1]*s*0.84+2) for p in CURSOR_PTS],fill=(255,255,255))

# positions (output px)
REST=(round(S(518)),round(S(42))); LIB=(round(S(249)),round(S(228))); EXTAB=(round(S(249)),round(S(48)))
OFFL=-OUT_W-120; OFFR=OUT_W+120

def compose(menu_key, menu_offs, tab_key, bar_off, card_off, tip, press, press_scale=1.0):
    cv=Image.new("RGB",(OUT_W,OUT_H),FRAME_BG)
    mb=MB[menu_key]
    for i,(y0,y1) in enumerate(BANDS):
        band=scale_center(mb[i],press_scale) if i==1 else mb[i]     # Libraries row (i==1) only
        cv.paste(band,(round(menu_offs[i]),y0))
    bar,card=TB[tab_key]
    cv.paste(bar,(round(bar_off),0)); cv.paste(card,(round(card_off),BARCUT))
    draw_cursor(cv,tip[0],tip[1],press)
    return cv

def menu_offs(base):                      # per-row stagger (lower rows lead)
    return [base+base*0.16*(i-1) for i in range(3)]

# ── timeline (seconds, preferred pace ~1.17x) ────────────────────────────────
T=dict(rest=0.82,glide=1.76,hover=2.40,press=2.60,selHold=3.39,trans=4.45,
       tabsHold=5.50,toEx=5.97,sw=6.52,exHold=8.43,back=9.48,end=10.24)
FPS=12; TOTAL=round(T['end']*FPS)

def state(lt):
    if lt<T['rest']:  return ('S1',menu_offs(0),'T1',OFFR,OFFR,REST,False,1.0)
    if lt<T['glide']:
        t=eOut(seg(lt,T['rest'],T['glide'])); tip=(lerp(REST[0],LIB[0],t),lerp(REST[1],LIB[1],t))
        mk='S2' if seg(lt,T['glide']-0.34,T['glide']-0.14)>0.5 else 'S1'
        return (mk,menu_offs(0),'T1',OFFR,OFFR,tip,False,1.0)
    if lt<T['hover']: return ('S2',menu_offs(0),'T1',OFFR,OFFR,LIB,False,1.0)
    if lt<T['press']:
        psc=1-0.03*math.sin(math.pi*seg(lt,T['hover'],T['press']))    # press bounce: Libraries row only
        return ('S3',menu_offs(0),'T1',OFFR,OFFR,LIB,True,psc)
    if lt<T['selHold']: return ('S3',menu_offs(0),'T1',OFFR,OFFR,LIB,False,1.0)
    if lt<T['trans']:                                     # menu out (accel) + tabs in (brake), staggered
        p=seg(lt,T['selHold'],T['trans'])
        ct=eOut(seg(p,0.35,1.0))                          # cursor lingers, then lifts and drifts to rest (no jump-cut)
        tip=(lerp(LIB[0],REST[0],ct),lerp(LIB[1],REST[1],ct))
        return ('S3',menu_offs(OFFL*eIn(seg(p,0,0.62))),'T1',
                lerp(OFFR,0,eOut(seg(p,0.28,0.92))), lerp(OFFR,0,eOut(seg(p,0.42,1.0))), tip,False,1.0)
    if lt<T['toEx']:  return ('S3',menu_offs(OFFL),'T1',0,0,REST,False,1.0)
    if lt<T['sw']:
        t=eOut(seg(lt,T['toEx'],T['sw'])); return ('S3',menu_offs(OFFL),'T1',0,0,(lerp(REST[0],EXTAB[0],t),lerp(REST[1],EXTAB[1],t)),False,1.0)
    if lt<T['exHold']:                                    # tab switch (snap) + brief press
        on=lt>T['sw']+0.10; return ('S3',menu_offs(OFFL),'T2' if on else 'T1',0,0,EXTAB,(lt-T['sw'])<0.12,1.0)
    if lt<T['back']:                                      # tabs out (accel) + menu in (brake)
        p=seg(lt,T['exHold'],T['back'])
        return ('S1',menu_offs(lerp(OFFL,0,eOut(seg(p,0.34,1.0)))),'T2',
                lerp(0,OFFR,eIn(seg(p,0.10,0.72))), lerp(0,OFFR,eIn(seg(p,0,0.62))), REST,False,1.0)
    return ('S1',menu_offs(0),'T1',OFFR,OFFR,REST,False,1.0)

# ── grey static outline (half weight = 1px) ──────────────────────────────────
RAD=16
def add_outline(im):
    ImageDraw.Draw(im).rounded_rectangle([0,0,OUT_W-1,OUT_H-1],radius=RAD,outline=(74,74,74),width=1)

# ── render frames ────────────────────────────────────────────────────────────
print(f"Rendering {TOTAL} frames…")
frames=[]
for f in range(TOTAL):
    lt=f/FPS
    im=compose(*state(lt)); add_outline(im); frames.append(im)
    if f%40==0: print(f"  {f}/{TOTAL}")

# ── brand palette + transparent rounded corners ──────────────────────────────
BRAND=[(26,26,25),(158,158,158),(242,242,240),(255,204,0),(38,32,3),(171,171,167),
       (60,60,59),(52,52,51),(0,0,0),(255,255,255),(74,74,74),(90,90,89),(45,45,44),
       (120,120,119),(204,204,204),(115,115,111),(140,140,136),(41,41,39),(86,71,2)]
SENT=(255,0,255)
montage=Image.new("RGB",(OUT_W,OUT_H*2)); montage.paste(frames[0],(0,0)); montage.paste(frames[TOTAL*60//100],(0,OUT_H))
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

out="/Users/aspa.founti/Claude/section1.gif"
pframes[0].save(out,save_all=True,append_images=pframes[1:],duration=int(1000/FPS),
                loop=0,optimize=True,transparency=255,disposal=1)
print(f"\nSaved -> {out} ({OUT_W}x{OUT_H}, {len(pframes)} frames, {os.path.getsize(out)//1024} KB)")
