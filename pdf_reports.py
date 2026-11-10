"""Original, multi-page Swedish scouting report templates for Andrablicken.
Not a reproduction of PFSA's graphics, text, or page layouts.
"""
from io import BytesIO
from pathlib import Path
import re
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit

FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
if Path(FONT_REG).exists():
    pdfmetrics.registerFont(TTFont('ABReg', FONT_REG))
    pdfmetrics.registerFont(TTFont('ABBold', FONT_BOLD))
    REG, BOLD = 'ABReg', 'ABBold'
else:
    REG, BOLD = 'Helvetica', 'Helvetica-Bold'

DARK = HexColor('#101713'); DEEP=HexColor('#19271C'); LIME=HexColor('#d7f179')
WHITE=HexColor('#F7F8F3'); INK=HexColor('#152118'); GREY=HexColor('#667569')
LINE=HexColor('#D8E0D5'); PALE=HexColor('#F2F5EF')
PAGE_W,PAGE_H=landscape(A4)
PITCH_LENGTH_TO_WIDTH=105/68

PLAYER_FIELDS = [
 ('scout_name','Scout'), ('player_name','Spelare'),('team','Lag'),('opponent','Motståndare'),
 ('match_date','Matchdatum'),('competition','Serie/tävling'),('position','Position'),('minutes','Observerade minuter'),
 ('result','Resultat'),('venue','Arena'),('source','Videolänk / observationsmetod'),
 ('game_context','Matchbild / sammanhang'),('starting_eleven','Laguppställning och byten'),
 ('shape','Formation / roll i laget'),('in_possession','Roll med boll'),('out_possession','Roll utan boll'),
 ('technical','Teknisk analys'),('tactical','Taktisk analys'),('physical','Fysiska egenskaper'),
 ('mental','Beslutsfattande och mentala egenskaper'), ('strengths','Tydliga styrkor'),
 ('weaknesses','Utvecklingsområden / risker'),('events','Konkreta matchsituationer + minut'),
 ('rating','Samlad bedömning (1–5)'),('potential','Potential / roll på högre nivå'),
 ('recommendation','Rekommendation och nästa steg'),('confidence','Säkerhet i bedömningen / mer underlag')
]
OPP_FIELDS = [
 ('scout_name','Scout'),('team','Motståndarlag'),('opponent','Observerad motpart'),
 ('competition','Serie/tävling'),('match_date','Matchdatum'),('result','Resultat'),('venue','Arena'),('source','Videolänk / observationsmetod'),
 ('game_context','Matchbild / sammanhang'),('starting_eleven','Startelva, roller och byten'),('shape','Utgångsformation'),
 ('recent_form','Senaste resultat / sammanhang'), ('in_possession','Uppspelsmönster'),('out_possession','Försvarsorganisation'),
 ('high_press','Presspel och triggers'),('low_block','Lågt och medelhögt försvar'),('transitions_attack','Offensiva omställningar'),
 ('transitions_defense','Defensiva omställningar'),('key_players','Nyckelspelare och matchups'),('bench','Bänk / alternativ'),
 ('set_attacking','Offensiva fasta situationer'),('set_defending','Defensiva fasta situationer'),
 ('corners','Hörnor och varianter'), ('free_kicks','Frisparkar / inkast'),('attack_shape','Anfallsorganisation / ytor'),
 ('defend_shape','Försvarsorganisation / ytor'),('strengths','Motståndarens styrkor'),('weaknesses','Motståndarens svagheter'),
 ('observations','Tidsstämplade observationer'), ('recommendation','Matchplan / rekommendationer'),
 ('summary','Slutsats och tre viktigaste insikterna'),('limitations','Osäkerheter / observationsbegränsningar')
]

