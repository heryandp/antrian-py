import asyncio
import websockets
import json
import logging
import signal
import sys
import platform

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('WebSocketServer')

class WebSocketServer:
    def __init__(self):
        self.clients = set()
        self.lock = asyncio.Lock()
        self.running = True

    async def register(self, websocket):
        async with self.lock:
            self.clients.add(websocket)
            logger.info(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket):
        async with self.lock:
            if websocket in self.clients:
                self.clients.remove(websocket)
                logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, message):
        if not self.clients:
            logger.debug("No clients connected, message not broadcast")
            return

        async with self.lock:
            disconnected = set()
            for client in self.clients:
                try:
                    await client.send(message)
                    logger.debug(f"Message broadcast successfully")
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"Client connection closed")
                    disconnected.add(client)
                except Exception as e:
                    logger.error(f"Error broadcasting: {str(e)}")
                    disconnected.add(client)
            
            # Remove disconnected clients
            for client in disconnected:
                await self.unregister(client)

    async def handler(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                if not self.running:
                    break
                try:
                    data = json.loads(message)
                    logger.debug(f"Received message: {data}")
                    await self.broadcast(message)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {str(e)}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed normally")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
        finally:
            await self.unregister(websocket)

    def stop(self):
        self.running = False
        logger.info("Server stopping...")

async def shutdown(server, ws_server):
    """Cleanup function for graceful shutdown"""
    server.stop()
    if ws_server:
        ws_server.close()
        await ws_server.wait_closed()
    logger.info("Server shutdown complete")

async def main():
    server = WebSocketServer()
    
    # Create the WebSocket server
    ws_server = await websockets.serve(server.handler, "localhost", 8765)
    logger.info("WebSocket server started on ws://localhost:8765")

    # Setup shutdown handler
    if platform.system() == 'Windows':
        # Windows specific shutdown handling
        def handle_shutdown(*args):
            asyncio.create_task(shutdown(server, ws_server))
            sys.exit(0)
        
        try:
            import win32api
            win32api.SetConsoleCtrlHandler(handle_shutdown, True)
        except ImportError:
            logger.warning("win32api not available, graceful shutdown may not work")
    else:
        # Unix-like systems
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, 
                lambda: asyncio.create_task(shutdown(server, ws_server)))

    try:
        # Keep the server running
        await asyncio.Future()  # run forever
    except (KeyboardInterrupt, SystemExit):
        await shutdown(server, ws_server)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
