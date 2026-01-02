#!/usr/bin/env python3
"""
Network I/O operations for Bluesound Controller.

Copyright 2025 tbaur

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import ssl
import urllib.request
import urllib.parse
import urllib.error
import logging
from typing import Optional, Dict

from constants import DEFAULT_TIMEOUT, MAX_XML_SIZE, MAX_RETRIES, RETRY_DELAY_BASE, MAX_RETRY_DELAY
from utils import retry_with_backoff

logger = logging.getLogger("Bluesound")


class Network:
    """
    Centralized network I/O operations.
    
    NOTE: SSL Verification DISABLED for local IoT context.
    This is intentional for local network device communication.
    """
    # DOCUMENTED DEVIATION: SSL Verification DISABLED for local IoT context.
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE
    
    @classmethod
    @retry_with_backoff(
        max_retries=MAX_RETRIES,
        base_delay=RETRY_DELAY_BASE,
        max_delay=MAX_RETRY_DELAY,
        exceptions=(urllib.error.URLError, TimeoutError, ConnectionError, OSError)
    )
    def _request_impl(cls,
                      url: str,
                      method: str = "GET",
                      data: Optional[bytes] = None,
                      headers: Optional[Dict] = None,
                      timeout: int = DEFAULT_TIMEOUT) -> Optional[bytes]:
        """
        Internal implementation of HTTP request (with retry logic).
        
        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            data: Optional encoded data to send
            headers: Optional headers
            timeout: Request timeout in seconds
            
        Returns:
            Response content as bytes, or None on error
        """
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        with urllib.request.urlopen(req, timeout=timeout, context=cls._SSL_CTX) as response:
            # Read with size limit to prevent memory exhaustion
            content = response.read(MAX_XML_SIZE + 1)
            if len(content) > MAX_XML_SIZE:
                logger.warning(f"Payload exceeded size limit ({url})")
                return None
            return content
    
    @classmethod
    def request(cls, 
                url: str, 
                method: str = "GET", 
                data: Optional[Dict] = None, 
                headers: Optional[Dict] = None,
                timeout: int = DEFAULT_TIMEOUT) -> Optional[bytes]:
        """
        Make HTTP request with security, error handling, and retry logic.
        
        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            data: Optional data to send
            headers: Optional headers
            timeout: Request timeout in seconds
            
        Returns:
            Response content as bytes, or None on error
        """
        # Validate URL scheme (only http/https allowed)
        if not url.startswith(('http://', 'https://')):
            logger.warning(f"Invalid URL scheme: {url}")
            return None
        
        # Encode data if provided
        encoded_data = None
        if data:
            encoded_data = urllib.parse.urlencode(data).encode('utf-8')
        
        try:
            return cls._request_impl(url, method, encoded_data, headers, timeout)
        except urllib.error.HTTPError as e:
            # Don't retry on HTTP errors (4xx, 5xx) - these are not transient
            logger.debug(f"HTTP error ({url}): {e.code} {e.reason}")
            return None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            # These are retried by the decorator, but if all retries fail, return None
            logger.debug(f"Network error after retries ({url}): {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error ({url}): {e}")
            return None
    
    @classmethod
    def get(cls, url: str, **kwargs) -> Optional[bytes]:
        """Make GET request."""
        return cls.request(url, method="GET", **kwargs)
    
    @classmethod
    def post(cls, url: str, data: Dict, **kwargs) -> Optional[bytes]:
        """Make POST request."""
        return cls.request(url, method="POST", data=data, **kwargs)

