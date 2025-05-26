import logging
from telegram import Update, Poll
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters, JobQueue
from typing import Final
from datetime import datetime, time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TIME_INPUT = range(1)

TOKEN = ''
TOKEN = None
with open('token.txt') as f:
    TOKEN = f.read().strip()



async def send_test_message(update: object, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    print(user_input)
    chat_id = update.effective_chat.id
    print(chat_id)

    await context.bot.send_message(chat_id=chat_id, text="Тестовая отправка.")



async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /start: Приветствие пользователя и инструкция по использованию бота.
    """
    logger.info("Command /start UP")
    await update.message.reply_text(
        "Добро пожаловать!\n\n"
        "Напишите время в формате ЧЧ:ММ, чтобы настроить ежедневный опрос.\n"
        "Например:\n"
        "/start - показать инструкцию\n"
        "18:30 - установить опрос на 18:30 ежедневно."
    )

async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Прием времени от пользователя и настройка ежедневного опроса.
    """
    user_input = update.message.text.strip()
    print(user_input)
    chat_id = update.effective_chat.id
    print(chat_id)
    print(f"User Input: {user_input}, Chat ID: {chat_id}")

    try:
        # Текущее время сервера
        current_time = datetime.now().strftime("%H:%M")
        await update.message.reply_text(f"Текущее время: {current_time}\n")

        # Парсим только время в формате ЧЧ:ММ
        reminder_time = datetime.strptime(user_input, "%H:%M").time()
    except ValueError:
        await update.message.reply_text("Неправильный формат времени. Используйте формат ЧЧ:ММ (например, 18:30)")
        return TIME_INPUT

    # Ставим ежедневный опрос в заданное время
    context.job_queue.run_daily(
        send_poll,
        time=reminder_time,
        days=(0, 1, 2, 3, 4, 5, 6),
        chat_id=chat_id,
        name=f"{chat_id}-daily-poll",
    )

    await update.message.reply_text(f"Опрос успешно настроен на ежедневную отправку в {user_input}.")
    print(chat_id)
    return None  # Завершаем диалог

async def send_poll(context: ContextTypes.DEFAULT_TYPE):
    """
    Отправка ежедневного опроса.
    """
    chat_id = context.job.chat_id
    question = "Ежедневный опрос: Какое у вас сегодня настроение?"
    options = ["Отличное", "Хорошее", "Так себе", "Плохое"]

    try:
        await context.bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            type=Poll.REGULAR,
            is_anonymous=True,
        )
    except Exception as e:
        print(f"Ошибка при отправке опроса: {e}")  # Выведем ошибку в консоль)

def main():
    app = Application.builder().token(TOKEN).build()

    # Хэндлеры
    test_handler = CommandHandler("test", send_test_message)
    app.add_handler(test_handler)
    app.add_handler(CommandHandler("start", start_command))  # Добавили команду /start
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time))

    # Запускаем приложение
    app.run_polling()

if __name__ == '__main__':
    main()