import tkinter as tk
from tkinter import ttk
import asyncio
import websockets
import json
from threading import Thread
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Display')

class CounterDisplay(tk.Frame):
    def __init__(self, parent, counter_name=""):
        super().__init__(parent)
        
        # Counter name
        ttk.Label(self, text=counter_name, 
                             font=('Helvetica', 24)).pack(pady=5)
        
        # Number display
        self.number_var = tk.StringVar(value="0")
        ttk.Label(self, textvariable=self.number_var,
                             font=('Helvetica', 72)).pack(pady=10)
        
        # Visual separator
        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=10)
        
    def update_number(self, number):
        self.number_var.set(str(number))

class QueueDisplay:
    def __init__(self, root):
        self.root = root
        self.root.title('Queue Display')
        
        # Make it fullscreen
        self.root.attributes('-fullscreen', False)
        self.root.bind('<F11>', self.toggle_fullscreen)
        self.root.bind('<Escape>', self.end_fullscreen)

        # Main container
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header
        header_frame = ttk.Frame(self.main_container)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Title
        ttk.Label(header_frame, text="SISTEM ANTRIAN", 
                 font=('Helvetica', 36, 'bold')).pack(side=tk.LEFT)
        
        # Connection status
        self.status_var = tk.StringVar(value="Menghubungkan...")
        ttk.Label(header_frame, textvariable=self.status_var,
                 font=('Helvetica', 12)).pack(side=tk.RIGHT, padx=10)

        # Grid for counter displays
        self.grid_frame = ttk.Frame(self.main_container)
        self.grid_frame.pack(fill=tk.BOTH, expand=True)

        # Dictionary to store counter frames
        self.counter_frames = {}

        # Start websocket connection
        self.ws_thread = Thread(target=self.start_websocket_client, daemon=True)
        self.ws_thread.start()

    def toggle_fullscreen(self, event=None):
        self.root.attributes('-fullscreen', not self.root.attributes('-fullscreen'))

    def end_fullscreen(self, event=None):
        self.root.attributes('-fullscreen', False)

    def start_websocket_client(self):
        asyncio.run(self.websocket_client())

    async def websocket_client(self):
        uri = "ws://localhost:8765"
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    logger.info("Connected to WebSocket server")
                    self.status_var.set("Terhubung")
                    
                    while True:
                        try:
                            message = await websocket.recv()
                            logger.debug(f"Received message: {message}")
                            data = json.loads(message)
                            
                            # Update display in the main thread
                            self.root.after(0, self.update_display, 
                                          data['counter_id'], 
                                          data['number'],
                                          data.get('counter_name', f"Counter {data['counter_id']}"))
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON received: {e}")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            break
                            
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self.status_var.set("Terputus - Mencoba menghubungkan kembali...")
                await asyncio.sleep(5)  # Wait before reconnecting

    def update_display(self, counter_id, number, counter_name):
        try:
            if counter_id not in self.counter_frames:
                self.create_counter_display(counter_id, counter_name)
            
            counter_frame = self.counter_frames[counter_id]
            counter_frame['number_var'].set(str(number))
            
            # Update queue stats
            from database import get_queue_stats
            service_code = counter_name.split(' ')[-1][0]  # Get first letter of counter name
            total, next_number = get_queue_stats(service_code)
            
            counter_frame['total_var'].set(f"Total: {total}")
            counter_frame['next_var'].set(f"Berikutnya: {next_number or '-'}")
            
            logger.debug(f"Updated display for counter {counter_id} with number {number}")
        except Exception as e:
            logger.error(f"Error updating display: {e}")

    def create_counter_display(self, counter_id, counter_name):
        try:
            if counter_id in self.counter_frames:
                return

            # Calculate grid position
            num_counters = len(self.counter_frames)
            row = num_counters // 2
            col = num_counters % 2

            # Create counter frame
            frame = ttk.LabelFrame(self.grid_frame, text=counter_name)
            frame.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')

            # Configure grid weights
            self.grid_frame.grid_columnconfigure(col, weight=1)
            self.grid_frame.grid_rowconfigure(row, weight=1)

            # Number display
            number_var = tk.StringVar(value="0")
            number_label = ttk.Label(frame, textvariable=number_var,
                                   font=('Helvetica', 72))
            number_label.pack(pady=10)
            
            # Queue stats
            stats_frame = ttk.Frame(frame)
            stats_frame.pack(fill='x', pady=5)
            
            total_var = tk.StringVar(value="Total: 0")
            next_var = tk.StringVar(value="Berikutnya: -")
            
            ttk.Label(stats_frame, textvariable=total_var,
                     font=('Helvetica', 12)).pack(side='left', padx=5)
            ttk.Label(stats_frame, textvariable=next_var,
                     font=('Helvetica', 12)).pack(side='right', padx=5)

            self.counter_frames[counter_id] = {
                'frame': frame,
                'number_var': number_var,
                'total_var': total_var,
                'next_var': next_var
            }
            logger.debug(f"Created new counter display for {counter_name}")
        except Exception as e:
            logger.error(f"Error creating counter display: {e}")

if __name__ == '__main__':
    root = tk.Tk()
    app = QueueDisplay(root)
    root.mainloop()
