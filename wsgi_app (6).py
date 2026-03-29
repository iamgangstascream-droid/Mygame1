import json
import random
import os
import hashlib
import time
import sqlite3
from datetime import datetime, timedelta

DB_PATH = '/home/SergeyScream1/legacy-war/game.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY, name TEXT, class TEXT DEFAULT 'warrior',
            level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0, exp_max INTEGER DEFAULT 100,
            hp INTEGER DEFAULT 100, hp_max INTEGER DEFAULT 100,
            mp INTEGER DEFAULT 50, mp_max INTEGER DEFAULT 50,
            pa INTEGER DEFAULT 20, pd INTEGER DEFAULT 15,
            ma INTEGER DEFAULT 5, md INTEGER DEFAULT 10,
            ev INTEGER DEFAULT 5, cr INTEGER DEFAULT 10,
            aden INTEGER DEFAULT 0, stars INTEGER DEFAULT 0, ton REAL DEFAULT 0,
            kills INTEGER DEFAULT 0, deaths INTEGER DEFAULT 0,
            pvp_wins INTEGER DEFAULT 0, pvp_losses INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 1000, clan_id INTEGER,
            referral_code TEXT, referrer_id INTEGER,
            daily_battles INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 20, last_energy_regen TIMESTAMP,
            last_battle_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_daily TIMESTAMP, language TEXT DEFAULT 'ru',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS monsters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, level INTEGER DEFAULT 1, grade TEXT DEFAULT 'D',
            hp INTEGER, hp_max INTEGER, mp INTEGER DEFAULT 0,
            pa INTEGER DEFAULT 0, pd INTEGER DEFAULT 0,
            ma INTEGER DEFAULT 0, md INTEGER DEFAULT 0,
            ev INTEGER DEFAULT 0, cr INTEGER DEFAULT 0,
            exp_reward INTEGER DEFAULT 0, aden_reward INTEGER DEFAULT 0,
            loot_table TEXT DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY, name TEXT, grade TEXT DEFAULT 'D',
            type TEXT, slot TEXT, level_req INTEGER DEFAULT 1,
            pa_bonus INTEGER DEFAULT 0, pd_bonus INTEGER DEFAULT 0,
            ma_bonus INTEGER DEFAULT 0, md_bonus INTEGER DEFAULT 0,
            hp_bonus INTEGER DEFAULT 0, mp_bonus INTEGER DEFAULT 0,
            ev_bonus INTEGER DEFAULT 0, cr_bonus INTEGER DEFAULT 0,
            set_id TEXT, value INTEGER DEFAULT 0,
            description TEXT, recipe TEXT, craft_cost INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, item_id TEXT, quantity INTEGER DEFAULT 1,
            equipped INTEGER DEFAULT 0, enhance_level INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, item_id)
        );
        CREATE TABLE IF NOT EXISTS equipment (
            user_id INTEGER PRIMARY KEY,
            weapon TEXT, weapon_enhance INTEGER DEFAULT 0,
            chest TEXT, chest_enhance INTEGER DEFAULT 0,
            helmet TEXT, helmet_enhance INTEGER DEFAULT 0,
            gloves TEXT, gloves_enhance INTEGER DEFAULT 0,
            boots TEXT, boots_enhance INTEGER DEFAULT 0,
            belt TEXT, belt_enhance INTEGER DEFAULT 0,
            ring TEXT, ring_enhance INTEGER DEFAULT 0,
            amulet TEXT, amulet_enhance INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS clans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
            leader_id INTEGER, level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER, referred_id INTEGER,
            level INTEGER DEFAULT 1, bonus_paid INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER, item_id TEXT, quantity INTEGER,
            price INTEGER, currency TEXT DEFAULT 'aden',
            enhance_level INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, channel TEXT DEFAULT 'world',
            message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pvp_queue (
            user_id INTEGER PRIMARY KEY,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bet INTEGER DEFAULT 0, currency TEXT DEFAULT 'aden'
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, type TEXT, amount REAL,
            currency TEXT, balance_before REAL, balance_after REAL,
            description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS battle_states (
            user_id INTEGER PRIMARY KEY,
            monster_id INTEGER, monster_hp INTEGER, monster_max_hp INTEGER,
            auto_mode INTEGER DEFAULT 0, battle_log TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS active_raids (
            id INTEGER PRIMARY KEY AUTOINCREMENT, boss_id INTEGER,
            boss_hp INTEGER, boss_max_hp INTEGER,
            participants TEXT DEFAULT '[]',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS raid_bosses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
            level INTEGER, hp INTEGER, hp_max INTEGER,
            pa INTEGER, pd INTEGER, ev INTEGER,
            exp_reward INTEGER, aden_reward INTEGER,
            loot_items TEXT DEFAULT '[]', active INTEGER DEFAULT 1,
            respawn_time INTEGER DEFAULT 3600
        );
    ''')
    cur.execute("SELECT COUNT(*) FROM monsters")
    if cur.fetchone()[0] == 0:
        monsters = [
            ("Крыса",1,"D",30,30,0,5,2,0,0,5,5,15,10,'[]'),
            ("Волк",1,"D",50,50,0,8,3,0,0,8,5,25,20,'[]'),
            ("Гоблин",2,"D",80,80,0,12,5,0,0,12,8,45,40,'[]'),
            ("Орк",2,"C",120,120,0,18,10,0,0,5,5,60,55,'[]'),
            ("Скелет",3,"C",150,150,0,22,12,0,0,8,5,90,80,'[]'),
            ("Зомби",3,"C",200,200,0,25,15,0,0,3,5,110,100,'[]'),
            ("Тролль",5,"B",400,400,0,40,25,0,0,5,8,200,180,'[]'),
            ("Оборотень",7,"B",600,600,0,55,30,0,0,15,10,300,260,'[]'),
            ("Демон",10,"A",900,900,0,75,45,0,0,10,12,450,400,'[]'),
            ("Дракон",15,"S",2000,2000,0,120,70,0,0,15,15,900,800,'[]'),
        ]
        cur.executemany('INSERT INTO monsters (name,level,grade,hp,hp_max,mp,pa,pd,ma,md,ev,cr,exp_reward,aden_reward,loot_table) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', monsters)
    cur.execute("SELECT COUNT(*) FROM items")
    if cur.fetchone()[0] == 0:
        items = [
            ("iron_sword","Железный меч","D","weapon","weapon",1,8,0,0,0,0,0,0,0,None,500,"Базовый меч","iron_shard:3",300),
            ("leather_armor","Кожаная броня","D","armor","chest",1,0,8,0,0,20,0,0,0,None,400,"Базовая броня","leather:4",200),
            ("iron_helm","Железный шлем","D","armor","helmet",1,0,5,0,0,10,0,0,0,None,250,"Защита головы","iron_shard:2",150),
            ("potion_small","Малое зелье","D","consumable","consumable",1,0,0,0,0,0,0,0,0,None,10,"Восстанавл. 30 HP",None,0),
            ("potion_large","Большое зелье","C","consumable","consumable",5,0,0,0,0,0,0,0,0,None,50,"Восстанавл. 100 HP",None,0),
            ("prot_stone","Камень защиты","D","consumable","consumable",1,0,0,0,0,0,0,0,0,None,10,"Защита от уничтожения",None,0),
            ("iron_shard","Осколок железа","D","material","material",1,0,0,0,0,0,0,0,0,None,5,"Матер. для крафта",None,0),
            ("leather","Кожа","D","material","material",1,0,0,0,0,0,0,0,0,None,5,"Матер. для крафта",None,0),
            ("steel_sword","Стальной меч","C","weapon","weapon",5,18,0,0,0,0,0,0,0,None,1500,"Меч C-grade","iron_shard:8+leather:5",800),
            ("chain_armor","Кольчуга","C","armor","chest",5,0,18,0,0,50,0,0,0,None,1200,"Броня C-grade","iron_shard:6+leather:8",600),
        ]
        cur.executemany('INSERT INTO items (id,name,grade,type,slot,level_req,pa_bonus,pd_bonus,ma_bonus,md_bonus,hp_bonus,mp_bonus,ev_bonus,cr_bonus,set_id,value,description,recipe,craft_cost) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', items)
    cur.execute("SELECT COUNT(*) FROM raid_bosses")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO raid_bosses (name,level,hp,hp_max,pa,pd,ev,exp_reward,aden_reward,loot_items) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    ('Мировой Дракон',20,50000,50000,150,80,15,5000,10000,'[]'))
    conn.commit()
    conn.close()
    print("OK DB")

try:
    init_db()
except Exception as e:
    print(f"DB init error: {e}")

# ========== HELPERS ==========
def get_player(uid):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM players WHERE user_id=?", (int(uid),))
        row = cur.fetchone(); conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_player: {e}"); return None

def create_player(uid, name, char_class, ref_code=None):
    try:
        rc = hashlib.md5(f"{uid}_{time.time()}".encode()).hexdigest()[:8]
        s = {"warrior":{"hp":150,"mp":50,"pa":25,"pd":20,"ma":5,"md":10,"ev":5,"cr":10},
             "mage":{"hp":100,"mp":100,"pa":8,"pd":8,"ma":30,"md":15,"ev":10,"cr":15},
             "rogue":{"hp":120,"mp":70,"pa":22,"pd":12,"ma":8,"md":8,"ev":25,"cr":25},
             "paladin":{"hp":180,"mp":80,"pa":18,"pd":25,"ma":12,"md":20,"ev":3,"cr":8}
             }.get(char_class,{"hp":150,"mp":50,"pa":25,"pd":20,"ma":5,"md":10,"ev":5,"cr":10})
        conn = get_db(); cur = conn.cursor()
        cur.execute('''INSERT OR IGNORE INTO players
            (user_id,name,class,hp,hp_max,mp,mp_max,pa,pd,ma,md,ev,cr,referral_code,aden,energy,last_energy_regen)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,100,20,CURRENT_TIMESTAMP)''',
            (int(uid),name,char_class,s["hp"],s["hp"],s["mp"],s["mp"],
             s["pa"],s["pd"],s["ma"],s["md"],s["ev"],s["cr"],rc))
        conn.commit(); conn.close()
        return get_player(uid)
    except Exception as e:
        print(f"create_player: {e}"); return None

def update_player(uid, upd):
    if not upd: return
    try:
        conn = get_db(); cur = conn.cursor()
        sc = ", ".join([f"{k}=?" for k in upd.keys()])
        cur.execute(f"UPDATE players SET {sc} WHERE user_id=?", list(upd.values())+[int(uid)])
        conn.commit(); conn.close()
    except Exception as e:
        print(f"update_player: {e}")

def add_item(uid, iid, qty=1, enh=0):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute('INSERT INTO inventory (user_id,item_id,quantity,enhance_level) VALUES (?,?,?,?) ON CONFLICT(user_id,item_id) DO UPDATE SET quantity=quantity+?',
                    (int(uid),iid,qty,enh,qty))
        conn.commit(); conn.close()
    except Exception as e:
        print(f"add_item: {e}")

def remove_item(uid, iid, qty=1):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=?", (int(uid),iid))
        row = cur.fetchone()
        if row:
            nq = row[0]-qty
            if nq<=0: cur.execute("DELETE FROM inventory WHERE user_id=? AND item_id=?",(int(uid),iid))
            else: cur.execute("UPDATE inventory SET quantity=? WHERE user_id=? AND item_id=?",(nq,int(uid),iid))
        conn.commit(); conn.close()
    except Exception as e:
        print(f"remove_item: {e}")

def get_inventory(uid):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute('SELECT i.*,inv.quantity,inv.equipped,inv.enhance_level FROM inventory inv JOIN items i ON inv.item_id=i.id WHERE inv.user_id=?',(int(uid),))
        r = [dict(x) for x in cur.fetchall()]; conn.close(); return r
    except: return []

def get_equipment(uid):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM equipment WHERE user_id=?",(int(uid),))
        row = cur.fetchone(); conn.close(); return dict(row) if row else {}
    except: return {}

def get_player_skills(uid):
    p = get_player(uid)
    if not p: return []
    sm = {
        "warrior":[{"id":"slash","name":"Рубящий удар","mp_cost":10,"damage_mult":1.5,"description":"Мощный удар","level_req":1},
                   {"id":"shield_bash","name":"Удар щитом","mp_cost":15,"damage_mult":1.2,"description":"Оглушает","level_req":5}],
        "mage":[{"id":"fireball","name":"Огненный шар","mp_cost":20,"damage_mult":2.0,"description":"Магия огня","level_req":1},
                {"id":"ice_lance","name":"Ледяное копьё","mp_cost":25,"damage_mult":1.8,"description":"Замедляет","level_req":5}],
        "rogue":[{"id":"backstab","name":"Удар в спину","mp_cost":10,"damage_mult":2.5,"description":"Критический","level_req":1},
                 {"id":"poison","name":"Яд","mp_cost":15,"damage_mult":1.3,"description":"Яд","level_req":5}],
        "paladin":[{"id":"holy_strike","name":"Священный удар","mp_cost":15,"damage_mult":1.6,"description":"Свет","level_req":1},
                   {"id":"heal","name":"Исцеление","mp_cost":30,"damage_mult":0,"description":"Лечит 30% HP","level_req":5}],
    }
    return [s for s in sm.get(p.get('class','warrior'),[]) if s['level_req']<=p['level']]

def get_monster_by_id(mid):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM monsters WHERE id=?",(int(mid),))
        row = cur.fetchone(); conn.close(); return dict(row) if row else None
    except: return None

def get_combat_stats(uid):
    p = get_player(uid)
    if not p: return None
    base = {"warrior":{"pa":20,"pd":15,"ev":5},"mage":{"pa":5,"pd":5,"ev":10},
            "rogue":{"pa":15,"pd":8,"ev":20},"paladin":{"pa":12,"pd":18,"ev":3}}
    b = base.get(p['class'],base['warrior'])
    return {"pa":max(1,b['pa']+p['level']*2),"pd":max(1,b['pd']+p['level']),
            "ev":min(90,max(5,b['ev']+p['level']//2)),
            "hp":p['hp'],"hp_max":p['hp_max'],"mp":p.get('mp',50),"mp_max":p.get('mp_max',50),
            "class":p['class'],"level":p['level']}

def calc_dmg(apa, dpd, dev, crit=False):
    apa=int(apa or 10); dpd=int(dpd or 0); dev=int(dev or 5)
    dmg = max(1, apa-dpd)
    if random.randint(1,100) <= max(20,95-dev):
        if crit: dmg=int(dmg*1.5)
        return random.randint(int(dmg*0.8),int(dmg*1.2))
    return 0

def regen_energy(uid):
    p = get_player(uid)
    if not p: return
    try:
        last = datetime.fromisoformat(str(p.get('last_energy_regen') or '2000-01-01')[:19])
    except:
        last = datetime.now()-timedelta(minutes=30)
    mins = int((datetime.now()-last).total_seconds()/60)
    if mins > 0:
        ne = min(20, p.get('energy',20)+mins)
        update_player(uid, {'energy':ne,'last_energy_regen':datetime.now().isoformat()})

def use_energy(uid, amt=1):
    p = get_player(uid)
    if not p: return False
    regen_energy(uid)
    p = get_player(uid)
    e = p.get('energy',20)
    if e >= amt:
        update_player(uid, {'energy':e-amt}); return True
    return False

def save_battle_state(uid, mid, mhp, mmhp, auto, log):
    conn = get_db(); cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO battle_states (user_id,monster_id,monster_hp,monster_max_hp,auto_mode,battle_log,updated_at) VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)',
                (uid,mid,mhp,mmhp,1 if auto else 0,json.dumps(log)))
    conn.commit(); conn.close()

def load_battle_state(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM battle_states WHERE user_id=?",(uid,))
    row = cur.fetchone(); conn.close()
    if row:
        s = dict(row); s['battle_log']=json.loads(s.get('battle_log','[]')); s['active']=True; return s
    return None

def clear_battle_state(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM battle_states WHERE user_id=?",(uid,))
    conn.commit(); conn.close()

def simulate_turn(pid, mid, action, skill_id=None, cur_mhp=None):
    p = get_player(pid)
    if not p: return {"error":"Player not found"}
    if not use_energy(pid, 1):
        return {"error":"Недостаточно энергии! Ждите восстановления (1 ед/15 мин) или купите за Stars."}
    m = get_monster_by_id(mid)
    if not m: return {"error":"Monster not found"}
    ps = get_combat_stats(pid)
    if not ps: return {"error":"Stats error"}
    mhp = cur_mhp if cur_mhp is not None else m['hp']
    mp_cost = 0
    if action == "attack":
        dmg = calc_dmg(ps['pa'], m['pd'], m['ev'])
        msg = f"⚔️ Вы нанесли {dmg} урона!" if dmg>0 else "❌ Промахнулись!"
    elif action == "skill" and skill_id:
        skills = get_player_skills(pid)
        sk = next((s for s in skills if s['id']==skill_id), None)
        if not sk: return {"error":"Skill not found"}
        if ps['mp'] < sk['mp_cost']: return {"error":"Недостаточно маны!"}
        mp_cost = sk['mp_cost']
        if sk['damage_mult'] > 0:
            d = int(ps['pa']*sk['damage_mult'])
            d = max(1,d-int(m['pd'] or 0))
            if random.randint(1,100) <= max(20,95-int(m['ev'] or 5)):
                d = random.randint(int(d*0.8),int(d*1.2))
            else: d=0
            dmg=d
        else:
            dmg=0
        msg = f"✨ {sk['name']}! {sk['description']}"
    else:
        return {"error":"Invalid action"}
    new_mhp = max(0, mhp-dmg)
    mdmg = calc_dmg(m['pa'], ps['pd'], ps['ev'])
    new_php = max(0, ps['hp']-mdmg)
    updates = {'hp':new_php}
    if mp_cost: updates['mp']=max(0,ps['mp']-mp_cost)
    update_player(pid, updates)
    bend = new_php<=0 or new_mhp<=0
    save_battle_state(pid,mid,new_mhp,m['hp_max'],False,[])
    if bend: clear_battle_state(pid)
    return {
        "player_damage":dmg,"player_hp":new_php,"player_hp_max":ps['hp_max'],
        "player_mp":max(0,ps['mp']-mp_cost),"player_mp_max":ps['mp_max'],
        "monster_damage":mdmg,"monster_hp":new_mhp,"monster_max_hp":m['hp_max'],
        "message":msg,
        "monster_message":f"👹 {m['name']} нанёс {mdmg} урона!" if mdmg>0 else f"💨 {m['name']} промахнулся!",
        "battle_end":bend
    }

def end_battle(pid, mid, victory):
    clear_battle_state(pid)
    p = get_player(pid); m = get_monster_by_id(mid)
    if not p: return {"error":"Player not found"}
    if victory and m:
        exp_g = m['exp_reward']
        aden_g = random.randint(int(m['aden_reward']*0.8), max(1,m['aden_reward']))
        ne = p['exp']+exp_g; nl = p['level']; nem = p.get('exp_max',100); lu = False
        while ne>=nem: ne-=nem; nl+=1; nem=int(nem*1.3); lu=True
        hi=20 if lu else 0; mi=10 if lu else 0
        update_player(pid,{'exp':ne,'exp_max':nem,'level':nl,'aden':p['aden']+aden_g,
                           'hp':p['hp']+hi,'hp_max':p['hp_max']+hi,'mp':p.get('mp',50)+mi,'mp_max':p.get('mp_max',50)+mi})
        return {"victory":True,"exp_gained":exp_g,"aden_gained":aden_g,"level_up":lu,"new_level":nl if lu else None}
    else:
        nhp = max(1,int(p['hp_max']*0.2))
        update_player(pid,{'hp':nhp,'mp':p.get('mp_max',50)})
        return {"victory":False,"player_hp":nhp}

def sim_pvp(a, d):
    ah=a['hp']; dh=d['hp']; log=[]; r=0
    while ah>0 and dh>0 and r<30:
        r+=1
        dmg=calc_dmg(a.get('pa',20)+a.get('level',1)*2,d.get('pd',15)+d.get('level',1),d.get('ev',5))
        if dmg>0: dh=max(0,dh-dmg); log.append(f"{a['name']} нанёс {dmg}")
        else: log.append(f"{a['name']} промах!")
        if dh<=0: break
        dmg2=calc_dmg(d.get('pa',20)+d.get('level',1)*2,a.get('pd',15)+a.get('level',1),a.get('ev',5))
        if dmg2>0: ah=max(0,ah-dmg2); log.append(f"{d['name']} нанёс {dmg2}")
        else: log.append(f"{d['name']} промах!")
    return {"winner":a if ah>0 else d,"loser":d if ah>0 else a,"log":log}

def get_clan_lb(lim=10):
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute('SELECT c.*,(SELECT COUNT(*) FROM players WHERE clan_id=c.id) as member_count FROM clans c ORDER BY c.level DESC,c.wins DESC LIMIT ?',(lim,))
        r=[dict(x) for x in cur.fetchall()]; conn.close(); return r
    except: return []

def get_ref_stats(uid):
    try:
        conn=get_db(); cur=conn.cursor()
        s={"level1":0,"level2":0,"level3":0,"total_earned":0}
        for lvl in [1,2,3]:
            cur.execute("SELECT COUNT(*),COALESCE(SUM(bonus_paid),0) FROM referrals WHERE referrer_id=? AND level=?",(int(uid),lvl))
            row=cur.fetchone(); s[f"level{lvl}"]=row[0] or 0; s["total_earned"]+=row[1] or 0
        conn.close(); return s
    except: return {"level1":0,"level2":0,"level3":0,"total_earned":0}

def get_market():
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute('SELECT m.*,p.name as seller_name,i.name as item_name,i.grade FROM market m JOIN players p ON m.seller_id=p.user_id JOIN items i ON m.item_id=i.id ORDER BY m.created_at DESC LIMIT 50')
        r=[dict(x) for x in cur.fetchall()]; conn.close(); return r
    except: return []

def get_shop():
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("SELECT * FROM items WHERE type IN ('consumable','weapon','armor') ORDER BY grade,level_req")
        r=[dict(x) for x in cur.fetchall()]; conn.close(); return r
    except: return []

def get_active_raid():
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute('SELECT r.*,rb.name,rb.pa,rb.pd,rb.ev,rb.exp_reward,rb.aden_reward FROM active_raids r JOIN raid_bosses rb ON r.boss_id=rb.id WHERE r.boss_hp>0 ORDER BY r.id LIMIT 1')
        row=cur.fetchone(); conn.close()
        if not row:
            conn2=get_db(); cur2=conn2.cursor()
            cur2.execute("SELECT * FROM raid_bosses WHERE active=1 LIMIT 1")
            boss=cur2.fetchone()
            if boss:
                cur2.execute("INSERT INTO active_raids (boss_id,boss_hp,boss_max_hp,participants) VALUES (?,?,?,'[]')",(boss['id'],boss['hp_max'],boss['hp_max']))
                conn2.commit()
            conn2.close()
            return None
        return dict(row)
    except: return None

# ========== WSGI ==========
def application(environ, start_response):
    st = '200 OK'
    hdrs = [('Content-Type','application/json'),('Access-Control-Allow-Origin','*'),
            ('Access-Control-Allow-Methods','GET, POST, OPTIONS'),('Access-Control-Allow-Headers','Content-Type')]
    path = environ.get('PATH_INFO','')
    method = environ.get('REQUEST_METHOD','GET')

    if method == 'OPTIONS':
        start_response('200 OK', hdrs); return [b'']

    def rb():
        try:
            l = environ.get('CONTENT_LENGTH','0')
            return json.loads(environ['wsgi.input'].read(int(l or 0)).decode('utf-8') or '{}')
        except: return {}

    def qp():
        qs = environ.get('QUERY_STRING','')
        return dict(p.split('=',1) for p in qs.split('&') if '=' in p)

    resp = {"error":"Not found"}

    try:
        # Статические файлы
        if method=='GET' and '.' in path.split('/')[-1]:
            base = '/home/SergeyScream1/legacy-war'
            fp = os.path.realpath(os.path.join(base, path.lstrip('/')))
            if fp.startswith(os.path.realpath(base)) and os.path.isfile(fp):
                ext = path.rsplit('.',1)[-1].lower()
                ct = {'js':'application/javascript','css':'text/css','html':'text/html; charset=utf-8',
                      'png':'image/png','jpg':'image/jpeg','ico':'image/x-icon'}.get(ext,'application/octet-stream')
                with open(fp,'rb') as f: c=f.read()
                start_response('200 OK',[('Content-Type',ct),('Content-Length',str(len(c)))]); return [c]
            start_response('404 NOT FOUND',[('Content-Type','text/plain')]); return [b'Not found']

        # Главная страница
        elif path=='/' and method=='GET':
            params=qp(); uid=params.get('user_id')
            html_path='/home/SergeyScream1/legacy-war/index.html'
            if not os.path.isfile(html_path):
                start_response('500 INTERNAL SERVER ERROR',[('Content-Type','text/plain')]); return [b'index.html not found']
            if uid:
                try:
                    if not get_player(int(uid)): create_player(int(uid),f"User_{uid}","warrior")
                except: pass
            with open(html_path,'r',encoding='utf-8') as f: html=f.read()
            start_response('200 OK',[('Content-Type','text/html; charset=utf-8')]); return [html.encode('utf-8')]

        elif path=='/health': resp={"status":"ok","version":"2.1"}

        elif path=='/api/energy' and method=='GET':
            uid=qp().get('user_id')
            if uid:
                regen_energy(int(uid)); p=get_player(int(uid))
                resp={"energy":p.get('energy',20),"max_energy":20}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/battle/state' and method=='GET':
            uid=qp().get('user_id')
            if uid:
                s=load_battle_state(int(uid)); resp=s if s else {"active":False}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/player/stats' and method=='GET':
            uid=qp().get('user_id')
            if uid:
                p=get_player(int(uid))
                if p:
                    regen_energy(int(uid)); p=get_player(int(uid))
                    resp={"name":p['name'],"class":p['class'],"level":p['level'],"rating":p['rating'],
                          "pvp_wins":p['pvp_wins'],"pvp_losses":p['pvp_losses'],
                          "aden":p['aden'],"stars":p['stars'],"ton":p.get('ton',0),
                          "hp":p['hp'],"hp_max":p['hp_max'],"mp":p.get('mp',50),"mp_max":p.get('mp_max',50),
                          "exp":p['exp'],"exp_max":p['exp_max'],"energy":p.get('energy',20)}
                else: st='404 NOT FOUND'; resp={"error":"Player not found"}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/player' and method=='POST':
            d=rb(); uid=d.get('user_id')
            if uid:
                p=get_player(int(uid))
                if not p: p=create_player(int(uid),d.get('name','Hero'),d.get('class','warrior'),d.get('ref_code'))
                resp={"player":p}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/player/settings' and method=='GET':
            uid=qp().get('user_id')
            p=get_player(int(uid)) if uid else None
            resp={"language":p.get('language','ru') if p else 'ru',"sound_enabled":1,"auto_battle_pve":0,"auto_battle_pvp":0}

        elif path=='/api/player/settings' and method=='POST':
            d=rb(); uid=qp().get('user_id') or d.get('user_id')
            if uid:
                upd={}
                if 'language' in d: upd['language']=d['language']
                if upd: update_player(int(uid),upd)
                resp={"success":True}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/player/skills' and method=='GET':
            uid=qp().get('user_id')
            if uid: resp={"skills":get_player_skills(int(uid))}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/monsters/list' and method=='GET':
            uid=qp().get('user_id')
            p=get_player(int(uid)) if uid else None
            lvl=p['level'] if p else 1
            conn=get_db(); cur=conn.cursor()
            cur.execute("SELECT * FROM monsters WHERE level BETWEEN ? AND ? ORDER BY level",(max(1,lvl-2),lvl+5))
            monsters=[dict(r) for r in cur.fetchall()]; conn.close()
            if not monsters:
                conn=get_db(); cur=conn.cursor()
                cur.execute("SELECT * FROM monsters ORDER BY level LIMIT 6")
                monsters=[dict(r) for r in cur.fetchall()]; conn.close()
            resp={"monsters":monsters}

        elif path=='/api/battle/turn' and method=='POST':
            d=rb(); uid=d.get('user_id'); mid=d.get('monster_id'); action=d.get('action')
            if not uid or not mid or not action: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                result=simulate_turn(int(uid),int(mid),action,d.get('skill_id'),d.get('current_monster_hp'))
                if 'error' in result: st='400 BAD REQUEST'
                resp=result

        elif path=='/api/battle/end' and method=='POST':
            d=rb(); uid=d.get('user_id'); mid=d.get('monster_id')
            if not uid or not mid: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else: resp=end_battle(int(uid),int(mid),d.get('victory',False))

        elif path=='/api/inventory' and method=='GET':
            uid=qp().get('user_id')
            if uid: resp={"inventory":get_inventory(int(uid))}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/equipment' and method=='GET':
            uid=qp().get('user_id')
            if uid: resp={"equipment":get_equipment(int(uid))}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/equip' and method=='POST':
            d=rb(); uid=d.get('user_id'); iid=d.get('item_id')
            if not uid or not iid: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                inv=get_inventory(int(uid))
                item=next((i for i in inv if i['id']==iid),None)
                if not item: resp={"error":"Item not in inventory"}
                elif not item.get('slot') or item.get('slot') in ('consumable','material'): resp={"error":"Cannot equip"}
                else:
                    slot=item['slot']
                    conn=get_db(); cur=conn.cursor()
                    cur.execute("UPDATE inventory SET equipped=0 WHERE user_id=?",(int(uid),))
                    cur.execute("UPDATE inventory SET equipped=1 WHERE user_id=? AND item_id=?",(int(uid),iid))
                    cur.execute(f"INSERT OR REPLACE INTO equipment (user_id,{slot}) VALUES (?,?)",(int(uid),iid))
                    conn.commit(); conn.close()
                    resp={"success":True,"equipped":iid}

        elif path=='/api/unequip' and method=='POST':
            d=rb(); uid=d.get('user_id'); slot=d.get('slot')
            if not uid or not slot: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                eq=get_equipment(int(uid)); iid=eq.get(slot)
                if iid:
                    conn=get_db(); cur=conn.cursor()
                    cur.execute("UPDATE inventory SET equipped=0 WHERE user_id=? AND item_id=?",(int(uid),iid))
                    cur.execute(f"UPDATE equipment SET {slot}=NULL WHERE user_id=?",(int(uid),))
                    conn.commit(); conn.close()
                resp={"success":True}

        elif path=='/api/shop' and method=='GET':
            resp={"shop":get_shop()}

        elif path=='/api/buy' and method=='POST':
            d=rb(); uid=d.get('user_id'); iid=d.get('item_id'); qty=int(d.get('quantity',1))
            if not uid or not iid: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                p=get_player(int(uid))
                conn=get_db(); cur=conn.cursor()
                cur.execute("SELECT * FROM items WHERE id=?",(iid,))
                item=cur.fetchone(); conn.close()
                if not item: resp={"error":"Item not found"}
                elif p['level']<item['level_req']: resp={"error":f"Нужен уровень {item['level_req']}"}
                elif p['aden']<item['value']*qty: resp={"error":"Недостаточно Аден"}
                else:
                    update_player(int(uid),{'aden':p['aden']-item['value']*qty})
                    add_item(int(uid),iid,qty)
                    resp={"success":True,"item":item['name'],"new_balance":p['aden']-item['value']*qty}

        elif path=='/api/market/listings' and method=='GET':
            resp={"listings":get_market()}

        elif path=='/api/market/buy' and method=='POST':
            d=rb(); bid=d.get('buyer_id'); lid=d.get('listing_id')
            if not bid or not lid: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                conn=get_db(); cur=conn.cursor()
                cur.execute("SELECT * FROM market WHERE id=?",(int(lid),))
                listing=cur.fetchone()
                if not listing: conn.close(); resp={"error":"Not found"}
                else:
                    l=dict(listing); buyer=get_player(int(bid))
                    if int(bid)==l['seller_id']: conn.close(); resp={"error":"Нельзя купить своё"}
                    elif l['currency']=='aden' and buyer['aden']<l['price']: conn.close(); resp={"error":"Мало Аден"}
                    elif l['currency']=='stars' and buyer['stars']<l['price']: conn.close(); resp={"error":"Мало Stars"}
                    else:
                        comm=int(l['price']*0.07); sg=l['price']-comm
                        seller=get_player(l['seller_id'])
                        if l['currency']=='aden':
                            update_player(int(bid),{'aden':buyer['aden']-l['price']})
                            if seller: update_player(l['seller_id'],{'aden':seller['aden']+sg})
                        else:
                            update_player(int(bid),{'stars':buyer['stars']-l['price']})
                            if seller: update_player(l['seller_id'],{'stars':seller['stars']+sg})
                        add_item(int(bid),l['item_id'],l['quantity'],l.get('enhance_level',0))
                        cur.execute("DELETE FROM market WHERE id=?",(int(lid),))
                        conn.commit(); conn.close()
                        resp={"success":True,"commission":comm,"currency":l['currency']}

        elif path=='/api/craftable' and method=='GET':
            uid=qp().get('user_id')
            if uid:
                inv=get_inventory(int(uid))
                conn=get_db(); cur=conn.cursor()
                cur.execute("SELECT * FROM items WHERE recipe IS NOT NULL AND recipe!=''")
                items=cur.fetchall(); conn.close()
                craftable=[]
                for item in items:
                    id2=dict(item); recipe={}
                    for part in item['recipe'].split('+'):
                        if ':' in part:
                            ing,cnt=part.split(':'); recipe[ing.strip()]=int(cnt.strip())
                    miss=[]; ok=True
                    for ing,cnt in recipe.items():
                        ii=next((i for i in inv if i['id']==ing),None)
                        if not ii or ii['quantity']<cnt: ok=False; miss.append(f"{ing} x{cnt}")
                    id2['can_craft']=ok; id2['missing']=miss; craftable.append(id2)
                resp={"craftable":craftable}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/craft' and method=='POST':
            d=rb(); uid=d.get('user_id'); iid=d.get('item_id'); qty=int(d.get('quantity',1))
            if not uid or not iid: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                conn=get_db(); cur=conn.cursor()
                cur.execute("SELECT * FROM items WHERE id=?",(iid,))
                item=cur.fetchone(); conn.close()
                if not item or not item['recipe']: resp={"error":"No recipe"}
                else:
                    recipe={}
                    for part in item['recipe'].split('+'):
                        if ':' in part:
                            ing,cnt=part.split(':'); recipe[ing.strip()]=int(cnt.strip())*qty
                    inv=get_inventory(int(uid))
                    miss=[f"{ing} x{cnt}" for ing,cnt in recipe.items()
                          if not next((i for i in inv if i['id']==ing and i['quantity']>=cnt),None)]
                    if miss: resp={"error":f"Не хватает: {', '.join(miss)}"}
                    else:
                        p=get_player(int(uid)); cost=item['craft_cost']*qty
                        if p['aden']<cost: resp={"error":f"Нужно {cost} Аден"}
                        else:
                            for ing,cnt in recipe.items(): remove_item(int(uid),ing,cnt)
                            update_player(int(uid),{'aden':p['aden']-cost})
                            add_item(int(uid),iid,qty)
                            resp={"success":True,"crafted":item['name'],"message":f"Создано {item['name']} x{qty}"}

        elif path=='/api/enhance' and method=='POST':
            d=rb(); uid=d.get('user_id'); iid=d.get('item_id'); use_prot=d.get('use_protection',False)
            if not uid or not iid: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                inv=get_inventory(int(uid)); item=next((i for i in inv if i['id']==iid),None)
                if not item: resp={"error":"Item not in inventory"}
                else:
                    ce=item.get('enhance_level',0)
                    if ce>=10: resp={"error":"Максимум +10"}
                    else:
                        chance={0:100,1:90,2:80,3:70,4:60,5:50,6:40,7:30,8:20,9:10}.get(ce,50)
                        cost=[500,1000,2000,4000,8000,15000,30000,60000,120000,200000][ce]
                        p=get_player(int(uid))
                        if p['aden']<cost: resp={"error":f"Нужно {cost} Аден"}
                        else:
                            hp=False
                            if use_prot:
                                ps_=next((i for i in inv if i['id']=='prot_stone'),None)
                                if ps_ and ps_['quantity']>0: hp=True; remove_item(int(uid),'prot_stone',1)
                            update_player(int(uid),{'aden':p['aden']-cost})
                            if random.randint(1,100)<=chance:
                                ne2=ce+1
                                conn=get_db(); cur=conn.cursor()
                                cur.execute("UPDATE inventory SET enhance_level=? WHERE user_id=? AND item_id=?",(ne2,int(uid),iid))
                                conn.commit(); conn.close()
                                resp={"success":True,"new_enhance":ne2,"message":f"✨ Успех! {item['name']} теперь +{ne2}"}
                            else:
                                if not hp:
                                    remove_item(int(uid),iid,1)
                                    resp={"success":False,"destroyed":True,"message":f"💀 Провал! {item['name']} уничтожен!"}
                                else:
                                    resp={"success":False,"destroyed":False,"message":f"🛡️ Провал! Камень защиты спас {item['name']}"}

        elif path=='/api/chat/messages' and method=='GET':
            params=qp(); ct=params.get('chat_type','world'); lim=int(params.get('limit',50))
            try:
                conn=get_db(); cur=conn.cursor()
                cur.execute('SELECT m.*,p.name as username FROM chat_messages m LEFT JOIN players p ON m.user_id=p.user_id WHERE m.channel=? ORDER BY m.created_at DESC LIMIT ?',(ct,lim))
                msgs=list(reversed([dict(r) for r in cur.fetchall()])); conn.close()
                resp={"messages":msgs}
            except: resp={"messages":[]}

        elif path=='/api/chat/send' and method=='POST':
            d=rb(); uid=d.get('user_id'); msg=(d.get('message') or '').strip()[:500]; ct=d.get('chat_type','world')
            if not uid or not msg: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                conn=get_db(); cur=conn.cursor()
                cur.execute("INSERT INTO chat_messages (user_id,channel,message) VALUES (?,?,?)",(int(uid),ct,msg))
                conn.commit(); conn.close(); resp={"success":True}

        elif path=='/api/pvp/queue' and method=='POST':
            d=rb(); uid=d.get('user_id')
            if not uid: st='400 BAD REQUEST'; resp={"error":"user_id required"}
            else:
                p=get_player(int(uid))
                conn=get_db(); cur=conn.cursor()
                cur.execute("SELECT * FROM pvp_queue WHERE user_id!=?",(int(uid),))
                opp=cur.fetchone()
                if opp:
                    cur.execute("DELETE FROM pvp_queue WHERE user_id IN (?,?)",(int(uid),opp['user_id']))
                    conn.commit(); conn.close()
                    op=get_player(opp['user_id'])
                    r=sim_pvp(p,op); wid=r['winner']['user_id']; lid=r['loser']['user_id']
                    ww=get_player(wid); ll=get_player(lid)
                    update_player(wid,{'pvp_wins':ww['pvp_wins']+1,'rating':ww['rating']+25})
                    update_player(lid,{'pvp_losses':ll['pvp_losses']+1,'rating':max(0,ll['rating']-25)})
                    resp={"found":True,"victory":wid==int(uid),"opponent":op['name'],"rating_change":25 if wid==int(uid) else -25,"log":r['log'][:5]}
                else:
                    cur.execute("INSERT OR REPLACE INTO pvp_queue (user_id) VALUES (?)",(int(uid),))
                    conn.commit(); conn.close(); resp={"found":False,"queued":True}

        elif path=='/api/pvp/queue/leave' and method=='POST':
            d=rb(); uid=d.get('user_id')
            if uid:
                conn=get_db(); cur=conn.cursor()
                cur.execute("DELETE FROM pvp_queue WHERE user_id=?",(int(uid),))
                conn.commit(); conn.close()
            resp={"success":True}

        elif path=='/api/pvp/challenge' and method=='POST':
            d=rb(); aid=d.get('attacker_id'); did=d.get('defender_id')
            if not aid or not did: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                a=get_player(int(aid)); dv=get_player(int(did))
                if not a or not dv: resp={"error":"Player not found"}
                else:
                    r=sim_pvp(a,dv); wid=r['winner']['user_id']; lid=r['loser']['user_id']
                    ww=get_player(wid); ll=get_player(lid)
                    update_player(wid,{'pvp_wins':ww['pvp_wins']+1,'rating':ww['rating']+25})
                    update_player(lid,{'pvp_losses':ll['pvp_losses']+1,'rating':max(0,ll['rating']-25)})
                    resp={"victory":wid==int(aid),"winner":r['winner']['name'],"loser":r['loser']['name'],"log":r['log'][:8]}

        elif path=='/api/player/search' and method=='GET':
            un=qp().get('username','')
            if un:
                conn=get_db(); cur=conn.cursor()
                cur.execute("SELECT user_id,name,level,rating FROM players WHERE name LIKE ? LIMIT 10",(f"%{un}%",))
                r=[dict(x) for x in cur.fetchall()]; conn.close(); resp={"players":r}
            else: resp={"players":[]}

        elif path=='/api/rating/top' and method=='GET':
            conn=get_db(); cur=conn.cursor()
            cur.execute("SELECT user_id,name,rating,pvp_wins,pvp_losses,level FROM players ORDER BY rating DESC LIMIT 10")
            r=[dict(x) for x in cur.fetchall()]; conn.close(); resp={"top":r}

        elif path=='/api/referral/link' and method=='GET':
            uid=qp().get('user_id')
            if uid:
                p=get_player(int(uid))
                if p and p.get('referral_code'): resp={"link":f"https://t.me/legacy_war_bot?start=ref_{p['referral_code']}"}
                else: resp={"error":"Player not found"}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/referral/stats' and method=='GET':
            uid=qp().get('user_id')
            if uid: resp=get_ref_stats(int(uid))
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/clan/leaderboard' and method=='GET':
            resp={"clans":get_clan_lb(10)}

        elif path=='/api/clan/info' and method=='GET':
            params=qp(); uid=params.get('user_id'); cid=params.get('clan_id')
            if uid:
                p=get_player(int(uid))
                cid=int(cid) if cid else (p.get('clan_id') if p else None)
                if cid:
                    conn=get_db(); cur=conn.cursor()
                    cur.execute("SELECT * FROM clans WHERE id=?",(cid,))
                    clan=cur.fetchone()
                    if clan:
                        c=dict(clan)
                        cur.execute("SELECT user_id,name,level,rating FROM players WHERE clan_id=? ORDER BY rating DESC",(cid,))
                        c['members']=[dict(r) for r in cur.fetchall()]; c['member_count']=len(c['members'])
                        resp={"clan":c}
                    else: resp={"clan":None}
                    conn.close()
                else: resp={"clan":None}
            else: st='400 BAD REQUEST'; resp={"error":"user_id required"}

        elif path=='/api/clan/create' and method=='POST':
            d=rb(); uid=d.get('user_id'); cn=(d.get('name') or '').strip()
            if not uid or not cn: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            elif len(cn)<3 or len(cn)>20: resp={"error":"Название: 3-20 символов"}
            else:
                p=get_player(int(uid))
                if not p: resp={"error":"Player not found"}
                elif p.get('clan_id'): resp={"error":"Вы уже в клане"}
                elif p.get('aden',0)<5000: resp={"error":"Нужно 5000 Аден"}
                else:
                    conn=get_db(); cur=conn.cursor()
                    cur.execute("SELECT id FROM clans WHERE name=?",(cn,))
                    if cur.fetchone(): conn.close(); resp={"error":"Название занято"}
                    else:
                        cur.execute("INSERT INTO clans (name,leader_id) VALUES (?,?)",(cn,int(uid)))
                        new_cid=cur.lastrowid; conn.commit(); conn.close()
                        update_player(int(uid),{'clan_id':new_cid,'aden':p['aden']-5000})
                        resp={"success":True,"clan_id":new_cid,"message":f"Клан «{cn}» создан!"}

        elif path=='/api/clan/join' and method=='POST':
            d=rb(); uid=d.get('user_id'); cid=d.get('clan_id')
            if not uid or not cid: st='400 BAD REQUEST'; resp={"error":"Missing fields"}
            else:
                p=get_player(int(uid))
                if not p: resp={"error":"Player not found"}
                elif p.get('clan_id'): resp={"error":"Вы уже в клане"}
                else:
                    conn=get_db(); cur=conn.cursor()
                    cur.execute("SELECT name FROM clans WHERE id=?",(int(cid),))
                    clan=cur.fetchone(); conn.close()
                    if not clan: resp={"error":"Клан не найден"}
                    else:
                        update_player(int(uid),{'clan_id':int(cid)})
                        resp={"success":True,"message":f"Вы вступили в клан «{clan['name']}»!"}

        elif path=='/api/clan/leave' and method=='POST':
            d=rb(); uid=d.get('user_id')
            if not uid: st='400 BAD REQUEST'; resp={"error":"user_id required"}
            else:
                p=get_player(int(uid))
                if not p or not p.get('clan_id'): resp={"error":"Вы не в клане"}
                else:
                    conn=get_db(); cur=conn.cursor()
                    cur.execute("SELECT leader_id FROM clans WHERE id=?",(p['clan_id'],))
                    clan=cur.fetchone(); conn.close()
                    if clan and dict(clan)['leader_id']==int(uid): resp={"error":"Лидер не может покинуть клан"}
                    else:
                        update_player(int(uid),{'clan_id':None}); resp={"success":True,"message":"Вы покинули клан"}

        elif path=='/api/raid/status' and method=='GET':
            raid=get_active_raid()
            if raid: resp={"active":True,"boss_hp":raid['boss_hp'],"boss_max_hp":raid['boss_max_hp'],"boss_name":raid['name'],"participants":json.loads(raid.get('participants','[]'))}
            else: resp={"active":False}

        elif path=='/api/raid/hit' and method=='POST':
            d=rb(); uid=d.get('user_id')
            if not uid: st='400 BAD REQUEST'; resp={"error":"user_id required"}
            else:
                ps=get_combat_stats(int(uid)); dmg=ps['pa']*2 if ps else 10
                raid=get_active_raid()
                if not raid: resp={"error":"No active raid"}
                else:
                    nhp=max(0,raid['boss_hp']-dmg)
                    participants=json.loads(raid.get('participants','[]'))
                    p=get_player(int(uid))
                    if p:
                        found=next((x for x in participants if x['user_id']==int(uid)),None)
                        if found: found['damage']+=dmg
                        else: participants.append({'user_id':int(uid),'name':p['name'],'damage':dmg})
                    conn=get_db(); cur=conn.cursor()
                    cur.execute("UPDATE active_raids SET boss_hp=?,participants=? WHERE id=?",(nhp,json.dumps(participants),raid['id']))
                    conn.commit(); conn.close()
                    resp={"success":True,"damage":dmg,"boss_hp":nhp,"boss_max_hp":raid['boss_max_hp']}

        elif path=='/api/player/topup' and method=='POST':
            d=rb(); uid=d.get('user_id'); cur2=d.get('currency','aden'); amt=int(d.get('amount',0))
            if not uid or amt<=0: st='400 BAD REQUEST'; resp={"error":"Invalid"}
            else:
                p=get_player(int(uid))
                if not p: resp={"error":"Player not found"}
                else:
                    cv=p.get(cur2,0); update_player(int(uid),{cur2:cv+amt})
                    resp={"success":True,"new_balance":cv+amt}

        elif path=='/api/player/withdraw' and method=='POST':
            d=rb(); uid=d.get('user_id'); cur2=d.get('currency','stars'); amt=int(d.get('amount',0))
            if not uid or amt<=0: st='400 BAD REQUEST'; resp={"error":"Invalid"}
            else:
                p=get_player(int(uid))
                if not p: resp={"error":"Player not found"}
                else:
                    cv=p.get(cur2,0)
                    if cv<amt: resp={"error":"Недостаточно средств"}
                    else: update_player(int(uid),{cur2:cv-amt}); resp={"success":True,"new_balance":cv-amt}

        elif path=='/api/buy/energy' and method=='POST':
            d=rb(); uid=d.get('user_id')
            if not uid: st='400 BAD REQUEST'; resp={"error":"user_id required"}
            else:
                p=get_player(int(uid))
                if not p: resp={"error":"Player not found"}
                elif p.get('stars',0)<10: resp={"error":"Нужно 10 Stars"}
                else: update_player(int(uid),{'stars':p['stars']-10,'energy':20}); resp={"success":True,"energy":20}

        elif path=='/api/webhook' or path=='/webhook':
            resp={"ok":True}

        else:
            st='404 NOT FOUND'; resp={"error":"Not found"}

    except Exception as e:
        print(f"ERROR [{path}]: {e}")
        import traceback; traceback.print_exc()
        st='500 INTERNAL SERVER ERROR'; resp={"error":str(e)}

    start_response(st, hdrs)
    return [json.dumps(resp, default=str, ensure_ascii=False).encode('utf-8')]
