import argparse
import asyncio
import os
import sys
import time
import random
import aiohttp
from prometheus_client import start_http_server, Gauge
from ccloud_auth_provider import CCloud_Auth_Provider
from ccloud_config import CCloud_Config

# 1. Prometheus Metrics Configuration
CONFLUENT_QUOTA_DEFAULT = Gauge(
    'confluent_quota_default_limit', 
    'The standard fallback/default limit assigned by Confluent Cloud before overrides.', 
    ['organization_id', 'scope', 'quota_id', 'environment_id', 'network_id', 'kafka_cluster']
)

CONFLUENT_QUOTA_APPLIED = Gauge(
    'confluent_quota_applied_limit', 
    'The active threshold currently enforced on your environment.', 
    ['organization_id', 'scope', 'quota_id', 'environment_id', 'network_id','kafka_cluster']
)

CONFLUENT_QUOTA_USAGE = Gauge(
    'confluent_quota_usage', 
    'The current utilization level tracking against your quota limit.', 
    ['organization_id', 'scope', 'quota_id', 'environment_id', 'network_id', 'kafka_cluster']
)

SCRAPE_DURATION = Gauge(
    'confluent_quota_scrape_duration_seconds', 
    'Total wall clock time taken to execute the background scope gather.'
)

RATE_LIMIT_HIT_TOTAL = Gauge(
    'confluent_quota_rate_limit_hits_total',
    'Total number of times a 429 Rate Limit was encountered and managed.'
)

# Core Verified Base and Route API Parameters
BASE_URL = "https://api.confluent.cloud"
APPLIED_QUOTAS_ENDPOINT = f"{BASE_URL}/service-quota/v1/applied-quotas"
# Note: We are not querying the scope "service_account" and "user_account" as we would have to fetch quotas for each of them individually by their ID
SCOPES = ["organization", "environment", "kafka_cluster", "network"]


CONFLUENT_CLOUD_API_KEY = os.getenv("CONFLUENT_CLOUD_API_KEY")
CONFLUENT_CLOUD_API_SECRET = os.getenv("CONFLUENT_CLOUD_API_SECRET")

