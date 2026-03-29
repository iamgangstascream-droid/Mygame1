// ============================================
// LEGACY WAR - GAME CLIENT (FULL VERSION)
// Версия: 2.1 - Энергия, Рейд, Автообновление боя
// ============================================

const API_URL = 'https://sergeyscream1.pythonanywhere.com';
let userId = null;
let currentLanguage = 'ru';
let playerSettings = {};
let activeChat = 'world';
let matchmakingActive = false;
let matchmakingInterval = null;
let chatInterval = null;
let battlePollingInterval = null;
let currentBattle = {
    active: false,
    monsterId: null,
    monsterHp: 0,
    monsterMaxHp: 0,
    autoMode: false,
    battleLog: []
};

const translations = {
    ru: {
        welcome: '✨ Добро пожаловать в Legacy War! ✨',
        selectTab: 'Выберите вкладку внизу',
        errorNoUserId: 'Ошибка: не передан user_id',
        victory: 'Победа!',
        defeat: 'Поражение...',
        autoBattleOn: 'Автобой включен',
        autoBattleOff: 'Автобой выключен',
        searchOpponent: 'Поиск соперника...',
        opponentFound: 'Соперник найден!',
        battleStart: 'Начинаем бой...',
        cancelSearch: 'Поиск отменен',
        notEnoughMana: 'Недостаточно маны!',
        skillNotAvailable: 'Навык недоступен',
        itemEquipped: 'Предмет экипирован',
        itemUnequipped: 'Предмет снят',
        notEnoughItems: 'Недостаточно предметов',
        craftSuccess: 'Предмет создан!',
        craftFailed: 'Не удалось создать предмет',
        enhanceSuccess: 'Заточка успешна!',
        enhanceFailed: 'Заточка не удалась',
        itemDestroyed: 'Предмет уничтожен!',
        protectionSaved: 'Камень защиты спас предмет!',
        balanceTopup: 'Пополнение выполнено',
        balanceWithdraw: 'Вывод выполнен',
        insufficientBalance: 'Недостаточно средств',
        playerNotFound: 'Игрок не найден',
        battleEnd: 'Бой окончен',
        levelUp: 'Уровень повышен!',
        newMessage: 'Новое сообщение'
    },
    en: {
        welcome: '✨ Welcome to Legacy War! ✨',
        selectTab: 'Select a tab below',
        errorNoUserId: 'Error: user_id not provided',
        victory: 'Victory!',
        defeat: 'Defeat...',
        autoBattleOn: 'Auto-battle enabled',
        autoBattleOff: 'Auto-battle disabled',
        searchOpponent: 'Searching for opponent...',
        opponentFound: 'Opponent found!',
        battleStart: 'Starting battle...',
        cancelSearch: 'Search cancelled',
        notEnoughMana: 'Not enough mana!',
        skillNotAvailable: 'Skill not available',
        itemEquipped: 'Item equipped',
        itemUnequipped: 'Item unequipped',
        notEnoughItems: 'Not enough items',
        craftSuccess: 'Item crafted!',
        craftFailed: 'Failed to craft item',
        enhanceSuccess: 'Enhancement successful!',
        enhanceFailed: 'Enhancement failed',
        itemDestroyed: 'Item destroyed!',
        protectionSaved: 'Protection stone saved the item!',
        balanceTopup: 'Top-up completed',
        balanceWithdraw: 'Withdrawal completed',
        insufficientBalance: 'Insufficient balance',
        playerNotFound: 'Player not found',
        battleEnd: 'Battle ended',
        levelUp: 'Level up!',
        newMessage: 'New message'
    }
};

async function init() {
    const urlParams = new URLSearchParams(window.location.search);
    userId = urlParams.get('user_id');

    if(!userId) {
        document.getElementById('contentArea').innerHTML = getText('errorNoUserId');
        return;
    }

    await loadPlayerStats();
    await loadPlayerSettings();
    await loadPlayerSkills();
    startAutoRefresh();
    switchTab('combat');
    initAudio();
    restoreBattle();
    startBattlePolling();
    setInterval(loadEnergy, 60000);
}

function getText(key) {
    return translations[currentLanguage][key] || translations.ru[key] || key;
}

async function loadPlayerStats() {
    try {
        const response = await fetch(`${API_URL}/api/player/stats?user_id=${userId}`);
        const data = await response.json();

        if(data.error) {
            console.error('Error loading stats:', data.error);
            return null;
        }

        document.getElementById('playerName').innerText = data.name;
        document.getElementById('playerLevel').innerText = data.level;
        document.getElementById('adenAmount').innerText = data.aden || 0;
        document.getElementById('starsAmount').innerText = data.stars || 0;
        document.getElementById('tonAmount').innerText = data.ton || 0;
        if(document.getElementById('energyAmount')) {
            document.getElementById('energyAmount').innerText = data.energy || 20;
        }

        updateHealthBar(data.hp, data.hp_max);
        updateManaBar(data.mp, data.mp_max);
        updateExpBar(data.exp, data.exp_max);

        return data;
    } catch(e) {
        console.error('Error loading stats:', e);
        return null;
    }
}

async function loadPlayerSettings() {
    try {
        const response = await fetch(`${API_URL}/api/player/settings?user_id=${userId}`);
        playerSettings = await response.json();
        currentLanguage = playerSettings.language || 'ru';
        return playerSettings;
    } catch(e) {
        console.error('Error loading settings:', e);
        return {};
    }
}

async function loadPlayerSkills() {
    try {
        const response = await fetch(`${API_URL}/api/player/skills?user_id=${userId}`);
        const data = await response.json();
        return data.skills || [];
    } catch(e) {
        console.error('Error loading skills:', e);
        return [];
    }
}

async function loadInventory() {
    try {
        const response = await fetch(`${API_URL}/api/inventory?user_id=${userId}`);
        const data = await response.json();
        return data.inventory || [];
    } catch(e) {
        console.error('Error loading inventory:', e);
        return [];
    }
}

async function loadEquipment() {
    try {
        const response = await fetch(`${API_URL}/api/equipment?user_id=${userId}`);
        const data = await response.json();
        return data.equipment || {};
    } catch(e) {
        console.error('Error loading equipment:', e);
        return {};
    }
}

function updateHealthBar(current, max) {
    const percent = (current / max) * 100;
    document.getElementById('hpValue').innerText = `${current}/${max}`;
    document.getElementById('hpBar').style.width = `${percent}%`;
}

function updateManaBar(current, max) {
    const percent = (current / max) * 100;
    document.getElementById('mpValue').innerText = `${current}/${max}`;
    document.getElementById('mpBar').style.width = `${percent}%`;
}

