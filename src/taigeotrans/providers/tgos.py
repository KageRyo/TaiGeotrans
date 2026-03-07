"""
TGOS API client for address geocoding.
Wraps the Taiwan Geospatial One Stop (TGOS) API from National Land Surveying and Mapping Center.
"""

import logging
import os
import time
from typing import Optional, Tuple

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class TGOSClient:
    """TGOS API client for address geocoding"""
    
    DEFAULT_BASE_URL = "https://api.tgos.tw/TGOS_API/api"
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ) -> None:
        """
        Initialize TGOS API client.
        
        Args:
            base_url: API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url or os.getenv("TGOS_API_BASE_URL", self.DEFAULT_BASE_URL)
        self.timeout = timeout or float(os.getenv("TGOS_API_TIMEOUT", self.DEFAULT_TIMEOUT))
        self.max_retries = max_retries or int(
            os.getenv("HTTP_MAX_RETRIES", self.DEFAULT_MAX_RETRIES)
        )
        self.retry_delay = retry_delay or float(
            os.getenv("HTTP_RETRY_DELAY", self.DEFAULT_RETRY_DELAY)
        )
        
        self._client: Optional[httpx.Client] = None
        logger.info(
            f"TGOS client initialized: base_url={self.base_url}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries}"
        )
    
    def __enter__(self) -> "TGOSClient":
        """Context manager enter"""
        self._client = httpx.Client(timeout=self.timeout)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit"""
        if self._client:
            self._client.close()
            self._client = None
    
    def geocode_address(
        self, 
        address: str
    ) -> Tuple[Optional[float], Optional[float], Optional[str], float]:
        """
        Convert Taiwan address to WGS84 coordinates via TGOS API.
        
        Args:
            address: Taiwan address in Chinese
        
        Returns:
            Tuple of (longitude, latitude, matched_address, confidence)
            Returns (None, None, None, 0.0) if geocoding fails
        """
        if not address or not address.strip():
            logger.warning("Empty address provided")
            return None, None, None, 0.0
        
        address = address.strip()
        
        # Create temporary client if not in context
        use_temp_client = self._client is None
        if use_temp_client:
            self._client = httpx.Client(timeout=self.timeout)
        
        try:
            lon, lat, matched_addr, conf = self._geocode_with_retry(address)
            return lon, lat, matched_addr, conf
        finally:
            if use_temp_client and self._client:
                self._client.close()
                self._client = None
    
    def _geocode_with_retry(
        self, 
        address: str
    ) -> Tuple[Optional[float], Optional[float], Optional[str], float]:
        """Geocode address with retry mechanism"""
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Geocoding '{address}' (attempt {attempt}/{self.max_retries})")
                return self._do_geocode_request(address)
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Request timeout (attempt {attempt}/{self.max_retries}): {e}")
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(f"HTTP error (attempt {attempt}/{self.max_retries}): {e}")
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error (attempt {attempt}/{self.max_retries}): {e}")
            
            # Wait before retrying if attempts remain
            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)  # Exponential backoff
        
        # All retries failed
        logger.error(f"Geocoding failed after {self.max_retries} attempts: {last_error}")
        return None, None, None, 0.0
    
    def _do_geocode_request(
        self, 
        address: str
    ) -> Tuple[Optional[float], Optional[float], Optional[str], float]:
        """Execute actual TGOS API request"""
        if not self._client:
            raise RuntimeError("HTTP client not initialized")
        
        url = f"{self.base_url}/Address/AddressQuery"
        
        # Build parameters according to TGOS API documentation
        params = {
            "address": address,
            "oAPPId": "",  # Optional, may be required in some cases
        }
        
        logger.debug(f"Sending request to TGOS: {url}")
        response = self._client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse TGOS response format
        # Note: Actual TGOS API response format may vary
        if not isinstance(data, dict):
            logger.warning(f"Unexpected response format: {type(data)}")
            return None, None, None, 0.0
        
        # TGOS API typically returns structure like (adjust according to actual API):
        # {
        #   "AddressList": [
        #     {
        #       "ADDRESS": "Standardized address",
        #       "X": "Longitude (WGS84)",
        #       "Y": "Latitude (WGS84)",
        #       "FULL_ADDR": "Full address"
        #     }
        #   ]
        # }
        
        address_list = data.get("AddressList", [])
        if not address_list or len(address_list) == 0:
            logger.info(f"TGOS did not find address: {address}")
            return None, None, None, 0.0
        
        # Take first result (usually best match)
        best_match = address_list[0]
        
        try:
            # Adjust field names according to actual API
            lon_str = best_match.get("X") or best_match.get("LON") or best_match.get("LON_WGS84")
            lat_str = best_match.get("Y") or best_match.get("LAT") or best_match.get("LAT_WGS84")
            matched_address = (
                best_match.get("FULL_ADDR") 
                or best_match.get("ADDRESS") 
                or address
            )
            
            if lon_str is None or lat_str is None:
                logger.warning(f"TGOS response missing coordinate data: {best_match}")
                return None, None, matched_address, 0.5
            
            lon = float(lon_str)
            lat = float(lat_str)
            
            # Confidence: higher if only one result
            confidence = 0.9 if len(address_list) == 1 else 0.7
            
            logger.info(
                f"TGOS geocoding successful: {address} -> ({lon}, {lat}), "
                f"matched: {matched_address}, confidence: {confidence}"
            )
            
            return lon, lat, matched_address, confidence
            
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse TGOS response: {e}, data: {best_match}")
            return None, None, None, 0.0
