Telegram.WebApp.ready();
Telegram.WebApp.expand();
Telegram.WebApp.requestFullscreen();

const user = Telegram.WebApp.initDataUnsafe.user || { id: 'anon' };
const storage = Telegram.WebApp.CloudStorage;
const botUsername = Telegram.WebApp.initDataUnsafe.bot_username || 'GrokTappersBot';

const TAP_VALUE_BASE = 1;
const BOOST_COST = 100;
const LEVEL_UP_THRESHOLD = 1000;
const DAILY_REWARD = 100;
const REFERRAL_BONUS = 50;
const DAILY_COOLDOWN = 86400000; 
const MIN_TAP_INTERVAL = 50; 

let coins = 0;
let level = 1;
let autoRate = 0;
let lastDaily = 0;
let lastTapTime = 0;
let tapValue = TAP_VALUE_BASE;

const coinsEl = document.getElementById('coins');
const levelEl = document.getElementById('level');
const autoRateEl = document.getElementById('auto-rate');
const tapArea = document.getElementById('tap-area');
const boostButton = document.getElementById('boost-button');
const dailyButton = document.getElementById('daily-reward');
const inviteButton = document.getElementById('invite-button');
const shareButton = document.getElementById('share-progress');
const leaderboardButton = document.getElementById('leaderboard-button');
const progressBar = document.getElementById('progress-bar');

function updateUI() {
    coinsEl.textContent = Math.floor(coins);
    levelEl.textContent = level;
    autoRateEl.textContent = autoRate;
    const progress = (coins % LEVEL_UP_THRESHOLD) / LEVEL_UP_THRESHOLD * 100;
    progressBar.style.width = `${progress}%`;
    dailyButton.disabled = (Date.now() - lastDaily < DAILY_COOLDOWN);
    dailyButton.textContent = dailyButton.disabled ? `Ежедневка через ${Math.floor((DAILY_COOLDOWN - (Date.now() - lastDaily)) / 3600000)} ч` : `Ежедневка (+${DAILY_REWARD})`;
}

function saveProgress() {
    const data = JSON.stringify({ coins, level, autoRate, lastDaily });
    storage.setItem('game_data', data, (err) => {
        if (err) console.error('Save error:', err);
    });
}

function checkLevelUp() {
    while (coins >= level * LEVEL_UP_THRESHOLD) {
        coins -= level * LEVEL_UP_THRESHOLD;
        level++;
        tapValue = TAP_VALUE_BASE + (level - 1);
        Telegram.WebApp.showAlert(`Уровень ${level}! Тап +${tapValue}`);
        saveProgress();
    }
}

storage.getItem('game_data', (err, data) => {
    if (data) {
        try {
            const parsed = JSON.parse(data);
            coins = parsed.coins || 0;
            level = parsed.level || 1;
            autoRate = parsed.autoRate || 0;
            lastDaily = parsed.lastDaily || 0;
            tapValue = TAP_VALUE_BASE + (level - 1);
        } catch (e) {
            console.error('Load error:', e);
        }
    }
    updateUI();
});

tapArea.addEventListener('touchstart', (e) => {
    e.preventDefault();
    if (Date.now() - lastTapTime < MIN_TAP_INTERVAL) return;
    lastTapTime = Date.now();
    coins += tapValue;
    checkLevelUp();
    updateUI();
    saveProgress();
    Telegram.WebApp.HapticFeedback.impactOccurred('heavy');
});

boostButton.addEventListener('click', () => {
    if (coins >= BOOST_COST) {
        coins -= BOOST_COST;
        autoRate += 1;
        updateUI();
        saveProgress();
        Telegram.WebApp.showAlert('+1 монета/сек!');
    } else {
        Telegram.WebApp.showAlert('Мало монет!');
    }
});

setInterval(() => {
    coins += autoRate;
    checkLevelUp();
    updateUI();
    saveProgress();
}, 1000);

dailyButton.addEventListener('click', () => {
    if (!dailyButton.disabled) {
        coins += DAILY_REWARD;
        lastDaily = Date.now();
        updateUI();
        saveProgress();
        Telegram.WebApp.showAlert(`+${DAILY_REWARD} монет!`);
    }
});

const initData = Telegram.WebApp.initDataUnsafe;
if (initData.start_param && initData.start_param.startsWith('ref_')) {
    const refId = initData.start_param.split('_')[1];
    coins += REFERRAL_BONUS;
    updateUI();
    saveProgress();
    Telegram.WebApp.showAlert(`Бонус +${REFERRAL_BONUS}`);
}

inviteButton.addEventListener('click', () => {
    const shareUrl = `https://t.me/share/url?url=https://t.me/${botUsername}?startapp=ref_${user.id}&text=Майни в Grok Tappers!`;
    Telegram.WebApp.openTelegramLink(shareUrl);
});

shareButton.addEventListener('click', () => {
    Telegram.WebApp.shareToStory(`https://t.me/${botUsername}?startapp`, {
        text: `В Grok Tappers ${Math.floor(coins)} монет, ур. ${level}!`
    });
});

leaderboardButton.addEventListener('click', () => {
    storage.setItem('high_score', coins.toString(), () => {
        storage.getItem('high_score', (err, score) => {
            Telegram.WebApp.showPopup({
                title: 'Лидерборд',
                message: `Твой: ${score || 0}\nГлоб: (бэкенд для 100k)`,
                buttons: [{ text: 'OK' }]
            });
        });
    });
});