REPORT_SPECS = {
 'player': {'title':'SPELARRAPPORT','subtitle':'Individuell observation och spelarbedömning','pages':[
 ('MATCH & SPELARPROFIL',[('Spelare och lag','player_name','team','opponent'),('Matchinformation','match_date','competition','result','venue'),('Uppdrag och källa','scout_name','position','minutes','source')]),
 ('MATCHKONTEXT OCH LAGUPPSTÄLLNING',[('Matchbild och observation','game_context'),('Laguppställning, byten och matchhändelser','starting_eleven'),('Underlagets begränsningar','confidence')]),
 ('FORMATION OCH POSITION',[('Formation och spelarens position','shape'),('Roll och uppgifter med boll','in_possession'),('Roll och uppgifter utan boll','out_possession')]),
 ('TEKNISKA EGENSKAPER',[('Första touch, passningar, mottagning, avslut','technical'),('Matchhändelser som stöder bedömningen','events')]),
 ('TAKTISKA EGENSKAPER',[('Positionering, speluppfattning, beslut och tajming','tactical'),('Särskilda styrkor som observerats','strengths')]),
 ('FYSIK OCH MENTALITET',[('Acceleration, snabbhet, löpförmåga och duellspel','physical'),('Arbetsinsats, koncentration, beslutsfattande','mental'),('Utvecklingsområden','weaknesses')]),
 ('SAMMANFATTNING & REKOMMENDATION',[('Samlad bedömning (1–5)','rating'),('Bedömd potential och möjlig roll','potential'),('Rekommendation till klubb och nästa observation','recommendation'),('Bedömningens säkerhet','confidence')]),
 ]},
 'opposition': {'title':'MOTSTÅNDARRAPPORT','subtitle':'Matchanalys, spelmodell och matchplan','pages':[
 ('MATCHINFORMATION',[('Lag, tävling och match','team','opponent','competition','match_date','result','venue'),('Scout och videokälla','scout_name','source')]),
 ('MATCHÖVERSIKT',[('Sammanfattning av matchbilden','game_context'),('Viktiga händelser och tidsstämplar','observations')]),
 ('LAGUPPSTÄLLNING',[('Startelva, byten och roller','starting_eleven'),('Nyckelspelare','key_players')]),
 ('FORMATION & FORM',[('Utgångsformation','shape'),('Senaste resultat och kontext','recent_form'),('Viktig information','strengths')]),
 ('FORMATION ÖVER MATCHENS FASER',[('Formation med boll','attack_shape'),('Formation utan boll','defend_shape'),('Förändringar efter byten','bench')]),
 ('SPELARANALYS: STARTELVA',[('Nyckelspelare, nummer, roll och beteenden','key_players'),('Dynamik och relationer i lagdelarna','observations')]),
 ('SPELARANALYS: BÄNK & ALTERNATIV',[('Avbytare, alternativa uppställningar','bench'),('Risker och möjligheter vid byten','weaknesses')]),
 ('FASTA SITUATIONER: ANFALL',[('Offensiva hörnor och frisparkar','set_attacking'),('Hörnvarianter och löpvägar','corners')]),
 ('FASTA SITUATIONER: FÖRSVAR',[('Markering, zon, andra bollar','set_defending'),('Frisparkar och inkast','free_kicks')]),
 ('FÖRSVARSORGANISATION',[('Presshöjd, linjer och avstånd','defend_shape'),('Utlösande pressignaler','high_press'),('Lågt och medelhögt block','low_block')]),
 ('ANFALLSORGANISATION',[('Uppspel, progression och överbelastningar','attack_shape'),('Mönster och prioriterade ytor','in_possession')]),
 ('OMSTÄLLNINGSSPEL',[('Offensiva omställningar','transitions_attack'),('Defensiva omställningar','transitions_defense'),('Press och återerövring','high_press')]),
 ('STYRKOR OCH SÅRBARHETER',[('Övergripande styrkor','strengths'),('Så kan motståndaren angripas','weaknesses'),('Matchbild / balans','game_context')]),
 ('MATCHPLAN & CHECKLISTA',[('Offensiva principer mot motståndaren','recommendation'),('Hur pressar och försvarar de?','high_press'),('Vilka ytor lämnar de?','weaknesses'),('Fasta situationer att förbereda','set_defending')]),
 ('SLUTSATS',[('Tre viktigaste slutsatserna','summary'),('Rekommendationer och prioriteringar','recommendation'),('Begränsningar / behov av fler observationer','limitations')]),
 ]}
}

def _safe(v):
    return str(v or '').replace('\r',' ').strip()

def _brand(c, title, page_no, total):
    c.setFillColor(WHITE); c.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0)
    c.setFillColor(DARK); c.rect(0,PAGE_H-68,PAGE_W,68,fill=1,stroke=0)
    c.setStrokeColor(LIME); c.setLineWidth(1.4);c.line(35,PAGE_H-68,PAGE_W-35,PAGE_H-68)
    c.setStrokeColor(LIME); c.circle(53,PAGE_H-32,16,stroke=1,fill=0)
    c.setFillColor(LIME); c.setFont(BOLD,17);c.drawCentredString(53,PAGE_H-38,'A')
    c.setFillColor(WHITE);c.setFont(BOLD,14);c.drawString(83,PAGE_H-33,'ANDRABLICKEN')
    c.setFont(REG,6.5);c.setFillColor(HexColor('#B3C0B1'));c.drawString(84,PAGE_H-47,'SCOUTING NETWORK')
    c.setFont(BOLD,11);c.setFillColor(WHITE);c.drawRightString(PAGE_W-36,PAGE_H-39,title)
    c.setStrokeColor(LINE);c.line(35,35,PAGE_W-35,35)
    c.setFont(REG,7.7);c.setFillColor(GREY);c.drawString(35,23,'ANDRABLICKEN  /  INTERN SCOUTINGRAPPORT')
    c.drawRightString(PAGE_W-36,23,f'{page_no:02d} / {total:02d}')

