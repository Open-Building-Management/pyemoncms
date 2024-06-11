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
loop.create_task(get_path("/feed/list.json"))
loop.create_task(get_path("/user/getuuid.json"))
loop.create_task(list_feeds())
loop.create_task(get_feed_fields(1))
loop.run_forever()
```
