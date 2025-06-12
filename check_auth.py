#!/usr/bin/env python3
"""Check Jira authentication status."""

import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def check_auth_status():
    """Check if Jira is authenticated."""
    try:
        from src.models.config import Settings
        from src.integrations.jira_client import JiraClient
        
        # Load settings
        settings = Settings()
        
        # Create Jira client
        jira_client = JiraClient(
            cloud_url=settings.jira_cloud_url,
            client_id=settings.jira_client_id,
            client_secret=settings.jira_client_secret,
            redirect_uri=settings.jira_redirect_uri,
            project_key=settings.jira_project_key,
            access_token=settings.jira_access_token,
            refresh_token=settings.jira_refresh_token
        )
        
        print("Checking Jira authentication status...")
        print(f"Jira URL: {settings.jira_cloud_url}")
        print(f"Project: {settings.jira_project_key}")
        print(f"Has Access Token: {bool(settings.jira_access_token)}")
        print(f"Has Refresh Token: {bool(settings.jira_refresh_token)}")
        
        # Check health
        health = await jira_client.health_check()
        print(f"Health Status: {health.get('status', 'unknown')}")
        
        if health.get('status') == 'authentication_required':
            auth_url = jira_client.get_authorization_url()
            print(f"\nAuthentication Required!")
            print(f"Visit this URL to authorize:")
            print(f"{auth_url}")
            print(f"\nOr visit your bot at: http://{settings.host}:{settings.port}/auth/jira")
        elif health.get('status') == 'healthy':
            print("\nAuthentication successful! Bot is ready to create tickets.")
        else:
            print(f"\nUnexpected status: {health}")
        
        await jira_client.close()
        return health.get('status') == 'healthy'
        
    except Exception as e:
        print(f"Error checking authentication: {e}")
        return False

async def main():
    """Main function."""
    print("Jira Authentication Status Checker\n")
    
    is_authenticated = await check_auth_status()
    
    if is_authenticated:
        print("\n✅ Ready to create Jira tickets!")
        return True
    else:
        print("\n❌ Authentication required before creating tickets.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)