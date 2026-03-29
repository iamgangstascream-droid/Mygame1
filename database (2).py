import os
import json
import sqlite3
import asyncpg
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

# ============================================
# LEGACY WAR - DATABASE CLASS
# Версия: 2.0
# Дата: 2026-03-28
# ============================================

class Database:
    def __init__(self, db_path: str = "game.db"):
        self.db_path = db_path
        self.pool = None
        self.use_postgres = os.getenv("DATABASE_URL") is not None

    async def init(self):
        """Инициализация базы данных"""
        if self.use_postgres:
            if not self.pool:
                self.pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
            await self._init_postgres_tables()
        else:
            # Для SQLite используем aiosqlite
            import aiosqlite
            self.pool = await aiosqlite.connect(self.db_path)
            await self._init_sqlite_tables()

    async def _init_postgres_tables(self):
        """Создание таблиц для PostgreSQL"""
        async with self.pool.acquire() as conn:
            # Таблица игроков
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    name TEXT,
                    class TEXT DEFAULT 'warrior',
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    exp_max INTEGER DEFAULT 100,
                    hp INTEGER DEFAULT 100,
                    hp_max INTEGER DEFAULT 100,
                    mp INTEGER DEFAULT 50,
                    mp_max INTEGER DEFAULT 50,
                    strength INTEGER DEFAULT 10,
                    dexterity INTEGER DEFAULT 10,
                    intelligence INTEGER DEFAULT 10,
                    constitution INTEGER DEFAULT 10,
                    wisdom INTEGER DEFAULT 10,
                    pa INTEGER DEFAULT 20,
                    pd INTEGER DEFAULT 15,
                    ma INTEGER DEFAULT 5,
                    md INTEGER DEFAULT 10,
                    ev INTEGER DEFAULT 5,
                    cr INTEGER DEFAULT 10,
                    cm REAL DEFAULT 1.5,
                    reg INTEGER DEFAULT 2,
                    pen INTEGER DEFAULT 5,
                    aден INTEGER DEFAULT 0,
                    stars INTEGER DEFAULT 0,
                    ton REAL DEFAULT 0,
                    kills INTEGER DEFAULT 0,
                    deaths INTEGER DEFAULT 0,
                    pvp_wins INTEGER DEFAULT 0,
                    pvp_losses INTEGER DEFAULT 0,
                    rating INTEGER DEFAULT 1000,
                    clan_id INTEGER,
                    referral_code TEXT,
                    referrer_id BIGINT,
                    daily_battles INTEGER DEFAULT 0,
                    last_battle_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_daily TIMESTAMP,
                    language TEXT DEFAULT 'ru',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица монстров
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS monsters (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    grade TEXT DEFAULT 'D',
                    hp INTEGER NOT NULL,
                    hp_max INTEGER NOT NULL,
                    mp INTEGER DEFAULT 0,
                    pa INTEGER DEFAULT 0,
                    pd INTEGER DEFAULT 0,
                    ma INTEGER DEFAULT 0,
                    md INTEGER DEFAULT 0,
                    ev INTEGER DEFAULT 0,
                    cr INTEGER DEFAULT 0,
                    exp_reward INTEGER DEFAULT 0,
                    aден_reward INTEGER DEFAULT 0,
                    stars_reward INTEGER DEFAULT 0,
                    skills TEXT DEFAULT '[]',
                    description TEXT,
                    image_url TEXT,
                    respawn_time INTEGER DEFAULT 60,
                    is_boss INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица предметов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    grade TEXT DEFAULT 'D',
                    type TEXT NOT NULL,
                    slot TEXT,
                    level_req INTEGER DEFAULT 1,
                    class_req TEXT,
                    pa_bonus INTEGER DEFAULT 0,
                    pd_bonus INTEGER DEFAULT 0,
                    ma_bonus INTEGER DEFAULT 0,
                    md_bonus INTEGER DEFAULT 0,
                    hp_bonus INTEGER DEFAULT 0,
                    mp_bonus INTEGER DEFAULT 0,
                    ev_bonus INTEGER DEFAULT 0,
                    cr_bonus INTEGER DEFAULT 0,
                    reg_bonus INTEGER DEFAULT 0,
                    enhance_pa REAL DEFAULT 0,
                    enhance_pd REAL DEFAULT 0,
                    enhance_ma REAL DEFAULT 0,
                    enhance_md REAL DEFAULT 0,
                    value INTEGER DEFAULT 0,
                    sell_value INTEGER DEFAULT 0,
                    craft_cost INTEGER DEFAULT 0,
                    recipe TEXT,
                    drop_chance REAL DEFAULT 0,
                    max_enhance INTEGER DEFAULT 10,
                    description TEXT,
                    icon TEXT,
                    set_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица инвентаря
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    user_id BIGINT NOT NULL,
                    item_id TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    equipped INTEGER DEFAULT 0,
                    enhance_level INTEGER DEFAULT 0,
                    durability INTEGER DEFAULT 100,
                    attributes TEXT DEFAULT '{}',
                    PRIMARY KEY (user_id, item_id)
                )
            ''')
            
            # Таблица экипировки
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS equipment (
                    user_id BIGINT PRIMARY KEY,
                    weapon TEXT,
                    weapon_enhance INTEGER DEFAULT 0,
                    chest TEXT,
                    chest_enhance INTEGER DEFAULT 0,
                    helmet TEXT,
                    helmet_enhance INTEGER DEFAULT 0,
                    gloves TEXT,
                    gloves_enhance INTEGER DEFAULT 0,
                    boots TEXT,
                    boots_enhance INTEGER DEFAULT 0,
                    belt TEXT,
                    belt_enhance INTEGER DEFAULT 0,
                    ring TEXT,
                    ring_enhance INTEGER DEFAULT 0,
                    amulet TEXT,
                    amulet_enhance INTEGER DEFAULT 0,
                    cloak TEXT,
                    cloak_enhance INTEGER DEFAULT 0
                )
            ''')
            
            # Таблица навыков
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    class TEXT NOT NULL,
                    level_req INTEGER DEFAULT 1,
                    mp_cost INTEGER DEFAULT 10,
                    hp_cost INTEGER DEFAULT 0,
                    damage_mult REAL DEFAULT 1.0,
                    damage_type TEXT DEFAULT 'physical',
                    effect_type TEXT,
                    effect_value INTEGER DEFAULT 0,
                    effect_duration INTEGER DEFAULT 0,
                    icon TEXT,
                    animation TEXT,
                    description TEXT,
                    cooldown INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица навыков игроков
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS player_skills (
                    user_id BIGINT NOT NULL,
                    skill_id TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, skill_id)
                )
            ''')
            
            # Таблица дропа
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS monster_drops (
                    monster_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    chance REAL NOT NULL,
                    min_quantity INTEGER DEFAULT 1,
                    max_quantity INTEGER DEFAULT 1,
                    PRIMARY KEY (monster_id, item_id)
                )
            ''')
            
            # Таблица чата
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username TEXT NOT NULL,
                    chat_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    target_user_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица настроек
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS player_settings (
                    user_id BIGINT PRIMARY KEY,
                    sound_enabled INTEGER DEFAULT 1,
                    music_enabled INTEGER DEFAULT 1,
                    notifications_enabled INTEGER DEFAULT 1,
                    language TEXT DEFAULT 'ru',
                    auto_battle_pve INTEGER DEFAULT 0,
                    auto_battle_pvp INTEGER DEFAULT 0,
                    show_combat_log INTEGER DEFAULT 1,
                    show_damage_numbers INTEGER DEFAULT 1
                )
            ''')
            
            # Таблица очереди PvP
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS pvp_queue (
                    user_id BIGINT PRIMARY KEY,
                    level INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    auto_battle INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица истории PvP
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS pvp_history (
                    id SERIAL PRIMARY KEY,
                    attacker_id BIGINT NOT NULL,
                    defender_id BIGINT NOT NULL,
                    winner_id BIGINT NOT NULL,
                    bet_amount INTEGER DEFAULT 0,
                    bet_currency TEXT DEFAULT 'stars',
                    attacker_rating_before INTEGER,
                    attacker_rating_after INTEGER,
                    defender_rating_before INTEGER,
                    defender_rating_after INTEGER,
                    battle_log TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица кланов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS clans (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    leader_id BIGINT NOT NULL,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица рефералов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL,
                    referred_id BIGINT NOT NULL,
                    level INTEGER NOT NULL,
                    bonus_paid INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица маркета
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS market (
                    id SERIAL PRIMARY KEY,
                    seller_id BIGINT NOT NULL,
                    item_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    currency TEXT DEFAULT 'stars',
                    enhance_level INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица градаций
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS item_grades (
                    grade TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    enhance_bonus REAL DEFAULT 1.0,
                    min_level INTEGER DEFAULT 1,
                    color TEXT,
                    icon TEXT,
                    description TEXT
                )
            ''')
            
            # Таблица достижений
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    reward_type TEXT,
                    reward_amount INTEGER DEFAULT 0,
                    icon TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица транзакций
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    balance_before INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица логов боев
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS battle_logs (
                    id SERIAL PRIMARY KEY,
                    battle_type TEXT NOT NULL,
                    user_id BIGINT NOT NULL,
                    opponent_id BIGINT,
                    result TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создаем индексы
            await self._create_indexes(conn)

    async def _init_sqlite_tables(self):
        """Создание таблиц для SQLite"""
        async with self.pool as conn:
            # Создаем все таблицы (аналогично PostgreSQL, но с SQLite синтаксисом)
            await conn.executescript('''
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    name TEXT,
                    class TEXT DEFAULT 'warrior',
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    exp_max INTEGER DEFAULT 100,
                    hp INTEGER DEFAULT 100,
                    hp_max INTEGER DEFAULT 100,
                    mp INTEGER DEFAULT 50,
                    mp_max INTEGER DEFAULT 50,
                    strength INTEGER DEFAULT 10,
                    dexterity INTEGER DEFAULT 10,
                    intelligence INTEGER DEFAULT 10,
                    constitution INTEGER DEFAULT 10,
                    wisdom INTEGER DEFAULT 10,
                    pa INTEGER DEFAULT 20,
                    pd INTEGER DEFAULT 15,
                    ma INTEGER DEFAULT 5,
                    md INTEGER DEFAULT 10,
                    ev INTEGER DEFAULT 5,
                    cr INTEGER DEFAULT 10,
                    cm REAL DEFAULT 1.5,
                    reg INTEGER DEFAULT 2,
                    pen INTEGER DEFAULT 5,
                    aден INTEGER DEFAULT 0,
                    stars INTEGER DEFAULT 0,
                    ton REAL DEFAULT 0,
                    kills INTEGER DEFAULT 0,
                    deaths INTEGER DEFAULT 0,
                    pvp_wins INTEGER DEFAULT 0,
                    pvp_losses INTEGER DEFAULT 0,
                    rating INTEGER DEFAULT 1000,
                    clan_id INTEGER,
                    referral_code TEXT,
                    referrer_id INTEGER,
                    daily_battles INTEGER DEFAULT 0,
                    last_battle_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_daily TIMESTAMP,
                    language TEXT DEFAULT 'ru',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS monsters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    grade TEXT DEFAULT 'D',
                    hp INTEGER NOT NULL,
                    hp_max INTEGER NOT NULL,
                    mp INTEGER DEFAULT 0,
                    pa INTEGER DEFAULT 0,
                    pd INTEGER DEFAULT 0,
                    ma INTEGER DEFAULT 0,
                    md INTEGER DEFAULT 0,
                    ev INTEGER DEFAULT 0,
                    cr INTEGER DEFAULT 0,
                    exp_reward INTEGER DEFAULT 0,
                    aден_reward INTEGER DEFAULT 0,
                    stars_reward INTEGER DEFAULT 0,
                    skills TEXT DEFAULT '[]',
                    description TEXT,
                    image_url TEXT,
                    respawn_time INTEGER DEFAULT 60,
                    is_boss INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    grade TEXT DEFAULT 'D',
                    type TEXT NOT NULL,
                    slot TEXT,
                    level_req INTEGER DEFAULT 1,
                    class_req TEXT,
                    pa_bonus INTEGER DEFAULT 0,
                    pd_bonus INTEGER DEFAULT 0,
                    ma_bonus INTEGER DEFAULT 0,
                    md_bonus INTEGER DEFAULT 0,
                    hp_bonus INTEGER DEFAULT 0,
                    mp_bonus INTEGER DEFAULT 0,
                    ev_bonus INTEGER DEFAULT 0,
                    cr_bonus INTEGER DEFAULT 0,
                    reg_bonus INTEGER DEFAULT 0,
                    enhance_pa REAL DEFAULT 0,
                    enhance_pd REAL DEFAULT 0,
                    enhance_ma REAL DEFAULT 0,
                    enhance_md REAL DEFAULT 0,
                    value INTEGER DEFAULT 0,
                    sell_value INTEGER DEFAULT 0,
                    craft_cost INTEGER DEFAULT 0,
                    recipe TEXT,
                    drop_chance REAL DEFAULT 0,
                    max_enhance INTEGER DEFAULT 10,
                    description TEXT,
                    icon TEXT,
                    set_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    equipped INTEGER DEFAULT 0,
                    enhance_level INTEGER DEFAULT 0,
                    durability INTEGER DEFAULT 100,
                    attributes TEXT DEFAULT '{}',
                    PRIMARY KEY (user_id, item_id)
                );
                
                CREATE TABLE IF NOT EXISTS equipment (
                    user_id INTEGER PRIMARY KEY,
                    weapon TEXT,
                    weapon_enhance INTEGER DEFAULT 0,
                    chest TEXT,
                    chest_enhance INTEGER DEFAULT 0,
                    helmet TEXT,
                    helmet_enhance INTEGER DEFAULT 0,
                    gloves TEXT,
                    gloves_enhance INTEGER DEFAULT 0,
                    boots TEXT,
                    boots_enhance INTEGER DEFAULT 0,
                    belt TEXT,
                    belt_enhance INTEGER DEFAULT 0,
                    ring TEXT,
                    ring_enhance INTEGER DEFAULT 0,
                    amulet TEXT,
                    amulet_enhance INTEGER DEFAULT 0,
                    cloak TEXT,
                    cloak_enhance INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    class TEXT NOT NULL,
                    level_req INTEGER DEFAULT 1,
                    mp_cost INTEGER DEFAULT 10,
                    hp_cost INTEGER DEFAULT 0,
                    damage_mult REAL DEFAULT 1.0,
                    damage_type TEXT DEFAULT 'physical',
                    effect_type TEXT,
                    effect_value INTEGER DEFAULT 0,
                    effect_duration INTEGER DEFAULT 0,
                    icon TEXT,
                    animation TEXT,
                    description TEXT,
                    cooldown INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS player_skills (
                    user_id INTEGER NOT NULL,
                    skill_id TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, skill_id)
                );
                
                CREATE TABLE IF NOT EXISTS monster_drops (
                    monster_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    chance REAL NOT NULL,
                    min_quantity INTEGER DEFAULT 1,
                    max_quantity INTEGER DEFAULT 1,
                    PRIMARY KEY (monster_id, item_id)
                );
                
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    chat_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    target_user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS player_settings (
                    user_id INTEGER PRIMARY KEY,
                    sound_enabled INTEGER DEFAULT 1,
                    music_enabled INTEGER DEFAULT 1,
                    notifications_enabled INTEGER DEFAULT 1,
                    language TEXT DEFAULT 'ru',
                    auto_battle_pve INTEGER DEFAULT 0,
                    auto_battle_pvp INTEGER DEFAULT 0,
                    show_combat_log INTEGER DEFAULT 1,
                    show_damage_numbers INTEGER DEFAULT 1
                );
                
                CREATE TABLE IF NOT EXISTS pvp_queue (
                    user_id INTEGER PRIMARY KEY,
                    level INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    auto_battle INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS pvp_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attacker_id INTEGER NOT NULL,
                    defender_id INTEGER NOT NULL,
                    winner_id INTEGER NOT NULL,
                    bet_amount INTEGER DEFAULT 0,
                    bet_currency TEXT DEFAULT 'stars',
                    attacker_rating_before INTEGER,
                    attacker_rating_after INTEGER,
                    defender_rating_before INTEGER,
                    defender_rating_after INTEGER,
                    battle_log TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS clans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    leader_id INTEGER NOT NULL,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    level INTEGER NOT NULL,
                    bonus_paid INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS market (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seller_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    currency TEXT DEFAULT 'stars',
                    enhance_level INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS item_grades (
                    grade TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    enhance_bonus REAL DEFAULT 1.0,
                    min_level INTEGER DEFAULT 1,
                    color TEXT,
                    icon TEXT,
                    description TEXT
                );
                
                CREATE TABLE IF NOT EXISTS achievements (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    reward_type TEXT,
                    reward_amount INTEGER DEFAULT 0,
                    icon TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    balance_before INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS battle_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    battle_type TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    opponent_id INTEGER,
                    result TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Создаем индексы
            await self._create_sqlite_indexes(conn)

    async def _create_indexes(self, conn):
        """Создание индексов для PostgreSQL"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_players_level ON players(level)",
            "CREATE INDEX IF NOT EXISTS idx_players_rating ON players(rating)",
            "CREATE INDEX IF NOT EXISTS idx_players_clan ON players(clan_id)",
            "CREATE INDEX IF NOT EXISTS idx_players_referral_code ON players(referral_code)",
            "CREATE INDEX IF NOT EXISTS idx_monsters_level ON monsters(level)",
            "CREATE INDEX IF NOT EXISTS idx_items_type ON items(type)",
            "CREATE INDEX IF NOT EXISTS idx_items_grade ON items(grade)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_type ON chat_messages(chat_type, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_pvp_queue_level ON pvp_queue(level)",
            "CREATE INDEX IF NOT EXISTS idx_market_price ON market(price)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)"
        ]
        for idx in indexes:
            await conn.execute(idx)

    async def _create_sqlite_indexes(self, conn):
        """Создание индексов для SQLite"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_players_level ON players(level)",
            "CREATE INDEX IF NOT EXISTS idx_players_rating ON players(rating)",
            "CREATE INDEX IF NOT EXISTS idx_players_clan ON players(clan_id)",
            "CREATE INDEX IF NOT EXISTS idx_players_referral_code ON players(referral_code)",
            "CREATE INDEX IF NOT EXISTS idx_monsters_level ON monsters(level)",
            "CREATE INDEX IF NOT EXISTS idx_items_type ON items(type)",
            "CREATE INDEX IF NOT EXISTS idx_items_grade ON items(grade)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_type ON chat_messages(chat_type, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_pvp_queue_level ON pvp_queue(level)",
            "CREATE INDEX IF NOT EXISTS idx_market_price ON market(price)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)"
        ]
        for idx in indexes:
            await conn.execute(idx)

    # ========== ОСНОВНЫЕ МЕТОДЫ ==========
    
    async def get_player(self, user_id: int) -> Optional[Dict]:
        """Получить данные игрока"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
                return dict(row) if row else None
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def create_player(self, user_id: int, name: str, char_class: str, referrer_code: str = None) -> Dict:
        """Создать нового игрока"""
        import hashlib
        import time
        
        referral_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8]
        referrer_id = None
        
        if referrer_code:
            referrer = await self.get_player_by_referral_code(referrer_code)
            if referrer:
                referrer_id = referrer['user_id']
        
        # Базовые статы для классов
        class_stats = {
            "warrior": {"hp_max": 150, "mp_max": 50, "pa": 25, "pd": 20, "ma": 5, "md": 10, "ev": 5, "cr": 10},
            "mage": {"hp_max": 100, "mp_max": 100, "pa": 8, "pd": 8, "ma": 30, "md": 15, "ev": 10, "cr": 15},
            "rogue": {"hp_max": 120, "mp_max": 70, "pa": 22, "pd": 12, "ma": 8, "md": 8, "ev": 25, "cr": 25},
            "paladin": {"hp_max": 180, "mp_max": 80, "pa": 18, "pd": 25, "ma": 12, "md": 20, "ev": 3, "cr": 8}
        }
        stats = class_stats.get(char_class, class_stats["warrior"])
        
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO players 
                    (user_id, name, class, hp, hp_max, mp, mp_max, referral_code, referrer_id,
                     pa, pd, ma, md, ev, cr, last_login)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, CURRENT_TIMESTAMP)
                ''', user_id, name, char_class, stats["hp_max"], stats["hp_max"], 
                    stats["mp_max"], stats["mp_max"], referral_code, referrer_id,
                    stats["pa"], stats["pd"], stats["ma"], stats["md"], stats["ev"], stats["cr"])
        else:
            async with self.pool as conn:
                await conn.execute('''
                    INSERT INTO players 
                    (user_id, name, class, hp, hp_max, mp, mp_max, referral_code, referrer_id,
                     pa, pd, ma, md, ev, cr, last_login)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', user_id, name, char_class, stats["hp_max"], stats["hp_max"], 
                    stats["mp_max"], stats["mp_max"], referral_code, referrer_id,
                    stats["pa"], stats["pd"], stats["ma"], stats["md"], stats["ev"], stats["cr"])
        
        # Если есть реферер, начисляем бонус
        if referrer_id:
            referrer = await self.get_player(referrer_id)
            if referrer:
                await self.update_player(referrer_id, {'aден': referrer['aден'] + 500})
                await self.log_transaction(referrer_id, 'referral_bonus', 500, 'aден', 
                                           referrer['aден'], referrer['aден'] + 500, 
                                           f"Бонус за реферала {user_id}")
        
        return await self.get_player(user_id)

    async def update_player(self, user_id: int, updates: Dict):
        """Обновить данные игрока"""
        if not updates:
            return
        
        set_parts = []
        values = []
        for key, val in updates.items():
            set_parts.append(f"{key} = ?" if not self.use_postgres else f"{key} = ${len(values)+1}")
            values.append(val)
        values.append(user_id)
        
        if self.use_postgres:
            query = f"UPDATE players SET {', '.join(set_parts)} WHERE user_id = ${len(values)}"
            async with self.pool.acquire() as conn:
                await conn.execute(query, *values)
        else:
            query = f"UPDATE players SET {', '.join(set_parts)} WHERE user_id = ?"
            async with self.pool as conn:
                await conn.execute(query, *values)

    async def get_player_by_referral_code(self, referral_code: str) -> Optional[Dict]:
        """Найти игрока по реферальному коду"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM players WHERE referral_code = $1", referral_code)
                return dict(row) if row else None
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute("SELECT * FROM players WHERE referral_code = ?", (referral_code,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    # ========== МЕТОДЫ ДЛЯ ИНВЕНТАРЯ ==========
    
    async def add_item(self, user_id: int, item_id: str, quantity: int = 1, enhance: int = 0):
        """Добавить предмет в инвентарь"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO inventory (user_id, item_id, quantity, enhance_level)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, item_id) DO UPDATE SET quantity = inventory.quantity + $3
                ''', user_id, item_id, quantity, enhance)
        else:
            async with self.pool as conn:
                await conn.execute('''
                    INSERT INTO inventory (user_id, item_id, quantity, enhance_level)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?
                ''', user_id, item_id, quantity, enhance, quantity)

    async def remove_item(self, user_id: int, item_id: str, quantity: int = 1):
        """Удалить предмет из инвентаря"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT quantity FROM inventory WHERE user_id = $1 AND item_id = $2", 
                                          user_id, item_id)
                if row:
                    new_qty = row['quantity'] - quantity
                    if new_qty <= 0:
                        await conn.execute("DELETE FROM inventory WHERE user_id = $1 AND item_id = $2", 
                                          user_id, item_id)
                    else:
                        await conn.execute("UPDATE inventory SET quantity = $1 WHERE user_id = $2 AND item_id = $3",
                                          new_qty, user_id, item_id)
        else:
            async with self.pool as conn:
                cursor = await conn.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", 
                                           (user_id, item_id))
                row = await cursor.fetchone()
                if row:
                    new_qty = row[0] - quantity
                    if new_qty <= 0:
                        await conn.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ?", 
                                          (user_id, item_id))
                    else:
                        await conn.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?",
                                          (new_qty, user_id, item_id))

    async def get_inventory(self, user_id: int) -> List[Dict]:
        """Получить инвентарь игрока"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT i.*, inv.quantity, inv.equipped, inv.enhance_level, ig.color as grade_color
                    FROM inventory inv 
                    JOIN items i ON inv.item_id = i.id 
                    LEFT JOIN item_grades ig ON i.grade = ig.grade
                    WHERE inv.user_id = $1
                ''', user_id)
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute('''
                    SELECT i.*, inv.quantity, inv.equipped, inv.enhance_level, ig.color as grade_color
                    FROM inventory inv 
                    JOIN items i ON inv.item_id = i.id 
                    LEFT JOIN item_grades ig ON i.grade = ig.grade
                    WHERE inv.user_id = ?
                ''', (user_id,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ========== МЕТОДЫ ДЛЯ МОНСТРОВ ==========
    
    async def get_monster_by_id(self, monster_id: int) -> Optional[Dict]:
        """Получить монстра по ID"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM monsters WHERE id = $1", monster_id)
                return dict(row) if row else None
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute("SELECT * FROM monsters WHERE id = ?", (monster_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_monsters_by_level_range(self, player_level: int) -> List[Dict]:
        """Получить монстров в диапазоне уровней ±3"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT m.*, 
                           array_agg(d.item_id || ':' || d.chance) as drops_info
                    FROM monsters m
                    LEFT JOIN monster_drops d ON m.id = d.monster_id
                    WHERE m.level BETWEEN $1 AND $2
                    GROUP BY m.id
                    ORDER BY m.level, m.name
                ''', max(1, player_level - 3), player_level + 3)
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute('''
                    SELECT m.*, 
                           GROUP_CONCAT(d.item_id || ':' || d.chance) as drops_info
                    FROM monsters m
                    LEFT JOIN monster_drops d ON m.id = d.monster_id
                    WHERE m.level BETWEEN ? AND ?
                    GROUP BY m.id
                    ORDER BY m.level, m.name
                ''', (max(1, player_level - 3), player_level + 3))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_monster_drops(self, monster_id: int) -> List[Dict]:
        """Получить дроп с монстра"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT i.id, i.name, i.grade, d.chance, d.min_quantity, d.max_quantity, ig.color as grade_color
                    FROM monster_drops d
                    JOIN items i ON d.item_id = i.id
                    LEFT JOIN item_grades ig ON i.grade = ig.grade
                    WHERE d.monster_id = $1
                ''', monster_id)
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute('''
                    SELECT i.id, i.name, i.grade, d.chance, d.min_quantity, d.max_quantity, ig.color as grade_color
                    FROM monster_drops d
                    JOIN items i ON d.item_id = i.id
                    LEFT JOIN item_grades ig ON i.grade = ig.grade
                    WHERE d.monster_id = ?
                ''', (monster_id,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ========== МЕТОДЫ ДЛЯ НАВЫКОВ ==========
    
    async def get_player_skills(self, user_id: int) -> List[Dict]:
        """Получить навыки игрока"""
        player = await self.get_player(user_id)
        if not player:
            return []
        
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM skills 
                    WHERE class = $1 AND level_req <= $2 
                    ORDER BY level_req
                ''', player['class'], player['level'])
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute('''
                    SELECT * FROM skills 
                    WHERE class = ? AND level_req <= ? 
                    ORDER BY level_req
                ''', (player['class'], player['level']))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ========== МЕТОДЫ ДЛЯ ЧАТА ==========
    
    async def send_chat_message(self, user_id: int, chat_type: str, message: str, target_user_id: int = None) -> int:
        """Отправить сообщение в чат"""
        player = await self.get_player(user_id)
        if not player:
            return 0
        
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    INSERT INTO chat_messages (user_id, username, chat_type, message, target_user_id)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                ''', user_id, player['name'], chat_type, message, target_user_id)
                return row['id'] if row else 0
        else:
            async with self.pool as conn:
                cursor = await conn.execute('''
                    INSERT INTO chat_messages (user_id, username, chat_type, message, target_user_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, player['name'], chat_type, message, target_user_id))
                return cursor.lastrowid

    async def get_chat_messages(self, user_id: int, chat_type: str, target_user_id: int = None, limit: int = 50) -> List[Dict]:
        """Получить сообщения чата"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                if chat_type == 'private' and target_user_id:
                    rows = await conn.fetch('''
                        SELECT * FROM chat_messages 
                        WHERE chat_type = 'private' 
                        AND ((user_id = $1 AND target_user_id = $2) OR (user_id = $2 AND target_user_id = $1))
                        ORDER BY created_at DESC LIMIT $3
                    ''', user_id, target_user_id, limit)
                else:
                    rows = await conn.fetch('''
                        SELECT * FROM chat_messages 
                        WHERE chat_type = $1 
                        ORDER BY created_at DESC LIMIT $2
                    ''', chat_type, limit)
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                if chat_type == 'private' and target_user_id:
                    cursor = await conn.execute('''
                        SELECT * FROM chat_messages 
                        WHERE chat_type = 'private' 
                        AND ((user_id = ? AND target_user_id = ?) OR (user_id = ? AND target_user_id = ?))
                        ORDER BY created_at DESC LIMIT ?
                    ''', (user_id, target_user_id, target_user_id, user_id, limit))
                else:
                    cursor = await conn.execute('''
                        SELECT * FROM chat_messages 
                        WHERE chat_type = ? 
                        ORDER BY created_at DESC LIMIT ?
                    ''', (chat_type, limit))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ========== МЕТОДЫ ДЛЯ НАСТРОЕК ==========
    
    async def get_player_settings(self, user_id: int) -> Dict:
        """Получить настройки игрока"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM player_settings WHERE user_id = $1", user_id)
                if not row:
                    await conn.execute('''
                        INSERT INTO player_settings (user_id) VALUES ($1)
                    ''', user_id)
                    return {"user_id": user_id, "sound_enabled": 1, "music_enabled": 1, 
                            "notifications_enabled": 1, "language": "ru", "auto_battle_pve": 0, 
                            "auto_battle_pvp": 0, "show_combat_log": 1, "show_damage_numbers": 1}
                return dict(row)
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute("SELECT * FROM player_settings WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()
                if not row:
                    await conn.execute('''
                        INSERT INTO player_settings (user_id) VALUES (?)
                    ''', (user_id,))
                    return {"user_id": user_id, "sound_enabled": 1, "music_enabled": 1, 
                            "notifications_enabled": 1, "language": "ru", "auto_battle_pve": 0, 
                            "auto_battle_pvp": 0, "show_combat_log": 1, "show_damage_numbers": 1}
                return dict(row)

    async def update_player_settings(self, user_id: int, settings: Dict) -> bool:
        """Обновить настройки игрока"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO player_settings 
                    (user_id, sound_enabled, music_enabled, notifications_enabled, language, 
                     auto_battle_pve, auto_battle_pvp, show_combat_log, show_damage_numbers)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (user_id) DO UPDATE SET
                        sound_enabled = $2,
                        music_enabled = $3,
                        notifications_enabled = $4,
                        language = $5,
                        auto_battle_pve = $6,
                        auto_battle_pvp = $7,
                        show_combat_log = $8,
                        show_damage_numbers = $9
                ''', user_id, 
                    settings.get('sound_enabled', 1),
                    settings.get('music_enabled', 1),
                    settings.get('notifications_enabled', 1),
                    settings.get('language', 'ru'),
                    settings.get('auto_battle_pve', 0),
                    settings.get('auto_battle_pvp', 0),
                    settings.get('show_combat_log', 1),
                    settings.get('show_damage_numbers', 1))
        else:
            async with self.pool as conn:
                await conn.execute('''
                    INSERT OR REPLACE INTO player_settings 
                    (user_id, sound_enabled, music_enabled, notifications_enabled, language, 
                     auto_battle_pve, auto_battle_pvp, show_combat_log, show_damage_numbers)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, 
                    settings.get('sound_enabled', 1),
                    settings.get('music_enabled', 1),
                    settings.get('notifications_enabled', 1),
                    settings.get('language', 'ru'),
                    settings.get('auto_battle_pve', 0),
                    settings.get('auto_battle_pvp', 0),
                    settings.get('show_combat_log', 1),
                    settings.get('show_damage_numbers', 1)))
        return True

    # ========== МЕТОДЫ ДЛЯ PVP ==========
    
    async def add_to_pvp_queue(self, user_id: int, level: int, rating: int, auto_battle: bool = False):
        """Добавить игрока в очередь PvP"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO pvp_queue (user_id, level, rating, auto_battle, joined_at)
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE SET
                        level = $2, rating = $3, auto_battle = $4, joined_at = CURRENT_TIMESTAMP
                ''', user_id, level, rating, 1 if auto_battle else 0)
        else:
            async with self.pool as conn:
                await conn.execute('''
                    INSERT OR REPLACE INTO pvp_queue (user_id, level, rating, auto_battle, joined_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, level, rating, 1 if auto_battle else 0))

    async def find_pvp_match(self, user_id: int, level: int, rating: int) -> Optional[int]:
        """Найти соперника для PvP"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT user_id FROM pvp_queue 
                    WHERE user_id != $1 
                    AND level BETWEEN $2 AND $3
                    ORDER BY ABS(rating - $4) LIMIT 1
                ''', user_id, max(1, level - 3), level + 3, rating)
                return row['user_id'] if row else None
        else:
            async with self.pool as conn:
                cursor = await conn.execute('''
                    SELECT user_id FROM pvp_queue 
                    WHERE user_id != ? 
                    AND level BETWEEN ? AND ?
                    ORDER BY ABS(rating - ?) LIMIT 1
                ''', (user_id, max(1, level - 3), level + 3, rating))
                row = await cursor.fetchone()
                return row[0] if row else None

    async def remove_from_pvp_queue(self, user_id: int):
        """Удалить игрока из очереди"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM pvp_queue WHERE user_id = $1", user_id)
        else:
            async with self.pool as conn:
                await conn.execute("DELETE FROM pvp_queue WHERE user_id = ?", (user_id,))

    async def save_pvp_history(self, attacker_id: int, defender_id: int, winner_id: int, 
                                bet_amount: int, bet_currency: str, attacker_rating_before: int,
                                attacker_rating_after: int, defender_rating_before: int,
                                defender_rating_after: int, battle_log: str):
        """Сохранить историю PvP боя"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO pvp_history 
                    (attacker_id, defender_id, winner_id, bet_amount, bet_currency,
                     attacker_rating_before, attacker_rating_after, 
                     defender_rating_before, defender_rating_after, battle_log)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ''', attacker_id, defender_id, winner_id, bet_amount, bet_currency,
                    attacker_rating_before, attacker_rating_after,
                    defender_rating_before, defender_rating_after, battle_log)
        else:
            async with self.pool as conn:
                await conn.execute('''
                    INSERT INTO pvp_history 
                    (attacker_id, defender_id, winner_id, bet_amount, bet_currency,
                     attacker_rating_before, attacker_rating_after, 
                     defender_rating_before, defender_rating_after, battle_log)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (attacker_id, defender_id, winner_id, bet_amount, bet_currency,
                    attacker_rating_before, attacker_rating_after,
                    defender_rating_before, defender_rating_after, battle_log))

    # ========== МЕТОДЫ ДЛЯ ТРАНЗАКЦИЙ ==========
    
    async def log_transaction(self, user_id: int, trans_type: str, amount: int, currency: str,
                               balance_before: int, balance_after: int, description: str):
        """Логирование транзакции"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO transactions 
                    (user_id, type, amount, currency, balance_before, balance_after, description)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''', user_id, trans_type, amount, currency, balance_before, balance_after, description)
        else:
            async with self.pool as conn:
                await conn.execute('''
                    INSERT INTO transactions 
                    (user_id, type, amount, currency, balance_before, balance_after, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, trans_type, amount, currency, balance_before, balance_after, description))

    # ========== МЕТОДЫ ДЛЯ ПОИСКА ==========
    
    async def search_players_by_name(self, username: str) -> List[Dict]:
        """Поиск игроков по никнейму"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT user_id, name, level, rating FROM players 
                    WHERE name ILIKE $1 LIMIT 10
                ''', f"%{username}%")
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute('''
                    SELECT user_id, name, level, rating FROM players 
                    WHERE name LIKE ? LIMIT 10
                ''', (f"%{username}%",))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ========== МЕТОДЫ ДЛЯ РЕФЕРАЛОВ ==========
    
    async def get_referral_stats(self, user_id: int) -> Dict:
        """Получить статистику рефералов"""
        stats = {"level1": 0, "level2": 0, "level3": 0, "total_earned": 0}
        
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                for lvl in [1, 2, 3]:
                    row = await conn.fetchrow('''
                        SELECT COUNT(*), COALESCE(SUM(bonus_paid), 0) as total 
                        FROM referrals WHERE referrer_id = $1 AND level = $2
                    ''', user_id, lvl)
                    if row:
                        stats[f"level{lvl}"] = row[0]
                        stats["total_earned"] += row[1]
        else:
            async with self.pool as conn:
                for lvl in [1, 2, 3]:
                    cursor = await conn.execute('''
                        SELECT COUNT(*), COALESCE(SUM(bonus_paid), 0) as total 
                        FROM referrals WHERE referrer_id = ? AND level = ?
                    ''', (user_id, lvl))
                    row = await cursor.fetchone()
                    if row:
                        stats[f"level{lvl}"] = row[0]
                        stats["total_earned"] += row[1]
        
        return stats

    # ========== МЕТОДЫ ДЛЯ КЛАНОВ ==========
    
    async def get_clan_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Получить топ кланов"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT c.id, c.name, c.level, c.wins, c.losses, 
                           (SELECT COUNT(*) FROM players WHERE clan_id = c.id) as member_count
                    FROM clans c 
                    ORDER BY c.level DESC LIMIT $1
                ''', limit)
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute('''
                    SELECT c.id, c.name, c.level, c.wins, c.losses, 
                           (SELECT COUNT(*) FROM players WHERE clan_id = c.id) as member_count
                    FROM clans c 
                    ORDER BY c.level DESC LIMIT ?
                ''', (limit,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ========== МЕТОДЫ ДЛЯ МАРКЕТА ==========
    
    async def get_market_listings(self, limit: int = 50) -> List[Dict]:
        """Получить список лотов на маркете"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT m.id, m.seller_id, p.name as seller_name, m.item_id, i.name as item_name,
                           i.grade, m.quantity, m.price, m.currency, m.created_at, m.enhance_level,
                           ig.color as grade_color
                    FROM market m 
                    JOIN players p ON m.seller_id = p.user_id
                    JOIN items i ON m.item_id = i.id
                    LEFT JOIN item_grades ig ON i.grade = ig.grade
                    ORDER BY m.created_at DESC LIMIT $1
                ''', limit)
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute('''
                    SELECT m.id, m.seller_id, p.name as seller_name, m.item_id, i.name as item_name,
                           i.grade, m.quantity, m.price, m.currency, m.created_at, m.enhance_level,
                           ig.color as grade_color
                    FROM market m 
                    JOIN players p ON m.seller_id = p.user_id
                    JOIN items i ON m.item_id = i.id
                    LEFT JOIN item_grades ig ON i.grade = ig.grade
                    ORDER BY m.created_at DESC LIMIT ?
                ''', (limit,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def add_market_listing(self, seller_id: int, item_id: str, quantity: int, 
                                  price: int, currency: str = 'stars', enhance_level: int = 0) -> int:
        """Добавить лот на маркет"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    INSERT INTO market (seller_id, item_id, quantity, price, currency, enhance_level)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                ''', seller_id, item_id, quantity, price, currency, enhance_level)
                return row['id'] if row else 0
        else:
            async with self.pool as conn:
                cursor = await conn.execute('''
                    INSERT INTO market (seller_id, item_id, quantity, price, currency, enhance_level)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (seller_id, item_id, quantity, price, currency, enhance_level))
                return cursor.lastrowid

    async def remove_market_listing(self, listing_id: int) -> bool:
        """Удалить лот с маркета"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                result = await conn.execute("DELETE FROM market WHERE id = $1", listing_id)
                return result == "DELETE 1"
        else:
            async with self.pool as conn:
                cursor = await conn.execute("DELETE FROM market WHERE id = ?", (listing_id,))
                return cursor.rowcount > 0

    # ========== МЕТОДЫ ДЛЯ КРАФТА ==========
    
    async def get_craftable_items(self, user_id: int) -> List[Dict]:
        """Получить список доступных для крафта предметов"""
        inventory = await self.get_inventory(user_id)
        
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM items WHERE recipe IS NOT NULL AND recipe != ''
                ''')
                items = [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute("SELECT * FROM items WHERE recipe IS NOT NULL AND recipe != ''")
                rows = await cursor.fetchall()
                items = [dict(row) for row in rows]
        
        craftable = []
        for item in items:
            recipe = {}
            if item['recipe']:
                for part in item['recipe'].split('+'):
                    if ':' in part:
                        ing, cnt = part.split(':')
                        recipe[ing] = int(cnt)
            
            missing = []
            can_craft = True
            for ing, cnt in recipe.items():
                inv_item = next((i for i in inventory if i['id'] == ing), None)
                if not inv_item or inv_item['quantity'] < cnt:
                    can_craft = False
                    missing.append(f"{ing} x{cnt}")
            
            item['can_craft'] = can_craft
            item['missing'] = missing
            item['recipe_dict'] = recipe
            craftable.append(item)
        
        return craftable

    # ========== МЕТОДЫ ДЛЯ ГРАДАЦИЙ ==========
    
    async def get_item_grades(self) -> List[Dict]:
        """Получить все градации предметов"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM item_grades ORDER BY min_level")
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute("SELECT * FROM item_grades ORDER BY min_level")
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_grade_by_name(self, grade_name: str) -> Optional[Dict]:
        """Получить градацию по имени"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM item_grades WHERE grade = $1", grade_name)
                return dict(row) if row else None
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute("SELECT * FROM item_grades WHERE grade = ?", (grade_name,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    # ========== МЕТОДЫ ДЛЯ АЧИВОК ==========
    
    async def get_achievements(self) -> List[Dict]:
        """Получить все достижения"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM achievements")
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute("SELECT * FROM achievements")
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def unlock_achievement(self, user_id: int, achievement_id: str) -> bool:
        """Разблокировать достижение"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                try:
                    await conn.execute('''
                        INSERT INTO player_achievements (user_id, achievement_id)
                        VALUES ($1, $2)
                    ''', user_id, achievement_id)
                    return True
                except:
                    return False
        else:
            async with self.pool as conn:
                try:
                    await conn.execute('''
                        INSERT INTO player_achievements (user_id, achievement_id)
                        VALUES (?, ?)
                    ''', (user_id, achievement_id))
                    return True
                except:
                    return False

    # ========== МЕТОДЫ ДЛЯ ТОПА ==========
    
    async def get_rating_top(self, limit: int = 10) -> List[Dict]:
        """Получить топ рейтинга"""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT user_id, name, rating, pvp_wins, pvp_losses 
                    FROM players 
                    ORDER BY rating DESC LIMIT $1
                ''', limit)
                return [dict(row) for row in rows]
        else:
            async with self.pool as conn:
                conn.row_factory = sqlite3.Row
                cursor = await conn.execute('''
                    SELECT user_id, name, rating, pvp_wins, pvp_losses 
                    FROM players 
                    ORDER BY rating DESC LIMIT ?
                ''', (limit,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ========== МЕТОДЫ ДЛЯ ЗАКРЫТИЯ ==========
    
    async def close(self):
        """Закрыть соединение с БД"""
        if self.pool:
            await self.pool.close()