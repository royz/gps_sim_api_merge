import datetime
import sys
import time
import config
import logging
import requests
import http.client
from bs4 import BeautifulSoup
from logging.handlers import RotatingFileHandler
import smtplib
import ssl


class Navixy:
    def __init__(self, username, password):
        self.username = username
        self.password = password
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
            response = requests.post('https://api.navixy.com/v2/user/auth',
                                     headers=headers, json=data).json()
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

        try:
            response = requests.post('https://api.navixy.com/v2/tracker/list',
                                     headers=headers, json=data)
            try:
                json_response = response.json()
                if json_response['success']:
                    numbers = []
                    for tracker in json_response['list']:
                        try:
                            numbers.append(tracker['source']['phone'])
                        except:
                            pass
                    return numbers
                else:
                    logger.error('could not get trackers list from Navixy')
                    return []
            except Exception as e:
                logger.error(get_error_str(e))
                return []

        except Exception as e:
            logger.error(get_error_str(e))
            return []


class ThingsMobile:
    BASE_URL = 'https://www.thingsmobile.com/services/business-api'

    def __init__(self, username=None, token=None):
        self.username = username or config.things_mobile_username
        self.token = token or config.things_mobile_token

    def check_last_connection_date(self, sim_number: str) -> bool:
        try:
            connection = http.client.HTTPSConnection('www.thingsmobile.com')
            payload = f'username={self.username}&token={self.token}&msisdn={sim_number}'
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            connection.request("POST", "/services/business-api/simStatus", payload, headers)
            response = connection.getresponse()
            data = response.read().decode('utf-8')
            with open('sim_status.xml', 'w') as f:
                f.write(data)
            soup = BeautifulSoup(data, 'lxml-xml')
            return soup.find('lastConnectionDate').text
        except Exception as e:
            logger.error(get_error_str(e))
            logger.error(f'failed to retrieve information for {sim_number}')


def get_error_str(err: Exception):
    return ' '.join(str(err).split())


def notify(number, date):
    message = 'Subject: Number last active more than 28 days ago\n\n' \
              f'{number} was last active more than 28 days ago.\n' \
              f'Last active on: {date}'

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(config.sender_email, config.sender_password)
            server.sendmail(config.sender_email, config.recipient_email, message)
        logger.info(f'email sent to {config.recipient_email}')
    except StopIteration:
        logger.error('could not send email')


if __name__ == '__main__':
    # configure the logger
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
        handlers=(
            RotatingFileHandler(
                filename='api-merge.log',
                maxBytes=(1024 ** 3) / 2,
                backupCount=1,
            ),
            logging.StreamHandler(sys.stdout)
        )
    )
    logger = logging.getLogger()

    things_mobile = ThingsMobile()
    navixy_numbers = []
    for navixy_account in config.navixy_accounts:
        navixy = Navixy(navixy_account['username'], navixy_account['password'])
        navixy_numbers.extend(navixy.get_tracker_list())
    logger.info(f'found {len(navixy_numbers)} numbers from {len(config.navixy_accounts)} navixy accounts')
    for navixy_number in navixy_numbers:
        last_date = things_mobile.check_last_connection_date(navixy_number)
        if last_date:

            last_date_object = datetime.datetime.strptime(last_date, '%Y-%m-%d %H:%M:%S')
            formatted_last_date = last_date_object.strftime('%d %b, %Y %H:%M:%S')
            time_delta = datetime.datetime.now() - last_date_object
            logger.info(f'last connection date of {navixy_number}: {formatted_last_date} [{time_delta.days} days ago]')
            if time_delta > datetime.timedelta(days=28):
                logger.info(f'{navixy_number} had last connection more than 28 days ago. notifying...')
                notify(navixy_number, formatted_last_date)
        else:
            logger.error(f'did not receive a valid date for number: {navixy_number}')
        time.sleep(5)
