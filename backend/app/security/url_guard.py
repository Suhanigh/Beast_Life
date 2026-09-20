"""SSRF protection: URL validation and sanitization."""
import re
import ipaddress
from urllib.parse import urlparse
from typing import Optional, Tuple


# Blocked IP ranges (private, loopback, link-local)
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),     # Loopback
    ipaddress.ip_network("10.0.0.0/8"),      # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),   # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local
    ipaddress.ip_network("::1/128"),         # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),       # IPv6 private
    ipaddress.ip_network("fe80::/10"),       # IPv6 link-local
]

# Allowed schemes
ALLOWED_SCHEMES = {"http", "https"}

# Blocked domains (for additional security)
BLOCKED_DOMAINS = {
    "localhost",
    "metadata.google.internal",  # GCP metadata
    "169.254.169.254",          # AWS metadata
}


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL for SSRF protection.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False, f"URL scheme '{parsed.scheme}' not allowed"
        
        # Check for blocked domains
        if parsed.hostname and parsed.hostname.lower() in BLOCKED_DOMAINS:
            return False, f"Domain '{parsed.hostname}' is blocked"
        
        # Check for IP addresses in blocked ranges
        if parsed.hostname:
            # Check if hostname is an IP address
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                for blocked_range in BLOCKED_IP_RANGES:
                    if ip in blocked_range:
                        return False, f"IP address '{ip}' is in blocked range"
            except ValueError:
                # Not an IP address, that's fine
                pass
        
        # Basic URL format validation
        if not parsed.netloc:
            return False, "Invalid URL format"
        
        return True, None
        
    except Exception as e:
        return False, f"URL validation error: {str(e)}"


def sanitize_url(url: str) -> Optional[str]:
    """
    Sanitize URL by removing fragments and certain query parameters.
    Returns None if URL is invalid.
    """
    is_valid, error = validate_url(url)
    if not is_valid:
        return None
    
    try:
        parsed = urlparse(url)
        # Reconstruct URL without fragment
        clean_url = parsed._replace(fragment="").geturl()
        return clean_url
    except Exception:
        return None


def is_from_search_results(url: str, search_results: list) -> bool:
    """
    Check if URL is from provided search results.
    This is an additional safety check to ensure we only fetch pages the search tool returned.
    """
    search_urls = {result.get("url", "") for result in search_results}
    return url in search_urls
