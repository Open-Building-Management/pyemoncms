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
import logging
from typing import Any

import aiohttp

HTTP_STATUS = {
    400: "invalid request",
    401: "unauthorized access",
    404: "Not found",
    406: "URI not acceptable",
}

MESSAGE_KEY = "message"
SUCCESS_KEY = "success"

logging.basicConfig()


class EmoncmsClient:
    """Emoncms client."""

    logger = logging.getLogger(__name__)

    def __init__(self, url: str, api_key: str, request_timeout: int = 20) -> None:
        """Initialize the client."""
        self.logger.info("Initializing Emoncms client")
        self.api_key = api_key
        self.url = url
        self.request_timeout = request_timeout

    async def async_request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Request emoncms server."""
        message = f"requesting emoncms on {path}"
        self.logger.debug(message)
        data = {SUCCESS_KEY: False, MESSAGE_KEY: None}
        if not params:
            params = {"apikey": self.api_key}
        async with aiohttp.ClientSession(self.url) as session:
            try:
                response = await session.get(
                    path, timeout=self.request_timeout, params=params
                )
            except aiohttp.ClientError as er:
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
                try:
                    if MESSAGE_KEY in json_response:
                        data[MESSAGE_KEY] = json_response[MESSAGE_KEY]
                except TypeError as er:
                    message = f"type error : {er}"
                    self.logger.error(message)
                    data[SUCCESS_KEY] = False
            else:
                message = f"error {response.status}"
                if response.status in HTTP_STATUS:
                    message = f"{message} {HTTP_STATUS[response.status]}"
                data[MESSAGE_KEY] = message
                self.logger.error(message)
        return data

    async def async_list_feeds(self) -> list[dict[str, Any]] | None:
        """Request emoncms feeds list.

        return a uuid per feed if available
        """
        uuid_data = await self.async_request("/user/getuuid.json")
        feed_data = await self.async_request("/feed/list.json")
        if feed_data[SUCCESS_KEY] and uuid_data[SUCCESS_KEY]:
            for feed in feed_data[MESSAGE_KEY]:
                feed["uuid"] = f"{uuid_data[MESSAGE_KEY]}_{feed['id']}"
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
