"""Jira OAuth 2.0 client for ticket creation and management."""

import httpx
import json
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode
from requests_oauthlib import OAuth2Session
from src.models.ticket import TicketData, TicketResponse, JiraTicketPayload
from src.utils.logger import get_logger
from src.utils.token_storage import TokenStorage

logger = get_logger(__name__)


class JiraClient:
    """Client for Jira Cloud API with OAuth 2.0 authentication."""
    
    def __init__(
        self,
        cloud_url: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        project_key: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None
    ):
        self.cloud_url = cloud_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.project_key = project_key
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Token storage for persistence
        self.token_storage = TokenStorage()
        
        # Detect if this is Jira Cloud or Data Center
        self.is_cloud = self.cloud_url.endswith('.atlassian.net')
        
        # Load saved tokens if not provided
        if not self.access_token:
            self._load_saved_tokens()
        
        # OAuth 2.0 endpoints
        if self.is_cloud:
            # Jira Cloud OAuth 2.0 (3LO) endpoints
            self.auth_url = "https://auth.atlassian.com/authorize"
            self.token_url = "https://auth.atlassian.com/oauth/token"
        else:
            # Jira Data Center OAuth endpoints
            self.auth_url = f"{self.cloud_url}/plugins/servlet/oauth/authorize"
            self.token_url = f"{self.cloud_url}/plugins/servlet/oauth/access-token"
        
        # Use appropriate API version: v3 for Cloud, v2 for Data Center
        api_version = "3" if self.is_cloud else "2"
        self.api_base = f"{self.cloud_url}/rest/api/{api_version}"
        
        # For Jira Cloud, we need to get the site ID from accessible resources
        self.site_id = None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth 2.0 authorization URL for Jira Cloud or Data Center.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL for user to visit
        """
        # OAuth 2.0 scopes based on Jira type
        if self.is_cloud:
            # Jira Cloud OAuth 2.0 (3LO) scopes
            scopes = [
                'read:jira-user',
                'read:jira-work',
                'write:jira-work',
                'offline_access'  # Required for refresh tokens
            ]
        else:
            # Jira Data Center scopes
            scopes = [
                'read:jira-user',
                'read:jira-work',
                'write:jira-work',
                'manage:jira-project',
                'manage:jira-configuration'
            ]
        
        if self.is_cloud:
            # For Jira Cloud, we need to add audience parameter
            oauth = OAuth2Session(
                client_id=self.client_id,
                redirect_uri=self.redirect_uri,
                scope=scopes
            )
            
            authorization_url, state = oauth.authorization_url(
                self.auth_url,
                state=state,
                audience="api.atlassian.com",
                prompt="consent"
            )
        else:
            # For Data Center, use standard OAuth2
            oauth = OAuth2Session(
                client_id=self.client_id,
                redirect_uri=self.redirect_uri,
                scope=scopes
            )
            
            authorization_url, state = oauth.authorization_url(
                self.auth_url,
                state=state
            )
        
        jira_type = "Cloud" if self.is_cloud else "Data Center"
        logger.info(f"Generated authorization URL for Jira {jira_type} OAuth")
        return authorization_url
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> Tuple[str, str]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Code received from OAuth callback
            
        Returns:
            Tuple of (access_token, refresh_token)
            
        Raises:
            Exception: If token exchange fails
        """
        try:
            if self.is_cloud:
                # For Jira Cloud, make direct HTTP request to token endpoint
                token_data = {
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": authorization_code,
                    "redirect_uri": self.redirect_uri
                }
                
                response = await self.client.post(
                    self.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")
                
                token = response.json()
            else:
                # For Data Center, use OAuth2Session
                oauth = OAuth2Session(
                    client_id=self.client_id,
                    redirect_uri=self.redirect_uri
                )
                
                token = oauth.fetch_token(
                    self.token_url,
                    code=authorization_code,
                    client_secret=self.client_secret
                )
            
            self.access_token = token['access_token']
            self.refresh_token = token.get('refresh_token')
            
            # For Jira Cloud, get accessible resources to find the correct site
            if self.is_cloud:
                await self._get_accessible_resources()
            
            # Save tokens for persistence
            self._save_tokens()
            
            logger.info("Successfully exchanged authorization code for tokens")
            return self.access_token, self.refresh_token
            
        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            raise
    
    async def refresh_access_token(self) -> str:
        """
        Refresh the access token using refresh token.
        
        Returns:
            New access token
            
        Raises:
            Exception: If token refresh fails
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")
        
        try:
            if self.is_cloud:
                # For Jira Cloud, make direct HTTP request to refresh token
                token_data = {
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token
                }
                
                response = await self.client.post(
                    self.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")
                
                token = response.json()
            else:
                # For Data Center, use OAuth2Session
                oauth = OAuth2Session(client_id=self.client_id)
                
                token = oauth.refresh_token(
                    self.token_url,
                    refresh_token=self.refresh_token,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            
            self.access_token = token['access_token']
            if 'refresh_token' in token:
                self.refresh_token = token['refresh_token']
            
            # For Jira Cloud, update accessible resources to ensure correct API base
            if self.is_cloud:
                await self._get_accessible_resources()
            
            # Save tokens for persistence
            self._save_tokens()
            
            logger.info("Successfully refreshed access token")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise
    
    async def _get_accessible_resources(self) -> None:
        """Get accessible resources for Jira Cloud to find the correct site ID."""
        try:
            if not self.access_token:
                return
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            
            response = await self.client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers=headers
            )
            
            if response.status_code == 200:
                resources = response.json()
                
                # Find the resource that matches our cloud URL
                for resource in resources:
                    if resource.get('url') == self.cloud_url:
                        self.site_id = resource.get('id')
                        # Update API base with the correct site ID
                        self.api_base = f"https://api.atlassian.com/ex/jira/{self.site_id}/rest/api/3"
                        logger.info(f"Found site ID: {self.site_id}")
                        return
                
                # If no exact match, use the first available resource
                if resources:
                    self.site_id = resources[0].get('id')
                    self.api_base = f"https://api.atlassian.com/ex/jira/{self.site_id}/rest/api/3"
                    logger.info(f"Using first available site ID: {self.site_id}")
            else:
                logger.warning(f"Failed to get accessible resources: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting accessible resources: {e}")
    
    def _load_saved_tokens(self) -> None:
        """Load saved tokens from storage."""
        try:
            tokens = self.token_storage.load_tokens('jira')
            if tokens:
                self.access_token = tokens.get('access_token')
                self.refresh_token = tokens.get('refresh_token')
                self.site_id = tokens.get('site_id')
                
                # Update API base if we have site_id for Cloud
                if self.is_cloud and self.site_id:
                    self.api_base = f"https://api.atlassian.com/ex/jira/{self.site_id}/rest/api/3"
                
                logger.info("Loaded saved Jira tokens")
        except Exception as e:
            logger.error(f"Failed to load saved tokens: {e}")
    
    def _save_tokens(self) -> None:
        """Save current tokens to storage."""
        try:
            tokens = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'site_id': self.site_id,
                'cloud_url': self.cloud_url,
                'api_base': self.api_base
            }
            self.token_storage.save_tokens('jira', tokens)
            logger.info("Saved Jira tokens")
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
    
    async def _make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_on_auth_error: bool = True
    ) -> httpx.Response:
        """
        Make authenticated request to Jira API with automatic token refresh.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to api_base)
            data: Request data
            params: Query parameters
            retry_on_auth_error: Whether to retry on authentication errors
            
        Returns:
            HTTP response
        """
        if not self.access_token:
            raise ValueError("No access token available. Please authenticate first.")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )
            
            # If unauthorized and we have a refresh token, try to refresh
            if response.status_code == 401 and retry_on_auth_error and self.refresh_token:
                logger.info("Access token expired, attempting to refresh")
                await self.refresh_access_token()
                
                # Update headers with new token
                headers["Authorization"] = f"Bearer {self.access_token}"
                
                # Retry the request
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Request to {url} failed: {e}")
            raise
    
    async def create_ticket(self, ticket_data: TicketData, reporter_account_id: Optional[str] = None) -> TicketResponse:
        """
        Create a Jira ticket from ticket data.
        
        Args:
            ticket_data: Structured ticket information
            reporter_account_id: Optional Jira account ID for reporter
            
        Returns:
            Ticket creation response
        """
        try:
            logger.info(f"Creating Jira ticket: {ticket_data.title}")
            
            # Create Jira payload with correct format for Cloud/Data Center
            payload = JiraTicketPayload.from_ticket_data(
                ticket_data=ticket_data,
                project_key=self.project_key,
                reporter_account_id=reporter_account_id,
                is_cloud=self.is_cloud
            )
            
            # Make API request
            response = await self._make_authenticated_request(
                method="POST",
                endpoint="/issue",
                data=payload.dict()
            )
            
            if response.status_code == 201:
                response_data = response.json()
                ticket_key = response_data.get("key")
                ticket_url = f"{self.cloud_url}/browse/{ticket_key}"
                
                logger.info(f"Successfully created ticket {ticket_key}")
                
                return TicketResponse(
                    success=True,
                    ticket_key=ticket_key,
                    ticket_url=ticket_url,
                    ticket_title=ticket_data.title
                )
            else:
                error_msg = f"Failed to create ticket: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return TicketResponse(
                    success=False,
                    error_message=error_msg
                )
        
        except Exception as e:
            error_msg = f"Unexpected error creating ticket: {e}"
            logger.error(error_msg, exc_info=True)
            
            return TicketResponse(
                success=False,
                error_message=error_msg
            )
    
    async def upload_attachment(self, ticket_key: str, file_path: str, filename: str) -> bool:
        """
        Upload an attachment to a Jira ticket.
        
        Args:
            ticket_key: Jira ticket key (e.g., PROJ-123)
            file_path: Local path to the file
            filename: Name for the attachment
            
        Returns:
            True if upload successful
        """
        try:
            logger.info(f"Uploading attachment {filename} to ticket {ticket_key}")
            
            # Prepare multipart form data
            with open(file_path, 'rb') as file:
                files = {
                    'file': (filename, file, 'application/octet-stream')
                }
                
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Atlassian-Token": "no-check"  # Required for file uploads
                }
                
                # Make upload request
                response = await self.client.post(
                    f"{self.api_base}/issue/{ticket_key}/attachments",
                    files=files,
                    headers=headers
                )
            
            if response.status_code == 200:
                logger.info(f"Successfully uploaded attachment {filename} to {ticket_key}")
                return True
            else:
                logger.error(f"Failed to upload attachment: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading attachment {filename}: {e}")
            return False
    
    async def upload_attachments(self, ticket_key: str, attachments: list) -> int:
        """
        Upload multiple attachments to a Jira ticket.
        
        Args:
            ticket_key: Jira ticket key
            attachments: List of MediaAttachment objects with local_path set
            
        Returns:
            Number of successfully uploaded attachments
        """
        if not attachments:
            return 0
        
        successful_uploads = 0
        
        for attachment in attachments:
            if not attachment.local_path or not attachment.local_path.exists():
                logger.warning(f"Skipping attachment {attachment.file_id}: no local file")
                continue
            
            # Use original filename or generate one
            filename = attachment.file_name or f"{attachment.file_unique_id}{self._get_attachment_extension(attachment)}"
            
            if await self.upload_attachment(ticket_key, str(attachment.local_path), filename):
                attachment.jira_attachment_id = ticket_key  # Store reference
                successful_uploads += 1
        
        logger.info(f"Uploaded {successful_uploads}/{len(attachments)} attachments to {ticket_key}")
        return successful_uploads
    
    def _get_attachment_extension(self, attachment) -> str:
        """Get appropriate file extension for attachment."""
        # Use original file name extension if available
        if attachment.file_name:
            from pathlib import Path
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
        from src.models.ticket import MediaType
        type_to_ext = {
            MediaType.IMAGE: '.jpg',
            MediaType.VIDEO: '.mp4',
            MediaType.AUDIO: '.mp3',
            MediaType.DOCUMENT: '.bin'
        }
        return type_to_ext.get(attachment.media_type, '.bin')
    
    async def get_project_info(self) -> Dict[str, Any]:
        """
        Get information about the configured project.
        
        Returns:
            Project information
        """
        try:
            response = await self._make_authenticated_request(
                method="GET",
                endpoint=f"/project/{self.project_key}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get project info: {response.status_code} - {response.text}")
                return {}
        
        except Exception as e:
            logger.error(f"Error getting project info: {e}")
            return {}
    
    async def get_issue_types(self) -> Dict[str, Any]:
        """
        Get available issue types for the project.
        
        Returns:
            Issue types information
        """
        try:
            response = await self._make_authenticated_request(
                method="GET",
                endpoint=f"/project/{self.project_key}/statuses"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get issue types: {response.status_code} - {response.text}")
                return {}
        
        except Exception as e:
            logger.error(f"Error getting issue types: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Jira API.
        
        Returns:
            Health check result
        """
        try:
            if not self.access_token:
                return {
                    "status": "authentication_required",
                    "error": "No access token available"
                }
            
            response = await self._make_authenticated_request(
                method="GET",
                endpoint="/serverInfo",
                retry_on_auth_error=False
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "healthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "server_info": {
                        "version": data.get("version"),
                        "deployment_type": data.get("deploymentType")
                    }
                }
            elif response.status_code == 401:
                return {
                    "status": "authentication_required",
                    "error": "Authentication required or token expired"
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"API returned status {response.status_code}"
                }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def is_authenticated(self) -> bool:
        """Check if client has valid authentication."""
        return self.access_token is not None