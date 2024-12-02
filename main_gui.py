import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
import asyncio
import os
from database import create_connection, get_next_number, init_database
from config import get_counter_list
from audio_manager import AudioManager
from websocket_client import WebSocketClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MainGUI')

class CounterManager(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Counter Management')
        self.geometry('400x500')

        # Counter list
        self.tree = ttk.Treeview(self, columns=('ID', 'Name', 'Description', 'Status'), show='headings')
        self.tree.heading('ID', text='ID')
        self.tree.heading('Name', text='Name')
        self.tree.heading('Description', text='Description')
        self.tree.heading('Status', text='Status')
        self.tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Add counter frame
        add_frame = ttk.LabelFrame(self, text='Add/Edit Counter')
        add_frame.pack(pady=10, padx=10, fill=tk.X)

        ttk.Label(add_frame, text='Name:').grid(row=0, column=0, pady=5, padx=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(add_frame, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(add_frame, text='Description:').grid(row=1, column=0, pady=5, padx=5)
        self.desc_var = tk.StringVar()
        self.desc_entry = ttk.Entry(add_frame, textvariable=self.desc_var)
        self.desc_entry.grid(row=1, column=1, pady=5, padx=5)

        btn_frame = ttk.Frame(add_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text='Add Counter', command=self.add_counter).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text='Update Counter', command=self.update_counter).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text='Toggle Status', command=self.toggle_status).pack(side=tk.LEFT, padx=5)

        self.load_counters()
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def load_counters(self):
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, description, is_active FROM counters')
        counters = cursor.fetchall()
        conn.close()

        for counter in counters:
            status = 'Active' if counter[3] else 'Inactive'
            self.tree.insert('', 'end', values=(counter[0], counter[1], counter[2], status))

    def on_select(self, event):
        selected_item = self.tree.selection()[0]
        values = self.tree.item(selected_item, 'values')
        self.name_var.set(values[1])
        self.desc_var.set(values[2])

    def add_counter(self):
        name = self.name_var.get()
        description = self.desc_var.get()
        if name:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO counters (name, description, is_active) VALUES (?, ?, 1)', (name, description))
            conn.commit()
            conn.close()
            self.tree.insert('', 'end', values=(cursor.lastrowid, name, description, 'Active'))

    def update_counter(self):
        selected_item = self.tree.selection()[0]
        counter_id = self.tree.item(selected_item, 'values')[0]
        name = self.name_var.get()
        description = self.desc_var.get()
        if name:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE counters SET name = ?, description = ? WHERE id = ?', (name, description, counter_id))
            conn.commit()
            conn.close()
            self.tree.item(selected_item, values=(counter_id, name, description, self.tree.item(selected_item, 'values')[3]))

    def toggle_status(self):
        if not self.tree.selection():
            messagebox.showwarning('Warning', 'No counter selected!')
            return
        selected_item = self.tree.selection()[0]
        counter_id = self.tree.item(selected_item, 'values')[0]
        current_status = self.tree.item(selected_item, 'values')[3]
        new_status = 'Inactive' if current_status == 'Active' else 'Active'
        is_active = 0 if current_status == 'Active' else 1
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE counters SET is_active = ? WHERE id = ?', (is_active, counter_id))
        conn.commit()
        conn.close()
        self.tree.item(selected_item, values=(counter_id, self.tree.item(selected_item, 'values')[1], self.tree.item(selected_item, 'values')[2], new_status))

class QueueApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Queue Management System')
        
        # Initialize database first
        try:
            init_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            messagebox.showerror("Error", "Gagal menginisialisasi database")
            raise
        
        # Load counter list
        try:
            self.counters = get_counter_list()
            if not self.counters:
                logger.warning("No active counters found")
                messagebox.showwarning("Warning", "Tidak ada loket aktif ditemukan")
            else:
                logger.info(f"Loaded {len(self.counters)} active counters")
        except Exception as e:
            logger.error(f"Failed to load counter list: {e}")
            messagebox.showerror("Error", "Gagal memuat daftar loket")
            raise
        
        # Initialize WebSocket client
        self.ws_client = WebSocketClient()
        self.ws_client.start()
        logger.info("WebSocket client initialized")
        
        # Initialize audio manager
        audio_dir = os.path.join(os.path.dirname(__file__), 'audio')
        self.audio_manager = AudioManager(audio_dir)
        
        self.setup_ui()
    
    def setup_ui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Counter selection
        ttk.Label(main_frame, text="Pilih Loket:").grid(row=0, column=0, padx=5, pady=5)
        
        self.counter_var = tk.StringVar()
        self.counter_select = ttk.Combobox(main_frame, textvariable=self.counter_var)
        
        # Create list of counter names for combobox
        counter_names = []
        for counter in self.counters:
            counter_names.append(counter[1])  # counter[1] is the name field
        
        self.counter_select['values'] = counter_names
        self.counter_select.grid(row=0, column=1, padx=5, pady=5)
        if counter_names:
            self.counter_select.set(counter_names[0])
        
        # Next number button
        next_btn = ttk.Button(main_frame, text="Nomor Berikutnya", command=self.next_number)
        next_btn.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Current number display
        self.current_number = tk.StringVar(value="---")
        ttk.Label(main_frame, text="Nomor Saat Ini:").grid(row=2, column=0, pady=5)
        ttk.Label(main_frame, textvariable=self.current_number, font=("Helvetica", 24)).grid(row=2, column=1, pady=5)
        
        # Counter management button
        manage_btn = ttk.Button(main_frame, text="Kelola Loket", command=self.open_counter_manager)
        manage_btn.grid(row=3, column=0, columnspan=2, pady=10)
    
    def next_number(self):
        """Handle next number button click"""
        try:
            current_counter = self.counter_var.get()
            if not current_counter:
                messagebox.showwarning("Peringatan", "Silakan pilih loket terlebih dahulu")
                return
            
            # Find counter ID from selected counter name
            counter_id = None
            for counter in self.counters:
                if counter[1] == current_counter:  # counter[1] is the name field
                    counter_id = counter[0]  # counter[0] is the id field
                    service_code = counter[2]  # counter[2] is the service_code field
                    break
            
            if counter_id is None:
                logger.error(f"Counter not found: {current_counter}")
                messagebox.showerror("Error", "Loket tidak ditemukan")
                return
            
            # Get next number
            next_number = get_next_number(counter_id)
            if next_number:
                self.current_number.set(next_number)
                
                # Prepare WebSocket message
                message = {
                    'type': 'call_number',
                    'counter_id': counter_id,
                    'number': next_number,
                    'counter_name': current_counter
                }
                
                # Send WebSocket message asynchronously
                asyncio.run(self.ws_client.send_message(json.dumps(message)))
                
                # Play audio
                self.audio_manager.play_notification()
                self.audio_manager.play_number(next_number)
            else:
                logger.warning("No waiting numbers available")
                self.current_number.set("---")
                messagebox.showinfo("Info", "Tidak ada antrian yang menunggu")
        
        except Exception as e:
            logger.error(f"Error in next_number: {e}")
            messagebox.showerror("Error", "Terjadi kesalahan sistem")
    
    def open_counter_manager(self):
        counter_manager = CounterManager(self.root)
        counter_manager.grab_set()

if __name__ == "__main__":
    try:
        # Set event loop policy for Windows
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        root = tk.Tk()
        app = QueueApp(root)
        root.protocol("WM_DELETE_WINDOW", lambda: root.destroy())
        root.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror("Error", "Aplikasi gagal dijalankan")
