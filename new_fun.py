import logging
import json
import os

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
)

USERS_FILE = 'users.json'
REVIEWS_FILE = 'reviews.json'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

(
    CHOOSE_GENDER,
    ENTER_AGE,
    ENTER_ABOUT,
    CHOOSE_TARGET_GENDER,
    ENTER_AGE_RANGE,
    UPLOAD_PHOTO,
) = range(6)

(
    EDIT_CHOOSE_FIELD,
    EDIT_FIELD,
) = range(6, 8)

(
    REVIEW_ENTER_TARGET,
    REVIEW_ENTER_TEXT,
) = range(8, 10)

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

# --- Добавим хранилище лайков в память (можно заменить на файл при необходимости) ---
# Формат: {user_id: set(user_id_которым поставлен лайк)}
LIKES_FILE = 'likes.json'

def get_likes():
    return load_json(LIKES_FILE, {})

def set_likes(data):
    save_json(LIKES_FILE, data)

def add_like(from_user_id, to_user_id):
    likes = get_likes()
    str_from = str(from_user_id)
    str_to = str(to_user_id)
    if str_from not in likes:
        likes[str_from] = []
    if str_to not in likes[str_from]:
        likes[str_from].append(str_to)
    set_likes(likes)

def check_mutual_like(user1_id, user2_id):
    likes = get_likes()
    str_user1 = str(user1_id)
    str_user2 = str(user2_id)
    return (str_user1 in likes and str_user2 in likes[str_user1]) and (str_user2 in likes and str_user1 in likes[str_user2])

# --- Главное меню ---

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Создать/обновить анкету", "Искать собеседника"],
        ["Редактировать профиль", "Оставить отзыв"],
        ["Посмотреть отзывы"]
    ]
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update, context)

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text == "создать/обновить анкету":
        reply_keyboard = [['мужской', 'женский', 'другой']]
        await update.message.reply_text(
            "Выбери свой пол:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
        )
        return CHOOSE_GENDER
    elif text == "искать собеседника":
        return await search(update, context)
    elif text == "редактировать профиль":
        return await edit(update, context)
    elif text == "оставить отзыв":
        return await review_start(update, context)
    elif text == "посмотреть отзывы":
        return await show_reviews(update, context)
    else:
        await main_menu(update, context)
        return

# --- Создание/обновление анкеты ---

async def choose_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.lower()
    if gender not in ['мужской', 'женский', 'другой']:
        await update.message.reply_text("Пожалуйста, выбери пол из предложенных вариантов.")
        return CHOOSE_GENDER
    context.user_data['gender'] = gender.capitalize()
    await update.message.reply_text("Сколько тебе лет?", reply_markup=ReplyKeyboardRemove())
    return ENTER_AGE

async def enter_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if age < 13 or age > 120:
            await update.message.reply_text("Пожалуйста, введи корректный возраст (от 13 до 120).")
            return ENTER_AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число.")
        return ENTER_AGE
    context.user_data['age'] = age
    await update.message.reply_text("Расскажи немного о себе (несколько слов):")
    return ENTER_ABOUT

async def enter_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about = update.message.text
    context.user_data['about'] = about
    reply_keyboard = [['мужской', 'женский', 'любой']]
    await update.message.reply_text(
        "Какой пол собеседника ты ищешь?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSE_TARGET_GENDER

async def choose_target_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_gender = update.message.text.lower()
    if target_gender not in ['мужской', 'женский', 'любой']:
        await update.message.reply_text("Пожалуйста, выбери пол собеседника из предложенных вариантов.")
        return CHOOSE_TARGET_GENDER
    context.user_data['target_gender'] = target_gender.capitalize()
    await update.message.reply_text(
        "Введите минимальный и максимальный возраст искомого собеседника через дефис (например, 20-30):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ENTER_AGE_RANGE

async def enter_age_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text("Пожалуйста, введи корректный диапазон в формате: 20-30")
        return ENTER_AGE_RANGE
    context.user_data['age_min'] = age_min
    context.user_data['age_max'] = age_max
    await update.message.reply_text(
        "Отправь свое фото (не документ, а именно фото) или нажми /skip чтобы пропустить:"
    )
    return UPLOAD_PHOTO

async def upload_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data['photo_id'] = photo.file_id
    else:
        context.user_data['photo_id'] = None

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

    await update.message.reply_text(
        "Анкета создана/обновлена! Теперь ты можешь искать собеседников.\n"
        "Главное меню:",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["Создать/обновить анкету", "Искать собеседника"],
                ["Редактировать профиль", "Оставить отзыв"],
                ["Посмотреть отзывы"]
            ], resize_keyboard=True)
    )
    return ConversationHandler.END

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['photo_id'] = None
    return await upload_photo(update, context)

