"""Tests for async_request method."""

import os
import sys

import pytest
from aiohttp import web

root_path = os.getcwd()
sys.path.insert(0, root_path)
from pyemoncms.emoncms_client import (  # pylint: disable=E0401,C0413
    EmoncmsAuthError,
    EmoncmsClient,
    EmoncmsConnectionError,
    EmoncmsError,
)

API_KEY = "123"

FEED = {
    "id":"1",
    "userid":"1",
    "name":"Cellule_Tcircuit",
    "tag":" sofrel_circuit_Cellule",
    "public":"0",
    "size":"35811340",
    "engine":"5",
    "processList":"",
    "unit":"",
    "time":1665509570,
    "value":17.690000534058
}

FEEDS = [ FEED ]


async def feed_list_route(request):
    """Emoncms feed list route."""
    if "apikey" not in request.query:
        return web.json_response(False)
    if request.query["apikey"] != API_KEY:
        raise web.HTTPUnauthorized(text="Invalid API key")
    return web.json_response(FEEDS)


async def input_post_route(request):
    """Emoncms input post route."""
    if request.query["apikey"] == "500":
        raise web.HTTPInternalServerError(text="boom")
    if request.query["apikey"] != API_KEY:
        raise web.HTTPUnauthorized(text="Invalid API key")
    return web.Response(text="ok")


def create_feed_api():
    """Emoncms server."""
    app = web.Application()
    app.router.add_route("GET", "/feed/list.json", feed_list_route)
    app.router.add_route("GET", "/user/getuuid.json", feed_list_route)
    app.router.add_route("POST", "/input/post", input_post_route)
    return app

async def test_response_ok(aiohttp_server):
    """Test correct response."""
    await aiohttp_server(create_feed_api(), port=8080)
    client = EmoncmsClient("http://127.0.0.1:8080", API_KEY)
    datas = await client.async_request("/feed/list.json")
    assert FEEDS == datas["message"]

async def test_no_api_auth(aiohttp_server):
    """Test incorrect API key."""
    await aiohttp_server(create_feed_api(), port=8080)
    client = EmoncmsClient("http://127.0.0.1:8080", "666")
    datas = await client.async_request("/feed/list.json")
    assert not datas["success"]
    assert "401" in datas["message"]

async def test_timeout():
    """Test when IP does not exist."""
    client = EmoncmsClient("http://192.16.1.32:8080", API_KEY, request_timeout=1)
    datas = await client.async_request("/feed/list.json")
    assert not datas["success"]
    assert "time out" in datas["message"]

async def test_client_error():
    """Test when IP exists but client not running."""
    client = EmoncmsClient("http://127.0.0.1:8087", API_KEY)
    datas = await client.async_request("/feed/list.json")
    assert not datas["success"]
    assert "client error" in datas["message"]

async def test_raise_auth_error(aiohttp_server):
    """Test incorrect API key raises with raise_errors."""
    await aiohttp_server(create_feed_api(), port=8080)
    client = EmoncmsClient("http://127.0.0.1:8080", "666", raise_errors=True)
    with pytest.raises(EmoncmsAuthError):
        await client.async_list_feeds()
    with pytest.raises(EmoncmsAuthError):
        await client.async_get_uuid()
    await client.close()

async def test_raise_timeout():
    """Test timeout raises with raise_errors."""
    client = EmoncmsClient(
        "http://192.16.1.32:8080", API_KEY, request_timeout=1, raise_errors=True
    )
    with pytest.raises(EmoncmsConnectionError):
        await client.async_request("/feed/list.json")
    await client.close()

async def test_raise_client_error(caplog):
    """Test refused connection raises with raise_errors, without error logs."""
    client = EmoncmsClient("http://127.0.0.1:8087", API_KEY, raise_errors=True)
    with pytest.raises(EmoncmsConnectionError):
        await client.async_request("/feed/list.json")
    with pytest.raises(EmoncmsConnectionError):
        await client.async_input_post({"a": 1})
    await client.close()
    assert not [r for r in caplog.records if r.levelname == "ERROR"]

async def test_input_post(aiohttp_server):
    """Test input post success and errors."""
    await aiohttp_server(create_feed_api(), port=8080)
    url = "http://127.0.0.1:8080"
    async with EmoncmsClient(url, API_KEY, raise_errors=True) as client:
        assert await client.async_input_post({"a": 1})
        with pytest.raises(EmoncmsAuthError):
            await client.async_input_post({"a": 1}, apikey="666")
        with pytest.raises(EmoncmsError):
            await client.async_input_post({"a": 1}, apikey="500")
    async with EmoncmsClient(url, API_KEY) as client:
        with pytest.raises(RuntimeError):
            await client.async_input_post({"a": 1}, apikey="666")
