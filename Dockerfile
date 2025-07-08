# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build tools
    build-essential \
    # For TensorFlow
    libhdf5-dev \
    pkg-config \
    # For Redis
    redis-server \
    # For database connections
    libpq-dev \
    # For mysqlclient
    default-libmysqlclient-dev \
    # For MSSQL
    curl \
    gnupg \
    # Process management
    supervisor \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC driver for SQL Server
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project (excluding .env and sensitive files)
COPY . .
# Remove any accidentally copied .env files
RUN rm -f .env .env.local .env.*.local

# Create media directories
RUN mkdir -p media/plots mystaticfiles

# Collect static files
RUN python manage.py collectstatic --noinput

# Create supervisor configuration
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create Redis configuration
RUN mkdir -p /etc/redis
COPY redis.conf /etc/redis/redis.conf

# Create startup script
COPY start_all_services.sh /start_all_services.sh
RUN chmod +x /start_all_services.sh

# Expose port
EXPOSE 8000

# Run the startup script
CMD ["/start_all_services.sh"]
