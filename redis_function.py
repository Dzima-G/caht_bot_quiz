import json
import logging
import os
import random
import subprocess
from typing import Optional

import redis
from dotenv import load_dotenv
from redis import Redis

logger = logging.getLogger(__name__)


def start_redist(host: str, port: str, db: int = 0) -> redis:
    port = int(port)
    redis_conn = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    try:
        redis_conn.ping()
        logger.info('Подключились к Redis!')
        return redis_conn
    except redis.exceptions.ConnectionError as e:
        logger.warning(f'Не удалось подключиться к Redis: {e}')

    try:
        subprocess.run(['wsl', 'redis-server', '--daemonize', 'yes'])
    except redis.exceptions.ConnectionError as e:
        logger.exception('Ошибка запуска Redis через консоль.')

    try:
        redis_conn.ping()
        logger.info('Подключились к Redis!')
        return redis_conn
    except redis.exceptions.ConnectionError as e:
        logger.warning(f'Не удалось подключиться к Redis: {e}')


def get_questions(file_name: str, encoding: str = 'utf-8') -> dict:
    with open(file_name, 'r', encoding=encoding) as content:
        content = json.load(content)
    return content


def get_user_random_question(redis_conn: Redis, user_id: int) -> Optional[dict]:
    keys = list(redis_conn.scan_iter(match='question:*', count=100))
    if not keys:
        logger.warning('База данных пуста - вопросов нет.')
        return None

    random_key = random.choice(keys)
    redis_conn.set(f'user:{user_id}:current_question', random_key)
    redis_conn.hincrby(f'user:{user_id}:stats', 'questions_asked', amount=1)

    return redis_conn.hgetall(random_key)


def get_stats(redis_conn: Redis, user_id: int) -> dict:
    stats = redis_conn.hgetall(f'user:{user_id}:stats')

    return stats


def record_stats(redis_conn: Redis, user_id: int, action: str) -> None:
    if action == 'correct_answer':
        redis_conn.hincrby(f'user:{user_id}:stats', 'correct_answers', amount=1)
    if action == 'give_up':
        redis_conn.hincrby(f'user:{user_id}:stats', 'give_up', amount=1)


def get_user_question(redis_conn: Redis, user_id: int) -> dict:
    user_q_key = redis_conn.get(f'user:{user_id}:current_question')

    if not user_q_key:
        question_data = get_user_random_question(redis_conn, user_id)
        return question_data

    question_data = redis_conn.hgetall(user_q_key)

    if not question_data:
        question_data = get_user_random_question(redis_conn, user_id)
        return question_data

    return question_data


def send_json_in_db(redis_conn: Redis, question_data: dict, prefix: str = 'id') -> None:
        existing_count = len(redis_conn.keys('question:*'))

        if existing_count > 0:
            start = existing_count + 1
        else:
            start = 1

        for i, (item, data) in enumerate(question_data.items(), start=start):
            key = f'question:{prefix}_{i}'
            redis_conn.hset(key, mapping=data)

        logger.info(f'Данные добавлены в базу данных.')




if __name__ == '__main__':
    load_dotenv()

    redis_host = os.environ['REDIS_HOST']
    redis_port = os.environ['REDIS_PORT']

    question_file_path = 'questions.json'

    try:
        dist_questions = get_questions('questions.json')
    except FileNotFoundError:
        raise f'Файл не найден: {question_file_path}.'


    redis_connection = start_redist(redis_host, redis_port)

    send_json_in_db(redis_connection, dist_questions)

