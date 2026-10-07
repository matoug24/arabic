"""Original, word-specific SVG scenes for concepts without a suitable sourced image.
No generic placeholder fallback: every concept must have an explicit scene definition.
"""
import html,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INK='#193b3a';GREEN='#176b60';GOLD='#eab654';RED='#c45538';BLUE='#4a87b5'
def rect(x,y,w,h,fill=GREEN):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}"/>'
def circle(x,y,r,fill=GOLD):return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'
def text(x,y,s,size=20,fill=INK):return f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Arial,sans-serif" font-size="{size}" fill="{fill}">{html.escape(str(s))}</text>'
def line(x1,y1,x2,y2,color=INK,width=4):return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
def arrow(x1,y1,x2,y2,color=GREEN):
    a=math.atan2(y2-y1,x2-x1);ax=x2-12*math.cos(a)+7*math.sin(a);ay=y2-12*math.sin(a)-7*math.cos(a);bx=x2-12*math.cos(a)-7*math.sin(a);by=y2-12*math.sin(a)+7*math.cos(a)
    return line(x1,y1,x2,y2,color)+f'<path d="M{ax:.2f},{ay:.2f} L{x2},{y2} L{bx:.2f},{by:.2f}" fill="none" stroke="{color}" stroke-width="4"/>'
def person(x,y,color=GREEN):return circle(x,y,17,'#ecc6a5')+line(x,y+20,x,y+80,color,15)+line(x,y+40,x-24,y+57,color,8)+line(x,y+40,x+24,y+57,color,8)+line(x,y+80,x-20,y+115,INK,8)+line(x,y+80,x+20,y+115,INK,8)
def book(x,y,color=BLUE):return rect(x,y,70,90,color)+line(x+12,y+5,x+12,y+85,'#fff',2)+line(x+25,y+30,x+60,y+30,'#fff',2)+line(x+25,y+45,x+60,y+45,'#fff',2)
def apple(x,y,color=RED):return circle(x-12,y,23,color)+circle(x+12,y,23,color)+f'<path d="M{x},{y-22} Q{x+4},{y-42} {x+20},{y-38}" fill="none" stroke="{GREEN}" stroke-width="6"/>'
def sun(x,y):return circle(x,y,25,GOLD)+''.join(line(x+32*math.cos(a),y+32*math.sin(a),x+43*math.cos(a),y+43*math.sin(a),GOLD,4) for a in [i*math.pi/4 for i in range(8)])
def moon(x,y):return circle(x,y,27,GOLD)+circle(x+12,y-7,24,'#fffef9')
def label(s):return text(250,355,s,19)
def pair_scene(left,right,caption):return rect(40,65,175,180,'#edf1e4')+rect(285,65,175,180,'#edf1e4')+text(125,125,left,25)+text(375,125,right,25)+arrow(220,165,275,165)+label(caption)

