from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import random
import time
from datetime import datetime

from fastapi import Request
from app.database import db
from app.auth import get_current_user
from app.routers.quests import update_quest_progress
from app.utils.limiter import limiter
from app.utils.redis_client import redis_client
from app.utils.security import log_audit, check_suspicious_activity
from app.utils.battle_nonce import (
    generate_battle_nonce, validate_battle_nonce,
    get_battle_lock,
    create_battle_state, get_battle_state,
    update_battle_state, finish_battle,
    BATTLE_TTL_SECONDS
)
from app.services.auto_battle_service import AutoBattleService

router = APIRouter(prefix="/api/battle", tags=["battle"])


class BattleTurnRequest(BaseModel):
    """Запрос на ход в бою"""
    monster_id: int = Field(..., ge=1, description="ID монстра")
    skill_id: Optional[str] = Field(None, description="ID навыка (если используется навык)")
    nonce: str = Field(..., min_length=10, description="Уникальный одноразовый токен")
    current_hp: Optional[int] = Field(None, ge=0, description="Текущее HP игрока")
    current_monster_hp: Optional[int] = Field(None, ge=0, description="Текущее HP монстра")


class StartBattleRequest(BaseModel):
    """Запрос на начало боя"""
    monster_id: int = Field(..., ge=1, description="ID монстра")


class CancelBattleRequest(BaseModel):
    """Запрос на отмену боя"""
    battle_id: str = Field(..., min_length=10, description="ID боя")


@router.post("/start")
@limiter.limit("30/minute")
async def start_battle(
    request: Request,
    req: StartBattleRequest,
    user_id: int = Depends(get_current_user)
):
    """
    Начало боя с монстром с защитой от спама
    """
    # 0. Проверка глобального кулдауна на начало боя (1 сек) в Redis
    cooldown_key = f"battle_start_cooldown:{user_id}"
    if await redis_client.get(cooldown_key):
        raise HTTPException(429, "Too many battle requests. Please wait.")
    await redis_client.set(cooldown_key, "1", expire=1)

    player = await db.get_player(user_id)
    if not player:
        raise HTTPException(404, "Player not found")
    
    monster = await db.get_monster_by_id(req.monster_id)
    if not monster:
        raise HTTPException(404, "Monster not found")

    # ИСПРАВЛЕНО: Проверка энергии (минимум 2)
    if player.get("energy", 0) < 2:
        raise HTTPException(400, "Not enough energy. Wait for regeneration.")
    
    # ИСПРАВЛЕНО: Списываем энергию сразу при старте боя
    await db.update_player(user_id, {"energy": player["energy"] - 2})

    # Проверяем, не в бою ли уже игрок
    existing_battle_id = await redis_client.get(f"user_battle:{user_id}")
    if existing_battle_id:
        state = await get_battle_state(existing_battle_id)
        if state and not state.get("is_finished"):
            raise HTTPException(400, "You are already in a battle")
    
    # Генерируем уникальный ID боя
    battle_id = f"battle_{user_id}_{req.monster_id}_{int(datetime.now().timestamp())}"
    
    # Создаем состояние боя
    await create_battle_state(
        battle_id=battle_id,
        player_id=user_id,
        monster_id=req.monster_id,
        monster_hp=monster.get("hp", 100)
    )
    await redis_client.set(f"user_battle:{user_id}", battle_id, expire=BATTLE_TTL_SECONDS)
    
    # Генерируем начальный nonce
    initial_nonce = generate_battle_nonce()
    
    return {
        "success": True,
        "battle_id": battle_id,
        "nonce": initial_nonce,
        "monster": {
            "id": monster["id"],
            "name": monster["name"],
            "hp": monster.get("hp", 100),
            "hp_max": monster.get("hp", 100),
            "attack": monster.get("attack", 10),
            "defense": monster.get("defense", 5),
            "evasion": monster.get("evasion", 5),
            "level": monster.get("level", 1),
            "exp_reward": monster.get("exp_reward", 10),
            "aden_reward": monster.get("aden_reward", 5)
        },
        "player": {
            "hp": player.get("hp", player.get("hp_max", 100)),
            "hp_max": player.get("hp_max", 100),
            "mp": player.get("mp", player.get("mp_max", 50)),
            "mp_max": player.get("mp_max", 50),
            "attack": player.get("attack", 20),
            "defense": player.get("defense", 15),
            "evasion": player.get("evasion", 5),
            "level": player.get("level", 1)
        }
    }