def _cover(c, spec, report_kind, data):
    c.setFillColor(DARK);c.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0)
    # Faint pitch marking, drawn with shapes not third-party graphics.
    pitch_h=405
    pitch_w=pitch_h/PITCH_LENGTH_TO_WIDTH
    pitch_x=PAGE_W-210-pitch_w/2
    pitch_y=90
    c.setStrokeColor(HexColor('#2B4934'));c.setLineWidth(1.5)
    c.rect(pitch_x,pitch_y,pitch_w,pitch_h,fill=0,stroke=1)
    c.line(pitch_x,pitch_y+pitch_h/2,pitch_x+pitch_w,pitch_y+pitch_h/2)
    c.circle(pitch_x+pitch_w/2,pitch_y+pitch_h/2,43,fill=0,stroke=1)
    penalty_w=pitch_w*.61;penalty_h=pitch_h*.16;penalty_x=pitch_x+(pitch_w-penalty_w)/2
    c.rect(penalty_x,pitch_y,penalty_w,penalty_h,fill=0,stroke=1)
    c.rect(penalty_x,pitch_y+pitch_h-penalty_h,penalty_w,penalty_h,fill=0,stroke=1)
    c.setStrokeColor(LIME);c.setLineWidth(1.8);c.circle(58,PAGE_H-57,24,stroke=1,fill=0)
    c.setFillColor(LIME);c.setFont(BOLD,24);c.drawCentredString(58,PAGE_H-65,'A')
    c.setFillColor(WHITE);c.setFont(BOLD,22);c.drawString(96,PAGE_H-55,'ANDRABLICKEN')
    c.setFont(REG,9);c.setFillColor(HexColor('#C0CCBC'));c.drawString(98,PAGE_H-73,'SCOUTING NETWORK')
    c.setFillColor(LIME);c.rect(48,PAGE_H-178,56,6,fill=1,stroke=0)
    c.setFont(BOLD,41);c.setFillColor(WHITE)
    c.drawString(48,PAGE_H-243,spec['title'])
    c.setFont(REG,13);c.drawString(48,PAGE_H-271,spec['subtitle'])
    c.setFillColor(LIME);c.setFont(BOLD,11)
    c.drawString(48,108,'SVENSK MALL  /  VERSION 1.0')
    c.setFont(REG,10);c.setFillColor(HexColor('#B3C0B1'))
    name=_safe(data.get('player_name') or data.get('team'))
    if name:c.drawString(48,85,'Objekt: '+name[:55])
    c.drawString(48,51,'Konfidentiellt arbetsmaterial · Egen rapportstruktur')

