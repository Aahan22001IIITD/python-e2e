import asyncio

async def price_generator():
    for price in [100.1 , 100.2 , 100]:
        yield price
        await asyncio.sleep(0.01)

async def consume():
    async for price in price_generator():
        print (price)

asyncio.run(consume())