import hashlib
import json
import logging
import os.path
import requests
import time
import uuid

from typing import Dict, Any

BASE_URL = 'https://open-ru.aqara.com/v3.0/open/api'

INCORRECT_REFRESH_TOKEN_CODE = 2006
ACCESSTOKEN_ILLEGAL = 108

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

logger = logging.getLogger(__name__)


class GetTokensError(Exception):
    pass


class AqaraSceneRunner:

    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None

    def __init__(
            self,
            *,
            app_id: str,
            app_key: str,
            key_id: str,
            account: str,
            state_dir: str
    ) -> None:
        self.app_id = app_id
        self.app_key = app_key
        self.key_id = key_id
        self.account = account

        self.tokens_file_path = os.path.join(state_dir, 'tokens.json')
        self.code_file_path = os.path.join(state_dir, 'code.json')

        if os.path.isfile(self.tokens_file_path):
            self._load_tokens()

    def _get_code(self) -> None:
        logger.info('Get code')
        data = {
            'intent': 'config.auth.getAuthCode',
            'data': {
                'account': self.account,
                'accountType': 0,
            }
        }
        resp = requests.post(
            BASE_URL,
            headers=self._get_headers(),
            json=data
        ).json()['result']
        logger.info(f'Get code. Resp {resp}')

    def _get_tokens(self) -> None:
        try:
            with open(self.code_file_path, 'r') as f:
                code = json.load(f)['code']
        except Exception:
            raise GetTokensError('Code is None')
        else:
            os.remove(self.code_file_path)

        logger.info(f'Get tokens. Code is {code}')
        data = {
            'intent': 'config.auth.getToken',
            'data': {
                'authCode': code,
                'account': self.account,
                'accountType': 0
                }
            }
        resp = requests.post(
            BASE_URL,
            headers=self._get_headers(),
            json=data
        ).json()

        if 'accessToken' in resp['result']:
            logger.info(f'Get tokens. Resp {resp}')
            self._save_tokens(resp['result'])
        else:
            logger.error(f'Get tokens. Error  {resp}')
            raise GetTokensError('Api error')

    def _load_tokens(self) -> None:
        logger.info('Load tokens')
        with open(self.tokens_file_path, 'r') as f:
            tokens = json.load(f)
        self.access_token = tokens['accessToken']
        self.refresh_token = tokens['refreshToken']
        self.expires_in = int(tokens['expiresIn'])
        logger.info('Tokens loaded')

    def _save_tokens(self, tokens: Dict[str, Any]) -> None:
        self.access_token = tokens['accessToken']
        self.refresh_token = tokens['refreshToken']
        tokens['expiresIn'] = round(time.time()) + int(tokens['expiresIn'])
        self.expires_in = tokens['expiresIn']
        with open(self.tokens_file_path, 'w+') as f:
            json.dump(tokens, f, indent=4)

    def _refresh_tokens(self) -> None:
        data = {
            'intent': 'config.auth.refreshToken',
            'data': {
                'refreshToken': self.refresh_token
            }
        }
        resp = requests.post(
            BASE_URL,
            headers=self._get_headers(),
            json=data
        ).json()

        if resp['code'] == INCORRECT_REFRESH_TOKEN_CODE:
            logger.error(f'Refresh tokens. Error {resp}')
            self._get_code()
            raise GetTokensError('Api error')

        logger.info(f'Refresh tokens. Resp {resp}')
        self._save_tokens(resp['result'])

    def _get_headers(self, access_token: str = '') -> Dict[str, str]:
        nonce = str(uuid.uuid4()).split('-')[0]
        header_time = str(int(time.time()*1000))

        pre_sign = f'Appid={self.app_id}&Keyid={self.key_id}&Nonce={nonce}&Time={header_time}{self.app_key}'

        if access_token:
            pre_sign = f'Accesstoken={access_token}&{pre_sign}'

        sign = hashlib.md5(pre_sign.lower().encode()).hexdigest()

        return {
            'Accesstoken': access_token,
            'Appid': self.app_id,
            'Keyid': self.key_id,
            'Nonce': nonce,
            'Time': header_time,
            'Sign': sign
        }

    def _make_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if os.path.isfile(self.code_file_path):
            self._get_tokens()
        elif self.access_token is None:
            self._get_code()
        elif self.expires_in and self.expires_in < time.time():
            self._refresh_tokens()

        headers = self._get_headers(self.access_token)
        logger.info(f'Make request with headers {headers}')

        resp = requests.post(BASE_URL, headers=headers, json=data).json()

        if resp['code'] == ACCESSTOKEN_ILLEGAL:
            logger.error(f'AccessToken illegal {resp}')
            self._get_code()

        logger.info(resp)
        return resp

    def run_scene(self, *, scene_id: str) -> None:
        logger.info('Run scene')
        data = {
            'intent': 'config.scene.run',
            'data': {
                'sceneId': scene_id
            }
        }
        self._make_request(data)

    def save_code(self, *, code: str) -> None:
        logger.info(f'Save {code} to {self.code_file_path}')
        with open(self.code_file_path, 'w+') as f:
            json.dump({'code': code}, f, indent=4)