function updateExpBar(current, max) {
    const percent = (current / max) * 100;
    document.getElementById('expValue').innerText = `${current}/${max}`;
    document.getElementById('expBar').style.width = `${percent}%`;
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toast.style.background = type === 'error' ? 'rgba(244, 67, 54, 0.9)' : 'rgba(0, 0, 0, 0.9)';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getGradeColor(grade) {
    const colors = {
        'D': '#808080',
        'C': '#00FF00',
        'B': '#0080FF',
        'A': '#FF00FF',
        'S': '#FFD700',
        'SS': '#FF0000'
    };
    return colors[grade] || '#FFFFFF';
}

function getEnhanceChance(level) {
    const chances = {0:100,1:90,2:80,3:70,4:60,5:50,6:40,7:30,8:20,9:10};
    return chances[level] || 50;
}

let audioEnabled = true;
let audioContext = null;

function initAudio() {
    if(playerSettings.sound_enabled) {
        audioEnabled = true;
    }
}

function playSound(type) {
    if(!audioEnabled) return;
    try {
        if(!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        switch(type) {
            case 'hit': oscillator.frequency.value = 440; gainNode.gain.value = 0.3; oscillator.type = 'sawtooth'; break;
            case 'heal': oscillator.frequency.value = 880; gainNode.gain.value = 0.2; oscillator.type = 'sine'; break;
            case 'levelup': oscillator.frequency.value = 523.25; gainNode.gain.value = 0.4; oscillator.type = 'triangle'; break;
            case 'click': oscillator.frequency.value = 220; gainNode.gain.value = 0.1; oscillator.type = 'square'; break;
            default: oscillator.frequency.value = 330; gainNode.gain.value = 0.2;
        }
        oscillator.start();
        gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.5);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch(e) {
        console.log('Audio not supported');
    }
}

function switchTab(tab) {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    const navItem = document.querySelector(`.nav-item[data-tab="${tab}"]`);
    if(navItem) navItem.classList.add('active');
    playSound('click');
    if(tab === 'combat') showCombatTab();
    else if(tab === 'inventory') showInventoryTab();
    else if(tab === 'skills') showSkillsTab();
    else if(tab === 'chat') showChatTab();
    else if(tab === 'trade') showTradeTab();
    else if(tab === 'clans') showClansTab();
}

function openModal(title, contentHtml) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalContent').innerHTML = contentHtml;
    document.getElementById('modalOverlay').classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeModalDirect() {
    document.getElementById('modalOverlay').classList.remove('open');
    document.body.style.overflow = '';
}

function closeModal(e) {
    if(e.target === document.getElementById('modalOverlay')) {
        closeModalDirect();
    }
}

// ========== ЭНЕРГИЯ ==========
async function loadEnergy() {
    try {
        const response = await fetch(`${API_URL}/api/energy?user_id=${userId}`);
        const data = await response.json();
        if(document.getElementById('energyAmount')) {
            document.getElementById('energyAmount').innerText = data.energy || 0;
        }
        return data;
    } catch(e) {
        console.error('Energy error:', e);
        return {energy: 20, max_energy: 20};
    }
}

async function showEnergyMenu() {
    const energy = await loadEnergy();
    openModal('⚡ Энергия', `
        <p style="font-size:32px;text-align:center">${energy.energy} / ${energy.max_energy}</p>
        <p>⚔️ Каждый бой тратит 1 энергию</p>
        <p>🔄 Восстанавливается: 1 ед. / 15 минут</p>
        <button class="action-btn" onclick="buyEnergy()">💎 Купить энергию (10 Stars)</button>
        <button class="action-btn" onclick="inviteForEnergy()">👥 Пригласить друга (+3 энергии)</button>
    `);
}

async function buyEnergy() {
    const response = await fetch(`${API_URL}/api/buy/energy`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: userId})
    });
    const data = await response.json();
    if (data.success) {
        showToast('Энергия восстановлена!');
        loadEnergy();
        closeModalDirect();
    } else {
        showToast(data.error, 'error');
    }
}

async function inviteForEnergy() {
    const response = await fetch(`${API_URL}/api/referral/link?user_id=${userId}`);
    const data = await response.json();
    const link = data.link || '';
    navigator.clipboard.writeText(link);
    showToast('Ссылка скопирована! Пригласи друга и получи +3 энергии');
}

// ========== АВТООБНОВЛЕНИЕ БОЯ ==========
async function startBattlePolling() {
    if (battlePollingInterval) clearInterval(battlePollingInterval);
    battlePollingInterval = setInterval(async () => {
        const response = await fetch(`${API_URL}/api/battle/state?user_id=${userId}`);
        const state = await response.json();
        if (state && state.active && state.monster_id) {
            if (document.getElementById('monsterHpValue')) {
                document.getElementById('monsterHpValue').innerText = state.monster_hp;
                document.getElementById('monsterHpFill').style.width = `${(state.monster_hp / state.monster_max_hp) * 100}%`;
            }
        }
    }, 2000);
}

async function restoreBattle() {
    const response = await fetch(`${API_URL}/api/battle/state?user_id=${userId}`);
    const state = await response.json();
    if (state && state.active) {
        showToast('Бой восстановлен!', 'success');
        startBattle(state.monster_id, 'Монстр', state.monster_max_hp, state.monster_hp);
    }
}

// ========== ВКЛАДКА БОЯ ==========
async function showCombatTab() {
    document.getElementById('contentArea').innerHTML = `
        <div style="display: flex; gap: 10px; margin-bottom: 15px;">
            <button class="action-btn" onclick="showMonsterList()">🐉 PVE</button>
            <button class="action-btn" onclick="showPVPMenu()">⚔️ PVP</button>
            <button class="action-btn" onclick="showRaidMenu()">👥 РЕЙД</button>
        </div>
        <div id="combatContent"></div>
    `;
    showMonsterList();
}

async function showMonsterList() {
    const player = await loadPlayerStats();
    const response = await fetch(`${API_URL}/api/monsters/list?user_id=${userId}`);
    const data = await response.json();

    let html = '<h3>🐉 Выбери монстра</h3>';
    html += '<div style="display: grid; grid-template-columns: repeat(2,1fr); gap: 10px;">';

    if(data.monsters && data.monsters.length > 0) {
        for(let monster of data.monsters) {
            html += `
                <div class="monster-card" onclick="startBattle(${monster.id}, '${monster.name}', ${monster.hp})">
                    <strong>${monster.name}</strong> (Ур. ${monster.level})
                    <div>❤️ ${monster.hp} HP</div>
                </div>
            `;
        }
    } else {
        html += '<p>Нет доступных монстров</p>';
    }

    html += '</div>';
    html += `
        <div style="margin-top: 20px; padding: 15px; background: rgba(255,215,0,0.1); border-radius: 15px;">
            <label style="display: flex; align-items: center; gap: 10px;">
                <input type="checkbox" id="autoBattleToggle" onchange="toggleAutoBattle()" ${playerSettings.auto_battle_pve ? 'checked' : ''}>
                <span>⚡ Автобой</span>
            </label>
        </div>
    `;

    document.getElementById('combatContent').innerHTML = html;
}

function toggleAutoBattle() {
    const toggle = document.getElementById('autoBattleToggle');
    currentBattle.autoMode = toggle.checked;
    showToast(getText(currentBattle.autoMode ? 'autoBattleOn' : 'autoBattleOff'));
}

async function startBattle(monsterId, monsterName, monsterHp, savedMonsterHp = null) {
    const energy = await loadEnergy();
    if (energy.energy < 1) {
        showToast('Недостаточно энергии! Пригласи друга или купи энергию', 'error');
        return;
    }

    currentBattle = {
        active: true,
        monsterId: monsterId,
        monsterHp: savedMonsterHp !== null ? savedMonsterHp : monsterHp,
        monsterMaxHp: monsterHp,
        autoMode: currentBattle.autoMode,
        battleLog: []
    };

    const player = await loadPlayerStats();

    document.getElementById('combatContent').innerHTML = `
        <div class="battle-fighters" style="display: flex; justify-content: space-between; margin-bottom: 20px;">
            <div class="fighter-card player" style="flex: 1; text-align: center; background: rgba(0,0,0,0.7); border-radius: 20px; padding: 15px;">
                <div class="fighter-avatar" style="font-size: 50px;">⚔️</div>
                <div class="fighter-name">${player.name}</div>
                <div class="fighter-hp-bar" style="background: rgba(255,255,255,0.2); height: 10px; border-radius: 5px; margin: 10px 0;">
                    <div class="fighter-hp-fill" id="playerHpFill" style="width: ${(player.hp/player.hp_max)*100}%; height: 100%; background: linear-gradient(90deg, #4caf50, #8bc34a); border-radius: 5px;"></div>
                </div>
                <div>❤️ <span id="playerHpValue">${player.hp}</span>/${player.hp_max}</div>
                <div>💙 <span id="playerMpValue">${player.mp}</span>/${player.mp_max}</div>
            </div>
            <div class="vs" style="display: flex; align-items: center; font-size: 30px; font-weight: bold; color: #ffd700;">VS</div>
            <div class="fighter-card opponent" style="flex: 1; text-align: center; background: rgba(0,0,0,0.7); border-radius: 20px; padding: 15px;">
                <div class="fighter-avatar" style="font-size: 50px;">👾</div>
                <div class="fighter-name">${monsterName}</div>
                <div class="fighter-hp-bar" style="background: rgba(255,255,255,0.2); height: 10px; border-radius: 5px; margin: 10px 0;">
                    <div class="fighter-hp-fill" id="monsterHpFill" style="width: 100%; height: 100%; background: linear-gradient(90deg, #f44336, #ff6b4a); border-radius: 5px;"></div>
                </div>
                <div>❤️ <span id="monsterHpValue">${currentBattle.monsterHp}</span>/${currentBattle.monsterMaxHp}</div>
            </div>
        </div>
        <div id="battleLog" class="battle-log" style="background: rgba(0,0,0,0.5); border-radius: 15px; padding: 15px; height: 200px; overflow-y: auto; font-size: 12px;"></div>
        <div id="battleActions" class="battle-actions" style="display: flex; gap: 10px; justify-content: center; margin-top: 20px;">
            <button class="action-btn" onclick="performBattleAction('attack')">⚔️ Атака</button>
            <button class="action-btn" onclick="showSkillsMenu()">✨ Навык</button>
        </div>
    `;

    if(currentBattle.autoMode) {
        document.getElementById('battleActions').innerHTML = '<div class="loader"></div><p style="text-align:center">Автобой активен...</p>';
        startAutoBattle();
    }
}

