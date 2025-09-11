import socket
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk
import queue
import os

# Configuración
HOST = "192.168.1.107"
PORT = 5000
FONT_FAMILY = "Segoe UI"
BG_COLOR = "#b8b8b8"
ACCENT_COLOR = "#4a86e8"
TEXT_COLOR = "#333333"

class ChatServer:
    def __init__(self, root):
        self.root = root
        self.root.title("server")
        self.root.geometry("650x600")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(600, 400)
        
        # Variables
        self.clientes = {}
        self.nombres_a_conn = {}
        self.log_queue = queue.Queue()
        
        # Establecer estilo
        self.setup_styles()
        
        # Interfaz
        self.setup_ui()
        
        # Iniciar servidor
        self.iniciar_servidor()
        
        # Procesar mensajes de la cola
        self.process_log_queue()
    
    def setup_styles(self):
        """Configurar estilos para los widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar colores
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TButton", 
                        font=(FONT_FAMILY, 10), 
                        background=ACCENT_COLOR, 
                        foreground="#000000")
        style.configure("TLabel", 
                        background=BG_COLOR, 
                        foreground=TEXT_COLOR)
        
    def setup_ui(self):
        """Configurar la interfaz de usuario"""
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="Log de servidor de Chat", 
                 font=(FONT_FAMILY, 14, "italic")).pack(side=tk.LEFT)
        
        # Botones de control
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(control_frame, text="Actualizar Lista", 
                  command=self.actualizar_lista_clientes).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(control_frame, text="Limpiar Log", 
                  command=self.limpiar_log).pack(side=tk.LEFT)
        
        # Frame para estadísticas
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.client_count = ttk.Label(stats_frame, text="Clientes conectados: 0", 
                                     font=(FONT_FAMILY, 10))
        self.client_count.pack(side=tk.LEFT)
        
        # Área de log
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_area = ScrolledText(
            log_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=25, 
            state="disabled",
            font=(FONT_FAMILY, 10),
            bg="white",
            fg=TEXT_COLOR,
            padx=10,
            pady=10
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # Configurar tags para diferentes tipos de mensajes
        self.text_area.tag_config("info", foreground="blue")
        self.text_area.tag_config("error", foreground="red")
        self.text_area.tag_config("success", foreground="green")
        self.text_area.tag_config("warning", foreground="orange")
        self.text_area.tag_config("private", foreground="purple")
        
        # Barra de estado
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_text = ttk.Label(status_frame, text="Servidor iniciado", font=(FONT_FAMILY, 9))
        self.status_text.pack(side=tk.LEFT, padx=5)
    
    def gui_log(self, msg, tag=None):
        """Agregar mensaje al log de la interfaz"""
        self.log_queue.put((msg, tag))
    
    def process_log_queue(self):
        """Procesar mensajes de la cola para actualizar la interfaz"""
        try:
            while True:
                msg, tag = self.log_queue.get_nowait()
                self.text_area.config(state="normal")
                
                if tag:
                    self.text_area.insert(tk.END, msg + "\n", tag)
                else:
                    self.text_area.insert(tk.END, msg + "\n")
                
                self.text_area.see(tk.END)
                self.text_area.config(state="disabled")
        except queue.Empty:
            pass
        
        # Programar próxima verificación
        self.root.after(100, self.process_log_queue)
    
    def actualizar_lista_clientes(self):
        """Actualizar la lista de clientes en la interfaz"""
        clientes = ", ".join(self.nombres_a_conn.keys()) if self.nombres_a_conn else "Ninguno"
        self.gui_log(f"[INFO] Clientes conectados: {clientes}", "info")
        self.client_count.config(text=f"Clientes conectados: {len(self.nombres_a_conn)}")
    
    def limpiar_log(self):
        """Limpiar el área de log"""
        self.text_area.config(state="normal")
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state="disabled")
    
    def send_all_file_chunked(self, dest_conn_list, nombre_archivo, contenido):
        """Enviar archivo a múltiples clientes"""
        try:
            size = len(contenido)
            for c in dest_conn_list:
                try:
                    c.sendall(b'F')
                    c.sendall(nombre_archivo.ljust(256).encode('utf-8'))
                    c.sendall(size.to_bytes(8, 'big'))
                    c.sendall(contenido)
                except:
                    # Si falla el envío, desconectar al cliente
                    if c in self.clientes:
                        nombre = self.clientes[c]
                        del self.clientes[c]
                        if nombre in self.nombres_a_conn:
                            del self.nombres_a_conn[nombre]
                        self.gui_log(f"[-] {nombre} desconectado por error de envío", "error")
        except Exception as e:
            self.gui_log(f"[ERROR] Error al enviar archivo: {e}", "error")
    
    def send_private_file(self, destinatario_conn, remitente, nombre_archivo, contenido):
        """Enviar archivo privado a un cliente específico"""
        try:
            size = len(contenido)
            # Enviar tipo 'FP' para archivo privado
            destinatario_conn.sendall(b'FP')
            # Enviar remitente (64 bytes)
            destinatario_conn.sendall(remitente.ljust(64).encode('utf-8'))
            # Enviar nombre del archivo (256 bytes)
            destinatario_conn.sendall(nombre_archivo.ljust(256).encode('utf-8'))
            # Enviar tamaño (8 bytes)
            destinatario_conn.sendall(size.to_bytes(8, 'big'))
            # Enviar contenido
            destinatario_conn.sendall(contenido)
            return True
        except Exception as e:
            self.gui_log(f"[ERROR] Error enviando archivo privado: {e}", "error")
            return False
    
    def enviar_lista_clientes(self):
        """Enviar lista de clientes a todos los conectados"""
        try:
            lista = ",".join(self.nombres_a_conn.keys())
            payload = b'L' + lista.encode('utf-8')
            
            for c in list(self.clientes.keys()):
                try:
                    c.sendall(payload)
                except:
                    # Si falla el envío, desconectar al cliente
                    if c in self.clientes:
                        nombre = self.clientes[c]
                        del self.clientes[c]
                        if nombre in self.nombres_a_conn:
                            del self.nombres_a_conn[nombre]
                        self.gui_log(f"[-] {nombre} desconectado por error de envío", "error")
            
            self.gui_log(f"[INFO] Lista enviada a clientes: {lista}", "info")
        except Exception as e:
            self.gui_log(f"[ERROR] Error enviando lista de clientes: {e}", "error")

    
    def manejar_cliente(self, conn, addr):
        """Manejar la conexión con un cliente"""
        nombre = None
        try:
            while True:
                tipo = conn.recv(1).decode("utf-8")
                if not tipo:
                    break

                if tipo == 'N':  # Nombre
                    nombre = conn.recv(1024).decode("utf-8").strip() or str(addr)
                    self.clientes[conn] = nombre
                    self.nombres_a_conn[nombre] = conn
                    self.gui_log(f"[+] {nombre} se ha conectado desde {addr}", "success")
                    self.enviar_lista_clientes()
                    self.actualizar_lista_clientes()

                elif tipo == 'M':  # Mensaje público
                    data = conn.recv(1024).decode("utf-8")
                    if not data:
                        break
                    nombre_actual = self.clientes.get(conn, "Desconocido")
                    mensaje = f"[{nombre_actual}]: {data}"
                    self.gui_log(mensaje)
                    
                    # Reenviar a todos
                    for c in list(self.clientes.keys()):
                        try:
                            c.sendall(b'M' + mensaje.encode('utf-8'))
                        except:
                            # Si falla el envío, desconectar al cliente
                            if c in self.clientes:
                                nombre_err = self.clientes[c]
                                del self.clientes[c]
                                if nombre_err in self.nombres_a_conn:
                                    del self.nombres_a_conn[nombre_err]
                                self.gui_log(f"[-] {nombre_err} desconectado por error de envío", "error")

                elif tipo == 'F':  # Archivo público
                    nombre_archivo = conn.recv(256).decode("utf-8").strip()
                    tamaño = int.from_bytes(conn.recv(8), 'big')
                    nombre_actual = self.clientes.get(conn, "Desconocido")
                    self.gui_log(f"[ARCHIVO] {nombre_actual} envió: {nombre_archivo} ({tamaño} bytes)", "info")

                    contenido = b''
                    leidos = 0
                    while leidos < tamaño:
                        chunk = conn.recv(min(4096, tamaño - leidos))
                        if not chunk:
                            break
                        contenido += chunk
                        leidos += len(chunk)

                    try:
                        if not os.path.exists("archivos_servidor"):
                            os.makedirs("archivos_servidor")
                        with open(f"archivos_servidor/recibido_{nombre_archivo}", "wb") as f:
                            f.write(contenido)
                        self.gui_log(f"[ARCHIVO] Guardado como: recibido_{nombre_archivo}", "success")
                    except Exception as e:
                        self.gui_log(f"[ERROR] Error guardando archivo: {e}", "error")

                    # Reenviar a todos excepto al emisor
                    dests = [c for c in list(self.clientes.keys()) if c != conn]
                    self.send_all_file_chunked(dests, nombre_archivo, contenido)

                elif tipo == 'P':  # Mensaje privado
                    dest_raw = conn.recv(64)
                    if not dest_raw:
                        break
                    destinatario = dest_raw.decode('utf-8').strip()
                    ln = int.from_bytes(conn.recv(4), 'big')
                    msg = conn.recv(ln).decode('utf-8') if ln > 0 else ""

                    remitente = self.clientes.get(conn, "Desconocido")
                    #self.gui_log(f"[PRIVADO] {remitente} -> {destinatario}: {msg}", "private")

                    dest_conn = self.nombres_a_conn.get(destinatario)
                    
                    # Payload al receptor
                    payload_receptor = b'P' + remitente.ljust(64).encode('utf-8') + ln.to_bytes(4, 'big') + msg.encode('utf-8')
                    
                    # Payload al emisor (eco)
                    payload_emisor = b'P' + destinatario.ljust(64).encode('utf-8') + ln.to_bytes(4, 'big') + msg.encode('utf-8')

                    # Enviar al receptor si existe
                    if dest_conn:
                        try:
                            dest_conn.sendall(payload_receptor)
                        except:
                            self.gui_log(f"[ERROR] Error enviando mensaje privado a {destinatario}", "error")
                    
                    # Enviar eco al emisor
                    try:
                        conn.sendall(payload_emisor)
                    except:
                        self.gui_log(f"[ERROR] Error enviando eco a {remitente}", "error")

                elif tipo == 'FP':  # Archivo privado
                    # Leer destinatario (64 bytes)
                    dest_raw = conn.recv(64)
                    if not dest_raw:
                        break
                    destinatario = dest_raw.decode('utf-8').strip()
                    
                    # Leer nombre archivo (256 bytes) y tamaño (8 bytes)
                    nombre_archivo = conn.recv(256).decode('utf-8').strip()
                    tamaño = int.from_bytes(conn.recv(8), 'big')
                    
                    remitente = self.clientes.get(conn, "Desconocido")
                    #self.gui_log(f"[ARCHIVO PRIVADO] {remitente} -> {destinatario}: {nombre_archivo} ({tamaño} bytes)", "private")

                    # Leer contenido
                    contenido = b''
                    leidos = 0
                    while leidos < tamaño:
                        chunk = conn.recv(min(4096, tamaño - leidos))
                        if not chunk:
                            break
                        contenido += chunk
                        leidos += len(chunk)

                    # Guardar archivo en servidor (opcional)
                    try:
                        if not os.path.exists("archivos_privados"):
                            os.makedirs("archivos_privados")
                        with open(f"archivos_privados/{remitente}_a_{destinatario}_{nombre_archivo}", "wb") as f:
                            f.write(contenido)
                        self.gui_log(f"[ARCHIVO PRIVADO] Guardado: {remitente}_a_{destinatario}_{nombre_archivo}", "success")
                    except Exception as e:
                        self.gui_log(f"[ERROR] Error guardando archivo privado: {e}", "error")

                    # Enviar al destinatario
                    dest_conn = self.nombres_a_conn.get(destinatario)
                    if dest_conn:
                        if not self.send_private_file(dest_conn, remitente, nombre_archivo, contenido):
                            self.gui_log(f"[ERROR] Error enviando archivo privado a {destinatario}", "error")
                    
                    # Enviar eco al remitente
                    try:
                        # Enviar confirmación al remitente
                        conn.sendall(b'P' + destinatario.ljust(64).encode('utf-8') + 
                                    len(f"Archivo enviado: {nombre_archivo}".encode('utf-8')).to_bytes(4, 'big') + 
                                    f"Archivo enviado: {nombre_archivo}".encode('utf-8'))
                    except:
                        self.gui_log(f"[ERROR] Error enviando eco a {remitente}", "error")

                else:
                    self.gui_log(f"[ADVERTENCIA] Tipo desconocido recibido: {repr(tipo)} de {addr}", "warning")

        except Exception as e:
            self.gui_log(f"[ERROR] Error con {addr}: {e}", "error")
        finally:
            try:
                conn.close()
            except:
                pass
            
            if conn in self.clientes:
                ap = self.clientes.pop(conn)
                if ap in self.nombres_a_conn:
                    del self.nombres_a_conn[ap]
                self.gui_log(f"[-] {ap} se ha desconectado", "info")
                self.enviar_lista_clientes()
                self.actualizar_lista_clientes()
    
    def iniciar_servidor(self):
        """Iniciar el servidor"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, PORT))
            self.server.listen(10)
            self.gui_log(f"[INFO] Servidor escuchando en {HOST}:{PORT}...", "info")
            self.status_text.config(text=f"Servidor ejecutándose en {HOST}:{PORT}")

            def aceptar_clientes():
                while True:
                    try:
                        conn, addr = self.server.accept()
                        hilo = threading.Thread(target=self.manejar_cliente, args=(conn, addr), daemon=True)
                        hilo.start()
                        self.gui_log(f"[INFO] Clientes activos: {threading.active_count()-1}", "info")
                    except:
                        break

            threading.Thread(target=aceptar_clientes, daemon=True).start()
            
        except Exception as e:
            self.gui_log(f"[ERROR] No se pudo iniciar el servidor: {e}", "error")
            self.status_text.config(text="Error al iniciar el servidor")

def main():
    root = tk.Tk()
    app = ChatServer(root)
    root.mainloop()

if __name__ == "__main__":
    main()