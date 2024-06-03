import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import stomp
import time
import threading


class ActiveMQListener(stomp.ConnectionListener):
    def __init__(self, table, save_var, directory_label):
        self.table = table
        self.save_var = save_var
        self.directory_label = directory_label
        self.messages = []

    def on_message(self, headers, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        self.table.insert("", "end", values=(timestamp, message))
        if self.save_var.get():
            directory = self.directory_label.cget("text")
            if directory:
                with open(f"{directory}/messages.txt", "a") as file:
                    file.write(f"{timestamp}: {message}\n")
        self.messages.append((timestamp, message))


class ActiveMQTool:
    def __init__(self, root):
        self.root = root
        self.root.title("北向开发工具")

        self.main_frame = tk.Frame(root)
        self.main_frame.pack(pady=20)

        self.title_label = tk.Label(self.main_frame, text="北向开发工具", font=("Arial", 16))
        self.title_label.pack(pady=10)

        self.xml_test_button = tk.Button(self.main_frame, text="XMLTest工具", command=self.open_xml_test)
        self.xml_test_button.pack(pady=5)

        self.websocket_button = tk.Button(self.main_frame, text="WebSocket工具")
        self.websocket_button.pack(pady=5)

    def open_xml_test(self):
        self.main_frame.pack_forget()
        self.xml_test_frame = tk.Frame(self.root)
        self.xml_test_frame.pack(pady=20)

        self.ip_label = tk.Label(self.xml_test_frame, text="服务器IP:")
        self.ip_label.grid(row=0, column=0, padx=5, pady=5)
        self.ip_entry = tk.Entry(self.xml_test_frame)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)

        self.port_label = tk.Label(self.xml_test_frame, text="端口:")
        self.port_label.grid(row=1, column=0, padx=5, pady=5)
        self.port_entry = tk.Entry(self.xml_test_frame)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)

        self.try_button = tk.Button(self.xml_test_frame, text="Try", command=self.try_connection)
        self.try_button.grid(row=2, column=0, padx=5, pady=5)
        self.connect_button = tk.Button(self.xml_test_frame, text="Connect", state="disabled",
                                        command=self.connect_to_server)
        self.connect_button.grid(row=2, column=1, padx=5, pady=5)

    def try_connection(self):
        ip = self.ip_entry.get()
        port = self.port_entry.get()
        try:
            conn = stomp.Connection([(ip, int(port))])
            conn.start()
            conn.connect(wait=True)
            conn.disconnect()
            messagebox.showinfo("Connection Test", "Connection Successful!")
            self.connect_button.config(state="normal")
        except Exception as e:
            messagebox.showerror("Connection Test", f"Connection Failed: {e}")

    def connect_to_server(self):
        ip = self.ip_entry.get()
        port = self.port_entry.get()
        self.conn = stomp.Connection([(ip, int(port))])
        self.conn.set_listener("", ActiveMQListener(self.message_table, self.save_var, self.directory_label))
        self.conn.start()
        self.conn.connect(wait=True)
        self.conn.subscribe(destination="/queue/test", id=1, ack="auto")
        self.xml_test_frame.pack_forget()
        self.open_message_receiver()

    def open_message_receiver(self):
        self.receiver_frame = tk.Frame(self.root)
        self.receiver_frame.pack(pady=20)

        self.save_var = tk.BooleanVar()

        self.save_button = tk.Checkbutton(self.receiver_frame, text="保存消息到本地", variable=self.save_var)
        self.save_button.grid(row=0, column=0, padx=5, pady=5)

        self.directory_button = tk.Button(self.receiver_frame, text="选择保存目录", command=self.select_directory,
                                          state="disabled")
        self.directory_button.grid(row=0, column=1, padx=5, pady=5)

        self.save_var.trace("w", self.toggle_directory_button)

        self.directory_label = tk.Label(self.receiver_frame, text="", wraplength=200)
        self.directory_label.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        self.message_frame = tk.Frame(self.receiver_frame)
        self.message_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.message_table = ttk.Treeview(self.message_frame, columns=("timestamp", "message"), show="headings")
        self.message_table.heading("timestamp", text="时间戳")
        self.message_table.heading("message", text="消息")
        self.message_table.pack()

    def toggle_directory_button(self, *args):
        if self.save_var.get():
            self.directory_button.config(state="normal")
        else:
            self.directory_button.config(state="disabled")

    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directory_label.config(text=directory)


if __name__ == "__main__":
    root = tk.Tk()
    app = ActiveMQTool(root)
    root.mainloop()
