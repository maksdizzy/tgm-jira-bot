# TG-Jira Bot

A production-ready Telegram bot that monitors chat messages for "#ticket" hashtags and automatically creates Jira tickets using OpenRouter LLM for intelligent content processing.

## 🚀 Latest Release - v1.0.0 (Stable)

**Production-ready release** with comprehensive testing and validation completed.

### ✅ Core Features Delivered
- **Telegram Bot Integration**: Webhook-based real-time message processing with #ticket hashtag detection
- **OpenRouter LLM Processing**: Google Gemini 2.5 Flash integration for intelligent ticket content extraction and structuring
- **Jira Cloud OAuth 2.0**: Secure authentication with accessible resources lookup and automatic token refresh
- **FastAPI Web Server**: Production-ready server with comprehensive health checks and monitoring endpoints
- **Docker Containerization**: Multi-stage builds optimized for production deployment
- **Structured Logging**: JSON format with correlation IDs for comprehensive observability

### 🔧 Key Technical Achievements
- **OAuth 2.0 Flow**: Fully implemented with proper Jira Cloud endpoints and token management
- **Simplified Ticket Creation**: Streamlined process handling project, summary, issue type, and description
- **Comprehensive Error Handling**: User-friendly error messages with detailed logging for debugging
- **Pydantic Data Validation**: Type-safe models ensuring data integrity throughout the application
- **Async/Await Architecture**: High-performance asynchronous processing for optimal scalability

## Architecture Overview

This bot integrates three main services:
- **Telegram Bot API** for message monitoring
- **OpenRouter LLM** (Google Gemini 2.5 Flash) for intelligent ticket content processing
- **Jira Cloud API** with OAuth 2.0 for secure ticket creation

```mermaid
graph TB
    A[Telegram Chat] -->|Message with #ticket| B[Telegram Bot API]
    B --> C[FastAPI Webhook Handler]
    C --> D[Message Processor]
    D --> E[OpenRouter LLM]
    E -->|Processed Content| F[Jira API Client]
    F -->|OAuth 2.0| G[Jira Cloud]
    G -->|Ticket Created| H[Response Handler]
    H --> I[Telegram Bot Response]
    I --> A
    
    J[Docker Container] -.-> C
    J -.-> K[Structured Logging]
    J -.-> L[Health Checks]
    J -.-> M[Environment Config]
```

## Features

### Core Functionality
- **Hashtag Detection**: Monitors for "#ticket" in any position within messages
- **Intelligent Processing**: Uses Google Gemini 2.5 Flash to extract structured ticket information
- **Automatic Ticket Creation**: Creates Jira tickets with processed content
- **User Feedback**: Responds with ticket links and confirmation

### LLM Processing Capabilities
- **Smart Title Generation**: Creates concise, descriptive ticket titles (max 100 characters)
- **Detailed Descriptions**: Expands brief messages into comprehensive descriptions with context
- **Priority Assessment**: Automatically assigns priority levels (Highest/High/Medium/Low/Lowest)
- **Issue Type Classification**: Categorizes as Bug/Task/Story/Epic/Improvement/New Feature
- **Label Extraction**: Identifies relevant labels and components from message content
- **Fallback Processing**: Graceful degradation when LLM parsing fails

### Technical Features
- **OAuth 2.0 Authentication**: Secure Jira integration with automatic token refresh
- **Webhook-based**: Real-time message processing via FastAPI webhooks
- **Docker Deployment**: Containerized with health checks and structured logging
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Rate Limiting**: Built-in protection against API abuse

## Project Structure

