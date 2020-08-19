import sys
import config
import logging
import requests
from logging.handlers import RotatingFileHandler

headers = {
    'Content-Type': 'application/json',
}


class Navixy:
    def __init__(self):
        self.username = config.navixy_username
        self.password = config.navixy_password
        self.user_hash = None

    def auth(self):
        logger.info(f'logging in to navixy account with {self.username}')
        data = {
            'login': self.username,
            'password': self.password
        }
        try:
            response = requests.post('https://api.navixy.com/v2/user/auth', headers=headers, json=data).json()
            if response['success']:
                self.user_hash = response['hash']
                logger.info('logged into navixy account')
        except Exception as e:
            logger.critical(e)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
        handlers=(
            RotatingFileHandler(
                filename='flex.log',
                maxBytes=(1024 ** 3) / 2,
                backupCount=1,
            ),
            logging.StreamHandler(sys.stdout)
        )
    )
    # logging.getLogger(aiohttp.__name__).setLevel(logging.ERROR)
    logger = logging.getLogger()

    navixy = Navixy()
    navixy.auth()