async function performBattleAction(action, skillId = null) {
    if(!currentBattle.active) return;

    const logDiv = document.getElementById('battleLog');
    logDiv.innerHTML += `<div>> ${action === 'attack' ? 'Наносим удар...' : 'Используем навык...'}</div>`;
    logDiv.scrollTop = logDiv.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/api/battle/turn`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: userId,
                monster_id: currentBattle.monsterId,
                action: action,
                skill_id: skillId,
                current_monster_hp: currentBattle.monsterHp
            })
        });
        const data = await response.json();

        if(data.error) {
            logDiv.innerHTML += `<div style="color: #f44336;">❌ ${data.error}</div>`;
            if(data.error.includes('энергии')) {
                currentBattle.active = false;
            }
            return;
        }

        currentBattle.monsterHp = data.monster_hp;
        currentBattle.battleLog.push(data.message);

        document.getElementById('monsterHpValue').innerText = data.monster_hp;
        document.getElementById('monsterHpFill').style.width = `${(data.monster_hp / data.monster_max_hp) * 100}%`;
        document.getElementById('playerHpValue').innerText = data.player_hp;
        document.getElementById('playerHpFill').style.width = `${(data.player_hp / data.player_hp_max) * 100}%`;
        document.getElementById('playerMpValue').innerText = data.player_mp;

        logDiv.innerHTML += `<div style="color: #4caf50;">✨ ${data.message}</div>`;
        logDiv.innerHTML += `<div style="color: #f44336;">💀 ${data.monster_message}</div>`;
        logDiv.scrollTop = logDiv.scrollHeight;

        playSound('hit');

        if(data.battle_end) {
            await endBattle(data.player_hp > 0);
        }
    } catch(e) {
        console.error('Battle error:', e);
        logDiv.innerHTML += `<div style="color: #f44336;">❌ Ошибка боя</div>`;
    }
}

async function endBattle(victory) {
    const response = await fetch(`${API_URL}/api/battle/end`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: userId, monster_id: currentBattle.monsterId, victory: victory})
    });
    const data = await response.json();

    const logDiv = document.getElementById('battleLog');
    if(data.victory) {
        logDiv.innerHTML += `<div style="color: #ffd700;">🎉 ${getText('victory')} +${data.exp_gained} опыта, +${data.aden_gained} Аден</div>`;
        if(data.level_up) {
            logDiv.innerHTML += `<div style="color: #ffd700;">✨ ${getText('levelUp')} ${data.new_level}!</div>`;
            playSound('levelup');
        }
        showToast(`${getText('victory')} +${data.exp_gained} опыта`);
    } else {
        logDiv.innerHTML += `<div style="color: #f44336;">💀 ${getText('defeat')}</div>`;
        showToast(getText('defeat'), 'error');
    }

    currentBattle.active = false;
    document.getElementById('battleActions').innerHTML = `<button class="action-btn" onclick="showCombatTab()">⚔️ НОВЫЙ БОЙ</button>`;
    await loadPlayerStats();
    await loadEnergy();
}

async function startAutoBattle() {
    while(currentBattle.active && currentBattle.autoMode) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        if(currentBattle.active) {
            await performBattleAction('attack');
        }
    }
}

async function showSkillsMenu() {
    const skills = await loadPlayerSkills();
    let skillsHtml = '<div style="display: grid; gap: 10px; margin-top: 10px;">';
    for(let skill of skills) {
        skillsHtml += `
            <button class="action-btn" onclick="performBattleAction('skill', '${skill.id}'); document.getElementById('skillsMenu').remove();">
                ✨ ${skill.name} (${skill.mp_cost} MP) - ${skill.description}
            </button>
        `;
    }
    skillsHtml += '<button class="action-btn action-btn-danger" onclick="document.getElementById(\'skillsMenu\').remove()">Отмена</button>';
    skillsHtml += '</div>';

    const menu = document.createElement('div');
    menu.id = 'skillsMenu';
    menu.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #1a1a2e; padding: 20px; border-radius: 20px; z-index: 2000; min-width: 300px; border: 2px solid #ffd700; max-height: 80vh; overflow-y: auto;';
    menu.innerHTML = `<h3>✨ Выбери навык</h3>${skillsHtml}`;
    document.body.appendChild(menu);
}

// ========== PVP С ТАЙМАУТОМ ==========
async function showPVPMenu() {
    document.getElementById('combatContent').innerHTML = `
        <div style="display: flex; gap: 10px; margin-bottom: 15px;">
            <button class="action-btn" onclick="startMatchmakingWithTimeout()">🎯 АВТОПОИСК (30 сек)</button>
            <button class="action-btn" onclick="showChallengeForm()">👤 ВЫЗВАТЬ</button>
        </div>
        <div id="pvpContent"></div>
    `;
    document.getElementById('pvpContent').innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <h3>⚔️ Поиск соперника</h3>
            <p>Диапазон уровней: ±3 | Таймаут: 30 секунд</p>
            <div id="matchmakingStatus"></div>
        </div>
    `;
}

async function startMatchmakingWithTimeout() {
    const timeout = 30;
    let secondsLeft = timeout;
    const statusDiv = document.getElementById('matchmakingStatus');
    
    const timer = setInterval(() => {
        secondsLeft--;
        if (statusDiv) {
            statusDiv.innerHTML = `<p>⏳ Поиск... ${secondsLeft} сек до таймаута</p><div class="loader"></div>`;
        }
        if (secondsLeft <= 0) {
            clearInterval(timer);
            cancelMatchmaking();
            showToast('Время поиска истекло', 'error');
        }
    }, 1000);
    
    try {
        const response = await fetch(`${API_URL}/api/pvp/queue`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_id: userId, auto_battle: false})
        });
        const data = await response.json();
        if(data.found) {
            clearInterval(timer);
            statusDiv.innerHTML = `<p>🎯 Соперник найден! Начинаем бой...</p>`;
            setTimeout(() => {
                openBattleWindow(data.battle_id, data.opponent_id);
            }, 2000);
        }
    } catch(e) {
        clearInterval(timer);
        showToast('Ошибка поиска', 'error');
    }
}

async function cancelMatchmaking() {
    await fetch(`${API_URL}/api/pvp/queue/leave`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: userId})
    });
    showToast(getText('cancelSearch'));
    showPVPMenu();
}

