import logging
import os
import requests
import time

from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import HomeworkStatusError, SendMessageError, StatusError


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


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log', encoding='utf-8',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for token in tokens:
        if not tokens[token]:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {token}. '
                f'Программа принудительно остановлена.'
            )
            raise AssertionError('Проверьте наличие токенов!')


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Бот отправил сообщение "{message}"')
    except SendMessageError('Сбой при отправке сообщения.'):
        logger.error('Произошла ошибка при отправке сообщения в Telegram.')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        homework = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if not homework.status_code == 200:
            message = 'API вернул код, отличный от 200.'
            logger.critical(message)
            raise StatusError(message)
        else:
            return homework.json()
    except requests.RequestException as error:
        logger.critical(error)


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if isinstance(response, dict) is not True:
        message = 'Тип данных не соответствуют документации.'
        logger.error(message)
        raise TypeError(message)
    expected_keys = ['current_date', 'homeworks']
    for key in expected_keys:
        if key not in response:
            message = f'Отсутствует ожидаемый ключ {key} в ответе API.'
            logger.error(message)
            raise KeyError(message)
    if isinstance(response['homeworks'], list) is not True:
        message = 'Тип данных не соответствуют документации.'
        logger.error(message)
        raise TypeError(message)


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус."""
    if (not len(homework) == 0
            and homework['status'] not in HOMEWORK_VERDICTS):
        message = 'Неожиданный статус домашней работы в ответе API.'
        logger.error(message)
        raise HomeworkStatusError(message)
    elif 'homework_name' not in homework:
        message = 'Отсутстnвует ключ "homework_name" в ответе API.'
        logger.error(message)
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


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if len(response['homeworks']) == 0:
                logger.debug('Изменения статуса проверки работы отсутствуют.')
            else:
                send_message(bot, parse_status(response['homeworks'][0]))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
