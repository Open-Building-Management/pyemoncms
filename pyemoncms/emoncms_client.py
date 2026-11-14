"""Emoncms client.

emoncms feed module :
an inexisting json route responds by {success: false, message : "Feed does not exist"}
examples of inexisting json routes :
- feed/aget.json?id=200 if there is no feed number 200
- feed/basket.json 
the feed/list.json always returns an array of json objects, which can be empty if there is no feed

emoncms user module
an inexisting json route responds by false which is not a json object
so there is a type error if you search for a key in the response
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
from typing import Any, Dict, TypeVar, Optional, cast

from aiohttp import ClientError, ClientSession, ClientTimeout

HTTP_STATUS = {
    400: "invalid request",
    401: "unauthorized access",
    404: "Not found",
    406: "URI not acceptable",
}

MESSAGE_KEY = "message"
SUCCESS_KEY = "success"

Self = TypeVar("Self", bound="EmoncmsClient")


class EmoncmsError(Exception):
    """Generic emoncms error."""


class EmoncmsAuthError(EmoncmsError):
    """Invalid API key (HTTP 401)."""


class EmoncmsConnectionError(EmoncmsError):
    """Emoncms server unreachable or timed out."""


@dataclass
class EmoncmsClient:
    """Emoncms client."""

    url: str = ""
    api_key: str | None = None
    request_timeout: int = 20
    session: ClientSession | None = None
    _close_session: bool = False
    raise_errors: bool = False
    logger = logging.getLogger(__name__)

    async def async_request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Request emoncms server."""
        message = f"requesting emoncms on {path}"
        self.logger.debug(message)
        data: dict[str, Any] = {SUCCESS_KEY: False, MESSAGE_KEY: None}
        if not params:
            params = {"apikey": self.api_key}
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True
        path = path.lstrip('/')
        url= f'{self.url}/{path}'
        try:
            response = await self.session.get(
                url, timeout=ClientTimeout(total=self.request_timeout), params=params
            )
            if response.status == 200:
                json_response = await response.json()
        except ClientError as er:
            message = f"client error : {er}"
            data[MESSAGE_KEY] = message
            self._log_error(message)
            if self.raise_errors:
                raise EmoncmsConnectionError(message) from er
            return data
        except asyncio.TimeoutError as er:
            message = "time out error"
            data[MESSAGE_KEY] = message
            self._log_error(message)
            if self.raise_errors:
                raise EmoncmsConnectionError(message) from er
            return data
        if response.status == 200:
            data[SUCCESS_KEY] = True
            data[MESSAGE_KEY] = json_response
        else:
            message = f"error {response.status}"
            if response.status in HTTP_STATUS:
                message = f"{message} {HTTP_STATUS[response.status]}"
            data[MESSAGE_KEY] = message
            self._log_error(message)
            self._raise_for_status(response.status, message)
        return data

    def _log_error(self, message: str) -> None:
        """Log at debug when raising, the caller decides how to report."""
        self.logger.log(logging.DEBUG if self.raise_errors else logging.ERROR, message)

    def _raise_for_status(self, status: int, message: str) -> None:
        """Raise the matching exception when raise_errors is enabled."""
        if not self.raise_errors:
            return
        if status == 401:
            raise EmoncmsAuthError(message)
        raise EmoncmsError(message)

    async def async_input_post(
        self,
        data: Dict[str, Any],
        node: Optional[str] = None,
        time: Optional[int] = None,
        apikey: Optional[str] = None,
    ) -> bool:
        """Async post data to an emoncms input/node."""
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        endpoint = f"{self.url.rstrip('/')}/input/post"
        json_string = json.dumps(data)

        effective_key = apikey if apikey is not None else self.api_key
        if not effective_key:
            raise ValueError("API key must be provided.")

        params = {"apikey": effective_key, "fulljson": json_string}
        if node:
            params["node"] = node
        if time is not None:
            params["time"] = str(time)

        try:
            async with self.session.post(
                endpoint, params=params, timeout=ClientTimeout(total=self.request_timeout)
            ) as resp:
                text = await resp.text()
                status = resp.status
        except (ClientError, asyncio.TimeoutError) as er:
            if self.raise_errors:
                raise EmoncmsConnectionError(f"POST failed : {er!r}") from er
            raise
        if status != 200:
            message = f"POST failed ({status}): {text}"
            self._raise_for_status(status, message)
            raise RuntimeError(message)
        return True

    async def async_get_uuid(self) -> str | None:
        """Return the unique identifier or None.
        
        first uuid version of emoncms is 11.5.7
        """
        result = await self.async_request('/user/getuuid.json')
        if result[SUCCESS_KEY]:
            json_response = result[MESSAGE_KEY]
            if json_response is False:
                return None
            if json_response[SUCCESS_KEY]:
                return cast(str, json_response[MESSAGE_KEY])
            message = json_response[MESSAGE_KEY]
            message = f"{message} : {self.url}"
            self.logger.debug(message)
        return None

    async def async_list_feeds(self) -> list[dict[str, Any]] | None:
        """Request emoncms feeds list."""
        feed_data = await self.async_request("/feed/list.json")
        if feed_data[SUCCESS_KEY]:
            return cast(list[dict[str, Any]], feed_data[MESSAGE_KEY])
        return None

    async def async_get_feed_fields(self, feed_id: int) -> list[Any] | None:
        """Get all fields for a single feed."""
        params = {"apikey": self.api_key, "id": feed_id}
        feed_data = await self.async_request("/feed/aget.json", params=params)
        if feed_data[SUCCESS_KEY]:
            return cast(list[Any], feed_data[MESSAGE_KEY])
        return None

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self: Self) -> Self:
        """Async enter for context manager."""
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit for content manager."""
        await self.close()
