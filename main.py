import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import asyncio
import websockets
import json
import threading
from datetime import datetime

class WebSocketTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WebSocket Tool")
        self.geometry("400x200")
        self.configure(bg='white')

        style = ttk.Style(self)
        style.configure('TLabel', background='white', foreground='#000000', font=('Arial', 12))
        style.configure('TEntry', font=('Arial', 12))
        style.configure('TButton', font=('Arial', 12), foreground='#000000', background='#ffffff', bordercolor='#000000', borderwidth=2)
        style.map('TButton', background=[('active', '#1abc9c'), ('disabled', '#d3d3d3')], foreground=[('disabled', '#a0a0a0')], bordercolor=[('disabled', '#a0a0a0')])
        style.configure('Treeview', font=('Arial', 12), rowheight=25, bordercolor='#000000')
        style.configure('Treeview.Heading', font=('Arial', 12, 'bold'))
        style.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])  # Add grid lines
        style.configure("Treeview", background="white", foreground="black", fieldbackground="white", bordercolor="#000000", borderwidth=1)
        style.map("Treeview", background=[('selected', '#1abc9c')], foreground=[('selected', 'black')])

        self.url_label = ttk.Label(self, text="WebSocket URL:")
        self.url_label.pack(pady=10)

        self.url_entry = ttk.Entry(self, width=50)
        self.url_entry.pack(pady=5)

        self.button_frame = tk.Frame(self, bg='white')
        self.button_frame.pack(pady=10)

        self.try_button = ttk.Button(self.button_frame, text="Try", command=self.try_connection)
        self.try_button.grid(row=0, column=0, padx=5)

        self.connect_button = ttk.Button(self.button_frame, text="Connect", state=tk.DISABLED, command=self.connect)
        self.connect_button.grid(row=0, column=1, padx=5)

        self.notifications = []
        self.websocket = None
        self.notification_window = None

    def try_connection(self):
        url = self.url_entry.get()
        asyncio.run(self.async_try_connection(url))

    async def async_try_connection(self, url):
        try:
            async with websockets.connect(url):
                messagebox.showinfo("Connection", "Successfully connected to the WebSocket server.")
                self.connect_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Connection", f"Failed to connect to the WebSocket server.\nError: {e}")

    def connect(self):
        url = self.url_entry.get()
        self.connect_button.config(state=tk.DISABLED)
        self.try_button.config(state=tk.DISABLED)
        self.url_entry.config(state=tk.DISABLED)
        self.notifications.clear()  # Clear previous notifications
        self.notification_id = 0  # Reset notification ID
        threading.Thread(target=self.async_connect, args=(url,)).start()

    def async_connect(self, url):
        asyncio.run(self.receive_notifications(url))

    async def receive_notifications(self, url):
        try:
            async with websockets.connect(url) as websocket:
                self.websocket = websocket
                self.open_notification_window()
                while True:
                    notification = await websocket.recv()
                    self.notifications.append(notification)
                    self.add_notification_to_table(notification)
        except Exception as e:
            messagebox.showerror("Connection", f"Disconnected from the WebSocket server.\nError: {e}")

    def open_notification_window(self):
        if self.notification_window:
            self.notification_window.destroy()

        self.notification_window = tk.Toplevel(self)
        self.notification_window.title("WebSocket Notifications")
        self.notification_window.geometry("800x500")
        self.notification_window.configure(bg='white')

        columns = ("ID", "Timestamp", "Notification")
        self.tree = ttk.Treeview(self.notification_window, columns=columns, show='headings')
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150 if col != "Notification" else 500)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree.bind('<Button-3>', self.show_context_menu)  # Show context menu on right click

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="View Details", command=self.show_notification_details)
        self.context_menu.add_command(label="Save", command=self.save_notification)

        self.save_button = ttk.Button(self.notification_window, text="Save", command=self.save_notification)
        self.save_button.pack(pady=10, side=tk.LEFT, padx=10)

        self.message_entry = ttk.Entry(self.notification_window, width=50)
        self.message_entry.pack(pady=10, side=tk.LEFT, padx=10)

        self.send_button = ttk.Button(self.notification_window, text="Send", command=self.send_message)
        self.send_button.pack(pady=10, side=tk.LEFT, padx=10)

        self.clear_button = ttk.Button(self.notification_window, text="Clear", command=self.clear_notifications)
        self.clear_button.pack(pady=10, side=tk.LEFT, padx=10)

    def add_notification_to_table(self, notification):
        notification_id = len(self.notifications)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.tree.insert("", "end", values=(notification_id + 1, timestamp, notification))

    def show_context_menu(self, event):
        selected_item = self.tree.identify_row(event.y)
        if selected_item:
            self.tree.selection_set(selected_item)
            self.context_menu.post(event.x_root, event.y_root)

    def show_notification_details(self):
        selected_item = self.tree.selection()
        if selected_item:
            notification = self.tree.item(selected_item, "values")[2]
            try:
                formatted_notification = json.dumps(json.loads(notification), indent=4)
            except json.JSONDecodeError:
                formatted_notification = notification
            messagebox.showinfo("Notification Details", formatted_notification)

    def save_notification(self):
        selected_item = self.tree.selection()
        if selected_item:
            notification = self.tree.item(selected_item, "values")[2]
            save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
            if save_path:
                with open(save_path, 'w') as file:
                    json.dump(json.loads(notification), file, indent=4)
                messagebox.showinfo("Save", "Notification saved successfully.")

    def clear_notifications(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.notifications.clear()
        self.notification_id = 0

    def send_message(self):
        message = self.message_entry.get()
        if message and self.websocket:
            asyncio.run(self.websocket.send(message))
            self.message_entry.delete(0, tk.END)

if __name__ == "__main__":
    app = WebSocketTool()
    app.mainloop()
