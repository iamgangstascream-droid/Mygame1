import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN", "8231782270:AAGGnJ-zC5pWl71bQxaf3allLW_dqoWqsiw")
API_URL = "https://sergeyscream1.pythonanywhere.com"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню бота"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="⚔️ Играть",
            web_app=WebAppInfo(url=f"{API_URL}/?user_id={user_id}")
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="stats"
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="👥 Рефералы",
            callback_data="referral"
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="🏆 Кланы",
            callback_data="clans"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 Магазин",
            callback_data="shop"
        ),
        InlineKeyboardButton(
            text="📈 Топ рейтинга",
            callback_data="top"
        )
    )
    return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start с поддержкой реферальных ссылок"""
    args = message.text.split()
    referrer_code = None
    
    # Проверяем реферальный код в формате /start ref_XXXXX
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_code = args[1][4:]  # Убираем "ref_"
        logger.info(f"Referral code detected: {referrer_code}")
    
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Создаём или получаем игрока через API
    async with aiohttp.ClientSession() as session:
        # Проверяем, есть ли игрок
        async with session.get(f"{API_URL}/api/player/stats?user_id={user_id}") as resp:
            if resp.status == 404:
                # Игрок не найден — создаём нового
                logger.info(f"Creating new player for user {user_id} with referrer {referrer_code}")
                async with session.post(f"{API_URL}/api/player", 
                    json={"user_id": user_id, "name": username, "class": "warrior", "ref_code": referrer_code}) as create_resp:
                    if create_resp.status == 200:
                        logger.info(f"New player created: {user_id}")
                        
                        # Если есть реферальный код, отправляем уведомление рефереру
                        if referrer_code:
                            # Ищем реферера по коду
                            async with session.get(f"{API_URL}/api/player?referral_code={referrer_code}") as ref_resp:
                                if ref_resp.status == 200:
                                    ref_data = await ref_resp.json()
                                    referrer_id = ref_data.get('user_id')
                                    if referrer_id:
                                        try:
                                            await bot.send_message(
                                                referrer_id,
                                                f"🎉 По вашей реферальной ссылке зарегистрировался новый игрок!\n"
                                                f"Вы получили бонус: 500 Аден!"
                                            )
                                            logger.info(f"Referral bonus sent to {referrer_id}")
                                        except Exception as e:
                                            logger.error(f"Failed to send referral notification: {e}")
                    else:
                        logger.error(f"Failed to create player: {create_resp.status}")
            elif resp.status == 200:
                player = await resp.json()
                logger.info(f"Existing player: {user_id}, level {player.get('level', 1)}")
            else:
                logger.error(f"Error checking player: {resp.status}")
    
    welcome_text = (
        "⚔️ *Legacy War* — эпическая RPG в Telegram!\n\n"
        "🌍 Мир погружён в вечную войну между тёмными силами и последними бастионами света.\n"
        "Тебе предстоит стать легендой этих земель!\n\n"
        "✨ *Особенности:*\n"
        "• 4 уникальных класса персонажей\n"
        "• PvE сражения с монстрами\n"
        "• PvP Арена с рейтингом\n"
        "• Крафт и заточка предметов\n"
        "• Кланы и рейды\n"
        "• Реферальная система с бонусами\n\n"
        "Нажми кнопку *Играть*, чтобы начать своё приключение!"
    )
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id)
    )


@dp.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    """Показать статистику игрока"""
    user_id = callback.from_user.id
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/api/player/stats?user_id={user_id}") as resp:
            if resp.status == 200:
                player = await resp.json()
                
                # Получаем инвентарь
                async with session.get(f"{API_URL}/api/inventory?user_id={user_id}") as inv_resp:
                    inventory = await inv_resp.json() if inv_resp.status == 200 else {"inventory": []}
                
                stats_text = (
                    f"📊 *Статистика персонажа*\n\n"
                    f"👤 Имя: {player.get('name', 'Hero')}\n"
                    f"🎭 Класс: {player.get('class', 'warrior')}\n"
                    f"✨ Уровень: {player.get('level', 1)}\n"
                    f"🏆 Рейтинг: {player.get('rating', 1000)}\n"
                    f"⚔️ PvP побед: {player.get('pvp_wins', 0)}\n"
                    f"💀 PvP поражений: {player.get('pvp_losses', 0)}\n"
                    f"💰 Аден: {player.get('aден', 0)}\n"
                    f"⭐ Stars: {player.get('stars', 0)}\n"
                    f"❤️ HP: {player.get('hp', 100)}/{player.get('hp_max', 100)}\n"
                    f"💙 MP: {player.get('mp', 50)}/{player.get('mp_max', 50)}\n"
                    f"📦 Предметов: {len(inventory.get('inventory', []))}\n"
                )
                
                await callback.message.edit_text(
                    stats_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
                    ])
                )
            else:
                await callback.answer("Ошибка загрузки статистики", show_alert=True)
    
    await callback.answer()


@dp.callback_query(F.data == "referral")
async def show_referral(callback: types.CallbackQuery):
    """Показать реферальную информацию"""
    user_id = callback.from_user.id
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/api/referral/link?user_id={user_id}") as link_resp:
            if link_resp.status == 200:
                link_data = await link_resp.json()
                referral_link = link_data.get('link', '')
                
                async with session.get(f"{API_URL}/api/referral/stats?user_id={user_id}") as stats_resp:
                    stats = await stats_resp.json() if stats_resp.status == 200 else {}
                
                text = (
                    "👥 *Реферальная система*\n\n"
                    f"🔗 Ваша ссылка:\n`{referral_link}`\n\n"
                    "💰 *Бонусы:*\n"
                    "• Уровень 1 (прямые): 500 Аден\n"
                    "• Уровень 2: 200 Аден\n"
                    "• Уровень 3: 100 Аден\n\n"
                    f"📊 *Ваша статистика:*\n"
                    f"• Рефералы 1 уровня: {stats.get('level1', 0)}\n"
                    f"• Рефералы 2 уровня: {stats.get('level2', 0)}\n"
                    f"• Рефералы 3 уровня: {stats.get('level3', 0)}\n"
                    f"• Всего заработано: {stats.get('total_earned', 0)} Аден"
                )
                
                await callback.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={referral_link}&text=Присоединяйся к Legacy War!")],
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
                    ])
                )
            else:
                await callback.answer("Ошибка загрузки реферальной ссылки", show_alert=True)
    
    await callback.answer()


@dp.callback_query(F.data == "clans")
async def show_clans(callback: types.CallbackQuery):
    """Показать информацию о кланах"""
    user_id = callback.from_user.id
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/api/clan/leaderboard") as leaderboard_resp:
            if leaderboard_resp.status == 200:
                data = await leaderboard_resp.json()
                clans = data.get('clans', [])
                
                if clans:
                    text = "🏆 *Топ кланов*\n\n"
                    for i, clan in enumerate(clans[:10], 1):
                        text += f"{i}. {clan['name']} (Ур. {clan['level']}) - {clan.get('member_count', 0)} участников\n"
                else:
                    text = "🏆 *Кланы*\n\nПока нет ни одного клана. Создай свой!"
                
                await callback.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
                    ])
                )
            else:
                await callback.answer("Ошибка загрузки кланов", show_alert=True)
    
    await callback.answer()


@dp.callback_query(F.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    """Показать магазин"""
    user_id = callback.from_user.id
    
    text = (
        "💰 *Магазин*\n\n"
        "🛒 *Обычный магазин (за Аден):*\n"
        "• Зелья, оружие, броня\n"
        "• Доступно в игре\n\n"
        "✨ *Премиум магазин (за Stars):*\n"
        "• Камни защиты (10 Stars)\n"
        "• Ускорители (20 Stars)\n"
        "• Скины персонажей (300 Stars)\n\n"
        "Нажми *Играть*, чтобы открыть полный магазин в игре!"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Играть", web_app=WebAppInfo(url=f"{API_URL}/?user_id={user_id}"))],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "top")
async def show_top(callback: types.CallbackQuery):
    """Показать топ рейтинга"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/api/rating/top") as resp:
            if resp.status == 200:
                data = await resp.json()
                top = data.get('top', [])
                
                text = "🏆 *Топ PvP рейтинга*\n\n"
                for i, player in enumerate(top[:10], 1):
                    text += f"{i}. {player['name']} — {player['rating']} рейтинга\n"
                
                await callback.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
                    ])
                )
            else:
                await callback.answer("Ошибка загрузки топа", show_alert=True)
    
    await callback.answer()


@dp.callback_query(F.data == "back")
async def back_to_menu(callback: types.CallbackQuery):
    """Вернуться в главное меню"""
    user_id = callback.from_user.id
    
    welcome_text = (
        "⚔️ *Legacy War* — главное меню\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id)
    )
    await callback.answer()


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 *Команды бота:*\n\n"
        "/start — начать игру\n"
        "/help — помощь\n\n"
        "Используй кнопки для навигации!",
        parse_mode="Markdown"
    )


async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())