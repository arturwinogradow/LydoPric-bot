from telegram.error import Forbidden
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply, ReplyKeyboardRemove
from typing import List, Tuple
import random
import logging
import signal
import sys
import json
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from flask import Flask
import threading

# Простой веб-сервер для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

# Запускаем веб-сервер в отдельном потоке
web_thread = threading.Thread(target=run_web)
web_thread.daemon = True
web_thread.start()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация бота
import os
TOKEN = os.environ.get('BOT_TOKEN', '7899973479:AAFTh9so7sIZC3pfaNRp1PJRybUYDFdMphs')
# Состояния для администратора
ADMIN_PASSWORD = "201014"

application = ApplicationBuilder().token(TOKEN).build()

# Словарь для хранения монет пользователей
user_coins = {}
# Словарь для хранения истории последних игр пользователей
user_history = {}
# Словарь для хранения информации о пользователях
user_profiles = {}
# Словарь для хранения временных меток последних ежедневных выплат
daily_bonus_times = {}
# Словарь для хранения использованных промокодов
used_promocodes = set()
# Словарь для хранения информации о покупках пользователей
user_purchases = {}

user_autoclicker_rates = {}

def load_data():
    global user_coins, user_history, user_profiles, daily_bonus_times, used_promocodes, user_purchases, user_autoclicker_rates
    try:
        import os
        file_path = os.path.join(os.path.dirname(__file__), 'data.json')
        with open(file_path, 'r') as f:
            data = json.load(f)
            user_coins = data.get('user_coins', {})
            user_history = data.get('user_history', {})
            user_profiles = data.get('user_profiles', {})
            daily_bonus_times = data.get('daily_bonus_times', {})
            used_promocodes = set(data.get('used_promocodes', []))
            user_purchases = data.get('user_purchases', {})
            user_autoclicker_rates = data.get('user_autoclicker_rates', {})
            logger.info("Данные успешно загружены из файла.")
    except FileNotFoundError:
        logger.info("Файл данных не найден. Инициализирую пустые данные.")
        # Инициализируем пустые данные
        user_coins = {}
        user_history = {}
        user_profiles = {}
        daily_bonus_times = {}
        used_promocodes = set()
        user_purchases = {}
        user_autoclicker_rates = {}
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных: {e}")
        # Инициализируем пустые данные при любой ошибке
        user_coins = {}
        user_history = {}
        user_profiles = {}
        daily_bonus_times = {}
        used_promocodes = set()
        user_purchases = {}
        user_autoclicker_rates = {}


# Загружаем данные при запуске бота
load_data()

# Символы и их веса для выигрышей в слотах
slot_symbols = {
    '🍒': 100,  # 3 черешни
    '🍇': 50,  # 3 винограда
    '🍊': 30,  # 3 апельсина
    '🔔': 20,  # 3 колокольчика
    '🍀': 500  # 3 четырёхлистника
}

# Добавляем карты для игры в дурака
deck = ['6♠', '7♠', '8♠', '9♠', '10♠', 'J♠', 'Q♠', 'K♠', 'A♠',
        '6♣', '7♣', '8♣', '9♣', '10♣', 'J♣', 'Q♣', 'K♣', 'A♣',
        '6♥', '7♥', '8♥', '9♥', '10♥', 'J♥', 'Q♥', 'K♥', 'A♥',
        '6♦', '7♦', '8♦', '9♦', '10♦', 'J♦', 'Q♦', 'K♦', 'A♦']

# Комбинации символов и их выигрыши в слотах
combinations = {
    ('🍒', '🍒', '🍒'): 100,
    ('🍇', '🍇', '🍇'): 50,
    ('🍊', '🍊', '🍊'): 30,
    ('🔔', '🔔', '🔔'): 20,
    ('🍀', '🍀', '🍀'): 500,
    ('🍒', '🍒'): 10,
    ('🍇', '🍇'): 10,
    ('🍊', '🍊'): 10,
    ('🔔', '🔔'): 10,
    ('🍀', '🍀'): 10
}

# Коэффициенты выигрышей в рулетке
roulette_odds = {
    10: 10,
    20: 5,
    30: 3.33,
    40: 2.5,
    50: 2,
    60: 1.67,
    70: 1.43
}


def save_data():
    data = {
        'user_coins': user_coins,
        'user_history': user_history,
        'user_profiles': user_profiles,
        'daily_bonus_times': daily_bonus_times,
        'used_promocodes': list(used_promocodes),
        'user_purchases': user_purchases,
        'user_autoclicker_rates': user_autoclicker_rates
    }
    import os
    file_path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(file_path, 'w') as f:
        json.dump(data, f)
    logger.info("Данные успешно сохранены в файл.")

# Функция для обработки завершения работы бота
def shutdown(signal, frame):
    logger.info("Завершение работы бота. Сохранение данных...")
    save_data()
    logger.info("Данные сохранены. До свидания!")
    sys.exit(0)

# Регистрируем обработчик сигнала завершения работы
signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# Загружаем данные при запуске бота
load_data()