def _field_block(c,x,top,w,h,title,keys,data,overflow,report_kind):
    y=top-h
    c.setFillColor(PALE);c.roundRect(x,y,w,h,5,stroke=0,fill=1)
    c.setFillColor(DEEP);c.roundRect(x,y+h-28,w,28,5,stroke=0,fill=1)
    c.rect(x,y+h-28,w,14,fill=1,stroke=0)
    c.setFillColor(LIME);c.rect(x+12,y+h-18,18,3,fill=1,stroke=0)
    c.setFillColor(WHITE);c.setFont(BOLD,9.4);c.drawString(x+37,y+h-19,title.upper()[:95])
    cy=y+h-44
    keys=list(keys)
    font_size=8.8
    row_h=(h-42)/max(1,len(keys))
    for idx,key in enumerate(keys):
        label=dict(PLAYER_FIELDS if report_kind=='player' else OPP_FIELDS).get(key,key)
        v=_safe(data.get(key))
        if len(keys)>1:
            # Fixed-height labelled rows, so a long field cannot overlap the next one.
            label_x=x+13; value_x=x+190; value_w=w-205
            c.setFont(BOLD,8.1);c.setFillColor(GREY)
            c.drawString(label_x,cy,label[:33])
            text_top=cy
            min_next=cy-row_h
            max_lines=max(1,int((row_h-6)/11))
            if v:
                lines=[]
                for para in v.split('\n'):
                    lines.extend(simpleSplit(para,REG,font_size,value_w) or [''])
                if len(lines)>max_lines:
                    overflow.append((title,label,v))
                    lines=lines[:max_lines]
                    if max_lines>1:lines[-1]='[Forts. i bilaga]'
                c.setFont(REG,font_size);c.setFillColor(INK)
                for z,line in enumerate(lines):
                    if text_top-z*11>min_next+1:c.drawString(value_x,text_top-z*11,line[:145])
            else:
                c.setStrokeColor(LINE);c.setLineWidth(.75)
                c.line(value_x,cy-4,x+w-13,cy-4)
            cy-=row_h
        else:
            c.setFont(BOLD,8.2);c.setFillColor(GREY);c.drawString(x+13,cy,label[:100])
            cy-=19
            available=cy-y-16
            max_lines=max(1,int(available/12))
            if v:
                lines=[]
                for para in v.split('\n'):
                    lines.extend(simpleSplit(para,REG,font_size,w-30) or [''])
                if len(lines)>max_lines:
                    overflow.append((title,label,v))
                    lines=lines[:max_lines]
                    if max_lines>1:lines[-1]='[Fortsättning i bilaga]'
                c.setFillColor(INK);c.setFont(REG,font_size)
                for z,line in enumerate(lines):c.drawString(x+13,cy-z*12,line[:160])
            else:
                c.setStrokeColor(LINE);c.setLineWidth(.75)
                for z in range(max_lines):
                    ly=cy-4-z*21
                    if ly>y+12:c.line(x+13,ly,x+w-13,ly)

def _pitch_geometry(x,y,w,h):
    """Fit a 105 x 68 pitch inside the available area without distortion."""
    margin=18
    caption_space=17
    max_pw=max(1,w-2*margin)
    max_ph=max(1,h-2*margin-caption_space)
    pw=min(max_pw,max_ph*PITCH_LENGTH_TO_WIDTH)
    ph=pw/PITCH_LENGTH_TO_WIDTH
    frame_w=pw+2*margin
    frame_h=ph+2*margin+caption_space
    frame_x=x+(w-frame_w)/2
    frame_y=y+(h-frame_h)/2
    return frame_x,frame_y,frame_w,frame_h,frame_x+margin,frame_y+margin+caption_space,pw,ph

def _pitch(c,x,y,w,h,markers=None):
    """Original football diagram, ready for pen annotation or digital player markers."""
    frame_x,frame_y,frame_w,frame_h,px,py,pw,ph=_pitch_geometry(x,y,w,h)
    c.setFillColor(HexColor('#E5EDE4'))
    c.roundRect(frame_x,frame_y,frame_w,frame_h,6,stroke=0,fill=1)
    c.setFillColor(HexColor('#D5E5D5'));c.rect(px,py,pw,ph,stroke=0,fill=1)
    c.setFillColor(HexColor('#CAE1CC'))
    for i in range(0,6,2):c.rect(px+(i/6)*pw,py,pw/6,ph,fill=1,stroke=0)
    c.setLineWidth(1);c.setStrokeColor(HexColor('#8BB28D'))
    c.rect(px,py,pw,ph,fill=0,stroke=1)
    c.line(px+pw/2,py,px+pw/2,py+ph)
    c.circle(px+pw/2,py+ph/2,min(33,ph*.12),fill=0,stroke=1)
    c.rect(px,py+ph*.26,pw*.16,ph*.48,fill=0,stroke=1)
    c.rect(px+pw*.84,py+ph*.26,pw*.16,ph*.48,fill=0,stroke=1)
    c.rect(px,py+ph*.38,pw*.07,ph*.24,fill=0,stroke=1)
    c.rect(px+pw*.93,py+ph*.38,pw*.07,ph*.24,fill=0,stroke=1)
    c.setFillColor(GREY);c.setFont(REG,7)
    c.drawString(px,frame_y+8,'TACTICAL BOARD  /  MARKERA POSITIONER OCH RÖRELSER')
    for i,marker in enumerate((markers or [])[:30]):
        try:
            mx=max(0,min(1,float(marker.get('x',0.5))))
            my=max(0,min(1,float(marker.get('y',0.5))))
            team=marker.get('team','a')
            cx=px+mx*pw;cy=py+(1-my)*ph
            c.setFillColor(LIME if team=='a' else DARK)
            c.setStrokeColor(DARK if team=='a' else LIME)
            c.circle(cx,cy,8,fill=1,stroke=1)
            c.setFillColor(DARK if team=='a' else WHITE)
            c.setFont(BOLD,6.6);c.drawCentredString(cx,cy-2.6,str(i+1))
        except Exception:continue

