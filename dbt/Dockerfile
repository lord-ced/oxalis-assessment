FROM python:3.11.6-slim

# Set working directory
WORKDIR /dbt

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install dbt-core and dbt-postgres
RUN pip install --no-cache-dir \
    dbt-core==1.6.6 \
    dbt-postgres==1.6.6

# Copy dbt project files
COPY . .

# Default command (will be overridden by docker-compose)
CMD ["dbt", "debug"]