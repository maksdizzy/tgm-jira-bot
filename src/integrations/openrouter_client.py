"""OpenRouter LLM client for processing ticket content."""

import json
import httpx
from typing import Optional, Dict, Any
from src.models.ticket import TicketData, LLMProcessingRequest, LLMProcessingResponse, Priority, IssueType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenRouterClient:
    """Client for OpenRouter LLM API integration."""
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1", model: str = "google/gemini-2.5-flash-preview-05-20"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _create_ticket_extraction_prompt(self, message_content: str, user_context: Optional[str] = None) -> str:
        """Create a prompt for extracting ticket information from message content."""
        
        prompt = f"""You are an expert at analyzing messages and extracting structured ticket information for Jira.

Analyze the following message and extract ticket information in JSON format.

Message: "{message_content}"

{f"User Context: {user_context}" if user_context else ""}

Extract the following information and respond with ONLY a valid JSON object:

{{
    "title": "A concise, descriptive title (max 100 characters)",
    "description": "A detailed description expanding on the message content",
    "priority": "One of: Highest, High, Medium, Low, Lowest",
    "issue_type": "One of: Bug, Task, Story, Epic, Improvement, New Feature",
    "labels": ["relevant", "labels", "as", "array"],
    "components": ["affected", "components", "as", "array"]
}}

Guidelines:
- Title should be clear and actionable
- Description should provide context and details
- Priority should be based on urgency indicators in the message
- Issue type should be inferred from the content:
  * Bug: Error reports, things not working
  * Task: General work items, requests
  * Story: User-focused features
  * Improvement: Enhancements to existing features
  * New Feature: Completely new functionality
- Labels should be relevant keywords (max 5)
- Components should be system/module names if identifiable

Respond with ONLY the JSON object, no additional text."""

        return prompt
    
    async def process_message(self, request: LLMProcessingRequest) -> LLMProcessingResponse:
        """
        Process message content using LLM to extract ticket information.
        
        Args:
            request: LLM processing request with message content
            
        Returns:
            LLM processing response with extracted ticket data
        """
        try:
            logger.info(f"Processing message with OpenRouter: {request.message_content[:100]}...")
            
            prompt = self._create_ticket_extraction_prompt(
                request.message_content,
                request.user_context
            )
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000,
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/tgm-jira-bot",
                "X-Title": "TG-Jira Bot"
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code != 200:
                error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return LLMProcessingResponse(
                    success=False,
                    error_message=error_msg
                )
            
            response_data = response.json()
            
            if "choices" not in response_data or not response_data["choices"]:
                error_msg = "No choices in OpenRouter response"
                logger.error(error_msg)
                return LLMProcessingResponse(
                    success=False,
                    error_message=error_msg
                )
            
            content = response_data["choices"][0]["message"]["content"].strip()
            logger.debug(f"OpenRouter response content: {content}")
            
            # Parse JSON response
            try:
                ticket_json = json.loads(content)
                
                # Validate and create TicketData
                ticket_data = TicketData(
                    title=ticket_json.get("title", "Untitled Ticket"),
                    description=ticket_json.get("description", request.message_content),
                    priority=Priority(ticket_json.get("priority", "Medium")),
                    issue_type=IssueType(ticket_json.get("issue_type", "Task")),
                    labels=ticket_json.get("labels", []),
                    components=ticket_json.get("components", [])
                )
                
                logger.info(f"Successfully processed message into ticket: {ticket_data.title}")
                
                return LLMProcessingResponse(
                    success=True,
                    ticket_data=ticket_data,
                    confidence_score=0.9  # Could be enhanced with actual confidence scoring
                )
                
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON from OpenRouter response: {e}"
                logger.error(f"{error_msg}. Content: {content}")
                
                # Fallback: create basic ticket from original message
                fallback_ticket = TicketData(
                    title=request.message_content[:100] + "..." if len(request.message_content) > 100 else request.message_content,
                    description=request.message_content,
                    priority=Priority.MEDIUM,
                    issue_type=IssueType.TASK
                )
                
                return LLMProcessingResponse(
                    success=True,
                    ticket_data=fallback_ticket,
                    confidence_score=0.3,
                    error_message=f"Used fallback processing due to JSON parse error: {e}"
                )
                
            except ValueError as e:
                error_msg = f"Invalid enum value in OpenRouter response: {e}"
                logger.error(error_msg)
                
                # Fallback with corrected values
                fallback_ticket = TicketData(
                    title=ticket_json.get("title", request.message_content[:100]),
                    description=ticket_json.get("description", request.message_content),
                    priority=Priority.MEDIUM,
                    issue_type=IssueType.TASK,
                    labels=ticket_json.get("labels", []),
                    components=ticket_json.get("components", [])
                )
                
                return LLMProcessingResponse(
                    success=True,
                    ticket_data=fallback_ticket,
                    confidence_score=0.5,
                    error_message=f"Used fallback values due to enum error: {e}"
                )
        
        except Exception as e:
            error_msg = f"Unexpected error in OpenRouter processing: {e}"
            logger.error(error_msg, exc_info=True)
            return LLMProcessingResponse(
                success=False,
                error_message=error_msg
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on OpenRouter API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.get(
                f"{self.base_url}/models",
                headers=headers
            )
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
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