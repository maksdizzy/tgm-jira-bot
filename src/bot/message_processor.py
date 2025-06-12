"""Message processing utilities for Telegram bot."""

import re
from typing import Optional, Dict, Any
from telegram import Update, User, Chat
from src.models.ticket import TicketRequest, LLMProcessingRequest
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MessageProcessor:
    """Processes Telegram messages for ticket creation."""
    
    def __init__(self):
        # Regex pattern to detect #ticket hashtag
        self.ticket_pattern = re.compile(r'#ticket\b', re.IGNORECASE)
        
        # Minimum message length for ticket creation
        self.min_message_length = 10
    
    def contains_ticket_hashtag(self, message_text: str) -> bool:
        """
        Check if message contains #ticket hashtag.
        
        Args:
            message_text: The message text to check
            
        Returns:
            True if message contains #ticket hashtag
        """
        if not message_text:
            return False
        
        return bool(self.ticket_pattern.search(message_text))
    
    def extract_ticket_content(self, message_text: str) -> str:
        """
        Extract ticket content from message, removing the #ticket hashtag.
        
        Args:
            message_text: The original message text
            
        Returns:
            Cleaned message content for ticket processing
        """
        if not message_text:
            return ""
        
        # Remove #ticket hashtag and clean up whitespace
        cleaned = self.ticket_pattern.sub('', message_text).strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def validate_message_for_ticket(self, message_text: str) -> tuple[bool, Optional[str]]:
        """
        Validate if message is suitable for ticket creation.
        
        Args:
            message_text: The message text to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not message_text:
            return False, "Message is empty"
        
        if not self.contains_ticket_hashtag(message_text):
            return False, "Message does not contain #ticket hashtag"
        
        ticket_content = self.extract_ticket_content(message_text)
        
        if len(ticket_content) < self.min_message_length:
            return False, f"Ticket content too short (minimum {self.min_message_length} characters)"
        
        # Check for common spam patterns
        if self._is_spam_like(ticket_content):
            return False, "Message appears to be spam or invalid"
        
        return True, None
    
    def _is_spam_like(self, content: str) -> bool:
        """
        Check if content appears to be spam or invalid.
        
        Args:
            content: Content to check
            
        Returns:
            True if content appears to be spam
        """
        # Check for excessive repetition
        words = content.lower().split()
        if len(words) > 3:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:  # Less than 30% unique words
                return True
        
        # Check for excessive special characters
        special_char_ratio = sum(1 for c in content if not c.isalnum() and not c.isspace()) / len(content)
        if special_char_ratio > 0.5:
            return True
        
        return False
    
    def create_ticket_request(self, update: Update) -> Optional[TicketRequest]:
        """
        Create a TicketRequest from Telegram update.
        
        Args:
            update: Telegram update object
            
        Returns:
            TicketRequest object or None if invalid
        """
        if not update.message or not update.message.text:
            logger.warning("Received update without message text")
            return None
        
        message = update.message
        user = message.from_user
        chat = message.chat
        
        # Validate message
        is_valid, error = self.validate_message_for_ticket(message.text)
        if not is_valid:
            logger.info(f"Invalid ticket message from user {user.id}: {error}")
            return None
        
        # Extract ticket content
        ticket_content = self.extract_ticket_content(message.text)
        
        # Create LLM processing request
        llm_request = LLMProcessingRequest(
            message_content=ticket_content,
            user_context=self._get_user_context(user),
            chat_context=self._get_chat_context(chat)
        )
        
        # Create ticket request
        ticket_request = TicketRequest(
            ticket_data=None,  # Will be populated after LLM processing
            telegram_user_id=user.id,
            telegram_username=user.username,
            telegram_chat_id=chat.id,
            original_message=message.text,
            message_id=message.message_id
        )
        
        logger.info(f"Created ticket request for user {user.id} in chat {chat.id}")
        return ticket_request
    
    def create_llm_request(self, update: Update) -> Optional[LLMProcessingRequest]:
        """
        Create an LLM processing request from Telegram update.
        
        Args:
            update: Telegram update object
            
        Returns:
            LLMProcessingRequest object or None if invalid
        """
        if not update.message or not update.message.text:
            return None
        
        message = update.message
        user = message.from_user
        chat = message.chat
        
        # Validate message
        is_valid, error = self.validate_message_for_ticket(message.text)
        if not is_valid:
            return None
        
        # Extract ticket content
        ticket_content = self.extract_ticket_content(message.text)
        
        return LLMProcessingRequest(
            message_content=ticket_content,
            user_context=self._get_user_context(user),
            chat_context=self._get_chat_context(chat)
        )
    
    def _get_user_context(self, user: User) -> str:
        """
        Extract user context information.
        
        Args:
            user: Telegram user object
            
        Returns:
            User context string
        """
        context_parts = []
        
        if user.first_name:
            context_parts.append(f"First name: {user.first_name}")
        
        if user.last_name:
            context_parts.append(f"Last name: {user.last_name}")
        
        if user.username:
            context_parts.append(f"Username: @{user.username}")
        
        return " | ".join(context_parts) if context_parts else "Unknown user"
    
    def _get_chat_context(self, chat: Chat) -> str:
        """
        Extract chat context information.
        
        Args:
            chat: Telegram chat object
            
        Returns:
            Chat context string
        """
        context_parts = []
        
        context_parts.append(f"Chat type: {chat.type}")
        
        if chat.title:
            context_parts.append(f"Chat title: {chat.title}")
        
        if chat.username:
            context_parts.append(f"Chat username: @{chat.username}")
        
        context_parts.append(f"Chat ID: {chat.id}")
        
        return " | ".join(context_parts)
    
    def format_error_message(self, error: str) -> str:
        """
        Format error message for user display.
        
        Args:
            error: Error message
            
        Returns:
            Formatted error message
        """
        return f"❌ **Error**: {error}\n\n💡 **Tip**: Use `#ticket` followed by a description of your issue."
    
    def format_processing_message(self) -> str:
        """
        Format processing message for user display.
        
        Returns:
            Processing message
        """
        return "🔄 **Processing your ticket request...**\n\nPlease wait while I analyze your message and create a Jira ticket."
    
    def get_help_message(self) -> str:
        """
        Get help message for ticket creation.
        
        Returns:
            Help message
        """
        return """🎫 **Ticket Creation Help**

To create a Jira ticket, send a message containing `#ticket` followed by your issue description.

**Examples:**
• `#ticket The login button is not working on mobile`
• `#ticket High priority: Database timeout errors`
• `#ticket Feature request: Add dark mode to dashboard`

**Tips:**
• Be descriptive - more details help create better tickets
• Include priority indicators (high, urgent, low) if needed
• Mention affected components or areas when possible

The bot will automatically:
✅ Extract a clear title and description
✅ Assign appropriate priority and issue type
✅ Add relevant labels and components
✅ Create the ticket in Jira
✅ Send you the ticket link"""