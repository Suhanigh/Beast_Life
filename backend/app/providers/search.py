"""Search client interface for web search."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import httpx
import os


class SearchResult(BaseModel):
    """Individual search result."""
    title: str
    url: str
    snippet: str
    source: Optional[str] = None


class SearchResponse(BaseModel):
    """Response from search API."""
    results: List[SearchResult]
    query: str
    total_results: Optional[int] = None


class SearchClient(ABC):
    """Abstract search client interface."""
    
    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """Execute web search."""
        pass


class TavilySearchClient(SearchClient):
    """Real Tavily search client for live web search."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Tavily API key."""
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY must be set")
        self.base_url = "https://api.tavily.com/search"
    
    def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """Execute web search using Tavily API."""
        headers = {
            "Content-Type": "application/json"
        }
        
        params = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_image_descriptions": False
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.base_url, json=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Convert Tavily response to our format
                tavily_results = data.get("results", [])
                results = [
                    SearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        snippet=result.get("content", ""),
                        source=result.get("published_date", None)
                    )
                    for result in tavily_results
                ]
                
                return SearchResponse(
                    results=results,
                    query=query,
                    total_results=len(results)
                )
                
        except httpx.HTTPError as e:
            raise Exception(f"Tavily API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")


class MockSearchClient(SearchClient):
    """Mock search client for testing and mock mode."""
    
    def __init__(self, scripted_results: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        """Initialize with optional scripted results by query."""
        self.scripted_results = scripted_results or self._get_default_scripted_results()
        self.call_count = 0
    
    def _get_default_scripted_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get default scripted results for protein-related queries."""
        return {
            "protein powder benefits gym-goers": [
                {
                    "title": "The Benefits of Protein Powder for Gym-Goers",
                    "url": "https://example.com/protein-benefits",
                    "snippet": "Protein powder helps with muscle recovery and growth, especially for busy individuals who need convenient nutrition options.",
                    "source": "Fitness Weekly"
                },
                {
                    "title": "When to Take Protein: Timing Matters",
                    "url": "https://example.com/protein-timing",
                    "snippet": "Research suggests consuming protein within 30 minutes after workout maximizes muscle protein synthesis.",
                    "source": "Nutrition Science"
                },
                {
                    "title": "Plant vs Animal Protein: What's Best?",
                    "url": "https://example.com/plant-animal-protein",
                    "snippet": "Both sources can be effective, but whey protein is particularly high in leucine, an essential amino acid for muscle building.",
                    "source": "Health Today"
                },
                {
                    "title": "Protein Powder Market Trends 2024",
                    "url": "https://example.com/protein-market",
                    "snippet": "The protein supplement market continues to grow as consumers prioritize convenience and fitness goals.",
                    "source": "Market Research"
                },
                {
                    "title": "Clean Label Protein Products on the Rise",
                    "url": "https://example.com/clean-protein",
                    "snippet": "Consumers increasingly seek protein powders without artificial sweeteners, colors, or preservatives.",
                    "source": "Industry Report"
                }
            ],
            "busy professionals fitness nutrition": [
                {
                    "title": "Fitness Tips for Busy Professionals",
                    "url": "https://example.com/busy-fitness",
                    "snippet": "Time-efficient workouts and nutrition strategies for professionals with limited time.",
                    "source": "Business Health"
                },
                {
                    "title": "Meal Prep for Active Lifestyles",
                    "url": "https://example.com/meal-prep",
                    "snippet": "Convenient meal preparation strategies for maintaining nutrition goals.",
                    "source": "Nutrition Guide"
                }
            ],
            "gym goers protein supplements": [
                {
                    "title": "Protein Supplements: A Complete Guide",
                    "url": "https://example.com/protein-guide",
                    "snippet": "Comprehensive guide to protein supplements for gym enthusiasts.",
                    "source": "Fitness Authority"
                },
                {
                    "title": "Whey vs Casein Protein",
                    "url": "https://example.com/whey-casein",
                    "snippet": "Comparison of different protein types for optimal results.",
                    "source": "Supplement Science"
                }
            ]
        }
    
    def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """Return scripted results or fallback to generic mock results."""
        self.call_count += 1
        
        # Check for scripted results (exact match or partial match)
        for scripted_query, results_data in self.scripted_results.items():
            if scripted_query.lower() in query.lower() or query.lower() in scripted_query.lower():
                return SearchResponse(
                    results=[SearchResult(**r) for r in results_data[:max_results]],
                    query=query,
                    total_results=len(results_data)
                )
        
        # Generic mock results
        return SearchResponse(
            results=[
                SearchResult(
                    title=f"Mock result for: {query}",
                    url="https://example.com/mock",
                    snippet="This is a mock search result for testing purposes.",
                    source="Mock Source"
                )
            ],
            query=query,
            total_results=1
        )


def get_search_client() -> SearchClient:
    """Factory function to get the appropriate search client."""
    from app.config import config
    
    if config.MOCK_MODE:
        return MockSearchClient()
    
    # Use real Tavily client if API key is available
    if config.TAVILY_API_KEY:
        try:
            return TavilySearchClient()
        except Exception as e:
            print(f"Warning: Failed to initialize Tavily client: {e}")
            print("Falling back to mock search client")
            return MockSearchClient()
    
    # Fallback to mock if no API key
    print("Warning: TAVILY_API_KEY not set, using mock search")
    return MockSearchClient()