```
tgm-jira-bot/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py     # Telegram bot setup and handlers
│   │   └── message_processor.py # Message parsing and validation
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── openrouter_client.py # OpenRouter LLM integration
│   │   └── jira_client.py      # Jira OAuth 2.0 and API client
│   ├── models/
│   │   ├── __init__.py
│   │   ├── ticket.py           # Ticket data models
│   │   └── config.py           # Configuration models
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # Structured logging setup
│       ├── health.py           # Health check endpoints
│       ├── media_processor.py  # Media file processing utilities
│       └── token_storage.py    # OAuth token management
├── tests/
│   ├── __init__.py
│   └── test_message_processor.py # Message processing unit tests
├── config/
│   ├── logging.yaml            # Logging configuration
│   └── .env.example            # Environment variables template
├── docker/
│   ├── Dockerfile              # Multi-stage production build
│   └── docker-compose.yml      # Container orchestration
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── setup.py                    # Automated project setup
├── run_dev.py                  # Development server launcher
├── check_auth.py              # OAuth authentication testing
├── test_fixes.py              # Integration testing utilities
├── test_jira_oauth.py         # Jira OAuth flow testing
├── JIRA_OAUTH_SETUP.md        # OAuth setup documentation
├── README.md
└── .gitignore
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant T as Telegram
    participant B as Bot (FastAPI)
    participant O as OpenRouter
    participant J as Jira Cloud
    
    U->>T: Sends message with #ticket
    T->>B: Webhook notification
    B->>B: Parse and validate message
    B->>O: Process content with GPT-4
    O->>B: Return structured ticket data
    B->>J: Create ticket via OAuth 2.0
    J->>B: Return ticket URL
    B->>T: Send confirmation message
    T->>U: Display ticket link
```

## Prerequisites

