import sys
import time
import config
import logging
import requests
import http.client
from bs4 import BeautifulSoup
from logging.handlers import RotatingFileHandler


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
                    return [{
                        'sim_number': tracker['source']['phone'],
                        'is_blocked': tracker['source']['blocked']
                    } for tracker in json_response['list']]
                else:
                    logger.error('could not get trackers list from Navixy')
                    return None
            except Exception as e:
                logger.error(get_error_str(e))
                return None

        except Exception as e:
            logger.error(get_error_str(e))
            return None


class ThingsMobile:
    BASE_URL = 'https://www.thingsmobile.com/services/business-api'

    def __init__(self, username=None, token=None):
        self.username = username or config.things_mobile_username
        self.token = token or config.things_mobile_token

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
            # with open('sim_status2.xml', 'w') as f:
            #     f.write(data)
            soup = BeautifulSoup(data, 'lxml-xml')
            return soup.find('status').text == 'active'
        except Exception as e:
            logger.error(get_error_str(e))
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
            soup = BeautifulSoup(data, 'xml')
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


def get_error_str(err: Exception):
    return ' '.join(str(err).split())


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

    while True:
        try:
            trackers_fetch_time = time.time()
            # get navixy trackers list
            trackers_list = []
            for navixy_account in config.navixy_accounts:
                navixy = Navixy(navixy_account['username'], navixy_account['password'])
                trackers_list.extend(navixy.get_tracker_list())

            if not trackers_list:
                # sleep for 30 minutes and try again
                time.sleep(1800)
                continue
            else:
                logger.info(f'{len(trackers_list)} trackers found from Navixy')

            # for each tracker check status and block or unblock
            # the sim depending on the Navixy blocked status.
            # also wait 5 minutes between each sim/tracker request
            for tracker in trackers_list:
                tracker_loop_start = time.time()

                # check status on things mobile for this sim
                things_mobile_status = things_mobile.sim_status(tracker['sim_number'])
                logger.info(f'sleeping for {120} sec')
                time.sleep(120)

                if things_mobile_status is None:
                    # sleep for 2 minutes and continue to next tracker
                    logger.info(f'sleeping for {120} sec')
                    time.sleep(120)
                    continue

                elif things_mobile_status is True:
                    if tracker['is_blocked']:
                        # when sim is active but gps is blocked: block sim
                        logger.info(f"[{tracker['sim_number']}] status:  sim is active but gps is blocked")
                        status = things_mobile.block_sim(tracker['sim_number'])
                        if status:
                            logger.info(f"[{tracker['sim_number']}] was successfully blocked")
                        else:
                            logger.error(f"could not block [{tracker['sim_number']}]")
                    else:
                        # when sim and gps both active: do nothing
                        logger.info(f"[{tracker['sim_number']}] status:  sim and gps both active")
                else:
                    if tracker['is_blocked']:
                        # when sim and gps both blocked: do nothing
                        logger.info(f"[{tracker['sim_number']}] status:  sim and gps both blocked")
                    else:
                        # when sim is blocked but gps is active: unblock the sim
                        logger.info(f"[{tracker['sim_number']}] status:  sim is blocked but gps is active")
                        status = things_mobile.unblock_sim(tracker['sim_number'])
                        if status:
                            logger.info(f"[{tracker['sim_number']}] was successfully unblocked")
                        else:
                            logger.error(f"could not unblock [{tracker['sim_number']}]")

                # sleep for some time so that the inner loop takes 5 minutes in total
                time_taken = time.time() - tracker_loop_start
                if time_taken < config.inner_loop_time:
                    time_to_sleep = config.inner_loop_time - time_taken
                    logger.info(f'sleeping for {round(time_to_sleep)} sec')
                    time.sleep(time_to_sleep)

            # sleep for some time so that the outer loop takes 2 hours in total
            time_taken = time.time() - trackers_fetch_time
            if time_taken < config.outer_loop_time:
                time_to_sleep = config.outer_loop_time - time_taken
                logger.info(f'sleeping for {round(time_to_sleep)} sec')
                time.sleep(time_to_sleep)
        except Exception as e:
            logger.critical(get_error_str(e))