# Обновляем функцию create_game_selection_keyboard для добавления новой кнопки
def create_game_selection_keyboard():
    keyboard = [
        [KeyboardButton("Игра в слоты")],
        [KeyboardButton("Игра в рулетку")],
        [KeyboardButton("Выбор"), KeyboardButton("Кейсы")],
        [KeyboardButton("Показать баланс"), KeyboardButton("Показать профиль")],
        [KeyboardButton("История игр"), KeyboardButton("Топ игроков")],
        [KeyboardButton("Использовать промокод"), KeyboardButton("Получить ежедневную выплату")],
        [KeyboardButton("Поделиться монетами"), KeyboardButton("Правила")],
        [KeyboardButton("Связаться с администратором")],
        [KeyboardButton("Магазин")],  # Добавляем кнопку "Магазин"
        [KeyboardButton("Вывод")],  # Добавляем кнопку "Вывод"

    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Функция для создания клавиатуры управления ставками в слотах
def create_slot_control_keyboard():
    keyboard = [
        [KeyboardButton("Играть в слоты")],
        [KeyboardButton("Бесплатная игра")],
        [KeyboardButton("Увеличить ставку"), KeyboardButton("Уменьшить ставку")],
        [KeyboardButton("Ввести ставку")],
        [KeyboardButton("Назад к выбору игры")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

save_data()  # Сохраняем данные после инициализации пользователя

# Функция для создания клавиатуры управления ставками в рулетке
def create_roulette_control_keyboard():
    keyboard = [
        [KeyboardButton("Ввести ставку и выбрать % апгрейда")],
        [KeyboardButton("Назад к выбору игры")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Функция для создания клавиатуры выбора % апгрейда в рулетке
def create_roulette_odds_keyboard():
    keyboard = [
        [KeyboardButton("10%"), KeyboardButton("20%")],
        [KeyboardButton("30%"), KeyboardButton("40%")],
        [KeyboardButton("50%"), KeyboardButton("60%")],
        [KeyboardButton("70%"), KeyboardButton("Назад к управлению ставками")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Функция для обработки ошибок Forbidden
async def handle_forbidden_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning(f"Bot was forbidden to send a message to {update.effective_chat.id}. Bot might have been removed from the group.")
    # Добавляем ID чата в список заблокированных чатов
    blocked_chats.add(update.effective_chat.id)

# Объявляем множество для хранения заблокированных чатов
blocked_chats = set()

# Функция для отправки сообщения с проверкой блокировки чата
async def safe_send_message(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE):
    if chat_id in blocked_chats:
        logger.info(f"Skipping sending message to blocked chat {chat_id}.")
        return
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
    except Forbidden:
        logger.warning(f"Bot was forbidden to send a message to {chat_id}. Bot might have been removed from the group.")
        blocked_chats.add(chat_id)

# Регистрируем обработчик для ошибок Forbidden
application.add_error_handler(handle_forbidden_error)

# Объявляем множество для хранения заблокированных чатов
blocked_chats = set()

# Регистрируем обработчик для ошибок Forbidden
application.add_error_handler(handle_forbidden_error)

# Функция для обработки запросов, когда бот выключен
async def bot_is_offline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ой! На данный момент бот находится в выключенном состоянии, подождите немного!")

# Функция для обработки всех запросов после завершения работы бота
async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bot_is_offline(update, context)



# Функция для начала игры
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    if user_id not in user_coins:
        user_coins[user_id] = 100  # Начальное количество монет
        user_history[user_id] = []  # История игр
        user_profiles[user_id] = {
            'name': user_name,
            'games_played': 0,
            'total_winnings': 0,
            'promocode_used': False
        }
        daily_bonus_times[user_id] = 0  # Время последней ежедневной выплаты
        save_data()  # Сохраняем данные после инициализации пользователя
    context.user_data['bet'] = 10  # Начальная ставка
    context.user_data['game_mode'] = None  # Начальный режим игры
    await update.message.reply_text(
        f"Добро пожаловать в казино, {user_name}! Ваш Telegram ID: {user_id}. У вас {user_coins[user_id]} монет.",
        reply_markup=create_game_selection_keyboard())

# Функция для выбора игры в слоты
async def select_slot_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return

    context.user_data['game_mode'] = 'slots'
    await update.message.reply_text("Вы выбрали игру в слоты.", reply_markup=create_slot_control_keyboard())


# Функция для выбора игры в рулетку
async def select_roulette_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return

    context.user_data['game_mode'] = 'roulette'
    await update.message.reply_text("Вы выбрали игру в рулетку.", reply_markup=create_roulette_control_keyboard())


async def play_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return
    bet = context.user_data.get('bet', 10)  # Получаем текущую ставку
    if user_coins[user_id] < bet:
        await update.message.reply_text(f"У вас недостаточно монет для ставки. У вас {user_coins[user_id]} монет.",
                                        reply_markup=create_slot_control_keyboard())
        return
    user_coins[user_id] -= bet  # Вычитаем ставку из баланса
    user_profiles[user_id]['games_played'] += 1
    # Симулируем выпадение слотов
    symbols = list(slot_symbols.keys())
    result = tuple(random.choice(symbols) for _ in range(3))
    message = f"Выпали слоты: {' '.join(result)}\n"  # Добавлен перенос строки

    # Определяем выигрыш
    winnings = 0
    if result in combinations:
        winnings = combinations[result]
    elif any(result[i] == result[j] for i in range(len(result)) for j in range(i + 1, len(result))):
        winnings = bet * 2
    user_coins[user_id] += winnings
    user_profiles[user_id]['total_winnings'] += winnings
    # Сохраняем результат игры в историю
    user_history[user_id].append({
        'result': result,
        'bet': bet,
        'winnings': winnings,
        'game_mode': 'slots'
    })
    message += f"Вы выиграли {winnings} монет!\n"  # Добавлен перенос строки
    message += f"Теперь у вас {user_coins[user_id]} монет."
    await update.message.reply_text(message, reply_markup=create_slot_control_keyboard())
    save_data()  # Сохраняем данные после каждой игры (строка 248)

# Функция для начала игры "Выбор"
async def choice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.", reply_markup=create_game_selection_keyboard())
        return
    await update.message.reply_text("Введите сумму, которую вы хотите поставить:", reply_markup=ForceReply(selective=True))
    context.user_data['awaiting_choice_bet'] = True


# Функция для выполнения игры "Выбор"
async def play_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    bet = context.user_data.get('choice_bet', 10)

    # Проверяем, достаточно ли монет для ставки
    if user_coins[user_id] < bet:
        await update.message.reply_text(
            f"У вас недостаточно монет для ставки {bet}. У вас {user_coins[user_id]} монет.",
            reply_markup=create_game_selection_keyboard())
        context.user_data.pop('choice_buttons', None)  # Очищаем данные после игры
        context.user_data.pop('choice_bet', None)  # Очищаем данные после игры
        context.user_data['game_mode'] = None  # Возвращаемся к выбору игры
        return

    user_coins[user_id] -= bet  # Вычитаем ставку из баланса
    user_profiles[user_id]['games_played'] += 1

    # Создаем три случайные кнопки с знаками вопроса
    buttons = ['❓', '❓', '❓']
    random.shuffle(buttons)
    keyboard = [
        [KeyboardButton(buttons[0]), KeyboardButton(buttons[1]), KeyboardButton(buttons[2])]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"Вы поставили {bet} монет. Выберите одну из кнопок:", reply_markup=reply_markup)
    context.user_data['choice_buttons'] = buttons
    context.user_data['choice_bet'] = bet


# Функция для выполнения игры "Выбор"
async def handle_choice_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    button_text = update.message.text.strip()
    if not context.user_data.get('choice_buttons', False):
        return
    buttons = context.user_data['choice_buttons']
    bet = context.user_data['choice_bet']
    if button_text not in buttons:
        await update.message.reply_text("Пожалуйста, выберите одну из предложенных кнопок.", reply_markup=create_game_selection_keyboard())
        return
    # Генерируем случайное число для определения выигрыша
    win_chance = random.randint(1, 100)
    winnings = 0
    if win_chance <= 33:  # 33% шанс на удвоение
        winnings = bet * 2  # Выигрыш равен удвоенной ставке
    # Иначе winnings остается 0, что означает, что ставка не сжигается
    user_coins[user_id] += winnings
    user_profiles[user_id]['total_winnings'] += winnings
    # Сохраняем результат игры в историю
    user_history[user_id].append({
        'result': button_text,
        'bet': bet,
        'winnings': winnings,
        'game_mode': 'choice'
    })
    message = f"Вы выбрали: {button_text}\n"  # Добавлен перенос строки
    if winnings > 0:
        message += f"Вы выиграли {winnings} монет!\n"  # Добавлен перенос строки
    else:
        message += "Вы не выиграли.\n"  # Добавлен перенос строки
    message += f"Теперь у вас {user_coins[user_id]} монет."
    await update.message.reply_text(message, reply_markup=create_game_selection_keyboard())
    context.user_data.pop('choice_buttons', None)  # Очищаем данные после игры
    context.user_data.pop('choice_bet', None)  # Очищаем данные после игры
    context.user_data['game_mode'] = None  # Возвращаемся к выбору игры
    save_data()  # Сохраняем данные после игры "Выбор"


# Функция для обработки введенной суммы ставки для игры "Выбор"
async def handle_choice_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    bet_text = update.message.text.strip()
    if not context.user_data.get('awaiting_choice_bet', False):
        return
    context.user_data['awaiting_choice_bet'] = False
    try:
        bet = int(bet_text)
        if bet < 10:
            await update.message.reply_text("Минимальная ставка 10 монет.", reply_markup=create_game_selection_keyboard())
            return
        if user_coins[user_id] < bet:
            await update.message.reply_text(f"У вас недостаточно монет для ставки {bet}. У вас {user_coins[user_id]} монет.", reply_markup=create_game_selection_keyboard())
            return
        context.user_data['choice_bet'] = bet
        context.user_data['game_mode'] = 'choice'  # Устанавливаем game_mode в 'choice'
        await play_choice(update, context)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число для ставки.", reply_markup=create_game_selection_keyboard())


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    # Здесь можно добавить проверку на конкретный администратора, если необходимо
    await update.message.reply_text("Введите пароль администратора:", reply_markup=ForceReply(selective=True))
    context.user_data['awaiting_admin_password'] = True

async def handle_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    password = update.message.text.strip()
    if not context.user_data.get('awaiting_admin_password', False):
        return
    context.user_data['awaiting_admin_password'] = False
    if password == ADMIN_PASSWORD:
        await update.message.reply_text("Пароль верный. Введите сумму, которую хотите зачислить на ваш баланс:", reply_markup=ForceReply(selective=True))
        context.user_data['awaiting_admin_amount'] = True
    else:
        await update.message.reply_text("Неверный пароль. Вернитесь к выбору игры.", reply_markup=create_game_selection_keyboard())

async def handle_admin_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    amount_text = update.message.text.strip()
    if not context.user_data.get('awaiting_admin_amount', False):
        return
    context.user_data['awaiting_admin_amount'] = False
    try:
        amount = int(amount_text)
        if amount <= 0:
            await update.message.reply_text("Сумма должна быть положительным числом.", reply_markup=create_game_selection_keyboard())
            return
        if user_id not in user_coins:
            user_coins[user_id] = 0
        user_coins[user_id] += amount
        await update.message.reply_text(f"Сумма {amount} монет успешно зачислена на ваш баланс. Теперь у вас {user_coins[user_id]} монет.", reply_markup=create_game_selection_keyboard())
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число для суммы.", reply_markup=create_game_selection_keyboard())



async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("Ты долбоеб? ", reply_markup=create_game_selection_keyboard())



# Функция для бесплатной игры в слоты
async def free_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.", reply_markup=create_game_selection_keyboard())
        return
    user_profiles[user_id]['games_played'] += 1
    # Симулируем выпадение слотов
    symbols = list(slot_symbols.keys())
    result = tuple(random.choice(symbols) for _ in range(3))
    message = f"Выпали слоты: {' '.join(result)}\n"  # Добавлен перенос строки

    # Определяем выигрыш
    winnings = 0
    if result in combinations:
        winnings = combinations[result]  # Бесплатный выигрыш для трех совпадающих символов
    elif any(result[i] == result[j] for i in range(len(result)) for j in range(i + 1, len(result))):
        winnings = 5  # Бесплатный выигрыш для двух совпадающих символов
    user_coins[user_id] += winnings
    user_profiles[user_id]['total_winnings'] += winnings
    # Сохраняем результат игры в историю
    user_history[user_id].append({
        'result': result,
        'bet': 0,
        'winnings': winnings,
        'game_mode': 'slots'
    })
    message += f"Вы выиграли {winnings} монет!\n"  # Добавлен перенос строки
    message += f"Теперь у вас {user_coins[user_id]} монет."
    await update.message.reply_text(message, reply_markup=create_slot_control_keyboard())
    save_data()  # Сохраняем данные после бесплатной игры


# Функция для начала игры "Кейсы"
async def cases_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.", reply_markup=create_game_selection_keyboard())
        return
    keyboard = [
        [KeyboardButton("Спасительный (100 монет)"), KeyboardButton("Богатый (500 монет)")],
        [KeyboardButton("Мажор (1000 монет)"), KeyboardButton("Назад к выбору игры")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите кейс:", reply_markup=reply_markup)
    context.user_data['game_mode'] = 'cases'  # Устанавливаем game_mode в 'cases'

# Функция для обработки выбора кейса
async def handle_case_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    case_text = update.message.text.strip()
    if case_text == "Спасительный (100 монет)":
        cost = 100
        if 'discount_cases' in user_purchases.get(user_id, []):
            cost = int(cost * 0.8)  # Применяем скидку -20%
        odds = {50: 0, 20: 200, 30: 150}
    elif case_text == "Богатый (500 монет)":
        cost = 500
        if 'discount_cases' in user_purchases.get(user_id, []):
            cost = int(cost * 0.8)  # Применяем скидку -20%
        odds = {50: 0, 20: 1000, 30: 750}
    elif case_text == "Мажор (1000 монет)":
        cost = 1000
        if 'discount_cases' in user_purchases.get(user_id, []):
            cost = int(cost * 0.8)  # Применяем скидку -20%
        odds = {50: 0, 20: 2000, 30: 1500}
    elif case_text == "Назад к выбору игры":
        await go_back_to_game_selection(update, context)
        return
    else:
        await update.message.reply_text("Пожалуйста, выберите один из предложенных кейсов.", reply_markup=create_game_selection_keyboard())
        return
    if user_coins[user_id] < cost:
        await update.message.reply_text(f"У вас недостаточно монет для покупки этого кейса. У вас {user_coins[user_id]} монет.", reply_markup=create_game_selection_keyboard())
        return
    user_coins[user_id] -= cost  # Вычитаем стоимость кейса из баланса
    user_profiles[user_id]['games_played'] += 1
    # Генерируем случайное число для определения выигрыша
    win_chance = random.randint(1, 100)
    winnings = 0
    cumulative_percentage = 0
    for percentage, reward in odds.items():
        cumulative_percentage += percentage
        if win_chance <= cumulative_percentage:
            winnings = reward
            break
    user_coins[user_id] += winnings
    user_profiles[user_id]['total_winnings'] += winnings
    # Сохраняем результат игры в историю
    user_history[user_id].append({
        'case': case_text,
        'cost': cost,
        'winnings': winnings,
        'game_mode': 'cases'
    })
    message = f"Вы выбрали кейс: {case_text}\n"
    message += f"Вы потратили {cost} монет.\n"
    message += f"Вы выиграли {winnings} монет!\n"
    message += f"Теперь у вас {user_coins[user_id]} монет."
    await update.message.reply_text(message, reply_markup=create_game_selection_keyboard())
    context.user_data['game_mode'] = None  # Возвращаемся к выбору игры
    save_data()  # Сохраняем данные после выбора кейса

# Функция для показа магазина
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.", reply_markup=create_game_selection_keyboard())
        return
    message = (
        "Добро пожаловать в магазин!\n"
        "Выберите товар для покупки:\n\n"
        "1. АвтоКликер Бот, 40 в 60с - 20000 монет\n"
        "2. Скидка -20% на кейсы - 10000 монет\n"
        "3. Улучшение АвтоКликер Бота, +40 в 60с - 100000 монет (доступно только после покупки первого)\n\n"
        "Для покупки товара отправьте номер товара (1, 2 или 3)."
    )
    await update.message.reply_text(message, reply_markup=ForceReply(selective=True))
    context.user_data['awaiting_shop_item'] = True

# Функция для обработки выбора товара в магазине
async def handle_shop_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    item_text = update.message.text.strip()
    if not context.user_data.get('awaiting_shop_item', False):
        return
    context.user_data['awaiting_shop_item'] = False
    try:
        item_number = int(item_text)
        if item_number == 1:
            if user_coins[user_id] < 20000:
                await update.message.reply_text("У вас недостаточно монет для покупки этого товара.", reply_markup=create_game_selection_keyboard())
                return
            user_coins[user_id] -= 20000
            user_purchases.setdefault(user_id, []).append('autoclicker_1')
            user_autoclicker_rates[user_id] = user_autoclicker_rates.get(user_id, 0) + 40  # Устанавливаем скорость автокликера
            await update.message.reply_text("Вы успешно купили АвтоКликер Бот, 40 в 60с!", reply_markup=create_game_selection_keyboard())
        elif item_number == 2:
            if user_coins[user_id] < 10000:
                await update.message.reply_text("У вас недостаточно монет для покупки этого товара.", reply_markup=create_game_selection_keyboard())
                return
            user_coins[user_id] -= 10000
            user_purchases.setdefault(user_id, []).append('discount_cases')
            await update.message.reply_text("Вы успешно купили Скидку -20% на кейсы!", reply_markup=create_game_selection_keyboard())
        elif item_number == 3:
            if 'autoclicker_1' not in user_purchases.get(user_id, []):
                await update.message.reply_text("Вы не можете купить это улучшение без АвтоКликера Бота, 40 в 60с.", reply_markup=create_game_selection_keyboard())
                return
            if user_coins[user_id] < 100000:
                await update.message.reply_text("У вас недостаточно монет для покупки этого товара.", reply_markup=create_game_selection_keyboard())
                return
            user_coins[user_id] -= 100000
            user_purchases.setdefault(user_id, []).append('autoclicker_upgrade')
            user_autoclicker_rates[user_id] = user_autoclicker_rates.get(user_id, 0) + 40  # Увеличиваем скорость автокликера до 80 в 60с
            await update.message.reply_text("Вы успешно купили Улучшение АвтоКликер Бота, +40 в 60с!", reply_markup=create_game_selection_keyboard())
        else:
            await update.message.reply_text("Пожалуйста, выберите один из предложенных товаров (1, 2 или 3).", reply_markup=create_game_selection_keyboard())
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректный номер товара (1, 2 или 3).", reply_markup=create_game_selection_keyboard())
    save_data()  # Сохраняем данные после покупки товара


# Добавляем обработчик для автоматического начисления монет
async def add_autoclicker_coins(context: ContextTypes.DEFAULT_TYPE) -> None:
    for user_id, rate in user_autoclicker_rates.items():
        if rate > 0:
            user_coins[user_id] += rate
            save_data()  # Сохраняем изменения после начисления

# Функция для уменьшения ставки в слотах
async def decrease_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return

    current_bet = context.user_data.get('bet', 10)
    new_bet = current_bet - 10

    if new_bet < 10:
        await update.message.reply_text(f"Минимальная ставка 10 монет.", reply_markup=create_slot_control_keyboard())
        return

    context.user_data['bet'] = new_bet
    await update.message.reply_text(f"Ставка уменьшена до {new_bet} монет.",
                                    reply_markup=create_slot_control_keyboard())


# Функция для ввода ставки в слотах
async def enter_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return

    await update.message.reply_text("Введите сумму ставки:", reply_markup=ForceReply(selective=True))
    context.user_data['awaiting_bet'] = True


# Функция для обработки введенной ставки в слотах
async def handle_entered_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    bet_text = update.message.text.strip()
    if not context.user_data.get('awaiting_bet', False):
        return
    context.user_data['awaiting_bet'] = False
    try:
        bet = int(bet_text)
        if bet < 10:
            await update.message.reply_text("Минимальная ставка 10 монет.", reply_markup=create_slot_control_keyboard())
            return
        if user_coins[user_id] < bet:
            await update.message.reply_text(
                f"У вас недостаточно монет для ставки {bet}. У вас {user_coins[user_id]} монет.",
                reply_markup=create_slot_control_keyboard())
            return
        context.user_data['bet'] = bet
        await update.message.reply_text(f"Ставка установлена на {bet} монет.",
                                        reply_markup=create_slot_control_keyboard())
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число для ставки.",
                                        reply_markup=create_slot_control_keyboard())
    save_data()  # Сохраняем данные после установки ставки (строка 464)

# Функция для возврата к выбору игры
async def go_back_to_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return

    context.user_data['game_mode'] = None
    await update.message.reply_text("Вы вернулись к выбору игры.", reply_markup=create_game_selection_keyboard())


# Функция для ввода ставки и выбора % апгрейда в рулетке
async def enter_roulette_bet_and_odds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return

    await update.message.reply_text("Введите сумму ставки:", reply_markup=ForceReply(selective=True))
    context.user_data['awaiting_roulette_bet'] = True

save_data()  # Сохраняем данные после установки ставки (строка 464)

# Функция для обработки введенной ставки в рулетке
async def handle_entered_roulette_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    bet_text = update.message.text.strip()
    if not context.user_data.get('awaiting_roulette_bet', False):
        return
    context.user_data['awaiting_roulette_bet'] = False
    try:
        bet = int(bet_text)
        if bet < 10:
            await update.message.reply_text("Минимальная ставка 10 монет.",
                                            reply_markup=create_roulette_control_keyboard())
            return
        if user_coins[user_id] < bet:
            await update.message.reply_text(
                f"У вас недостаточно монет для ставки {bet}. У вас {user_coins[user_id]} монет.",
                reply_markup=create_roulette_control_keyboard())
            return
        context.user_data['roulette_bet'] = bet
        await update.message.reply_text("Выберите % апгрейда:", reply_markup=create_roulette_odds_keyboard())
        context.user_data['awaiting_roulette_odds'] = True
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число для ставки.",
                                        reply_markup=create_roulette_control_keyboard())
    save_data()  # Сохраняем данные после установки ставки в рулетке (строка 504)


# Функция для обработки ошибок Forbidden
async def handle_forbidden_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning(f"Bot was forbidden to send a message to {update.effective_chat.id}. Bot might have been removed from the group.")



# Функция для обработки выбора % апгрейда в рулетке
async def handle_roulette_odds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    odds_text = update.message.text.strip()
    if not context.user_data.get('awaiting_roulette_odds', False):
        return
    context.user_data['awaiting_roulette_odds'] = False
    try:
        odds = int(odds_text.strip('%'))
        if odds not in roulette_odds:
            await update.message.reply_text("Выберите один из предложенных % апгрейда.",
                                            reply_markup=create_roulette_odds_keyboard())
            return
        bet = context.user_data.get('roulette_bet', 10)
        user_coins[user_id] -= bet  # Вычитаем ставку из баланса
        user_profiles[user_id]['games_played'] += 1
        # Генерируем случайное число для рулетки
        win_chance = random.randint(1, 100)
        message = f"Ваша ставка: {bet} монет"
        message += f"Выбранный % апгрейда: {odds}%"
        winnings = 0
        if win_chance <= odds:
            winnings = round(bet * roulette_odds[odds])  # Округляем выигрыш до ближайшего целого числа
            user_coins[user_id] += winnings
            user_profiles[user_id]['total_winnings'] += winnings
            message += f"Вы выиграли {winnings} монет!"
        else:
            message += "Вы не выиграли."
        message += f"Теперь у вас {user_coins[user_id]} монет."
        # Сохраняем результат игры в историю
        user_history[user_id].append({
            'bet': bet,
            'winnings': winnings,
            'odds': odds,
            'game_mode': 'roulette'
        })
        await update.message.reply_text(message, reply_markup=create_roulette_control_keyboard())
    except ValueError:
        await update.message.reply_text("Пожалуйста, выберите один из предложенных % апгрейда.",
                                        reply_markup=create_roulette_odds_keyboard())
    save_data()  # Сохраняем данные после выбора % апгрейда в рулетке (строка 559)

# Функция для показа баланса
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return

    await update.message.reply_text(f"Текущий баланс: {user_coins[user_id]} монет.",
                                    reply_markup=create_game_selection_keyboard())


# Функция для показа профиля пользователя
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.", reply_markup=create_game_selection_keyboard())
        return
    profile = user_profiles[user_id]
    message = (
        f"Профиль пользователя {profile['name']}:\n"
        f"ID пользователя: {user_id}\n"
        f"Баланс: {user_coins[user_id]} монет\n"
        f"Игр сыграно: {profile['games_played']}\n"
        f"Общие выигрыши: {profile['total_winnings']} монет"
    )
    await update.message.reply_text(message, reply_markup=create_game_selection_keyboard())

# Функция для показа истории игр
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.", reply_markup=create_game_selection_keyboard())
        return
    history = user_history.get(user_id, [])
    if not history:
        await update.message.reply_text("У вас пока нет истории игр.", reply_markup=create_game_selection_keyboard())
        return
    message = "История последних игр:\n"
    for i, game in enumerate(history, start=1):
        if game['game_mode'] == 'slots':
            result = ' '.join(game['result'])
            bet = game['bet']
            winnings = game['winnings']
            message += f"{i}. Игра в слоты: Выпали слоты: {result}, Ставка: {bet} монет, Выигрыш: {winnings} монет\n"
        elif game['game_mode'] == 'roulette':
            bet = game['bet']
            winnings = game['winnings']
            odds = game['odds']
            message += f"{i}. Игра в рулетку: Ставка: {bet} монет, % апгрейда: {odds}%, Выигрыш: {winnings} монет\n"
    await update.message.reply_text(message, reply_markup=create_game_selection_keyboard())


# Функция для показа топ игроков
async def show_top_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Сортируем пользователей по количеству монет
    sorted_users = sorted(user_coins.items(), key=lambda x: x[1], reverse=True)[:10]
    if not sorted_users:
        await update.message.reply_text("Пока нет игроков с достаточным количеством монет.", reply_markup=create_game_selection_keyboard())
        return
    message = "Топ-10 игроков:\n"
    for rank, (user_id, coins) in enumerate(sorted_users, start=1):
        user_name = user_profiles.get(user_id, {}).get('name', 'Unknown')
        message += f"{rank}. {user_name}: {coins} монет\n"
    await update.message.reply_text(message, reply_markup=create_game_selection_keyboard())


# Функция для использования промокода
async def use_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return
    if user_profiles[user_id].get('promocode_used', False):
        await update.message.reply_text("Вы уже использовали промокод.", reply_markup=create_game_selection_keyboard())
        return
    await update.message.reply_text("Введите промокод:", reply_markup=ForceReply(selective=True))
    context.user_data['awaiting_promocode'] = True

# Функция для обработки промокода
async def handle_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    promocode = update.message.text.strip()
    if not context.user_data.get('awaiting_promocode', False):
        return
    context.user_data['awaiting_promocode'] = False
    if promocode == "1000" and promocode not in used_promocodes:
        user_coins[user_id] += 1000
        user_profiles[user_id]['promocode_used'] = True
        used_promocodes.add(promocode)
        save_data()  # Сохраняем данные после использования промокода
        await update.message.reply_text("Промокод активирован! Вы получили 1000 монет.", reply_markup=create_game_selection_keyboard())
    else:
        await update.message.reply_text("Неверный промокод или он уже был использован.", reply_markup=create_game_selection_keyboard())

# Функция для обработки выбора % апгрейда в рулетке
async def handle_roulette_odds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    odds_text = update.message.text.strip()
    if not context.user_data.get('awaiting_roulette_odds', False):
        return
    context.user_data['awaiting_roulette_odds'] = False
    try:
        odds = int(odds_text.strip('%'))
        if odds not in roulette_odds:
            await update.message.reply_text("Выберите один из предложенных % апгрейда.",
                                            reply_markup=create_roulette_odds_keyboard())
            return
        bet = context.user_data.get('roulette_bet', 10)
        user_coins[user_id] -= bet  # Вычитаем ставку из баланса
        user_profiles[user_id]['games_played'] += 1
        # Генерируем случайное число для рулетки
        win_chance = random.randint(1, 100)
        message = f"Ваша ставка: {bet} монет\n"
        message += f"Выбранный % апгрейда: {odds}%\n"
        winnings = 0
        if win_chance <= odds:
            winnings = round(bet * roulette_odds[odds])  # Округляем выигрыш до ближайшего целого числа
            user_coins[user_id] += winnings
            user_profiles[user_id]['total_winnings'] += winnings
            message += f"Вы выиграли {winnings} монет!\n"
        else:
            message += "Вы не выиграли.\n"
        message += f"Теперь у вас {user_coins[user_id]} монет."
        # Сохраняем результат игры в историю
        user_history[user_id].append({
            'bet': bet,
            'winnings': winnings,
            'odds': odds,
            'game_mode': 'roulette'
        })
        await update.message.reply_text(message, reply_markup=create_roulette_control_keyboard())
    except ValueError:
        await update.message.reply_text("Пожалуйста, выберите один из предложенных % апгрейда.",
                                        reply_markup=create_roulette_odds_keyboard())
    save_data()  # Сохраняем данные после выбора % апгрейда в рулетке (строка 559)

# Функция для получения ежедневной выплаты
async def get_daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    # Проверяем, получал ли пользователь ежедневную выплату за последние 24 часа
    last_bonus_time = daily_bonus_times.get(user_id, 0)
    current_time = time.time()
    if current_time - last_bonus_time < 86400:  # 86400 секунд = 24 часа
        await update.message.reply_text("Вы уже получили ежедневную выплату за последние 24 часа. Попробуйте завтра.",
                                        reply_markup=create_game_selection_keyboard())
        return
    bonus_amount = 200  # Сумма ежедневной выплаты
    user_coins[user_id] += bonus_amount
    daily_bonus_times[user_id] = current_time
    await update.message.reply_text(f"Вы получили ежедневную выплату! Теперь у вас {user_coins[user_id]} монет.",
                                    reply_markup=create_game_selection_keyboard())
    save_data()  # Сохраняем данные после получения ежедневной выплаты (строка 636)

# Функция для показа информации о правилах
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rules_message = (
        "Правила казино:\n"
        "1. Игра в слоты:\n"
        "   - Ставка: от 10 монет.\n"
        "   - Выигрыши:\n"
        "     - 3 одинаковых символа: соответствующий выигрыш.\n"
        "     - 2 одинаковых символа: удвоенная ставка.\n"
        "   - Бесплатная игра: минимальный выигрыш 5 монет.\n"
        "2. Игра в рулетку:\n"
        "   - Ставка: от 10 монет.\n"
        "   - Выбор % апгрейда: 10%, 20%, 30%, 40%, 50%, 60%, 70%.\n"
        "   - Чем меньше %, тем выше коэффициент выигрыша.\n"
        "   - Округление выигрышей до ближайшего целого числа.\n"
        "3. Промокоды:\n"
        "   - Используйте промокод '1000' для получения 1000 монет (один раз).\n"
        "4. **Ежедневная выплата**:\n"
        "   - Получайте 200 монет каждые 24 часа."
    )
    await update.message.reply_text(rules_message, reply_markup=create_game_selection_keyboard())


# Функция для связи с администратором
async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    admin_username = "@lonyxx2"  # Замените на реальный username администратора

    await update.message.reply_text(f"Для связи с администратором напишите сообщение: {admin_username}",
                                    reply_markup=create_game_selection_keyboard())

async def handle_share_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    share_user_id_text = update.message.text.strip()
    if not context.user_data.get('awaiting_share_user_id', False):
        return
    context.user_data['awaiting_share_user_id'] = False
    try:
        share_user_id = int(share_user_id_text)
        if share_user_id == user_id:
            await update.message.reply_text("Вы не можете поделиться монетами с самим собой.",
                                            reply_markup=create_game_selection_keyboard())
            return
        if share_user_id not in user_coins:
            await update.message.reply_text("Пользователь с таким ID не найден.",
                                            reply_markup=create_game_selection_keyboard())
            return
        await update.message.reply_text("Введите количество монет, которое вы хотите поделиться:",
                                        reply_markup=ForceReply(selective=True))
        context.user_data['share_user_id'] = share_user_id
        context.user_data['awaiting_share_amount'] = True
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректный ID пользователя.",
                                        reply_markup=create_game_selection_keyboard())


# Функция для обработки разделения монет
async def handle_share_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    share_amount_text = update.message.text.strip()
    if not context.user_data.get('awaiting_share_amount', False):
        return
    context.user_data['awaiting_share_amount'] = False
    try:
        share_amount = int(share_amount_text)
        if share_amount <= 0:
            await update.message.reply_text("Количество монет должно быть больше 0.",
                                            reply_markup=create_game_selection_keyboard())
            return
        if user_coins[user_id] < share_amount:
            await update.message.reply_text(f"У вас недостаточно монет для поделки. У вас {user_coins[user_id]} монет.",
                                            reply_markup=create_game_selection_keyboard())
            return
        share_user_id = context.user_data.get('share_user_id')
        user_coins[user_id] -= share_amount
        user_coins[share_user_id] += share_amount
        await update.message.reply_text(
            f"Вы успешно поделились {share_amount} монет с пользователем {share_user_id}. Теперь у вас {user_coins[user_id]} монет.",
            reply_markup=create_game_selection_keyboard())
        await context.bot.send_message(chat_id=share_user_id,
                                       text=f"Вы получили {share_amount} монет от пользователя {user_id}.")
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное количество монет.",
                                        reply_markup=create_game_selection_keyboard())
    save_data()  # Сохраняем данные после разделения монет (строка 688)


async def share_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return
    await update.message.reply_text("Введите ID пользователя, которому вы хотите поделиться монетами:",
                                    reply_markup=ForceReply(selective=True))
    context.user_data['awaiting_share_user_id'] = True

save_data()  # Сохраняем данные после разделения монет (строка 688)


# Функция для увеличения ставки в слотах
async def increase_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in user_coins:
        await update.message.reply_text("Вы не начали игру. Введите /start.",
                                        reply_markup=create_game_selection_keyboard())
        return
    current_bet = context.user_data.get('bet', 10)
    new_bet = current_bet + 10
    if new_bet > user_coins[user_id]:
        await update.message.reply_text(f"Вы не можете установить ставку больше вашего баланса. У вас {user_coins[user_id]} монет.",
                                        reply_markup=create_slot_control_keyboard())
        return
    context.user_data['bet'] = new_bet
    await update.message.reply_text(f"Ставка увеличена до {new_bet} монет.",
                                    reply_markup=create_slot_control_keyboard())

# Обновляем функцию handle_message для обработки новых команд и состояний
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text

    if context.user_data.get('awaiting_admin_password', False):
        await handle_admin_password(update, context)
    elif context.user_data.get('awaiting_admin_amount', False):
        await handle_admin_amount(update, context)
    elif context.user_data.get('awaiting_promocode', False):
        await handle_promocode(update, context)
    elif context.user_data.get('awaiting_bet', False):
        await handle_entered_bet(update, context)
    elif context.user_data.get('awaiting_roulette_bet', False):
        await handle_entered_roulette_bet(update, context)
    elif context.user_data.get('awaiting_roulette_odds', False):
        await handle_roulette_odds(update, context)
    elif context.user_data.get('awaiting_share_user_id', False):
        await handle_share_user_id(update, context)
    elif context.user_data.get('awaiting_share_amount', False):
        await handle_share_amount(update, context)
    elif context.user_data.get('awaiting_choice_bet', False):
        await handle_choice_bet(update, context)
    elif context.user_data.get('choice_buttons', False):
        await handle_choice_button(update, context)
    elif context.user_data.get('game_mode') == 'slots':
        if text == "Играть в слоты":
            await play_slots(update, context)
        elif text == "Бесплатная игра":
            await free_play(update, context)
        elif text == "Увеличить ставку":
            await increase_bet(update, context)
        elif text == "Уменьшить ставку":
            await decrease_bet(update, context)
        elif text == "Ввести ставку":
            await enter_bet(update, context)
        elif text == "Назад к выбору игры":
            await go_back_to_game_selection(update, context)
        else:
            await update.message.reply_text("Неизвестная команда. Пожалуйста, используйте кнопки для взаимодействия с ботом.", reply_markup=create_slot_control_keyboard())
    elif context.user_data.get('game_mode') == 'roulette':
        if text == "Ввести ставку и выбрать % апгрейда":
            await enter_roulette_bet_and_odds(update, context)
        elif text == "Назад к выбору игры":
            await go_back_to_game_selection(update, context)
        elif text in ["10%", "20%", "30%", "40%", "50%", "60%", "70%"]:
            await handle_roulette_odds(update, context)
        elif text == "Назад к управлению ставками":
            await update.message.reply_text("Введите сумму ставки:", reply_markup=ForceReply(selective=True))
            context.user_data['awaiting_roulette_bet'] = True
        else:
            await update.message.reply_text("Неизвестная команда. Пожалуйста, используйте кнопки для взаимодействия с ботом.", reply_markup=create_roulette_control_keyboard())
    elif context.user_data.get('game_mode') == 'choice':  # Добавляем проверку для game_mode 'choice'
        await handle_choice_button(update, context)
    elif context.user_data.get('game_mode') == 'cases':
        await handle_case_selection(update, context)
    elif context.user_data.get('awaiting_shop_item', False):
        await handle_shop_item(update, context)  # Обработка выбора товара в магазине
    elif context.user_data.get('awaiting_dumbbell_bet', False):
        await handle_entered_dumbbell_bet(update, context)  # Обработка введенной ставки в дурака
    elif context.user_data.get('awaiting_player_attack', False) or context.user_data.get('awaiting_player_defense', False):
        await handle_player_card(update, context)  # Обработка карты игрока в дурака
    else:
        if text == "Игра в слоты":
            await select_slot_game(update, context)
        elif text == "Игра в рулетку":
            await select_roulette_game(update, context)
        elif text == "Показать баланс":
            await show_balance(update, context)
        elif text == "Показать профиль":
            await show_profile(update, context)
        elif text == "История игр":
            await show_history(update, context)
        elif text == "Топ игроков":
            await show_top_players(update, context)
        elif text == "Использовать промокод":
            await use_promocode(update, context)
        elif text == "Получить ежедневную выплату":
            await get_daily_bonus(update, context)
        elif text == "Поделиться монетами":
            await share_coins(update, context)
        elif text == "Правила":
            await show_rules(update, context)
        elif text == "Связаться с администратором":
            await contact_admin(update, context)
        elif text == "Выбор":
            await choice_game(update, context)
        elif text == "Кейсы":
            await cases_game(update, context)
        elif text == "Для администраторов":
            await admin_command(update, context)
        elif text == "Вывод":  # Добавляем обработку кнопки "Вывод"
            await withdraw_command(update, context)
        elif text == "Магазин":  # Добавляем обработку кнопки "Магазин"
            await shop(update, context)
        else:
            await update.message.reply_text("Неизвестная команда. Пожалуйста, используйте кнопки для взаимодействия с ботом.", reply_markup=create_game_selection_keyboard())

    # Сохраняем данные после каждого изменения
    save_data()  # Сохраняем данные после обработки сообщения

# Создаем приложение
application = ApplicationBuilder().token(TOKEN).build()

# Регистрируем команды
start_handler = CommandHandler('start', start)
shop_handler = CommandHandler('shop', shop)  # Добавляем обработчик для команды /shop
message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
rules_handler = CommandHandler('rules', show_rules)
contact_admin_handler = CommandHandler('contact', contact_admin)
withdraw_handler = CommandHandler('withdraw', withdraw_command)
application.add_handler(withdraw_handler)
application.add_handler(start_handler)
application.add_handler(shop_handler)  # Добавляем обработчик для команды /shop
application.add_handler(message_handler)
application.add_handler(rules_handler)
application.add_handler(contact_admin_handler)
admin_handler = CommandHandler('admin', admin_command)
application.add_handler(admin_handler)



# Запускаем бота
logger.info("Бот запущен.")
application.run_polling()

# Регистрируем обработчик для всех запросов после завершения работы бота
application.add_handler(MessageHandler(filters.ALL, handle_all_messages))


