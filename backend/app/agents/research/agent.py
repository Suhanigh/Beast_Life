"""Research agent with tool-calling LLM."""
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.providers.llm import LLMClient, LLMMessage, ToolCall, get_llm_client
from app.providers.search import SearchClient, get_search_client
from app.providers.page_reader import PageReader, get_page_reader
from app.security.url_guard import validate_url, is_from_search_results
from app.config import config
from app.agents.research.prompts import (
    RESEARCH_SYSTEM_PROMPT,
    WEB_SEARCH_TOOL_DESCRIPTION,
    READ_PAGE_TOOL_DESCRIPTION,
    FINISH_TOOL_DESCRIPTION
)


class ResearchAgent:
    """Research agent that uses tool-calling LLM to gather information."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        search_client: Optional[SearchClient] = None,
        page_reader: Optional[PageReader] = None
    ):
        """Initialize research agent with clients."""
        self.llm_client = llm_client or get_llm_client()
        self.search_client = search_client or get_search_client()
        self.page_reader = page_reader or get_page_reader()
        
        # State tracking
        self.tool_calls = []
        self.sources = []
        self.search_results_cache = {}  # For validation
        self.tool_call_count = 0
        self.followup_search_count = 0
        self.start_time = None
    
    def research(
        self,
        product_name: str,
        product_description: str,
        target_audience: str,
        campaign_objective: str,
        tone: str
    ) -> Dict[str, Any]:
        """
        Execute research workflow for a campaign brief.
        
        Returns:
            Dict with angles, sources, tool_calls, source_gap
        """
        self.start_time = time.time()
        self.tool_calls = []
        self.sources = []
        self.search_results_cache = {}
        self.tool_call_count = 0
        self.followup_search_count = 0
        
        # Build system prompt with limits
        system_prompt = RESEARCH_SYSTEM_PROMPT.format(
            MAX_TOOL_CALLS=config.MAX_TOOL_CALLS,
            MAX_FOLLOWUP_SEARCHES=config.MAX_FOLLOWUP_SEARCHES,
            PAGE_TEXT_CAP=config.PAGE_TEXT_CAP,
            RESEARCH_WALL_CLOCK=config.RESEARCH_WALL_CLOCK
        )
        
        # Build user prompt
        user_prompt = f"""
Research for a marketing campaign:

Product: {product_name}
Description: {product_description}
Target Audience: {target_audience}
Campaign Objective: {campaign_objective}
Tone: {tone}

CRITICAL INSTRUCTIONS:
1. Start with web_search for the product category and target audience
2. ALWAYS use the exact URLs returned by web_search - never make up URLs
3. Read the actual search results pages to gather real information
4. Do not use example.com or any made-up URLs
5. Base your insights on actual source content

