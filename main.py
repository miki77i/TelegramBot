import telebot
from telebot import types
import json
import os
import random


bot = telebot.TeleBot("8121277507:AAEvqSpC30D6kQzU1-ACkDgJ5FLomy7DKnc")

#настройки
DATA_FILE = 'users_data.json'

#загрузка данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": {}, "pairs": {}}

#сохранение данных
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


#кнопки для указания пола
gender_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
gender_markup.add("Мужской", "Женский")

#кнопки для указания типа знакомства
goal_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
goal_markup.add("Дружба", "Отношения", "Общение")

#/start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "Привет! Я бот для знакомств.\n"
        "Создай анкету: /create_profile\n"
        "Найди пару: /find")

#анкета
@bot.message_handler(commands=['create_profile'])
def create_profile(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id in data["users"]:
        bot.send_message(message.chat.id, "У тебя уже есть анкета! Посмотреть: /my_profile")
        return
    
    msg = bot.send_message(message.chat.id, 
        "Создаем анкету\n"
        "Как тебя зовут и сколько тебе лет?\n"
        "Формат: Имя, Возраст\n"
        "Пример: Анна, 25",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_name_age)

def process_name_age(message):
    try:
        name, age = message.text.split(', ')
        if not name or not age.isdigit():
            raise ValueError
        
        chat_id = message.chat.id
        bot.send_message(chat_id, "Выбери пол:", reply_markup=gender_markup)
        bot.register_next_step_handler(message, process_gender, name, age)
    except:
        bot.send_message(message.chat.id, "Неправильный формат! Попробуй еще раз: /create_profile")

def process_gender(message, name, age):
    if message.text not in ["Мужской", "Женский"]:
        bot.send_message(message.chat.id, "Пожалуйста, выбери пол из кнопок!")
        return
    
    chat_id = message.chat.id
    bot.send_message(chat_id, "Из какого ты города?", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_city, name, age, message.text)

def process_city(message, name, age, gender):
    city = message.text
    chat_id = message.chat.id
    bot.send_message(chat_id, 
        "Расскажи о себе:")
    bot.register_next_step_handler(message, process_bio, name, age, gender, city)

def process_bio(message, name, age, gender, city):
    bio = message.text
    chat_id = message.chat.id
    bot.send_message(chat_id, "Что ты ищешь?", reply_markup=goal_markup)
    bot.register_next_step_handler(message, process_goal, name, age, gender, city, bio)

def process_goal(message, name, age, gender, city, bio):
    if message.text not in ["Дружба", "Отношения", "Общение"]:
        bot.send_message(message.chat.id, "Пожалуйста, выбери из предложенных вариантов!")
        return
    
    chat_id = message.chat.id
    bot.send_message(chat_id, "Пришли свое фото", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_photo, name, age, gender, city, bio, message.text)

def process_photo(message, name, age, gender, city, bio, goal):
    if not message.photo:
        bot.send_message(message.chat.id, "Это не фото! Попробуй еще раз: /create_profile")
        return
    
    photo_id = message.photo[-1].file_id
    user_id = str(message.from_user.id)
    
#сохраняем анкету
    data = load_data()
    data["users"][user_id] = {
        "name": name,
        "age": age,
        "gender": gender,
        "city": city,
        "bio": bio,
        "goal": goal,
        "photo": photo_id,
        "likes": 0,
        "matches": []
    }
    save_data(data)
    

    bot.send_photo(message.chat.id, photo_id,
        caption=f"🎉 Анкета создана!\n\n"
                f"{name}, {age} лет\n"
                f"{gender}, {city}\n\n"
                f"{bio}\n\n"
                f"Ищет: {goal}")


@bot.message_handler(commands=['my_profile'])
def show_profile(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data["users"]:
        bot.send_message(message.chat.id, "У тебя нет анкеты. Создай: /create_profile")
        return
    
    profile = data["users"][user_id]
    bot.send_photo(message.chat.id, profile["photo"],
        caption=f"{profile['name']}, {profile['age']} лет\n"
                f"{profile['gender']}, {profile['city']}\n\n"
                f"{profile['bio']}\n\n"
                f"Лайков: {profile['likes']}\n"
                f"Взаимность: {len(profile['matches'])}\n"
                f"Ищет: {profile['goal']}")

# Поиск
@bot.message_handler(commands=['find'])
def find_pair(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data["users"]:
        bot.send_message(message.chat.id, "Сначала создай анкету: /create_profile")
        return
    
    viewed = data["pairs"].get(user_id, []) + [user_id]
    available = [uid for uid in data["users"] if uid not in viewed]
    
    if not available:
        bot.send_message(message.chat.id, "Пока нет новых анкет. Попробуй позже!")
        return
    
    partner_id = random.choice(available)
    partner = data["users"][partner_id]
    

    if user_id not in data["pairs"]:
        data["pairs"][user_id] = []
    data["pairs"][user_id].append(partner_id)
    save_data(data)
    
    #кнопки
    markup = types.InlineKeyboardMarkup()
    like_btn = types.InlineKeyboardButton("Лайк", callback_data=f"like_{partner_id}")
    skip_btn = types.InlineKeyboardButton("Пропустить", callback_data=f"skip_{partner_id}")
    markup.add(like_btn, skip_btn)
    
    bot.send_photo(message.chat.id, partner["photo"],
        caption=f"{partner['name']}, {partner['age']} лет\n"
                f"{partner['gender']}, {partner['city']}\n\n"
                f"{partner['bio']}\n\n"
                f"Ищет: {partner['goal']}",
        reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith(('like_', 'skip_')))
def handle_callback(call):
    user_id = str(call.from_user.id)
    partner_id = call.data.split('_')[1]
    data = load_data()
    
    if call.data.startswith('like_'):

        data["users"][partner_id]["likes"] += 1
        

        if user_id in data["users"][partner_id].get("liked_by", []):


            data["users"][user_id]["matches"].append(partner_id)
            data["users"][partner_id]["matches"].append(user_id)
            
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="Это взаимно! Вы понравились друг другу!")
            

            partner = data["users"][partner_id]
            bot.send_message(
                partner_id,
                f"вы ответили взаимностью с {data['users'][user_id]['name']}!\n"
                f"Напиши привет: @{call.from_user.username}" if call.from_user.username else "")
        else:

            if "liked_by" not in data["users"][partner_id]:
                data["users"][partner_id]["liked_by"] = []
            data["users"][partner_id]["liked_by"].append(user_id)
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="Твой лайк отправлен!")
    
    elif call.data.startswith('skip_'):
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="Анкета пропущена")
    
    save_data(data)



if __name__ == '__main__':
    print("Бот запущен!")
    bot.infinity_polling()

# @bot.message_handler(commands=["start_chat"])
# def