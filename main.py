import json
import sys
from pprint import pprint

import config
import logging
import requests
from logging.handlers import RotatingFileHandler


class Navixy:
    API_BASE = 'https://api.navixy.com/v2'

    def __init__(self):
        self.username = config.navixy_username
        self.password = config.navixy_password
        self.user_hash = None

    def auth(self):
        logger.info(f'logging in to navixy account with {self.username}')

        headers = {
            'Content-Type': 'application/json',
        }

        data = {
            'login': self.username,
            'password': self.password
        }
        try:
            response = requests.post(f'{self.API_BASE}/user/auth', headers=headers, json=data).json()
            if response['success']:
                self.user_hash = response['hash']
                logger.info('logged into navixy account')
        except Exception as e:
            logger.critical(e)

    def get_tracker_list(self):
        if not self.user_hash:
            self.auth()

        headers = {
            'Content-Type': 'application/json',
        }

        data = {
            'hash': self.user_hash
        }

        response = requests.post(f'{self.API_BASE}/tracker/list', headers=headers, json=data)

        with open('trackers.json', 'w', encoding='utf-8') as f:
            json.dump(response.json(), f)

        pprint(response.json())


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
    navixy.get_tracker_list()
