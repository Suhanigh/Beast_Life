"""Page reading with httpx + trafilatura for content extraction."""
import httpx
import trafilatura
from typing import Optional, Dict, Any
from datetime import datetime
from app.security.url_guard import validate_url
from app.config import config


class PageReader:
    """Reads and extracts content from web pages."""
    
    def __init__(self, timeout: int = None, mock_mode: bool = False):
        """Initialize page reader with timeout."""
        self.timeout = timeout or config.PAGE_FETCH_TIMEOUT
        self.mock_mode = mock_mode or config.MOCK_MODE
        self.client = httpx.Client(timeout=self.timeout) if not mock_mode else None
        
        # Mock page content for testing
        self.mock_pages = {
            "https://example.com/protein-benefits": {
                "title": "The Benefits of Protein Powder for Gym-Goers",
                "text": "Protein powder has become an essential supplement for fitness enthusiasts. Research shows that adequate protein intake is crucial for muscle recovery and growth. For busy gym-goers, protein powder offers a convenient way to meet daily protein requirements without extensive meal preparation. Studies indicate that consuming 20-30g of protein post-workout can significantly enhance muscle protein synthesis. Whey protein, in particular, is rapidly absorbed and rich in leucine, making it ideal for post-exercise recovery."
            },
            "https://example.com/protein-timing": {
                "title": "When to Take Protein: Timing Matters",
                "text": "The timing of protein consumption can impact its effectiveness. Research suggests that consuming protein within 30 minutes after workout maximizes muscle protein synthesis. This 'anabolic window' is when muscles are most receptive to nutrient uptake. However, total daily protein intake remains more important than precise timing. For optimal results, aim for 1.6-2.2g of protein per kg of body weight daily, distributed across meals and post-workout nutrition."
            },
            "https://example.com/plant-animal-protein": {
                "title": "Plant vs Animal Protein: What's Best?",
                "text": "Both plant and animal proteins can be effective for muscle building, but they have different amino acid profiles. Whey protein is particularly high in leucine, an essential amino acid that triggers muscle protein synthesis. Plant proteins like pea and rice protein can be complete when combined. The choice often comes down to dietary preferences, digestibility, and fitness goals. Research shows that with proper planning, plant-based athletes can achieve similar muscle-building results."
            },
            "https://example.com/protein-market": {
                "title": "Protein Powder Market Trends 2024",
                "text": "The protein supplement market continues to experience robust growth as consumers increasingly prioritize health and fitness. Market analysis shows strong demand for convenient, high-quality protein products. Consumer preferences are shifting toward clean label products with transparent ingredient lists. The market expansion is driven by rising gym memberships, health consciousness, and the convenience of protein supplements for busy lifestyles."
            },
            "https://example.com/clean-protein": {
                "title": "Clean Label Protein Products on the Rise",
                "text": "Consumers increasingly seek protein powders without artificial sweeteners, colors, or preservatives. The clean label movement has gained significant traction in the supplement industry. Products with natural ingredients and minimal processing are preferred by health-conscious consumers. Market research indicates that clean label protein products command premium pricing and show strong growth potential. This trend reflects broader consumer demand for transparency and natural ingredients."
            },
            "https://example.com/busy-fitness": {
                "title": "Fitness Tips for Busy Professionals",
                "text": "Time-efficient workouts are essential for busy professionals. High-intensity interval training (HIIT) can provide significant benefits in short sessions. Nutrition plays a crucial role, with meal prep being a key strategy for maintaining healthy eating habits. Protein supplements offer convenience for those with limited time for meal preparation. The key is consistency rather than perfection in both exercise and nutrition."
            },
            "https://example.com/meal-prep": {
                "title": "Meal Prep for Active Lifestyles",
                "text": "Meal preparation is a cornerstone of maintaining nutrition goals for active individuals. Planning and preparing meals in advance ensures consistent protein intake and supports fitness objectives. Protein powders can supplement meal prep by providing convenient nutrition between meals. The combination of whole foods and strategic supplementation helps meet the high protein demands of active lifestyles."
            },
            "https://example.com/protein-guide": {
                "title": "Protein Supplements: A Complete Guide",
                "text": "Protein supplements come in various forms including whey, casein, and plant-based options. Each type has different absorption rates and amino acid profiles. Whey protein is rapidly absorbed, making it ideal post-workout. Casein digests slowly, providing sustained amino acid release. Plant proteins offer alternatives for those with dietary restrictions. The choice depends on individual goals, dietary preferences, and timing needs."
            },
            "https://example.com/whey-casein": {
                "title": "Whey vs Casein Protein",
                "text": "Whey and casein proteins offer different benefits due to their digestion rates. Whey protein rapidly increases amino acid levels in the blood, making it ideal for post-workout recovery. Casein protein provides a slow, steady release of amino acids over several hours, beneficial for overnight recovery. Many athletes combine both types to maximize benefits. Research supports the strategic use of different protein types based on timing and goals."
            }
        }
    
    def read_page(self, url: str) -> Dict[str, Any]:
        """
        Read and extract content from a URL.
        
        Returns:
            Dict with url, title, text, excerpt, accessed_at, error (if any)
        """
        # Validate URL for SSRF protection
        is_valid, error = validate_url(url)
        if not is_valid:
            return {
                "url": url,
                "error": f"URL validation failed: {error}",
                "accessed_at": datetime.utcnow().isoformat()
            }
        
        # Mock mode: return scripted content
        if self.mock_mode and url in self.mock_pages:
            page_data = self.mock_pages[url]
            content = page_data["text"]
            excerpt = content[:200] + "..." if len(content) > 200 else content
            
            # Enforce text cap
            if len(content) > config.PAGE_TEXT_CAP:
                content = content[:config.PAGE_TEXT_CAP]
            
            return {
                "url": url,
                "title": page_data["title"],
                "text": content,
                "excerpt": excerpt,
                "accessed_at": datetime.utcnow().isoformat()
            }
        
        # Mock mode: return generic content for unknown URLs
        if self.mock_mode:
            return {
                "url": url,
                "title": "Mock Page",
                "text": "This is mock page content for testing purposes.",
                "excerpt": "This is mock page content...",
                "accessed_at": datetime.utcnow().isoformat()
            }
        
        # Live mode: actual page reading
        try:
            # Fetch the page
            response = self.client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            # Extract content using trafilatura
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return {
                    "url": url,
                    "error": "Failed to download page content",
                    "accessed_at": datetime.utcnow().isoformat()
                }
            
            # Extract main content
            content = trafilatura.extract(downloaded)
            
            # Extract title using BeautifulSoup from the HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(downloaded, 'html.parser')
            title = soup.title.string if soup.title else "Unknown Title"
            
            # Create excerpt (first 200 chars)
            excerpt = content[:200] + "..." if len(content) > 200 else content
            
            # Enforce text cap
            if len(content) > config.PAGE_TEXT_CAP:
                content = content[:config.PAGE_TEXT_CAP]
            
            return {
                "url": url,
                "title": title,
                "text": content,
                "excerpt": excerpt,
                "accessed_at": datetime.utcnow().isoformat(),
                "status_code": response.status_code
            }
            
        except httpx.TimeoutException:
            return {
                "url": url,
                "error": f"Request timed out after {self.timeout}s",
                "accessed_at": datetime.utcnow().isoformat()
            }
        except httpx.HTTPStatusError as e:
            return {
                "url": url,
                "error": f"HTTP error: {e.response.status_code}",
                "accessed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "url": url,
                "error": f"Unexpected error: {str(e)}",
                "accessed_at": datetime.utcnow().isoformat()
            }
    
    def close(self):
        """Close the HTTP client."""
        if self.client:
            self.client.close()


def get_page_reader() -> PageReader:
    """Factory function to get a page reader instance."""
    return PageReader()
