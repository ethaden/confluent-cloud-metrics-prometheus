# Base class for providing authentication headers or tokens for clients
import os
from abc import ABC
from typing import Any, Dict
import re
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

# Search for values like $(env:MyFancyEnvironmentVariable)
env_variable_pattern = r"\$\{env:(?P<envVarName>[^\)]+)\}"

class CCloud_Config(ABC):

    def __init__(self, config_file_name: str):
        super().__init__()
        self._config = self._read_config_file(config_file_name)
        self._inject_environment_variables(self._config)

    def _inject_environment_variables(self, config: Dict[str, Any]):
        for key in config.keys():
            value = config.get(key)
            if isinstance(value, Dict):
                self._inject_environment_variables(value)
            elif isinstance(value, str):
                match = re.search(env_variable_pattern, value)
                if match:
                    config[key] = os.getenv(match.group('envVarName'), 'UNDEFINED')
            

    def get_auth_config(self)->Dict[str, Any]:
        return self._config.get('auth')

    def get_http_port(self)->int:
        return self._config.get('http_port')

    def get_refresh_interval(self) -> int:
        return self._config.get('refresh_interval')

    def _read_config_file(self, config_file_name: str) -> Dict[str, Any]:
        try:
            with open(config_file_name, 'r', encoding='utf-8') as fs:
                return load(fs, Loader=Loader)
        except OSError:
            pass
        raise RuntimeError(f'Unable to open config file "{config_file_name}"')
