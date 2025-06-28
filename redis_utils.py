import json
import logging
import os
import random
import subprocess
from typing import Dict, Optional

import redis
from dotenv import load_dotenv
from redis import Redis

logger = logging.getLogger(__name__)


def start_redist(host: str, port: str, db: int = 0) -> redis:
    port = int(port)
    client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    try:
        client.ping()
        logger.info('Подключились к Redis!')
        return client
    except redis.exceptions.ConnectionError as e:
        logger.warning(f'Не удалось подключиться к Redis: {e}')

    try:
        subprocess.run(['wsl', 'redis-server', '--daemonize', 'yes'])
    except redis.exceptions.ConnectionError as e:
        logger.exception('Ошибка запуска Redis через консоль.')

    try:
        client.ping()
        logger.info('Подключились к Redis!')
        return client
    except redis.exceptions.ConnectionError as e:
        logger.warning(f'Не удалось подключиться к Redis: {e}')


def get_questions(file_name: str, encoding:str = 'utf-8') -> dict:
    if not os.path.isfile(file_name):
        logger.error(f'Файл не найден: {file_name}.')
        raise FileNotFoundError(f'Файл не найден: {file_name}.')

    try:
        with open(file_name, 'r', encoding=encoding) as contents:
            contents = json.load(contents)
        return contents
    except Exception as e:
        logger.exception(f'Ошибка при чтении файла {file_name}: {e}')
        raise


def get_user_random_question(r: Redis, user_id: int) -> Optional[dict]:

    keys = list(r.scan_iter(match='question:*', count=100))
    if not keys:
        logger.warning('База данных пуста - вопросов нет.')
        return None

    random_key = random.choice(keys)
    r.set(f'user:{user_id}:current_question', random_key)

    return r.hgetall(random_key)


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


def send_json_in_db(redis_conn: Redis, question_data: dict, prefix: str = 'id') -> bool:
    try:
        existing_count = len(redis_conn.keys('question:*'))

        if existing_count > 0:
            start = existing_count + 1
        else:
            start = 1

        for i, (item, data) in enumerate(question_data.items(), start=start):
            key = f'question:{prefix}_{i}'
            redis_conn.hset(key, mapping=data)

        logger.info(f'Данные добавлены в базу данных.')
        return True
    except Exception:
        logger.exception('Проблема с записью в БД.')
        return False


if __name__ == '__main__':
    load_dotenv()

    redis_host = os.environ['REDIS_HOST']
    redis_port = os.environ['REDIS_PORT']

    dist_questions = get_questions('questions.json')

    r = start_redist(redis_host, redis_port)

    send_json_in_db(r, dist_questions)