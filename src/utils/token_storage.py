"""Token storage utilities for persisting OAuth tokens."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TokenStorage:
    """Simple file-based token storage for OAuth tokens."""
    
    def __init__(self, storage_path: str = "tokens.json"):
        """
        Initialize token storage.
        
        Args:
            storage_path: Path to the token storage file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(exist_ok=True)
    
    def save_tokens(self, service: str, tokens: Dict[str, Any]) -> bool:
        """
        Save tokens for a service.
        
        Args:
            service: Service name (e.g., 'jira')
            tokens: Token data to save
            
        Returns:
            True if saved successfully
        """
        try:
            # Load existing tokens
            all_tokens = self._load_all_tokens()
            
            # Update tokens for the service
            all_tokens[service] = tokens
            
            # Save back to file
            with open(self.storage_path, 'w') as f:
                json.dump(all_tokens, f, indent=2)
            
            logger.info(f"Saved tokens for service: {service}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save tokens for {service}: {e}")
            return False
    
    def load_tokens(self, service: str) -> Optional[Dict[str, Any]]:
        """
        Load tokens for a service.
        
        Args:
            service: Service name (e.g., 'jira')
            
        Returns:
            Token data or None if not found
        """
        try:
            all_tokens = self._load_all_tokens()
            tokens = all_tokens.get(service)
            
            if tokens:
                logger.info(f"Loaded tokens for service: {service}")
                return tokens
            else:
                logger.debug(f"No tokens found for service: {service}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load tokens for {service}: {e}")
            return None
    
    def delete_tokens(self, service: str) -> bool:
        """
        Delete tokens for a service.
        
        Args:
            service: Service name (e.g., 'jira')
            
        Returns:
            True if deleted successfully
        """
        try:
            all_tokens = self._load_all_tokens()
            
            if service in all_tokens:
                del all_tokens[service]
                
                # Save back to file
                with open(self.storage_path, 'w') as f:
                    json.dump(all_tokens, f, indent=2)
                
                logger.info(f"Deleted tokens for service: {service}")
                return True
            else:
                logger.debug(f"No tokens to delete for service: {service}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete tokens for {service}: {e}")
            return False
    
    def _load_all_tokens(self) -> Dict[str, Any]:
        """Load all tokens from storage file."""
        if not self.storage_path.exists():
            return {}
        
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Could not load tokens from {self.storage_path}, starting fresh")
            return {}
    
    def has_tokens(self, service: str) -> bool:
        """
        Check if tokens exist for a service.
        
        Args:
            service: Service name (e.g., 'jira')
            
        Returns:
            True if tokens exist
        """
        tokens = self.load_tokens(service)
        return tokens is not None and bool(tokens.get('access_token'))