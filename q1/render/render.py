import sys, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SP='/tmp/claude-0/-home-user/07a9afce-4b58-51c8-8b68-e57167d38bb0/scratchpad'
import os
FD=os.environ.get('CLEFFY_FONTS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts'))
OUT='/tmp/q1out'
REPO='/home/claude/maxharris1/cleffy/public'
S=2  # supersample
W,H=1080*S,1350*S
INK=(28,25,23); RAISED=(41,37,36); PAPER=(247,245,239); PAGE=(255,255,255)
ACC=(67,56,202); ACC_INK=(79,70,229); HAND_INK=(250,204,21); HILITE=(253,224,71)
HAND_PAPER=(185,28,28); RED=(220,38,38); BLUE=(37,99,235); MUTED=(87,83,78)
def f(name,size): return ImageFont.truetype(FD+'/'+name,int(size*S))
BOD=lambda s: f('bodoni-moda/package/files/bodoni-moda-latin-600-normal.woff',s)
BODI=lambda s: f('bodoni-moda/package/files/bodoni-moda-latin-600-italic.woff',s)
BOD4=lambda s: f('bodoni-moda/package/files/bodoni-moda-latin-400-normal.woff',s)
SANS=lambda s: f('instrument-sans/package/files/instrument-sans-latin-400-normal.woff',s)
SANSM=lambda s: f('instrument-sans/package/files/instrument-sans-latin-500-normal.woff',s)
SANSB=lambda s: f('instrument-sans/package/files/instrument-sans-latin-600-normal.woff',s)
HAND=lambda s: f('caveat/package/files/caveat-latin-600-normal.woff',s)
def P(v): return int(v*S)

def staves(d, top, color, groups=2, gap=12, x0=0, x1=1080):
    # groups of 5 faint lines
    for g in range(groups):
        y=top+g*140
        for i in range(5):
            yy=P(y+i*gap); d.line([(P(x0),yy),(P(x1),yy)],fill=color,width=max(1,S))
def full_staves(d,color,gap=13,band=200,start=60,h=1350):
    y=start
    while y<h:
        for i in range(5):
            yy=P(y+i*gap); d.line([(0,yy),(W,yy)],fill=color,width=max(1,S))
        y+=band
def base(bg):
    im=Image.new('RGB',(W,H),bg); return im, ImageDraw.Draw(im)
def text(d,xy,s,font,fill,anchor='la',spacing=0):
    d.text((P(xy[0]),P(xy[1])),s,font=font,fill=fill,anchor=anchor)
def tw(d,s,font): b=d.textbbox((0,0),s,font=font); return (b[2]-b[0])/S
def wordmark(d,x,y,color,size=34):
    text(d,(x,y),'Cleffy',BOD(size),color)
def rule(d,x,y,w,color,th=2): d.rectangle([P(x),P(y),P(x+w),P(y+th)],fill=color)
def ellipse_mark(d,box,color,width=6,rot=0,gap=0.0):
    (x0,y0,x1,y1)=box; cx=(x0+x1)/2; cy=(y0+y1)/2; rx=(x1-x0)/2; ry=(y1-y0)/2
    pts=[]; n=200
    for i in range(int(n*(1.0-gap))+8):
        t=2*math.pi*i/n - 0.6
        wob=1+0.03*math.sin(3*t)
        x=rx*math.cos(t)*wob; yv=ry*math.sin(t)*wob
        a=math.radians(rot)
        pts.append((P(cx+x*math.cos(a)-yv*math.sin(a)),P(cy+x*math.sin(a)+yv*math.cos(a))))
    d.line(pts,fill=color,width=P(width),joint='curve')
def arc_mark(d,p0,p1,h,color,width=5):
    pts=[]
    for i in range(101):
        t=i/100; x=p0[0]+(p1[0]-p0[0])*t; y=p0[1]+(p1[1]-p0[1])*t - h*4*t*(1-t)
        pts.append((P(x),P(y)))
    d.line(pts,fill=color,width=P(width),joint='curve')
def chip(d,x,y,initials,name,color,on_ink=False):
    r=22; d.ellipse([P(x),P(y),P(x+2*r),P(y+2*r)],fill=color)
    text(d,(x+r,y+r),initials,SANSB(16),(255,255,255),anchor='mm')
    nx=x+2*r+8; w=tw(d,name,SANSM(18))+24
    d.rounded_rectangle([P(nx),P(y+6),P(nx+w),P(y+2*r-6)],radius=P(16),fill=(255,255,255) if not on_ink else RAISED, outline=(230,228,222) if not on_ink else None)
    text(d,(nx+12,y+r),name,SANSM(18),INK if not on_ink else PAPER,anchor='lm')
