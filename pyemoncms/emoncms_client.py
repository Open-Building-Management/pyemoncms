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

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, TypeVar

from aiohttp import ClientError, ClientSession

HTTP_STATUS = {
    400: "invalid request",
    401: "unauthorized access",
    404: "Not found",
    406: "URI not acceptable",
}

MESSAGE_KEY = "message"
SUCCESS_KEY = "success"

logging.basicConfig()

Self = TypeVar("Self", bound="EmoncmsClient")

@dataclass
class EmoncmsClient:
    """Emoncms client."""

    url: str = None
    api_key: str = None
    request_timeout: int = 20
    session: ClientSession | None = None
    _close_session: bool = False
    logger = logging.getLogger(__name__)

    async def async_request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Request emoncms server."""
        message = f"requesting emoncms on {path}"
        self.logger.debug(message)
        data = {SUCCESS_KEY: False, MESSAGE_KEY: None}
        if not params:
            params = {"apikey": self.api_key}
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True
        path = path.lstrip('/')
        url= f'{self.url}/{path}'
        try:
            response = await self.session.get(
                url, timeout=self.request_timeout, params=params
            )
        except ClientError as er:
            message = f"client error : {er}"
            data[MESSAGE_KEY] = message
            self.logger.error(message)
            return data
        except asyncio.TimeoutError:
            message = "time out error"
            data[MESSAGE_KEY] = message
            self.logger.error(message)
            return data
        if response.status == 200:
            data[SUCCESS_KEY] = True
            json_response = await response.json()
            data[MESSAGE_KEY] = json_response
        else:
            message = f"error {response.status}"
            if response.status in HTTP_STATUS:
                message = f"{message} {HTTP_STATUS[response.status]}"
            data[MESSAGE_KEY] = message
            self.logger.error(message)
        return data

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
                return json_response[MESSAGE_KEY]
            message = json_response[MESSAGE_KEY]
            message = f"{message} : {self.url}"
            self.logger.debug(message)
        return None

    async def async_list_feeds(self) -> list[dict[str, Any]] | None:
        """Request emoncms feeds list."""
        feed_data = await self.async_request("/feed/list.json")
        if feed_data[SUCCESS_KEY]:
            return feed_data[MESSAGE_KEY]
        return None

    async def async_get_feed_fields(self, feed_id: int) -> list[str, Any] | None:
        """Get all fields for a single feed."""
        params = {"apikey": self.api_key, "id": feed_id}
        feed_data = await self.async_request("/feed/aget.json", params=params)
        if feed_data[SUCCESS_KEY]:
            return feed_data[MESSAGE_KEY]
        return None

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter for context manager."""
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit for content manager."""
        await self.close()
