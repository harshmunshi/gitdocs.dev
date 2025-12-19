"""Low-level Jira REST API client with retry and rate limiting."""

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from gitdocs.core.errors import AuthError, JiraError

logger = logging.getLogger(__name__)


class JiraClient:
    """
    Low-level HTTP client for Jira Cloud REST API.

    Uses Basic auth with API token and provides retry/backoff handling.
    """

    API_VERSION = "3"
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
        Initialize Jira client.

        Args:
            base_url: Jira Cloud base URL (e.g., https://company.atlassian.net)
            email: Jira account email
            api_token: Jira API token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/rest/api/{self.API_VERSION}"
        self.agile_api_base = f"{self.base_url}/rest/agile/1.0"

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
            # Note: async close should be done in async context
            pass

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 401:
            raise AuthError(
                "Jira authentication failed. Check your email and API token.",
                details={"status_code": 401},
            )

        if response.status_code == 403:
            raise AuthError(
                "Jira access forbidden. Check your permissions.",
                details={"status_code": 403},
            )

        if response.status_code == 404:
            raise JiraError(
                "Resource not found",
                status_code=404,
                response_body=response.text,
            )

        if response.status_code == 429:
            raise JiraError(
                "Rate limited by Jira. Please wait and retry.",
                status_code=429,
            )

        if response.status_code >= 400:
            raise JiraError(
                f"Jira API error: {response.status_code}",
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
        """
        Make a GET request to Jira API.

        Args:
            endpoint: API endpoint (relative to API base)
            params: Query parameters

        Returns:
            JSON response as dict
        """
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
        """
        Make a POST request to Jira API.

        Args:
            endpoint: API endpoint
            data: JSON body
            params: Query parameters

        Returns:
            JSON response as dict
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        logger.debug(f"POST {url} data={data}")

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
        """Make a PUT request to Jira API."""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        logger.debug(f"PUT {url} data={data}")

        response = self._client.put(url, json=data)
        return self._handle_response(response)

    def get_agile(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to Jira Agile API."""
        url = f"{self.agile_api_base}/{endpoint.lstrip('/')}"
        logger.debug(f"GET (agile) {url} params={params}")

        response = self._client.get(url, params=params)
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
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Async POST request."""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        response = await self.async_client.post(url, json=data, params=params)
        return self._handle_response(response)
