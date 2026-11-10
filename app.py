"""Andrablicken Scouting Network.

The application supports a local demo mode and a hardened hosted pilot mode.
Match video remains at its authorized external provider; only links are stored.
"""
import os, sqlite3, hashlib, hmac, secrets, json, re, uuid
from pathlib import Path
from datetime import datetime
from urllib.parse import urlsplit
from io import BytesIO
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pdf_reports import render_pdf, PLAYER_FIELDS, OPP_FIELDS

ROOT=Path(__file__).resolve().parent
ENV=os.environ.get('ANDRABLICKEN_ENV','development').strip().lower()
PRODUCTION=ENV=='production'
STORE=Path(os.environ.get('ANDRABLICKEN_STORAGE',str(ROOT/'data')))
STORE.mkdir(parents=True,exist_ok=True)
UPLOADS=STORE/'uploads';UPLOADS.mkdir(exist_ok=True)
DB=STORE/'portal.sqlite3'
SECRET=os.environ.get('ANDRABLICKEN_SESSION_SECRET','').strip()
if not SECRET:
    if PRODUCTION:raise RuntimeError('ANDRABLICKEN_SESSION_SECRET krävs i produktion.')
    secret_path=STORE/'.session_key'
    if not secret_path.exists():secret_path.write_text(secrets.token_hex(32),encoding='ascii')
    SECRET=secret_path.read_text(encoding='ascii').strip()
if len(SECRET)<32:raise RuntimeError('Sessionshemligheten måste vara minst 32 tecken.')
ALLOW_REGISTRATION=os.environ.get('ANDRABLICKEN_ALLOW_REGISTRATION','0' if PRODUCTION else '1')=='1'
SEED_DEMO=os.environ.get('ANDRABLICKEN_SEED_DEMO','0')=='1'
DEMO_PASSWORD=os.environ.get('ANDRABLICKEN_DEMO_PASSWORD','')
if SEED_DEMO and (PRODUCTION or len(DEMO_PASSWORD)<10):
    raise RuntimeError('Demodata får endast aktiveras lokalt med ANDRABLICKEN_DEMO_PASSWORD på minst 10 tecken.')

app=FastAPI(title='Andrablicken Scouting Network')
if PRODUCTION:
    allowed_hosts=[h.strip() for h in os.environ.get('ANDRABLICKEN_ALLOWED_HOSTS','').split(',') if h.strip()]
    if not allowed_hosts:raise RuntimeError('ANDRABLICKEN_ALLOWED_HOSTS krävs i produktion.')
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=allowed_hosts)
app.add_middleware(SessionMiddleware,secret_key=SECRET,https_only=PRODUCTION,same_site='lax',session_cookie='andrablicken_session',max_age=60*60*8)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
tmpl=Jinja2Templates(directory=str(ROOT/'templates'))

@app.middleware('http')
async def security_headers(request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='SAMEORIGIN'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    if PRODUCTION:response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    return response

PLAYER_GROUPS=[('Identitet och match',PLAYER_FIELDS[:11]),('Matchbild och position',PLAYER_FIELDS[11:16]),('Bedömning',PLAYER_FIELDS[16:23]),('Slutsats och rekommendation',PLAYER_FIELDS[23:])]
OPP_GROUPS=[('Identitet och match',OPP_FIELDS[:8]),('Matchbild och laguppställning',OPP_FIELDS[8:12]),('Spelmodell och press',OPP_FIELDS[12:18]),('Spelare och fasta situationer',OPP_FIELDS[18:24]),('Organisation, styrkor och analys',OPP_FIELDS[24:29]),('Matchplan och slutsatser',OPP_FIELDS[29:])]
QUESTIONS=[
 {'q':'Vad bör en scout prioritera vid en första observation?', 'a':['Bekräfta förutfattade uppfattningar','Dokumentera konkreta beteenden och matchsituationer','Endast titta på mål och assist'], 'correct':1},
 {'q':'Vad är en observation?', 'a':['Spelaren flyttade in centralt i minut 23','Spelaren är förmodligen lat','Spelaren passar inte i någon klubb'], 'correct':0},
 {'q':'Hur bör osäkerhet beskrivas?', 'a':['Utelämnas för att rapporten ska se starkare ut','Redovisas med observationsunderlag och möjliga begränsningar','Ersättas med ett poängbetyg'], 'correct':1},
 {'q':'Vilken användning av video är rätt?', 'a':['Ladda upp valfri ligamatch på vår egen server','Använda matchmaterial enligt rättighetshavarens och klubbens tillstånd','Sprida matchfilen till alla nätverkets medlemmar'], 'correct':1},
 {'q':'Vad är en bra slutrekommendation?', 'a':['Han känns bra','Observation → analys → förslag på nästa steg','En lista med många adjektiv'], 'correct':1},
]
COURSE_LESSONS=[
 ('01','Scoutens roll och arbetsmetod','Vad gör en scout?', 'En scoutrapport ska hjälpa en klubb att fatta ett fotbollsbeslut. Skilj därför mellan fakta, observationer, tolkningar och rekommendationer. Bestäm före matchen vad uppdraget ska besvara, till exempel hur laget bygger upp eller om en specifik spelare passar en roll.'),
 ('02','Observation och dokumentation','Från match till belägg','Skriv ned konkreta händelser med minut, matchsituation och kontext. Exempel: ”23:40 – vänsterbacken kliver in centralt i uppspel och skapar en fri passningslinje”. Undvik personliga omdömen utan bevis. Observera flera matcher när underlaget är tunt.'),
 ('03','Bedömning och rekommendation','Gör analysen användbar','Sammanfatta det du faktiskt såg. Separera spelarens styrkor och utvecklingsområden från hur de passar klubbens spelmodell. Avsluta med tydlig rekommendation: bevaka igen, analysera en annan match, provträna eller avstå – samt säkerhet i bedömningen.'),
]

def db():
    con=sqlite3.connect(DB,timeout=30)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=30000')
    return con

def password_hash(password):
    salt=os.urandom(16)
    hashed=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,260000)
    return salt.hex()+':'+hashed.hex()