def save(im,name):
    im=im.resize((1080,1350),Image.LANCZOS); im.save(OUT+'/'+name,quality=95); print('saved',name)
def score_card(im,box,crop=None,shadow=True):
    x0,y0,x1,y1=box
    sc=Image.open(REPO+'/marketing/fur-elise-opening.png').convert('RGB')
    if crop: sc=sc.crop(crop)
    pad=36; iw=P(x1-x0-2*pad); ih=int(sc.height*iw/sc.width)
    y1=y0+ih/S+2*pad
    if shadow:
        sh=Image.new('RGBA',im.size,(0,0,0,0)); sd=ImageDraw.Draw(sh)
        sd.rounded_rectangle([P(x0),P(y0+14),P(x1),P(y1+14)],radius=P(10),fill=(28,25,23,70))
        sh=sh.filter(ImageFilter.GaussianBlur(P(22))); im.paste(sh,(0,0),sh)
    d=ImageDraw.Draw(im)
    d.rounded_rectangle([P(x0),P(y0),P(x1),P(y1)],radius=P(10),fill=PAGE)
    sc=sc.resize((iw,ih),Image.LANCZOS)
    im.paste(sc,(P(x0+pad),P(y0+pad)))
    return (x0+pad,y0+pad,(x1-x0-2*pad),ih/S)

# ---------- Post 1: Google Docs for sheet music (ink) ----------
def post1():
    im,d=base(INK); full_staves(d,(52,48,46))
    wordmark(d,96,90,PAPER,36)
    text(d,(96,420),'Sheet music',BOD(112),PAPER)
    text(d,(96,548),'that syncs.',BODI(112),PAPER)
    text(d,(120,700),'(finally)',HAND(84),HAND_INK)
    rule(d,96,860,120,ACC_INK,3)
    for i,l in enumerate(['Mark up a score with your students,','live, from one link. They join in','the browser. No account needed.']):
        text(d,(96,900+i*46),l,SANS(34),(214,211,204))
    text(d,(96,1220),'cleffy.io',SANSM(30),PAPER)
    save(im,'01-sheet-music-that-syncs.jpg')

# ---------- Post 2: live marks on the score (paper + page) ----------
def post2():
    im,d=base(PAPER); full_staves(d,(232,229,221))
    wordmark(d,96,90,INK,36)
    text(d,(96,200),'You write it.',BOD(84),INK)
    text(d,(96,300),'They see it, live.',BODI(84),INK)
    sx,sy,sw,sh=score_card(im,(70,500,1010,0),crop=(0,90,730,370))
    d=ImageDraw.Draw(im)
    k=sw/730; oy=90
    ellipse_mark(d,(sx+205*k,sy+(140-oy)*k,sx+445*k,sy+(225-oy)*k),RED,width=6,rot=-3)
    arc_mark(d,(sx+500*k,sy+(150-oy)*k),(sx+690*k,sy+(150-oy)*k),40,BLUE,width=6)
    chip(d,sx+250*k,sy-80,'MT','Ms. Torres',RED)
    chip(d,sx+520*k,sy-80,'AJ','Alex',BLUE)
    text(d,(96,1080),'Every mark streams to everyone on the score',SANS(34),MUTED)
    text(d,(96,1126),'as it is drawn, not after.',SANS(34),MUTED)
    text(d,(96,1232),'Beethoven, Für Elise. Public domain.',SANS(24),(120,113,108))
    save(im,'02-you-write-they-see-live.jpg')

# ---------- Post 3: how a lesson starts (paper) ----------
def post3():
    im,d=base(PAPER); full_staves(d,(232,229,221))
    wordmark(d,96,90,INK,36)
    text(d,(96,200),'How a lesson starts',BOD(80),INK)
    rule(d,96,320,120,ACC,3)
    rows=[('A','Add a score','Upload a PDF, or search thousands of','public-domain scores in the app.'),
          ('B','Share one link','Students open it in any browser and','type a name. No accounts, no installs.'),
          ('C','Mark it up together','Ink streams live as everyone draws.','Anyone editing can erase or refine a mark.')]
    y=400
    for L,t,a,b in rows:
        d.rectangle([P(96),P(y),P(96+76),P(y+76)],outline=INK,width=P(2))
        text(d,(134,y+38),L,BOD(40),INK,anchor='mm')
        text(d,(208,y+2),t,SANSB(40),INK)
        text(d,(208,y+60),a,SANS(32),MUTED); text(d,(208,y+102),b,SANS(32),MUTED)
        y+=250
    text(d,(96,1190),'For students 13 and up.',SANS(26),(120,113,108))
    text(d,(984,1232),'cleffy.io',SANSM(30),INK,anchor='ra')
    save(im,'03-how-a-lesson-starts.jpg')

