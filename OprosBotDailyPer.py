import logging
from telegram import Update, Poll
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from typing import Final
# from datetime import datetime, time, timedelta
from datetime import datetime, time, timezone, timedelta

from zoneinfo import ZoneInfo

# Настройка структурированного логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN: Final[str] = ''
try:
    with open('token.txt') as f:
        TOKEN = f.read().strip()
    logger.info("Токен бота успешно загружен")
except FileNotFoundError:
    logger.error("Файл token.txt не найден!")
    exit(1)

tz_moscow = ZoneInfo('Europe/Moscow')


async def send_test_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для отладки"""
    chat_id = update.effective_chat.id
    logger.info(f"Тестовая команда от chat_id: {chat_id}")
    await context.bot.send_message(chat_id=chat_id, text="✅ Тестовая отправка работает!")


async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.jobs()
    if not jobs:
        await update.message.reply_text("📭 Список заданий пуст.")
        return

    message = []
    for job in jobs:
        if "daily-poll" in job.name:
            user_time = job.data.get('user_time', 'Неизвестно') if job.data else 'Неизвестно'
            next_run = job.next_run_time.astimezone(tz_moscow).strftime(
                '%H:%M %d.%m.%Y') if job.next_run_time else 'Неизвестно'
            message.append(f"• **{user_time} MSK** (запуск: {next_run})")

    await update.message.reply_text("📋 Запланированные опросы:\n" + "\n".join(message))



# async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     jobs = context.job_queue.jobs()
#     if not jobs:
#         await update.message.reply_text("📭 Список заданий пуст.")
#         return
#
#     message = []
#     for job in jobs:
#         chat_id = job.chat_id or "Неизвестно"
#         # ✅ Извлекаем время опроса из имени или данных
#         if "daily-poll" in job.name:
#             # Время пользователя хранится в job.callback_kwargs или нужно парсить
#             next_run_msk = job.next_run_time.astimezone(tz_moscow).strftime('%H:%M')
#             message.append(
#                 f"• **{chat_id}-daily-poll**: запуск **{next_run_msk} MSK** ({job.next_run_time.astimezone(tz_moscow).strftime('%d.%m.%Y')})")
#
#     await update.message.reply_text("📋 Запланированные опросы:\n" + "\n".join(message))
#

# async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Показать все запланированные задания"""
#     jobs = context.job_queue.jobs()
#     if not jobs:
#         await update.message.reply_text("📭 Список заданий пуст.")
#         return
#
#     message = []
#     for job in jobs:
#         next_run = job.next_run_time.astimezone(tz_moscow) if job.next_run_time else "Не задано"
#         message.append(f"• {job.name}: {next_run.strftime('%H:%M %d.%m.%Y')} (ежедневно)")
#
#     await update.message.reply_text("📋 Запланированные опросы:\n" + "\n".join(message))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и инструкции"""
    logger.info(f"Команда /start от пользователя {update.effective_user.id}")
    await update.message.reply_text(
        "🎉 Добро пожаловать в бот ежедневных опросов!\n\n"
        "📝 **Как использовать:**\n"
        "• Напишите время в формате **ЧЧ:ММ** (например: 18:30)\n"
        "• Бот настроит ежедневный опрос в это время\n\n"
        "📋 **Команды:**\n"
        "/jobs — показать запланированные опросы\n"
        "/test — тестовая отправка"
    )


async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    chat_id = update.effective_chat.id
    logger.info(f"Ввод времени '{user_input}' от chat_id: {chat_id}")

    try:
        # Парсим время пользователя (MSK)
        msk_time = datetime.strptime(user_input, "%H:%M").time()

        # Конвертируем MSK → UTC для Telegram
        now_msk = datetime.now(tz_moscow)
        msk_datetime = datetime.combine(now_msk.date(), msk_time, tzinfo=tz_moscow)
        utc_datetime = msk_datetime.astimezone(timezone.utc)
        utc_time = utc_datetime.time()

        # Первый запуск
        now_utc = datetime.now(timezone.utc)
        next_run_utc = datetime.combine(now_utc.date(), utc_time, tzinfo=timezone.utc)
        if next_run_utc <= now_utc:
            next_run_utc += timedelta(days=1)

        # Удаляем старые задания
        current_jobs = context.job_queue.get_jobs_by_name(f"{chat_id}-daily-poll")
        for job in current_jobs:
            job.schedule_removal()

        # Запускаем ежедневно в UTC (что = MSK время пользователя)
        context.job_queue.run_repeating(
            send_poll,
            interval=timedelta(days=1),
            first=next_run_utc - now_utc,
            chat_id=chat_id,
            name=f"{chat_id}-daily-poll",
            data={'user_time': user_input}
        )

        logger.info(f"Опрос {chat_id}: MSK {user_input} → UTC {utc_time}")
        await update.message.reply_text(
            f"✅ Опрос настроен на **{user_input} MSK** ежедневно!\n"
            f"📅 Первая отправка: **{msk_datetime.strftime('%H:%M %d.%m.%Y')}**"
        )

    except ValueError:
        await update.message.reply_text("❌ Формат: **ЧЧ:ММ** (09:23)")