def _inner(c, spec, index, total, page, data,overflow,report_kind):
    title,groups = page
    _brand(c,spec['title'],index,total)
    c.setFillColor(INK);c.setFont(BOLD,20);c.drawString(36,PAGE_H-105,title)
    c.setStrokeColor(LIME);c.setLineWidth(3);c.line(36,PAGE_H-115,156,PAGE_H-115)
    area_top=PAGE_H-135
    usable=area_top-53
    padding=13
    n=len(groups)
    weights=[1]*n
    if n==2: weights=[1.15,1]
    elif n==3: weights=[.9,1.1,1]
    elif n==4: weights=[1,1,1,1]
    diagram_titles=['FORMATION OCH POSITION','FORMATION & FORM','FORMATION ÖVER MATCHENS FASER',
         'FASTA SITUATIONER: ANFALL','FASTA SITUATIONER: FÖRSVAR',
         'FÖRSVARSORGANISATION','ANFALLSORGANISATION','OMSTÄLLNINGSSPEL']
    if title in diagram_titles:
        pitch_w=356
        raw=data.get('tactics','')
        try:
            markers=json.loads(raw) if raw else []
            if not isinstance(markers,list):markers=[]
        except (ValueError,TypeError):markers=[]
        _pitch(c,36,53,pitch_w,usable,markers)
        field_x=36+pitch_w+15
        field_w=PAGE_W-36-field_x
    else:field_x=36;field_w=PAGE_W-72
    available=usable-padding*(n-1)
    heights=[available*w/sum(weights) for w in weights]
    yy=area_top
    for (block_title,*keys),h in zip(groups,heights):
        _field_block(c,field_x,yy,field_w,h,block_title,keys,data,overflow,report_kind)
        yy-=h+padding

def _append_fulltext(c,spec,items,total):
    """Add complete field content when a PDF summary box is too small.

    Nothing is silently lost: long narratives continue on extra pages.
    """
    page_no=total
    def start_page():
        nonlocal page_no
        page_no+=1
        _brand(c,spec['title']+' / BILAGA',page_no,page_no)
        c.setFillColor(INK);c.setFont(BOLD,20)
        c.drawString(36,PAGE_H-110,'KOMPLETTERANDE RAPPORTTEXT')
        c.setStrokeColor(LIME);c.setLineWidth(3);c.line(36,PAGE_H-121,200,PAGE_H-121)
        return PAGE_H-158
    y=None
    for title,label,v in items:
        if y is None:y=start_page()
        if y<100:
            c.showPage();y=start_page()
        c.setFillColor(DEEP);c.setFont(BOLD,9);c.drawString(40,y,title[:100].upper());y-=19
        c.setFillColor(GREY);c.setFont(BOLD,8.5);c.drawString(40,y,label[:100]);y-=17
        for paragraph in v.split('\n'):
            lines=simpleSplit(paragraph,REG,9.4,PAGE_W-83) or ['']
            for line in lines:
                if y<60:
                    c.showPage();y=start_page()
                c.setFillColor(INK);c.setFont(REG,9.4);c.drawString(40,y,line);y-=14
            y-=5
        y-=15
    if y is not None:c.showPage()

def render_pdf(kind='player',data=None):
    if kind not in REPORT_SPECS:raise ValueError('Unknown report kind')
    data=data or {}
    spec=REPORT_SPECS[kind]
    buf=BytesIO();c=canvas.Canvas(buf,pagesize=landscape(A4),pageCompression=1)
    c.setTitle('Andrablicken - '+spec['title'].title())
    c.setAuthor('Andrablicken Scouting Network')
    total=len(spec['pages'])+1
    overflow=[]
    _cover(c,spec,kind,data);c.showPage()
    for idx,page in enumerate(spec['pages'],start=2):
        _inner(c,spec,idx,total,page,data,overflow,kind);c.showPage()
    if overflow:
        # Preserve first occurrence for values that appear in multiple summaries.
        seen=set();unique=[]
        for title,label,value in overflow:
            marker=(label,value)
            if marker not in seen:seen.add(marker);unique.append((title,label,value))
        _append_fulltext(c,spec,unique,total)
    c.save();buf.seek(0)
    return buf.getvalue()

if __name__=='__main__':
    target=Path(__file__).parent/'static'
    (target/'spelarrapport-mall.pdf').write_bytes(render_pdf('player'))
    (target/'motstandarrapport-mall.pdf').write_bytes(render_pdf('opposition'))
    print('Created PDFs')
