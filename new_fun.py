import logging
import json
import os

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
)

# Файлы для хранения данных
USERS_FILE = 'users.json'
REVIEWS_FILE = 'reviews.json'

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    CHOOSE_GENDER,
    ENTER_AGE,
    ENTER_ABOUT,
    CHOOSE_TARGET_GENDER,
    ENTER_AGE_RANGE,
) = range(5)

(
    EDIT_CHOOSE_FIELD,
    EDIT_FIELD,
) = range(5, 7)

(
    REVIEW_ENTER_TARGET,
    REVIEW_ENTER_TEXT,
) = range(7, 9)

# --- Работа с JSON ---

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_users_list():
    return load_json(USERS_FILE, [])

def set_users_list(users):
    save_json(USERS_FILE, users)

def get_reviews():
    return load_json(REVIEWS_FILE, {})

def set_reviews(reviews):
    save_json(REVIEWS_FILE, reviews)

# --- Поиск пользователя ---
def find_user_by_id(user_id):
    users_list = get_users_list()
    for u in users_list:
        if u['user_id'] == user_id:
            return u
    return None

def find_user_by_username(username):
    users_list = get_users_list()
    username = username.lstrip('@').lower()
    for u in users_list:
        if 'username' in u and u['username'].lower() == username:
            return u
    return None

# --- Главное меню ---
MENU_CREATE_PROFILE = 'menu_create_profile'
MENU_SEARCH = 'menu_search'
MENU_EDIT_PROFILE = 'menu_edit_profile'
MENU_REVIEW = 'menu_review'
MENU_SHOW_REVIEWS = 'menu_show_reviews'
MENU_CANCEL = 'menu_cancel'

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Создать / Обновить анкету", callback_data=MENU_CREATE_PROFILE)],
        [InlineKeyboardButton("Поиск собеседников", callback_data=MENU_SEARCH)],
        [InlineKeyboardButton("Редактировать профиль", callback_data=MENU_EDIT_PROFILE)],
        [InlineKeyboardButton("Оставить отзыв", callback_data=MENU_REVIEW)],
        [InlineKeyboardButton("Показать отзывы обо мне", callback_data=MENU_SHOW_REVIEWS)],
        [InlineKeyboardButton("Отмена", callback_data=MENU_CANCEL)],
    ]
    return InlineKeyboardMarkup(keyboard)

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Добро пожаловать! Выберите действие:",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

