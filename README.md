# pyemoncms
python library for emoncms API

rely on [aiohttp](https://github.com/aio-libs/aiohttp)

to install : `pip3 install pyemoncms`

how to use :

```
import logging
import asyncio
from pyemoncms import EmoncmsClient

key = "your32bitsAPIkey"
url = "http://url:8081"
client = EmoncmsClient(url, key, request_timeout=1)
client.logger.setLevel("DEBUG")

async def get_path(path):
    print(await client.async_request(path))

async def list_feeds():
    print(await client.async_list_feeds())
    
async def get_feed_fields(feed_id):
    print(await client.async_get_feed_fields(feed_id))


loop = asyncio.get_event_loop()
loop.create_task(get_path("feed/list.json"))
loop.create_task(get_path("/user/getuuid.json"))
loop.create_task(list_feeds())
loop.create_task(get_feed_fields(1))
try:
    loop.run_forever()
except Exception:
    client.logger.error("something happened")
finally:
    loop.run_until_complete(client.close())
    loop.close()
```

even simpler with a context manager :

```
async def main():
    """fetches somes datas in emoncms"""
    async with EmoncmsClient(url, key, request_timeout=1) as client:
        client.logger.setLevel("DEBUG")
        print(await client.async_get_uuid())
        print(await client.async_list_feeds())
        print(await client.async_get_feed_fields(1))

if __name__ == "__main__":
    asyncio.run(main())
```
