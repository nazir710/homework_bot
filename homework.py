import logging
import os
import requests
import sys
import time

from dotenv import load_dotenv
from http import HTTPStatus
from telebot import TeleBot

from exceptions import HomeworkStatusError, StatusError


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    tokens_is_valid = True
    for token in tokens:
        if not tokens[token]:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {token}. '
                f'Программа принудительно остановлена.'
            )
            tokens_is_valid = False
    if not tokens_is_valid:
        raise AssertionError('Проверьте наличие токенов!')


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'Бот отправил сообщение "{message}".'
        )
        return True
    except Exception:
        return False


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        homework = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if not homework.status_code == HTTPStatus.OK:
            message = (
                f'API вернул статус, отличный от 200: {homework.status_code}'
            )
            logger.critical(message)
            raise StatusError(message)
        else:
            return homework.json()
    except requests.RequestException:
        message = f'API вернул статус, отличный от 200: {homework.status_code}'
        raise StatusError(message)


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        message = (
            f'Тип данных не соответствуют документации: '
            f'получен тип данных {type(response)}'
        )
        raise TypeError(message)
    expected_keys = ['current_date', 'homeworks']
    for key in expected_keys:
        if key not in response:
            message = f'Отсутствует ожидаемый ключ {key} в ответе API.'
            raise KeyError(message)
    if not isinstance(response['homeworks'], list):
        message = (
            f'Тип данных не соответствуют документации: '
            f'получен тип данных {type(response)}'
        )
        raise TypeError(message)


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус."""
    if (not len(homework) == 0
            and homework['status'] not in HOMEWORK_VERDICTS):
        verdict = homework['status']
        message = (
            f'Неожиданный статус домашней работы в ответе API: {verdict}.'
        )
        raise HomeworkStatusError(message)
    elif 'homework_name' not in homework:
        message = 'Отсутстnвует ключ "homework_name" в ответе API.'
        raise KeyError(message)
    else:
        verdict = homework['status']
        homework_name = homework['homework_name']
        message = (
            f'Изменился статус проверки работы "{homework_name}". '
            f'{HOMEWORK_VERDICTS[verdict]}'
        )
        logger.debug(message)
        return message


def check_send_message_status(bot, message):
    """Проверяет ответ функции send_message."""
    if not send_message(bot, message):
        logger.error(
            'Произошла ошибка при отправке сообщения в Telegram.'
        )


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    error_messages = []
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if len(response['homeworks']) == 0:
                logger.debug('Изменения статуса проверки работы отсутствуют.')
            else:
                parse_status_message = parse_status(response['homeworks'][0])
                logger.debug(parse_status_message)
                check_send_message_status(bot, parse_status_message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            error_messages.append(message)
            logger.error(message)
            if (len(error_messages) == 1 or len(error_messages) > 1
                    and not error_messages[-1] == error_messages[-2]):
                check_send_message_status(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='program.log', encoding='utf-8',
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    main()
