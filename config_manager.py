import tkinter as tk
from tkinter import ttk, messagebox
import string
from config import load_config, save_config

class ConfigManager:
    def __init__(self, root):
        self.window = tk.Toplevel(root)
        self.window.title('Pengaturan Sistem Antrian')
        self.window.geometry('600x400')
        
        # Load current config
        self.config = load_config()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Office Settings Tab
        office_frame = ttk.Frame(notebook)
        notebook.add(office_frame, text='Kantor')
        
        ttk.Label(office_frame, text="Nama Kantor/Unit:").pack(pady=5)
        self.office_name = tk.StringVar(value=self.config['office_name'])
        ttk.Entry(office_frame, textvariable=self.office_name, width=50).pack(pady=5)
        
        # Counter Settings Tab
        counter_frame = ttk.Frame(notebook)
        notebook.add(counter_frame, text='Counter')
        
        # Counter configuration
        ttk.Label(counter_frame, text="Konfigurasi Counter:").pack(pady=5)
        counter_config_frame = ttk.Frame(counter_frame)
        counter_config_frame.pack(fill='x', padx=10)
        
        self.counter_vars = {}
        row = 0
        for letter in string.ascii_uppercase[:8]:  # Limit to A-H
            ttk.Label(counter_config_frame, text=f"Counter {letter}:").grid(row=row, column=0, pady=2)
            var = tk.StringVar(value=str(self.config['counters'].get(letter, 0)))
            spinbox = ttk.Spinbox(counter_config_frame, from_=0, to=9, width=5, textvariable=var)
            spinbox.grid(row=row, column=1, padx=5, pady=2)
            self.counter_vars[letter] = var
            row += 1
        
        # Service Settings Tab
        service_frame = ttk.Frame(notebook)
        notebook.add(service_frame, text='Layanan')
        
        # Service list
        self.service_list = []
        ttk.Label(service_frame, text="Daftar Layanan:").pack(pady=5)
        
        services_frame = ttk.Frame(service_frame)
        services_frame.pack(fill='both', expand=True, padx=10)
        
        # Add service button
        ttk.Button(service_frame, text="Tambah Layanan", 
                  command=self.add_service).pack(pady=5)
        
        # Load existing services
        for service in self.config['services']:
            self.add_service_row(services_frame, service)
        
        # Save button
        ttk.Button(self.window, text="Simpan Pengaturan", 
                  command=self.save_settings).pack(pady=10)
    
    def add_service(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Tambah Layanan")
        
        ttk.Label(dialog, text="Kode (A-Z):").pack(pady=5)
        code_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=code_var).pack(pady=5)
        
        ttk.Label(dialog, text="Nama Layanan:").pack(pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var).pack(pady=5)
        
        ttk.Label(dialog, text="Deskripsi:").pack(pady=5)
        desc_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=desc_var).pack(pady=5)
        
        def save_service():
            code = code_var.get().upper()
            if len(code) != 1 or not code.isalpha():
                messagebox.showerror("Error", "Kode harus satu huruf (A-Z)")
                return
            
            service = {
                "code": code,
                "name": name_var.get(),
                "description": desc_var.get()
            }
            self.config['services'].append(service)
            self.add_service_row(dialog.master, service)
            dialog.destroy()
        
        ttk.Button(dialog, text="Simpan", command=save_service).pack(pady=10)
    
    def add_service_row(self, parent, service):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=2)
        
        ttk.Label(frame, text=f"[{service['code']}]").pack(side='left', padx=5)
        ttk.Label(frame, text=service['name']).pack(side='left', padx=5)
        ttk.Label(frame, text=service['description']).pack(side='left', padx=5)
        
        def delete_service():
            self.config['services'].remove(service)
            frame.destroy()
        
        ttk.Button(frame, text="Hapus", command=delete_service).pack(side='right', padx=5)
    
    def save_settings(self):
        # Update office name
        self.config['office_name'] = self.office_name.get()
        
        # Update counters
        new_counters = {}
        for letter, var in self.counter_vars.items():
            count = int(var.get())
            if count > 0:
                new_counters[letter] = count
        self.config['counters'] = new_counters
        
        # Save config
        save_config(self.config)
        messagebox.showinfo("Sukses", "Pengaturan berhasil disimpan!")
        self.window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigManager(root)
    root.mainloop()
