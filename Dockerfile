# Use an official Python runtime as a base image
FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the rest of the application code into the container
COPY . .

# Install dependencies and package
RUN uv sync && uv pip install -e .

# Define the command to run your application
CMD ["uv", "run"]