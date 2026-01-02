from langchain_tavily import TavilySearch
from langchain.tools import tool
import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API key from environment variable
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable is not set")

@dataclass
class TavilyConfig:
    """Configuration class for Tavily search parameters."""
    max_results: int = 5
    topic: str = "general"
    include_answer: bool = False
    include_raw_content: bool = True
    include_images: bool = False
    include_image_descriptions: bool = False
    search_depth: str = "basic"
    country: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @staticmethod
    def get_medical_domains() -> List[str]:
        """Get list of trusted medical domains for search."""
        return [
            "ncbi.nlm.nih.gov",
            "pubmed.ncbi.nlm.nih.gov",
            "nih.gov",
            "nejm.org",
            "bmj.com",
            "jamanetwork.com",
            "nature.com",
            "science.org",
            "springer.com",
            "medlineplus.gov",
            "mayoclinic.org",
            "webmd.com",
            "hopkinsmedicine.org",
            "clevelandclinic.org",
            "patient.info",
            "community.patient.info",
            "healthline.com",
            "drugs.com",
            "medicinenet.com",
            "rarediseases.org",
            "patientslikeme.com",
            "healthboards.com",
            "verywellhealth.com",
            "thelancet.com",
        ]

    @staticmethod
    def get_excluded_domains() -> List[str]:
        """Get list of domains to exclude from search results."""
        return [
            "youtube.com",
            "twitter.com",
            "x.com",
            "facebook.com",
            "instagram.com",
            "reddit.com",
            "medium.com",
            "tiktok.com",
            "quora.com",
            "pinterest.com",
            "linkedin.com",
        ]


def build_tavily(config: Optional[TavilyConfig] = None) -> TavilySearch:
    """
    Build a TavilySearch instance with medical-focused configuration.

    Args:
        config: Optional TavilyConfig object. If None, uses default medical config.

    Returns:
        Configured TavilySearch instance

    Raises:
        ValueError: If TAVILY_API_KEY is not set in environment
        Exception: If TavilySearch initialization fails
    """
    try:
        if config is None:
            config = TavilyConfig()

        logger.info("Initializing TavilySearch with medical domain configuration")

        tool = TavilySearch(
            api_key=TAVILY_API_KEY,
            max_results=config.max_results,
            topic=config.topic,
            include_answer=config.include_answer,
            include_raw_content=config.include_raw_content,
            include_images=config.include_images,
            include_image_descriptions=config.include_image_descriptions,
            search_depth=config.search_depth,
            include_domains=TavilyConfig.get_medical_domains(),
            exclude_domains=TavilyConfig.get_excluded_domains(),
            country=config.country,
            start_date=config.start_date,
            end_date=config.end_date,
        )

        logger.info("TavilySearch initialized successfully")
        return tool

    except Exception as e:
        logger.error(f"Failed to initialize TavilySearch: {str(e)}")
        raise

# Global tool instance - will be initialized lazily
_tavily_tool: Optional[TavilySearch] = None


def get_tavily_tool() -> TavilySearch:
    """Get or create the TavilySearch tool instance."""
    global _tavily_tool
    if _tavily_tool is None:
        _tavily_tool = build_tavily()
    return _tavily_tool


def format_search_results(results: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Format Tavily search results into a clean, consistent format.

    Args:
        results: Raw results from TavilySearch

    Returns:
        List of formatted result dictionaries with title and content
    """
    try:
        if not isinstance(results, dict) or "results" not in results:
            logger.warning("Invalid results format received from TavilySearch")
            return []

        formatted_results = []
        for result in results["results"]:
            if not isinstance(result, dict):
                continue

            formatted_result = {
                "title": result.get("title", "").strip(),
                "content": result.get("content", "").strip(),
                "url": result.get("url", "").strip()
            }

            # Only include results with meaningful content
            if formatted_result["title"] and formatted_result["content"]:
                formatted_results.append(formatted_result)

        logger.info(f"Formatted {len(formatted_results)} search results")
        return formatted_results

    except Exception as e:
        logger.error(f"Error formatting search results: {str(e)}")
        return []


@tool()
def tavily_medical_search(query: str) -> List[Dict[str, str]]:
    """用 Tavily 在可信医学域名内搜索，返回标题/内容/URL。自动限制可信站点，减少噪声。适合获取最新医疗资讯或背景资料。"""
    try:
        if not query or not query.strip():
            logger.warning("Empty query provided to tavily_medical_search")
            return []

        logger.info(f"Searching for medical information: {query[:100]}...")

        tool = get_tavily_tool()
        raw_results = tool.invoke(query.strip())
        formatted_results = format_search_results(raw_results)

        logger.info(f"Medical search completed: {len(formatted_results)} results found")
        return formatted_results

    except Exception as e:
        logger.error(f"Error in tavily_medical_search: {str(e)}")
        return []


if __name__ == "__main__":
    # Example usage for testing
    test_query = "Differential diagnosis of acute chest pain in emergency settings."
    results = tavily_medical_search.invoke(test_query)

    print(f"Search results for: {test_query}")
    print("-" * 50)
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   Content: {result['content'][:200]}...")
        print(f"   URL: {result['url']}")
        print()