@router.get("/state")
async def get_battle_state_endpoint(
    battle_id: str,
    user_id: int = Depends(get_current_user)
):
    """Получение текущего состояния боя"""
    battle_state = await get_battle_state(battle_id)
    
    if not battle_state:
        raise HTTPException(404, "Battle not found")
    
    if battle_state.get("player_id") != user_id:
        raise HTTPException(403, "Not your battle")
    
    player = await db.get_player(user_id)
    monster = await db.get_monster_by_id(battle_state["monster_id"])
    
    current_nonce = generate_battle_nonce()
    
    return {
        "success": True,
        "battle_id": battle_id,
        "nonce": current_nonce,
        "is_finished": battle_state.get("is_finished", False),
        "monster_hp": battle_state.get("monster_hp", monster.get("hp", 100) if monster else 100),
        "monster_max_hp": monster.get("hp", 100) if monster else 100,
        "player_hp": player.get("hp", player.get("hp_max", 100)) if player else 100,
        "player_max_hp": player.get("hp_max", 100) if player else 100,
        "turn_number": battle_state.get("turn_number", 0)
    }


@router.post("/turn")
@limiter.limit("120/minute")
async def battle_turn(
    request: Request,
    req: BattleTurnRequest,
    user_id: int = Depends(get_current_user)
):
    """Ход в бою с защитой от replay-атак"""
    battle_id = await redis_client.get(f"user_battle:{user_id}")
    battle_state = await get_battle_state(battle_id) if battle_id else None
    
    if battle_state and (battle_state.get("monster_id") != req.monster_id or battle_state.get("is_finished")):
        battle_state = None

    if not battle_state:
        monster = await db.get_monster_by_id(req.monster_id)
        if not monster:
            raise HTTPException(404, "Monster not found")
        
        battle_id = f"battle_{user_id}_{req.monster_id}_{int(datetime.now().timestamp())}"
        await create_battle_state(
            battle_id=battle_id,
            player_id=user_id,
            monster_id=req.monster_id,
            monster_hp=monster.get("hp", 100)
        )
        await redis_client.set(f"user_battle:{user_id}", battle_id, expire=BATTLE_TTL_SECONDS)
        battle_state = await get_battle_state(battle_id)
    
    if not await validate_battle_nonce(battle_id, req.nonce):
        raise HTTPException(409, "Invalid or expired nonce. Please refresh battle state.")
    
    lock = get_battle_lock(battle_id)
    async with lock:
        await log_audit(user_id, "battle_turn", "info", request.client.host)
        if await check_suspicious_activity(user_id, "battle_turn", window_seconds=60, threshold=100):
            await log_audit(user_id, "suspicious_battle_activity", "warning", request.client.host)
            
        if battle_state.get("is_finished"):
            raise HTTPException(400, "Battle already finished")
        
        player = await db.get_player(user_id)
        if not player:
            raise HTTPException(404, "Player not found")
        
        monster = await db.get_monster_by_id(battle_state["monster_id"])
        if not monster:
            raise HTTPException(404, "Monster not found")
        
        db_player_hp = player.get("hp", 0)
        if db_player_hp <= 0:
            db_player_hp = max(1, int(player.get("hp_max", 100) * 0.3))
            await db.update_player(user_id, {"hp": db_player_hp})
        current_player_hp = db_player_hp
        current_monster_hp = req.current_monster_hp if req.current_monster_hp else battle_state.get("monster_hp", monster.get("hp", 100))
        
        if req.skill_id:
            result = await process_skill_attack(
                user_id, player, monster, req.skill_id,
                current_player_hp, current_monster_hp, battle_id
            )
            await update_quest_progress(user_id, "skills", 1)
        else:
            result = await process_normal_attack(
                player, monster, current_player_hp, current_monster_hp, battle_id
            )
        
        if result.get("victory") or result.get("is_dead"):
            await update_battle_state(battle_id, {
                "monster_hp": 0 if result.get("victory") else battle_state.get("monster_hp"),
                "is_finished": True,
                "finished_at": datetime.now().isoformat()
            })
            await finish_battle(battle_id)
            await redis_client.delete(f"user_battle:{user_id}")
        else:
            await update_battle_state(battle_id, {
                "monster_hp": result["monster_hp"],
                "last_action_at": datetime.now().isoformat(),
                "turn_number": battle_state.get("turn_number", 0) + 1
            })
        
        next_nonce = generate_battle_nonce()
        result["next_nonce"] = next_nonce
        result["battle_id"] = battle_id
        result["success"] = True
        
        return result


