import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
import asyncio
from database import create_connection, get_next_number, create_new_number
from config import load_config, get_office_name, get_service_list
from audio_manager import AudioManager
import os
from websocket_client import WebSocketClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TicketDisplay')

class TicketDisplay:
    def __init__(self, root):
        self.root = root
        self.root.title('Ambil Nomor Antrian')
        
        # Make it fullscreen
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        
        # Load config
        self.config = load_config()
        
        # Initialize WebSocket client
        self.ws_client = WebSocketClient()
        self.ws_client.start()
        
        # Main container
        main_container = ttk.Frame(self.root, padding="20")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        office_name = get_office_name()
        ttk.Label(header_frame, text=office_name, 
                 font=('Helvetica', 24, 'bold')).pack(side=tk.LEFT)
        
        # Services
        services_frame = ttk.Frame(main_container)
        services_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create buttons for each service
        row = 0
        col = 0
        for service in get_service_list():
            frame = ttk.LabelFrame(services_frame, text=service['name'])
            frame.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            
            ttk.Label(frame, text=service['description'],
                     wraplength=300).pack(pady=5)
            
            ttk.Button(frame, text="Ambil Nomor Antrian",
                      command=lambda s=service: self.take_number(s)).pack(pady=10)
            
            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1
        
        # Configure grid
        services_frame.grid_columnconfigure(0, weight=1)
        services_frame.grid_columnconfigure(1, weight=1)
        
        # Initialize audio manager
        audio_dir = os.path.join(os.path.dirname(__file__), 'audio')
        self.audio_manager = AudioManager(audio_dir)
    
    def take_number(self, service):
        number = None
        try:
            number = create_new_number(service['code'])
            if number:
                logger.info(f"Created new number: {number}")
                messagebox.showinfo("Nomor Antrian", f"Nomor antrian anda: {number}")
                
                # Send WebSocket notification
                message = {
                    'type': 'new_number',
                    'number': number,
                    'service': service['code']
                }
                asyncio.run(self.ws_client.send_message(message))
                
                # Play notification
                self.audio_manager.play_notification()
            else:
                logger.error("Failed to create new number")
                messagebox.showerror("Error", "Gagal mengambil nomor antrian")
        except Exception as e:
            logger.error(f"Error taking number: {e}")
            messagebox.showerror("Error", "Terjadi kesalahan sistem")

if __name__ == "__main__":
    root = tk.Tk()
    app = TicketDisplay(root)
    root.mainloop()
