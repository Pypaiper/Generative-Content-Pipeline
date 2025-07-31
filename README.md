# Table of Contents

1. [Setup](#setup)

## Setup

1. Get package manager, uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Install dependencies: `uv sync --all-packages`
3. Install packages: `uv build --all`

## Developement in local environment

<<<<<<< HEAD
1. Start docker: `docker compose up`
2. Get password: `docker compose exec  -it code cat /root/.config/code-server/config.yaml`
3. Login with password at `127.0.0.1:8080/?folder=/config/workspace`
=======
1. Start docker: `docker compose up -d`
2. Get password: `docker compose exec  -it code cat /root/.config/code-server/config.yaml`
3. Login at `127.0.0.1:28080`
>>>>>>> 96927201545e0e669f460ef7933e5b5d59b86541