async function showChallengeForm() {
    document.getElementById('pvpContent').innerHTML = `
        <div style="padding: 20px;">
            <h3>👤 Вызов игрока</h3>
            <input type="text" id="playerNameInput" placeholder="Введите никнейм" style="width: 100%; padding: 12px; border-radius: 25px; margin: 10px 0; background: rgba(0,0,0,0.8); color: white; border: 1px solid #ffd700;">
            <input type="number" id="betAmountInput" placeholder="Ставка (Stars)" value="0" style="width: 100%; padding: 12px; border-radius: 25px; margin: 10px 0; background: rgba(0,0,0,0.8); color: white; border: 1px solid #ffd700;">
            <button class="action-btn" onclick="searchAndChallenge()">🔍 Найти и вызвать</button>
            <div id="searchResults" style="margin-top: 20px;"></div>
        </div>
    `;
}

async function searchAndChallenge() {
    const username = document.getElementById('playerNameInput').value;
    const betAmount = parseInt(document.getElementById('betAmountInput').value) || 0;
    if(!username) { showToast('Введите никнейм', 'error'); return; }
    const response = await fetch(`${API_URL}/api/player/search?username=${encodeURIComponent(username)}`);
    const data = await response.json();
    if(data.players && data.players.length > 0) {
        let html = '<h4>Найденные игроки:</h4>';
        for(let player of data.players) {
            if(player.user_id == userId) continue;
            html += `
                <div class="monster-card" style="margin: 10px 0; cursor: pointer;" onclick="challengePlayer(${player.user_id}, '${player.name}', ${betAmount})">
                    <strong>${player.name}</strong> (Ур. ${player.level}) - Рейтинг: ${player.rating}
                    <button class="action-btn" style="margin-top: 5px;">⚔️ Вызвать на бой</button>
                </div>
            `;
        }
        document.getElementById('searchResults').innerHTML = html;
    } else {
        document.getElementById('searchResults').innerHTML = '<p>❌ Игрок не найден</p>';
    }
}

async function challengePlayer(opponentId, opponentName, betAmount) {
    showToast(`Вызываем ${opponentName} на бой...`);
    try {
        const response = await fetch(`${API_URL}/api/pvp/challenge`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({attacker_id: userId, defender_id: opponentId, bet_amount: betAmount, bet_currency: 'stars'})
        });
        const data = await response.json();
        if(data.error) {
            showToast(data.error, 'error');
        } else {
            showToast(data.victory ? getText('victory') : getText('defeat'));
            await loadPlayerStats();
            showPVPMenu();
        }
    } catch(e) {
        showToast('Ошибка вызова', 'error');
    }
}

