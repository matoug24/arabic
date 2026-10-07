"""Corrections recorded during the systematic 40-sheet, 2,000-entry review."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from concept_diagrams import *
CLONES={'watch':'wristwatch','test':'exam','transport':'vehicle','flight':'airplane','trainer':'sneaker','environment':'nature','classroom':'class','hall':'corridor','motorhome':'camper','fly':'airplane','camping':'tent','light':'lamp','nut':'walnut'}
SPECIAL={'company','and','science','guest','dishonest','coach','club','pool','take','have','bit','fingernail','toenail','waist','date','pot','alert','mine','queue','hem','babysitter','soil','area','for','collection','ticket','cricket','netball','squash','sweetcorn','lotion','badge','will','comfort','relief','headphone','earmuff','cracker','pulse','heartbeat','thermostat','try','snowball','weight','toboggan','furry','gain','capital','gravy','labor','birth','tape','cream','grocery','sorbet','check','inspire','pack','mug','goldfish','pipe','torch','bat','showerhead','textbook','gecko','workbook','sketchbook','clipboard','carton','attendance','courthouse','dense','weaving','core','signpost','solid','stop'}
MEANINGS={'watch':'A small clock worn on your wrist.','company':'A business or organization where people work.','date':'A sweet fruit that grows on a date palm.','capital':'The main city where a country\'s government is based.','labor':'Physical work that takes effort.','mug':'A drinking cup with a handle.','cell':'A tiny unit that makes up a living thing.','blind':'A window covering that can be rolled up.','cricket':'A sport played with a bat, ball and wickets.','club':'A group of people who meet for a shared activity.','flight':'A journey through the air in an aircraft.','pool':'A place filled with water for swimming.','pipe':'A hollow tube that carries water or another material.','torch':'A portable electric lamp, also called a flashlight.','bat':'A wooden implement used to hit a ball in a sport.','fingernail':'The hard covering at the end of a finger.','toenail':'The hard covering at the end of a toe.','soil':'Earth in which plants grow.','sorbet':'A frozen dessert made with fruit and water.','cream':'The rich white part of milk, used in food.','nut':'An edible seed with a hard shell.','bit':'A small part or amount of something.','five':'The number after four and before six.','second':'Position two in an ordered sequence.','for':'Used to show who something is intended to help or belong to.'}
def cup():return rect(155,95,175,155,BLUE)+f'<path d="M330 110 Q425 105 405 205 Q370 235 330 218" fill="none" stroke="{BLUE}" stroke-width="24"/>'+line(170,106,315,106,'#dce4dc',5)
def fish():return f'<ellipse cx="245" cy="180" rx="115" ry="65" fill="{GOLD}"/><path d="M135 180L55 100V255Z" fill="{GOLD}"/><path d="M225 120L270 78L310 132M225 230L285 280L310 225" fill="{RED}"/>'+circle(305,157,9,INK)
def pot():return rect(130,115,240,145,BLUE)+rect(95,125,55,25,BLUE)+rect(350,125,55,25,BLUE)+line(145,105,355,105,INK,9)+rect(218,80,65,18,INK)
def medical_graph(wrist=False):
    s=person(105,85) if not wrist else rect(60,155,200,60,'#ecc6a5')+circle(240,175,13,RED)
    return s+rect(285,80,170,155,'#edf1e4')+f'<path d="M295 170H320L330 155L342 195L352 120L365 190L380 160H443" fill="none" stroke="{RED}" stroke-width="6"/>'
def extra(key):
    if key in ('take','have'):return person(140,80)+circle(285,165,40,GOLD)+(arrow(345,160,185,160) if key=='take' else line(150,150,260,168,GREEN,10))+label('Bring an object toward you' if key=='take' else 'An object that you possess')
    if key=='guest':return rect(290,65,130,225,'#d5ebee')+person(130,85)+person(350,90,BLUE)+arrow(180,170,280,170)+text(250,50,'Welcome!',25)+label('A visitor you welcome into your home')
    if key=='ticket':return rect(85,105,330,160,'#edf1e4')+text(250,153,'BUS TICKET',24)+rect(130,185,100,35,BLUE)+circle(155,227,12,INK)+circle(210,227,12,INK)+''.join(circle(330,120+i*22,3,INK) for i in range(6))+label('A pass that allows you to travel or enter')
    if key=='stop':return person(150,85)+arrow(210,175,310,175)+line(320,85,320,270,RED,13)+label('End the movement or action')
    if key=='cracker':return rect(105,90,290,195,'#ead49d')+''.join(circle(135+(i%6)*45,120+(i//6)*40,4,'#9f783c') for i in range(24))+label('A thin crisp biscuit for a snack')
    if key in ('fingernail','toenail'):
        s=rect(180,175,170,95,'#ecc6a5')
        for i in range(5):x=160+i*45;h=90+20*(i%3);s+=rect(x,190-h,36,h+40,'#ecc6a5')+rect(x+7,200-h,22,25,'#fffef9')
        return s+arrow(110,85,185,115)+label('Hard nail at the end of a '+('finger' if key=='fingernail' else 'toe'))
    if key=='waist':return f'<path d="M160 55H340L315 135L305 175L345 285H155L195 175L185 135Z" fill="#ecc6a5"/>'+line(170,170,325,170,RED,9)+arrow(65,170,170,170)+label('Around the middle of the body')
    if key=='date':return ''.join(f'<ellipse cx="{130+i*80}" cy="175" rx="30" ry="55" fill="#8d542a"/>'+line(125+i*80,140,135+i*80,210,'#5b361e',3) for i in range(4))+label('Sweet fruit from a date palm')
    if key in ('mug','cream','sorbet'):
        if key=='mug':return cup()+label('A cup with a handle')
        s=f'<path d="M120 195H380Q355 290 250 290Q145 290 120 195Z" fill="{BLUE}"/>'
        s+=''.join(circle(190+i*60,185,42,'#fff5dd' if key=='cream' else ['#efbba8','#edd069','#bdcf80'][i]) for i in range(3))
        return s+label('Rich dairy cream' if key=='cream' else 'A frozen fruit dessert')
    if key=='pot':return pot()+label('A container for cooking')
    if key in ('soil','environment'):return rect(70,175,360,120,'#8d542a')+rect(70,160,360,22,GREEN)+line(250,165,250,90,GREEN,6)+circle(220,115,24,GREEN)+circle(278,92,24,GREEN)+label('Earth where plants grow')
    if key in ('and','for','will','mine','check','try','inspire','gain'):
        if key=='and':return book(65,100)+text(250,170,'&',70)+circle(370,165,48,GOLD)+label('One thing and another together')
        if key=='for':return person(100,90)+rect(200,150,80,75,RED)+rect(230,145,20,85,GOLD)+arrow(290,185,370,185)+person(415,90,BLUE)+label('A gift intended for this person')
        if key=='will':return person(110,100)+arrow(185,175,370,175)+rect(340,90,100,135,'#edf1e4')+text(390,135,'TOMORROW',15)+text(390,185,'✓',45,GREEN)+label('An action planned for the future')
        if key=='mine':return person(175,80)+book(260,145)+arrow(245,155,200,135)+label('This belongs to me')
        if key=='check':return rect(140,70,220,220,'#edf1e4')+''.join(text(185,118+i*50,'✓',28,GREEN)+line(225,110+i*50,330,110+i*50,INK,2) for i in range(3))+circle(380,245,30,'none')+line(403,267,430,294,BLUE,8)+label('Look carefully to make sure it is right')
        if key=='inspire':return person(105,100)+book(190,160)+arrow(275,140,345,105)+circle(370,70,25,GOLD)+person(390,155,BLUE)+label('Give someone a new idea or encouragement')
        if key=='gain':return text(110,100,'BEFORE',20)+text(365,100,'AFTER',20)+circle(110,190,35,GOLD)+circle(330,190,35,GOLD)+circle(400,190,35,GOLD)+arrow(160,190,270,190)+label('Get more than you had before')
        return person(120,75)+circle(220,145,25,GOLD)+arrow(255,155,350,200)+rect(350,175,70,90,BLUE)+label('Make an attempt')
    if key in ('dishonest','comfort','relief','alert'):
        if key=='dishonest':return person(105,100)+rect(200,180,90,45,GOLD)+text(250,95,'I did not take it!',20,RED)+line(350,100,450,195,RED,6)+label('Saying something that is not true')
        if key=='comfort':return person(160,100)+person(310,100,BLUE)+line(165,145,292,142,GREEN,10)+text(260,75,'It will be okay.',22)+label('Help someone feel less worried')
        if key=='relief':return pair_scene('WORRIED','SAFE NOW ✓','The worry has passed')
        return person(200,100)+circle(190,94,4,INK)+circle(210,94,4,INK)+sun(360,130)+label('Awake and paying attention')
    if key in ('queue','coach','club','babysitter','company','attendance'):
        if key=='queue':return ''.join(person(80+i*110,100) for i in range(4))+arrow(50,275,440,275)+label('People waiting in a line')
        if key=='coach':return person(125,80)+person(355,130,BLUE)+circle(340,270,28,GOLD)+arrow(180,150,320,190)+label('A person helping players improve')
        if key=='babysitter':return person(125,65)+person(310,155,BLUE)+circle(390,220,28,GOLD)+label('An adult looking after a child')
        if key=='company':return rect(160,50,240,245,'#e5ecde')+''.join(rect(185+(i%3)*65,80+(i//3)*55,40,30,BLUE) for i in range(9))+person(80,170)+label('A business where people work')
        if key=='attendance':return ''.join(person(80+i*110,80) +text(80+i*110,270,'✓',35,GREEN) for i in range(4))+label('Present for class')
        return ''.join(person(120+i*120,85) for i in range(3))+circle(250,285,28,GOLD)+label('People meeting for a shared interest')
    if key in ('pool','cricket','netball','squash','bat'):
        if key=='pool':return rect(55,70,390,225,'#91cfdf')+''.join(f'<path d="M70 {110+i*45}q25 -18 50 0t50 0t50 0t50 0t50 0t50 0" fill="none" stroke="white" stroke-width="4"/>' for i in range(4))+circle(250,160,23,'#ecc6a5')+label('A pool for swimming')
        if key=='bat':return f'<path d="M130 95Q105 75 125 50Q145 40 160 65L365 260Q380 280 360 300Q340 312 320 290Z" fill="#a9733e"/>'+circle(350,80,33,'#fff5dd')+label('A bat for hitting a ball')
        s=person(125,85)+circle(320,230,18,GOLD)
        if key=='cricket':s+=''.join(line(320+i*25,70,320+i*25,195,GREEN,8) for i in range(3))+line(320,70,370,70)+line(165,160,265,250,'#a9733e',16);caption='Bat, ball and wickets'
        elif key=='netball':s+=line(385,80,385,300,BLUE,8)+f'<ellipse cx="355" cy="90" rx="55" ry="15" fill="none" stroke="{BLUE}" stroke-width="5"/>'+arrow(220,190,345,110);caption='A team game with a ball and raised net'
        else:s+=line(405,55,405,295,BLUE,12)+circle(220,150,30,'none')+line(210,175,170,215,GREEN,8)+arrow(260,165,390,150);caption='A racket game played against a wall'
        return s+label(caption)
    if key in ('furry','dense','weaving','area','collection','bit','core','capital'):
        if key=='dense':return ''.join(circle(70+(i%10)*39,80+(i//10)*38,15,GREEN) for i in range(50))+label('Many things packed closely together')
        if key=='furry':return ''.join(line(70+i*7,90+j*37,80+i*7,60+j*37,'#926238',3) for j in range(6) for i in range(48))+label('Covered with soft hair or fur')
        if key=='weaving':return ''.join(rect(75+i*42,50,22,240,BLUE) for i in range(8))+''.join(rect(60,75+i*38,365,18,GOLD) for i in range(6))+label('Threads crossing over and under')
        if key=='area':return rect(90,65,320,230,'#e5ecde')+''.join(line(90+i*40,65,90+i*40,295,'#98b9a2',1) for i in range(9))+''.join(line(90,65+i*38,410,65+i*38,'#98b9a2',1) for i in range(7))+label('The space inside a boundary')
        if key=='collection':return ''.join(circle(100+(i%4)*100,100+(i//4)*100,28,[GOLD,GREEN,BLUE,RED][i%4]) for i in range(8))+label('Things gathered and kept together')
        if key=='bit':return rect(70,95,365,185,'#edf1e4')+rect(70,95,35,35,RED)+arrow(120,60,95,95)+label('A small part of something')
        if key=='core':return circle(250,165,115,RED)+circle(250,165,85,'#fff5dd')+circle(250,165,28,'#8d542a')+arrow(75,90,225,150)+label('The central part')
        return rect(55,55,390,245,'#edf1e4')+circle(125,220,10,GREEN)+circle(390,250,10,GREEN)+text(250,150,'★',65,GOLD)+rect(190,200,120,70,BLUE)+label('The main government city of a country')
    if key in ('science','thermostat','textbook','workbook','sketchbook','clipboard','cell'):
        if key=='science':return f'<path d="M140 70h50v90l65 100H75l65-100Z" fill="#b4dde6" stroke="{BLUE}" stroke-width="4"/>'+circle(160,230,15,GOLD)+circle(190,195,10,GOLD)+sun(360,145)+label('Learn about the world through observations')
        if key=='thermostat':return rect(105,65,290,225,'#e5ecde')+rect(145,100,210,85,'white')+text(250,159,'21°C',40)+text(185,255,'−',50)+text(325,255,'+',50)+label('A control that sets the temperature')
        if key=='cell':return circle(250,180,110,'#d5ebee')+circle(250,175,35,BLUE)+''.join(circle(180+i*35,115+i%3*55,12,GOLD) for i in range(5))+label('A tiny living unit with a nucleus')
        s=book(145,60)+book(285,70,GREEN)
        if key=='clipboard':s=rect(135,50,230,250,BLUE)+rect(150,70,200,210,'white')+rect(200,40,100,35,GOLD)
        if key in ('workbook','clipboard'):s+=''.join(line(175,125+i*40,335,125+i*40,INK,2) for i in range(3))+text(240,225,'1. ___ 2. ___',17)
        if key=='sketchbook':s+=sun(285,195)+line(130,245,355,245,INK,2)
        return s+label({'textbook':'A book used for learning a subject','workbook':'A book of practice exercises','sketchbook':'A book for drawings','clipboard':'A board and clip that holds paper'}[key])
    if key in ('heartbeat','pulse'):return medical_graph(key=='pulse')+label('The regular beating of the heart' if key=='heartbeat' else 'A heartbeat felt at the wrist')
    if key in ('tape','hem','lotion','badge','pipe','torch','showerhead','earmuff','headphone','carton','goldfish','gecko','sweetcorn','grocery','pack'):
        if key=='goldfish':return fish()+label('An ornamental orange fish')
        if key=='gecko':
            s=f'<ellipse cx="250" cy="180" rx="95" ry="45" fill="{GREEN}"/><path d="M160 180Q80 90 75 280" fill="none" stroke="{GREEN}" stroke-width="20"/>'+circle(345,155,30,GREEN)+circle(357,148,9,GOLD)
            for x,y in [(180,130),(275,130),(180,240),(275,240)]:s+=line(x,180,x,y,GREEN,12)+''.join(circle(x-15+i*8,y,5,GOLD) for i in range(5))
            return s+label('A small climbing lizard with toe pads')
        if key=='sweetcorn':return f'<ellipse cx="250" cy="170" rx="60" ry="120" fill="{GOLD}"/>'+''.join(circle(218+(i%4)*21,85+(i//4)*25,8,'#cc9326') for i in range(28))+f'<path d="M180 110Q105 280 235 300M320 110Q395 280 265 300" fill="{GREEN}"/>'+label('Sweet kernels on a corn cob')
        if key=='tape':return circle(220,160,90,'#e8d6a7')+circle(220,160,45,'white')+rect(220,205,200,45,'#e8d6a7')+label('A sticky strip for joining things')
        if key=='hem':return f'<path d="M150 60h200v225H270V155h-40v130h-80Z" fill="{BLUE}"/>'+line(155,263,225,263,GOLD,10)+line(275,263,345,263,GOLD,10)+arrow(60,263,147,263)+label('The folded, sewn edge of clothing')
        if key=='badge':return rect(145,95,220,150,BLUE)+rect(210,70,90,35,GOLD)+circle(205,155,25,'white')+text(290,178,'NAME',24,'white')+label('A label you wear to identify yourself')
        if key=='lotion':return rect(185,85,130,210,'#d5ebee')+rect(200,55,100,35,BLUE)+text(250,175,'SKIN',24)+circle(250,225,20,'white')+label('A liquid cream for skin')
        if key=='pipe':return line(100,95,100,240,BLUE,35)+line(100,240,350,240,BLUE,35)+line(350,240,350,120,BLUE,35)+arrow(175,225,260,225)+label('A hollow tube that carries water')
        if key=='torch':return rect(110,130,210,90,BLUE)+circle(325,175,45,GOLD)+f'<path d="M360 145L460 65V285L360 205Z" fill="#fff0bf"/>'+label('A portable electric light')
        if key=='showerhead':return line(100,50,300,50,BLUE,18)+line(300,50,345,100,BLUE,18)+f'<ellipse cx="345" cy="100" rx="65" ry="23" fill="{INK}"/>'+''.join(line(285+i*20,125,255+i*20,250,BLUE,3) for i in range(7))+label('The head that sprays shower water')
        if key in ('earmuff','headphone'):
            s=f'<path d="M120 210V130A130 100 0 012380 130V210" fill="none" stroke="{BLUE}" stroke-width="18"/>'.replace('012380','0 1 380')+rect(110,155,55,100,BLUE)+rect(335,155,55,100,BLUE)
            return s+(text(250,205,'♪',65) if key=='headphone' else text(250,205,'❄',65))+label('Listen through ear speakers' if key=='headphone' else 'Keep your ears warm in cold weather')
        if key=='carton':return rect(155,110,190,180,BLUE)+f'<path d="M155 110L200 60H300L345 110Z" fill="#d5ebee"/>'+line(205,58,295,58,INK,4)+label('A cardboard container for a drink')
        s=rect(130,150,230,140,GOLD)+apple(200,105)+book(280,50)+arrow(280,135,285,220)
        return s+label('Food and household shopping' if key=='grocery' else 'Put things into a bag for a trip')
    if key in ('snowball','toboggan'):
        if key=='snowball':return rect(55,45,390,260,'#d5ebee')+circle(250,185,70,'white')+text(115,105,'❄',35)+text(400,265,'❄',35)+label('A ball made from packed snow')
        return line(70,80,430,280,BLUE,4)+line(120,170,300,245,'#8d542a',20)+line(110,215,315,290,'#8d542a',7)+label('A sled that slides down snow')
    if key=='weight':return rect(125,150,250,130,BLUE)+rect(185,180,130,55,'white')+text(250,218,'250 g',30)+apple(250,95)+label('How heavy something is')
    if key=='labor':return person(105,80)+person(390,80,BLUE)+rect(190,165,110,90,GOLD)+line(130,145,190,180,GREEN,10)+line(370,145,300,180,BLUE,10)+label('Physical work that takes effort')
    if key=='birth':return person(150,70)+circle(290,180,30,'#ecc6a5')+rect(245,200,150,70,'#d5ebee')+label('A baby comes into the world')
    if key=='gravy':return f'<ellipse cx="250" cy="200" rx="130" ry="60" fill="{BLUE}"/><ellipse cx="250" cy="190" rx="105" ry="40" fill="#8d542a"/>'+line(320,160,400,80,INK,9)+label('A sauce served with a meal')
    if key=='courthouse':return rect(105,120,290,160,'#dce4dc')+f'<path d="M85 120L250 45L415 120Z" fill="{BLUE}"/>'+''.join(rect(135+i*65,140,30,120,'white') for i in range(4))+text(250,105,'⚖',35,'white')+label('A building where legal cases are heard')
    if key=='solid':return f'<path d="M125 140L250 70L375 140L250 210Z" fill="#6cacc5"/><path d="M125 140V270L250 335V210Z" fill="{BLUE}"/><path d="M250 210V335L375 270V140Z" fill="#32657f"/>'+label('A material that holds its shape')
    if key=='signpost':return line(250,45,250,300,'#8d542a',18)+f'<path d="M95 85H350L390 120L350 155H95Z" fill="{BLUE}"/><path d="M405 190H145L105 225L145 260H405Z" fill="{GREEN}"/>'+text(230,130,'TOWN',26,'white')+text(275,235,'PARK',26,'white')+label('A post showing directions')
    return render(key)
def main():
    path=ROOT/'data/curriculum.json';words=json.loads(path.read_text(encoding='utf-8'));by={w['english']:w for w in words};changes=[]
    for key,source in CLONES.items():
        w=by[key];other=by[source]
        for field in ('image','image_source','image_creator','image_license'):w[field]=other[field]
        w['image_review']='Full-sheet review: corrected a homograph by choosing '+source+' for the intended sense.';changes.append(key)
    weekdays=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];months=['January','February','March','April','May','June','July','August','September','October','November','December']
    numbers={'zero':0,'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
    for w in words:
        key=w['english'];body=None
        if key in SPECIAL or key=='cell':body=extra(key)
        elif key in weekdays or key in months:
            names=weekdays if key in weekdays else months;body=''
            for i,name in enumerate(names):x=50+(i%4)*110;y=50+(i//4)*85;body+=rect(x,y,96,64,GREEN if name==key else '#dce4dc')+text(x+48,y+24,i+1,16,'white' if name==key else INK)+text(x+48,y+48,name[:3],17,'white' if name==key else INK)
            body+=label(key+' — '+('day of the week' if key in weekdays else 'month of the year'));w['category']='Time and position'
        elif key in numbers:body=text(250,155,numbers[key],110)+''.join(circle(75+(i%5)*85,210+(i//5)*60,17,GREEN) for i in range(numbers[key]))+label('A count of '+str(numbers[key]))
        if body:
            filename=f'reviewed-{w["id"]}.svg';svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 390"><title>{html.escape(key)} — reviewed scene</title><rect width="500" height="390" rx="20" fill="#fffef9"/>{body}</svg>'
            (ROOT/'static/images'/filename).write_text(svg,encoding='utf-8');w.update(image='images/'+filename,image_source='https://github.com/matoug24/arabic/blob/main/static/images/'+filename,image_creator='Arabic, together project — original reviewed SVG scene',image_license='CC BY-SA 4.0',image_candidate=None,image_approved=False,image_review='Full-sheet review: replaced ambiguous, noisy or wrong-sense match with a concept-specific scene. Parent approval still required.');changes.append(key)
        if key in MEANINGS:w['meaning']=MEANINGS[key]
        if key=='cell':w['category']='School and learning';w['topic']='Science and the living world'
        if key in {'capital','courthouse'}:w['category']='Places and travel'
    path.write_text(json.dumps(words,ensure_ascii=False,indent=2),encoding='utf-8');(ROOT/'data/image_corrections.json').write_text(json.dumps(sorted(set(changes)),ensure_ascii=False,indent=2),encoding='utf-8');print('Reviewed/corrected pictures:',len(set(changes)))
if __name__=='__main__':main()
