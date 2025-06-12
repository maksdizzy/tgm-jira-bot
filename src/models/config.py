"""Configuration models for the TG-Jira bot."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: str = Field(..., env="TELEGRAM_WEBHOOK_URL")
    
    # OpenRouter Configuration
    openrouter_api_key: str = Field(..., env="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="openai/gpt-4-turbo", env="OPENROUTER_MODEL")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", env="OPENROUTER_BASE_URL")
    
    # Jira OAuth 2.0 Configuration
    jira_cloud_url: str = Field(..., env="JIRA_CLOUD_URL")
    jira_client_id: str = Field(..., env="JIRA_CLIENT_ID")
    jira_client_secret: str = Field(..., env="JIRA_CLIENT_SECRET")
    jira_project_key: str = Field(..., env="JIRA_PROJECT_KEY")
    jira_redirect_uri: str = Field(default="http://localhost:8000/auth/callback", env="JIRA_REDIRECT_URI")
    
    # Application Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    environment: str = Field(default="development", env="ENVIRONMENT")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    
    # Optional OAuth tokens (will be set after authentication)
    jira_access_token: Optional[str] = Field(default=None, env="JIRA_ACCESS_TOKEN")
    jira_refresh_token: Optional[str] = Field(default=None, env="JIRA_REFRESH_TOKEN")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def jira_auth_url(self) -> str:
        """Generate Jira OAuth authorization URL."""
        return f"{self.jira_cloud_url}/plugins/servlet/oauth/authorize"
    
    @property
    def jira_token_url(self) -> str:
        """Generate Jira OAuth token URL."""
        return f"{self.jira_cloud_url}/plugins/servlet/oauth/access-token"
    
    @property
    def is_jira_data_center(self) -> bool:
        """Check if this is a Jira Data Center instance (not Cloud)."""
        # Cloud instances have .atlassian.net domain, Data Center instances don't
        return not self.jira_cloud_url.endswith('.atlassian.net')
    
    @property
    def jira_api_version(self) -> str:
        """Get the appropriate Jira API version."""
        return "2" if self.is_jira_data_center else "3"