TIME={'soon':('NOW','a moment later',280),'early':('8:00','start 9:00',155),'nearly':('START','almost finished',365),'almost':('START','not quite finished',365),'just':('a moment ago','NOW',360),'already':('DONE','NOW',165),'yet':('not done','later',360),'still':('same activity','NOW',300),'tonight':('TODAY','NIGHT',340),'sleepiness':('AWAKE','getting sleepy',300),'impatient':('waiting','hurry!',220)}
CALENDARS={'daily':(7,set(range(7)),'Every day'),'usually':(7,{0,1,2,3,4,5},'On most days'),'rarely':(14,{10},'Only once in a while'),'weekly':(14,{2,9},'One day each week'),'monthly':(12,set(range(12)),'Once in each month'),'yearly':(5,set(range(5)),'Once in each year')}
SPACE={'into':(60,180,230,180,'Move inside'),'onto':(80,120,245,95,'Move onto the top'),'down':(230,80,230,220,'Move downward'),'beside':(135,190,None,None,'Next to the box'),'apart':(80,170,400,170,'Move away from one another'),'away':(260,180,430,180,'Move farther away'),'along':(60,270,430,270,'Follow the path'),'beyond':(230,180,425,180,'Past the boundary'),'throughout':(80,170,400,170,'In every part'),'via':(80,270,400,85,'Reach it through another place'),'deep':(250,275,None,None,'Far below the surface'),'shallow':(250,110,None,None,'Close to the surface'),'high':(250,75,None,None,'Far above the ground'),'steep':(80,280,330,75,'A steep slope'),'curved':(70,240,400,140,'A line that bends'),'rounded':(250,175,None,None,'A rounded corner')}
QUANTITY={'enough':(3,3,'Three people, three seats'),'each':(4,4,'One for every person'),'only':(1,5,'Just one selected'),'plus':(2,3,'Two plus three'),'total':(2,3,'All the items together'),'most':(7,10,'Seven out of ten'),'sparse':(3,12,'Only a few, far apart'),'quite':(6,10,'A fairly large amount'),'really':(9,10,'A very strong amount'),'rather':(6,10,'Somewhat more than expected')}
LOGIC={'unless':('RAIN','Take umbrella unless sunny'),'whether':('SUN or RAIN','Which will it be?'),'either':('A or B','Choose one of two'),'nor':('NOT A + NOT B','Neither choice'),'also':('BOOK + BALL','One more thing too'),'though':('RAIN','Still going outside'),'whereas':('ONE READS','The other plays'),'except':('ALL BUT ONE','Leave one out'),'despite':('RAIN','Playing anyway'),'perhaps':('MAYBE','An uncertain possibility'),'maybe':('MAYBE','It might happen'),'about':('TOPIC','Talking about one thing')}
LOCATIONS={'everywhere':set(range(9)),'nowhere':set(),'somewhere':{5},'anywhere':{1,3,5,7},'wherever':{0,2,4,6,8}}
ORDINALS={'seventh':7,'eighth':8,'ninth':9,'tenth':10}
LANGUAGE={'grammar','noun','sentence','spelling','paragraph','example','fact','meaning','diagram','compare'}
FEELINGS={'polite','rude','gentle','honest','careless','disappointment','concentration','hygiene','myself','yourself','whose'}
TEXTURES={'fuzzy','silky','shiny','bright','pale','patterned','checkered','blunt','ripe','unripe','crunchy','crunch','flavour','volume'}
SCENES={'crossing','stop sign','tidy','neat','discount','something','anything','grade','practice','opponent','pull','leftover','borrow','rehearsal','performance','toll','deposit','refund'}
def render(key):
    if key=='easily':return person(90,80)+rect(345,160,90,85,GOLD)+circle(190,170,22,BLUE)+arrow(220,170,350,170)+text(380,125,'✓',50,GREEN)+label('One simple action without difficulty')
    if key in TIME:
        left,right,p=TIME[key];s=arrow(60,200,430,200)+circle(p,200,13,RED)+text(80,240,left,17)+text(360,240,right,17)
        if key=='tonight':s+=sun(115,105)+moon(365,100)
        elif key=='sleepiness':s+=person(120,85)+text(360,120,'Z z z',35)
        elif key=='impatient':s+=person(120,75)+circle(360,110,32,'#edf1e4')+line(360,110,360,84)+line(360,110,383,124)+text(290,65,'!',38,RED)
        else:s+=rect(140,100,200,25,'#e5ecde')+rect(140,100,(p-60)*.52,25,GREEN)
        return s+label(right)
    if key in CALENDARS:
        n,active,caption=CALENDARS[key];s='';cols=7 if n in (7,14) else (4 if n==12 else 5)
        for i in range(n):x=45+(i%cols)*58;y=100+(i//cols)*65;s+=rect(x,y,48,48,GREEN if i in active else '#dce4dc')+text(x+24,y+32,i+1,18,'white' if i in active else INK)
        return s+label(caption)
    if key in ORDINALS:
        n=ORDINALS[key];s=arrow(40,220,450,220)
        for i in range(10):s+=circle(52+i*43,145,17,GOLD if i+1==n else '#dce4dc')+text(52+i*43,151,i+1,15)
        return s+line(52+(n-1)*43,180,52+(n-1)*43,205,RED)+label(f'Position {n} in a line of ten')
    if key in ('hundred','thousand'):
        n=100 if key=='hundred' else 1000;cols=10 if n==100 else 40;r=4 if n==100 else 1.6;dx=22 if n==100 else 10;dy=18 if n==100 else 7
        s=''.join(circle(50+(i%cols)*dx,55+(i//cols)*dy,r,GREEN) for i in range(n))
        return s+text(250,295,n,45)+label('Ten groups of ten' if n==100 else 'Ten groups of one hundred')
    if key in SPACE:
        x,y,x2,y2,caption=SPACE[key];s=rect(190,110,125,120,'#dce4dc')
        if key in ('deep','shallow'):s=rect(65,90,370,220,'#d5ebee')+line(65,90,435,90,BLUE)+line(320,90,320,y,GREEN,2)
        if key=='high':s=line(60,290,440,290)+line(320,290,320,80,GREEN,2)
        if key=='steep':s=f'<path d="M60 295 L340 70 L420 295Z" fill="#dce4dc" stroke="{GREEN}" stroke-width="4"/>'
        if key=='curved':return f'<path d="M70 240 Q160 40 270 155 T430 120" fill="none" stroke="{BLUE}" stroke-width="15"/>'+label(caption)
        if key=='rounded':return f'<rect x="125" y="80" width="250" height="200" rx="75" fill="#dce4dc" stroke="{GREEN}" stroke-width="6"/>'+label(caption)
        if key in ('throughout','beyond'):s+=line(345,50,345,290,RED,3)
        if key=='via':s+=circle(235,180,30,GOLD)+text(235,185,'via',17);s+=arrow(80,270,235,200)+arrow(250,165,400,85)
        elif x2 is not None:s+=circle(x,y,16,BLUE)+arrow(x,y,x2,y2)
        else:s+=circle(x,y,18,BLUE)
        return s+label(caption)
    if key in QUANTITY:
        n,total,caption=QUANTITY[key];s=''
        if key in ('enough','each'):
            for i in range(n):x=75+i*95;s+=person(x,65)+rect(x-25,210,50,12,GOLD)+line(x-20,220,x-20,260)+line(x+20,220,x+20,260)
        elif key in ('plus','total'):
            s=''.join(apple(55+i*70,130) for i in range(n))+text(240,140,'+',45)+''.join(apple(305+i*70,130,GREEN) for i in range(total))+text(250,265,'2 + 3 = 5',35)
        else:
            for i in range(total):s+=circle(65+(i%5)*83,100+(i//5)*95,21,GREEN if i<n else '#dce4dc')
            s+=text(250,280,f'{n} / {total}',28)
        return s+label(caption)
    if key in LOCATIONS:
        s=rect(35,55,430,255,'#edf1e4')
        for i in range(9):x=90+(i%3)*155;y=90+(i//3)*90;s+=circle(x,y,15,RED if i in LOCATIONS[key] else '#dce4dc')+line(x,y+15,x,y+29,INK if i in LOCATIONS[key] else '#dce4dc',3)
        return s+label({'everywhere':'In all places','nowhere':'Not in any place','somewhere':'In one place, not sure where','anywhere':'Any place can be chosen','wherever':'No matter which place'}[key])
    if key in LOGIC:
        left,caption=LOGIC[key];s=rect(35,70,190,180,'#edf1e4')+rect(275,70,190,180,'#edf1e4')+text(130,110,left,18)+arrow(225,160,275,160)
        if key in ('unless','though','despite'):s+=circle(125,155,30,'#b3cbd2')+line(105,190,97,222,BLUE)+line(140,190,132,222,BLUE)+person(375,95)+text(375,275,'OUTSIDE',14)
        elif key in ('either','nor','whether','whereas','also'):s+=book(80,135)+circle(370,170,35,GOLD)+text(370,177,'B',26)
        elif key=='except':s+=''.join(circle(70+i*60,165,18,RED if i==3 else GREEN) for i in range(7))+line(240,125,295,195,RED)
        else:s+=person(125,130)+text(365,192,'?',75)
        return s+label(caption)
    if key in LANGUAGE:
        if key=='paragraph':s=''.join(rect(70,65+i*28,350 if i!=5 else 240,10,GREEN) for i in range(6));return s+label('Several sentences together')
        if key in ('grammar','sentence','spelling'):
            tokens=['The','cat','sleeps.'] if key!='spelling' else ['c','a','t'];s=''
            for i,t in enumerate(tokens):s+=rect(45+i*145,110,120,85,[GOLD,BLUE,GREEN][i])+text(105+i*145,161,t,23,'white')
            return s+arrow(55,240,440,240)+label({'grammar':'Words arranged to make sense','sentence':'One complete thought','spelling':'Letters in the right order'}[key])
        if key=='noun':return person(100,80)+apple(260,175)+book(350,125)+text(100,255,'person',18)+text(260,255,'thing',18)+text(385,255,'object',18)+label('Naming words: people, places and things')
        if key=='example':return circle(150,160,55,GREEN)+circle(355,160,55,GREEN)+line(65,270,430,270)+label('One instance shows what we mean')
        if key=='fact':return apple(185,155)+apple(290,155)+text(250,260,'1 + 1 = 2',40)+label('Something that can be checked')
        if key=='meaning':return book(60,105)+arrow(165,160,285,160)+apple(365,160)+text(100,245,'word',19)+text(360,245,'what it represents',18)+label('Connecting a word to an idea')
        if key=='compare':return rect(70,150,110,110,BLUE)+rect(305,65,110,195,GREEN)+text(120,295,'shorter',20)+text(360,295,'taller',20)+label('Look at similarities and differences')
        return rect(200,55,100,50,BLUE)+arrow(250,110,250,185)+rect(120,195,260,65,GREEN)+label('A drawing that explains connections')
    if key in FEELINGS:
        s=person(110,75)+person(390,75,BLUE)
        if key=='polite':s+=rect(155,50,190,65,'#edf1e4')+text(250,89,'Please. Thank you.',18);caption='Speaking with good manners'
        elif key=='rude':s+=rect(155,45,190,75,'#f8ded5')+text(250,76,'STOP! ME FIRST!',19,RED)+line(100,40,400,225,RED);caption='Interrupting without care'
        elif key=='gentle':s+=circle(250,190,38,GOLD)+line(160,170,230,185,GREEN,3);caption='A careful, light touch'
        elif key=='honest':s+=rect(215,175,65,40,GOLD)+arrow(155,205,330,205)+text(250,280,'Your lost wallet.',22);caption='Returning what belongs to someone else'
        elif key=='careless':s+=rect(200,180,55,65,BLUE)+line(255,235,305,265,BLUE)+circle(295,265,25,'#d5ebee');caption='Not taking enough care'
        elif key=='disappointment':s+=circle(250,140,52,'#ecc6a5')+circle(233,128,4,INK)+circle(270,128,4,INK)+f'<path d="M225 169 Q250 145 278 169" fill="none" stroke="{INK}" stroke-width="4"/>';caption='Feeling sad when a hope does not happen'
        elif key=='concentration':s+=book(213,140)+arrow(158,120,218,147)+arrow(345,120,282,147);caption='Giving one task your full attention'
        elif key=='hygiene':s+=rect(200,155,100,25,BLUE)+circle(237,215,12,'#d5ebee')+circle(272,215,12,'#d5ebee')+text(250,280,'Clean hands',24);caption='Keeping your body clean'
        elif key in ('myself','yourself'):s+=rect(200,65,110,170,'#d5ebee')+person(250,80)+arrow(155,180,200,180);caption='I do it for myself' if key=='myself' else 'You do it for yourself'
        else:s+=rect(225,175,60,45,GOLD)+text(250,110,'?',60)+arrow(165,205,220,205)+arrow(340,205,290,205);caption='Who owns this?'
        return s+label(caption)
    if key in TEXTURES:
        if key in ('ripe','unripe'):return apple(130,155,GREEN)+apple(360,155,RED)+text(130,245,'not ready',22)+text(360,245,'ready to eat',22)+line(100 if key=='unripe' else 330,270,160 if key=='unripe' else 390,270,GOLD,9)+label('An apple ready to eat' if key=='ripe' else 'An apple not ready to eat yet')
        if key=='blunt':return f'<path d="M95 125H305 Q385 125 385 175H95Z" fill="#c4d1d4" stroke="{INK}" stroke-width="3"/>'+rect(70,122,80,55,GREEN)+circle(385,170,35,'none')+label('A rounded tip; not sharp')
        if key in ('crunchy','crunch','flavour'):return apple(190,160)+person(340,90)+text(280,75,'CRUNCH!' if key!='flavour' else 'sweet / sour',25)+''.join(circle(230+i*12,200+i%2*15,4,GOLD) for i in range(7))+label('A crisp bite makes a crunch' if key!='flavour' else 'How food tastes')
        if key=='volume':return rect(125,65,100,230,'#d5ebee')+rect(285,125,110,170,'#d5ebee')+line(130,100,220,100,BLUE)+line(290,170,390,170,BLUE)+text(175,255,'1 litre',20)+text(340,255,'half litre',20)+label('How much a container holds')
        if key=='pale':return circle(125,170,60,'#f4d8d3')+circle(365,170,60,RED)+text(125,270,'pale',24)+text(365,270,'strong colour',22)
        if key in ('bright','shiny'):return sun(255,165)+''.join(line(250,165,80+i*65,275,GOLD,3) for i in range(6))+label('A bright light' if key=='bright' else 'Light reflected from a surface')
        s=rect(85,60,330,240,'#edf1e4')
        for r in range(6):
            for c in range(8):
                x=105+c*38;y=82+r*35
                if key=='checkered':s+=rect(x,y,32,32,GREEN if (r+c)%2 else '#eab654')
                elif key=='patterned':s+=circle(x+12,y+12,9,GREEN if (r+c)%2 else GOLD)
                elif key=='silky':s+=f'<path d="M{x} {y}q12 -15 24 0" fill="none" stroke="{BLUE}" stroke-width="2"/>'
                else:s+=''.join(line(x+12,y+12,x+12+12*math.cos(a),y+12+12*math.sin(a),GREEN,2) for a in [i*math.pi/4 for i in range(8)])
        return s+label({'checkered':'Alternating square colours','patterned':'A repeating design','silky':'Smooth threads like silk','fuzzy':'A soft surface with fine hairs'}[key])
    if key in SCENES:
        if key in ('crossing','stop sign','toll'):
            s=rect(60,70,380,220,'#b8c4c4')
            if key=='crossing':s+=''.join(rect(110+i*42,90,24,180,'white') for i in range(7))+person(250,65);caption='Walking across the road'
            elif key=='stop sign':s+=f'<path d="M180 65h140l60 60v100l-60 60H180l-60-60V125Z" fill="{RED}"/>'+text(250,188,'STOP',45,'white');caption='Stop before continuing'
            else:s+=line(100,140,370,140,RED,13)+circle(125,220,25,GOLD)+text(125,227,'$',25)+person(360,110);caption='Pay to use this road'
            return s+label(caption)
        if key in ('tidy','neat'):return book(70,130)+book(180,130)+book(290,130)+line(60,225,435,225)+label('Things arranged neatly in their places')
        if key=='discount':return rect(100,85,300,180,'#edf1e4')+text(250,135,'$10',35)+line(180,110,325,145,RED)+text(250,220,'$7',55,GREEN)+label('A lower price than before')
        if key in ('something','anything'):return rect(75,115,145,140,GOLD)+text(150,210,'?',70)+book(310,135)+apple(385,75)+label('One thing, not named' if key=='something' else 'Any of the things can be chosen')
        if key=='grade':return rect(135,65,230,230,'#edf1e4')+text(250,150,'8 / 10',50,GREEN)+text(250,225,'Good work ✓',22)+label('A mark for school work')
        if key=='practice':return pair_scene('TRY 1','TRY 2 → TRY 3','Repeat a skill to improve')
        if key=='opponent':return person(100,80)+person(400,80,BLUE)+circle(250,180,30,GOLD)+arrow(150,170,210,170)+arrow(350,170,290,170)+label('Players on opposite sides')
        if key=='pull':return person(95,80)+rect(320,130,95,95,GOLD)+line(135,150,320,175)+arrow(315,245,150,245)+label('Bring something toward you')
        if key=='leftover':return circle(250,170,100,'#d5ebee')+apple(280,190)+text(250,65,'AFTER THE MEAL',22)+label('Food remaining after eating')
        if key=='borrow':return person(100,60)+person(395,60,BLUE)+book(215,160)+arrow(335,95,165,95)+arrow(165,295,335,295)+text(250,65,'Use now',20)+text(250,330,'Return later',20)
        if key in ('rehearsal','performance'):
            s=rect(60,50,380,230,'#e5ecde')+rect(60,50,35,230,RED)+rect(405,50,35,230,RED)+person(250,95)+line(235,235,300,235,BLUE)
            if key=='performance':s+=''.join(circle(90+i*62,305,16,INK) for i in range(6))
            else:s+=text(250,70,'PRACTICE BEFORE THE SHOW',17)
            return s+label('Performing for an audience' if key=='performance' else 'Practicing a show before the audience comes')
        if key in ('deposit','refund'):
            s=rect(245,110,140,145,'#dce4dc')+rect(275,80,80,25,BLUE)+circle(105,180,25,GOLD)+text(105,188,'$',26)
            s+=arrow(140,180,240,180) if key=='deposit' else arrow(245,280,110,280)
            return s+label('Put money into your account' if key=='deposit' else 'Money returned after a purchase')
    raise KeyError('No concept-specific scene for '+key)
def main():
    path=ROOT/'data/curriculum.json';words=json.loads(path.read_text(encoding='utf-8'));count=0
    for w in words:
        if w['image']:continue
        body=render(w['english']);filename=f'concept-{w["id"]}.svg'
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 390"><title>{html.escape(w["english"])} concept scene</title><desc>Original concept diagram. Parent must review the intended sense.</desc><rect width="500" height="390" rx="20" fill="#fffef9"/>{body}</svg>'
        (ROOT/'static/images'/filename).write_text(svg,encoding='utf-8')
        w.update(image='images/'+filename,image_candidate=None,image_source='https://github.com/matoug24/arabic/blob/main/static/images/'+filename,image_creator='Arabic, together project — original SVG concept diagram',image_license='CC BY-SA 4.0',image_match='Explicit scene for '+w['english'],image_review='Original semantic scene/diagram; English labels help explain abstract concepts. Review the intended meaning before publication.',image_approved=False);count+=1
    path.write_text(json.dumps(words,ensure_ascii=False,indent=2),encoding='utf-8');print('Original concept scenes:',count,'; total coverage:',sum(bool(w['image']) for w in words))
if __name__=='__main__':main()
