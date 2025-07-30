if command -v uv >/dev/null 2>&1; then
  echo "uv exists."
else
  echo "uv does not exist."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
if command -v uvx ruff >/dev/null 2>&1; then
  echo "uvx ruff exists."
else
  echo "uvx ruff does not exist."
  uv tool install ruff@latest
fi

uvx ruff check scraping/ video_generation/ opensora/ --fix
uvx ruff format scraping/ video_generation/ opensora/
uvx ruff check scraping/ video_generation/ opensora/
uvx ruff format --diff scraping/ video_generation/ opensora/