function openBattleWindow(battleId, opponentId) {
    const battleWindow = window.open('', '_blank', 'width=450,height=700');
    battleWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head><title>Legacy War - PvP Бой</title><meta charset="UTF-8">
        <style>
            *{margin:0;padding:0;box-sizing:border-box;}
            body{background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;font-family:monospace;min-height:100vh;padding:20px;}
            .fighter-card{background:rgba(0,0,0,0.7);border-radius:20px;padding:20px;text-align:center;margin:10px 0;border:2px solid #ffd700;}
            .fighter-card.player{border-color:#4caf50;}
            .fighter-card.opponent{border-color:#f44336;}
            .hp-bar{background:rgba(255,255,255,0.2);height:10px;border-radius:5px;overflow:hidden;margin:10px 0;}
            .hp-fill{background:linear-gradient(90deg,#4caf50,#8bc34a);height:100%;transition:width 0.3s;}
            .vs{text-align:center;font-size:24px;font-weight:bold;color:#ffd700;margin:10px 0;}
            .battle-log{background:rgba(0,0,0,0.7);border-radius:15px;padding:15px;height:200px;overflow-y:auto;font-size:12px;margin:20px 0;}
            .action-btn{background:linear-gradient(45deg,#ffd700,#ffb347);border:none;padding:12px 24px;border-radius:50px;color:#1a1a2e;font-weight:bold;cursor:pointer;margin:5px;}
            .timer{font-size:12px;color:#ffd700;text-align:center;margin:10px 0;}
        </style>
        </head>
        <body>
            <div style="max-width:500px;margin:0 auto">
                <div class="fighter-card player" id="playerCard">
                    <div id="playerName">Загрузка...</div>
                    <div class="hp-bar"><div class="hp-fill" id="playerHpFill" style="width:100%"></div></div>
                    <div>❤️ <span id="playerHp">0</span>/<span id="playerMaxHp">0</span></div>
                </div>
                <div class="vs">⚔️ VS ⚔️</div>
                <div class="fighter-card opponent" id="opponentCard">
                    <div id="opponentName">Загрузка...</div>
                    <div class="hp-bar"><div class="hp-fill" id="opponentHpFill" style="width:100%"></div></div>
                    <div>❤️ <span id="opponentHp">0</span>/<span id="opponentMaxHp">0</span></div>
                </div>
                <div class="timer" id="turnTimer">⏱️ Ход: 30 сек</div>
                <div id="battleLog" class="battle-log"></div>
                <div id="battleActions" class="battle-actions">
                    <button class="action-btn" onclick="sendAction('attack')">⚔️ Атака</button>
                </div>
            </div>
            <script>
                const API_URL = '${API_URL}';
                const userId = ${userId};
                const opponentId = ${opponentId};
                const battleId = '${battleId}';
                let battleActive = true;
                let turnTimeout = 30;
                let turnInterval;

                function startTurnTimer() {
                    if(turnInterval) clearInterval(turnInterval);
                    turnTimeout = 30;
                    turnInterval = setInterval(() => {
                        turnTimeout--;
                        document.getElementById('turnTimer').innerHTML = \`⏱️ Ход: \${turnTimeout} сек\`;
                        if(turnTimeout <= 0) {
                            clearInterval(turnInterval);
                            sendAction('attack');
                        }
                    }, 1000);
                }

                async function loadBattleState() {
                    const response = await fetch(\`\${API_URL}/api/battle/state?battle_id=\${battleId}&user_id=\${userId}\`);
                    const data = await response.json();
                    if(data.error) return;
                    document.getElementById('playerName').innerText = data.player_name;
                    document.getElementById('opponentName').innerText = data.opponent_name;
                    document.getElementById('playerHp').innerText = data.player_hp;
                    document.getElementById('playerMaxHp').innerText = data.player_max_hp;
                    document.getElementById('opponentHp').innerText = data.opponent_hp;
                    document.getElementById('opponentMaxHp').innerText = data.opponent_max_hp;
                    document.getElementById('playerHpFill').style.width = \${(data.player_hp / data.player_max_hp) * 100}%;
                    document.getElementById('opponentHpFill').style.width = \${(data.opponent_hp / data.opponent_max_hp) * 100}%;
                    if(data.battle_end) {
                        battleActive = false;
                        clearInterval(turnInterval);
                        document.getElementById('battleActions').innerHTML = '<button class="action-btn" onclick="window.close()">Закрыть</button>';
                    }
                    if(data.current_turn === userId) {
                        startTurnTimer();
                    } else {
                        if(turnInterval) clearInterval(turnInterval);
                        document.getElementById('turnTimer').innerHTML = '⏳ Ожидание хода соперника...';
                    }
                }

                async function sendAction(action) {
                    if(!battleActive) return;
                    const response = await fetch(\`\${API_URL}/api/battle/pvp_turn\`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({battle_id: battleId, user_id: userId, action: action})
                    });
                    const data = await response.json();
                    const logDiv = document.getElementById('battleLog');
                    logDiv.innerHTML += \`<div>> \${data.message}</div>\`;
                    logDiv.scrollTop = logDiv.scrollHeight;
                    await loadBattleState();
                }

                loadBattleState();
                setInterval(loadBattleState, 2000);
            </script>
        </body>
        </html>
    `);
}

// ========== РЕЙДОВЫЙ БОСС ==========
async function showRaidMenu() {
    document.getElementById('combatContent').innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <h3>👥 Рейдовый босс</h3>
            <div id="raidContent"></div>
        </div>
    `;
    showRaidStatus();
    if (window.raidInterval) clearInterval(window.raidInterval);
    window.raidInterval = setInterval(showRaidStatus, 10000);
}

async function showRaidStatus() {
    const response = await fetch(`${API_URL}/api/raid/status`);
    const raid = await response.json();
    if (!raid.active) {
        document.getElementById('raidContent').innerHTML = '<p>🤝 Рейдовый босс перерождается...</p><div class="loader"></div>';
        return;
    }
    let participantsHtml = '<h4>🏆 Топ урона:</h4>';
    (raid.participants || []).slice(0, 10).forEach((p, i) => {
        const medal = i === 0 ? '🥇' : (i === 1 ? '🥈' : (i === 2 ? '🥉' : `${i+1}.`));
        participantsHtml += `<div class="clan-member">${medal} ${p.name} — ${p.damage} урона</div>`;
    });
    document.getElementById('raidContent').innerHTML = `
        <div class="monster-card" style="text-align:center">
            <div style="font-size:48px">🐉</div>
            <h3>${raid.boss_name}</h3>
            <div class="fighter-hp-bar" style="margin:10px 0">
                <div class="fighter-hp-fill" style="width: ${(raid.boss_hp / raid.boss_max_hp) * 100}%; height:20px; background:linear-gradient(90deg,#f44336,#ff6b4a)"></div>
            </div>
            <div>❤️ ${raid.boss_hp} / ${raid.boss_max_hp} HP</div>
            <button class="action-btn" onclick="hitRaidBoss()">⚔️ Атаковать босса (10 урона)</button>
            ${participantsHtml}
        </div>
    `;
}

async function hitRaidBoss() {
    const response = await fetch(`${API_URL}/api/raid/hit`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: userId, damage: 10})
    });
    const data = await response.json();
    if (data.error) {
        showToast(data.error, 'error');
    } else if (data.raid_ended) {
        showToast('🏆 Рейдовый босс повержен!', 'success');
        let rewardsMsg = '🎁 Награды:\n';
        data.rewards.forEach(r => { rewardsMsg += `${r.name}: ${r.reward} Аден\n`; });
        alert(rewardsMsg);
        showRaidStatus();
    } else {
        showToast(`Вы нанесли ${data.damage} урона! Осталось ${data.boss_hp} HP`, 'success');
        showRaidStatus();
    }
}

// ========== ОСТАЛЬНЫЕ ВКЛАДКИ (сокращённо, без изменений) ==========
async function showInventoryTab() {
    document.getElementById('contentArea').innerHTML = `
        <div class="grid-2">
            <div class="menu-card" onclick="showInventoryList()"><div class="menu-icon">📦</div><div>ИНВЕНТАРЬ</div></div>
            <div class="menu-card" onclick="showEquipmentList()"><div class="menu-icon">👕</div><div>ЭКИПИРОВКА</div></div>
            <div class="menu-card" onclick="showCraftList()"><div class="menu-icon">🔨</div><div>КРАФТ</div></div>
            <div class="menu-card" onclick="showEnhanceList()"><div class="menu-icon">✨</div><div>ЗАТОЧКА</div></div>
            <div class="menu-card" onclick="showProfile()"><div class="menu-icon">👤</div><div>ПРОФИЛЬ</div></div>
        </div>
        <div id="invContent" class="battle-log" style="margin-top:15px;">Выберите раздел</div>
    `;
}

async function showInventoryList() {
    const inventory = await loadInventory();
    let items = '';
    if(inventory.length > 0) {
        for(let item of inventory) {
            const gradeColor = getGradeColor(item.grade);
            items += `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid rgba(255,215,0,0.3);">
                    <div><span style="color: ${gradeColor};">${item.name}</span> ${item.enhance_level > 0 ? `[+${item.enhance_level}]` : ''} x${item.quantity} ${item.equipped ? '<span style="color:#4caf50;"> [E]</span>' : ''}</div>
                    <div>${item.slot && !item.equipped ? `<button class="action-btn" style="padding:5px 10px;font-size:11px;" onclick="equipItem('${item.id}')">👕 Надеть</button>` : ''}${item.equipped ? `<button class="action-btn" style="padding:5px 10px;font-size:11px;" onclick="unequipItem('${item.slot}')">❌ Снять</button>` : ''}</div>
                </div>
            `;
        }
    } else { items = '<p>📭 Инвентарь пуст</p>'; }
    document.getElementById('invContent').innerHTML = `<h3>📦 Инвентарь</h3>${items}`;
}

async function showEquipmentList() {
    const equipment = await loadEquipment();
    const inventory = await loadInventory();
    const slots = ['weapon', 'chest', 'helmet', 'gloves', 'boots', 'belt', 'ring', 'amulet'];
    const slotNames = {'weapon':'Оружие','chest':'Нагрудник','helmet':'Шлем','gloves':'Перчатки','boots':'Ботинки','belt':'Пояс','ring':'Кольцо','amulet':'Амулет'};
    let html = '<h3>👕 Экипировка</h3>';
    for(let slot of slots) {
        const itemId = equipment[slot];
        let itemName = 'Пусто', gradeColor = '#888';
        if(itemId) {
            const item = inventory.find(i => i.id === itemId);
            if(item) { itemName = `${item.name}${equipment[`${slot}_enhance`] > 0 ? ` [+${equipment[`${slot}_enhance`]}]` : ''}`; gradeColor = getGradeColor(item.grade); }
        }
        html += `<div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid rgba(255,215,0,0.3);"><span><strong>${slotNames[slot]}:</strong> <span style="color: ${gradeColor};">${itemName}</span></span>${itemId ? `<button class="action-btn" style="padding:5px 10px;font-size:11px;" onclick="unequipItem('${slot}')">Снять</button>` : ''}</div>`;
    }
    document.getElementById('invContent').innerHTML = html;
}

async function equipItem(itemId) {
    const response = await fetch(`${API_URL}/api/equip`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId,item_id:itemId})});
    const result = await response.json();
    if(result.success) { showToast(getText('itemEquipped')); playSound('click'); showInventoryList(); await loadPlayerStats(); }
    else { showToast(result.error, 'error'); }
}

async function unequipItem(slot) {
    const response = await fetch(`${API_URL}/api/unequip`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId,slot:slot})});
    const result = await response.json();
    if(result.success) { showToast(getText('itemUnequipped')); playSound('click'); showEquipmentList(); await loadPlayerStats(); }
    else { showToast(result.error, 'error'); }
}

async function showCraftList() {
    const response = await fetch(`${API_URL}/api/craftable?user_id=${userId}`);
    const data = await response.json();
    let items = '';
    if(data.craftable && data.craftable.length > 0) {
        for(let item of data.craftable) {
            const gradeColor = getGradeColor(item.grade);
            items += `<div style="padding:10px;border-bottom:1px solid rgba(255,215,0,0.3);"><p>${item.can_craft ? '✅' : '❌'} <strong style="color:${gradeColor};">${item.name}</strong> (${item.craft_cost} аден)</p><p style="font-size:11px;">Рецепт: ${item.recipe}</p>${item.can_craft ? `<button class="action-btn" style="padding:5px 10px;font-size:11px;" onclick="craftItem('${item.id}')">🔨 Создать</button>` : `<span style="color:#f44336;">Не хватает: ${item.missing.join(', ')}</span>`}</div>`;
        }
    } else { items = '<p>🔨 Нет доступных рецептов</p>'; }
    document.getElementById('invContent').innerHTML = `<h3>🔨 Крафт</h3>${items}<div id="craftResult"></div>`;
}

async function craftItem(itemId) {
    const response = await fetch(`${API_URL}/api/craft`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId,item_id:itemId,quantity:1})});
    const data = await response.json();
    if(data.success) { showToast(getText('craftSuccess')); playSound('click'); showCraftList(); await loadPlayerStats(); }
    else { showToast(data.error || getText('craftFailed'), 'error'); }
}

async function showEnhanceList() {
    const inventory = await loadInventory();
    const player = await loadPlayerStats();
    let items = '';
    const costs = [500,1000,2000,4000,8000,15000,30000,60000,120000,200000];
    for(let item of inventory) {
        if(item.type === 'weapon' || item.type === 'armor') {
            const cost = costs[item.enhance_level] || 10000;
            const chance = getEnhanceChance(item.enhance_level);
            const gradeColor = getGradeColor(item.grade);
            items += `<div style="display:flex;justify-content:space-between;align-items:center;padding:10px;border-bottom:1px solid rgba(255,215,0,0.3);"><div><strong style="color:${gradeColor};">${item.name}</strong> [+${item.enhance_level}]<div style="font-size:11px;">Шанс: ${chance}% | Стоимость: ${cost} аден</div></div><div><button class="action-btn" style="padding:5px 10px;font-size:11px;" onclick="enhanceItem('${item.id}', false)" ${player.aden < cost ? 'disabled' : ''}>✨ Заточить</button><button class="action-btn" style="padding:5px 10px;font-size:11px;" onclick="enhanceItem('${item.id}', true)" ${player.aden < cost ? 'disabled' : ''}>🛡️ С защитой</button></div></div>`;
        }
    }
    if(!items) items = '<p>🔨 Нет предметов для заточки</p>';
    document.getElementById('invContent').innerHTML = `<h3>✨ Заточка предметов</h3>${items}<div id="enhanceResult"></div>`;
}

async function enhanceItem(itemId, useProtection) {
    const response = await fetch(`${API_URL}/api/enhance`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId,item_id:itemId,use_protection:useProtection})});
    const data = await response.json();
    if(data.success !== undefined) {
        if(data.success) { showToast(getText('enhanceSuccess')); playSound('levelup'); }
        else if(data.destroyed) { showToast(getText('itemDestroyed'), 'error'); }
        else { showToast(getText('enhanceFailed'), 'error'); }
        showEnhanceList();
        await loadPlayerStats();
    } else { showToast(data.error, 'error'); }
}