### Required Accounts and Credentials
1. **Telegram Bot Token**
   - Create a bot via [@BotFather](https://t.me/botfather)
   - Obtain the bot token

2. **OpenRouter API Key**
   - Sign up at [OpenRouter](https://openrouter.ai/)
   - Generate an API key
   - Ensure sufficient credits for Google Gemini 2.5 Flash usage
   - Default model: `google/gemini-2.5-flash-preview-05-20` (configurable)

3. **Jira Cloud OAuth 2.0 Credentials**
   - Access to a Jira Cloud instance
   - OAuth 2.0 app credentials (Client ID and Secret)
   - Appropriate permissions for ticket creation

### System Requirements
- Docker and Docker Compose
- Python 3.11+ (for local development)
- Internet connectivity for API access

## Quick Start

### Automated Setup (Recommended)
```bash
# Clone the repository
git clone <repository-url>
cd tgm-jira-bot

# Run automated setup (creates venv, installs dependencies, copies config)
python setup.py

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Edit .env with your credentials (created from template)
nano .env

# Start development server
python run_dev.py
```

### Production Deployment
```bash
# Clone and configure
git clone <repository-url>
cd tgm-jira-bot
cp config/.env.example .env
# Edit .env with production credentials

# Deploy with Docker
docker-compose up -d

# Verify deployment
curl http://localhost:8000/health
```

## Installation and Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd tgm-jira-bot
```

### 2. Environment Configuration
```bash
cp config/.env.example .env
```

Edit `.env` with your credentials:
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# OpenRouter
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=google/gemini-2.5-flash-preview-05-20

# Jira OAuth 2.0
JIRA_CLOUD_URL=https://your-domain.atlassian.net
JIRA_CLIENT_ID=your_oauth_client_id
JIRA_CLIENT_SECRET=your_oauth_client_secret
JIRA_PROJECT_KEY=your_project_key

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
SECRET_KEY=your_secret_key_here_change_in_production
```

### 3. Docker Deployment
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### 4. Local Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Run the application
python run_dev.py
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather | Yes | - |
| `TELEGRAM_WEBHOOK_URL` | Public URL for webhook endpoint | Yes | - |
| `OPENROUTER_API_KEY` | OpenRouter API key | Yes | - |
| `OPENROUTER_MODEL` | LLM model to use | No | `google/gemini-2.5-flash-preview-05-20` |
| `JIRA_CLOUD_URL` | Jira Cloud instance URL | Yes | - |
| `JIRA_CLIENT_ID` | OAuth 2.0 Client ID | Yes | - |
| `JIRA_CLIENT_SECRET` | OAuth 2.0 Client Secret | Yes | - |
| `JIRA_PROJECT_KEY` | Target Jira project key | Yes | - |
| `LOG_LEVEL` | Logging level | No | `INFO` |
| `ENVIRONMENT` | Environment name | No | `development` |

### Webhook Setup

1. **Set Webhook URL**: Configure your Telegram bot webhook to point to your deployed instance:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://your-domain.com/webhook"}'
   ```

2. **Verify Webhook**: Check webhook status:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```

## Usage

### Basic Usage
1. Add the bot to your Telegram chat
2. Send a message containing `#ticket` followed by your issue description
3. The bot will process the message and create a Jira ticket
4. Receive a confirmation message with the ticket link

### Example Messages
```
#ticket The login button is not working on the mobile app

#ticket High priority: Database connection timeout errors occurring frequently

#ticket Feature request: Add dark mode to the user dashboard
```

### LLM Processing
The bot uses Google Gemini 2.5 Flash via OpenRouter to intelligently process your message and extract:
- **Title**: Concise summary of the issue (max 100 characters)
- **Description**: Detailed explanation with context and expanded details
- **Priority**: Automatically assessed based on content (Highest/High/Medium/Low/Lowest)
- **Issue Type**: Bug, Task, Story, Epic, Improvement, or New Feature
- **Labels**: Relevant tags and keywords (max 5)
- **Components**: Affected system/module names if identifiable

## Monitoring and Health Checks

### Health Endpoints
- `GET /health` - Basic health check
- `GET /ready` - Readiness check for container orchestration

### Logging
The application uses structured JSON logging with the following levels:
- `ERROR`: Critical errors requiring attention
- `WARNING`: Important events that might need investigation
- `INFO`: General operational messages
- `DEBUG`: Detailed debugging information

### Monitoring Metrics
- Ticket creation success/failure rates
- API response times
- Error frequency and types
- Message processing volume

## Security Considerations

1. **Webhook Validation**: All incoming webhooks are validated against Telegram signatures
2. **OAuth 2.0 Security**: Secure token storage with automatic refresh handling
3. **Environment Isolation**: All sensitive data stored in environment variables
4. **Input Validation**: All user inputs are sanitized before processing
5. **Rate Limiting**: Built-in protection against API abuse
6. **Error Handling**: Sensitive information is never exposed in error messages

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_bot.py
```

### Code Quality
```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

### Local Development with ngrok
For local webhook testing:
```bash
# Install ngrok
# Start your local server
python src/main.py

# In another terminal, expose local server
ngrok http 8000

# Update webhook URL with ngrok URL
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-ngrok-url.ngrok.io/webhook"}'
```

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Messages**
   - Verify webhook URL is publicly accessible
   - Check Telegram webhook status with `getWebhookInfo`
   - Ensure SSL certificate is valid

2. **Jira Authentication Errors**
   - Verify OAuth 2.0 credentials are correct
   - Check token expiration and refresh logic
   - Ensure proper Jira permissions

3. **OpenRouter API Errors**
   - Verify API key is valid and has sufficient credits
   - Check rate limiting and quota usage
   - Ensure model name is correct

4. **Docker Container Issues**
   - Check container logs: `docker-compose logs`
   - Verify environment variables are set
   - Ensure all required ports are exposed

### Debug Mode
Enable debug logging by setting `LOG_LEVEL=DEBUG` in your environment variables.

### Testing OAuth Flow
Use the provided testing utilities:
```bash
# Test Jira OAuth authentication
python test_jira_oauth.py

# Check authentication status
python check_auth.py

# Run integration tests
python test_fixes.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Production Status

### ✅ Successfully Tested Features
- **Ticket Creation**: End-to-end ticket creation workflow validated in production
- **OAuth Authentication**: Fully functional with automatic token refresh
- **LLM Processing**: Google Gemini 2.5 Flash successfully extracting structured ticket data
- **API Integrations**: All external API connections working correctly
- **Error Handling**: Comprehensive error recovery and user feedback
- **Logging**: Structured JSON logging with correlation IDs operational

### 🔧 Production Deployment Notes
- Multi-stage Docker builds optimized for production
- Health check endpoints for container orchestration
- Structured logging for monitoring and debugging
- Async/await architecture for high performance
- Comprehensive error handling with user-friendly messages

## License

[Add your license information here]

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error details
3. Create an issue in the repository
4. Include relevant log snippets and configuration details