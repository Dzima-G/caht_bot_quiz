import logging
import os
import re
import string

import vk_api as vk
from dotenv import load_dotenv
from redis import Redis
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id
from vk_api.vk_api import VkApiMethod

from redis_utils import (get_user_question, get_user_random_question,
                         start_redist)

logger = logging.getLogger('vk_logger')

QUESTION, ANSWER = range(2)

user_states = {}


def normalize_text(text: str) -> str:
    text = re.sub(r'\[.*?\]', '', text)
    text = text.strip().lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text


def build_keyboard() -> VkKeyboard:
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(
        'Новый вопрос',
        color=VkKeyboardColor.POSITIVE
    )
    keyboard.add_button(
        'Сдаться',
        color=VkKeyboardColor.NEGATIVE
    )
    keyboard.add_line()
    keyboard.add_button(
        'Мой счёт',
        color=VkKeyboardColor.SECONDARY
    )
    return keyboard


def send_message(vk_api: VkApiMethod, event, text: str, keyboard: VkKeyboard) -> None:
    params = dict(peer_id=event.peer_id,
                  message=text,
                  random_id=get_random_id())
    if keyboard:
        params['keyboard'] = keyboard.get_keyboard()
    vk_api.messages.send(**params)


def handle_new_question_request(vk_api: VkApiMethod, redis_conn: Redis, event, keyboard) -> None:
    question_data = get_user_random_question(redis_conn, event.user_id)

    text = question_data.get('question')
    send_message(vk_api, event, text, keyboard)

    text = question_data.get('answer')
    send_message(vk_api, event, text, keyboard)


def give_up(vk_api: VkApiMethod, redis_conn: Redis, event, keyboard) -> None:
    question_data = get_user_question(redis_conn, event.user_id)
    new_question_data = get_user_random_question(redis_conn, event.user_id)

    text = f'Вы сдались...!\nПравильный ответ: {question_data.get("answer")}\n'
    send_message(vk_api, event, text, keyboard)
    text = f'Ваш новый вопрос:\n {new_question_data.get("question")}'
    send_message(vk_api, event, text, keyboard)


def get_statistic(vk_api: VkApiMethod, redis_conn: Redis, event, keyboard) -> None:
    text = 'Вот ваша статистика: ...'
    send_message(vk_api, event, text, keyboard)


def handle_solution_attempt(vk_api: VkApiMethod, redis_conn: Redis, event, keyboard) -> None:
    question_data = get_user_question(redis_conn, event.user_id)

    correct_answer_text = normalize_text(question_data.get('answer'))
    user_answer_text = normalize_text(event.text)

    if user_answer_text.startswith(correct_answer_text):
        text = 'Правильно! Поздравляю! Для следующего вопроса нажмите «Новый вопрос».'
        send_message(vk_api, event, text, keyboard)
        user_states[event.user_id] = QUESTION
    else:
        text = 'Неправильно… Попробуете ещё раз?'
        send_message(vk_api, event, text, keyboard)


def run_vk_bot(token: str, redis_conn: Redis):
    try:
        vk_session = vk.VkApi(token=token)
        vk_api = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)
    except Exception:
        logger.exception('Проблема с подключением vk API')
        return

    keyboard = build_keyboard()
    logger.info('Бот VK успешно запущен!')

    for event in longpoll.listen():
        try:
            if event.type != VkEventType.MESSAGE_NEW:
                continue

            if not event.to_me:
                continue

            if event.user_id not in user_states:
                user_states[event.user_id] = QUESTION

            state = user_states[event.user_id]

            if event.text == 'Новый вопрос' and state == QUESTION:
                handle_new_question_request(vk_api, redis_conn, event, keyboard)
                user_states[event.user_id] = ANSWER
            elif event.text == 'Новый вопрос' and state == ANSWER:
                send_message(
                    vk_api,
                    event,
                    'Сейчас не время запрашивать новый вопрос.\n'
                    'Сначала либо ответьте, либо нажмите «СДАТЬСЯ».',
                    keyboard
                )
            elif event.text == 'Сдаться' and state == ANSWER:
                give_up(vk_api, redis_conn, event, keyboard)
            elif event.text == 'Сдаться' and state == QUESTION:
                send_message(
                    vk_api,
                    event,
                    'Вы еще не получил вопрос!\n',
                    keyboard
                )
            elif event.text == 'Мой счёт' and state == ANSWER:
                get_statistic(vk_api, redis_conn, event, keyboard)
            elif event.text == 'Мой счёт' and state == QUESTION:
                get_statistic(vk_api, redis_conn, event, keyboard)
            elif state == ANSWER:
                handle_solution_attempt(vk_api, redis_conn, event, keyboard)
            else:
                send_message(
                    vk_api,
                    event,
                    'Привет! Я бот для викторины!\n'
                    'Нажмите «Новый вопрос» что бы начать викторину.',
                    keyboard
                )

        except Exception:
            logger.exception('Ошибка при запуске бота!')
            continue


if __name__ == '__main__':
    load_dotenv()

    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    logger.addHandler(console_handler)

    vk_token = os.environ['VK_TOKEN']
    redis_host = os.environ['REDIS_HOST']
    redis_port = os.environ['REDIS_PORT']

    redis_connection = start_redist(redis_host, redis_port)

    logger.info('Redis - запущен!')

    run_vk_bot(vk_token, redis_connection)
