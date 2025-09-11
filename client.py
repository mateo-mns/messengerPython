import socket
import threading
import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk, Listbox, simpledialog
from datetime import datetime

# Configuración
HOST = "192.168.1.107"
PORT = 5000
FONT_FAMILY = "Arial"
BG_COLOR = "#34495e"
ACCENT_COLOR = "#3498db"
TEXT_COLOR = "white"

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Messenger Client")
        self.root.geometry("900x650")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(800, 600)
        
        # Variables
        self.cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.private_windows = {}
        self.connected = False
        self.nombre = ""
        self.clientes_conectados = []
        
        # Mostrar interfaz de login
        self.setup_login_interface()
        
    def setup_login_interface(self):
        """Interfaz para ingresar nombre de usuario"""
        self.login_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.login_frame.pack(expand=True, fill="both", padx=100, pady=100)
        
        # Logo/título
        title_frame = tk.Frame(self.login_frame, bg=BG_COLOR)
        title_frame.pack(pady=(0, 40))
        
        tk.Label(title_frame, text="💬", font=(FONT_FAMILY, 40), bg=BG_COLOR, fg="white").pack()
        tk.Label(title_frame, text="Messenger", font=(FONT_FAMILY, 24, "bold"), 
                bg=BG_COLOR, fg=ACCENT_COLOR).pack()
        tk.Label(title_frame, text="Conéctate y chatea con otros", font=(FONT_FAMILY, 12), 
                bg=BG_COLOR, fg="#bdc3c7").pack(pady=(5, 0))
        
        # Formulario de login
        form_frame = tk.Frame(self.login_frame, bg=BG_COLOR)
        form_frame.pack(pady=20)
        
        tk.Label(form_frame, text="Ingresa tu nombre:", font=(FONT_FAMILY, 12), 
                bg=BG_COLOR, fg="white", justify="left").grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        self.name_entry = tk.Entry(form_frame, font=(FONT_FAMILY, 14), width=25, bg="#ecf0f1", 
                                relief="flat", highlightthickness=1, highlightcolor=ACCENT_COLOR)
        self.name_entry.grid(row=1, column=0, ipady=8, pady=(0, 20))
        self.name_entry.bind("<Return>", lambda e: self.connect_to_server())
        self.name_entry.focus()
        
        self.connect_btn = tk.Button(form_frame, text="Conectar al Chat", 
                                font=(FONT_FAMILY, 12, "bold"), bg=ACCENT_COLOR, fg="white",
                                command=self.connect_to_server, width=20, height=2,
                                relief="flat", cursor="hand2")
        self.connect_btn.grid(row=2, column=0)
        
    def setup_chat_interface(self):
        """Configurar la interfaz de chat después del login"""
        # Destruir frame de login
        self.login_frame.destroy()
        
        # Frame principal con paned window para división
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=BG_COLOR, sashwidth=5)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame izquierdo (chat principal)
        left_frame = tk.Frame(main_paned, bg="#ecf0f1")
        main_paned.add(left_frame, width=600, minsize=400)
        
        # Frame derecho (lista de clientes)
        right_frame = tk.Frame(main_paned, bg=BG_COLOR, width=250)
        main_paned.add(right_frame, minsize=200)
        
        # Frame superior para información de conexión
        info_frame = tk.Frame(left_frame, bg="#ecf0f1")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(info_frame, text="Chat", font=(FONT_FAMILY, 12, "bold"), 
                bg="#ecf0f1", fg="#2c3e50").pack(side=tk.LEFT)
        
        self.status_label = tk.Label(info_frame, text=f"Conectado como {self.nombre}", 
                                    font=(FONT_FAMILY, 10), bg="#ecf0f1", fg="#7f8c8d")
        self.status_label.pack(side=tk.RIGHT)
        
        # Área de chat
        chat_frame = tk.Frame(left_frame, bg="white")
        chat_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chat_area = scrolledtext.ScrolledText(
            chat_frame, 
            wrap=tk.WORD, 
            state="disabled", 
            font=(FONT_FAMILY, 11),
            bg="white",
            fg="#2c3e50",
            padx=15,
            pady=15
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        
        # Configurar tags para diferentes tipos de mensajes
        self.chat_area.tag_config("error", foreground="#e74c3c")
        self.chat_area.tag_config("archivo", foreground="#3498db")
        self.chat_area.tag_config("privado", foreground="#9b59b6")
        self.chat_area.tag_config("sistema", foreground="#7f8c8d", font=(FONT_FAMILY, 10, "italic"))
        
        # Frame de entrada
        input_frame = tk.Frame(left_frame, bg="#bdc3c7")
        input_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.entry_msg = tk.Entry(input_frame, font=(FONT_FAMILY, 12), bg="white", 
                                 relief="flat", highlightthickness=1, highlightcolor=ACCENT_COLOR)
        self.entry_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5), pady=10)
        self.entry_msg.bind("<Return>", lambda e: self.enviar_mensaje())
        
        # Botones
        btn_frame = tk.Frame(input_frame, bg="#bdc3c7")
        btn_frame.pack(side=tk.RIGHT)
        
        self.btn_enviar = tk.Button(btn_frame, text="Enviar", 
                                   font=(FONT_FAMILY, 11, "bold"), bg="#2ecc71", fg="white",
                                   command=self.enviar_mensaje, relief="flat", cursor="hand2", width=8)
        self.btn_enviar.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_archivo = tk.Button(btn_frame, text="Archivo", 
                                    font=(FONT_FAMILY, 11), bg="#e67e22", fg="white",
                                    command=self.enviar_archivo, relief="flat", cursor="hand2")
        self.btn_archivo.pack(side=tk.LEFT)
        
        # Panel derecho - Lista de clientes conectados
        client_list_frame = tk.Frame(right_frame, bg=BG_COLOR)
        client_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(client_list_frame, text="Clientes Conectados", font=(FONT_FAMILY, 12, "bold"), 
                bg=BG_COLOR, fg="white").pack(pady=(0, 10))
        
        # Listbox para clientes conectados
        listbox_frame = tk.Frame(client_list_frame, bg=BG_COLOR)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        self.client_listbox = Listbox(listbox_frame, font=(FONT_FAMILY, 11), 
                                     bg="#2c3e50", fg="white", selectbackground=ACCENT_COLOR,
                                     relief="flat", highlightthickness=0)
        self.client_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar para la listbox
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.client_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.client_listbox.yview)
        
        # Botones de acción para clientes
        client_btn_frame = tk.Frame(client_list_frame, bg=BG_COLOR)
        client_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.btn_privado = tk.Button(client_btn_frame, text="Mensaje Privado", 
                                    font=(FONT_FAMILY, 10), bg="#9b59b6", fg="white",
                                    command=self.iniciar_privado_desde_lista, 
                                    relief="flat", cursor="hand2")
        self.btn_privado.pack(fill=tk.X, pady=(0, 5))
        
        # self.btn_archivo_privado = tk.Button(client_btn_frame, text="Enviar Archivo", 
        #                                     font=(FONT_FAMILY, 10), bg="#e67e22", fg="white",
        #                                     command=self.enviar_archivo_privado_desde_lista, 
        #                                     relief="flat", cursor="hand2")
        #self.btn_archivo_privado.pack(fill=tk.X)
        
        # Barra de estado
        status_frame = tk.Frame(self.root, bg="#2c3e50", height=25)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        self.status_text = tk.Label(status_frame, text="Conectado", font=(FONT_FAMILY, 9), 
                                   bg="#2c3e50", fg="white", anchor="w")
        self.status_text.pack(side=tk.LEFT, padx=10)
        
        # Iniciar hilo de escucha
        threading.Thread(target=self.escuchar_servidor, daemon=True).start()
        
        # Mostrar mensaje de bienvenida
        self.escribir_en_chat("Bienvenido al chat! Escribe un mensaje para comenzar.", "sistema")
    
    def actualizar_lista_clientes(self, clientes):
        """Actualizar la lista de clientes conectados"""
        self.clientes_conectados = clientes
        self.client_listbox.delete(0, tk.END)
        
        for cliente in clientes:
            if cliente != self.nombre:  # No mostrar nuestro propio nombre
                self.client_listbox.insert(tk.END, cliente)
    
    def iniciar_privado_desde_lista(self):
        """Iniciar chat privado desde la lista de clientes seleccionados"""
        seleccion = self.client_listbox.curselection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Por favor selecciona un cliente de la lista")
            return
            
        destino = self.client_listbox.get(seleccion[0])
        self.get_private_window(destino)
    
    # def enviar_archivo_privado_desde_lista(self):
    #     """Enviar archivo privado desde la lista de clientes seleccionados"""
    #     seleccion = self.client_listbox.curselection()
    #     if not seleccion:
    #         messagebox.showwarning("Selección requerida", "Por favor selecciona un cliente de la lista")
    #         return
            
    #     destino = self.client_listbox.get(seleccion[0])
    #     self.enviar_archivo_privado(destino)
    
    def connect_to_server(self):
        """Conectar al servidor"""
        self.nombre = self.name_entry.get().strip()
        if not self.nombre:
            messagebox.showerror("Error", "Por favor ingresa un nombre válido")
            return
            
        try:
            self.cliente.connect((HOST, PORT))
            self.cliente.sendall(b'N' + self.nombre.encode('utf-8'))
            
            # Actualizar UI
            self.connected = True
            self.root.title(f"Messenger client - {self.nombre}")
            self.setup_chat_interface()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar al servidor: {e}")
    
    def escribir_en_chat(self, texto, tipo="normal"):
        """Escribir texto en el área de chat con formato"""
        self.chat_area.config(state="normal")
        
        # Aplicar formato según el tipo
        if tipo == "error":
            self.chat_area.insert(tk.END, texto + "\n", "error")
        elif tipo == "archivo":
            self.chat_area.insert(tk.END, texto + "\n", "archivo")
        elif tipo == "privado":
            self.chat_area.insert(tk.END, texto + "\n", "privado")
        elif tipo == "sistema":
            self.chat_area.insert(tk.END, texto + "\n", "sistema")
        else:
            self.chat_area.insert(tk.END, texto + "\n")
        
        self.chat_area.yview(tk.END)
        self.chat_area.config(state="disabled")
    
    def get_private_window(self, destino):
        """Obtener o crear ventana de chat privado"""
        if destino in self.private_windows:
            window = self.private_windows[destino]['win']
            window.deiconify()  # Mostrar ventana si estaba minimizada
            window.focus_force()  # Dar foco a la ventana
            return self.private_windows[destino]

        win = tk.Toplevel(self.root)
        win.title(f"Chat privado con {destino}")
        win.geometry("500x400")
        win.configure(bg="#ecf0f1")
        win.minsize(400, 600)
        
        # Frame principal
        main_frame = tk.Frame(win, bg="#ecf0f1")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Encabezado
        header_frame = tk.Frame(main_frame, bg=ACCENT_COLOR, height=50)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text=f"Chat con {destino}", 
                font=(FONT_FAMILY, 12, "bold"), bg=ACCENT_COLOR, fg="white").pack(pady=15)
        
        # Área de chat
        txt = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            state="disabled", 
            font=(FONT_FAMILY, 10),
            bg="white",
            fg="#2c3e50",
            padx=10,
            pady=10
        )
        txt.pack(fill=tk.BOTH, expand=True)
        
        # Frame de entrada
        input_frame = tk.Frame(main_frame, bg="#bdc3c7", height=60)
        input_frame.pack(fill=tk.X, pady=(10, 0))
        input_frame.pack_propagate(False)
        
        entry = tk.Entry(input_frame, font=(FONT_FAMILY, 11), bg="white",
                       relief="flat", highlightthickness=1, highlightcolor=ACCENT_COLOR)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5), pady=10)
        entry.bind("<Return>", lambda e: self.enviar_privado(destino, entry))
        
        # Botones en ventana privada
        priv_btn_frame = tk.Frame(input_frame, bg="#bdc3c7")
        priv_btn_frame.pack(side=tk.RIGHT)
        
        btn = tk.Button(priv_btn_frame, text="Enviar", 
                       font=(FONT_FAMILY, 11, "bold"), bg="#2ecc71", fg="white",
                       command=lambda: self.enviar_privado(destino, entry), 
                       relief="flat", cursor="hand2", width=8)
        btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Botón para enviar archivo en chat privado
        btn_file = tk.Button(priv_btn_frame, text="Archivo", 
                            font=(FONT_FAMILY, 11), bg="#e67e22", fg="white",
                            command=lambda: self.enviar_archivo_privado(destino), 
                            relief="flat", cursor="hand2")
        btn_file.pack(side=tk.LEFT)

        def write_private_line(s):
            txt.config(state="normal")
            txt.insert(tk.END, s + "\n")
            txt.yview(tk.END)
            txt.config(state="disabled")

        self.private_windows[destino] = {
            'win': win, 
            'text': txt, 
            'entry': entry, 
            'write': write_private_line
        }
        
        # Configurar comportamiento al cerrar la ventana
        def on_closing_private():
            win.withdraw()  # Ocultar en lugar de destruir
        
        win.protocol("WM_DELETE_WINDOW", on_closing_private)
        
        return self.private_windows[destino]
    
    def escuchar_servidor(self):
        """Escuchar mensajes del servidor"""
        while self.connected:
            try:
                tipo_b = self.cliente.recv(1)
                if not tipo_b:
                    break
                tipo = tipo_b.decode('utf-8')

                if tipo == 'M':  # Mensaje público
                    data = self.cliente.recv(1024).decode('utf-8')
                    if not data:
                        break
                    self.escribir_en_chat(data)

                elif tipo == 'F':  # Archivo público
                    nombre_archivo = self.cliente.recv(256).decode('utf-8').strip()
                    tamaño = int.from_bytes(self.cliente.recv(8), 'big')
                    self.escribir_en_chat(f"[ARCHIVO] Recibiendo: {nombre_archivo} ({tamaño} bytes)", "archivo")
                    
                    if not os.path.exists("descargas"):
                        os.makedirs("descargas")
                    
                    ruta = os.path.join("descargas", nombre_archivo)
                    with open(ruta, 'wb') as f:
                        leidos = 0
                        while leidos < tamaño:
                            chunk = self.cliente.recv(min(4096, tamaño - leidos))
                            if not chunk:
                                break
                            f.write(chunk)
                            leidos += len(chunk)
                    
                    self.escribir_en_chat(f"[ARCHIVO] Descarga completada: {nombre_archivo}", "archivo")

                elif tipo == 'P':  # Mensaje privado
                    remitente = self.cliente.recv(64).decode('utf-8').strip()
                    ln = int.from_bytes(self.cliente.recv(4), 'big')
                    msg = self.cliente.recv(ln).decode('utf-8') if ln > 0 else ""
                    
                    pv = self.get_private_window(remitente)
                    #pv['write'](f"[{remitente}]: {msg}")

                elif tipo == 'FP':  # Archivo privado
                    remitente = self.cliente.recv(64).decode('utf-8').strip()
                    nombre_archivo = self.cliente.recv(256).decode('utf-8').strip()
                    tamaño = int.from_bytes(self.cliente.recv(8), 'big')
                    
                    pv = self.get_private_window(remitente)
                    pv['write'](f"[ARCHIVO] {remitente} está enviando: {nombre_archivo} ({tamaño} bytes)")
                    
                    if not os.path.exists("descargas_privadas"):
                        os.makedirs("descargas_privadas")
                    
                    ruta = os.path.join("descargas_privadas", nombre_archivo)
                    with open(ruta, 'wb') as f:
                        leidos = 0
                        while leidos < tamaño:
                            chunk = self.cliente.recv(min(4096, tamaño - leidos))
                            if not chunk:
                                break
                            f.write(chunk)
                            leidos += len(chunk)
                    
                    pv['write'](f"[ARCHIVO] Descarga completada: {nombre_archivo}")

                elif tipo == 'L':  # Lista de clientes
                    # Recibir la lista de clientes
                    data = self.cliente.recv(1024).decode('utf-8')
                    clientes = data.split(',') if data else []
                    self.actualizar_lista_clientes(clientes)

            except Exception as e:
                self.escribir_en_chat(f"[ERROR] {e}", "error")
                break

    def enviar_mensaje(self):
        """Enviar mensaje público"""
        msg = self.entry_msg.get().strip()
        if msg:
            try:
                self.cliente.sendall(b'M' + msg.encode('utf-8'))
                self.entry_msg.delete(0, tk.END)
            except:
                self.escribir_en_chat("[ERROR] No se pudo enviar el mensaje", "error")

    def enviar_privado(self, destino, entry):
        """Enviar mensaje privado"""
        msg = entry.get().strip()
        if not msg:
            return
        
        try:
            destinatario = destino
            self.cliente.sendall(b'P' + destinatario.ljust(64).encode('utf-8') + 
                                len(msg.encode('utf-8')).to_bytes(4, 'big') + 
                                msg.encode('utf-8'))
            entry.delete(0, tk.END)
            
            # Mostrar en la ventana privada
            pv = self.get_private_window(destino)
            pv['write'](f"[Tú]: {msg}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar privado: {e}")

    def enviar_archivo_privado(self, destino):
        """Enviar archivo en chat privado"""
        ruta = filedialog.askopenfilename()
        if not ruta:
            return
        
        try:
            nombre_archivo = os.path.basename(ruta)
            tam = os.path.getsize(ruta)
            
            # Enviar tipo 'FP' para archivo privado
            self.cliente.sendall(b'FP')
            # Enviar destinatario (64 bytes)
            self.cliente.sendall(destino.ljust(64).encode('utf-8'))
            # Enviar nombre del archivo (256 bytes)
            self.cliente.sendall(nombre_archivo.ljust(256).encode('utf-8'))
            # Enviar tamaño (8 bytes)
            self.cliente.sendall(tam.to_bytes(8, 'big'))
            
            # Enviar contenido
            with open(ruta, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.cliente.sendall(chunk)
            
            # Mostrar en la ventana privada
            pv = self.get_private_window(destino)
            pv['write'](f"[Tú] Enviaste un archivo: {nombre_archivo}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar el archivo: {e}")

    def iniciar_privado(self):
        """Iniciar chat privado (método alternativo)"""
        dest = simpledialog.askstring("Chat privado", "Nombre del destinatario:", parent=self.root)
        if dest:
            self.get_private_window(dest)

    def enviar_archivo(self):
        """Enviar archivo público"""
        ruta = filedialog.askopenfilename()
        if not ruta:
            return
        
        try:
            nombre = os.path.basename(ruta)
            tam = os.path.getsize(ruta)
            
            self.cliente.sendall(b'F')
            self.cliente.sendall(nombre.ljust(256).encode('utf-8'))
            self.cliente.sendall(tam.to_bytes(8, 'big'))
            
            with open(ruta, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.cliente.sendall(chunk)
            
            self.escribir_en_chat(f"[ARCHIVO] Enviado: {nombre}", "archivo")
            
        except Exception as e:
            self.escribir_en_chat(f"[ERROR] {e}", "error")

    def on_closing(self):
        """Manejar cierre de la aplicación"""
        try:
            self.cliente.close()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()