async def process_normal_attack(
    player: dict,
    monster: dict,
    current_player_hp: int,
    current_monster_hp: int,
    battle_id: str
) -> dict:
    """Обработка обычной атаки"""
    buffs = await db.get_active_buffs(player["user_id"])
    atk_mult = 1.0 + sum(b.get("attack_bonus_percent", 0) for b in buffs.values())
    def_mult = 1.0 + sum(b.get("defense_bonus_percent", 0) for b in buffs.values())
    eva_mult = 1.0 + sum(b.get("evasion_bonus_percent", 0) for b in buffs.values())
    crit_bonus_sum = sum(b.get("crit_bonus_percent", 0) for b in buffs.values())
    reflect_sum = sum(b.get("reflect_percent", 0) for b in buffs.values())
    stun_chance_sum = sum(b.get("stun_chance", 0) for b in buffs.values())

    premium_atk = 1.15 if player.get("premium_until") and datetime.fromisoformat(player["premium_until"]) > datetime.now() else 1.0
    
    player_attack = int(player.get("attack", 20) * atk_mult * premium_atk)
    damage_player = max(1, player_attack - (monster.get("defense", 0) // 2))
    
    if damage_player > 0:
        await update_quest_progress(player["user_id"], "damage", damage_player)

    is_crit_player = False
    player_crit_chance = 5 + (player.get("intuition", 0) * 0.2) + (crit_bonus_sum * 100)
    if random.randint(1, 100) <= player_crit_chance:
        is_crit_player = True
        crit_multiplier = player.get("crit_damage", 150) / 100
        damage_player = int(damage_player * crit_multiplier)

    player_hit_chance = max(50, 95 - monster.get("evasion", 5))
    if random.randint(1, 100) > player_hit_chance:
        damage_player = 0
        is_crit_player = False
    
    monster_attack = monster.get("attack", 10)
    player_defense = int(player.get("defense", 15) * def_mult)
    damage_monster = max(1, monster_attack - (player_defense // 2))
    
    is_crit_monster = False
    monster_crit_chance = monster.get("crit_damage", 100) / 10 if "crit_damage" in monster else 5
    if random.randint(1, 100) <= monster_crit_chance:
        is_crit_monster = True
        damage_monster = int(damage_monster * 1.5)

    monster_hit_chance = max(30, 95 - int(player.get("evasion", 5) * eva_mult))
    if random.randint(1, 100) > monster_hit_chance:
        damage_monster = 0
        is_crit_monster = False

    reflected_to_monster = 0
    if damage_monster > 0 and reflect_sum > 0:
        reflected_to_monster = int(damage_monster * reflect_sum)
    
    monster_stunned = False
    if damage_player > 0 and stun_chance_sum > 0:
        if random.random() < stun_chance_sum:
            monster_stunned = True

    new_monster_hp = max(0, current_monster_hp - (damage_player + reflected_to_monster))
    new_player_hp = max(0, current_player_hp - damage_monster)
    victory = new_monster_hp <= 0
    is_dead = False
    
    await db.update_player(player["user_id"], {"hp": new_player_hp})
    
    # ИСПРАВЛЕНО: При смерти корректно сбрасываем бой в Redis
    if new_player_hp <= 0:
        restore_hp = max(1, int(player.get("hp_max", 100) * 0.3))
        await db.update_player(player["user_id"], {"hp": restore_hp})
        is_dead = True
    
    await db.decrement_buffs(player["user_id"])
    
    result = {
        "player_dmg": damage_player,
        "monster_dmg": damage_monster,
        "is_crit_player": is_crit_player,
        "is_crit_monster": is_crit_monster,
        "monster_hp": new_monster_hp,
        "monster_max_hp": monster.get("hp", 100),
        "player_hp": restore_hp if is_dead else new_player_hp,
        "player_hp_max": player.get("hp_max", 100),
        "victory": victory,
        "is_dead": is_dead
    }
    
    if victory:
        reward = await process_victory(player["user_id"], player, monster)
        result["reward"] = reward
    elif not is_dead:
        new_mp = min(player.get("mp_max", 50), player.get("mp", 0) + 5)
        await db.update_player(player["user_id"], {"mp": new_mp})
    
    return result


async def process_skill_attack(
    user_id: int,
    player: dict,
    monster: dict,
    skill_id: str,
    current_player_hp: int,
    current_monster_hp: int,
    battle_id: str
) -> dict:
    """Обработка атаки навыком"""
    skill_result = await db.use_skill(user_id, skill_id, player.get("mp", 0))
    if not skill_result["success"]:
        raise HTTPException(400, skill_result["error"])
    
    buffs = await db.get_active_buffs(user_id)
    atk_mult = 1.0 + sum(b.get("attack_bonus_percent", 0) for b in buffs.values())
    def_mult = 1.0 + sum(b.get("defense_bonus_percent", 0) for b in buffs.values())
    eva_mult = 1.0 + sum(b.get("evasion_bonus_percent", 0) for b in buffs.values())
    crit_bonus_sum = sum(b.get("crit_bonus_percent", 0) for b in buffs.values())
    
    player_attack = int(player.get("attack", 20) * atk_mult)

    hits = skill_result.get("hits", 1)
    total_damage = 0

    for _ in range(hits):
        damage = int(player_attack * skill_result.get("multiplier", 1.5))
        damage = max(1, damage - (monster.get("defense", 0) // 2))

        is_crit = False
        player_crit_chance = 10 + (player.get("intuition", 0) * 0.3) + (crit_bonus_sum * 100)
        if random.randint(1, 100) <= player_crit_chance:
            is_crit = True
            crit_multiplier = player.get("crit_damage", 150) / 100
            damage = int(damage * crit_multiplier)

        hit_chance = max(60, 95 - monster.get("evasion", 5))
        if random.randint(1, 100) > hit_chance:
            damage = 0
            is_crit = False

        total_damage += damage

    if total_damage > 0:
        await update_quest_progress(user_id, "damage", total_damage)
    
    new_monster_hp = max(0, current_monster_hp - total_damage)
    victory = new_monster_hp <= 0
    
    monster_damage = 0
    new_player_hp = current_player_hp
    is_dead = False
    
    if not victory:
        monster_attack = monster.get("attack", 10)
        player_defense = int(player.get("defense", 15) * def_mult)
        monster_damage = max(1, monster_attack - (player_defense // 2))
        
        if random.randint(1, 100) <= 5: 
            monster_damage = int(monster_damage * 1.5)

        monster_hit_chance = max(30, 95 - int(player.get("evasion", 5) * eva_mult))
        if random.randint(1, 100) > monster_hit_chance:
            monster_damage = 0
        
        new_player_hp = max(0, current_player_hp - monster_damage)
    
    new_mp = player.get("mp", 0) - skill_result["mp_cost"]
    await db.update_player(user_id, {
        "mp": max(0, new_mp),
        "hp": new_player_hp
    })
    
    await db.decrement_buffs(user_id)
    
    if skill_result.get("type") == "buff":
        await db.add_buff(
            user_id, skill_id,
            skill_result.get("attack_bonus_percent", 0),
            skill_result.get("defense_bonus_percent", 0),
            skill_result.get("evasion_bonus_percent", 0),
            skill_result.get("crit_bonus_percent", 0),
            skill_result.get("reflect_percent", 0),
            skill_result.get("stun_chance", 0),
            skill_result.get("duration", 3)
        )
    
    # ИСПРАВЛЕНО: При смерти от монстра во время скилла тоже сбрасываем бой
    if new_player_hp <= 0:
        restore_hp = max(1, int(player.get("hp_max", 100) * 0.3))
        await db.update_player(user_id, {"hp": restore_hp})
        is_dead = True

    result = {
        "type": "damage",
        "damage": total_damage,
        "is_crit": False,
        "monster_damage": monster_damage,
        "skill_name": skill_result["name"],
        "mp_cost": skill_result["mp_cost"],
        "new_mp": max(0, new_mp),
        "monster_hp": new_monster_hp,
        "player_hp": restore_hp if is_dead else new_player_hp,
        "victory": victory,
        "is_dead": is_dead
    }
    
    if victory:
        reward = await process_victory(user_id, player, monster)
        result["reward"] = reward
    
    return result


async def process_victory(user_id: int, player: dict, monster: dict) -> dict:
    """Обработка победы над монстром"""
    await update_quest_progress(user_id, "kills", 1)

    fatigue = await db.get_farming_fatigue(user_id)

    exp_mult = 1.0
    aden_mult = 1.0
    if player.get("premium_until") and datetime.fromisoformat(player["premium_until"]) > datetime.now():
        exp_mult = 1.25
        aden_mult = 1.25

    exp_gain = int(monster.get("exp_reward", 10) * fatigue * exp_mult)
    aden_gain = int(monster.get("aden_reward", 5) * aden_mult)
    
    await db.update_achievement(user_id, "monster_hunter", 1)
    if monster.get("tier", 1) >= 4:
        await db.update_achievement(user_id, "elite_slayer", 1)
    if monster.get("tier", 1) >= 5:
        await db.update_achievement(user_id, "boss_killer", 1)
    
    exp_result = await db.add_exp(user_id, exp_gain, monster.get("level", 1), monster.get("tier", 1))

    fresh_player = await db.get_player(user_id)
    await db.update_player(user_id, {"aden": fresh_player.get("aden", 0) + aden_gain})
    await db.add_fight(user_id)
    
    await db.update_player(user_id, {
        "hp": fresh_player.get("hp_max", 100),
        "mp": fresh_player.get("mp_max", 50)
    })
    
    drops = await db.process_drop(user_id, monster)
    
    reward = {
        "exp": exp_gain,
        "aden": aden_gain,
        "fatigue": fatigue
    }
    
    if exp_result.get("level_up"):
        reward["level_up"] = True
        reward["new_level"] = exp_result.get("new_level")
    
    if drops:
        reward["drops"] = drops
    
    return reward


@router.post("/cancel")
async def cancel_battle(
    req: CancelBattleRequest,
    user_id: int = Depends(get_current_user)
):
    """Отмена текущего боя"""
    battle_state = await get_battle_state(req.battle_id)
    
    if not battle_state:
        raise HTTPException(404, "Battle not found")
    
    if battle_state.get("player_id") != user_id:
        raise HTTPException(403, "Not your battle")
    
    if battle_state.get("is_finished"):
        raise HTTPException(400, "Battle already finished")
    
    await finish_battle(req.battle_id)
    await redis_client.delete(f"user_battle:{user_id}")
    
    player = await db.get_player(user_id)
    if player:
        await db.update_player(user_id, {"hp": player.get("hp_max", 100)})
    
    return {"success": True, "message": "Battle cancelled"}


@router.post("/retreat")
async def retreat_from_battle(
    user_id: int = Depends(get_current_user)
):
    """Отступление из боя (с штрафом)"""
    battle_id = await redis_client.get(f"user_battle:{user_id}")
    battle_state = await get_battle_state(battle_id) if battle_id else None
    
    if not battle_state:
        raise HTTPException(404, "No active battle found")
    
    player = await db.get_player(user_id)
    if player:
        hp_loss = int(player.get("hp_max", 100) * 0.1)
        new_hp = max(1, player.get("hp", player.get("hp_max", 100)) - hp_loss)
        await db.update_player(user_id, {"hp": new_hp})
    
    await finish_battle(battle_id)
    await redis_client.delete(f"user_battle:{user_id}")
    
    return {
        "success": True,
        "message": "You retreated from battle",
        "hp_loss": int(player.get("hp_max", 100) * 0.1) if player else 0
    }


@router.post("/tutorial")
async def start_tutorial_battle(
    user_id: int = Depends(get_current_user)
):
    """Туториальный бой для новых игроков"""
    player = await db.get_player(user_id)
    if not player:
        raise HTTPException(404, "Player not found")

    monster = await db.get_monster_by_id(1)  # Крыса
    if not monster:
        raise HTTPException(404, "Tutorial monster not found")

    existing_battle_id = await redis_client.get(f"user_battle:{user_id}")
    if existing_battle_id:
        state = await get_battle_state(existing_battle_id)
        if state and not state.get("is_finished"):
            return {
                "success": False,
                "message": "You are already in a battle",
                "battle_id": existing_battle_id
            }

    battle_id = f"tutorial_{user_id}_{int(time.time())}"

    await create_battle_state(
        battle_id=battle_id,
        player_id=user_id,
        monster_id=1,
        monster_hp=monster["hp"]
    )
    await redis_client.set(f"user_battle:{user_id}", battle_id, expire=BATTLE_TTL_SECONDS)

    initial_nonce = generate_battle_nonce()

    return {
        "success": True,
        "battle_id": battle_id,
        "nonce": initial_nonce,
        "monster": {
            "id": monster["id"],
            "name": monster["name"],
            "hp": monster.get("hp", 100),
            "hp_max": monster.get("hp", 100),
            "attack": monster.get("attack", 10),
            "defense": monster.get("defense", 5),
            "evasion": monster.get("evasion", 5),
            "level": monster.get("level", 1),
            "exp_reward": monster.get("exp_reward", 10),
            "aden_reward": monster.get("aden_reward", 5)
        },
        "player": {
            "hp": player.get("hp", player.get("hp_max", 100)),
            "hp_max": player.get("hp_max", 100),
            "mp": player.get("mp", player.get("mp_max", 50)),
            "mp_max": player.get("mp_max", 50),
            "attack": player.get("attack", 20),
            "defense": player.get("defense", 15),
            "evasion": player.get("evasion", 5),
            "level": player.get("level", 1)
        },
        "message": "Туториальный бой начался! Попробуй атаковать."
    }


@router.post("/auto/start")
async def start_auto_battle(
    req: StartBattleRequest,
    user_id: int = Depends(get_current_user)
):
    """Запуск пассивного автобоя через AutoBattleService"""
    player = await db.get_player(user_id)
    if not player or player.get("energy", 0) < 10:
        raise HTTPException(400, "Need at least 10 energy to start auto-battle")

    return await AutoBattleService.start_auto_battle(user_id, req.monster_id)


@router.post("/auto/stop")
async def stop_auto_battle(
    user_id: int = Depends(get_current_user)
):
    """Остановка пассивного автобоя и получение накопленных наград"""
    return await AutoBattleService.stop_auto_battle(user_id)


@router.get("/auto/status")
async def get_auto_battle_status(
    user_id: int = Depends(get_current_user)
):
    """Получение статуса и накопленных наград автобоя"""
    return await AutoBattleService.get_auto_battle_status(user_id)
