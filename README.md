# 📈 Stock Price Predictor

A comprehensive Django-based stock price prediction application with machine learning capabilities, REST API, web dashboard, and Telegram bot integration.

## ✨ Features

- 🤖 **Machine Learning Predictions**: Advanced TensorFlow/Keras models for stock price forecasting
- 📊 **Web Dashboard**: Interactive web interface for making predictions and viewing results
- 🚀 **REST API**: RESTful API with JWT authentication
- 🤖 **Telegram Bot**: Get predictions directly via Telegram
- 📈 **Historical Data**: Fetch and analyze historical stock data using Yahoo Finance
- 🔒 **Rate Limiting**: Built-in rate limiting to prevent abuse
- 📱 **Responsive Design**: Modern, mobile-friendly web interface
- 🔄 **Async Processing**: Celery task queue for handling predictions
- 🐳 **Docker Support**: Containerized deployment with Docker Compose
- 📊 **Visualization**: Interactive charts and graphs for predictions

## 🛠️ Tech Stack

- **Backend**: Django 5.0.6, Django REST Framework
- **Machine Learning**: TensorFlow 2.19.0, Scikit-learn
- **Database**: SQLite (default), PostgreSQL, MySQL, MSSQL support
- **Cache/Queue**: Redis, Celery
- **Data Source**: Yahoo Finance API (yfinance)
- **Visualization**: Matplotlib
- **Telegram**: python-telegram-bot
- **Deployment**: Docker, Gunicorn, Nginx-ready

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Redis server
- Git

### Method 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/jitendra-ky/price_predictor
   cd price_predictor
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your configuration:

3. **Build and run with Docker**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Web Dashboard: http://localhost:8000/dashboard/

### Method 2: Local Development Setup

1. **Clone and setup virtual environment**
   ```bash
   git clone https://github.com/jitendra-ky/price_predictor
   cd price_predictor
   python -m venv .venv
   source .venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Redis**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis-server
   
   # macOS
   brew install redis
   brew services start redis
   
   # Windows
   # Download and install Redis from https://redis.io/download
   ```

4. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Start services**
   
   **Terminal 1 - Django Server:**
   ```bash
   python manage.py runserver
   ```
   
   **Terminal 2 - Celery Worker: (only needed for telegram bot)**
   ```bash
   python manage.py startcelery
   ```
   
   **Terminal 3 - Telegram Bot:**
   ```bash
   python manage.py telegrambot
   ```

## 📝 Configuration

### Environment Variables

Create a `.env` file in the root directory:
check `.env.example`

## 🎯 Usage

### Web Dashboard

1. Navigate to `http://localhost:8000/dashboard`
2. Register a new account or login
3. Enter a stock ticker symbol (e.g., AAPL, GOOGL, TSLA)
4. Click "Predict" to get ML-powered predictions
5. View interactive charts and metrics

### Telegram Bot

1. Start a chat with your bot
2. Use `/start` to begin
3. Use `/predict AAPL` to get predictions for Apple stock
4. Use `/help` for all available commands
5. use `/latest` to get recent prediction

## 🔧 Development

### Project Structure

```
price_predictor/
├── core/                    # Main application
│   ├── management/commands/ # Django management commands
│   ├── services/           # Business logic
│   ├── telegram/          # Telegram bot integration
│   └── utils/             # Utility functions
├── user/                   # User management
├── templates/             # HTML templates
├── static/               # Static files
├── media/                # User uploads
├── zproject/             # Django settings
└── requirements.txt      # Python dependencies
```

### Running Tests

```bash
python manage.py test
```

### Code Quality

```bash
# Run linting
ruff check .

```

## 🔍 API Documentation

### Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/register/` | Register new user | No |
| GET | `/api/v1/register/` | Get user profile | Yes |
| POST | `/api/v1/token/` | Get JWT token | No |
| POST | `/api/v1/token/refresh/` | Refresh JWT token | No |
| POST | `/api/v1/predict/` | Make stock prediction | Yes |
| GET | `/api/v1/predictions/` | Get user predictions | Yes |
| GET | `/healthz/` | Health check | No |
