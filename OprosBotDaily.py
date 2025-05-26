import logging
import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# Включаем логирование
# logging.basicConfig(
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# Ваш токен бота
TOKEN = ''
TOKEN = None
with open('token.txt') as f:
    TOKEN = f.read().strip()

TIME_INPUT = 1  # Состояние для ConversationHandler


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я буду отправлять опросы в заданное время.\n"
        "Пожалуйста, введи время напоминания в формате ЧЧ:ММ (например, 15:30):"
    )
    chat_id = update.effective_chat.id
    print(chat_id)
    return TIME_INPUT


async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    print(user_input)
    chat_id = update.effective_chat.id

    try:
        # Парсим только время
        reminder_time = datetime.datetime.strptime(user_input, "%H:%M").time()
    except ValueError:
        await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, введи время в формате ЧЧ:ММ."
        )
        return TIME_INPUT

    # Отменяем предыдущую задачу для этого чата, если есть
    # current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    # for job in current_jobs:
    #     job.schedule_removal()

    # Планируем ежедневный опрос в заданное время
    context.job_queue.run_daily(
        send_poll,
        time=reminder_time,
        days=(0, 1, 2, 3, 4, 5, 6),  # Каждый день недели
        chat_id=chat_id,
        name=str(chat_id),  # Имя задачи — chat_id для удобства управления
    )

    await update.message.reply_text(f"Отлично! Опрос будет отправляться ежедневно в {user_input}.")

    return ConversationHandler.END


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


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена. Если хочешь, можешь задать время опроса заново командой /start.")
    return ConversationHandler.END


def main():
    # TOKEN = TOKEN  # Замените на токен вашего бота

    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TIME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Запускаем бота
    application.run_polling()


if __name__ == "__main__":
    main()