# --- Поиск и просмотр анкет с лайками и отзывами ---

async def show_profile(update_obj, context, profiles, index):
    if index >= len(profiles):
        if hasattr(update_obj, 'callback_query') and update_obj.callback_query:
            await update_obj.callback_query.edit_message_text("Анкеты закончились.")
        else:
            await update_obj.message.reply_text("Анкеты закончились.")
        return

    profile = profiles[index]
    text = (
        f"Пол: {profile['gender']}\n"
        f"Возраст: {profile['age']}\n"
        f"О себе: {profile['about']}\n"
    )
    keyboard = [
        [
            InlineKeyboardButton("👍 Нравится", callback_data=f"like_{index}"),
            InlineKeyboardButton("➡️ Пропустить", callback_data=f"skip_{index}")
        ],
        [
            InlineKeyboardButton("Отзывы", callback_data=f"reviews_{index}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if 'photo_id' in profile and profile['photo_id']:
        if hasattr(update_obj, 'callback_query') and update_obj.callback_query:
            await update_obj.callback_query.edit_message_media(
                media=InputMediaPhoto(profile['photo_id'], caption=text),
                reply_markup=reply_markup
            )
        else:
            await update_obj.message.reply_photo(
                photo=profile['photo_id'],
                caption=text,
                reply_markup=reply_markup
            )
    else:
        if hasattr(update_obj, 'callback_query') and update_obj.callback_query:
            await update_obj.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update_obj.message.reply_text(text, reply_markup=reply_markup)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = find_user_by_id(user_id)
    if not user:
        await update.message.reply_text("Сначала создай анкету.")
        return ConversationHandler.END
    users_list = get_users_list()
    results = [
        u for u in users_list
        if u['user_id'] != user_id and
           (user['target_gender'].lower() == 'любой' or u['gender'].lower() == user['target_gender'].lower()) and
           (user['age_min'] <= u['age'] <= user['age_max'])
    ]
    if not results:
        await update.message.reply_text("По вашим параметрам собеседников не найдено.")
        return ConversationHandler.END
    context.user_data['search_results'] = results
    context.user_data['search_index'] = 0
    await show_profile(update, context, results, 0)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    index = context.user_data.get('search_index', 0)
    results = context.user_data.get('search_results', [])
    if not results:
        await query.edit_message_text("Нет анкет для показа.")
        return

    if data.startswith("like_"):
        # Лайкнули анкету с индексом
        liked_index = int(data.split('_')[1])
        liked_user = results[liked_index]
        liker_id = query.from_user.id
        liked_id = liked_user['user_id']

        add_like(liker_id, liked_id)
        await query.answer("Вы поставили лайк!")

        # Проверяем взаимный лайк
        if check_mutual_like(liker_id, liked_id):
            # Отправляем уведомления обоим пользователям
            liker = find_user_by_id(liker_id)
            liked = find_user_by_id(liked_id)
            if liker and liked:
                liker_name = liker.get('username') or f"Пользователь {liker_id}"
                liked_name = liked.get('username') or f"Пользователь {liked_id}"

                try:
                    await context.bot.send_message(
                        chat_id=liker_id,
                        text=f"У вас взаимный лайк с @{liked_name}! Вот его анкета:\n"
                             f"Пол: {liked['gender']}\nВозраст: {liked['age']}\nО себе: {liked['about']}\nTelegram: @{liked.get('username', 'не указан')}"
                    )
                    await context.bot.send_message(
                        chat_id=liked_id,
                        text=f"У вас взаимный лайк с @{liker_name}! Вот его анкета:\n"
                             f"Пол: {liker['gender']}\nВозраст: {liker['age']}\nО себе: {liker['about']}\nTelegram: @{liker.get('username', 'не указан')}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления о взаимном лайке: {e}")

        index = liked_index + 1
        context.user_data['search_index'] = index
        if index < len(results):
            await show_profile(query, context, results, index)
        else:
            await query.edit_message_text("Анкеты закончились.")

    elif data.startswith("skip_"):
        skip_index = int(data.split('_')[1])
        await query.answer("Анкета пропущена.")
        index = skip_index + 1
        context.user_data['search_index'] = index
        if index < len(results):
            await show_profile(query, context, results, index)
        else:
            await query.edit_message_text("Анкеты закончились.")

    elif data.startswith("reviews_"):
        rev_index = int(data.split('_')[1])
        profile = results[rev_index]
        username = profile.get('username')
        if not username:
            await query.answer("У этого пользователя нет username, отзывы недоступны.", show_alert=True)
            return
        reviews = get_reviews()
        user_reviews = reviews.get(username.lower(), [])
        if not user_reviews:
            text = "Отзывов о пользователе пока нет."
        else:
            text = "Отзывы о пользователе:\n\n" + "\n\n".join(user_reviews)
        try:
            await query.answer()
            await query.message.reply_text(text)
        except Exception as e:
            logger.error(f"Ошибка при отправке отзывов: {e}")

# --- Редактирование профиля ---

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = find_user_by_id(update.message.from_user.id)
    if not user:
        await update.message.reply_text("Сначала создай анкету.")
        return ConversationHandler.END
    reply_keyboard = [
        ['Пол', 'Возраст'],
        ['О себе', 'Искомый пол'],
        ['Возрастной диапазон', 'Фото'],
        ['Отмена']
    ]
    await update.message.reply_text(
        "Что хочешь изменить?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return EDIT_CHOOSE_FIELD

async def edit_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.lower()
    if choice == 'отмена':
        await update.message.reply_text("Редактирование отменено.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    fields_map = {
        'пол': 'gender',
        'возраст': 'age',
        'о себе': 'about',
        'искомый пол': 'target_gender',
        'возрастной диапазон': 'age_range',
        'фото': 'photo'
    }
    if choice not in fields_map:
        await update.message.reply_text("Пожалуйста, выбери поле из списка.")
        return EDIT_CHOOSE_FIELD
    context.user_data['edit_field'] = fields_map[choice]
    field = fields_map[choice]
    if field == 'age_range':
        await update.message.reply_text("Введите минимальный и максимальный возраст искомого собеседника через дефис (например, 20-30):")
    elif field == 'gender':
        await update.message.reply_text("Выберите свой пол: Мужской, Женский, Другой")
    elif field == 'target_gender':
        await update.message.reply_text("Какой пол собеседника вы ищете? Мужской, Женский, Любой")
    elif field == 'age':
        await update.message.reply_text("Введите ваш возраст:")
    elif field == 'about':
        await update.message.reply_text("Расскажите немного о себе:")
    elif field == 'photo':
        await update.message.reply_text("Отправьте новое фото или /skip чтобы удалить текущее:")
        return EDIT_FIELD
    return EDIT_FIELD

async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = context.user_data.get('edit_field')
    user_id = update.message.from_user.id
    users_list = get_users_list()
    user = next((u for u in users_list if u['user_id'] == user_id), None)
    if not user:
        await update.message.reply_text("Ошибка: профиль не найден.")
        return ConversationHandler.END

    if field == 'photo':
        if update.message.photo:
            photo = update.message.photo[-1]
            user['photo_id'] = photo.file_id
        else:
            await update.message.reply_text("Пожалуйста, отправьте фото или используйте /skip")
            return EDIT_FIELD
    else:
        text = update.message.text.strip()
        text_lower = text.lower()
        if field == 'gender':
            if text_lower not in ['мужской', 'женский', 'другой']:
                await update.message.reply_text("Пожалуйста, выберите: Мужской, Женский или Другой")
                return EDIT_FIELD
            user['gender'] = text.capitalize()
        elif field == 'target_gender':
            if text_lower not in ['мужской', 'женский', 'любой']:
                await update.message.reply_text("Пожалуйста, выберите: Мужской, Женский или Любой")
                return EDIT_FIELD
            user['target_gender'] = text.capitalize()
        elif field == 'age':
            try:
                age = int(text)
                if age < 13 or age > 120:
                    raise ValueError
                user['age'] = age
            except ValueError:
                await update.message.reply_text("Введите корректный возраст (от 13 до 120):")
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
                await update.message.reply_text("Пожалуйста, введи корректный диапазон в формате: 20-30")
                return EDIT_FIELD

    set_users_list(users_list)
    await update.message.reply_text("Данные обновлены!", reply_markup=ReplyKeyboardRemove())
    await main_menu(update, context)
    return ConversationHandler.END

async def skip_photo_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    users_list = get_users_list()
    for u in users_list:
        if u['user_id'] == user_id:
            u['photo_id'] = None
            break
    set_users_list(users_list)
    await update.message.reply_text("Фото удалено из профиля!", reply_markup=ReplyKeyboardRemove())
    await main_menu(update, context)
    return ConversationHandler.END

# --- Отзывы ---

async def review_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите username пользователя, о котором хотите оставить отзыв (например, @username):")
    return REVIEW_ENTER_TARGET

async def review_enter_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    context.user_data['review_target'] = username
    await update.message.reply_text(f"Вы оставляете отзыв пользователю {username}. Напишите текст отзыва:")
    return REVIEW_ENTER_TEXT

async def review_enter_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    username = context.user_data.get('review_target')
    if not username:
        await update.message.reply_text("Ошибка: не выбран пользователь.")
        return ConversationHandler.END
    reviews = get_reviews()
    key = username.lower()
    if key not in reviews:
        reviews[key] = []
    reviews[key].append(text)
    set_reviews(reviews)
    await update.message.reply_text("Ваш отзыв сохранён!", reply_markup=ReplyKeyboardRemove())
    await main_menu(update, context)
    return ConversationHandler.END

async def show_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username
    if not username:
        await update.message.reply_text("У вас нет username.")
        return
    reviews = get_reviews()
    user_reviews = reviews.get(username.lower(), [])
    if not user_reviews:
        await update.message.reply_text("Отзывов о вас пока нет.")
    else:
        await update.message.reply_text("Отзывы о вас:\n" + "\n\n".join(user_reviews))
    await main_menu(update, context)
    return

# --- Запуск бота ---

def main():
    application = Application.builder().token("8121277507:AAEvqSpC30D6kQzU1-ACkDgJ5FLomy7DKnc").build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^(Создать/обновить анкету|Редактировать профиль|Оставить отзыв|Посмотреть отзывы|Искать собеседника)$"), handle_menu),
        ],
        states={
            CHOOSE_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_gender)],
            ENTER_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_age)],
            ENTER_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_about)],
            CHOOSE_TARGET_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_target_gender)],
            ENTER_AGE_RANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_age_range)],
            UPLOAD_PHOTO: [
                MessageHandler(filters.PHOTO, upload_photo),
                CommandHandler("skip", skip_photo)
            ],
            EDIT_CHOOSE_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_choose_field)],
            EDIT_FIELD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field),
                MessageHandler(filters.PHOTO, edit_field),
                CommandHandler("skip", skip_photo_edit)
            ],
            REVIEW_ENTER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_enter_target)],
            REVIEW_ENTER_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_enter_text)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
