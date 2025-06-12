"""Telegram bot implementation for TG-Jira integration."""

import asyncio
from typing import Optional, Dict, Any
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram.constants import ParseMode
from src.models.config import Settings
from src.models.ticket import TicketRequest, LLMProcessingRequest
from src.bot.message_processor import MessageProcessor
from src.integrations.openrouter_client import OpenRouterClient
from src.integrations.jira_client import JiraClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TelegramBot:
    """Telegram bot for creating Jira tickets from chat messages."""
    
    def __init__(
        self,
        settings: Settings,
        openrouter_client: OpenRouterClient,
        jira_client: JiraClient
    ):
        self.settings = settings
        self.openrouter_client = openrouter_client
        self.jira_client = jira_client
        self.message_processor = MessageProcessor()
        
        # Initialize bot application
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        
        # Setup handlers
        self._setup_handlers()
        
        # Bot statistics
        self.stats = {
            "messages_processed": 0,
            "tickets_created": 0,
            "errors": 0
        }
    
    def _setup_handlers(self):
        """Setup Telegram bot handlers."""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("stats", self._stats_command))
        self.application.add_handler(CommandHandler("health", self._health_command))
        
        # Message handler for ticket creation
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_message
            )
        )
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
    
    async def _start_command(self, update: Update, context) -> None:
        """Handle /start command."""
        welcome_message = """🎫 **Welcome to TG-Jira Bot!**

I help you create Jira tickets directly from Telegram messages.

**How to use:**
Send a message containing `#ticket` followed by your issue description, and I'll automatically create a Jira ticket for you.

**Example:**
`#ticket The login button is not working on mobile devices`

**Commands:**
• `/help` - Show detailed help
• `/stats` - Show bot statistics
• `/health` - Check bot health status

Let's get started! 🚀"""
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"Start command from user {update.effective_user.id}")
    
    async def _help_command(self, update: Update, context) -> None:
        """Handle /help command."""
        help_message = self.message_processor.get_help_message()
        
        await update.message.reply_text(
            help_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"Help command from user {update.effective_user.id}")
    
    async def _stats_command(self, update: Update, context) -> None:
        """Handle /stats command."""
        stats_message = f"""📊 **Bot Statistics**

**Messages Processed:** {self.stats['messages_processed']}
**Tickets Created:** {self.stats['tickets_created']}
**Errors:** {self.stats['errors']}

**Success Rate:** {(self.stats['tickets_created'] / max(1, self.stats['messages_processed']) * 100):.1f}%

**Jira Authentication:** {'✅ Connected' if self.jira_client.is_authenticated() else '❌ Not authenticated'}"""
        
        await update.message.reply_text(
            stats_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"Stats command from user {update.effective_user.id}")
    
    async def _health_command(self, update: Update, context) -> None:
        """Handle /health command."""
        try:
            # Check all services
            telegram_status = "✅ Connected"
            
            openrouter_health = await self.openrouter_client.health_check()
            openrouter_status = "✅ Healthy" if openrouter_health.get("status") == "healthy" else "❌ Unhealthy"
            
            jira_health = await self.jira_client.health_check()
            jira_status_map = {
                "healthy": "✅ Healthy",
                "authentication_required": "🔐 Auth Required",
                "unhealthy": "❌ Unhealthy"
            }
            jira_status = jira_status_map.get(jira_health.get("status"), "❓ Unknown")
            
            # Add authentication help if needed
            auth_help = ""
            if jira_health.get("status") == "authentication_required":
                auth_help = f"\n\n🔑 **To authorize Jira:**\nVisit: `{self.settings.host}:{self.settings.port}/auth/jira`"
            
            health_message = f"""🏥 **Health Status**

**Telegram Bot:** {telegram_status}
**OpenRouter API:** {openrouter_status}
**Jira API:** {jira_status}

**Overall Status:** {'✅ All systems operational' if all(s.startswith('✅') for s in [telegram_status, openrouter_status, jira_status]) else '⚠️ Some issues detected'}{auth_help}"""
            
            await update.message.reply_text(
                health_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            await update.message.reply_text(
                "❌ **Health check failed**\n\nUnable to check system status.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        logger.info(f"Health command from user {update.effective_user.id}")
    
    async def _handle_message(self, update: Update, context) -> None:
        """Handle incoming messages for ticket creation."""
        try:
            self.stats["messages_processed"] += 1
            
            # Check if message contains ticket hashtag
            if not self.message_processor.contains_ticket_hashtag(update.message.text):
                return  # Ignore messages without #ticket
            
            logger.info(f"Processing ticket request from user {update.effective_user.id}")
            
            # Validate message
            is_valid, error = self.message_processor.validate_message_for_ticket(update.message.text)
            if not is_valid:
                await update.message.reply_text(
                    self.message_processor.format_error_message(error),
                    parse_mode=ParseMode.MARKDOWN
                )
                self.stats["errors"] += 1
                return
            
            # Send processing message
            processing_msg = await update.message.reply_text(
                self.message_processor.format_processing_message(),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Create LLM processing request
            llm_request = self.message_processor.create_llm_request(update)
            if not llm_request:
                await processing_msg.edit_text(
                    "❌ **Error**: Failed to process message",
                    parse_mode=ParseMode.MARKDOWN
                )
                self.stats["errors"] += 1
                return
            
            # Process with OpenRouter LLM
            llm_response = await self.openrouter_client.process_message(llm_request)
            
            if not llm_response.success or not llm_response.ticket_data:
                error_msg = llm_response.error_message or "Failed to process message content"
                await processing_msg.edit_text(
                    f"❌ **Error**: {error_msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
                self.stats["errors"] += 1
                return
            
            # Check Jira authentication
            if not self.jira_client.is_authenticated():
                auth_url = self.jira_client.get_authorization_url()
                await processing_msg.edit_text(
                    f"🔐 **Jira Authentication Required**\n\n"
                    f"The bot needs to be authorized to create Jira tickets.\n\n"
                    f"**Admin**: Please visit this URL to authorize:\n"
                    f"[Authorize Bot]({auth_url})\n\n"
                    f"Or visit: `{self.settings.host}:{self.settings.port}/auth/jira`",
                    parse_mode=ParseMode.MARKDOWN
                )
                self.stats["errors"] += 1
                return
            
            # Create Jira ticket
            ticket_response = await self.jira_client.create_ticket(llm_response.ticket_data)
            
            if ticket_response.success:
                # Success message
                success_message = ticket_response.formatted_response
                
                # Add confidence info if available
                if llm_response.confidence_score:
                    confidence_emoji = "🎯" if llm_response.confidence_score > 0.8 else "📊"
                    success_message += f"\n\n{confidence_emoji} Processing confidence: {llm_response.confidence_score:.0%}"
                
                await processing_msg.edit_text(
                    success_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                self.stats["tickets_created"] += 1
                logger.info(f"Successfully created ticket {ticket_response.ticket_key} for user {update.effective_user.id}")
                
            else:
                # Error message
                await processing_msg.edit_text(
                    ticket_response.formatted_response,
                    parse_mode=ParseMode.MARKDOWN
                )
                self.stats["errors"] += 1
                logger.error(f"Failed to create ticket: {ticket_response.error_message}")
        
        except Exception as e:
            logger.error(f"Unexpected error handling message: {e}", exc_info=True)
            self.stats["errors"] += 1
            
            try:
                await update.message.reply_text(
                    "❌ **Unexpected Error**\n\nSomething went wrong while processing your request. Please try again later.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass  # Ignore errors when sending error messages
    
    async def _error_handler(self, update: Update, context) -> None:
        """Handle errors in bot operations."""
        logger.error(f"Bot error: {context.error}", exc_info=True)
        self.stats["errors"] += 1
        
        if update and update.message:
            try:
                await update.message.reply_text(
                    "❌ **Bot Error**\n\nAn error occurred while processing your request.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass  # Ignore errors when sending error messages
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """
        Set webhook for the bot.
        
        Args:
            webhook_url: URL for webhook endpoint
            
        Returns:
            True if webhook was set successfully
        """
        try:
            bot = Bot(token=self.settings.telegram_bot_token)
            await bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            return False
    
    async def remove_webhook(self) -> bool:
        """
        Remove webhook for the bot.
        
        Returns:
            True if webhook was removed successfully
        """
        try:
            bot = Bot(token=self.settings.telegram_bot_token)
            await bot.delete_webhook()
            logger.info("Webhook removed")
            return True
        except Exception as e:
            logger.error(f"Failed to remove webhook: {e}")
            return False
    
    async def process_webhook_update(self, update_data: Dict[str, Any]) -> None:
        """
        Process webhook update from Telegram.
        
        Args:
            update_data: Raw update data from webhook
        """
        try:
            update = Update.de_json(update_data, self.application.bot)
            if update:
                await self.application.process_update(update)
        except Exception as e:
            logger.error(f"Failed to process webhook update: {e}", exc_info=True)
    
    async def start_polling(self) -> None:
        """Start bot in polling mode (for development)."""
        logger.info("Starting bot in polling mode")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
    
    async def stop_polling(self) -> None:
        """Stop bot polling."""
        logger.info("Stopping bot polling")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        return self.stats.copy()