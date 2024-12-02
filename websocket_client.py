import asyncio
import websockets
import json
import logging
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('WebSocketClient')

class WebSocketClient:
    def __init__(self):
        self.websocket = None
        self.connected = False
        self.reconnect_interval = 5  # seconds
        self.uri = "ws://localhost:8765"
        self.connection_thread = None
        self.message_handlers = []
        logger.debug("WebSocketClient initialized")
    
    def start(self):
        """Start WebSocket client in a separate thread"""
        logger.debug("Starting WebSocket client")
        if not self.connection_thread:
            self.connection_thread = Thread(target=self._run_client, daemon=True)
            self.connection_thread.start()
            logger.info("WebSocket client thread started")
    
    def _run_client(self):
        """Run the WebSocket client event loop"""
        logger.debug("Setting up client event loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while True:
            try:
                logger.debug("Attempting to connect to WebSocket server")
                loop.run_until_complete(self._connect_and_listen())
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
            
            # Wait before reconnecting
            logger.debug(f"Waiting {self.reconnect_interval} seconds before reconnecting")
            loop.run_until_complete(asyncio.sleep(self.reconnect_interval))
    
    async def _connect_and_listen(self):
        """Connect to WebSocket server and listen for messages"""
        try:
            logger.debug(f"Connecting to {self.uri}")
            async with websockets.connect(self.uri) as websocket:
                self.websocket = websocket
                self.connected = True
                logger.info("Successfully connected to WebSocket server")
                
                while True:
                    try:
                        message = await websocket.recv()
                        logger.debug(f"Received message: {message}")
                        await self._handle_message(message)
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket connection closed")
                        break
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")
        
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            self.connected = False
            self.websocket = None
            logger.info("WebSocket connection cleaned up")
    
    async def _handle_message(self, message):
        """Handle incoming messages"""
        try:
            data = json.loads(message)
            logger.debug(f"Processing message: {data}")
            for handler in self.message_handlers:
                await handler(data)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
    
    async def send_message(self, message):
        """Send a message to the WebSocket server"""
        if not self.connected or not self.websocket:
            logger.warning("Not connected to server, cannot send message")
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Message sent successfully: {message}")
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.connected = False
            self.websocket = None
            return False
    
    def add_message_handler(self, handler):
        """Add a message handler function"""
        self.message_handlers.append(handler)
        logger.debug(f"Added message handler, total handlers: {len(self.message_handlers)}")
    
    def remove_message_handler(self, handler):
        """Remove a message handler function"""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)
            logger.debug(f"Removed message handler, remaining handlers: {len(self.message_handlers)}")
