"""Client for the TGOS address geocoding service."""

from __future__ import annotations

import logging
import math
import os
import time

import httpx

logger = logging.getLogger(__name__)


class TGOSConfigurationError(RuntimeError):
    """Raised when TGOS credentials are missing or incomplete."""


class TGOSResponseError(RuntimeError):
    """Raised when TGOS returns a response that cannot be interpreted."""


class TGOSRequestError(RuntimeError):
    """Raised when a TGOS request fails after retrying."""


class TGOSClient:
    """HTTP client for TGOS's documented ``QueryAddr`` endpoint.

    The credentials are read from ``TGOS_APP_ID`` and ``TGOS_API_KEY`` when
    they are not passed explicitly.  This client never loads ``.env`` files
    or logs either credential; applications can load their configuration
    before constructing the client.
    """

    DEFAULT_BASE_URL = "https://addr.tgos.tw/addrws/v30/QueryAddr.asmx/QueryAddr"
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0

    def __init__(
        self,
        app_id: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ) -> None:
        """Initialize a TGOS client.

        Args:
            app_id: TGOS application ID, or ``TGOS_APP_ID``.
            api_key: TGOS API key, or ``TGOS_API_KEY``.
            base_url: TGOS QueryAddr endpoint.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of attempts for network/5xx errors.
            retry_delay: Base delay between attempts in seconds.
        """
        self.app_id = app_id if app_id is not None else os.getenv("TGOS_APP_ID")
        self.api_key = api_key if api_key is not None else os.getenv("TGOS_API_KEY")
        self.base_url: str = base_url or os.getenv("TGOS_API_BASE_URL") or self.DEFAULT_BASE_URL

        self.timeout = (
            timeout
            if timeout is not None
            else self._read_float_env("TGOS_API_TIMEOUT", self.DEFAULT_TIMEOUT)
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else self._read_int_env("HTTP_MAX_RETRIES", self.DEFAULT_MAX_RETRIES)
        )
        self.retry_delay = (
            retry_delay
            if retry_delay is not None
            else self._read_float_env("HTTP_RETRY_DELAY", self.DEFAULT_RETRY_DELAY)
        )

        if self.timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if self.max_retries < 1:
            raise ValueError("max_retries must be at least one")
        if self.retry_delay < 0:
            raise ValueError("retry_delay cannot be negative")

        self._client: httpx.Client | None = None

        logger.debug(
            "TGOS client initialized: base_url=%s, timeout=%ss, max_retries=%s",
            self.base_url,
            self.timeout,
            self.max_retries,
        )

    @staticmethod
    def _read_float_env(name: str, default: float) -> float:
        value = os.getenv(name)
        return default if value is None else float(value)

    @staticmethod
    def _read_int_env(name: str, default: int) -> int:
        value = os.getenv(name)
        return default if value is None else int(value)

    def __enter__(self) -> TGOSClient:
        """Open a reusable HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Close the reusable HTTP client."""
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client, if it is open."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def geocode_address(
        self,
        address: str,
    ) -> tuple[float | None, float | None, str | None, float | None]:
        """Convert an address to WGS84 coordinates through TGOS.

        Returns ``(longitude, latitude, matched_address, confidence)``.  The
        confidence value is ``1.0`` only for the service's exact-match result;
        it is ``None`` for fuzzy matches because TGOS does not provide a
        numeric confidence score.
        """
        self._validate_credentials()

        if not address or not address.strip():
            logger.warning("Empty address provided")
            return None, None, None, 0.0

        address = address.strip()
        use_temporary_client = self._client is None
        if use_temporary_client:
            self._client = httpx.Client(timeout=self.timeout)

        try:
            return self._geocode_with_retry(address)
        finally:
            if use_temporary_client:
                self.close()

    def _validate_credentials(self) -> None:
        if not self.app_id or not self.api_key:
            raise TGOSConfigurationError(
                "TGOS geocoding requires both TGOS_APP_ID and TGOS_API_KEY. "
                "Pass app_id/api_key or configure those environment variables."
            )

    def _geocode_with_retry(
        self,
        address: str,
    ) -> tuple[float | None, float | None, str | None, float | None]:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("Geocoding request attempt %s/%s", attempt, self.max_retries)
                return self._do_geocode_request(address)
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code < 500 and status_code != 429:
                    raise TGOSRequestError(
                        f"TGOS rejected the request with HTTP {status_code}"
                    ) from exc
                last_error = exc
            except httpx.RequestError as exc:
                last_error = exc

            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)

        raise TGOSRequestError(
            f"TGOS request failed after {self.max_retries} attempts"
        ) from last_error

    def _do_geocode_request(
        self,
        address: str,
    ) -> tuple[float | None, float | None, str | None, float | None]:
        if self._client is None:
            raise RuntimeError("HTTP client is not initialized")

        params = {
            "oAPPId": self.app_id,
            "oAPIKey": self.api_key,
            "oAddress": address,
            "oSRS": "EPSG:4326",
            "oFuzzyType": "0",
            "oResultDataType": "JSON",
            "oFuzzyBuffer": "0",
            "oIsOnlyFullMatch": "false",
            "oIsLockCounty": "false",
            "oIsLockTown": "false",
            "oIsLockVillage": "false",
            "oIsLockRoadSection": "false",
            "oIsLockLane": "false",
            "oIsLockAlley": "false",
            "oIsLockArea": "false",
            "oIsSameNumber_SubNumber": "true",
            "oCanIgnoreVillage": "true",
            "oCanIgnoreNeighborhood": "true",
            "oReturnMaxCount": "1",
        }

        logger.debug("Sending TGOS address request to %s", self.base_url)
        response = self._client.get(self.base_url, params=params)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as exc:
            raise TGOSResponseError("TGOS returned invalid JSON") from exc

        if not isinstance(data, dict):
            raise TGOSResponseError("TGOS returned an unexpected response object")

        address_list = data.get("AddressList")
        if address_list is None:
            raise TGOSResponseError("TGOS response is missing AddressList")
        if not isinstance(address_list, list):
            raise TGOSResponseError("TGOS AddressList is not a list")
        if not address_list:
            logger.info("TGOS did not find an address")
            return None, None, None, 0.0

        best_match = address_list[0]
        if not isinstance(best_match, dict):
            raise TGOSResponseError("TGOS AddressList contains an invalid item")

        try:
            lon = float(best_match["X"])
            lat = float(best_match["Y"])
        except (KeyError, TypeError, ValueError) as exc:
            raise TGOSResponseError("TGOS response is missing X/Y coordinates") from exc

        if not math.isfinite(lon) or not math.isfinite(lat):
            raise TGOSResponseError("TGOS returned non-finite coordinates")
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise TGOSResponseError("TGOS returned coordinates outside EPSG:4326")

        matched_address = best_match.get("FULL_ADDR") or address
        if not isinstance(matched_address, str):
            matched_address = str(matched_address)

        confidence: float | None = None
        info = data.get("Info")
        if isinstance(info, list) and info and isinstance(info[0], dict):
            if info[0].get("OutMatchType") == "完全比對":
                confidence = 1.0

        logger.info("TGOS geocoding succeeded for one address")
        return lon, lat, matched_address, confidence


__all__ = [
    "TGOSClient",
    "TGOSConfigurationError",
    "TGOSRequestError",
    "TGOSResponseError",
]
