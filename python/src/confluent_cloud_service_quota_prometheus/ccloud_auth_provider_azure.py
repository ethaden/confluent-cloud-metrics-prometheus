# Class for providing authentication headers or tokens for clients for Azure

import time
import jwt
import aiohttp

from typing import Any, Dict, Tuple
from util_decode_jwt import decode_jwt

from azure.identity.aio import DefaultAzureCredential
from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError

from ccloud_auth_provider import CCloud_Auth_Provider, AuthenticationError


class CCloud_Auth_Provider_Azure(CCloud_Auth_Provider):

    #def __init__(self, app_id: str, pool_id: str, exclude_managed_identity_credential: bool=False, min_token_validity: int=30, logging_enable: bool=False):
    def __init__(self, auth_config_azure: Dict[str, Any]):
        try:
            self._app_id = auth_config_azure.get('app_id')
            self._pool_id = auth_config_azure.get('pool_id', None)
            self._min_token_validity = int(auth_config_azure.get('min_token_validity', '30'))
            self._exclude_managed_identity_credential = auth_config_azure.get('exclude_managed_identity_credential', 'false').lower() == 'true'
            self._logging_enable = auth_config_azure.get('logging_enable', 'false').lower() == 'true'
            # Note, that while writing this comment, the feature of using the visual studio code extension to authenticate with Azure via DefaultAzureCredential is broken in the libs
            # To save some time, we disable this and the shared token method for now
            #default_credential = DefaultAzureCredential()
            #if logging_enable:
            #    logging.basicConfig(level=logging.DEBUG)
            # Unfortunately, we need to stick to setting exclude_visual_studio_code_credential=True until the developers finally fix their code
            self._default_credential = DefaultAzureCredential(exclude_visual_studio_code_credential=True,
                    exclude_shared_token_cache_credential=True, 
                    exclude_managed_identity_credential=self._exclude_managed_identity_credential,
                    logging_enable=self._logging_enable)
            self._azure_token = None
            self._azure_token_access_token_decoded = None
            self._ccloud_token = None
            self._ccloud_token_access_token_decoded = None
        except ClientAuthenticationError as exc:
            raise AuthenticationError from exc
    
    @property
    def app_id(self)->str:
        return self._app_id

    @property
    def pool_id(self)->str:
        return self._pool_id

    async def _get_azure_token(self)->Tuple[str, bool]:
        if self._azure_token is not None:
            expiration = int(self._azure_token_access_token_decoded['exp'])
            now = int(time.time())
            if expiration - now >= self._min_token_validity:
                return self._azure_token, False

        self._azure_token = await self._default_credential.get_token(f'{self._app_id}/.default')
        self._azure_token_access_token_decoded = self.decode_jwt(self._azure_token.token)
        # print ('#####################################')
        # print ('Azure Token')
        # print ('#####################################')
        # print (self._azure_token)
        # print ('Decoded:')
        # print (decode_jwt(self._azure_token.token))
        # print ('#####################################')
        return self._azure_token, True
    
    async def get_azure_token_with_expiry(self, cluster_id)->Tuple[str, float, str, Dict[str, str]]:
        token, _ = await self._get_azure_token()
        if self._pool_id is not None:
            return (token.token, float(self._azure_token_access_token_decoded['exp']), '', {'logicalCluster': cluster_id, 'identityPoolId': self._pool_id})
        return (token.token, float(self._azure_token_access_token_decoded['exp']), '')
        

    @property
    async def azure_token(self)->str:
        token, _ = await self._get_azure_token()
        return token.token
    
    @property
    async def ccloud_sts_token(self)->str:
        azure_token, azure_token_renewed = await self._get_azure_token()
        if self._ccloud_token is not None:
            if not azure_token_renewed:
                expiration = int(self._ccloud_token_access_token_decoded['exp'])
                now = int(time.time())
                if expiration - now >= self._min_token_validity:
                    return self._ccloud_token['access_token']

        data = {'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
                'subject_token': azure_token.token,
                'identity_pool_id': self._pool_id,
                'subject_token_type': 'urn:ietf:params:oauth:token-type:jwt',
                'requested_token_type': 'urn:ietf:params:oauth:token-type:access_token'}
        url = 'https://api.confluent.cloud/sts/v1/oauth2/token'
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as response:
                if response.status != 200:
                    error_msg = (await response.json()).get('errors')[0].get('detail')
                    raise RuntimeError(f'Unable to authenticate (status code: {response.status}, message: "{error_msg}")')
                self._ccloud_token = await response.json()
        self._ccloud_token_access_token_decoded = self.decode_jwt(self._ccloud_token['access_token'])
        return self._ccloud_token['access_token']
    
    def decode_jwt(self, access_token: str)->Dict[str, Any]:
        alg = jwt.get_unverified_header(access_token)['alg']
        decoded = jwt.decode(access_token, algorithms=[alg], options={"verify_signature": False})
        return decoded

    async def get_token(self) -> str:
        return await self.ccloud_sts_token

    async def get_bearer(self) -> str:
        return await self.ccloud_sts_token

    async def get_auth_header(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {await self.ccloud_sts_token}'
        }

