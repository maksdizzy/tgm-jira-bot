"""Media processing utilities for Telegram attachments."""

import os
import tempfile
import aiofiles
from pathlib import Path
from typing import List, Optional, Tuple
from telegram import Update, PhotoSize, Video, Document, Audio, VideoNote, Voice
from src.models.ticket import MediaAttachment, MediaType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MediaProcessor:
    """Processes media attachments from Telegram messages."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize media processor.
        
        Args:
            temp_dir: Temporary directory for file downloads
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "tgm_jira_bot"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Supported file extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v'}
        self.document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.log', '.json', '.xml'}
        self.audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}
        
        # File size limits (in bytes)
        self.max_file_size = 50 * 1024 * 1024  # 50MB
    
    def extract_media_from_update(self, update: Update) -> List[MediaAttachment]:
        """
        Extract media attachments from Telegram update.
        
        Args:
            update: Telegram update object
            
        Returns:
            List of MediaAttachment objects
        """
        attachments = []
        
        if not update.message:
            logger.debug("No message in update")
            return attachments
        
        message = update.message
        
        # Debug logging
        logger.debug(f"Message type: {type(message)}")
        logger.debug(f"Message attributes: {dir(message)}")
        logger.debug(f"Message content_type: {getattr(message, 'content_type', 'unknown')}")
        logger.debug(f"Has photo: {bool(message.photo)}")
        logger.debug(f"Has video: {bool(message.video)}")
        logger.debug(f"Has document: {bool(message.document)}")
        logger.debug(f"Has audio: {bool(message.audio)}")
        logger.debug(f"Has voice: {bool(message.voice)}")
        logger.debug(f"Has video_note: {bool(message.video_note)}")
        
        # Check if message has any media at all
        if hasattr(message, 'effective_attachment'):
            logger.debug(f"Effective attachment: {message.effective_attachment}")
        
        # Process photos
        if message.photo:
            logger.debug(f"Processing {len(message.photo)} photo sizes")
            # Get the largest photo size
            largest_photo = max(message.photo, key=lambda p: p.file_size or 0)
            attachment = self._create_photo_attachment(largest_photo)
            if attachment:
                attachments.append(attachment)
                logger.debug(f"Added photo attachment: {attachment.file_id}")
        
        # Process video
        if message.video:
            attachment = self._create_video_attachment(message.video)
            if attachment:
                attachments.append(attachment)
        
        # Process video note (circular video)
        if message.video_note:
            attachment = self._create_video_note_attachment(message.video_note)
            if attachment:
                attachments.append(attachment)
        
        # Process document
        if message.document:
            attachment = self._create_document_attachment(message.document)
            if attachment:
                attachments.append(attachment)
        
        # Process audio
        if message.audio:
            attachment = self._create_audio_attachment(message.audio)
            if attachment:
                attachments.append(attachment)
        
        # Process voice message
        if message.voice:
            attachment = self._create_voice_attachment(message.voice)
            if attachment:
                attachments.append(attachment)
        
        logger.info(f"Extracted {len(attachments)} media attachments from message")
        return attachments
    
    def _create_photo_attachment(self, photo: PhotoSize) -> Optional[MediaAttachment]:
        """Create MediaAttachment from PhotoSize."""
        try:
            return MediaAttachment(
                file_id=photo.file_id,
                file_unique_id=photo.file_unique_id,
                file_size=photo.file_size,
                media_type=MediaType.IMAGE,
                width=photo.width,
                height=photo.height,
                mime_type="image/jpeg"  # Telegram photos are always JPEG
            )
        except Exception as e:
            logger.error(f"Error creating photo attachment: {e}")
            return None
    
    def _create_video_attachment(self, video: Video) -> Optional[MediaAttachment]:
        """Create MediaAttachment from Video."""
        try:
            return MediaAttachment(
                file_id=video.file_id,
                file_unique_id=video.file_unique_id,
                file_name=video.file_name,
                file_size=video.file_size,
                mime_type=video.mime_type,
                media_type=MediaType.VIDEO,
                width=video.width,
                height=video.height,
                duration=video.duration
            )
        except Exception as e:
            logger.error(f"Error creating video attachment: {e}")
            return None
    
    def _create_video_note_attachment(self, video_note: VideoNote) -> Optional[MediaAttachment]:
        """Create MediaAttachment from VideoNote."""
        try:
            return MediaAttachment(
                file_id=video_note.file_id,
                file_unique_id=video_note.file_unique_id,
                file_size=video_note.file_size,
                media_type=MediaType.VIDEO,
                width=video_note.length,
                height=video_note.length,
                duration=video_note.duration,
                mime_type="video/mp4"
            )
        except Exception as e:
            logger.error(f"Error creating video note attachment: {e}")
            return None
    
    def _create_document_attachment(self, document: Document) -> Optional[MediaAttachment]:
        """Create MediaAttachment from Document."""
        try:
            # Determine media type based on MIME type or file extension
            media_type = self._determine_media_type(document.file_name, document.mime_type)
            
            return MediaAttachment(
                file_id=document.file_id,
                file_unique_id=document.file_unique_id,
                file_name=document.file_name,
                file_size=document.file_size,
                mime_type=document.mime_type,
                media_type=media_type
            )
        except Exception as e:
            logger.error(f"Error creating document attachment: {e}")
            return None
    
    def _create_audio_attachment(self, audio: Audio) -> Optional[MediaAttachment]:
        """Create MediaAttachment from Audio."""
        try:
            return MediaAttachment(
                file_id=audio.file_id,
                file_unique_id=audio.file_unique_id,
                file_name=audio.file_name,
                file_size=audio.file_size,
                mime_type=audio.mime_type,
                media_type=MediaType.AUDIO,
                duration=audio.duration
            )
        except Exception as e:
            logger.error(f"Error creating audio attachment: {e}")
            return None
    
    def _create_voice_attachment(self, voice: Voice) -> Optional[MediaAttachment]:
        """Create MediaAttachment from Voice."""
        try:
            return MediaAttachment(
                file_id=voice.file_id,
                file_unique_id=voice.file_unique_id,
                file_size=voice.file_size,
                mime_type=voice.mime_type,
                media_type=MediaType.AUDIO,
                duration=voice.duration
            )
        except Exception as e:
            logger.error(f"Error creating voice attachment: {e}")
            return None
    
    def _determine_media_type(self, file_name: Optional[str], mime_type: Optional[str]) -> MediaType:
        """Determine media type from file name and MIME type."""
        # Check MIME type first
        if mime_type:
            if mime_type.startswith('image/'):
                return MediaType.IMAGE
            elif mime_type.startswith('video/'):
                return MediaType.VIDEO
            elif mime_type.startswith('audio/'):
                return MediaType.AUDIO
        
        # Check file extension
        if file_name:
            ext = Path(file_name).suffix.lower()
            if ext in self.image_extensions:
                return MediaType.IMAGE
            elif ext in self.video_extensions:
                return MediaType.VIDEO
            elif ext in self.audio_extensions:
                return MediaType.AUDIO
        
        # Default to document
        return MediaType.DOCUMENT
    
    async def download_media(self, bot, attachment: MediaAttachment) -> bool:
        """
        Download media file from Telegram.
        
        Args:
            bot: Telegram bot instance
            attachment: MediaAttachment to download
            
        Returns:
            True if download successful
        """
        try:
            # Check file size limit
            if attachment.file_size and attachment.file_size > self.max_file_size:
                logger.warning(f"File too large: {attachment.file_size} bytes (max: {self.max_file_size})")
                return False
            
            # Get file from Telegram
            file = await bot.get_file(attachment.file_id)
            
            # Generate local file path
            file_extension = self._get_file_extension(attachment)
            local_filename = f"{attachment.file_unique_id}{file_extension}"
            local_path = self.temp_dir / local_filename
            
            # Download file
            await file.download_to_drive(local_path)
            
            # Update attachment with local path
            attachment.local_path = local_path
            
            logger.info(f"Downloaded media file: {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading media file {attachment.file_id}: {e}")
            return False
    
    def _get_file_extension(self, attachment: MediaAttachment) -> str:
        """Get appropriate file extension for attachment."""
        # Use original file name extension if available
        if attachment.file_name:
            ext = Path(attachment.file_name).suffix
            if ext:
                return ext
        
        # Use MIME type to determine extension
        if attachment.mime_type:
            mime_to_ext = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'video/mp4': '.mp4',
                'video/webm': '.webm',
                'audio/mpeg': '.mp3',
                'audio/ogg': '.ogg',
                'application/pdf': '.pdf',
                'text/plain': '.txt'
            }
            return mime_to_ext.get(attachment.mime_type, '.bin')
        
        # Default based on media type
        type_to_ext = {
            MediaType.IMAGE: '.jpg',
            MediaType.VIDEO: '.mp4',
            MediaType.AUDIO: '.mp3',
            MediaType.DOCUMENT: '.bin'
        }
        return type_to_ext.get(attachment.media_type, '.bin')
    
    def cleanup_temp_files(self, attachments: List[MediaAttachment]) -> None:
        """
        Clean up temporary files.
        
        Args:
            attachments: List of attachments to clean up
        """
        for attachment in attachments:
            if attachment.local_path and attachment.local_path.exists():
                try:
                    attachment.local_path.unlink()
                    logger.debug(f"Cleaned up temp file: {attachment.local_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {attachment.local_path}: {e}")
    
    def get_attachment_summary(self, attachments: List[MediaAttachment]) -> str:
        """
        Get a summary of attachments for display.
        
        Args:
            attachments: List of attachments
            
        Returns:
            Summary string
        """
        if not attachments:
            return "No attachments"
        
        summary_parts = []
        type_counts = {}
        
        for attachment in attachments:
            media_type = attachment.media_type
            type_counts[media_type] = type_counts.get(media_type, 0) + 1
        
        for media_type, count in type_counts.items():
            emoji = {
                MediaType.IMAGE: "🖼️",
                MediaType.VIDEO: "🎥",
                MediaType.AUDIO: "🎵",
                MediaType.DOCUMENT: "📄"
            }.get(media_type, "📎")
            
            if count == 1:
                summary_parts.append(f"{emoji} 1 {media_type}")
            else:
                summary_parts.append(f"{emoji} {count} {media_type}s")
        
        return ", ".join(summary_parts)