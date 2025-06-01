import logging
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from datetime import datetime, time, timezone, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open('token.txt') as f:
    TOKEN = f.read().strip()

# Московское время +5 часов (укажите нужный вам часовой пояс)
tz_moscow = timezone(timedelta(hours=5))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Command /start received")
    await update.message.reply_text(
        "Добро пожаловать!\n\n"
        "Напишите время в формате ЧЧ:ММ, чтобы настроить ежедневный опрос.\n"
        "Например:\n"
        "/start - показать инструкцию\n"
        "/help - показать меню команд\n"
        "18:30 - установить опрос на 18:30 ежедневно."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Список доступных команд:\n"
        "/start - Запустить бота и получить инструкцию\n"
        "/help - Показать это сообщение\n"
        "/jobs - Показать список запланированных опросов\n"
        "/test - Отправить тестовое сообщение\n\n"
        "Чтобы настроить ежедневный опрос, просто отправьте время в формате ЧЧ:ММ, например, 18:30."
    )
    await update.message.reply_text(help_text)


async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.jobs()
    if not jobs:
        await update.message.reply_text("Список заданий пуст.")
        return

    message = []
    for job in jobs:
        next_run = job.next_run_time
        if next_run:
            next_run_local = next_run.astimezone(tz_moscow)
            next_run_str = next_run_local.strftime("%Y-%m-%d %H:%M:%S")
        else:
            next_run_str = "неизвестно"
        message.append(f"- Название: {job.name}, Следующее выполнение: {next_run_str}, Частота: Ежедневно")

    await update.message.reply_text("\n".join(message))


async def send_test_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Тестовая отправка.")


async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    chat_id = update.effective_chat.id
    logger.info(f"User input time: {user_input} from chat {chat_id}")

    try:
        # Парсим время в формате ЧЧ:ММ
        reminder_time = datetime.strptime(user_input, "%H:%M").time()
        # Добавляем таймзону
        reminder_time = reminder_time.replace(tzinfo=tz_moscow)
    except ValueError:
        await update.message.reply_text("Неправильный формат времени. Используйте формат ЧЧ:ММ (например, 18:30).")
        return

    # Отменяем старые задачи с таким именем
    current_jobs = context.job_queue.get_jobs_by_name(f"{chat_id}-daily-poll")
    for job in current_jobs:
        job.schedule_removal()

    # Запускаем ежедневный опрос в указанное время
    context.job_queue.run_daily(
        send_poll,
        time=reminder_time,
        days=tuple(range(7)),  # Каждый день недели
        chat_id=chat_id,
        name=f"{chat_id}-daily-poll",
    )

    await update.message.reply_text(f"Опрос успешно настроен на ежедневную отправку в {user_input} (МСК).")


async def send_poll(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    question = "Ежедневный опрос: Какое у вас сегодня настроение?"
    options = ["Отличное", "Хорошее", "Так себе", "Плохое"]

    try:
        await context.bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=True,
        )
        logger.info(f"Poll sent to chat {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке опроса: {e}")


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("jobs", list_jobs))
    app.add_handler(CommandHandler("test", send_test_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time))

    logger.info("Bot started polling бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
