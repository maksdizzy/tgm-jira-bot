"""Ticket data models for Jira integration."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class Priority(str, Enum):
    """Ticket priority levels."""
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


class IssueType(str, Enum):
    """Jira issue types."""
    BUG = "Bug"
    TASK = "Task"
    STORY = "Story"
    EPIC = "Epic"
    IMPROVEMENT = "Improvement"
    NEW_FEATURE = "New Feature"


class TicketData(BaseModel):
    """Structured ticket data extracted from message content."""
    
    title: str = Field(..., description="Concise ticket title")
    description: str = Field(..., description="Detailed ticket description")
    priority: Priority = Field(default=Priority.MEDIUM, description="Ticket priority")
    issue_type: IssueType = Field(default=IssueType.TASK, description="Type of issue")
    labels: List[str] = Field(default_factory=list, description="Relevant labels")
    components: List[str] = Field(default_factory=list, description="Affected components")
    
    class Config:
        use_enum_values = True
        
    def __init__(self, **data):
        # Convert string values to enums if needed
        if 'priority' in data and isinstance(data['priority'], str):
            try:
                data['priority'] = Priority(data['priority'])
            except ValueError:
                # If the string doesn't match exactly, try to find a close match
                priority_map = {
                    'highest': Priority.HIGHEST,
                    'high': Priority.HIGH,
                    'medium': Priority.MEDIUM,
                    'low': Priority.LOW,
                    'lowest': Priority.LOWEST
                }
                data['priority'] = priority_map.get(data['priority'].lower(), Priority.MEDIUM)
        
        if 'issue_type' in data and isinstance(data['issue_type'], str):
            try:
                data['issue_type'] = IssueType(data['issue_type'])
            except ValueError:
                # If the string doesn't match exactly, try to find a close match
                issue_type_map = {
                    'bug': IssueType.BUG,
                    'task': IssueType.TASK,
                    'story': IssueType.STORY,
                    'epic': IssueType.EPIC,
                    'improvement': IssueType.IMPROVEMENT,
                    'new feature': IssueType.NEW_FEATURE,
                    'feature': IssueType.NEW_FEATURE
                }
                data['issue_type'] = issue_type_map.get(data['issue_type'].lower(), IssueType.TASK)
        
        super().__init__(**data)


class TicketRequest(BaseModel):
    """Request data for creating a Jira ticket."""
    
    ticket_data: TicketData
    telegram_user_id: int = Field(..., description="Telegram user ID")
    telegram_username: Optional[str] = Field(None, description="Telegram username")
    telegram_chat_id: int = Field(..., description="Telegram chat ID")
    original_message: str = Field(..., description="Original message content")
    message_id: int = Field(..., description="Telegram message ID")


class TicketResponse(BaseModel):
    """Response data after creating a Jira ticket."""
    
    success: bool = Field(..., description="Whether ticket creation was successful")
    ticket_key: Optional[str] = Field(None, description="Jira ticket key (e.g., PROJ-123)")
    ticket_url: Optional[str] = Field(None, description="Direct URL to the ticket")
    error_message: Optional[str] = Field(None, description="Error message if creation failed")
    
    @property
    def formatted_response(self) -> str:
        """Generate a formatted response message for Telegram."""
        if self.success and self.ticket_key and self.ticket_url:
            return f"✅ Ticket created successfully!\n\n🎫 **{self.ticket_key}**\n🔗 [View Ticket]({self.ticket_url})"
        elif self.error_message:
            return f"❌ Failed to create ticket: {self.error_message}"
        else:
            return "❌ Failed to create ticket: Unknown error occurred"


class JiraTicketPayload(BaseModel):
    """Jira API payload for ticket creation."""
    
    fields: Dict[str, Any] = Field(..., description="Jira ticket fields")
    
    @classmethod
    def from_ticket_data(
        cls,
        ticket_data: TicketData,
        project_key: str,
        reporter_account_id: Optional[str] = None,
        is_cloud: bool = True
    ) -> "JiraTicketPayload":
        """Create Jira payload from ticket data for Cloud or Data Center."""
        fields = {
            "project": {"key": project_key},
            "summary": ticket_data.title,
            "issuetype": {"name": ticket_data.issue_type if isinstance(ticket_data.issue_type, str) else ticket_data.issue_type.value}
        }
        
        # Handle description format based on Jira type
        if is_cloud:
            # Jira Cloud uses Atlassian Document Format (ADF)
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": ticket_data.description
                            }
                        ]
                    }
                ]
            }
        else:
            # Jira Data Center uses plain text
            fields["description"] = ticket_data.description
        
        # Add reporter if provided
        if reporter_account_id:
            if is_cloud:
                fields["reporter"] = {"accountId": reporter_account_id}
            else:
                fields["reporter"] = {"name": reporter_account_id}
        
        # Add labels if any
        if ticket_data.labels:
            fields["labels"] = ticket_data.labels
        
        # Note: Components and priority fields removed as they may not be available on all Jira screens
        
        return cls(fields=fields)


class LLMProcessingRequest(BaseModel):
    """Request for LLM processing of message content."""
    
    message_content: str = Field(..., description="Original message content")
    user_context: Optional[str] = Field(None, description="Additional user context")
    chat_context: Optional[str] = Field(None, description="Chat context information")


class LLMProcessingResponse(BaseModel):
    """Response from LLM processing."""
    
    success: bool = Field(..., description="Whether processing was successful")
    ticket_data: Optional[TicketData] = Field(None, description="Extracted ticket data")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    confidence_score: Optional[float] = Field(None, description="Confidence in extraction (0-1)")