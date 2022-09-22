import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Sends a message to the TELEGRAM_CHAT_ID."""
    logger.info('Попытка отправить сообщение в Telegram.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Не удалось отправить сообщение в Telegram: {error}')
    else:
        logger.info('Удачная отправка сообщения в Telegram.')


def get_api_answer(current_timestamp: int) -> dict:
    """
    Makes a request to the endpoint of the API service.
    If successful, returns the response converted to python data types.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    logger.info('Отправка запроса к API.')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        raise exceptions.EndpointIsUnavailable(
            'An error was received during the endpoint request')

    if response.status_code != HTTPStatus.OK:
        raise exceptions.EndpointIsUnavailable(
            'The API returned a code other than 200')
    return response.json()


def check_response(response: dict) -> list:
    """
    Checks the API response for correctness.
    If the answer meets expectations, returns a list of homework.
    """
    if not isinstance(response, dict):
        raise TypeError('The API response must be a dictionary')

    if 'current_date' not in response or 'homeworks' not in response:
        raise exceptions.APIResponseIsIncorrect(
            'The API response must contain the `homeworks` '
            'and `current_date` keys'
        )

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            'In the response, the `homeworks` key must match the list')
    return homeworks


def parse_status(homework: dict) -> str:
    """Returns a message about the status of homework."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError(
            'Each `homework` must contain the keys `homework_name` and '
            '`status`'
        )

    if homework_status not in HOMEWORK_STATUSES:
        possible_statuses = ', '.join(HOMEWORK_STATUSES.keys())
        raise exceptions.UnexpectedStatus(
            f'Invalid status {homework_status}. '
            f'Possible statuses: {possible_statuses}'
        )

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Checks the availability of environment variables."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """The main logic of the bot."""
    if not check_tokens():
        logger.critical(f'Отсутствует обязательная переменная окружения.')
        sys.exit('Программа принудительно остановлена.')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    last_msg = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            if homeworks:
                new_msg = parse_status(homeworks[0])
                send_message(bot, new_msg)
            else:
                logger.debug('В ответе отсутствуют новые статусы.')
            current_timestamp = response.get('current_date')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_msg != message:
                send_message(bot, message)
                last_msg = message

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