# async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_input = update.message.text.strip()
#     chat_id = update.effective_chat.id
#     logger.info(f"Ввод времени '{user_input}' от chat_id: {chat_id}")
#
#     try:
#         # ✅ ПАРСИМ время как MSK (не UTC!)
#         reminder_time = datetime.strptime(user_input, "%H:%M").time()
#
#         # ✅ Текущее время ВСЕГДА в MSK
#         now = datetime.now(tz_moscow)
#         next_run_at = datetime.combine(now.date(), reminder_time, tzinfo=tz_moscow)
#
#         if next_run_at <= now:
#             next_run_at += timedelta(days=1)
#
#         # ✅ Удаляем старые задания
#         current_jobs = context.job_queue.get_jobs_by_name(f"{chat_id}-daily-poll")
#         for job in current_jobs:
#             job.schedule_removal()
#
#         # ✅ run_daily с правильным временем MSK
#         context.job_queue.run_daily(
#             send_poll,
#             time=reminder_time,  # Это время пользователя (MSK)
#             days=(0, 1, 2, 3, 4, 5, 6),
#             chat_id=chat_id,
#             name=f"{chat_id}-daily-poll",
#         )
#
#         logger.info(f"Опрос запланирован для {chat_id} на MSK {reminder_time}")
#         await update.message.reply_text(
#             f"✅ Опрос настроен на **{user_input} MSK** ежедневно!\n"
#             f"📅 Первая отправка: **{next_run_at.astimezone(tz_moscow).strftime('%H:%M %d.%m.%Y')}**"
#         )
#
#     except ValueError:
#         await update.message.reply_text("❌ Используйте формат **ЧЧ:ММ** (19:18)")


# async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Обработка ввода времени и планирование опроса"""
#     user_input = update.message.text.strip()
#     chat_id = update.effective_chat.id
#     logger.info(f"Ввод времени '{user_input}' от chat_id: {chat_id}")
#
#     try:
#         # Парсинг времени
#         reminder_time = datetime.strptime(user_input, "%H:%M").time()
#
#         # Расчёт времени следующего запуска
#         now = datetime.now(tz_moscow)
#         next_run_at = datetime.combine(now.date(), reminder_time, tzinfo=tz_moscow)
#         if next_run_at <= now:
#             next_run_at += timedelta(days=1)
#
#         # Удаляем старое задание для этого чата
#         current_jobs = context.job_queue.get_jobs_by_name(f"{chat_id}-daily-poll")
#         for job in current_jobs:
#             job.schedule_removal()
#
#         # Планируем новое ежедневное задание
#         context.job_queue.run_daily(
#             send_poll,
#             time=reminder_time,
#             days=(0, 1, 2, 3, 4, 5, 6),  # Все дни недели
#             chat_id=chat_id,
#             name=f"{chat_id}-daily-poll",
#         )
#
#         logger.info(f"Ежедневный опрос запланирован для чата {chat_id} на {reminder_time}")
#         await update.message.reply_text(
#             f"✅ **Опрос настроен!**\n"
#             f"⏰ Время: **{user_input}** (ежедневно)\n"
#             f"📅 Первая отправка: **{next_run_at.astimezone(tz_moscow).strftime('%H:%M %d.%m.%Y')}**"
#         )
#
#     except ValueError:
#         logger.warning(f"Неверный формат времени '{user_input}' от chat_id: {chat_id}")
#         await update.message.reply_text(
#             "❌ **Неверный формат времени!**\n\n"
#             "Используйте формат **ЧЧ:ММ**\n"
#             "Примеры: `09:00`, `14:30`, `22:45`"
#         )


async def send_poll(context: ContextTypes.DEFAULT_TYPE):
    """Отправка ежедневного опроса о настроении"""
    chat_id = context.job.chat_id
    question = "🌈 **Ежедневный опрос**\nКакое у вас сегодня настроение?"
    options = ["😊 Отличное!", "🙂 Хорошее", "😐 Так себе", "😔 Плохое"]

    try:
        await context.bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            type=Poll.REGULAR,
            is_anonymous=False,  # Неанонимный для лучшего UX
        )
        logger.info(f"Ежедневный опрос отправлен в chat_id: {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки опроса в {chat_id}: {str(e)}")


def main():
    """Запуск бота"""
    app = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    app.add_handler(CommandHandler("test", send_test_message))
    app.add_handler(CommandHandler("jobs", list_jobs))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time))

    logger.info("🚀 Запуск Telegram-бота...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