async function showProfile() {
    const player = await loadPlayerStats();
    if(!player) return;
    document.getElementById('invContent').innerHTML = `<h3>👤 Профиль</h3><div class="setting-group"><p><strong>👤 Имя:</strong> ${player.name}</p><p><strong>🎭 Класс:</strong> ${player.class}</p><p><strong>✨ Уровень:</strong> ${player.level}</p><p><strong>🏆 Рейтинг PvP:</strong> ${player.rating}</p><p><strong>⚔️ Побед в PvP:</strong> ${player.pvp_wins}</p><p><strong>💀 Поражений в PvP:</strong> ${player.pvp_losses}</p><p><strong>❤️ HP:</strong> ${player.hp}/${player.hp_max}</p><p><strong>💙 MP:</strong> ${player.mp}/${player.mp_max}</p><p><strong>⭐ Опыт:</strong> ${player.exp}/${player.exp_max}</p><p><strong>💰 Аден:</strong> ${player.aden}</p><p><strong>⭐ Stars:</strong> ${player.stars}</p><p><strong>💎 TON:</strong> ${player.ton || 0}</p></div>`;
}

async function showSkillsTab() {
    const skills = await loadPlayerSkills();
    const player = await loadPlayerStats();
    let html = '<h3>✨ Доступные навыки</h3>';
    for(let skill of skills) {
        const available = player.level >= skill.level_req;
        html += `<div class="setting-group" style="${!available ? 'opacity:0.5;' : ''}"><h4>${skill.name}</h4><p>${skill.description}</p><p>📊 Урон: ${skill.damage_mult}x | 💙 MP: ${skill.mp_cost}</p><p>📈 Требуемый уровень: ${skill.level_req}</p>${!available ? '<span style="color:#f44336;">🔒 Недоступен</span>' : '<span style="color:#4caf50;">✅ Доступен</span>'}</div>`;
    }
    document.getElementById('contentArea').innerHTML = html;
}

async function showChatTab() {
    document.getElementById('contentArea').innerHTML = `<div class="chat-container"><div class="chat-tabs"><button class="chat-tab ${activeChat === 'world' ? 'active' : ''}" onclick="switchChat('world')">🌍 Мировой</button><button class="chat-tab ${activeChat === 'clan' ? 'active' : ''}" onclick="switchChat('clan')">🏰 Клановый</button><button class="chat-tab ${activeChat === 'private' ? 'active' : ''}" onclick="switchChat('private')">💬 Личный</button></div><div id="chatMessages" class="chat-messages"></div><div class="chat-input"><input type="text" id="chatInput" placeholder="Введите сообщение..." onkeypress="handleChatKeypress(event)"><button onclick="sendChatMessage()">📤</button></div></div>`;
    await loadChatMessages();
    if(chatInterval) clearInterval(chatInterval);
    chatInterval = setInterval(loadChatMessages, 3000);
}

async function loadChatMessages() {
    try {
        const response = await fetch(`${API_URL}/api/chat/messages?user_id=${userId}&chat_type=${activeChat}&limit=50`);
        const data = await response.json();
        const messagesDiv = document.getElementById('chatMessages');
        if(messagesDiv) {
            messagesDiv.innerHTML = (data.messages || []).map(msg => `<div class="chat-message"><strong>${escapeHtml(msg.username)}</strong>: ${escapeHtml(msg.message)}<span class="time">${new Date(msg.created_at).toLocaleTimeString()}</span></div>`).join('');
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    } catch(e) { console.error('Error loading messages:', e); }
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if(!message) return;
    try {
        await fetch(`${API_URL}/api/chat/send`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId,chat_type:activeChat,message:message})});
        input.value = '';
        await loadChatMessages();
        playSound('click');
    } catch(e) { console.error('Error sending message:', e); }
}

function switchChat(type) { activeChat = type; showChatTab(); }
function handleChatKeypress(event) { if(event.key === 'Enter') sendChatMessage(); }

async function showTradeTab() {
    document.getElementById('contentArea').innerHTML = `<div class="grid-2"><div class="menu-card" onclick="showShopList()"><div class="menu-icon">🛒</div><div>МАГАЗИН</div></div><div class="menu-card" onclick="showMarketList()"><div class="menu-icon">📈</div><div>МАРКЕТ</div></div><div class="menu-card" onclick="showReferralList()"><div class="menu-icon">👥</div><div>РЕФЕРАЛЫ</div></div></div><div id="tradeContent" class="battle-log" style="margin-top:15px;">Выберите раздел</div>`;
}

async function showShopList() {
    const response = await fetch(`${API_URL}/api/shop`);
    const data = await response.json();
    let items = '';
    for(let item of data.shop) {
        const gradeColor = getGradeColor(item.grade);
        items += `<div style="display:flex;justify-content:space-between;align-items:center;padding:10px;border-bottom:1px solid rgba(255,215,0,0.3);"><div><strong style="color:${gradeColor};">${item.name}</strong> (${item.grade || 'D'})<div style="font-size:11px;">${item.description}</div><div style="font-size:10px;">Треб. уровень: ${item.level_req}</div></div><div><span>💰 ${item.value} аден</span><button class="action-btn" style="padding:5px 10px;font-size:11px;" onclick="buyItem('${item.id}')">Купить</button></div></div>`;
    }
    document.getElementById('tradeContent').innerHTML = `<h3>🛒 Магазин</h3>${items}<div id="shopResult"></div>`;
}

async function buyItem(itemId) {
    const player = await loadPlayerStats();
    const response = await fetch(`${API_URL}/api/shop`);
    const data = await response.json();
    const item = data.shop.find(i => i.id === itemId);
    if(!item) { showToast('Предмет не найден', 'error'); return; }
    if(player.aden < item.value) { showToast(getText('insufficientBalance'), 'error'); return; }
    const buyRes = await fetch(`${API_URL}/api/buy`, {method:'POST',body:JSON.stringify({user_id:userId,item_id:itemId,quantity:1})});
    const result = await buyRes.json();
    if(result.success) { showToast(`Куплен ${result.item}! Новый баланс: ${result.new_balance} аден`); playSound('click'); await loadPlayerStats(); showShopList(); }
    else { showToast(result.error, 'error'); }
}