Please research this product and audience to develop 3 creative marketing angles.
"""
        
        # Define tools
        tools = [
            {
                "name": "web_search",
                "description": WEB_SEARCH_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "read_page",
                "description": READ_PAGE_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to read"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "finish",
                "description": FINISH_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "object", "description": "Final research output"}
                    },
                    "required": ["result"]
                }
            }
        ]
        
        # Start conversation
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]
        
        # Main tool-calling loop
        max_iterations = config.MAX_TOOL_CALLS + 2  # +2 for safety
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Check limits
            if self.tool_call_count >= config.MAX_TOOL_CALLS:
                return self._finish_with_limit("Maximum tool calls reached")
            
            if self.followup_search_count >= config.MAX_FOLLOWUP_SEARCHES:
                return self._finish_with_limit("Maximum follow-up searches reached")
            
            elapsed = time.time() - self.start_time
            if elapsed >= config.RESEARCH_WALL_CLOCK:
                return self._finish_with_limit("Research time limit reached")
            
            # Call LLM
            try:
                response = self.llm_client.chat(messages, tools=tools)
            except Exception as e:
                return self._finish_with_error(f"LLM call failed: {str(e)}")
            
            # Handle tool calls
            if response.tool_calls:
                messages.append(LLMMessage(
                    role="assistant",
                    tool_calls=response.tool_calls
                ))
                
                for tool_call in response.tool_calls:
                    tool_result = self._execute_tool(tool_call)
                    messages.append(LLMMessage(
                        role="tool",
                        tool_call_id=str(tool_call.name + str(self.tool_call_count)),
                        content=json.dumps(tool_result)
                    ))
            elif response.content:
                # LLM provided final response without tool call
                messages.append(LLMMessage(
                    role="assistant",
                    content=response.content
                ))
                # Try to parse as JSON result
                try:
                    result = json.loads(response.content)
                    if "angles" in result:
                        # Populate sources and tool_calls from agent state
                        result["sources"] = self.sources
                        result["tool_calls"] = self.tool_calls
                        
                        # Check source gap
                        source_gap = None
                        if len(result["sources"]) < 3:
                            source_gap = f"Only {len(result['sources'])} source(s) found (minimum 3 required)"
                        result["source_gap"] = source_gap
                        
                        return result
                except json.JSONDecodeError:
                    pass
                break
            else:
                break
        
        # If we exit loop without finish, return error
        return self._finish_with_error("Research did not complete properly")
    
    def _execute_tool(self, tool_call: ToolCall) -> Dict[str, Any]:
        """Execute a tool call and return result."""
        self.tool_call_count += 1
        start_time = time.time()
        
        try:
            if tool_call.name == "web_search":
                result = self._execute_web_search(tool_call.arguments)
            elif tool_call.name == "read_page":
                result = self._execute_read_page(tool_call.arguments)
            elif tool_call.name == "finish":
                result = self._execute_finish(tool_call.arguments)
                if "final_result" in result:
                    return result  # Special signal to finish
            else:
                result = {"error": f"Unknown tool: {tool_call.name}"}
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log tool call
            self.tool_calls.append({
                "step": self.tool_call_count,
                "tool": tool_call.name,
                "args": tool_call.arguments,
                "result_summary": str(result)[:200],
                "decision": f"Executed {tool_call.name}",
                "latency_ms": latency_ms
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def _execute_web_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute web search tool."""
        query = arguments.get("query")
        if not query:
            return {"error": "Query required"}
        
        if self.tool_call_count > 1:  # First search doesn't count as followup
            self.followup_search_count += 1
        
        try:
            response = self.search_client.search(query, max_results=10)
            
            # Cache results for URL validation
            self.search_results_cache[query] = [
                {"url": r.url, "title": r.title} for r in response.results
            ]
            
            # Explicitly tell LLM to use these URLs
            urls_list = "\n".join([f"- {r.url}: {r.title}" for r in response.results])
            
            return {
                "results": [
                    {
                        "title": r.title,
                        "url": r.url,
                        "snippet": r.snippet
                    }
                    for r in response.results
                ],
                "total": len(response.results),
                "message": f"Found {len(response.results)} search results. IMPORTANT: You MUST use these exact URLs for read_page: {urls_list}"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _execute_read_page(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute read page tool."""
        url = arguments.get("url")
        if not url:
            return {"error": "URL required"}
        
        # If LLM tries to use example.com or invalid URL, substitute with real search result
        if "example.com" in url:
            # Get the first available real URL from search results
            all_search_results = []
            for results in self.search_results_cache.values():
                all_search_results.extend(results)
            
            if all_search_results:
                real_url = all_search_results[0]["url"]
                print(f"⚠ LLM tried to use invalid URL '{url}', substituting with real URL: {real_url}")
                url = real_url
        
        # Validate URL
        is_valid, error = validate_url(url)
        if not is_valid:
            return {"error": f"URL validation failed: {error}"}
        
        try:
            page_data = self.page_reader.read_page(url)
            
            if "error" in page_data:
                return page_data
            
            # Add to sources
            source_id = len(self.sources) + 1
            self.sources.append({
                "id": source_id,
                "title": page_data.get("title", "Unknown"),
                "url": url,
                "accessed_at": page_data.get("accessed_at"),
                "excerpt": page_data.get("excerpt", "")
            })
            
            return {
                "title": page_data.get("title"),
                "text": page_data.get("text"),
                "excerpt": page_data.get("excerpt"),
                "source_id": source_id
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _execute_finish(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute finish tool and validate result."""
        result = arguments.get("result")
        if not result:
            return {"error": "Result required"}
        
        try:
            # Populate sources from agent state
            result["sources"] = self.sources
            result["tool_calls"] = self.tool_calls
            
            validated = self._validate_and_return(result)
            return {"final_result": validated}
        except Exception as e:
            return {"error": f"Validation failed: {str(e)}"}
    
    def _validate_and_return(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate result and return final output."""
        # Check for required fields
        if "angles" not in result:
            raise ValueError("Missing 'angles' in result")
        
        angles = result.get("angles", [])
        if len(angles) != 3:
            raise ValueError(f"Expected 3 angles, got {len(angles)}")
        
        # Ensure sources and tool_calls are present
        if "sources" not in result:
            result["sources"] = self.sources
        if "tool_calls" not in result:
            result["tool_calls"] = self.tool_calls
        
        # Check source gap
        source_gap = None
        if len(result["sources"]) < 3:
            source_gap = f"Only {len(result['sources'])} source(s) found (minimum 3 required)"
        
        return {
            "angles": result["angles"],
            "sources": result["sources"],
            "tool_calls": result["tool_calls"],
            "source_gap": source_gap
        }
    
    def _finish_with_limit(self, reason: str) -> Dict[str, Any]:
        """Finish research due to limits."""
        return {
            "angles": [],
            "sources": self.sources,
            "tool_calls": self.tool_calls,
            "source_gap": f"Research stopped due to limit: {reason}"
        }
    
    def _finish_with_error(self, error: str) -> Dict[str, Any]:
        """Finish research due to error."""
        return {
            "angles": [],
            "sources": self.sources,
            "tool_calls": self.tool_calls,
            "source_gap": f"Research failed: {error}"
        }
    
    def close(self):
        """Clean up resources."""
        if self.page_reader:
            self.page_reader.close()
