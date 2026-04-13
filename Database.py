import os
import aiosqlite
import hashlib
import secrets
import time
import logging
import random
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Путь к БД берём из переменной окружения DB_PATH
# На Render persistent disk: /var/data/game.db (не сбрасывается при деплое!)
# Локально: ./game.db
DB_PATH = os.environ.get("DB_PATH", "/var/data/game.db")

# Создаём директорию если не существует (для /var/data на Render)
_db_dir = os.path.dirname(DB_PATH)
if _db_dir and not os.path.exists(_db_dir):
    try:
        os.makedirs(_db_dir, exist_ok=True)
        logger.info(f"Created DB directory: {_db_dir}")
    except Exception:
        # Если не удалось создать /var/data — fallback на локальный файл
        DB_PATH = "game.db"
        logger.warning(f"Could not create {_db_dir}, falling back to local game.db")

# Whitelist для безопасных названий слотов экипировки
VALID_SLOTS = {"weapon", "helmet", "chest", "legs", "boots", "gloves"}


class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self.pool: Optional[aiosqlite.Connection] = None
        self._items_cache = {}
        self._cache_time = 0
        self._bot_info = None

    async def connect(self):
        """Подключение к БД с WAL-режимом для производительности"""
        self.pool = await aiosqlite.connect(self.path)
        self.pool.row_factory = aiosqlite.Row

        await self.pool.execute("PRAGMA journal_mode=WAL")
        await self.pool.execute("PRAGMA synchronous=NORMAL")
        await self.pool.execute("PRAGMA cache_size=-10000")
        await self.pool.execute("PRAGMA temp_store=MEMORY")

        await self.init_db()
        logger.info("Database connected (WAL mode enabled)")

    async def close(self):
        if self.pool:
            await self.pool.close()

    @asynccontextmanager
    async def get_cursor(self):
        async with self.pool.cursor() as cursor:
            try:
                yield cursor
                await self.pool.commit()
            except Exception as e:
                await self.pool.rollback()
                logger.error(f"DB Error: {e}")
                raise

    async def init_db(self):
        """Инициализация всех таблиц"""
        async with self.get_cursor() as cursor:
            # ===== PLAYERS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    class TEXT DEFAULT 'warrior',
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    exp_max INTEGER DEFAULT 120,
                    hp INTEGER DEFAULT 80,
                    hp_max INTEGER DEFAULT 80,
                    mp INTEGER DEFAULT 50,
                    mp_max INTEGER DEFAULT 50,
                    attack INTEGER DEFAULT 20,
                    defense INTEGER DEFAULT 15,
                    evasion INTEGER DEFAULT 5,
                    crit_damage INTEGER DEFAULT 10,
                    resistance REAL DEFAULT 0,
                    strength REAL DEFAULT 0,
                    agility REAL DEFAULT 0,
                    endurance REAL DEFAULT 0,
                    intuition REAL DEFAULT 0,
                    aden INTEGER DEFAULT 0,
                    stars INTEGER DEFAULT 0,
                    ton REAL DEFAULT 0,
                    pvp_wins INTEGER DEFAULT 0,
                    pvp_losses INTEGER DEFAULT 0,
                    rating INTEGER DEFAULT 0,
                    clan_id INTEGER,
                    referral_code TEXT UNIQUE,
                    referrer_id INTEGER,
                    language TEXT DEFAULT 'ru',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_daily TIMESTAMP,
                    daily_streak INTEGER DEFAULT 0,
                    premium_until TIMESTAMP,
                    premium_type TEXT,
                    registration_ip TEXT,
                    is_banned INTEGER DEFAULT 0,
                    ban_reason TEXT,
                    banned_at TIMESTAMP,
                    total_referral_bonus INTEGER DEFAULT 0,
                    energy INTEGER DEFAULT 100,
                    energy_max INTEGER DEFAULT 100,
                    last_energy_regen TIMESTAMP,
                    auto_battle_daily_limit INTEGER DEFAULT 300
                )
            ''')

            # ===== DAILY QUESTS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_quests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT, -- 'kills', 'damage', 'skills'
                    target INTEGER,
                    progress INTEGER DEFAULT 0,
                    reward_aden INTEGER DEFAULT 0,
                    reward_stars INTEGER DEFAULT 0,
                    is_completed INTEGER DEFAULT 0,
                    is_claimed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES players(user_id)
                )
            ''')
            
            # ===== SESSIONS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id INTEGER PRIMARY KEY,
                    token TEXT UNIQUE,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES players(user_id)
                )
            ''')

            # ===== AUDIT LOGS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    severity TEXT,
                    ip_address TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ===== EQUIPMENT =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS equipment (
                    user_id INTEGER PRIMARY KEY,
                    weapon TEXT,
                    helmet TEXT,
                    chest TEXT,
                    legs TEXT,
                    boots TEXT,
                    gloves TEXT,
                    FOREIGN KEY (user_id) REFERENCES players(user_id)
                )
            ''')
            
            # ===== INVENTORY =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER,
                    item_id TEXT,
                    quantity INTEGER DEFAULT 1,
                    equipped INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, item_id)
                )
            ''')
            
            # ===== REFERRALS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    referred_level INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 0,
                    level_reached_at TIMESTAMP,
                    total_donations_stars INTEGER DEFAULT 0,
                    total_commission_earned INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    became_active_at TIMESTAMP,
                    referrer_ip TEXT,
                    referred_ip TEXT,
                    total_fights INTEGER DEFAULT 0,
                    expired_at TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (referrer_id) REFERENCES players(user_id),
                    FOREIGN KEY (referred_id) REFERENCES players(user_id)
                )
            ''')
            
            # ===== REFERRAL COMMISSIONS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS referral_commissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    amount_stars INTEGER DEFAULT 0,
                    amount_aden INTEGER DEFAULT 0,
                    commission_percent INTEGER DEFAULT 30,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    donate_id INTEGER,
                    metadata TEXT,
                    FOREIGN KEY (referrer_id) REFERENCES players(user_id),
                    FOREIGN KEY (referred_id) REFERENCES players(user_id)
                )
            ''')
            
            # ===== FARMING STATS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS farming_stats (
                    user_id INTEGER PRIMARY KEY,
                    fights_today INTEGER DEFAULT 0,
                    last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_fights INTEGER DEFAULT 0
                )
            ''')
            
            # ===== CRAFTING LIMITS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS crafting_limits (
                    user_id INTEGER PRIMARY KEY,
                    crafts_today INTEGER DEFAULT 0,
                    last_craft_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_crafts INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES players(user_id)
                )
            ''')
            
            # ===== MONSTERS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS monsters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    level INTEGER,
                    tier INTEGER DEFAULT 1,
                    grade TEXT DEFAULT 'D',
                    hp INTEGER,
                    hp_max INTEGER,
                    attack INTEGER,
                    defense INTEGER DEFAULT 0,
                    evasion INTEGER DEFAULT 5,
                    crit_damage INTEGER DEFAULT 100,
                    resistance REAL DEFAULT 0,
                    exp_reward INTEGER,
                    aden_reward INTEGER,
                    loot_table TEXT
                )
            ''')
            
            # ===== ITEMS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    type TEXT,
                    grade TEXT DEFAULT 'NG',
                    slot TEXT,
                    level_req INTEGER DEFAULT 1,
                    attack_bonus INTEGER DEFAULT 0,
                    defense_bonus INTEGER DEFAULT 0,
                    evasion_bonus INTEGER DEFAULT 0,
                    crit_damage_bonus INTEGER DEFAULT 0,
                    hp_bonus INTEGER DEFAULT 0,
                    mp_bonus INTEGER DEFAULT 0,
                    effect_value INTEGER DEFAULT 0,
                    value INTEGER DEFAULT 0,
                    description TEXT,
                    rarity TEXT DEFAULT 'Common'
                )
            ''')
            
            # ===== CHAT MESSAGES =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ===== PVP DAILY =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS pvp_daily (
                    user_id INTEGER PRIMARY KEY,
                    fights_today INTEGER DEFAULT 0,
                    last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ===== SKILLS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    class TEXT,
                    level_req INTEGER DEFAULT 1,
                    mp_cost INTEGER DEFAULT 10,
                    type TEXT, -- 'damage', 'buff', 'multi_hit'
                    value REAL DEFAULT 0,
                    attack_bonus_percent REAL DEFAULT 0,
                    defense_bonus_percent REAL DEFAULT 0,
                    evasion_bonus_percent REAL DEFAULT 0,
                    crit_bonus_percent REAL DEFAULT 0,
                    reflect_percent REAL DEFAULT 0,
                    stun_chance REAL DEFAULT 0,
                    duration INTEGER DEFAULT 0,
                    description TEXT
                )
            ''')
            
            # ===== PLAYER SKILLS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_skills (
                    user_id INTEGER,
                    skill_id TEXT,
                    level INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, skill_id)
                )
            ''')
            
            # ===== ACTIVE BUFFS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS active_buffs (
                    user_id INTEGER,
                    skill_id TEXT,
                    remaining_turns INTEGER,
                    attack_bonus_percent REAL DEFAULT 0,
                    defense_bonus_percent REAL DEFAULT 0,
                    evasion_bonus_percent REAL DEFAULT 0,
                    crit_bonus_percent REAL DEFAULT 0,
                    reflect_percent REAL DEFAULT 0,
                    stun_chance REAL DEFAULT 0,
                    PRIMARY KEY (user_id, skill_id)
                )
            ''')
            
            # ===== SHOP ITEMS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS shop_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT,
                    name TEXT,
                    price_aden INTEGER DEFAULT 0,
                    price_stars INTEGER DEFAULT 0,
                    category TEXT DEFAULT 'consumable',
                    is_permanent INTEGER DEFAULT 1,
                    weekly_limit INTEGER DEFAULT 0,
                    description TEXT,
                    FOREIGN KEY (item_id) REFERENCES items(id)
                )
            ''')
            
            # ===== SHOP PURCHASES =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS shop_purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    shop_item_id INTEGER,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    week_number INTEGER,
                    FOREIGN KEY (user_id) REFERENCES players(user_id),
                    FOREIGN KEY (shop_item_id) REFERENCES shop_items(id)
                )
            ''')
            
            # ===== RECIPES =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_item_id TEXT,
                    result_quantity INTEGER DEFAULT 1,
                    level_req INTEGER DEFAULT 1,
                    craft_time INTEGER DEFAULT 5,
                    success_chance REAL DEFAULT 1.0,
                    description TEXT,
                    FOREIGN KEY (result_item_id) REFERENCES items(id)
                )
            ''')
            
            # ===== RECIPE MATERIALS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS recipe_materials (
                    recipe_id INTEGER,
                    material_id TEXT,
                    quantity INTEGER DEFAULT 1,
                    PRIMARY KEY (recipe_id, material_id),
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id),
                    FOREIGN KEY (material_id) REFERENCES items(id)
                )
            ''')
            
            # ===== PLAYER RECIPES =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_recipes (
                    user_id INTEGER,
                    recipe_id INTEGER,
                    learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, recipe_id)
                )
            ''')
            
            # ===== CRAFTING QUEUE =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS crafting_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    recipe_id INTEGER,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (user_id) REFERENCES players(user_id),
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
                )
            ''')
            
            # ===== ACHIEVEMENTS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    reward INTEGER DEFAULT 0,
                    target INTEGER DEFAULT 0
                )
            ''')
            
            # ===== PLAYER ACHIEVEMENTS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_achievements (
                    user_id INTEGER,
                    achievement_id TEXT,
                    progress INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0,
                    completed_at TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id)
                )
            ''')
            
            # ===== DONATIONS =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS donations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    stars_amount INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    transaction_id TEXT UNIQUE,
                    telegram_charge_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES players(user_id)
                )
            ''')
            
            # ===== STORE ITEMS (ДОНАТ) =====
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS store_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    description TEXT,
                    price_stars INTEGER DEFAULT 0,
                    reward_stars INTEGER DEFAULT 0,
                    reward_aden INTEGER DEFAULT 0,
                    reward_item_id TEXT,
                    reward_quantity INTEGER DEFAULT 1,
                    is_popular INTEGER DEFAULT 0,
                    icon TEXT DEFAULT '⭐'
                )
            ''')
            
            # ===== СИД МОНСТРОВ =====
            await cursor.execute("SELECT count(*) FROM monsters")
            if (await cursor.fetchone())[0] == 0:
                monsters = [
                    ("Крыса", 1, 1, "NG", 80, 80, 18, 8, 8, 100, 0, 8, 3, '{"drops": [{"id": "potion_hp_small", "name": "Малое зелье HP", "chance": 0.15}, {"id": "leather", "name": "Кожа", "chance": 0.10}]}'),
                    ("Слизень", 1, 1, "NG", 90, 90, 15, 10, 5, 100, 0, 10, 3, '{"drops": [{"id": "potion_hp_small", "name": "Малое зелье HP", "chance": 0.12}, {"id": "iron_shard", "name": "Осколок железа", "chance": 0.08}]}'),
                    ("Гоблин", 2, 1, "NG", 120, 120, 25, 12, 10, 110, 2, 12, 5, '{"drops": [{"id": "potion_hp_small", "name": "Малое зелье HP", "chance": 0.20}, {"id": "leather", "name": "Кожа", "chance": 0.15}, {"id": "herb", "name": "Трава", "chance": 0.15}]}'),
                    ("Волк", 3, 1, "NG", 160, 160, 32, 15, 12, 120, 5, 18, 8, '{"drops": [{"id": "potion_hp_small", "name": "Малое зелье HP", "chance": 0.18}, {"id": "wolf_fang", "name": "Волчий клык", "chance": 0.25}]}'),
                    ("Орк-воин", 6, 2, "D", 350, 350, 55, 25, 8, 150, 10, 35, 15, '{"drops": [{"id": "potion_hp_mid", "name": "Среднее зелье HP", "chance": 0.15}, {"id": "iron_shard", "name": "Осколок железа", "chance": 0.30}, {"id": "iron_sword", "name": "Железный меч", "chance": 0.02}]}'),
                ]
                await cursor.executemany('''
                    INSERT INTO monsters (name, level, tier, grade, hp, hp_max, attack, defense, evasion, crit_damage, resistance, exp_reward, aden_reward, loot_table)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', monsters)
            
            # ===== СИД ПРЕДМЕТОВ =====
            await cursor.execute("SELECT count(*) FROM items")
            if (await cursor.fetchone())[0] == 0:
                items = [
                    ("potion_hp_small", "Малое зелье HP", "consumable", "D", None, 1, 0, 0, 0, 0, 0, 0, 50, 15, "Восстанавливает 50 HP", "Common"),
                    ("potion_hp_mid", "Среднее зелье HP", "consumable", "C", None, 1, 0, 0, 0, 0, 0, 0, 100, 75, "Восстанавливает 100 HP", "Uncommon"),
                    ("potion_mp_small", "Малое зелье MP", "consumable", "D", None, 1, 0, 0, 0, 0, 0, 0, 30, 20, "Восстанавливает 30 MP", "Common"),
                    ("wooden_sword", "Деревянный меч", "weapon", "NG", "weapon", 1, 5, 0, 0, 0, 0, 0, 0, 150, "Базовое оружие", "Common"),
                    ("iron_sword", "Железный меч", "weapon", "D", "weapon", 6, 12, 0, 0, 0, 0, 0, 0, 750, "Прочное железное оружие", "Uncommon"),
                    ("iron_helmet", "Железный шлем", "armor", "D", "helmet", 6, 0, 5, 2, 0, 0, 0, 0, 200, "Железная защита головы", "Uncommon"),
                    ("iron_chest", "Железный нагрудник", "armor", "D", "chest", 6, 0, 12, 5, 0, 0, 0, 0, 600, "Железная защита тела", "Uncommon"),
                    ("steel_sword", "Стальной меч", "weapon", "C", "weapon", 11, 22, 0, 0, 0, 0, 0, 0, 3000, "Качественная сталь", "Rare"),
                    ("leather", "Кожа", "material", "NG", None, 1, 0, 0, 0, 0, 0, 0, 0, 5, "Материал для крафта", "Common"),
                    ("iron_shard", "Осколок железа", "material", "D", None, 1, 0, 0, 0, 0, 0, 0, 0, 10, "Материал для крафта", "Common"),
                    ("herb", "Трава", "material", "NG", None, 1, 0, 0, 0, 0, 0, 0, 0, 3, "Лечебная трава", "Common"),
                ]
                await cursor.executemany('''
                    INSERT INTO items (id, name, type, grade, slot, level_req, attack_bonus, defense_bonus, evasion_bonus, crit_damage_bonus, hp_bonus, mp_bonus, effect_value, value, description, rarity)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', items)
            
            # ===== СИД НАВЫКОВ =====
            await cursor.execute("SELECT count(*) FROM skills")
            if (await cursor.fetchone())[0] == 0:
                skills = [
                    ("slash", "Яростный удар", "berserk", 1, 0, "damage", 1.65, 0, 0, 0, 0, 0, 0, 0, "Урон ×1.65"),
                    ("blood_rush", "Кровавый натиск", "berserk", 5, 0, "damage", 2.2, 0, 0, 0, 0.2, 0, 0, 2, "Урон ×2.2 + +20% крит на 2 хода"),
                    ("berserk_rage", "Ярость берсерка", "berserk", 12, 0, "buff", 0, 0.45, -0.20, 0, 0.35, 0, 0, 3, "+45% атака, +35% крит, -20% защита на 3 хода"),
                    ("shield_bash", "Щитовой удар", "guardian", 1, 0, "damage", 1.0, 0, 0, 0, 0, 0, 0.5, 1, "Урон + стан на 1 ход"),
                    ("iron_wall", "Железная стена", "guardian", 6, 0, "buff", 0, 0, 0.40, 0, 0, 0.20, 0, 3, "+40% защита + 20% отражение на 3 хода"),
                    ("holy_revenge", "Священное возмездие", "guardian", 15, 0, "buff", 0, 0, 0, 0, 0, 0.45, 0, 3, "Отражает 45% урона на 3 хода"),
                    ("backstab", "Призрачный клинок", "critical", 1, 0, "damage", 1.5, 0, 0, 0.3, 0.2, 0, 0, 0, "Урон ×1.5 + высокий шанс крита"),
                    ("death_strike", "Смертельный выпад", "critical", 8, 0, "damage", 2.6, 0, 0, 0, 0.4, 0, 0, 0, "Урон ×2.6 + гарантированный крит при уклонении цели"),
                    ("shadow_dance", "Танец теней", "critical", 14, 0, "buff", 0, 0, 0, 0.25, 0.50, 0, 0, 4, "+50% крит +25% уклонение на 4 хода"),
                    ("thunder_smash", "Громовой молот", "stormbringer", 1, 0, "damage", 1.4, 0, 0, 0, 0, 0, 0.6, 1, "Урон + стан на 1-2 хода"),
                    ("earthquake", "Землетрясение", "stormbringer", 7, 0, "multi", 0.9, 0, 0, 0, 0, 0, 0, 2, "Урон по всем + замедление на 2 хода"),
                    ("storm_wave", "Разрушительная волна", "stormbringer", 16, 0, "damage", 2.8, 0, 0, 0, 0, 0, 0, 2, "Массивный урон + стан на 2 хода"),
                ]
                await cursor.executemany('''
                    INSERT INTO skills (id, name, class, level_req, mp_cost, type, value,
                                      attack_bonus_percent, defense_bonus_percent, evasion_bonus_percent,
                                      crit_bonus_percent, reflect_percent, stun_chance, duration, description)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', skills)
            
            # ===== СИД МАГАЗИНА =====
            await cursor.execute("SELECT count(*) FROM shop_items")
            if (await cursor.fetchone())[0] == 0:
                shop_items = [
                    ("potion_hp_small", "Малое зелье HP", 15, 0, "consumable", 1, 0, "Восстанавливает 50 HP"),
                    ("potion_hp_mid", "Среднее зелье HP", 75, 0, "consumable", 1, 0, "Восстанавливает 100 HP"),
                    ("potion_mp_small", "Малое зелье MP", 20, 0, "consumable", 1, 0, "Восстанавливает 30 MP"),
                    ("wooden_sword", "Деревянный меч", 150, 0, "weapon", 1, 0, "Базовое оружие"),
                    ("iron_sword", "Железный меч", 750, 0, "weapon", 1, 0, "Прочное железное оружие"),
                    ("iron_helmet", "Железный шлем", 200, 0, "armor", 1, 0, "Железная защита головы"),
                    ("iron_chest", "Железный нагрудник", 600, 0, "armor", 1, 0, "Железная защита тела"),
                ]
                await cursor.executemany('''
                    INSERT INTO shop_items (item_id, name, price_aden, price_stars, category, is_permanent, weekly_limit, description)
                    VALUES (?,?,?,?,?,?,?,?)
                ''', shop_items)
            
            # ===== СИД ДОНАТ ТОВАРОВ =====
            await cursor.execute("SELECT count(*) FROM store_items")
            if (await cursor.fetchone())[0] == 0:
                store_items = [
                    ("💎 50 Звезд", "Пополнение баланса", 50, 50, 0, None, 0, 1, "⭐"),
                    ("💎 100 Звезд", "Пополнение баланса", 100, 100, 0, None, 0, 1, "⭐"),
                    ("💎 250 Звезд", "Пополнение баланса", 250, 250, 0, None, 0, 1, "⭐"),
                    ("💎 500 Звезд", "Пополнение баланса", 500, 500, 0, None, 1, 1, "⭐"),
                    ("💰 5000 Аден", "Валюта игры", 10, 0, 5000, None, 0, 0, "💰"),
                ]
                await cursor.executemany('''
                    INSERT INTO store_items (name, description, price_stars, reward_stars, reward_aden, reward_item_id, reward_quantity, is_popular, icon)
                    VALUES (?,?,?,?,?,?,?,?,?)
                ''', store_items)
            
            # ===== СИД РЕЦЕПТОВ ДЛЯ КРАФТА =====
            await cursor.execute("SELECT count(*) FROM recipes")
            if (await cursor.fetchone())[0] == 0:
                recipes = [
                    ("iron_sword", 1, 1, 30, 0.8, "Железный меч"),
                    ("iron_helmet", 1, 1, 20, 0.85, "Железный шлем"),
                    ("iron_chest", 1, 1, 45, 0.75, "Железный нагрудник"),
                    ("potion_hp_small", 1, 1, 1, 1.0, "Малое зелье HP"),
                    ("potion_mp_small", 1, 1, 1, 1.0, "Малое зелье MP"),
                ]
                await cursor.executemany('''
                    INSERT INTO recipes (result_item_id, result_quantity, level_req, craft_time, success_chance, description)
                    VALUES (?,?,?,?,?,?)
                ''', recipes)
                
                recipe_materials = [
                    (1, "leather", 5), (1, "iron_shard", 10),
                    (2, "leather", 3), (2, "iron_shard", 5),
                    (3, "leather", 8), (3, "iron_shard", 12),
                    (4, "herb", 3),
                    (5, "magic_dust", 2),
                ]
                await cursor.executemany('''
                    INSERT INTO recipe_materials (recipe_id, material_id, quantity)
                    VALUES (?,?,?)
                ''', recipe_materials)
            
            # ===== СИД ДОСТИЖЕНИЙ =====
            await cursor.execute("SELECT count(*) FROM achievements")
            if (await cursor.fetchone())[0] == 0:
                achievements = [
                    ("monster_hunter", "Охотник на монстров", "Убейте 10 монстров", 50, 10),
                    ("elite_slayer", "Убийца элиты", "Убейте 5 элитных монстров", 100, 5),
                    ("boss_killer", "Покоритель боссов", "Победите босса", 250, 1),
                    ("pioneer", "Первопроходец", "Достигните 5 уровня", 50, 5),
                    ("veteran", "Ветеран", "Достигните 15 уровня", 200, 15),
                    ("wealthy", "Богач", "Соберите 10,000 аден", 100, 10000),
                ]
                await cursor.executemany('''
                    INSERT INTO achievements (id, name, description, reward, target)
                    VALUES (?,?,?,?,?)
                ''', achievements)

            await self.run_migrations()
            logger.info("Database initialized with anti-cheat tables and achievements (WAL mode enabled)")

    async def run_migrations(self):
        """Проверка и применение миграций БД для существующих таблиц"""
        async with self.get_cursor() as cursor:
            # --- Players ---
            await cursor.execute("PRAGMA table_info(players)")
            columns = [row[1] for row in await cursor.fetchall()]

            migrations = [
                ('attack', 'INTEGER DEFAULT 20'),
                ('defense', 'INTEGER DEFAULT 15'),
                ('evasion', 'INTEGER DEFAULT 5'),
                ('crit_damage', 'INTEGER DEFAULT 10'),
                ('resistance', 'REAL DEFAULT 0'),
                ('strength', 'REAL DEFAULT 0'),
                ('agility', 'REAL DEFAULT 0'),
                ('endurance', 'REAL DEFAULT 0'),
                ('intuition', 'REAL DEFAULT 0'),
                ('energy', 'INTEGER DEFAULT 100'),
                ('energy_max', 'INTEGER DEFAULT 100'),
                ('last_energy_regen', 'TIMESTAMP'),
                ('auto_battle_daily_limit', 'INTEGER DEFAULT 300'),
                ('exp_max', 'INTEGER DEFAULT 120'),
                ('premium_until', 'TIMESTAMP'),
                ('premium_type', 'TEXT')
            ]

            for col_name, col_def in migrations:
                if col_name not in columns:
                    await cursor.execute(f"ALTER TABLE players ADD COLUMN {col_name} {col_def}")
                    logger.info(f"Migration: Added column {col_name} to players")

            # --- Monsters ---
            await cursor.execute("PRAGMA table_info(monsters)")
            columns = [row[1] for row in await cursor.fetchall()]
            if 'crit_damage' not in columns:
                await cursor.execute("ALTER TABLE monsters ADD COLUMN crit_damage INTEGER DEFAULT 100")
            if 'resistance' not in columns:
                await cursor.execute("ALTER TABLE monsters ADD COLUMN resistance REAL DEFAULT 0")

            # --- Items ---
            await cursor.execute("PRAGMA table_info(items)")
            columns = [row[1] for row in await cursor.fetchall()]
            for col in ['attack_bonus', 'defense_bonus', 'evasion_bonus', 'crit_damage_bonus']:
                if col not in columns:
                    await cursor.execute(f"ALTER TABLE items ADD COLUMN {col} INTEGER DEFAULT 0")

            # --- Skills & Buffs ---
            for table in ['skills', 'active_buffs']:
                await cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in await cursor.fetchall()]
                skill_migrations = [
                    ('attack_bonus_percent', 'REAL DEFAULT 0'),
                    ('defense_bonus_percent', 'REAL DEFAULT 0'),
                    ('evasion_bonus_percent', 'REAL DEFAULT 0'),
                    ('crit_bonus_percent', 'REAL DEFAULT 0'),
                    ('reflect_percent', 'REAL DEFAULT 0'),
                    ('stun_chance', 'REAL DEFAULT 0')
                ]
                for col_name, col_def in skill_migrations:
                    if col_name not in columns:
                        await cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")

    # ===== ОСНОВНЫЕ МЕТОДЫ =====
    
    async def get_player(self, user_id: int) -> Optional[Dict]:
        """Получение данных игрока с регенерацией энергии"""
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row: return None
            player = dict(row)

            # Регенерация энергии (1 в 3 минуты)
            now = datetime.now()
            last_regen = player.get("last_energy_regen")
            if last_regen:
                if isinstance(last_regen, str):
                    try:
                        last_regen = datetime.fromisoformat(last_regen)
                    except ValueError:
                        last_regen = None

                if last_regen:
                    seconds_passed = (now - last_regen).total_seconds()
                    energy_to_add = int(seconds_passed / 180)

                    if energy_to_add > 0 and player["energy"] < player["energy_max"]:
                        new_energy = min(player["energy_max"], player["energy"] + energy_to_add)
                        new_regen_time = now.isoformat() if new_energy < player["energy_max"] else None

                        await cursor.execute(
                            "UPDATE players SET energy = ?, last_energy_regen = ? WHERE user_id = ?",
                            (new_energy, new_regen_time, user_id)
                        )
                        player["energy"] = new_energy
                        player["last_energy_regen"] = new_regen_time
            elif player["energy"] < player["energy_max"]:
                await cursor.execute(
                    "UPDATE players SET last_energy_regen = ? WHERE user_id = ?",
                    (now.isoformat(), user_id)
                )
                player["last_energy_regen"] = now.isoformat()

            await cursor.execute("SELECT * FROM equipment WHERE user_id = ?", (user_id,))
            equip = await cursor.fetchone()
            if equip: equip = dict(equip)
            player["equipment"] = equip if equip else {}
            return player

    async def get_player_by_token(self, token: str) -> Optional[Dict]:
        user_id = await self.get_user_by_token(token)
        if user_id:
            return await self.get_player(user_id)
        return None

    async def update_player(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """ИСПРАВЛЕНО: Обновление произвольных полей игрока по словарю {field: value}"""
        if not updates:
            return False
        # ИСПРАВЛЕНО: Добавлены недостающие поля (aden, mp, mp_max, premium_*, attack, defense, evasion, crit_damage)
        allowed_fields = {
            "hp", "hp_max", "mp", "mp_max", "energy", "energy_max", "level", "exp", "exp_max",
            "aden", "stars", "name", "char_class", "pvp_wins", "pvp_losses",
            "is_banned", "last_energy_regen", "daily_streak", "last_daily", "rating",
            "ton", "premium_until", "premium_type", "attack", "defense", "evasion", "crit_damage"
        }
        safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        if not safe_updates:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in safe_updates)
        values = list(safe_updates.values()) + [user_id]
        async with self.get_cursor() as cursor:
            await cursor.execute(
                f"UPDATE players SET {set_clause} WHERE user_id = ?",
                values,
            )
        return True

    async def create_player(self, user_id: int, name: str, char_class: str, ref_code: Optional[str] = None, ip_address: Optional[str] = None) -> Dict:
        """Создание персонажа с приземлёнными статами + полная энергия + премиум-поддержка"""

        class_base_stats = {
            "berserk":      {"strength": 10, "agility": 7,  "endurance": 9,  "intuition": 5},
            "guardian":     {"strength": 8,  "agility": 6,  "endurance": 13, "intuition": 7},
            "critical":     {"strength": 7,  "agility": 12, "endurance": 7,  "intuition": 9},
            "stormbringer": {"strength": 9,  "agility": 8,  "endurance": 10, "intuition": 8}
        }

        base = class_base_stats.get(char_class, class_base_stats["berserk"])

        referral_code = secrets.token_urlsafe(12)
        if not name or len(name) > 32:
            name = f"Hero_{user_id % 10000}"

        referrer_id = None
        if ref_code and ref_code != referral_code:
            async with self.get_cursor() as cursor:
                await cursor.execute("SELECT user_id FROM players WHERE referral_code = ?", (ref_code,))
                row = await cursor.fetchone()
                if row: row = dict(row)
                if row:
                    referrer_id = row["user_id"]

        async with self.get_cursor() as cursor:
            await cursor.execute('''
                INSERT INTO players (
                    user_id, name, class,
                    strength, agility, endurance, intuition,
                    hp, hp_max, mp, mp_max,
                    energy, energy_max,
                    level, exp, exp_max,
                    aden, stars,
                    referral_code, referrer_id, registration_ip,
                    daily_streak, last_daily
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, name, char_class,
                base["strength"], base["agility"], base["endurance"], base["intuition"],
                85, 85, 50, 50,
                100, 100,                    # ← Энергия начинается ПОЛНОСТЬЮ заполненной
                1, 0, 120,
                120, 0,                      # стартовые 120 аден
                referral_code, referrer_id, ip_address,
                0, None
            ))

            # Создаём таблицы
            await cursor.execute("INSERT INTO equipment (user_id) VALUES (?)", (user_id,))
            await cursor.execute("INSERT INTO farming_stats (user_id) VALUES (?)", (user_id,))
            await cursor.execute("INSERT INTO pvp_daily (user_id) VALUES (?)", (user_id,))
            await cursor.execute("INSERT INTO crafting_limits (user_id) VALUES (?)", (user_id,))

            # Стартовые навыки
            class_skills = {
                "berserk": ["slash"],
                "guardian": ["shield_bash"],
                "critical": ["backstab"],
                "stormbringer": ["thunder_smash"]
            }
            for skill_id in class_skills.get(char_class, []):
                await cursor.execute(
                    "INSERT INTO player_skills (user_id, skill_id, level) VALUES (?, ?, 1)",
                    (user_id, skill_id)
                )

        # Пересчёт статов + первая ежедневная награда
        await self._recalculate_stats(user_id)
        await self.get_daily_bonus(user_id)           # первая награда при создании
        await self.add_exp(user_id, 500, monster_level=3) # быстрый старт (2–3 уровень)

        # Финальное восстановление
        async with self.get_cursor() as cursor:
            await cursor.execute("""
                UPDATE players
                SET hp = hp_max,
                    mp = mp_max,
                    energy = energy_max
                WHERE user_id = ?
            """, (user_id,))

        return await self.get_player(user_id)

    async def get_pvp_daily_limit(self, user_id: int) -> tuple:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT fights_today, last_reset FROM pvp_daily WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row: row = dict(row)
            if not row:
                return 10, 0
            last_reset = datetime.fromisoformat(row["last_reset"])
            now = datetime.now()
            if now.date() > last_reset.date():
                await cursor.execute("UPDATE pvp_daily SET fights_today = 0, last_reset = ? WHERE user_id = ?", (now.isoformat(), user_id))
                return 10, 0
            fights = row["fights_today"]
            return max(0, 10 - fights), fights

    async def add_pvp_fight(self, user_id: int):
        async with self.get_cursor() as cursor:
            await cursor.execute("UPDATE pvp_daily SET fights_today = fights_today + 1 WHERE user_id = ?", (user_id,))

    async def get_rating_top(self, limit: int = 10) -> List[Dict]:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT user_id, name, level, rating, pvp_wins, pvp_losses FROM players ORDER BY rating DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ===== НАВЫКИ И БАФЫ (ИСПРАВЛЕНО: Добавлены недостающие методы) =====

    async def get_player_skills(self, user_id: int, char_class: str = None, level: int = 1) -> List[Dict]:
        """Получение изученных и доступных для изучения навыков"""
        async with self.get_cursor() as cursor:
            await cursor.execute('''
                SELECT ps.skill_id, ps.level, s.name, s.mp_cost, s.type, s.value, s.description, s.duration
                FROM player_skills ps
                JOIN skills s ON ps.skill_id = s.id
                WHERE ps.user_id = ?
            ''', (user_id,))
            learned = [dict(row) for row in await cursor.fetchall()]
            
            # Получаем доступные для изучения
            if char_class:
                await cursor.execute('''
                    SELECT s.id, s.name, s.level_req, s.mp_cost, s.type, s.value, s.description
                    FROM skills s
                    WHERE s.class = ? AND s.id NOT IN (SELECT skill_id FROM player_skills WHERE user_id = ?) AND s.level_req <= ?
                ''', (char_class, user_id, level))
                available = [dict(row) for row in await cursor.fetchall()]
            else:
                available = []
            
            return learned + available

    async def learn_skill(self, user_id: int, skill_id: str) -> Dict:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT level FROM player_skills WHERE user_id = ? AND skill_id = ?", (user_id, skill_id))
            if await cursor.fetchone():
                return {"success": False, "error": "Skill already learned"}
            await cursor.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
            skill = await cursor.fetchone()
            if not skill: return {"success": False, "error": "Skill not found"}
            await cursor.execute("INSERT INTO player_skills (user_id, skill_id, level) VALUES (?, ?, 1)", (user_id, skill_id))
            return {"success": True, "message": f"Learned {skill['name']}"}

    async def upgrade_skill(self, user_id: int, skill_id: str) -> Dict:
        return {"success": False, "error": "Not implemented yet"}

    async def use_skill(self, user_id: int, skill_id: str, current_mp: int) -> Dict:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT * FROM player_skills WHERE user_id = ? AND skill_id = ?", (user_id, skill_id))
            if not await cursor.fetchone():
                return {"success": False, "error": "Skill not learned"}
            
            await cursor.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
            skill = dict(await cursor.fetchone())
            
            if current_mp < skill["mp_cost"]:
                return {"success": False, "error": "Not enough MP"}
            
            return {
                "success": True, "name": skill["name"], "mp_cost": skill["mp_cost"], "type": skill["type"],
                "multiplier": skill.get("value", 1.5), "hits": 3 if skill["type"] == "multi" else 1,
                "attack_bonus_percent": skill.get("attack_bonus_percent", 0),
                "defense_bonus_percent": skill.get("defense_bonus_percent", 0),
                "evasion_bonus_percent": skill.get("evasion_bonus_percent", 0),
                "crit_bonus_percent": skill.get("crit_bonus_percent", 0),
                "reflect_percent": skill.get("reflect_percent", 0),
                "stun_chance": skill.get("stun_chance", 0),
                "duration": skill.get("duration", 3)
            }

    async def get_active_buffs(self, user_id: int) -> Dict[str, Dict]:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT * FROM active_buffs WHERE user_id = ?", (user_id,))
            rows = await cursor.fetchall()
            return {row["skill_id"]: dict(row) for row in rows}

    async def add_buff(self, user_id: int, skill_id: str, atk: float, defen: float, eva: float, crit: float, ref: float, stun: float, dur: int):
        async with self.get_cursor() as cursor:
            await cursor.execute('''INSERT INTO active_buffs (user_id, skill_id, remaining_turns, attack_bonus_percent, defense_bonus_percent, evasion_bonus_percent, crit_bonus_percent, reflect_percent, stun_chance) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_id, skill_id) DO UPDATE SET remaining_turns = ?''', 
            (user_id, skill_id, dur, atk, defen, eva, crit, ref, stun, dur))

    async def decrement_buffs(self, user_id: int):
        async with self.get_cursor() as cursor:
            await cursor.execute("DELETE FROM active_buffs WHERE user_id = ? AND remaining_turns <= 1", (user_id,))
            await cursor.execute("UPDATE active_buffs SET remaining_turns = remaining_turns - 1 WHERE user_id = ?", (user_id,))

    # ===== ИНВЕНТАРЬ, ПРЕДМЕТЫ, ДРОП (ИСПРАВЛЕНО: Добавлены недостающие методы) =====

    async def add_item(self, user_id: int, item_id: str, qty: int = 1):
        async with self.get_cursor() as cursor:
            await cursor.execute('''INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?) 
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?''', (user_id, item_id, qty, qty))

    async def process_drop(self, user_id: int, monster: dict) -> List[Dict]:
        drops = []
        loot_table = json.loads(monster.get("loot_table", "{}")).get("drops", [])
        for drop in loot_table:
            if random.random() < drop["chance"]:
                await self.add_item(user_id, drop["id"])
                drops.append(drop)
        return drops

    async def get_monster_by_id(self, monster_id: int) -> Optional[Dict]:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT * FROM monsters WHERE id = ?", (monster_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    # ===== БОЕВАЯ СИСТЕМА (Опыт, Усталость, Фарм) =====

    async def add_fight(self, user_id: int):
        async with self.get_cursor() as cursor:
            await cursor.execute("UPDATE farming_stats SET fights_today = fights_today + 1, total_fights = total_fights + 1 WHERE user_id = ?", (user_id,))

    async def get_farming_fatigue(self, user_id: int) -> float:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT fights_today, last_reset FROM farming_stats WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row: return 1.0
            row = dict(row)
            if datetime.fromisoformat(row["last_reset"]).date() != datetime.now().date():
                await cursor.execute("UPDATE farming_stats SET fights_today = 0, last_reset = ? WHERE user_id = ?", (datetime.now().isoformat(), user_id))
                return 1.0
            fights = row["fights_today"]
            return max(0.1, 1.0 - (fights / 500))

    async def add_exp(self, user_id: int, amount: int, monster_level: int = 1, tier: int = 1) -> Dict:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
            p = dict(await cursor.fetchone())
            p["exp"] += amount
            level_up = False
            while p["exp"] >= p["exp_max"]:
                p["exp"] -= p["exp_max"]
                p["level"] += 1
                p["exp_max"] = int(p["exp_max"] * 1.2)
                level_up = True
            await cursor.execute("UPDATE players SET level = ?, exp = ?, exp_max = ? WHERE user_id = ?", (p["level"], p["exp"], p["exp_max"], user_id))
            if level_up:
                await self._recalculate_stats(user_id)
            return {"level_up": level_up, "new_level": p["level"]}

    async def _recalculate_stats(self, user_id: int):
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
            p = dict(await cursor.fetchone())
            lvl = p["level"]
            hp_max = int(85 + lvl * 15 + p["endurance"] * 5)
            mp_max = int(50 + lvl * 5 + p["intuition"] * 2)
            attack = int(20 + lvl * 3 + p["strength"] * 2)
            defense = int(15 + lvl * 2 + p["endurance"])
            evasion = int(5 + lvl + p["agility"])
            await cursor.execute("UPDATE players SET hp_max=?, mp_max=?, attack=?, defense=?, evasion=? WHERE user_id=?", (hp_max, mp_max, attack, defense, evasion, user_id))

    # ===== РЕФЕРАЛЬНАЯ СИСТЕМА =====
    
    async def get_referral_stats(self, user_id: int) -> Dict:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) as count, SUM(is_active) as active_count FROM referrals WHERE referrer_id = ?", (user_id,))
            stats = await cursor.fetchone()
            if stats: stats = dict(stats)
            total_referrals = stats["count"] if stats else 0
            active_referrals = stats["active_count"] if stats else 0
            
            await cursor.execute("SELECT COALESCE(SUM(amount_aden), 0) as total_aden, COALESCE(SUM(amount_stars), 0) as total_stars FROM referral_commissions WHERE referrer_id = ?", (user_id,))
            commissions = await cursor.fetchone()
            if commissions: commissions = dict(commissions)
            
            await cursor.execute('''
                SELECT r.referred_id, p.name, p.level, r.is_active, r.created_at, r.became_active_at,
                       r.total_donations_stars, r.total_fights
                FROM referrals r JOIN players p ON r.referred_id = p.user_id
                WHERE r.referrer_id = ? ORDER BY r.created_at DESC
            ''', (user_id,))
            referrals_list = await cursor.fetchall()
            
            await cursor.execute('''
                SELECT rc.*, p.name as referred_name
                FROM referral_commissions rc JOIN players p ON rc.referred_id = p.user_id
                WHERE rc.referrer_id = ? ORDER BY rc.created_at DESC LIMIT 50
            ''', (user_id,))
            commissions_list = await cursor.fetchall()
            
            await cursor.execute("SELECT referral_code FROM players WHERE user_id = ?", (user_id,))
            player = await cursor.fetchone()
            if player: player = dict(player)
            bot_info = await self.get_bot_info()
            referral_link = f"https://t.me/{bot_info['username']}?start=ref_{player['referral_code']}"
            
            return {
                "total_referrals": total_referrals,
                "active_referrals": active_referrals,
                "total_commission_aden": commissions["total_aden"] if commissions else 0,
                "total_commission_stars": commissions["total_stars"] if commissions else 0,
                "referrals": [dict(row) for row in referrals_list],
                "commissions_history": [dict(row) for row in commissions_list],
                "referral_link": referral_link
            }

    async def get_bot_info(self):
        if self._bot_info:
            return self._bot_info
        from aiogram import Bot
        import os
        bot = Bot(token=os.getenv("BOT_TOKEN", ""))
        bot_info = await bot.get_me()
        await bot.session.close()
        self._bot_info = {"username": bot_info.username}
        return self._bot_info

    async def update_achievement(self, user_id: int, achievement_id: str, progress_increment: int = 1):
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT * FROM achievements WHERE id = ?", (achievement_id,))
            achievement = await cursor.fetchone()
            if achievement: achievement = dict(achievement)
            if not achievement:
                return
            await cursor.execute('''
                INSERT INTO player_achievements (user_id, achievement_id, progress, completed) VALUES (?, ?, ?, 0)
                ON CONFLICT(user_id, achievement_id) DO UPDATE SET progress = progress + ?
            ''', (user_id, achievement_id, progress_increment, progress_increment))
            await cursor.execute("SELECT progress, completed FROM player_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, achievement_id))
            p_ach = await cursor.fetchone()
            if p_ach: p_ach = dict(p_ach)
            if not p_ach["completed"] and p_ach["progress"] >= achievement["target"]:
                await cursor.execute('''
                    UPDATE player_achievements SET completed = 1, completed_at = ? WHERE user_id = ? AND achievement_id = ?
                ''', (datetime.now().isoformat(), user_id, achievement_id))
                await cursor.execute("UPDATE players SET stars = stars + ? WHERE user_id = ?", (achievement["reward"], user_id))

    async def use_consumable(self, user_id: int, item_id: str) -> tuple:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id))
            row = await cursor.fetchone()
            if row: row = dict(row)
            if not row or row["quantity"] <= 0:
                return False, "Item not found"
            await cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ? AND quantity > 0", (user_id, item_id))
            return True, "Item used"

    async def get_daily_bonus(self, user_id: int) -> Dict:
        async with self.get_cursor() as cursor:
            await cursor.execute("SELECT last_daily, daily_streak FROM players WHERE user_id = ?", (user_id,))
            player = await cursor.fetchone()
            if player: player = dict(player)
            last_daily = datetime.fromisoformat(player["last_daily"]) if player["last_daily"] else None
            now = datetime.now()
            if last_daily and last_daily.date() == now.date():
                return {"available": False, "next_in": "tomorrow"}
            if last_daily and (now - last_daily).days == 1:
                streak = player["daily_streak"] + 1
            else:
                streak = 1
            streak = min(streak, 30)
            rewards = {1: {"aden": 100, "exp": 30}, 3: {"aden": 200, "exp": 60, "item": "potion_hp_small"}, 7: {"aden": 500, "exp": 150, "item": "potion_hp_mid", "stars": 5}, 14: {"aden": 1000, "exp": 300, "item": "iron_sword", "stars": 10}, 30: {"aden": 3000, "exp": 1000, "item": "steel_sword", "stars": 25}}
            reward_key = max([k for k in rewards.keys() if k <= streak], default=1)
            reward = rewards[reward_key]
            await cursor.execute("UPDATE players SET aden = aden + ?, exp = exp + ?, daily_streak = ?, last_daily = ? WHERE user_id = ?", (reward["aden"], reward["exp"], streak, now.isoformat(), user_id))
            if "item" in reward:
                await self.add_item(user_id, reward["item"])
            return {"available": True, "streak": streak, "reward": reward}