async function showMarketList() {
    const response = await fetch(`${API_URL}/api/market/listings`);
    const data = await response.json();
    let items = '';
    for(let listing of data.listings) {
        const gradeColor = listing.grade_color || '#ffd700';
        items += `<div style="display:flex;justify-content:space-between;align-items:center;padding:10px;border-bottom:1px solid rgba(255,215,0,0.3);"><div><strong style="color:${gradeColor};">${listing.item_name}</strong>${listing.enhance_level > 0 ? `<span style="color:#ffd700;">[+${listing.enhance_level}]</span>` : ''}<div style="font-size:11px;">x${listing.quantity} | Продавец: ${listing.seller_name}</div></div><div><span>💰 ${listing.price} ${listing.currency}</span><button class="action-btn" style="padding:5px 10px;font-size:11px;" onclick="buyFromMarket(${listing.id})">Купить</button></div></div>`;
    }
    document.getElementById('tradeContent').innerHTML = `<h3>📈 Маркет</h3>${items || '<p>Нет активных лотов</p>'}<div id="marketResult"></div>`;
}

async function buyFromMarket(listingId) {
    const response = await fetch(`${API_URL}/api/market/buy`, {method:'POST',body:JSON.stringify({buyer_id:userId,listing_id:listingId})});
    const data = await response.json();
    if(data.success) { showToast(`Куплено! Комиссия: ${data.commission} ${data.currency}`); playSound('click'); await loadPlayerStats(); showMarketList(); }
    else { showToast(data.error, 'error'); }
}

async function showReferralList() {
    const linkResponse = await fetch(`${API_URL}/api/referral/link?user_id=${userId}`);
    const linkData = await linkResponse.json();
    const statsResponse = await fetch(`${API_URL}/api/referral/stats?user_id=${userId}`);
    const stats = await statsResponse.json();
    document.getElementById('tradeContent').innerHTML = `<h3>👥 Реферальная система</h3><p>🔗 Ваша ссылка:</p><div style="display:flex;gap:10px;margin:10px 0;"><input type="text" id="referralLink" value="${linkData.link || ''}" readonly style="flex:1;padding:10px;border-radius:20px;background:rgba(0,0,0,0.8);color:white;border:1px solid #ffd700;"><button class="action-btn" onclick="copyReferralLink()">📋 Копировать</button></div><p>📊 Статистика:</p><p>• Рефералы 1 уровня: ${stats.level1 || 0}</p><p>• Рефералы 2 уровня: ${stats.level2 || 0}</p><p>• Рефералы 3 уровня: ${stats.level3 || 0}</p><p>💰 Заработано: ${stats.total_earned || 0} Аден</p><p style="font-size:12px;margin-top:15px;">✨ Бонусы: 1 ур. - 500 Аден, 2 ур. - 200 Аден, 3 ур. - 100 Аден</p>`;
}

function copyReferralLink() { const linkInput = document.getElementById('referralLink'); if(linkInput) { linkInput.select(); document.execCommand('copy'); showToast('Ссылка скопирована!'); } }

async function showClansTab() {
    document.getElementById('contentArea').innerHTML = `<div style="display:flex;gap:10px;margin-bottom:15px;flex-wrap:wrap"><button class="action-btn" onclick="showClanLeaderboard()">🏆 Топ кланов</button><button class="action-btn" onclick="showMyClan()">🛡️ Мой клан</button><button class="action-btn" onclick="showCreateClan()">➕ Создать клан</button></div><div id="clansContent"><div style="text-align:center;padding:30px;color:#ffd700">Загрузка...</div></div>`;
    showClanLeaderboard();
}

async function showClanLeaderboard() {
    document.getElementById('clansContent').innerHTML = '<div style="text-align:center;padding:20px">⏳ Загрузка...</div>';
    try {
        const r = await fetch(`${API_URL}/api/clan/leaderboard`);
        const data = await r.json();
        const clans = data.clans || [];
        let html = '<h3 style="color:#ffd700;margin-bottom:12px">🏆 Топ кланов</h3>';
        if(clans.length === 0) html += '<p style="color:#aaa;text-align:center;padding:20px">Кланов пока нет. Будь первым!</p>';
        else {
            const medals = ['🥇','🥈','🥉'];
            clans.forEach((clan, i) => { html += `<div class="clan-card" onclick="showClanDetail(${clan.id})"><div style="display:flex;justify-content:space-between;align-items:center"><div><span style="font-size:18px">${medals[i] || `#${i+1}`}</span><strong style="color:#ffd700;margin-left:8px">${clan.name}</strong></div><span style="color:#aaa;font-size:12px">Ур.${clan.level}</span></div><div style="font-size:12px;color:#aaa;margin-top:4px">👥 ${clan.member_count || 0} участников · ⚔️ ${clan.wins || 0} побед</div></div>`; });
        }
        document.getElementById('clansContent').innerHTML = html;
    } catch(e) { document.getElementById('clansContent').innerHTML = '<p style="color:#f44336">Ошибка загрузки кланов</p>'; }
}

async function showMyClan() {
    document.getElementById('clansContent').innerHTML = '<div style="text-align:center;padding:20px">⏳ Загрузка...</div>';
    try {
        const r = await fetch(`${API_URL}/api/clan/info?user_id=${userId}`);
        const data = await r.json();
        if(!data.clan) { document.getElementById('clansContent').innerHTML = `<div style="text-align:center;padding:30px"><div style="font-size:48px;margin-bottom:12px">🛡️</div><p style="color:#ffd700;font-size:16px;margin-bottom:8px">Вы не в клане</p><p style="color:#aaa;font-size:13px">Вступите в существующий клан или создайте свой</p><button class="action-btn" style="margin-top:16px" onclick="showClanLeaderboard()">Посмотреть кланы</button></div>`; return; }
        const clan = data.clan;
        let html = `<div style="background:rgba(255,215,0,0.1);border-radius:12px;padding:16px;margin-bottom:12px"><h3 style="color:#ffd700;font-size:20px">🛡️ ${clan.name}</h3><div style="font-size:13px;color:#aaa;margin-top:6px">Уровень ${clan.level} · ${clan.member_count} участников</div><div style="font-size:13px;color:#aaa">⚔️ Побед: ${clan.wins || 0} · Поражений: ${clan.losses || 0}</div></div><h4 style="color:#ffd700;margin-bottom:8px">👥 Участники</h4>`;
        (clan.members || []).forEach(m => { html += `<div class="clan-member"><span>${m.name}</span><span style="color:#ffd700">Ур.${m.level} · ⭐${m.rating}</span></div>`; });
        html += `<button class="modal-action-btn btn-red" style="margin-top:16px" onclick="leaveClan()">🚪 Покинуть клан</button>`;
        document.getElementById('clansContent').innerHTML = html;
    } catch(e) { document.getElementById('clansContent').innerHTML = '<p style="color:#f44336">Ошибка загрузки</p>'; }
}

async function showClanDetail(clanId) {
    try {
        const r = await fetch(`${API_URL}/api/clan/info?user_id=${userId}&clan_id=${clanId}`);
        const data = await r.json();
        if(!data.clan) { showToast('Клан не найден'); return; }
        const clan = data.clan;
        let html = `<div style="background:rgba(255,215,0,0.08);border-radius:12px;padding:14px;margin-bottom:14px"><div style="font-size:13px;color:#aaa">Уровень ${clan.level} · Участников: ${clan.member_count}</div><div style="font-size:13px;color:#aaa">⚔️ Побед: ${clan.wins || 0}</div></div><h4 style="color:#ffd700;margin-bottom:8px">👥 Участники (${(clan.members||[]).length})</h4>`;
        (clan.members || []).slice(0,10).forEach(m => { html += `<div class="clan-member"><span>${m.name}</span><span style="color:#ffd700">Ур.${m.level}</span></div>`; });
        html += `<button class="modal-action-btn btn-gold" onclick="joinClan(${clanId});closeModalDirect()">⚔️ Вступить в клан</button>`;
        openModal(`🛡️ ${clan.name}`, html);
    } catch(e) { showToast('Ошибка загрузки клана'); }
}

function showCreateClan() {
    openModal('➕ Создать клан', `<p style="color:#aaa;font-size:13px;margin-bottom:16px">Создание клана стоит <strong style="color:#ffd700">5000 Аден</strong>.</p><input id="clanNameInput" placeholder="Название клана (3-20 символов)" style="width:100%;padding:12px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,215,0,0.3);border-radius:10px;color:#fff;font-size:15px;outline:none;margin-bottom:12px"><button class="modal-action-btn btn-gold" onclick="createClan()">⚔️ Создать за 5000 Аден</button>`);
    setTimeout(() => document.getElementById('clanNameInput')?.focus(), 100);
}

async function createClan() {
    const name = (document.getElementById('clanNameInput')?.value || '').trim();
    if(!name) { showToast('Введите название клана!'); return; }
    try {
        const r = await fetch(`${API_URL}/api/clan/create`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId, name})});
        const data = await r.json();
        if(data.error) { showToast('❌ ' + data.error); return; }
        showToast('✅ ' + data.message);
        closeModalDirect();
        showMyClan();
        loadPlayerStats();
    } catch(e) { showToast('Ошибка создания клана'); }
}

