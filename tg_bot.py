import logging
import os
import re
import string

from dotenv import load_dotenv
from redis import Redis
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (CallbackContext, CommandHandler, ConversationHandler,
                          Filters, MessageHandler, Updater)

from redis_utils import (get_user_question, get_user_random_question,
                         start_redist)

logger = logging.getLogger('tg_logger')

QUESTION, ANSWER = range(2)


def normalize_text(text: str) -> str:
    text = re.sub(r'\[.*?\]', '', text)
    text = text.strip().lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text


def handle_new_question_request(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    r = context.bot_data.get('CONNECTION_REDIS')

    question_data = get_user_random_question(r, user_id)

    update.message.reply_text(question_data.get('question'))
    update.message.reply_text(question_data.get('answer'))

    return ANSWER


def handle_solution_attempt(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    r = context.bot_data.get('CONNECTION_REDIS')
    question_data = get_user_question(r, user_id)

    correct_answer_text = normalize_text(question_data.get('answer'))
    user_answer_text = normalize_text(update.message.text)

    if user_answer_text.startswith(correct_answer_text):
        update.message.reply_text('Правильно! Поздравляю! Для следующего вопроса нажмите «Новый вопрос».')
        return QUESTION
    else:
        update.message.reply_text('Неправильно… Попробуете ещё раз?')
        return ANSWER


def block_new_question(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        'Сейчас не время запрашивать новый вопрос.\n'
        'Сначала либо ответьте, либо нажмите «СДАТЬСЯ».')
    return ANSWER


def default_answer(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Нажмите «Новый вопрос» что бы начать викторину.')


def give_up(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    r = context.bot_data.get('CONNECTION_REDIS')
    question_data = get_user_question(r, user_id)
    new_question_data = get_user_random_question(r, user_id)

    update.message.reply_text(f'Вы сдались...\nПравильный ответ: {question_data.get("answer")}')
    update.message.reply_text(f'Ваш новый вопрос:\n {new_question_data.get("question")}')

    return ANSWER


def get_statistic(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Вот ваша статистика: ...')


def start(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /start is issued."""
    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    user = update.effective_user
    update.message.reply_markdown_v2(
        f'Привет {user.mention_markdown_v2()}\! Я бот для викторины\! ',
        reply_markup=reply_markup,
    )
    return QUESTION


def run_tg_bot(tg_token: str, redis: Redis) -> None:
    """Start the bot."""
    updater = Updater(tg_token)

    dispatcher = updater.dispatcher
    dispatcher.bot_data['CONNECTION_REDIS'] = redis

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request),

        ],
        states={
            QUESTION: [
                MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request),
                MessageHandler(Filters.regex('^Мой счет$'), get_statistic),
                MessageHandler(Filters.text & ~Filters.command, default_answer),
            ],
            ANSWER: [
                MessageHandler(Filters.regex('^Новый вопрос$'), block_new_question),
                MessageHandler(Filters.regex('^Сдаться$'), give_up),
                MessageHandler(Filters.regex('^Мой счет$'), get_statistic),
                MessageHandler(Filters.text & ~Filters.command, handle_solution_attempt),
            ]
        },
        fallbacks=[CommandHandler('start', start)],
    )

    dispatcher.add_handler(conv_handler)

    try:
        updater.start_polling()
        updater.idle()
    except Exception:
        logger.exception('Ошибка при запуске бота!')


if __name__ == '__main__':
    load_dotenv()

    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    logger.addHandler(console_handler)

    tg_token = os.environ['TELEGRAM_TOKEN']
    redis_host = os.environ['REDIS_HOST']
    redis_port = os.environ['REDIS_PORT']

    redis_connection = start_redist(redis_host, redis_port)

    logger.info('Redis - запущен!')

    run_tg_bot(tg_token, redis_connection)
