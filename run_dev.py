#!/usr/bin/env python3
"""Development runner script for TG-Jira bot."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models.config import Settings
from src.utils.logger import setup_logging, get_logger


def main():
    """Main development runner."""
    print("🚀 Starting TG-Jira Bot in development mode...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📝 Please copy config/.env.example to .env and configure your settings:")
        print("   cp config/.env.example .env")
        print("   # Then edit .env with your actual credentials")
        return
    
    try:
        # Load settings
        settings = Settings()
        
        # Setup logging
        setup_logging(log_level=settings.log_level)
        logger = get_logger(__name__)
        
        logger.info("🔧 Development mode configuration:")
        logger.info(f"   Environment: {settings.environment}")
        logger.info(f"   Log Level: {settings.log_level}")
        logger.info(f"   Host: {settings.host}:{settings.port}")
        logger.info(f"   Webhook URL: {settings.telegram_webhook_url or 'Not configured (polling mode)'}")
        
        # Check required credentials
        missing_creds = []
        if not settings.telegram_bot_token:
            missing_creds.append("TELEGRAM_BOT_TOKEN")
        if not settings.openrouter_api_key:
            missing_creds.append("OPENROUTER_API_KEY")
        if not settings.jira_client_id:
            missing_creds.append("JIRA_CLIENT_ID")
        if not settings.jira_client_secret:
            missing_creds.append("JIRA_CLIENT_SECRET")
        if not settings.secret_key:
            missing_creds.append("SECRET_KEY")
        
        if missing_creds:
            print(f"❌ Missing required environment variables: {', '.join(missing_creds)}")
            print("📝 Please configure these in your .env file")
            return
        
        print("✅ Configuration looks good!")
        print("\n🔗 Available endpoints:")
        print(f"   Health Check: http://{settings.host}:{settings.port}/health")
        print(f"   API Docs: http://{settings.host}:{settings.port}/docs")
        print(f"   Jira Auth: http://{settings.host}:{settings.port}/auth/jira")
        
        if not settings.jira_access_token:
            print("\n⚠️  Jira not authenticated yet!")
            print(f"   Visit http://{settings.host}:{settings.port}/auth/jira to authenticate")
        
        print(f"\n🤖 Starting server on {settings.host}:{settings.port}...")
        print("   Press Ctrl+C to stop")
        
        # Import and run the FastAPI app
        import uvicorn
        uvicorn.run(
            "src.main:app",
            host=settings.host,
            port=settings.port,
            reload=True,
            log_level=settings.log_level.lower()
        )
        
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)