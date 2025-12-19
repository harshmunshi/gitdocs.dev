"""Low-level Confluence REST API client."""

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from gitdocs.core.errors import AuthError, ConfluenceError

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """
    Low-level HTTP client for Confluence Cloud REST API v2.

    Uses Basic auth with API token.
    """

    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Initialize Confluence client.

        Args:
            base_url: Confluence Cloud base URL
            email: Atlassian account email
            api_token: Confluence API token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        # Confluence Cloud API v2 base
        self.api_base = f"{self.base_url}/wiki/api/v2"
        # Legacy API for some operations
        self.legacy_api_base = f"{self.base_url}/wiki/rest/api"

        self._client = httpx.Client(
            auth=(email, api_token),
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        self._async_client: httpx.AsyncClient | None = None

    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                auth=self._client.auth,
                timeout=self._client.timeout,
                headers=dict(self._client.headers),
            )
        return self._async_client

    def close(self) -> None:
        """Close HTTP clients."""
        self._client.close()
        if self._async_client:
            pass

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 401:
            raise AuthError(
                "Confluence authentication failed. Check your email and API token.",
                details={"status_code": 401},
            )

        if response.status_code == 403:
            raise AuthError(
                "Confluence access forbidden. Check your permissions.",
                details={"status_code": 403},
            )

        if response.status_code == 404:
            raise ConfluenceError(
                "Resource not found",
                status_code=404,
                response_body=response.text,
            )

        if response.status_code == 429:
            raise ConfluenceError(
                "Rate limited by Confluence. Please wait and retry.",
                status_code=429,
            )

        if response.status_code >= 400:
            raise ConfluenceError(
                f"Confluence API error: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        if response.status_code == 204:
            return {}

        return response.json()

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to Confluence API v2."""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        logger.debug(f"GET {url} params={params}")

        response = self._client.get(url, params=params)
        return self._handle_response(response)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request to Confluence API v2."""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        logger.debug(f"POST {url}")

        response = self._client.post(url, json=data, params=params)
        return self._handle_response(response)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PUT request to Confluence API v2."""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        logger.debug(f"PUT {url}")

        response = self._client.put(url, json=data)
        return self._handle_response(response)

    def get_legacy(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to legacy Confluence API."""
        url = f"{self.legacy_api_base}/{endpoint.lstrip('/')}"
        logger.debug(f"GET (legacy) {url} params={params}")

        response = self._client.get(url, params=params)
        return self._handle_response(response)

    def post_legacy(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request to legacy Confluence API."""
        url = f"{self.legacy_api_base}/{endpoint.lstrip('/')}"
        logger.debug(f"POST (legacy) {url}")

        response = self._client.post(url, json=data)
        return self._handle_response(response)

    def put_legacy(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PUT request to legacy Confluence API."""
        url = f"{self.legacy_api_base}/{endpoint.lstrip('/')}"
        logger.debug(f"PUT (legacy) {url}")

        response = self._client.put(url, json=data)
        return self._handle_response(response)

    # =========================================================================
    # Async methods
    # =========================================================================

    async def aget(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Async GET request."""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        response = await self.async_client.get(url, params=params)
        return self._handle_response(response)

    async def apost(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Async POST request."""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        response = await self.async_client.post(url, json=data)
        return self._handle_response(response)
