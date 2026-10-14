# Pin the Debian release so it matches a release supported by Docker's apt repository
FROM python:3.14-slim

ENV DEBIAN_FRONTEND=noninteractive
# Install the Docker CLI and compose plugin from Docker's official repository
# (no engine: the CLI uses Docker Desktop on the host via the mounted socket)
RUN install -m 0755 -d /etc/apt/keyrings \
    && apt-get update && apt-get install -y --no-install-recommends \
        apt-transport-https ca-certificates curl gnupg lsb-release git git-extras openssh-client curl \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list \
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
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin azure-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /workspaces
