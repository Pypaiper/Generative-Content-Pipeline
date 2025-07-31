# Table of Contents

1. [Setup](#setup)

## Setup

1. Get package manager, uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Install dependencies: `uv sync --all-packages`
3. Install packages: `uv build --all`

## Developement in local environment

1. Start docker: `docker compose up`
2. Get password: `docker compose exec  -it code cat /root/.config/code-server/config.yaml`
3. Login with password at `127.0.0.1:8080/?folder=/config/workspace`
