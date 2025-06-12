"""Message processing utilities for Telegram bot."""

import re
from typing import Optional, Dict, Any, List
from telegram import Update, User, Chat
from src.models.ticket import TicketRequest, LLMProcessingRequest, MediaAttachment
from src.utils.logger import get_logger
from src.utils.media_processor import MediaProcessor

logger = get_logger(__name__)


class MessageProcessor:
    """Processes Telegram messages for ticket creation."""
    
    def __init__(self):
        # Regex pattern to detect #ticket hashtag
        self.ticket_pattern = re.compile(r'#ticket\b', re.IGNORECASE)
        
        # Minimum message length for ticket creation
        self.min_message_length = 10
        
        # Media processor for handling attachments
        self.media_processor = MediaProcessor()
    
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
    
    def validate_message_for_ticket(self, message_text: str, has_media: bool = False) -> tuple[bool, Optional[str]]:
        """
        Validate if message is suitable for ticket creation.
        
        Args:
            message_text: The message text to validate
            has_media: Whether the message has media attachments
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not message_text:
            return False, "Message is empty"
        
        if not self.contains_ticket_hashtag(message_text):
            return False, "Message does not contain #ticket hashtag"
        
        ticket_content = self.extract_ticket_content(message_text)
        
        # If there are media attachments, allow shorter text content
        min_length = 5 if has_media else self.min_message_length
        
        if len(ticket_content) < min_length:
            if has_media:
                return False, f"Ticket content too short (minimum {min_length} characters with media)"
            else:
                return False, f"Ticket content too short (minimum {min_length} characters)"
        
        # Check for common spam patterns (skip if only media with minimal text)
        if not has_media and self._is_spam_like(ticket_content):
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
    
    def extract_media_attachments(self, update: Update) -> List[MediaAttachment]:
        """
        Extract media attachments from Telegram update.
        
        Args:
            update: Telegram update object
            
        Returns:
            List of MediaAttachment objects
        """
        return self.media_processor.extract_media_from_update(update)
    
    def create_ticket_request(self, update: Update) -> Optional[TicketRequest]:
        """
        Create a TicketRequest from Telegram update.
        
        Args:
            update: Telegram update object
            
        Returns:
            TicketRequest object or None if invalid
        """
        if not update.message:
            logger.warning("Received update without message")
            return None
        
        message = update.message
        user = message.from_user
        chat = message.chat
        
        # Extract media attachments
        media_attachments = self.extract_media_attachments(update)
        has_media = len(media_attachments) > 0
        
        # Handle messages with only media and #ticket hashtag
        message_text = message.text or message.caption or ""
        if not message_text and has_media:
            message_text = "#ticket"  # Default text for media-only tickets
        
        if not message_text:
            logger.warning("Received update without message text or caption")
            return None
        
        # Validate message
        is_valid, error = self.validate_message_for_ticket(message_text, has_media)
        if not is_valid:
            logger.info(f"Invalid ticket message from user {user.id}: {error}")
            return None
        
        # Extract ticket content
        ticket_content = self.extract_ticket_content(message_text)
        
        # Add media context to ticket content if attachments exist
        if media_attachments:
            media_summary = self.media_processor.get_attachment_summary(media_attachments)
            ticket_content = f"{ticket_content}\n\nAttachments: {media_summary}".strip()
        
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
            original_message=message_text,
            message_id=message.message_id
        )
        
        logger.info(f"Created ticket request for user {user.id} in chat {chat.id} with {len(media_attachments)} attachments")
        return ticket_request
    
    def create_llm_request(self, update: Update) -> Optional[LLMProcessingRequest]:
        """
        Create an LLM processing request from Telegram update.
        
        Args:
            update: Telegram update object
            
        Returns:
            LLMProcessingRequest object or None if invalid
        """
        if not update.message:
            return None
        
        message = update.message
        user = message.from_user
        chat = message.chat
        
        # Extract media attachments
        media_attachments = self.extract_media_attachments(update)
        has_media = len(media_attachments) > 0
        
        # Handle messages with only media and #ticket hashtag
        message_text = message.text or message.caption or ""
        if not message_text and has_media:
            message_text = "#ticket"  # Default text for media-only tickets
        
        if not message_text:
            return None
        
        # Validate message
        is_valid, error = self.validate_message_for_ticket(message_text, has_media)
        if not is_valid:
            return None
        
        # Extract ticket content
        ticket_content = self.extract_ticket_content(message_text)
        
        # Add media context to ticket content if attachments exist
        if media_attachments:
            media_summary = self.media_processor.get_attachment_summary(media_attachments)
            ticket_content = f"{ticket_content}\n\nAttachments: {media_summary}".strip()
        
        return LLMProcessingRequest(
            message_content=ticket_content,
            user_context=self._get_user_context(user),
            chat_context=self._get_chat_context(chat),
            media_attachments=media_attachments
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

**Media Support:**
📎 Attach images, videos, or documents to your ticket
🖼️ Screenshots help illustrate UI/UX issues
🎥 Screen recordings show step-by-step problems
📄 Log files and documents provide technical context

**Tips:**
• Be descriptive - more details help create better tickets
• Include priority indicators (high, urgent, low) if needed
• Mention affected components or areas when possible
• Attach relevant media files for better context

The bot will automatically:
✅ Extract a clear title and description
✅ Assign appropriate priority and issue type
✅ Add relevant labels and components
✅ Upload and attach media files to Jira
✅ Create the ticket in Jira
✅ Send you the ticket link"""