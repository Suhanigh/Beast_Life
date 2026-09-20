"""LLM client interface with tool calling support."""
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel


class ToolCall(BaseModel):
    """Represents a tool call request from the LLM."""
    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""
    tool_call_id: str
    result: Any


class LLMMessage(BaseModel):
    """Message in the conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None


class LLMResponse(BaseModel):
    """Response from the LLM."""
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None  # tokens, cost estimate


class LLMClient(ABC):
    """Abstract LLM client interface."""
    
    @abstractmethod
    def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Send chat completion request with optional tool calling."""
        pass
    
    @abstractmethod
    def estimate_cost(self, usage: Dict[str, int]) -> float:
        """Estimate cost based on token usage."""
        pass


class MockLLMClient(LLMClient):
    """Mock LLM client for testing and mock mode."""
    
    def __init__(self, scripted_responses: Optional[List[Dict[str, Any]]] = None):
        """Initialize with optional scripted responses."""
        self.scripted_responses = scripted_responses or self._get_default_scripted_responses()
        self.call_count = 0
        self.current_script_index = 0
    
    def _get_default_scripted_responses(self) -> List[Dict[str, Any]]:
        """Get default scripted responses for research workflow."""
        return [
            # First call: respond with web_search tool call
            {
                "tool_calls": [
                    {
                        "name": "web_search",
                        "arguments": {"query": "protein powder benefits gym-goers"}
                    }
                ]
            },
            # Second call: respond with read_page tool calls for search results
            {
                "tool_calls": [
                    {
                        "name": "read_page",
                        "arguments": {"url": "https://example.com/protein-benefits"}
                    },
                    {
                        "name": "read_page",
                        "arguments": {"url": "https://example.com/protein-timing"}
                    },
                    {
                        "name": "read_page",
                        "arguments": {"url": "https://example.com/clean-protein"}
                    }
                ]
            },
            # Third call: respond with final content (not tool call) with angles
            {
                "content": json.dumps({
                    "angles": [
                        {
                            "audience_insight": "Busy gym-goers prioritize convenience without sacrificing nutrition quality",
                            "hook": "Fuel Your Ambition, Not Your Schedule",
                            "visual_direction": "Dynamic split-screen showing professional athlete in office transitioning to gym setting",
                            "rationale": "Research shows busy professionals seek convenient nutrition solutions that align with their fitness goals",
                            "source_ids": [1, 2],
                            "statements": [
                                {
                                    "text": "Busy gym-goers need convenient nutrition options",
                                    "label": "sourced_observation"
                                },
                                {
                                    "text": "Split-screen visual represents work-life balance",
                                    "label": "creative_interpretation"
                                }
                            ]
                        },
                        {
                            "audience_insight": "Gym enthusiasts are increasingly educated about protein timing and quality",
                            "hook": "The 30-Minute Window: Don't Miss Your Moment",
                            "visual_direction": "Clock visualization with protein shake at 30-minute mark post-workout",
                            "rationale": "Research indicates consuming protein within 30 minutes after workout maximizes muscle protein synthesis",
                            "source_ids": [2],
                            "statements": [
                                {
                                    "text": "Protein timing within 30 minutes post-workout maximizes muscle protein synthesis",
                                    "label": "sourced_observation"
                                },
                                {
                                    "text": "Clock visualization creates urgency and relevance",
                                    "label": "creative_interpretation"
                                }
                            ]
                        },
                        {
                            "audience_insight": "Health-conscious consumers prefer clean label products without artificial ingredients",
                            "hook": "Clean Fuel, Clean Gains",
                            "visual_direction": "Minimalist product shot with natural ingredient callouts",
                            "rationale": "Market research shows strong demand for protein powders without artificial sweeteners or preservatives",
                            "source_ids": [3],
                            "statements": [
                                {
                                    "text": "Consumers seek protein powders without artificial sweeteners",
                                    "label": "sourced_observation"
                                },
                                {
                                    "text": "Minimalist aesthetic communicates purity",
                                    "label": "creative_interpretation"
                                }
                            ]
                        }
                    ]
                }),
                "finish_reason": "stop"
            }
        ]
    
    def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Return scripted response or simulate tool calling."""
        self.call_count += 1
        
        # If we have scripted responses, use them
        if self.scripted_responses and self.current_script_index < len(self.scripted_responses):
            response_data = self.scripted_responses[self.current_script_index]
            self.current_script_index += 1
            
            if "tool_calls" in response_data:
                return LLMResponse(
                    tool_calls=[ToolCall(**tc) for tc in response_data["tool_calls"]],
                    finish_reason="tool_calls"
                )
            else:
                return LLMResponse(
                    content=response_data.get("content", ""),
                    finish_reason="stop"
                )
        
        # Fallback: simple mock response
        return LLMResponse(
            content="Mock research complete",
            finish_reason="stop",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        )
    
    def estimate_cost(self, usage: Dict[str, int]) -> float:
        """Mock cost estimation."""
        return 0.001  # $0.001 per 1K tokens


def get_llm_client() -> LLMClient:
    """Factory function to get the appropriate LLM client."""
    from app.config import config
    
    if config.MOCK_MODE:
        return MockLLMClient()
    
    # In future phases, return real Gemini client
    # For now, return mock even in live mode until Phase 2 is complete
    return MockLLMClient()
