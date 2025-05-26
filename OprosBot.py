import telebot
import datetime
from telegram import Update, Poll
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

# Ваш токен бота
TOKEN = ''
TOKEN = None
with open('token.txt') as f:
    TOKEN = f.read().strip()
# bot = telebot.TeleBot(TOKEN)
TIME_INPUT = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я буду отправлять опросы в заданное время.\n"
        "Пожалуйста, введи время напоминания в формате ГГГГ-ММ-ДД ЧЧ:ММ (например, 2025-05-24 15:30):"
    )
    chat_id = update.effective_chat.id
    print(chat_id)
    # ждем ввода от пользователя
    return TIME_INPUT
    print(TIME_INPUT)




# обрабатывает ответ пользователя, содержащий дату и время.Обработчик ввода времени
async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # получает текст, отправленный пользователем
    user_input = update.message.text
    print(user_input)
    chat_id = update.effective_chat.id
    print(chat_id)

    try:
        # Parse user input datetime
        reminder_time = datetime.datetime.strptime(user_input, "%Y-%m-%d %H:%M")

        now = datetime.datetime.now()
        delay = (reminder_time - now).total_seconds()

        if delay <= 0:
            await update.message.reply_text("Время должно быть в будущем./n"
                                            " Попробуй ещё раз.")
            return TIME_INPUT

        # Schedule poll sending
        # Если задержка допустима (будущее время), он планирует send_pollвыполнение
        # функции один раз после задержки, используя:
        context.job_queue.run_once(send_poll, delay, chat_id=chat_id)

        await update.message.reply_text(f"Отлично! Опрос будет отправлен в {reminder_time}.")
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, введи время в формате ГГГГ-ММ-ДД ЧЧ:ММ."
        )
        return TIME_INPUT
        print(TIME_INPUT)


# Функция для создания опроса
# async def send_poll(context: ContextTypes.DEFAULT_TYPE):
#     chat_id = context.job.chat_id
#     print(chat_id)
#     question = "Какой ваш любимый язык программирования?"
#     options = ["Python", "JavaScript", "C++", "Java", "Другой"]
#     await context.bot.send_poll(
#         chat_id=chat_id,
#         question=question,
#         options=options,
#         is_anonymous=False,
#         allows_multiple_answers=False,
#     )
async def send_poll(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    print(job)
    chat_id = job.chat_id
    print(chat_id)

    question = "Ежедневный опрос: Как ваше настроение сегодня?"
    options = ["Отлично", "Хорошо", "Нормально", "Плохо"]

    await context.bot.send_poll(
        chat_id=chat_id,
        question=question,
        options=options,
        is_anonymous=False,
    )



def main():
    # Replace 'YOUR_BOT_TOKEN_HERE' with your actual bot token
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TIME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time)],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()


# функция вызывается очередью заданий при наступлении запланированного времени
# async def send_poll(context: ContextTypes.DEFAULT_TYPE):
#     job = context.job
#     указывает чат, куда следует отправить опро
# chat_id = job.chat_id
# Here you implement sending your poll
# await context.bot.send_poll(
#     chat_id=chat_id,
#     question="Ваш вопрос?",
#     options=["Вариант 1", "Вариант 2", "Вариант 3"],
#     is_anonymous=False,
# )


# Команда /start для запуска бота и планирования опроса
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     chat_id = update.effective_chat.id
#     await update.message.reply_text("Привет! Я буду отправлять опросы в заданное время.")
#     await update.message.reply_text("Введи время напоминания.")


# Планируем опрос через 10 секунд после команды /start (пример)
# scheduler = context.job_queue
# Добавляем задачу в очередь
# scheduler.run_once(send_poll, when=2, chat_id=chat_id)

# Основная функция запуска бота
# def main():
#     application = ApplicationBuilder().token(TOKEN).build()
#
#     application.add_handler(CommandHandler("start", start))
#
#     print("Бот запущен...")
#     application.run_polling()
#
#
# if __name__ == '__main__':
#     asyncio.run(main())
# bot.polling(none_stop=True)