def menu_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == MENU_CREATE_PROFILE:
        query.message.delete()
        reply_keyboard = [['Мужской', 'Женский', 'Другой']]
        query.message.reply_text(
            "Давай создадим твою анкету.\nВыбери свой пол:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return CHOOSE_GENDER
    elif data == MENU_SEARCH:
        query.message.delete()
        fake_update = query
        fake_update.message = query.message
        search(fake_update, context)
        return ConversationHandler.END
    elif data == MENU_EDIT_PROFILE:
        query.message.delete()
        fake_update = query
        fake_update.message = query.message
        return edit(fake_update, context)
    elif data == MENU_REVIEW:
        query.message.delete()
        fake_update = query
        fake_update.message = query.message
        return review_start(fake_update, context)
    elif data == MENU_SHOW_REVIEWS:
        query.message.delete()
        fake_update = query
        fake_update.message = query.message
        show_reviews(fake_update, context)
        return ConversationHandler.END
    elif data == MENU_CANCEL:
        query.message.delete()
        query.message.reply_text("Отменено.")
        return ConversationHandler.END

# --- Создание анкеты ---
def choose_gender(update: Update, context: CallbackContext):
    gender = update.message.text
    if gender not in ['Мужской', 'Женский', 'Другой']:
        update.message.reply_text("Пожалуйста, выбери пол из предложенных вариантов.")
        return CHOOSE_GENDER
    context.user_data['gender'] = gender
    update.message.reply_text("Сколько тебе лет?", reply_markup=ReplyKeyboardRemove())
    return ENTER_AGE

def enter_age(update: Update, context: CallbackContext):
    try:
        age = int(update.message.text)
        if age < 13 or age > 120:
            update.message.reply_text("Пожалуйста, введи корректный возраст (от 13 до 120).")
            return ENTER_AGE
    except ValueError:
        update.message.reply_text("Пожалуйста, введи число.")
        return ENTER_AGE
    context.user_data['age'] = age
    update.message.reply_text("Расскажи немного о себе (несколько слов):")
    return ENTER_ABOUT

def enter_about(update: Update, context: CallbackContext):
    about = update.message.text
    context.user_data['about'] = about
    reply_keyboard = [['Мужской', 'Женский', 'Любой']]
    update.message.reply_text(
        "Какой пол собеседника ты ищешь?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return CHOOSE_TARGET_GENDER

def choose_target_gender(update: Update, context: CallbackContext):
    target_gender = update.message.text
    if target_gender not in ['Мужской', 'Женский', 'Любой']:
        update.message.reply_text("Пожалуйста, выбери пол собеседника из предложенных вариантов.")
        return CHOOSE_TARGET_GENDER
    context.user_data['target_gender'] = target_gender
    update.message.reply_text(
        "Введите минимальный и максимальный возраст искомого собеседника через дефис (например, 20-30):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ENTER_AGE_RANGE

def enter_age_range(update: Update, context: CallbackContext):
    text = update.message.text
    try:
        parts = text.split('-')
        if len(parts) != 2:
            raise ValueError
        age_min = int(parts[0])
        age_max = int(parts[1])
        if not (13 <= age_min <= age_max <= 120):
            raise ValueError
    except ValueError:
        update.message.reply_text("Пожалуйста, введи корректный диапазон в формате: 20-30")
        return ENTER_AGE_RANGE
    context.user_data['age_min'] = age_min
    context.user_data['age_max'] = age_max

    username = update.message.from_user.username
    if username:
        context.user_data['username'] = username

    user_id = update.message.from_user.id
    users_list = get_users_list()
    found = False
    for u in users_list:
        if u['user_id'] == user_id:
            u.update(context.user_data)
            found = True
            break
    if not found:
        new_user = context.user_data.copy()
        new_user['user_id'] = user_id
        users_list.append(new_user)
    set_users_list(users_list)

    update.message.reply_text(
        "Анкета создана/обновлена! Теперь вы можете использовать главное меню.",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

# --- Поиск и просмотр анкет ---
def show_profile(update_obj, context, profiles, index):
    if index >= len(profiles):
        if hasattr(update_obj, 'callback_query') and update_obj.callback_query:
            update_obj.callback_query.edit_message_text("Анкеты закончились.")
        else:
            update_obj.message.reply_text("Анкеты закончились.")
        return

    profile = profiles[index]
    text = (
        f"Пол: {profile['gender']}\n"
        f"Возраст: {profile['age']}\n"
        f"О себе: {profile['about']}\n"
        f"Telegram: @{profile.get('username', 'не указан')}"
    )
    keyboard = [
        [
            InlineKeyboardButton("👍 Нравится", callback_data=f"like_{index}"),
            InlineKeyboardButton("➡️ Пропустить", callback_data=f"skip_{index}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_obj, 'callback_query') and update_obj.callback_query:
        update_obj.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        update_obj.message.reply_text(text, reply_markup=reply_markup)

def search(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = find_user_by_id(user_id)
    if not user:
        update.message.reply_text("Сначала создайте анкету через главное меню.")
        return

    users_list = get_users_list()
    results = [
        u for u in users_list
        if u['user_id'] != user_id and
           (user['target_gender'] == 'Любой' or u['gender'] == user['target_gender']) and
           (user['age_min'] <= u['age'] <= user['age_max'])
    ]

    if not results:
        update.message.reply_text("По вашим параметрам собеседников не найдено.")
        return

    context.user_data['search_results'] = results
    context.user_data['search_index'] = 0
    show_profile(update, context, results, 0)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    index = context.user_data.get('search_index', 0)
    results = context.user_data.get('search_results', [])

    if not results:
        query.answer("Нет анкет для показа.")
        return

    if data.startswith("like_"):
        query.answer("Вы поставили лайк!")
    elif data.startswith("skip_"):
        query.answer("Анкета пропущена.")

    index += 1
    context.user_data['search_index'] = index
    if index < len(results):
        show_profile(query, context, results, index)
    else:
        query.edit_message_text("Анкеты закончились.")

# --- Редактирование профиля ---
def edit(update: Update, context: CallbackContext):
    user = find_user_by_id(update.message.from_user.id)
    if not user:
        update.message.reply_text("Сначала создайте анкету через главное меню.")
        return ConversationHandler.END

    reply_keyboard = [
        ['Пол', 'Возраст'],
        ['О себе', 'Искомый пол'],
        ['Возрастной диапазон', 'Отмена']
    ]
    update.message.reply_text(
        "Что хотите изменить?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return EDIT_CHOOSE_FIELD

def edit_choose_field(update: Update, context: CallbackContext):
    choice = update.message.text.lower()
    if choice == 'отмена':
        update.message.reply_text("Редактирование отменено.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    fields_map = {
        'пол': 'gender',
        'возраст': 'age',
        'о себе': 'about',
        'искомый пол': 'target_gender',
        'возрастной диапазон': 'age_range',
    }

    if choice not in fields_map:
        update.message.reply_text("Пожалуйста, выберите поле из списка.")
        return EDIT_CHOOSE_FIELD

    context.user_data['edit_field'] = fields_map[choice]

    if fields_map[choice] == 'age_range':
        update.message.reply_text("Введите минимальный и максимальный возраст искомого собеседника через дефис (например, 20-30):")
    elif fields_map[choice] == 'gender':
        update.message.reply_text("Выберите свой пол: Мужской, Женский, Другой")
    elif fields_map[choice] == 'target_gender':
        update.message.reply_text("Какой пол собеседника вы ищете? Мужской, Женский, Любой")
    elif fields_map[choice] == 'age':
        update.message.reply_text("Введите ваш возраст:")
    elif fields_map[choice] == 'about':
        update.message.reply_text("Расскажите немного о себе:")

    return EDIT_FIELD

def edit_field(update: Update, context: CallbackContext):
    field = context.user_data.get('edit_field')
    text = update.message.text.strip()

    user_id = update.message.from_user.id
    users_list = get_users_list()
    user = None
    for u in users_list:
        if u['user_id'] == user_id:
            user = u
            break
    if not user:
        update.message.reply_text("Ошибка: профиль не найден.")
        return ConversationHandler.END

    if field == 'gender':
        if text not in ['Мужской', 'Женский', 'Другой']:
            update.message.reply_text("Пожалуйста, выберите: Мужской, Женский или Другой")
            return EDIT_FIELD
        user['gender'] = text

    elif field == 'target_gender':
        if text not in ['Мужской', 'Женский', 'Любой']:
            update.message.reply_text("Пожалуйста, выберите: Мужской, Женский или Любой")
            return EDIT_FIELD
        user['target_gender'] = text

    elif field == 'age':
        try:
            age = int(text)
            if age < 13 or age > 120:
                raise ValueError
            user['age'] = age
        except ValueError:
            update.message.reply_text("Введите корректный возраст (от 13 до 120):")
            return EDIT_FIELD

    elif field == 'about':
        user['about'] = text

    elif field == 'age_range':
        try:
            parts = text.split('-')
            if len(parts) != 2:
                raise ValueError
            age_min = int(parts[0])
            age_max = int(parts[1])
            if not (13 <= age_min <= age_max <= 120):
                raise ValueError
            user['age_min'] = age_min
            user['age_max'] = age_max
        except ValueError:
            update.message.reply_text("Пожалуйста, введите корректный диапазон в формате: 20-30")
            return EDIT_FIELD

    set_users_list(users_list)
    update.message.reply_text("Данные обновлены!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- Оставление отзывов ---
def review_start(update: Update, context: CallbackContext):
    args = context.args
    if args:
        username = args[0]
        context.user_data['review_target'] = username
        update.message.reply_text(f"Вы оставляете отзыв пользователю {username}. Напишите текст отзыва:")
        return REVIEW_ENTER_TEXT
    else:
        update.message.reply_text("Введите username пользователя, о котором хотите оставить отзыв (например, @username):")
        return REVIEW_ENTER_TARGET

def review_enter_target(update: Update, context: CallbackContext):
    username = update.message.text.strip()
    if not username.startswith('@'):
        update.message.reply_text("Пожалуйста, введите username в формате @username")
        return REVIEW_ENTER_TARGET
    context.user_data['review_target'] = username
    update.message.reply_text(f"Вы оставляете отзыв пользователю {username}. Напишите текст отзыва:")
    return REVIEW_ENTER_TEXT

def review_enter_text(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    username = context.user_data.get('review_target')
    if not username:
        update.message.reply_text("Ошибка: не указан пользователь для отзыва.")
        return ConversationHandler.END

    target_user = find_user_by_username(username)
    if not target_user:
        update.message.reply_text("Пользователь с таким username не найден.")
        return ConversationHandler.END

    user_id = target_user['user_id']
    from_id = update.message.from_user.id

    reviews = get_reviews()
    if str(user_id) not in reviews:
        reviews[str(user_id)] = []
    reviews[str(user_id)].append({'from_id': from_id, 'text': text})
    set_reviews(reviews)

    update.message.reply_text("Спасибо! Ваш отзыв сохранён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def show_reviews(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    reviews = get_reviews()
    user_reviews = reviews.get(str(user_id), [])
    if not user_reviews:
        update.message.reply_text("О вас ещё нет отзывов.")
        return

    texts = []
    users_list = get_users_list()
    for i, rev in enumerate(user_reviews, 1):
        from_user = None
        for u in users_list:
            if u['user_id'] == rev['from_id']:
                from_user = u
                break
        from_name = from_user.get('username', f"Пользователь {rev['from_id']}") if from_user else f"Пользователь {rev['from_id']}"
        texts.append(f"{i}. От {from_name}: {rev['text']}")
    update.message.reply_text("\n\n".join(texts))

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Отменено.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    TOKEN = '8121277507:AAEvqSpC30D6kQzU1-ACkDgJ5FLomy7DKnc'

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_GENDER: [MessageHandler(Filters.text & ~Filters.command, choose_gender)],
            ENTER_AGE: [MessageHandler(Filters.text & ~Filters.command, enter_age)],
            ENTER_ABOUT: [MessageHandler(Filters.text & ~Filters.command, enter_about)],
            CHOOSE_TARGET_GENDER: [MessageHandler(Filters.text & ~Filters.command, choose_target_gender)],
            ENTER_AGE_RANGE: [MessageHandler(Filters.text & ~Filters.command, enter_age_range)],
            EDIT_CHOOSE_FIELD: [MessageHandler(Filters.text & ~Filters.command, edit_choose_field)],
            EDIT_FIELD: [MessageHandler(Filters.text & ~Filters.command, edit_field)],
            REVIEW_ENTER_TARGET: [MessageHandler(Filters.text & ~Filters.command, review_enter_target)],
            REVIEW_ENTER_TEXT: [MessageHandler(Filters.text & ~Filters.command, review_enter_text)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CallbackQueryHandler(menu_handler, pattern='^menu_'))
    dp.add_handler(CallbackQueryHandler(button_handler, pattern='^(like_|skip_)'))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