async function joinClan(clanId) {
    try {
        const r = await fetch(`${API_URL}/api/clan/join`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId, clan_id:clanId})});
        const data = await r.json();
        if(data.error) { showToast('❌ ' + data.error); return; }
        showToast('✅ ' + data.message);
        showMyClan();
    } catch(e) { showToast('Ошибка вступления в клан'); }
}

async function leaveClan() {
    if(!confirm('Покинуть клан?')) return;
    try {
        const r = await fetch(`${API_URL}/api/clan/leave`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId})});
        const data = await r.json();
        if(data.error) { showToast('❌ ' + data.error); return; }
        showToast('✅ ' + data.message);
        showClansTab();
    } catch(e) { showToast('Ошибка'); }
}

async function showSettings() {
    const settings = await loadPlayerSettings();
    document.getElementById('contentArea').innerHTML = `<div class="settings-window"><h3>⚙️ Настройки</h3><div class="setting-group"><h4>🔊 Звук</h4><label><input type="checkbox" id="soundToggle" ${settings.sound_enabled ? 'checked' : ''}> Включить звук</label></div><div class="setting-group"><h4>🌐 Язык</h4><select id="languageSelect"><option value="ru" ${settings.language === 'ru' ? 'selected' : ''}>Русский</option><option value="en" ${settings.language === 'en' ? 'selected' : ''}>English</option></select></div><button class="action-btn" onclick="saveSettings()">💾 Сохранить</button></div>`;
}

async function saveSettings() {
    const settings = { sound_enabled: document.getElementById('soundToggle')?.checked ? 1 : 0, language: document.getElementById('languageSelect')?.value || 'ru' };
    const response = await fetch(`${API_URL}/api/player/settings?user_id=${userId}`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)});
    const result = await response.json();
    if(result.success) { showToast('Настройки сохранены!'); await loadPlayerSettings(); initAudio(); }
}

async function showBalanceMenu() {
    const player = await loadPlayerStats();
    document.getElementById('contentArea').innerHTML = `<div class="balance-menu"><h3>💰 Баланс</h3><div class="setting-group"><h4>💰 Аден</h4><p style="font-size:24px;color:#ffd700;">${player.aden || 0}</p><button class="action-btn" onclick="showTopUp('aden')">Пополнить</button></div><div class="setting-group"><h4>⭐ Stars</h4><p style="font-size:24px;color:#ff6b9d;">${player.stars || 0}</p><button class="action-btn" onclick="showTopUp('stars')">Пополнить</button><button class="action-btn action-btn-danger" onclick="showWithdraw('stars')">Вывести</button></div><div class="setting-group"><h4>💎 TON</h4><p style="font-size:24px;color:#0088cc;">${player.ton || 0}</p><button class="action-btn" onclick="showTopUp('ton')">Пополнить</button><button class="action-btn action-btn-danger" onclick="showWithdraw('ton')">Вывести</button></div></div>`;
}

async function showTopUp(currency) {
    const amount = prompt(`Введите сумму для пополнения ${currency.toUpperCase()}:`, '100');
    if(amount && !isNaN(amount) && parseInt(amount) > 0) {
        const response = await fetch(`${API_URL}/api/player/topup`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId, currency:currency, amount:parseInt(amount)})});
        const result = await response.json();
        if(result.success) { showToast(`${getText('balanceTopup')} ${amount} ${currency.toUpperCase()}! Новый баланс: ${result.new_balance}`); playSound('click'); await loadPlayerStats(); showBalanceMenu(); }
        else { showToast(result.error || getText('insufficientBalance'), 'error'); }
    }
}

async function showWithdraw(currency) {
    const amount = prompt(`Введите сумму для вывода ${currency.toUpperCase()}:`, '100');
    if(amount && !isNaN(amount) && parseInt(amount) > 0) {
        const response = await fetch(`${API_URL}/api/player/withdraw`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId, currency:currency, amount:parseInt(amount)})});
        const result = await response.json();
        if(result.success) { showToast(`${getText('balanceWithdraw')} ${amount} ${currency.toUpperCase()}! Новый баланс: ${result.new_balance}`); playSound('click'); await loadPlayerStats(); showBalanceMenu(); }
        else { showToast(result.error || getText('insufficientBalance'), 'error'); }
    }
}

function startAutoRefresh() { setInterval(async () => { await loadPlayerStats(); }, 10000); }

// Глобальные экспорты
window.init = init;
window.switchTab = switchTab;
window.showCombatTab = showCombatTab;
window.showMonsterList = showMonsterList;
window.startBattle = startBattle;
window.performBattleAction = performBattleAction;
window.showSkillsMenu = showSkillsMenu;
window.toggleAutoBattle = toggleAutoBattle;
window.showPVPMenu = showPVPMenu;
window.startMatchmakingWithTimeout = startMatchmakingWithTimeout;
window.cancelMatchmaking = cancelMatchmaking;
window.showChallengeForm = showChallengeForm;
window.searchAndChallenge = searchAndChallenge;
window.challengePlayer = challengePlayer;
window.showRaidMenu = showRaidMenu;
window.showRaidStatus = showRaidStatus;
window.hitRaidBoss = hitRaidBoss;
window.showInventoryTab = showInventoryTab;
window.showInventoryList = showInventoryList;
window.showEquipmentList = showEquipmentList;
window.equipItem = equipItem;
window.unequipItem = unequipItem;
window.showCraftList = showCraftList;
window.craftItem = craftItem;
window.showEnhanceList = showEnhanceList;
window.enhanceItem = enhanceItem;
window.showProfile = showProfile;
window.showSkillsTab = showSkillsTab;
window.showChatTab = showChatTab;
window.switchChat = switchChat;
window.sendChatMessage = sendChatMessage;
window.handleChatKeypress = handleChatKeypress;
window.showTradeTab = showTradeTab;
window.showShopList = showShopList;
window.buyItem = buyItem;
window.showMarketList = showMarketList;
window.buyFromMarket = buyFromMarket;
window.showReferralList = showReferralList;
window.copyReferralLink = copyReferralLink;
window.showClansTab = showClansTab;
window.showClanLeaderboard = showClanLeaderboard;
window.showMyClan = showMyClan;
window.showClanDetail = showClanDetail;
window.showCreateClan = showCreateClan;
window.createClan = createClan;
window.joinClan = joinClan;
window.leaveClan = leaveClan;
window.showSettings = showSettings;
window.saveSettings = saveSettings;
window.showBalanceMenu = showBalanceMenu;
window.showTopUp = showTopUp;
window.showWithdraw = showWithdraw;
window.showEnergyMenu = showEnergyMenu;
window.buyEnergy = buyEnergy;
window.inviteForEnergy = inviteForEnergy;
window.openModal = openModal;
window.closeModal = closeModal;
window.closeModalDirect = closeModalDirect;

document.addEventListener('DOMContentLoaded', init);