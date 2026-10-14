# Class for providing authentication headers or tokens for clients for Azure

import base64

from typing import Any, Dict, Tuple
from decode_jwt import decode_jwt

from azure.identity import DefaultAzureCredential
from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError

from ccloud_auth_provider import CCloud_Auth_Provider, AuthenticationError


class CCloud_Auth_Provider_BasicAuth(CCloud_Auth_Provider):

    def __init__(self, auth_config_basicauth: Dict[str, Any]):
        self._global_api_key = None
        self._global_api_secret = None
        self._global_base64_encoded = None
        self._cloud_base64_encoded = None
        self._cloud_api_key = None
        self._cloud_api_secret = None
        if 'global' in auth_config_basicauth:
            config_global = auth_config_basicauth.get('global')
            self._global_api_key = config_global.get('key', None)
            self._global_api_secret = config_global.get('secret', None)
            self._global_base64_encoded = base64.b64encode(f"{self._global_api_key}:{self._global_api_secret}".encode("utf-8")).decode("utf-8")
            # Use global API Key if configured and no cloud key is configured
            self._cloud_base64_encoded = self._global_base64_encoded
        if 'cloud' in auth_config_basicauth:
            config_cloud = auth_config_basicauth.get('cloud')
            self._cloud_api_key = config_cloud.get('key', None)
            self._cloud_api_secret = config_cloud.get('secret', None)
            # Use cloud key if configured
            self._cloud_base64_encoded = base64.b64encode(f"{self._cloud_api_key}:{self._cloud_api_secret}".encode("utf-8")).decode("utf-8")
       
    async def get_auth_header(self) -> Dict[str, str]:
        if self._global_base64_encoded is None:
            raise RuntimeError('Using kafka cluster keys not implemented yet')
        return {
            'Authorization': f'Basic {self._global_base64_encoded}'
        }
