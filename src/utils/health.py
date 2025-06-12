"""Health check utilities for monitoring application status."""

import asyncio
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HealthChecker:
    """Health checker for monitoring external dependencies."""
    
    def __init__(self):
        self.last_checks = {}
        self.check_interval = timedelta(minutes=5)
    
    async def check_telegram_api(self, bot_token: str) -> Dict[str, Any]:
        """Check Telegram Bot API connectivity."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{bot_token}/getMe"
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        return {
                            "status": "healthy",
                            "response_time_ms": response.elapsed.total_seconds() * 1000,
                            "bot_info": data.get("result", {})
                        }
                
                return {
                    "status": "unhealthy",
                    "error": f"API returned status {response.status_code}",
                    "response": response.text[:200]
                }
        except Exception as e:
            logger.error(f"Telegram API health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_openrouter_api(self, api_key: str, base_url: str) -> Dict[str, Any]:
        """Check OpenRouter API connectivity."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                # Use a simple models endpoint to check connectivity
                response = await client.get(
                    f"{base_url}/models",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                
                return {
                    "status": "unhealthy",
                    "error": f"API returned status {response.status_code}",
                    "response": response.text[:200]
                }
        except Exception as e:
            logger.error(f"OpenRouter API health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_jira_api(self, jira_url: str, access_token: Optional[str] = None) -> Dict[str, Any]:
        """Check Jira API connectivity."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {}
                if access_token:
                    headers["Authorization"] = f"Bearer {access_token}"
                
                # Check basic connectivity to Jira instance
                response = await client.get(
                    f"{jira_url}/rest/api/3/serverInfo",
                    headers=headers
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
                
                return {
                    "status": "unhealthy",
                    "error": f"API returned status {response.status_code}",
                    "response": response.text[:200]
                }
        except Exception as e:
            logger.error(f"Jira API health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def comprehensive_health_check(
        self,
        telegram_token: str,
        openrouter_key: str,
        openrouter_url: str,
        jira_url: str,
        jira_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform comprehensive health check of all dependencies."""
        start_time = datetime.utcnow()
        
        # Run all checks concurrently
        telegram_check, openrouter_check, jira_check = await asyncio.gather(
            self.check_telegram_api(telegram_token),
            self.check_openrouter_api(openrouter_key, openrouter_url),
            self.check_jira_api(jira_url, jira_token),
            return_exceptions=True
        )
        
        # Handle any exceptions from the checks
        if isinstance(telegram_check, Exception):
            telegram_check = {"status": "unhealthy", "error": str(telegram_check)}
        if isinstance(openrouter_check, Exception):
            openrouter_check = {"status": "unhealthy", "error": str(openrouter_check)}
        if isinstance(jira_check, Exception):
            jira_check = {"status": "unhealthy", "error": str(jira_check)}
        
        # Determine overall health
        all_healthy = all(
            check.get("status") in ["healthy", "authentication_required"]
            for check in [telegram_check, openrouter_check, jira_check]
        )
        
        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds() * 1000
        
        result = {
            "overall_status": "healthy" if all_healthy else "unhealthy",
            "timestamp": start_time.isoformat(),
            "total_check_time_ms": total_time,
            "services": {
                "telegram": telegram_check,
                "openrouter": openrouter_check,
                "jira": jira_check
            }
        }
        
        # Cache the result
        self.last_checks["comprehensive"] = {
            "result": result,
            "timestamp": start_time
        }
        
        return result
    
    def get_cached_health(self, check_type: str = "comprehensive") -> Optional[Dict[str, Any]]:
        """Get cached health check result if recent enough."""
        cached = self.last_checks.get(check_type)
        if cached:
            age = datetime.utcnow() - cached["timestamp"]
            if age < self.check_interval:
                return cached["result"]
        return None
    
    async def basic_health_check(self) -> Dict[str, Any]:
        """Basic health check for application readiness."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": "running",
            "version": "1.0.0"
        }


# Global health checker instance
health_checker = HealthChecker()