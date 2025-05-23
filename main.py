import telebot
import g4f
from telebot import types
import threading
import time

TELEGRAM_BOT_TOKEN = '7946963630:AAGygp6dxRM285VRmR6AHKua0myBsQ5QwVs'
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

providers = [prov for prov in g4f.Provider.__dict__.values() if callable(prov)]

chat_histories = {}
chat_styles = {}

DEFAULT_STYLE = (
    "Ты дружелюбный, вежливый и краткий помощник. "
    "Отвечай простым языком, добавляй эмодзи и юмор, если это уместно."
)

# Задаём chat_id, в который бот будет отправлять пинги
PING_CHAT_ID = 123456789  # <-- сюда вставь свой чат ID

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=3)

    btn1 = types.InlineKeyboardButton("📢 Канал", url="https://t.me/твой_канал")
    btn2 = types.InlineKeyboardButton("🛠 Поддержка", url="https://t.me/твой_чат_поддержки")
    btn3 = types.InlineKeyboardButton("💰 Донатик", url="https://t.me/ссылка_на_донат")

    markup.add(btn1, btn2, btn3)

    text = ("Приветствую тебя, друг! 👋\n\n"
            "Я твой дружелюбный GPT-бот 🤖\n"
            "Задавай вопросы и получай ответы быстро и легко!\n\n"
            "Ниже полезные ссылки для тебя:\n"
            "Чтобы задать стиль общения, напиши команду:\n"
            "/style <текст_стиля>\n\n"
            "Пример:\n"
            "/style Отвечай как пират с кучей эмодзи ☠️🏴‍☠️")
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['style'])
def set_style(message):
    user_id = message.chat.id
    style_text = message.text[len('/style '):].strip()

    if not style_text:
        bot.reply_to(message, "⚠️ Пожалуйста, укажи стиль после команды /style")
        return

    chat_styles[user_id] = style_text
    bot.reply_to(message, f"✅ Стиль общения установлен:\n\n{style_text}")

@bot.message_handler(func=lambda message: True)
def reply(message):
    user_id = message.chat.id
    question = message.text

    if user_id not in chat_histories:
        chat_histories[user_id] = []

    chat_histories[user_id].append({"role": "user", "content": question})

    # Храним последние 20 сообщений
    if len(chat_histories[user_id]) > 20:
        chat_histories[user_id] = chat_histories[user_id][-20:]

    bot.send_chat_action(user_id, 'typing')
    thinking = bot.reply_to(message, "🤔 Думаю над ответом...")

    style_text = chat_styles.get(user_id, DEFAULT_STYLE)
    system_message = {"role": "system", "content": style_text}

    for provider in providers:
        try:
            response = g4f.ChatCompletion.create(model="gpt-3.5-turbo",
                                                 provider=provider,
                                                 messages=[system_message] + chat_histories[user_id])

            reply_text = str(response)

            # Убираем лишний текст об улучшении языковых навыков
            if "I am still improving my command" in reply_text:
                reply_text = reply_text.split("I am still improving my command")[0].strip()

            # Убираем лишние вопросительные знаки (по желанию, можно убрать или доработать)
            reply_text = reply_text.replace('??', '').replace(' ?', '').strip()

            if "limit" in reply_text.lower():
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=thinking.message_id,
                    text="⏳ Мой лимит исчерпан, попробуй через 15 минут.")
                return

            if len(reply_text) > 4000:
                reply_text = reply_text[:3990] + "..."

            chat_histories[user_id].append({
                "role": "assistant",
                "content": reply_text
            })

            bot.edit_message_text(chat_id=user_id,
                                  message_id=thinking.message_id,
                                  text=f"🤖 {reply_text}")
            return

        except Exception as e:
            print(f"❌ Провайдер {provider.__name__} не сработал: {e}")
            continue

    bot.edit_message_text(chat_id=user_id,
                          message_id=thinking.message_id,
                          text="⚠️ Все провайдеры недоступны. Попробуй позже.")

def ping_bot():
    while True:
        try:
            bot.send_message(PING_CHAT_ID, "⏰ Пинг, чтобы бот не спал!")
        except Exception as e:
            print(f"Ошибка при пинге: {e}")
        time.sleep(300)  # ждем 5 минут

if __name__ == '__main__':
    # Запускаем функцию пинга в отдельном потоке, чтобы не блокировать бота
    threading.Thread(target=ping_bot, daemon=True).start()

    print("✅ Бот запущен!")
    bot.infinity_polling()
