"""
A tiny SMTP server for tests (real sockets, real smtplib on the client side).

modes:  accept | bad_auth | reject_rcpt (550) | temp_rcpt (451) | reject_data (554)
        drop (closes at once) | silent (accepts, never answers)
Pass tls=(certfile, keyfile) to advertise and support STARTTLS.
"""
import base64
import socket
import ssl
import threading
import time


class FakeSmtpServer:
    def __init__(self, mode="accept", tls=None):
        self.mode, self.tls = mode, tls
        self.messages, self.connections, self.auth_user = [], 0, None
        self.tls_negotiated = False
        self._stop = False
        self._sock = socket.socket()
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(16)
        self._sock.settimeout(0.2)              # lets stop() end the accept loop promptly
        self.port = self._sock.getsockname()[1]
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop = True
        if self._thread:
            self._thread.join(timeout=2)        # after this nothing is listening any more
        try:
            self._sock.close()
        except OSError:
            pass

    def _serve(self):
        while not self._stop:
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            conn.settimeout(None)
            self.connections += 1
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        try:
            self._talk(conn)
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _talk(self, conn):
        if self.mode == "drop":
            return
        if self.mode == "silent":
            while not self._stop:
                time.sleep(0.05)
            return
        state = {"conn": conn}

        def send(text):
            state["conn"].sendall(text.encode() + b"\r\n")

        reader = conn.makefile("rb")
        send("220 fake.local ESMTP ready")
        sender, rcpts = None, []
        while True:
            line = reader.readline()
            if not line:
                return
            cmd = line.decode(errors="replace").strip()
            up = cmd.upper()
            if up.startswith("EHLO"):
                if self.tls and not self.tls_negotiated:
                    send("250-fake.local")
                    send("250-STARTTLS")
                    send("250 AUTH PLAIN")
                else:
                    send("250-fake.local")
                    send("250 AUTH PLAIN")
            elif up == "STARTTLS" and self.tls:
                send("220 Ready to start TLS")
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ctx.load_cert_chain(*self.tls)
                state["conn"] = ctx.wrap_socket(conn, server_side=True)
                reader = state["conn"].makefile("rb")
                self.tls_negotiated = True
            elif up.startswith("AUTH PLAIN"):
                if self.mode == "bad_auth":
                    send("535 5.7.8 Authentication credentials invalid")
                else:
                    parts = base64.b64decode(cmd.split()[2]).split(b"\0")
                    self.auth_user = parts[1].decode()
                    send("235 2.7.0 Authentication successful")
            elif up.startswith("MAIL FROM"):
                sender = cmd[10:].strip()
                send("250 OK")
            elif up.startswith("RCPT TO"):
                if self.mode == "reject_rcpt":
                    send("550 5.1.1 User unknown")
                elif self.mode == "temp_rcpt":
                    send("451 4.3.0 Try again later")
                else:
                    rcpts.append(cmd[8:].strip())
                    send("250 OK")
            elif up == "DATA":
                send("354 End data with <CR><LF>.<CR><LF>")
                lines = []
                while True:
                    row = reader.readline()
                    if row in (b".\r\n", b""):
                        break
                    lines.append(row.decode(errors="replace"))
                if self.mode == "reject_data":
                    send("554 5.6.0 Transaction failed")
                else:
                    self.messages.append({"from": sender, "to": rcpts, "data": "".join(lines)})
                    send("250 OK queued")
            elif up in ("RSET", "NOOP"):
                send("250 OK")
            elif up == "QUIT":
                send("221 Bye")
                return
            else:
                send("502 Not implemented")
