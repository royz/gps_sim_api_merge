import json
import sys
from pprint import pprint
import config
import logging
import requests
from logging.handlers import RotatingFileHandler
import http.client
from bs4 import BeautifulSoup


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


class ThingsMobile:
    BASE_URL = 'https://www.thingsmobile.com/services/business-api'

    def __init__(self, username=None, token=None):
        self.username = username or config.things_mobile_username
        self.token = token or config.things_mobile_token
        print(self.username)
        print(self.token)

    def sim_status(self, sim_number: str) -> bool:
        try:
            connection = http.client.HTTPSConnection('www.thingsmobile.com')
            payload = f'username={self.username}&token={self.token}&msisdn={sim_number}'
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            connection.request("POST", "/services/business-api/simStatus", payload, headers)
            response = connection.getresponse()
            data = response.read().decode('utf-8')
            soup = BeautifulSoup(data, 'lxml-xml')
            return soup.find('status').text == 'active'
        except Exception as e:
            logger.error(e)
            logger.error(f'failed to retrieve information for {sim_number}')

    def block_sim(self, sim_number: str = '882360012289512') -> bool:
        try:
            connection = http.client.HTTPSConnection('www.thingsmobile.com')
            payload = f'username={self.username}&token={self.token}&msisdn={sim_number}'
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            connection.request("POST", "/services/business-api/blockSim", payload, headers)
            response = connection.getresponse()
            data = response.read().decode('utf-8')
            soup = BeautifulSoup(data, 'lxml-xml')
            return soup.find('done').text == 'true'
        except Exception as e:
            logger.error(e)
            logger.error(f'failed to block sim: {sim_number}')

    def unblock_sim(self, sim_number: str = '882360012289512') -> bool:
        try:
            connection = http.client.HTTPSConnection('www.thingsmobile.com')
            payload = f'username={self.username}&token={self.token}&msisdn={sim_number}'
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            connection.request("POST", "/services/business-api/unblockSim", payload, headers)
            response = connection.getresponse()
            data = response.read().decode('utf-8')
            soup = BeautifulSoup(data, 'lxml-xml')
            return soup.find('done').text == 'true'
        except Exception as e:
            logger.error(e)
            logger.error(f'failed to unblock sim: {sim_number}')


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

    # navixy = Navixy()
    # navixy.get_tracker_list()

    things_mobile = ThingsMobile()
    status = things_mobile.unblock_sim('882360012774864')
    print(status)