# ---------- Post 4: why I built it (ink) ----------
def post4():
    im,d=base(INK); full_staves(d,(52,48,46))
    wordmark(d,96,90,PAPER,36)
    text(d,(96,250),'Why I built',BOD(96),PAPER)
    text(d,(96,362),'Cleffy.',BODI(96),PAPER)
    rule(d,96,520,120,ACC_INK,3)
    lines=['I watched my dad’s piano teacher send','PDFs back and forth over Zoom screen','shares.','','So I built a score you share with one link.','You mark it, and the mark shows up on','your student’s copy while you draw.']
    for i,l in enumerate(lines): text(d,(96,580+i*50),l,SANS(36),(214,211,204))
    text(d,(96,1040),'Max',HAND(80),HAND_INK)
    text(d,(96,1140),'Founder. One developer in New York.',SANS(28),(168,162,158))
    save(im,'04-why-i-built-cleffy.jpg')

# ---------- Post 5: no account needed (paper, page phone-ish) ----------
def post5():
    im,d=base(PAPER); full_staves(d,(232,229,221))
    wordmark(d,96,90,INK,36)
    text(d,(96,200),'One link.',BOD(96),INK)
    text(d,(96,316),'No account.',BODI(96),INK)
    # link card
    x0,y0,x1,y1=96,520,984,760
    d.rounded_rectangle([P(x0),P(y0),P(x1),P(y1)],radius=P(14),fill=PAGE,outline=(226,223,215),width=P(2))
    text(d,(x0+40,y0+40),'JOIN THE SCORE',SANSB(22),(120,113,108))
    text(d,(x0+40,y0+82),'Für Elise · Beethoven',BOD(44),INK)
    d.rounded_rectangle([P(x0+40),P(y0+160),P(x0+560),P(y0+212)],radius=P(8),outline=(214,211,204),width=P(2),fill=PAPER)
    text(d,(x0+60,y0+186),'Your name',SANS(26),(150,144,138),anchor='lm')
    d.rounded_rectangle([P(x0+590),P(y0+160),P(x1-40),P(y0+212)],radius=P(8),fill=ACC)
    text(d,((x0+590+x1-40)/2,y0+186),'Join',SANSM(26),(255,255,255),anchor='mm')
    for i,l in enumerate(['Your student taps the link, types a name','and is on the score. Phone, laptop or','tablet. A finger or a mouse can draw.']):
        text(d,(96,840+i*48),l,SANS(34),MUTED)
    text(d,(96,1232),'cleffy.io',SANSM(30),INK)
    save(im,'05-one-link-no-account.jpg')

# ---------- Post 6: try it (ink + page) ----------
def post6():
    im,d=base(INK); full_staves(d,(52,48,46))
    wordmark(d,96,90,PAPER,36)
    text(d,(96,200),'Draw on',BOD(100),PAPER)
    text(d,(96,318),'Für Elise.',BODI(100),PAPER)
    sx,sy,sw,sh=score_card(im,(70,500,1010,0),crop=(560,118,1440,370),shadow=False)
    d=ImageDraw.Draw(im); k=sw/880; ox=560; oy=118
    ellipse_mark(d,(sx+(950-ox)*k,sy+(130-oy)*k,sx+(1190-ox)*k,sy+(225-oy)*k),HAND_PAPER,width=6,rot=2)
    text(d,(sx+(960-ox)*k,sy+sh+40),'your turn',HAND(60),HAND_INK)
    text(d,(96,1010),'Open the demo and write on the score.',SANS(36),(214,211,204))
    text(d,(96,1058),'No sign-up.',SANS(36),(214,211,204))
    d.rounded_rectangle([P(96),P(1170),P(520),P(1250)],radius=P(10),fill=ACC_INK)
    text(d,(308,1210),'cleffy.io/try',SANSM(34),(255,255,255),anchor='mm')
    save(im,'06-draw-on-fur-elise.jpg')

def avatar():
    a=Image.open(REPO+'/icons/icon-512.png').convert('RGB').resize((1080,1080),Image.LANCZOS)
    a.save(OUT+'/00-profile-picture.png'); print('saved avatar')

