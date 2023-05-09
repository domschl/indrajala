import asyncio
import certifi
import ssl
import websockets

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations(certifi.where())
# ssl_context.load_verify_locations('/home/dsc/certs/nineveh.pem', 'home/dsc/certs/nineveh-key.pem' )

async def hello():
    uri = "wss://nineveh:23577"
    async with websockets.connect(
        uri, ssl=ssl_context
  ) as websocket:
        name = "Bla"
        await websocket.send(name)
        print(f"> {name}")
        greeting = await websocket.recv()
        print(f"< {greeting}")

asyncio.get_event_loop().run_until_complete(hello())
asyncio.get_event_loop().run_until_complete(hello())
asyncio.get_event_loop().run_until_complete(hello())