def verify_password(password,stored):
    try:
        salt,h=stored.split(':')
        candidate=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),260000)
        return hmac.compare_digest(candidate,bytes.fromhex(h))
    except Exception:return False

def init_db():
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS clubs(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','scout','club')),club_id INTEGER REFERENCES clubs(id));
        CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY, club_id INTEGER NOT NULL REFERENCES clubs(id),title TEXT NOT NULL,fixture TEXT NOT NULL,match_date TEXT,deadline TEXT,video_url TEXT,instructions TEXT,scout_id INTEGER REFERENCES users(id),created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY,assignment_id INTEGER NOT NULL REFERENCES assignments(id),scout_id INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL, UNIQUE(assignment_id,scout_id));
        CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,assignment_id INTEGER NOT NULL REFERENCES assignments(id),scout_id INTEGER NOT NULL REFERENCES users(id),kind TEXT NOT NULL CHECK(kind IN ('player','opposition')),payload TEXT NOT NULL DEFAULT '{}',status TEXT NOT NULL DEFAULT 'draft',review_note TEXT DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,uploaded_file TEXT);
        CREATE TABLE IF NOT EXISTS lessons(user_id INTEGER NOT NULL REFERENCES users(id),lesson_index INTEGER NOT NULL,done_at TEXT NOT NULL,PRIMARY KEY(user_id,lesson_index));
        CREATE TABLE IF NOT EXISTS quiz_results(user_id INTEGER PRIMARY KEY REFERENCES users(id),best_score INTEGER NOT NULL,passed INTEGER NOT NULL,finished_at TEXT NOT NULL);
        ''')
        user_columns={row['name'] for row in con.execute('PRAGMA table_info(users)').fetchall()}
        if 'active' not in user_columns:
            con.execute('ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
        if 'session_version' not in user_columns:
            con.execute('ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1')
        con.execute('PRAGMA journal_mode=WAL')
        count=con.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c']
        if not count and SEED_DEMO:
            con.execute('INSERT INTO clubs(name) VALUES (?)',('Demo IF',))
            club_id=con.execute('SELECT id FROM clubs WHERE name=?',('Demo IF',)).fetchone()['id']
            for name,email,role,cid in [('Administratör','admin@andrablicken.demo','admin',None),('Demo Scout','scout@andrablicken.demo','scout',None),('Demo Sportchef','klubb@andrablicken.demo','club',club_id)]:
                con.execute('INSERT INTO users(name,email,password_hash,role,club_id) VALUES (?,?,?,?,?)',(name,email,password_hash(DEMO_PASSWORD),role,cid))
            scout=con.execute("SELECT id FROM users WHERE role='scout'").fetchone()['id']
            now=datetime.now().isoformat(timespec='minutes')
            con.execute('INSERT INTO assignments(club_id,title,fixture,match_date,deadline,video_url,instructions,scout_id,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                        (club_id,'Pilot: Spelaranalys','Exempellag A – Exempellag B','2026-11-01','2026-11-30','https://www.veo.co/','Bedöm en central mittfältare. Demolänk till leverantörens startsida, inte en verklig match.',scout,now))
            con.execute('INSERT INTO assignments(club_id,title,fixture,match_date,deadline,video_url,instructions,scout_id,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                        (club_id,'Pilot: Motståndaranalys','Exempellag C – Exempellag D','2026-11-08','2026-11-30','','Analysera press, omställningar och fasta situationer.',None,now))
        elif not count and PRODUCTION:
            email=os.environ.get('ANDRABLICKEN_BOOTSTRAP_ADMIN_EMAIL','').strip().lower()
            password=os.environ.get('ANDRABLICKEN_BOOTSTRAP_ADMIN_PASSWORD','')
            name=os.environ.get('ANDRABLICKEN_BOOTSTRAP_ADMIN_NAME','Administratör').strip()[:120]
            if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(password)<14:
                raise RuntimeError('En giltig bootstrap-admin och lösenord på minst 14 tecken krävs för en tom produktionsdatabas.')
            con.execute('INSERT INTO users(name,email,password_hash,role,club_id) VALUES (?,?,?,?,NULL)',
                        (name,email,password_hash(password),'admin'))
init_db()

def get_user(request):
    uid=request.session.get('uid')
    if not uid:return None
    with db() as con:user=con.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    if not user or not user['active'] or request.session.get('sv')!=user['session_version']:
        request.session.clear()
        return None
    return user

def require_user(request,roles=None):
    user=get_user(request)
    if not user:raise HTTPException(401,'Du måste logga in.')
    if roles and user['role'] not in roles:raise HTTPException(403,'Du saknar behörighet.')
    return user

def token(request):
    if 'csrf' not in request.session:request.session['csrf']=secrets.token_urlsafe(32)
    return request.session['csrf']

def check_token(request, value):
    if not value or not hmac.compare_digest(str(value),str(request.session.get('csrf',''))):
        raise HTTPException(403,'Ogiltig formulärtoken. Ladda om sidan.')

def page(request,name,**context):
    return tmpl.TemplateResponse(request,name,{'user':get_user(request),'csrf':token(request),'flash':request.session.pop('flash',None),'allow_registration':ALLOW_REGISTRATION,'seed_demo':SEED_DEMO,**context})

def go(url):return RedirectResponse(url,status_code=303)

def notice(request,message):request.session['flash']=message

def fetch_assignment(aid):
    with db() as con:return con.execute('SELECT a.*,c.name AS club_name,u.name AS scout_name FROM assignments a JOIN clubs c ON c.id=a.club_id LEFT JOIN users u ON u.id=a.scout_id WHERE a.id=?',(aid,)).fetchone()

def can_access_assignment(user,a,full=False):
    if user['role']=='admin':return True
    if user['role']=='club':return user['club_id']==a['club_id']
    if full:return a['scout_id']==user['id']
    return a['scout_id'] is None or a['scout_id']==user['id']

def fetch_report(rid):
    with db() as con:return con.execute('SELECT r.*,a.club_id,a.title AS assignment_title,a.fixture,a.video_url FROM reports r JOIN assignments a ON a.id=r.assignment_id WHERE r.id=?',(rid,)).fetchone()

def can_view_report(user,r):
    if user['role']=='admin':return True
    if user['role']=='scout':return r['scout_id']==user['id']
    return user['role']=='club' and user['club_id']==r['club_id'] and r['status']=='approved'

def safe_video_url(value):
    value=(value or '').strip()
    if not value:return ''
    try:
        parts=urlsplit(value)
        if parts.scheme not in ('https','http') or not parts.netloc or parts.username:return ''
        return value
    except Exception:return ''

@app.get('/',response_class=HTMLResponse)
def landing():return FileResponse(ROOT/'static'/'index.html')

@app.get('/login',response_class=HTMLResponse)
def login_page(request:Request):return page(request,'login.html')

@app.post('/login')
async def login(request:Request,email:str=Form(...),password:str=Form(...),csrf:str=Form(...)):
    check_token(request,csrf)
    with db() as con:u=con.execute('SELECT * FROM users WHERE email=?',(email.lower().strip(),)).fetchone()
    if not u or not verify_password(password,u['password_hash']):
        return page(request,'login.html',error='Fel e-postadress eller lösenord.')
    if not u['active']:
        return page(request,'login.html',error='Kontot är avstängt. Kontakta administratören.')
    request.session.clear();request.session['uid']=u['id'];request.session['sv']=u['session_version'];request.session['csrf']=secrets.token_urlsafe(32)
    return go('/app')

@app.get('/register',response_class=HTMLResponse)
def register_page(request:Request):
    if not ALLOW_REGISTRATION:raise HTTPException(404)
    return page(request,'register.html')

@app.post('/register')
async def register(request:Request,name:str=Form(...),email:str=Form(...),password:str=Form(...),role:str=Form(...),club_name:str=Form(''),csrf:str=Form(...)):
    if not ALLOW_REGISTRATION:raise HTTPException(404)
    check_token(request,csrf)
    name=name.strip()[:120];email=email.strip().lower()[:254]
    if role not in ['club','scout'] or not name or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(password)<10:
        return page(request,'register.html',error='Ange korrekt namn, e-postadress och lösenord (minst 10 tecken).')
    if role=='club' and not club_name.strip():return page(request,'register.html',error='Ange klubbnamn.')
    try:
        with db() as con:
            club_id=None
            if role=='club':
                existing=con.execute('SELECT id FROM clubs WHERE name=?',(club_name.strip(),)).fetchone()
                if existing:return page(request,'register.html',error='Klubbnamnet finns redan i pilotportalen. Kontakta administratören.')
                con.execute('INSERT INTO clubs(name) VALUES (?)',(club_name.strip()[:120],))
                club_id=con.execute('SELECT last_insert_rowid() AS id').fetchone()['id']
            con.execute('INSERT INTO users(name,email,password_hash,role,club_id) VALUES (?,?,?,?,?)',(name,email,password_hash(password),role,club_id))
            uid=con.execute('SELECT last_insert_rowid() AS id').fetchone()['id']
    except sqlite3.IntegrityError:return page(request,'register.html',error='E-postadressen är redan registrerad.')
    request.session.clear();request.session['uid']=uid;request.session['sv']=1;request.session['csrf']=secrets.token_urlsafe(32)
    return go('/app')

@app.post('/logout')
async def logout(request:Request,csrf:str=Form(...)):
    check_token(request,csrf);request.session.clear();return go('/')

@app.get('/account',response_class=HTMLResponse)
def account_page(request:Request):
    require_user(request)
    return page(request,'account.html')

@app.post('/account/password')
async def change_password(request:Request,current_password:str=Form(...),new_password:str=Form(...),confirm_password:str=Form(...),csrf:str=Form(...)):
    user=require_user(request);check_token(request,csrf)
    if new_password!=confirm_password:
        return page(request,'account.html',error='De nya lösenorden matchar inte.')
    if len(new_password)<14:
        return page(request,'account.html',error='Det nya lösenordet måste vara minst 14 tecken.')
    if not verify_password(current_password,user['password_hash']):
        return page(request,'account.html',error='Nuvarande lösenord är fel.')
    with db() as con:
        con.execute('UPDATE users SET password_hash=?,session_version=session_version+1 WHERE id=?',(password_hash(new_password),user['id']))
        session_version=con.execute('SELECT session_version FROM users WHERE id=?',(user['id'],)).fetchone()['session_version']
    request.session['sv']=session_version
    notice(request,'Lösenordet har ändrats. Andra inloggade sessioner har avslutats.')
    return go('/account')

def admin_form_values(name,email,role,club_id):
    name=name.strip()[:120]
    email=email.strip().lower()[:254]
    if not name or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):
        raise ValueError('Ange ett namn och en giltig e-postadress.')
    if role not in ('admin','scout','club'):
        raise ValueError('Ogiltig roll.')
    selected_club=int(club_id) if role=='club' and str(club_id).isdigit() else None
    if role=='club' and selected_club is None:
        raise ValueError('Ett klubbkonto måste kopplas till en klubb.')
    return name,email,role,selected_club

@app.get('/admin/users',response_class=HTMLResponse)
def admin_users_page(request:Request):
    require_user(request,('admin',))
    with db() as con:
        clubs=con.execute('SELECT c.*,COUNT(u.id) AS user_count FROM clubs c LEFT JOIN users u ON u.club_id=c.id GROUP BY c.id ORDER BY c.name').fetchall()
        users=con.execute('SELECT u.*,c.name AS club_name FROM users u LEFT JOIN clubs c ON c.id=u.club_id ORDER BY u.active DESC,u.name').fetchall()
    return page(request,'admin_users.html',clubs=clubs,users=users)

@app.post('/admin/clubs')
async def admin_create_club(request:Request,name:str=Form(...),csrf:str=Form(...)):
    require_user(request,('admin',));check_token(request,csrf)
    name=name.strip()[:120]
    if not name:raise HTTPException(400,'Klubbnamn krävs.')
    try:
        with db() as con:con.execute('INSERT INTO clubs(name) VALUES (?)',(name,))
    except sqlite3.IntegrityError:
        notice(request,'Klubbnamnet finns redan.')
        return go('/admin/users')
    notice(request,f'Klubben {name} har skapats.')
    return go('/admin/users')

@app.post('/admin/users')
async def admin_create_user(request:Request,name:str=Form(...),email:str=Form(...),role:str=Form(...),club_id:str=Form(''),password:str=Form(...),confirm_password:str=Form(...),csrf:str=Form(...)):
    require_user(request,('admin',));check_token(request,csrf)
    try:name,email,role,selected_club=admin_form_values(name,email,role,club_id)
    except ValueError as exc:
        notice(request,str(exc));return go('/admin/users')
    if password!=confirm_password or len(password)<14:
        notice(request,'Lösenorden måste matcha och vara minst 14 tecken.')
        return go('/admin/users')
    try:
        with db() as con:
            if selected_club and not con.execute('SELECT 1 FROM clubs WHERE id=?',(selected_club,)).fetchone():raise ValueError('Klubben finns inte.')
            con.execute('INSERT INTO users(name,email,password_hash,role,club_id,active,session_version) VALUES (?,?,?,?,?,1,1)',(name,email,password_hash(password),role,selected_club))
    except sqlite3.IntegrityError:
        notice(request,'E-postadressen används redan.')
        return go('/admin/users')
    except ValueError as exc:
        notice(request,str(exc));return go('/admin/users')
    notice(request,f'Kontot för {name} har skapats.')
    return go('/admin/users')

@app.post('/admin/users/{user_id}/update')
async def admin_update_user(request:Request,user_id:int,name:str=Form(...),email:str=Form(...),role:str=Form(...),club_id:str=Form(''),csrf:str=Form(...)):
    admin=require_user(request,('admin',));check_token(request,csrf)
    try:name,email,role,selected_club=admin_form_values(name,email,role,club_id)
    except ValueError as exc:
        notice(request,str(exc));return go('/admin/users')
    with db() as con:
        target=con.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
        if not target:raise HTTPException(404)
        if selected_club and not con.execute('SELECT 1 FROM clubs WHERE id=?',(selected_club,)).fetchone():
            notice(request,'Klubben finns inte.');return go('/admin/users')
        active_admins=con.execute("SELECT COUNT(*) AS c FROM users WHERE role='admin' AND active=1").fetchone()['c']
        if target['role']=='admin' and target['active'] and role!='admin' and active_admins<=1:
            notice(request,'Den sista aktiva administratören kan inte byta roll.');return go('/admin/users')
        if user_id==admin['id'] and role!='admin':
            notice(request,'Du kan inte ta bort din egen administratörsroll.');return go('/admin/users')
        try:
            con.execute('UPDATE users SET name=?,email=?,role=?,club_id=?,session_version=session_version+1 WHERE id=?',(name,email,role,selected_club,user_id))
        except sqlite3.IntegrityError:
            notice(request,'E-postadressen används redan.');return go('/admin/users')
        new_version=con.execute('SELECT session_version FROM users WHERE id=?',(user_id,)).fetchone()['session_version']
    if user_id==admin['id']:request.session['sv']=new_version
    notice(request,f'Kontot för {name} har uppdaterats.')
    return go('/admin/users')

@app.post('/admin/users/{user_id}/status')
async def admin_user_status(request:Request,user_id:int,action:str=Form(...),csrf:str=Form(...)):
    admin=require_user(request,('admin',));check_token(request,csrf)
    active=1 if action=='activate' else 0 if action=='deactivate' else None
    if active is None:raise HTTPException(400)
    if user_id==admin['id'] and not active:
        notice(request,'Du kan inte stänga av ditt eget konto.');return go('/admin/users')
    with db() as con:
        target=con.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
        if not target:raise HTTPException(404)
        active_admins=con.execute("SELECT COUNT(*) AS c FROM users WHERE role='admin' AND active=1").fetchone()['c']
        if not active and target['role']=='admin' and target['active'] and active_admins<=1:
            notice(request,'Den sista aktiva administratören kan inte stängas av.');return go('/admin/users')
        con.execute('UPDATE users SET active=?,session_version=session_version+1 WHERE id=?',(active,user_id))
    notice(request,'Kontot har aktiverats.' if active else 'Kontot har stängts av och dess sessioner har avslutats.')
    return go('/admin/users')

@app.post('/admin/users/{user_id}/password')
async def admin_reset_password(request:Request,user_id:int,password:str=Form(...),confirm_password:str=Form(...),csrf:str=Form(...)):
    admin=require_user(request,('admin',));check_token(request,csrf)
    if password!=confirm_password or len(password)<14:
        notice(request,'Lösenorden måste matcha och vara minst 14 tecken.');return go('/admin/users')
    with db() as con:
        target=con.execute('SELECT name FROM users WHERE id=?',(user_id,)).fetchone()
        if not target:raise HTTPException(404)
        con.execute('UPDATE users SET password_hash=?,session_version=session_version+1 WHERE id=?',(password_hash(password),user_id))
        new_version=con.execute('SELECT session_version FROM users WHERE id=?',(user_id,)).fetchone()['session_version']
    if user_id==admin['id']:request.session['sv']=new_version
    notice(request,f'Lösenordet för {target["name"]} har återställts och gamla sessioner har avslutats.')
    return go('/admin/users')

@app.get('/app',response_class=HTMLResponse)
def dashboard(request:Request):
    u=require_user(request)
    with db() as con:
        if u['role']=='admin':
            assignments=con.execute('SELECT a.*,c.name AS club_name,u.name AS scout_name FROM assignments a JOIN clubs c ON c.id=a.club_id LEFT JOIN users u ON u.id=a.scout_id ORDER BY a.id DESC').fetchall()
            reports=con.execute('SELECT r.*,a.title AS assignment_title,c.name AS club_name FROM reports r JOIN assignments a ON a.id=r.assignment_id JOIN clubs c ON c.id=a.club_id ORDER BY r.id DESC LIMIT 12').fetchall()
        elif u['role']=='club':
            assignments=con.execute('SELECT a.*,c.name AS club_name,u.name AS scout_name FROM assignments a JOIN clubs c ON c.id=a.club_id LEFT JOIN users u ON u.id=a.scout_id WHERE a.club_id=? ORDER BY a.id DESC',(u['club_id'],)).fetchall()
            reports=con.execute('SELECT r.*,a.title AS assignment_title,c.name AS club_name FROM reports r JOIN assignments a ON a.id=r.assignment_id JOIN clubs c ON c.id=a.club_id WHERE a.club_id=? AND r.status=? ORDER BY r.id DESC',(u['club_id'],'approved')).fetchall()
        else:
            assignments=con.execute('SELECT a.*,c.name AS club_name,u.name AS scout_name FROM assignments a JOIN clubs c ON c.id=a.club_id LEFT JOIN users u ON u.id=a.scout_id WHERE a.scout_id=? OR a.scout_id IS NULL ORDER BY a.id DESC',(u['id'],)).fetchall()
            reports=con.execute('SELECT r.*,a.title AS assignment_title,c.name AS club_name FROM reports r JOIN assignments a ON a.id=r.assignment_id JOIN clubs c ON c.id=a.club_id WHERE r.scout_id=? ORDER BY r.id DESC',(u['id'],)).fetchall()
    return page(request,'dashboard.html',assignments=assignments,reports=reports)

@app.get('/assignments/new',response_class=HTMLResponse)
def new_assignment_page(request:Request):
    u=require_user(request,('admin','club'))
    with db() as con:
        clubs=con.execute('SELECT * FROM clubs ORDER BY name').fetchall() if u['role']=='admin' else con.execute('SELECT * FROM clubs WHERE id=?',(u['club_id'],)).fetchall()
        scouts=con.execute("SELECT id,name,email FROM users WHERE role='scout' ORDER BY name").fetchall()
    return page(request,'new_assignment.html',clubs=clubs,scouts=scouts)

@app.post('/assignments/new')
async def new_assignment(request:Request,club_id:int=Form(...),title:str=Form(...),fixture:str=Form(...),match_date:str=Form(''),deadline:str=Form(''),video_url:str=Form(''),instructions:str=Form(''),scout_id:str=Form(''),csrf:str=Form(...)):
    u=require_user(request,('admin','club'));check_token(request,csrf)
    if u['role']=='club' and u['club_id']!=club_id:raise HTTPException(403)
    if not title.strip() or not fixture.strip():raise HTTPException(400,'Titel och match krävs.')
    video=safe_video_url(video_url)
    if video_url.strip() and not video:raise HTTPException(400,'Videolänken måste börja med https:// eller http://')
    scout=int(scout_id) if scout_id.isdigit() else None
    with db() as con:
        if not con.execute('SELECT 1 FROM clubs WHERE id=?',(club_id,)).fetchone():raise HTTPException(404)
        if scout and not con.execute("SELECT 1 FROM users WHERE id=? AND role='scout'",(scout,)).fetchone():raise HTTPException(400)
        con.execute('INSERT INTO assignments(club_id,title,fixture,match_date,deadline,video_url,instructions,scout_id,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                    (club_id,title.strip()[:160],fixture.strip()[:160],match_date[:20],deadline[:20],video,instructions[:5000],scout,datetime.now().isoformat(timespec='minutes')))
        aid=con.execute('SELECT last_insert_rowid() AS id').fetchone()['id']
    notice(request,'Uppdraget är skapat.')
    return go(f'/assignments/{aid}')

@app.get('/assignments/{aid}',response_class=HTMLResponse)
def assignment_detail(request:Request,aid:int):
    u=require_user(request);a=fetch_assignment(aid)
    if not a:raise HTTPException(404)
    if not can_access_assignment(u,a):raise HTTPException(403)
    with db() as con:
        reports=con.execute('SELECT r.*,u.name AS scout_name FROM reports r JOIN users u ON u.id=r.scout_id WHERE r.assignment_id=? ORDER BY r.id DESC',(aid,)).fetchall()
        if u['role']=='club':reports=[r for r in reports if r['status']=='approved']
        elif u['role']=='scout':reports=[r for r in reports if r['scout_id']==u['id']]
        applicants=con.execute('SELECT ap.*,u.name,u.email FROM applications ap JOIN users u ON u.id=ap.scout_id WHERE ap.assignment_id=?',(aid,)).fetchall() if u['role'] in ('club','admin') else []
        has_applied=con.execute('SELECT 1 FROM applications WHERE assignment_id=? AND scout_id=?',(aid,u['id'])).fetchone() is not None if u['role']=='scout' else False
    full=can_access_assignment(u,a,full=True)
    return page(request,'assignment.html',a=a,reports=reports,applicants=applicants,has_applied=has_applied,full=full)

@app.post('/assignments/{aid}/apply')
async def apply(request:Request,aid:int,csrf:str=Form(...)):
    u=require_user(request,('scout',));check_token(request,csrf);a=fetch_assignment(aid)
    if not a:raise HTTPException(404)
    if a['scout_id']:raise HTTPException(409,'Uppdraget är redan tillsatt.')
    with db() as con:con.execute('INSERT OR IGNORE INTO applications(assignment_id,scout_id,created_at) VALUES (?,?,?)',(aid,u['id'],datetime.now().isoformat(timespec='minutes')))
    notice(request,'Intresseanmälan skickad till klubben.')
    return go(f'/assignments/{aid}')

@app.post('/assignments/{aid}/assign/{scout_id}')
async def assign(request:Request,aid:int,scout_id:int,csrf:str=Form(...)):
    u=require_user(request,('admin','club'));check_token(request,csrf);a=fetch_assignment(aid)
    if not a:raise HTTPException(404)
    if u['role']=='club' and a['club_id']!=u['club_id']:raise HTTPException(403)
    with db() as con:
        if not con.execute("SELECT 1 FROM users WHERE id=? AND role='scout'",(scout_id,)).fetchone():raise HTTPException(400)
        con.execute('UPDATE assignments SET scout_id=? WHERE id=?',(scout_id,aid))
    notice(request,'Scouten har tilldelats uppdraget.')
    return go(f'/assignments/{aid}')

@app.post('/assignments/{aid}/video')
async def edit_video(request:Request,aid:int,video_url:str=Form(''),csrf:str=Form(...)):
    u=require_user(request,('admin','club'));check_token(request,csrf);a=fetch_assignment(aid)
    if not a:raise HTTPException(404)
    if u['role']=='club' and a['club_id']!=u['club_id']:raise HTTPException(403)
    video=safe_video_url(video_url)
    if video_url.strip() and not video:raise HTTPException(400,'Felaktig videolänk.')
    with db() as con:con.execute('UPDATE assignments SET video_url=? WHERE id=?',(video,aid))
    notice(request,'Videolänken uppdaterad. Kontrollera att scouten har rätt behörighet hos videoleverantören.')
    return go(f'/assignments/{aid}')

@app.post('/assignments/{aid}/reports')
async def create_report(request:Request,aid:int,kind:str=Form(...),csrf:str=Form(...)):
    u=require_user(request,('scout','admin'));check_token(request,csrf);a=fetch_assignment(aid)
    if not a:raise HTTPException(404)
    if u['role']=='scout' and a['scout_id']!=u['id']:raise HTTPException(403)
    if kind not in ('player','opposition'):raise HTTPException(400)
    now=datetime.now().isoformat(timespec='minutes')
    payload={'scout_name':u['name'],'match_date':a['match_date'],'source':a['video_url'],'game_context':a['instructions']}
    with db() as con:
        con.execute("INSERT INTO reports(assignment_id,scout_id,kind,payload,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",(aid,u['id'],kind,json.dumps(payload,ensure_ascii=False),'draft',now,now))
        rid=con.execute('SELECT last_insert_rowid() AS id').fetchone()['id']
    return go(f'/reports/{rid}/edit')

@app.get('/reports/{rid}/edit',response_class=HTMLResponse)
def edit_report(request:Request,rid:int):
    u=require_user(request,('scout','admin'));r=fetch_report(rid)
    if not r:raise HTTPException(404)
    if u['role']!='admin' and r['scout_id']!=u['id']:raise HTTPException(403)
    if r['status'] in ('approved','submitted'):raise HTTPException(409,'Rapporten är låst under granskning eller efter godkännande.')
    return page(request,'edit_report.html',r=r,payload=json.loads(r['payload']),groups=PLAYER_GROUPS if r['kind']=='player' else OPP_GROUPS)

@app.post('/reports/{rid}/save')
async def save_report(request:Request,rid:int):
    u=require_user(request,('scout','admin'));r=fetch_report(rid)
    if not r:raise HTTPException(404)
    if u['role']!='admin' and r['scout_id']!=u['id']:raise HTTPException(403)
    if r['status'] in ('approved','submitted'):raise HTTPException(409,'Rapporten är låst.')
    form=await request.form();check_token(request,str(form.get('csrf','')))
    kind=r['kind'];fields=PLAYER_FIELDS if kind=='player' else OPP_FIELDS
    payload={key:str(form.get(key,'')).strip()[:10000] for key,_ in fields}
    # Positions are edited using the on-page tactical board. Keep this JSON small.
    raw_tactics=str(form.get('tactics','[]'))[:8000]
    try:
        tactics=json.loads(raw_tactics)
        if not isinstance(tactics,list):tactics=[]
        tactics=[{'x':max(0,min(1,float(m['x']))),'y':max(0,min(1,float(m['y']))),'team':'b' if m.get('team')=='b' else 'a'} for m in tactics if isinstance(m,dict) and 'x' in m and 'y' in m][:30]
    except (ValueError,TypeError,KeyError):tactics=[]
    payload['tactics']=json.dumps(tactics)
    action=str(form.get('action','save'))
    if action=='submit' and not any(payload.get(k) for k in ('recommendation','summary')):
        notice(request,'Skriv en rekommendation eller slutsats innan du skickar in rapporten.')
        return go(f'/reports/{rid}/edit')
    status='submitted' if action=='submit' else 'draft'
    with db() as con:con.execute('UPDATE reports SET payload=?,status=?,review_note=?,updated_at=? WHERE id=?',(json.dumps(payload,ensure_ascii=False),status,'',datetime.now().isoformat(timespec='minutes'),rid))
    notice(request,'Rapporten skickades för granskning.' if action=='submit' else 'Utkastet sparades.')
    return go(f'/reports/{rid}' if action=='submit' else f'/reports/{rid}/edit')

@app.get('/reports/{rid}',response_class=HTMLResponse)
def report_detail(request:Request,rid:int):
    u=require_user(request);r=fetch_report(rid)
    if not r:raise HTTPException(404)
    if not can_view_report(u,r):raise HTTPException(403)
    return page(request,'report.html',r=r,payload=json.loads(r['payload']))

@app.get('/reports/{rid}/pdf')
def report_pdf(request:Request,rid:int):
    u=require_user(request);r=fetch_report(rid)
    if not r:raise HTTPException(404)
    if not can_view_report(u,r):raise HTTPException(403)
    data=json.loads(r['payload'])
    body=render_pdf(r['kind'],data)
    filename=f'andrablicken-{r["kind"]}-rapport-{rid}.pdf'
    return StreamingResponse(BytesIO(body),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="{filename}"','Cache-Control':'private, no-store'})

@app.get('/reports/{rid}/attachment')
def report_attachment(request:Request,rid:int):
    u=require_user(request);r=fetch_report(rid)
    if not r or not r['uploaded_file']:raise HTTPException(404)
    if not can_view_report(u,r):raise HTTPException(403)
    path=UPLOADS/Path(r['uploaded_file']).name
    if not path.exists():raise HTTPException(404)
    return FileResponse(path,media_type='application/pdf',filename=f'bilaga-rapport-{rid}.pdf',headers={'Cache-Control':'private, no-store'})

@app.post('/reports/{rid}/attachment')
async def upload_attachment(request:Request,rid:int,file:UploadFile=File(...),csrf:str=Form(...)):
    u=require_user(request,('scout','admin'));check_token(request,csrf);r=fetch_report(rid)
    if not r:raise HTTPException(404)
    if u['role']!='admin' and r['scout_id']!=u['id']:raise HTTPException(403)
    if r['status'] not in ('draft','changes_requested'):raise HTTPException(409,'Rapporten kan inte ändras nu.')
    if not file.filename or not file.filename.lower().endswith('.pdf'):raise HTTPException(400,'Endast PDF är tillåtet.')
    content=await file.read(8*1024*1024+1)
    if len(content)>8*1024*1024 or not content.startswith(b'%PDF-'):
        raise HTTPException(400,'Filen måste vara en PDF på högst 8 MB.')
    fname=uuid.uuid4().hex+'.pdf'
    (UPLOADS/fname).write_bytes(content)
    old=r['uploaded_file']
    with db() as con:con.execute('UPDATE reports SET uploaded_file=?,updated_at=? WHERE id=?',(fname,datetime.now().isoformat(timespec='minutes'),rid))
    if old:
        try:(UPLOADS/Path(old).name).unlink(missing_ok=True)
        except OSError:pass
    notice(request,'PDF-bilagan uppladdad. Den blir synlig för klubben efter godkännande.')
    return go(f'/reports/{rid}/edit')

@app.post('/reports/{rid}/review')
async def review_report(request:Request,rid:int,decision:str=Form(...),review_note:str=Form(''),csrf:str=Form(...)):
    require_user(request,('admin',));check_token(request,csrf);r=fetch_report(rid)
    if not r:raise HTTPException(404)
    if decision not in ('approve','changes'):raise HTTPException(400)
    if r['status'] not in ('submitted','approved'):raise HTTPException(409,'Rapporten är inte inskickad.')
    status='approved' if decision=='approve' else 'changes_requested'
    with db() as con:con.execute('UPDATE reports SET status=?,review_note=?,updated_at=? WHERE id=?',(status,review_note[:3000],datetime.now().isoformat(timespec='minutes'),rid))
    notice(request,'Rapporten godkänd och synlig för klubben.' if decision=='approve' else 'Ändringar begärda. Scouten kan redigera igen.')
    return go(f'/reports/{rid}')

@app.get('/courses',response_class=HTMLResponse)
def courses(request:Request):
    u=require_user(request)
    with db() as con:
        done={r['lesson_index'] for r in con.execute('SELECT lesson_index FROM lessons WHERE user_id=?',(u['id'],)).fetchall()}
        quiz=con.execute('SELECT * FROM quiz_results WHERE user_id=?',(u['id'],)).fetchone()
    return page(request,'courses.html',lessons=COURSE_LESSONS,done=done,quiz=quiz)

@app.get('/courses/lesson/{idx}',response_class=HTMLResponse)
def lesson_page(request:Request,idx:int):
    u=require_user(request)
    if idx<0 or idx>=len(COURSE_LESSONS):raise HTTPException(404)
    return page(request,'lesson.html',lesson=COURSE_LESSONS[idx],idx=idx)

@app.post('/courses/lesson/{idx}/complete')
async def mark_lesson(request:Request,idx:int,csrf:str=Form(...)):
    u=require_user(request);check_token(request,csrf)
    if idx<0 or idx>=len(COURSE_LESSONS):raise HTTPException(404)
    with db() as con:con.execute('INSERT OR IGNORE INTO lessons(user_id,lesson_index,done_at) VALUES (?,?,?)',(u['id'],idx,datetime.now().isoformat(timespec='minutes')))
    notice(request,'Lektionen markerades som genomförd.')
    return go('/courses')

@app.get('/courses/quiz',response_class=HTMLResponse)
def quiz_page(request:Request):
    require_user(request)
    return page(request,'quiz.html',questions=QUESTIONS)

@app.post('/courses/quiz')
async def submit_quiz(request:Request):
    u=require_user(request);form=await request.form();check_token(request,str(form.get('csrf','')))
    with db() as con:done=con.execute('SELECT COUNT(*) AS c FROM lessons WHERE user_id=?',(u['id'],)).fetchone()['c']
    if done<len(COURSE_LESSONS):
        notice(request,'Gå igenom alla tre lektioner innan kunskapstestet.')
        return go('/courses')
    score=sum(1 for i,q in enumerate(QUESTIONS) if str(form.get(f'q{i}',''))==str(q['correct']))
    passed=score>=4
    with db() as con:
        old=con.execute('SELECT best_score,passed FROM quiz_results WHERE user_id=?',(u['id'],)).fetchone()
        best=max(score,old['best_score'] if old else 0)
        passed_all=bool(passed or (old and old['passed']))
        con.execute('INSERT INTO quiz_results(user_id,best_score,passed,finished_at) VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET best_score=?,passed=?,finished_at=?',
                    (u['id'],best,int(passed_all),datetime.now().isoformat(timespec='minutes'),best,int(passed_all),datetime.now().isoformat(timespec='minutes')))
    return page(request,'quiz_result.html',score=score,passed=passed,questions=QUESTIONS)

@app.get('/health')
def health():return {'status':'ok','mode':ENV}
