# Чат-бот викторина
Чат-бот викторины для VK и Telegram

### Как установить
#### Переменные окружения:

Часть настроек проекта берётся из переменных окружения. Чтобы их определить, создайте файл `.env` в корневом каталоге и запишите туда данные в таком формате: `ПЕРЕМЕННАЯ=значение`.

```
.
├── .env
└── tg_bot.py
```
Обязательные переменные окружения:
- `TELEGRAM_TOKEN` - токен выглядит например: `6000000001:ADEeVTKrhmLSBouDAjhT0r9tBG-AW5VU9YG`. См. документацию https://core.telegram.org/bots/faq#how-do-i-create-a-bot
- `VK_TOKEN` - токен выглядит например:
  `vk1.a.XxBH4zwP0Ak1eriSpKWRH6FwWE59LugTklFHsReYRt9tQehjRYrLwyb8kylLp27YHninApFuyRi-MLMXtSnV6Bb3nCutvq27jCv82Yn6bKbeDsVCfhQi3gxxSXKxWslNROWFWyN7S3pDWUqscB5OX_wXXtdMn_p4KE-9nUeWaKr-2uCo2Yyj65_4IAmT9jZ0NKKxPfnnxsxkAHsJho33uw`.
  См. документацию https://dev.vk.com/ru/api/access-token/community-token/in-community-settings
- `REDIS_HOST` - хост для подключения к Redis выглядит например: `localhost`. См. документацию https://redis-docs.ru/operate/oss_and_stack/install/install-redis/
- `REDIS_PORT` - порт для подключения к Redis выглядит например: `6379`. См. документацию https://redis-docs.ru/operate/oss_and_stack/install/install-redis/


Python3 должен быть уже установлен. 
Затем используйте `pip` (или `pip3`, есть конфликт с Python2) для установки зависимостей:

```sh
pip install -r requirements.txt
```

Для хранения вопросов викторины используется база данных Redis.
Установка см. документацию https://redis-docs.ru/operate/oss_and_stack/install/install-redis/ 
Для экспорта вопросов в базу данных используйте файл `questions.json` (пример файла представлен в репозитории) и скрипт: 
```sh
python redis_utils.py
```

### Применение
Скрипты работают из консольной утилиты.

Для запуска например:
```sh
python tg_bot.py
```

### Цель проекта

Код написан в образовательных целях на онлайн-курсе для веб-разработчиков [dvmn.org](https://dvmn.org/).