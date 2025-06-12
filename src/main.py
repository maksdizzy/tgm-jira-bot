"""Main FastAPI application for TG-Jira bot."""

import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
from src.models.config import Settings
from src.models.ticket import TicketResponse
from src.bot.telegram_bot import TelegramBot
from src.integrations.openrouter_client import OpenRouterClient
from src.integrations.jira_client import JiraClient
from src.utils.logger import setup_logging, get_logger
from src.utils.health import health_checker

# Global variables for dependency injection
settings: Settings = None
telegram_bot: TelegramBot = None
openrouter_client: OpenRouterClient = None
jira_client: JiraClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global settings, telegram_bot, openrouter_client, jira_client
    
    # Startup
    logger.info("Starting TG-Jira Bot application")
    
    # Load settings
    settings = Settings()
    
    # Setup logging
    setup_logging(log_level=settings.log_level)
    
    # Initialize clients
    openrouter_client = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        model=settings.openrouter_model
    )
    
    jira_client = JiraClient(
        cloud_url=settings.jira_cloud_url,
        client_id=settings.jira_client_id,
        client_secret=settings.jira_client_secret,
        redirect_uri=settings.jira_redirect_uri,
        project_key=settings.jira_project_key,
        access_token=settings.jira_access_token,
        refresh_token=settings.jira_refresh_token
    )
    
    # Initialize Telegram bot
    telegram_bot = TelegramBot(
        settings=settings,
        openrouter_client=openrouter_client,
        jira_client=jira_client
    )
    
    # Initialize the Telegram application
    await telegram_bot.application.initialize()
    
    # Set webhook if webhook URL is configured
    if settings.telegram_webhook_url:
        webhook_success = await telegram_bot.set_webhook(settings.telegram_webhook_url)
        if webhook_success:
            logger.info("Webhook mode enabled")
        else:
            logger.error("Failed to set webhook, check configuration")
    else:
        logger.warning("No webhook URL configured, webhook mode disabled")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TG-Jira Bot application")
    
    # Remove webhook
    if settings.telegram_webhook_url:
        await telegram_bot.remove_webhook()
    
    # Shutdown Telegram application
    await telegram_bot.application.shutdown()
    
    # Close clients
    await openrouter_client.close()
    await jira_client.close()
    
    logger.info("Application shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="TG-Jira Bot",
    description="Telegram bot for creating Jira tickets with LLM processing",
    version="1.0.0",
    lifespan=lifespan
)

# Setup logger
logger = get_logger(__name__)


def get_settings() -> Settings:
    """Dependency to get settings."""
    return settings


def get_telegram_bot() -> TelegramBot:
    """Dependency to get Telegram bot."""
    return telegram_bot


def get_jira_client() -> JiraClient:
    """Dependency to get Jira client."""
    return jira_client


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "TG-Jira Bot API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/webhook")
async def webhook(
    request: Request,
    bot: TelegramBot = Depends(get_telegram_bot)
):
    """
    Telegram webhook endpoint.
    
    Receives updates from Telegram and processes them.
    """
    try:
        # Get raw update data
        update_data = await request.json()
        
        logger.debug(f"Received webhook update: {update_data}")
        
        # Process update with bot
        await bot.process_webhook_update(update_data)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    try:
        health_result = await health_checker.basic_health_check()
        return health_result
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/ready")
async def readiness_check(
    settings: Settings = Depends(get_settings),
    bot: TelegramBot = Depends(get_telegram_bot)
):
    """Readiness check for container orchestration."""
    try:
        # Check if all required components are initialized
        checks = {
            "settings_loaded": settings is not None,
            "bot_initialized": bot is not None,
            "jira_configured": bool(settings.jira_client_id and settings.jira_client_secret),
            "openrouter_configured": bool(settings.openrouter_api_key),
            "telegram_configured": bool(settings.telegram_bot_token)
        }
        
        all_ready = all(checks.values())
        
        return {
            "ready": all_ready,
            "checks": checks,
            "timestamp": health_checker.basic_health_check()["timestamp"]
        }
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail="Readiness check failed")


@app.get("/health/comprehensive")
async def comprehensive_health_check(
    settings: Settings = Depends(get_settings)
):
    """Comprehensive health check of all dependencies."""
    try:
        # Get cached result if available
        cached_result = health_checker.get_cached_health()
        if cached_result:
            return cached_result
        
        # Perform comprehensive check
        health_result = await health_checker.comprehensive_health_check(
            telegram_token=settings.telegram_bot_token,
            openrouter_key=settings.openrouter_api_key,
            openrouter_url=settings.openrouter_base_url,
            jira_url=settings.jira_cloud_url,
            jira_token=settings.jira_access_token
        )
        
        return health_result
    
    except Exception as e:
        logger.error(f"Comprehensive health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/stats")
async def get_stats(bot: TelegramBot = Depends(get_telegram_bot)):
    """Get bot statistics."""
    try:
        stats = bot.get_stats()
        return {
            "bot_stats": stats,
            "jira_authenticated": jira_client.is_authenticated() if jira_client else False
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@app.get("/auth/jira")
async def jira_auth_start(jira: JiraClient = Depends(get_jira_client)):
    """Start Jira OAuth 2.0 authentication flow."""
    try:
        auth_url = jira.get_authorization_url()
        return {
            "auth_url": auth_url,
            "message": "Visit the auth_url to authorize the application"
        }
    except Exception as e:
        logger.error(f"Failed to start Jira auth: {e}")
        raise HTTPException(status_code=500, detail="Failed to start authentication")


@app.get("/auth/callback")
async def jira_auth_callback(
    code: str,
    state: str = None,
    jira: JiraClient = Depends(get_jira_client)
):
    """Handle Jira OAuth 2.0 callback."""
    try:
        # Exchange code for tokens
        access_token, refresh_token = await jira.exchange_code_for_tokens(code)
        
        logger.info("Jira OAuth authentication successful")
        
        return {
            "success": True,
            "message": "Authentication successful",
            "access_token": access_token[:10] + "..." if access_token else None,
            "has_refresh_token": bool(refresh_token)
        }
    
    except Exception as e:
        logger.error(f"Jira auth callback failed: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@app.post("/test/ticket")
async def test_ticket_creation(
    request: Dict[str, Any],
    bot: TelegramBot = Depends(get_telegram_bot)
):
    """Test endpoint for ticket creation (development only)."""
    try:
        if not settings.environment == "development":
            raise HTTPException(status_code=403, detail="Test endpoint only available in development")
        
        message_content = request.get("message", "Test ticket from API")
        
        # Create mock LLM request
        from src.models.ticket import LLMProcessingRequest
        llm_request = LLMProcessingRequest(
            message_content=message_content,
            user_context="Test user",
            chat_context="Test chat"
        )
        
        # Process with OpenRouter
        llm_response = await openrouter_client.process_message(llm_request)
        
        if not llm_response.success:
            return {"success": False, "error": llm_response.error_message}
        
        # Create Jira ticket
        ticket_response = await jira_client.create_ticket(llm_response.ticket_data)
        
        return {
            "success": ticket_response.success,
            "ticket_key": ticket_response.ticket_key,
            "ticket_url": ticket_response.ticket_url,
            "error": ticket_response.error_message,
            "processed_data": llm_response.ticket_data.dict() if llm_response.ticket_data else None
        }
    
    except Exception as e:
        logger.error(f"Test ticket creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # For development - run with uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )