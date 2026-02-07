import logging
import re
from telegram import Update, Poll
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from typing import Final
from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN: Final[str] = ''
try:
    with open('token.txt') as f:
        TOKEN = f.read().strip()
    if not TOKEN or len(TOKEN) < 30:
        raise ValueError("Неверный формат токена")
    logger.info("✅ Токен загружен")
except (FileNotFoundError, ValueError) as e:
    logger.error(f"❌ Ошибка токена: {e}")
    exit(1)

tz_moscow = ZoneInfo('Europe/Moscow')


async def send_test_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"Тест от chat_id: {chat_id}")
    await context.bot.send_message(chat_id=chat_id, text="✅ Тест работает!")


async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    jobs = context.job_queue.get_jobs_by_name(f"{chat_id}-daily-poll")

    if not jobs:
        await update.message.reply_text("📭 Опросы не запланированы.")
        return

    now_msk = datetime.now(tz_moscow)
    message_parts = []

    for job in jobs:
        user_time = job.data.get('user_time', 'Неизвестно') if job.data else 'Неизвестно'
        next_run = job.next_run_time

        if next_run:
            next_msk = next_run.astimezone(tz_moscow)
            delta = next_msk - now_msk
            days = delta.days
            hours = int(delta.total_seconds() / 3600) % 24
            message_parts.append(
                f"• **{user_time} MSK**\n   ⏰ {next_msk.strftime('%H:%M %d.%m.%Y')}\n   ⏳ Через: {days}д {hours}ч")
        else:
            message_parts.append(f"• **{user_time} MSK**")

    await update.message.reply_text("📋 Ваши опросы:\n\n" + "\n".join(message_parts))


async def stop_polls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    jobs = context.job_queue.get_jobs_by_name(f"{chat_id}-daily-poll")
    removed = 0
    for job in jobs:
        job.schedule_removal()
        removed += 1

    status = f"🛑 Отменено {removed} опросов." if removed else "ℹ️ Опросы не найдены."
    await update.message.reply_text(status)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 **Помощь по боту 🏰**

🕐 **Настройка времени:**
• `/time_12:00` — опрос в 12:00 MSK
• `/time_18:30` — опрос в 18:30 MSK

📋 **Команды:**
• `/help` — эта справка
• `/time` — примеры времени
• `/jobs` — список опросов
• `/stop` — отменить все
• `/test` — тест бота
• `/start` — приветствие

✅ **Формат:** ЧЧ:ММ (00:00–23:59) MSK
    """
    await update.message.reply_text(help_text)


async def time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает /time и /time_ЧЧ:ММ"""
    chat_id = update.effective_chat.id
    command = update.message.text.strip()

    logger.info(f"Команда времени '{command}' от chat_id: {chat_id}")

    # /time — помощь
    if command == '/time':
        await update.message.reply_text(
            "🕐 **Установите время:**\n\n"
            "• `/time_12:00`\n"
            "• `/time_18:30`\n"
            "• `/time_09:15`\n\n"
            "✅ 00:00–23:59 MSK"
        )
        return

    # /time_ЧЧ:ММ
    time_match = re.match(r'/time_(\d{2}:\d{2})', command)
    if not time_match:
        await update.message.reply_text("❌ Формат: `/time_ЧЧ:ММ`\n📋 `/help`")
        return

    user_time_str = time_match.group(1)
    logger.info(f"✅ Время извлечено: {user_time_str}")

    try:
        hour, minute = map(int, user_time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Неверное время")

        # Удаляем старые задания
        current_jobs = context.job_queue.get_jobs_by_name(f"{chat_id}-daily-poll")
        for job in current_jobs:
            job.schedule_removal()

        # Конвертируем MSK → UTC
        now_msk = datetime.now(tz_moscow)
        msk_datetime = datetime.combine(now_msk.date(), time(hour, minute), tzinfo=tz_moscow)
        utc_datetime = msk_datetime.astimezone(timezone.utc)

        # Первый запуск
        now_utc = datetime.now(timezone.utc)
        next_run_utc = datetime.combine(now_utc.date(), utc_datetime.time(), tzinfo=timezone.utc)
        if next_run_utc <= now_utc:
            next_run_utc += timedelta(days=1)

        # Запускаем задание
        context.job_queue.run_repeating(
            send_poll,
            interval=timedelta(days=1),
            first=next_run_utc - now_utc,
            chat_id=chat_id,
            name=f"{chat_id}-daily-poll",
            data={'user_time': user_time_str}
        )

        # Проверяем
        new_jobs = context.job_queue.get_jobs_by_name(f"{chat_id}-daily-poll")
        if new_jobs:
            await update.message.reply_text(
                f"✅ **Опрос на {user_time_str} MSK** 🏰\n"
                f"📅 Первая отправка: **{msk_datetime.strftime('%H:%M %d.%m.%Y')}**\n"
                f"📋 `/jobs` — проверить"
            )
            logger.info(f"✅ Задание создано для {chat_id}")
        else:
            await update.message.reply_text("❌ Ошибка планирования!")

    except ValueError:
        await update.message.reply_text("❌ Время: **00:00–23:59**\n📋 `/help`")


async def send_poll(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    question = " **Ежедневный опрос 🏰**\nКакое настроение сегодня?"
    options = ["😊 Отличное!", "🙂 Хорошее", "😐 Так себе", "😔 Плохое"]

    try:
        await context.bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            type=Poll.REGULAR,
            is_anonymous=False,
        )
        logger.info(f"✅ Опрос отправлен: {chat_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка опроса {chat_id}: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 **Бот опросов 🏰**\n\n"
        "🕐 `/time_12:00` — настроить опрос\n\n"
        "📋 **Команды:**\n"
        "• `/help` — справка\n"
        "• `/time` — помощь\n"
        "• `/jobs` — статус\n"
        "• `/stop` — отменить"
    )


def main():
    app = Application.builder().token(TOKEN).build()

    # ✅ НОВЫЙ обработчик для /time и /time_ЧЧ:ММ
    app.add_handler(MessageHandler(filters.Regex(r'^/time(_\d{2}:\d{2})?$'), time_handler))

    # Остальные команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("jobs", list_jobs))
    app.add_handler(CommandHandler("stop", stop_polls))
    app.add_handler(CommandHandler("test", send_test_message))

    logger.info("🚀 Бот запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
