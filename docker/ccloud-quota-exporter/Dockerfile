# Pin the Debian release so it matches a release supported by Docker's apt repository
FROM python:3.14-slim

ENV DEBIAN_FRONTEND=noninteractive
# Install the Docker CLI and compose plugin from Docker's official repository
# (no engine: the CLI uses Docker Desktop on the host via the mounted socket)
RUN install -m 0755 -d /etc/apt/keyrings \
    && apt-get update && apt-get install -y --no-install-recommends \
        apt-transport-https ca-certificates curl gnupg lsb-release curl \
    && mkdir -p /etc/apt/keyrings \
    && curl -sLS https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
    && chmod go+r /etc/apt/keyrings/microsoft.gpg \
    # 2. Dynamically discover distribution and add the software repository
    # No release for Debian trixie yet, hardcode bookworm for now
    #&& AZ_DIST=$(lsb_release -cs) \
    && AZ_DIST=bookworm \
    && echo "Types: deb\nURIs: https://packages.microsoft.com/repos/azure-cli/\nSuites: ${AZ_DIST}\nComponents: main\nArchitectures: $(dpkg --print-architecture)\nSigned-By: /etc/apt/keyrings/microsoft.gpg" | tee /etc/apt/sources.list.d/azure-cli.sources \
    # 3. Update apt and install the additional packages
    && apt-get update \
    && apt-get install -y --no-install-recommends azure-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m python \
    && mkdir -p /srv/python

# Install uv globally
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY ./python /srv/python

RUN cd /srv/python \
    && chown -R python:python /srv/python \
    && rm -rf /srv/python/__pycache__ /srv/python/*.pyc /srv/python/*.pyo /srv/python/.venv\
    && uv sync

CMD ["/srv/python/.venv/bin/python", "-u", "src/confluent_cloud_service_quota_prometheus/ccloud_prometheus_quota_api_exporter.py", "/srv/python/config.yaml"]
WORKDIR /srv/python
USER python
