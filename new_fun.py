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
import logging

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Этапы разговора для создания анкеты
(
    CHOOSE_GENDER,
    ENTER_AGE,
    ENTER_ABOUT,
    CHOOSE_TARGET_GENDER,
    ENTER_AGE_RANGE,
) = range(5)

# Этапы разговора для редактирования профиля
(
    EDIT_CHOOSE_FIELD,
    EDIT_FIELD,
) = range(5, 7)

# Этапы разговора для отзывов
(
    REVIEW_ENTER_TARGET,
    REVIEW_ENTER_TEXT,
) = range(7, 9)

# Хранение данных пользователей: список словарей с данными
users_list = []

# Хранение отзывов: user_id -> список отзывов (каждый отзыв — dict с 'from_id' и 'text')
reviews = {}


def find_user_by_id(user_id):
    for u in users_list:
        if u['user_id'] == user_id:
            return u
    return None


def find_user_by_username(username):
    username = username.lstrip('@').lower()
    for u in users_list:
        if 'username' in u and u['username'].lower() == username:
            return u
    return None


def start(update: Update, context: CallbackContext):
    reply_keyboard = [['Мужской', 'Женский', 'Другой']]
    update.message.reply_text(
        "Привет! Давай создадим твою анкету.\n"
        "Выбери свой пол:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return CHOOSE_GENDER


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

    # Сохраняем username (если есть)
    username = update.message.from_user.username
    if username:
        context.user_data['username'] = username

    # Сохраняем данные пользователя
    user_id = update.message.from_user.id
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

    update.message.reply_text(
        "Анкета создана/обновлена! Теперь ты можешь искать собеседников командой /search\n"
        "Чтобы редактировать профиль — /edit\n"
        "Чтобы оставить отзыв — /review\n"
        "Чтобы посмотреть отзывы о себе — /showreviews"
    )
    return ConversationHandler.END


def show_profile(update_obj, context, profiles, index):
    if index >= len(profiles):
        if update_obj.callback_query:
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

    if update_obj.callback_query:
        update_obj.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        update_obj.message.reply_text(text, reply_markup=reply_markup)


def search(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = find_user_by_id(user_id)
    if not user:
        update.message.reply_text("Сначала создай анкету командой /start")
        return

    # Фильтрация анкет
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
        # Здесь можно добавить логику сохранения лайка, например, для взаимных совпадений
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
        update.message.reply_text("Сначала создай анкету командой /start")
        return ConversationHandler.END

    reply_keyboard = [
        ['Пол', 'Возраст'],
        ['О себе', 'Искомый пол'],
        ['Возрастной диапазон', 'Отмена']
    ]
    update.message.reply_text(
        "Что хочешь изменить?",
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
        update.message.reply_text("Пожалуйста, выбери поле из списка.")
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

    user = find_user_by_id(update.message.from_user.id)
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
            update.message.reply_text("Пожалуйста, введи корректный диапазон в формате: 20-30")
            return EDIT_FIELD

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

    if user_id not in reviews:
        reviews[user_id] = []
    reviews[user_id].append({'from_id': from_id, 'text': text})

    update.message.reply_text("Спасибо! Ваш отзыв сохранён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def show_reviews(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_reviews = reviews.get(user_id, [])
    if not user_reviews:
        update.message.reply_text("О вас ещё нет отзывов.")
        return

    texts = []
    for i, rev in enumerate(user_reviews, 1):
        from_user = find_user_by_id(rev['from_id'])
        from_name = from_user.get('username', f"Пользователь {rev['from_id']}") if from_user else f"Пользователь {rev['from_id']}"
        texts.append(f"{i}. От {from_name}: {rev['text']}")
    update.message.reply_text("\n\n".join(texts))


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Отменено.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main(): 
    TOKEN = 'ВАШ_ТОКЕН_ЗДЕСЬ'  # Вставьте сюда токен вашего бота

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Создание анкеты
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_GENDER: [MessageHandler(Filters.text & ~Filters.command, choose_gender)],
            ENTER_AGE: [MessageHandler(Filters.text & ~Filters.command, enter_age)],
            ENTER_ABOUT: [MessageHandler(Filters.text & ~Filters.command, enter_about)],
            CHOOSE_TARGET_GENDER: [MessageHandler(Filters.text & ~Filters.command, choose_target_gender)],
            ENTER_AGE_RANGE: [MessageHandler(Filters.text & ~Filters.command, enter_age_range)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Редактирование профиля
    edit_conv = ConversationHandler(
        entry_points=[CommandHandler('edit', edit)],
        states={
            EDIT_CHOOSE_FIELD: [MessageHandler(Filters.text & ~Filters.command, edit_choose_field)],
            EDIT_FIELD: [MessageHandler(Filters.text & ~Filters.command, edit_field)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Оставление отзыва
    review_conv = ConversationHandler(
        entry_points=[CommandHandler('review', review_start)],
        states={
            REVIEW_ENTER_TARGET: [MessageHandler(Filters.text & ~Filters.command, review_enter_target)],
            REVIEW_ENTER_TEXT: [MessageHandler(Filters.text & ~Filters.command, review_enter_text)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(edit_conv)
    dp.add_handler(review_conv)
    dp.add_handler(CommandHandler('search', search))
    dp.add_handler(CommandHandler('showreviews', show_reviews))
    dp.add_handler(CommandHandler('cancel', cancel))
    dp.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен...")
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
