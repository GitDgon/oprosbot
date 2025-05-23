import telebot
from telegram import Update, Poll
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# Ваш токен бота
TOKEN = ''
TOKEN = None
with open('token.txt') as f:
    TOKEN = f.read().strip()
#bot = telebot.TeleBot(TOKEN)


# Функция для создания опроса
async def send_poll(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    question = "Какой ваш любимый язык программирования?"
    options = ["Python", "JavaScript", "C++", "Java", "Другой"]
    await context.bot.send_poll(
        chat_id=chat_id,
        question=question,
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False,
    )

# Команда /start для запуска бота и планирования опроса
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("Привет! Я буду отправлять опросы в заданное время.")

    # Планируем опрос через 10 секунд после команды /start (пример)
    scheduler = context.job_queue
    # Добавляем задачу в очередь
    scheduler.run_once(send_poll, when=2, chat_id=chat_id)

# Основная функция запуска бота
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
#bot.polling(none_stop=True)