class Prometheus_Confluent_Cloud_Quota_Exporter:
    def __init__(self, ccloud_config: CCloud_Config, auth_provider: CCloud_Auth_Provider):
        self._ccloud_config = ccloud_config
        self._auth_provider = auth_provider

    async def fetch_endpoint(self, session: aiohttp.ClientSession, url: str, params: dict = None, max_retries: int = 5) -> dict:
        """Performs HTTP GET requests with custom headers, intercepting 429 status codes for backoffs."""
        headers = await self._auth_provider.get_auth_header()
        headers['Accept'] = 'application/json'
        
        attempt = 0
        while True:
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 429:
                        RATE_LIMIT_HIT_TOTAL.inc()
                        attempt += 1
                        if attempt > max_retries:
                            print(f"Max retries reached for URL: {url}")
                            response.raise_for_status()

                        # Extract relative delay in seconds from standard header
                        retry_after_raw = response.headers.get("Retry-After")
                        if retry_after_raw and retry_after_raw.isdigit():
                            wait_seconds = int(retry_after_raw)
                        else:
                            wait_seconds = (2 ** attempt) + random.uniform(0.1, 1.0)
                            
                        print(f"Rate limited (429). Pausing for {wait_seconds} seconds before retry...")
                        await asyncio.sleep(wait_seconds)
                        continue
                    
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientResponseError as e:
                if e.status != 429 or attempt >= max_retries:
                    raise e

    async def fetch_quota_for_scope(self, session: aiohttp.ClientSession, scope: str):
        """Scrapes the correct applied-quotas collection route and pages through metadata links cleanly."""
        next_url = APPLIED_QUOTAS_ENDPOINT
        # Initial parameters required by the collection query
        params = {"scope": scope, "page_size": 100}
        
        try:
            while next_url:
                # Confluent embeds query strings directly inside metadata.next for subsequent pages. 
                # If the next_url isn't the base endpoint, query parameters are already contained in it.
                current_params = params if next_url == APPLIED_QUOTAS_ENDPOINT else None
                
                data = await self.fetch_endpoint(session, next_url, params=current_params)
                
                # Map values into metrics
                for item in data.get("data", []):
                    quota_id = item.get("id")
                    if not quota_id:
                        continue
                    
                    default_limit = item.get("default_limit")
                    applied_limit = item.get("applied_limit")
                    organization_id = item.get("organization").get("id")
                    if "environment" in item and "id" in item["environment"]:
                        environment_id = item.get("environment").get("id")
                    else:
                        environment_id = ""
                    if "network" in item and "id" in item["network"]:
                        network_id = item.get("network").get("id")
                    else:
                        network_id = ""
                    if "kafka_cluster" in item and "id" in item["kafka_cluster"]:
                        kafka_cluster = item.get("kafka_cluster").get("id")
                    else:
                        kafka_cluster = ""            
                    usage = item.get("usage")
                    
                    if default_limit is not None:
                        CONFLUENT_QUOTA_DEFAULT.labels(scope=scope, quota_id=quota_id, organization_id=organization_id, environment_id=environment_id, network_id=network_id, kafka_cluster=kafka_cluster).set(default_limit)
                    if applied_limit is not None:
                        CONFLUENT_QUOTA_APPLIED.labels(scope=scope, quota_id=quota_id, organization_id=organization_id, environment_id=environment_id, network_id=network_id, kafka_cluster=kafka_cluster).set(applied_limit)
                    if usage is not None:
                        CONFLUENT_QUOTA_USAGE.labels(scope=scope, quota_id=quota_id, organization_id=organization_id, environment_id=environment_id, network_id=network_id, kafka_cluster=kafka_cluster).set(usage)
                
                # Extract pagination tracker safely
                metadata = data.get("metadata", {})
                next_url = metadata.get("next")
                
                if next_url:
                    # Politeness pacing delay between iterative pagination fetches
                    await asyncio.sleep(0.05)
                    
        except Exception as e:
            print(f"Error executing pagination scrape on scope '{scope}': {e}")

    async def background_quota_sync_loop(self):
        """Use static scopes and processes individual pipelines concurrently."""
        async with aiohttp.ClientSession() as session:
            while True:
                start_time = time.time()
                print("Beginning verified API scraping run against Confluent Cloud Service Quotas...")
                
                try:
                    # Gather metrics for each scope concurrently using non-blocking paths
                    tasks = [self.fetch_quota_for_scope(session, scope) for scope in SCOPES]
                    await asyncio.gather(*tasks)
                    
                    SCRAPE_DURATION.set(time.time() - start_time)
                    print(f"Successfully processed metrics across {len(SCOPES)} scopes.")
                    
                except Exception as e:
                    print(f"Critical error in top-level sync runner: {e}")
                
                # Query every 15 minutes to stay well within healthy usage limits
                await asyncio.sleep(self._ccloud_config.get_refresh_interval())

    async def main(self):
        start_http_server(self._ccloud_config.get_http_port())
        print(f"Prometheus monitoring online at http://localhost:{self._ccloud_config.get_http_port()}/metrics")
        await self.background_quota_sync_loop()

if __name__ == '__main__':
    if sys.version_info >= (3, 9):
        parser = argparse.ArgumentParser(
            prog='prometheus_quota_api_exporter',
            exit_on_error=True,
        )  # type: ignore  # pragma: no cover
    else:
        parser = argparse.ArgumentParser(
            prog='prometheus_quota_api_exporter',
        )  # type: ignore  # pragma: no cover

    parser.add_argument('config_file', nargs='?', help='A config file')
    try:
        parsed_args = parser.parse_args()
    except SystemExit:
        parser.print_help()
        sys.exit(1)
    config_file_name = parsed_args.config_file
    if config_file_name is None or config_file_name=="":
        print ('Please provide a config file')
        parser.print_help()
        sys.exit(1)

    ccloud_config = CCloud_Config(config_file_name)
    auth_provider = CCloud_Auth_Provider.create_auth(ccloud_config.get_auth_config())
    ccloud_exporter = Prometheus_Confluent_Cloud_Quota_Exporter(ccloud_config, auth_provider)
    try:
        asyncio.run(ccloud_exporter.main())
    except KeyboardInterrupt:
        print("Exporter shutdown complete.")
