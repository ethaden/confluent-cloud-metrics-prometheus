# Base class for providing authentication headers or tokens for clients
from abc import ABC
from typing import Any, Dict

class CCloud_Auth_Provider(ABC):
    async def get_bearer(self, uri: str) -> str:
        pass

    async def get_auth_header(self, uri: str) -> Dict[str, str]:
        pass

    @staticmethod
    def create_auth(auth_config: Dict[str, Any]) -> CCloud_Auth_Provider:
        if auth_config['selected'] == 'azure':
            from ccloud_auth_provider_azure import CCloud_Auth_Provider_Azure
            return CCloud_Auth_Provider_Azure(auth_config.get('azure', {}))
        if auth_config['selected'] == 'basicauth':
            from ccloud_auth_provider_basicauth import CCloud_Auth_Provider_BasicAuth
            return CCloud_Auth_Provider_BasicAuth(auth_config.get('basicauth', {}))
        raise RuntimeError('No suitable authentication method configured')

class AuthenticationError(Exception):
    pass
