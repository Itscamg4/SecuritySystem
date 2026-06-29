"""
Security Alarm — Python WiFi backend
Runs a local Flask server. The ESP8266 POSTs to /alert whenever
something is detected; this app handles the email alert + cooldown.

Install deps:  pip install flask
"""

import socket
import time
import smtplib
import threading
from email.message import EmailMessage

from flask import Flask, request, jsonify
from werkzeug.serving import make_server

import tkinter as tk
from tkinter import ttk, messagebox

# ── Hardcoded sender credentials ──────────────────────────────────────────────

SENDER_EMAIL    = 'camcodetests@gmail.com'
SENDER_PASSWORD = 'twbh vmje ilhy rwfo'

# ── Flask app ─────────────────────────────────────────────────────────────────

flask_app = Flask(__name__)
_gui_ref  = None   # set to the SecurityAlarmApp instance when server starts


@flask_app.route('/alert', methods=['POST'])
def handle_alert():
    data     = request.get_json(silent=True) or {}
    distance = data.get('distance', '?')
    if _gui_ref and _gui_ref.running:
        _gui_ref.on_detection(distance)
    return jsonify({'status': 'ok'}), 200


@flask_app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'alive'}), 200


# ── Helpers ───────────────────────────────────────────────────────────────────

def email_alert(subject, body, to):
    msg = EmailMessage()
    msg.set_content(body)
    msg['subject'] = subject
    msg['to']      = to
    msg['from']    = SENDER_EMAIL
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()


def get_local_ip():
    """Return the machine's LAN IP (the one the ESP8266 can reach)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


# ── Flask server thread ───────────────────────────────────────────────────────

class FlaskServerThread(threading.Thread):
    """Wraps werkzeug's make_server so we can start and stop it cleanly."""

    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.srv = make_server(host, port, flask_app)

    def run(self):
        self.srv.serve_forever()

    def shutdown(self):
        self.srv.shutdown()


# ── GUI ───────────────────────────────────────────────────────────────────────

class SecurityAlarmApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Security Alarm')
        self.resizable(False, False)
        self.configure(bg='#0f1117')

        self.last_alert    = 0
        self.running       = False
        self.server_thread = None
        self.local_ip      = get_local_ip()

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        BG       = '#0f1117'
        CARD     = '#1a1d27'
        ACCENT   = '#f75a4f'
        FG       = '#e8eaf0'
        MUTED    = '#8b8fa8'
        ENTRY_BG = '#242736'
        LOG_BG   = '#12151f'
        GREEN    = '#4fc97a'

        style = ttk.Style(self)
        style.theme_use('clam')

        styles = {
            'TEntry':         dict(fieldbackground=ENTRY_BG, background=ENTRY_BG,
                                   foreground=FG, insertcolor=FG,
                                   borderwidth=0, relief='flat', padding=8),
            'TLabel':         dict(background=CARD, foreground=MUTED,
                                   font=('Helvetica Neue', 11)),
            'Header.TLabel':  dict(background=BG, foreground=FG,
                                   font=('Helvetica Neue', 20, 'bold')),
            'Sub.TLabel':     dict(background=BG, foreground=MUTED,
                                   font=('Helvetica Neue', 11)),
            'Section.TLabel': dict(background=CARD, foreground=ACCENT,
                                   font=('Helvetica Neue', 10, 'bold')),
            'IP.TLabel':      dict(background=CARD, foreground=GREEN,
                                   font=('Courier New', 12, 'bold')),
            'URL.TLabel':     dict(background=CARD, foreground=FG,
                                   font=('Courier New', 10)),
            'LogLabel.TLabel':dict(background=BG, foreground=MUTED,
                                   font=('Helvetica Neue', 10, 'bold')),
            'Start.TButton':  dict(background=ACCENT, foreground='white',
                                   font=('Helvetica Neue', 12, 'bold'),
                                   borderwidth=0, relief='flat', padding=(0, 10)),
            'Stop.TButton':   dict(background='#3a3d50', foreground=FG,
                                   font=('Helvetica Neue', 12, 'bold'),
                                   borderwidth=0, relief='flat', padding=(0, 10)),
        }
        for name, cfg in styles.items():
            style.configure(name, **cfg)

        style.map('Start.TButton',
                  background=[('active', '#d94540'), ('disabled', '#4a2a2a')])
        style.map('Stop.TButton',
                  background=[('active', '#2a2d3a'), ('disabled', '#1e2030')])

        outer = tk.Frame(self, bg=BG, padx=30, pady=30)
        outer.pack(fill='both', expand=True)

        # ── Header ────────────────────────────────────────────────────────────
        ttk.Label(outer, text='Security Alarm',
                  style='Header.TLabel').grid(row=0, column=0,
                                              columnspan=2, sticky='w')
        ttk.Label(outer,
                  text='WiFi mode — ESP8266 posts alerts over your local network.',
                  style='Sub.TLabel').grid(row=1, column=0, columnspan=2,
                                           sticky='w', pady=(2, 20))

        # ── Card ──────────────────────────────────────────────────────────────
        card = tk.Frame(outer, bg=CARD, padx=24, pady=20)
        card.grid(row=2, column=0, columnspan=2, sticky='ew')
        card.columnconfigure(1, weight=1)

        def section(row, text):
            ttk.Label(card, text=text, style='Section.TLabel').grid(
                row=row, column=0, columnspan=2, sticky='w', pady=(14, 4))

        def field(row, label, default=''):
            ttk.Label(card, text=label).grid(
                row=row, column=0, sticky='w', pady=5, padx=(0, 20))
            var = tk.StringVar(value=default)
            ttk.Entry(card, textvariable=var, width=36,
                      style='TEntry').grid(row=row, column=1,
                                           sticky='ew', pady=5)
            return var

        # ── Server section ────────────────────────────────────────────────────
        section(0, 'SERVER')

        ttk.Label(card, text='Your IP').grid(
            row=1, column=0, sticky='w', pady=5, padx=(0, 20))
        ttk.Label(card, text=self.local_ip, style='IP.TLabel').grid(
            row=1, column=1, sticky='w', pady=5)

        self.v_port = field(2, 'Port', '5000')

        ttk.Label(card, text='ESP8266 URL').grid(
            row=3, column=0, sticky='w', pady=5, padx=(0, 20))
        self.url_var = tk.StringVar(value=self._make_url())
        ttk.Label(card, textvariable=self.url_var,
                  style='URL.TLabel').grid(row=3, column=1, sticky='w', pady=5)

        # Live-update the URL preview as the user types a different port
        self.v_port.trace_add('write', lambda *_: self.url_var.set(self._make_url()))

        self.v_cooldown = field(4, 'Cooldown (s)', '60')

        # ── Email section ─────────────────────────────────────────────────────
        section(5, 'EMAIL')
        self.v_recipient = field(6, 'Send alert to',  'itscamg@gmail.com')
        self.v_subject   = field(7, 'Subject',        'Security Alert!')
        self.v_message   = field(8, 'Message',
                                 'Something was detected by your security sensor.')

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = tk.Frame(outer, bg=BG)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0), sticky='ew')
        btn_frame.columnconfigure((0, 1), weight=1)

        self.start_btn = ttk.Button(btn_frame, text='Start Server',
                                     style='Start.TButton', command=self.start)
        self.start_btn.grid(row=0, column=0, sticky='ew', padx=(0, 8))

        self.stop_btn = ttk.Button(btn_frame, text='Stop',
                                    style='Stop.TButton', command=self.stop,
                                    state='disabled')
        self.stop_btn.grid(row=0, column=1, sticky='ew')

        # ── Status ────────────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value='● Idle')
        self.status_label = tk.Label(outer, textvariable=self.status_var,
                                      bg=BG, fg=MUTED,
                                      font=('Helvetica Neue', 10))
        self.status_label.grid(row=4, column=0, sticky='w', pady=(12, 0))

        # ── Log ───────────────────────────────────────────────────────────────
        ttk.Label(outer, text='LOG', style='LogLabel.TLabel').grid(
            row=5, column=0, columnspan=2, sticky='w', pady=(16, 6))

        self.log_box = tk.Text(
            outer, height=12, width=62,
            bg=LOG_BG, fg='#a8d8a8',
            insertbackground=FG,
            font=('Courier New', 11),
            relief='flat', borderwidth=0,
            padx=12, pady=10,
            state='disabled', wrap='word')
        self.log_box.grid(row=6, column=0, columnspan=2, sticky='ew')

        sb = ttk.Scrollbar(outer, orient='vertical', command=self.log_box.yview)
        sb.grid(row=6, column=2, sticky='ns')
        self.log_box.configure(yscrollcommand=sb.set)

        self.log_box.tag_configure('error',  foreground='#f75a4f')
        self.log_box.tag_configure('email',  foreground='#f7c948')
        self.log_box.tag_configure('wait',   foreground='#8b8fa8')
        self.log_box.tag_configure('detect', foreground='#ff9f43')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_url(self):
        port = self.v_port.get() if hasattr(self, 'v_port') else '5000'
        return f'http://{self.local_ip}:{port}/alert'

    def log(self, msg):
        """Thread-safe log write."""
        self.after(0, self._write_log, msg)

    def _write_log(self, msg):
        self.log_box.configure(state='normal')
        tag = (
            'error'  if '[ERROR]'  in msg else
            'email'  if '[EMAIL]'  in msg else
            'wait'   if '[WAIT]'   in msg else
            'detect' if '[DETECT]' in msg else ''
        )
        ts = time.strftime('%H:%M:%S')
        self.log_box.insert('end', f'{ts}  {msg}\n', tag)
        self.log_box.see('end')
        self.log_box.configure(state='disabled')

    def _set_status(self, text, color):
        self.after(0, lambda: (
            self.status_var.set(text),
            self.status_label.configure(fg=color)
        ))

    # ── Detection handler (called from Flask thread) ──────────────────────────

    def on_detection(self, distance):
        self.log(f'[DETECT]  Object at {distance} cm')

        try:
            cooldown = int(self.v_cooldown.get())
        except ValueError:
            cooldown = 60

        now = time.time()
        if now - self.last_alert > cooldown:
            self.last_alert = now
            # Email in its own thread so the Flask response isn't delayed
            threading.Thread(target=self._send_email, daemon=True).start()
        else:
            remaining = int(cooldown - (now - self.last_alert))
            self.log(f'[WAIT]    Cooldown active — {remaining}s remaining')

    def _send_email(self):
        recipient = self.v_recipient.get().strip()
        try:
            email_alert(self.v_subject.get(), self.v_message.get(), recipient)
            self.log(f'[EMAIL]   Alert sent to {recipient}')
        except Exception as e:
            self.log(f'[ERROR]   Email failed: {e}')

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def start(self):
        global _gui_ref

        try:
            port = int(self.v_port.get())
        except ValueError:
            messagebox.showerror('Invalid input', 'Port must be a whole number.')
            return

        if not self.v_recipient.get().strip():
            messagebox.showerror('Missing field', 'Please enter a recipient email.')
            return

        try:
            self.server_thread = FlaskServerThread('0.0.0.0', port)
            self.server_thread.start()
        except OSError as e:
            messagebox.showerror('Server error',
                                 f'Could not bind to port {port}:\n{e}')
            return

        _gui_ref     = self
        self.running = True

        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self._set_status('● Listening', '#4fc97a')
        self.log(f'Server started on port {port}.')
        self.log(f'Flash ESP8266 with SERVER_URL = "{self._make_url()}"')

    def stop(self):
        global _gui_ref

        self.running = False
        _gui_ref     = None

        if self.server_thread:
            self.server_thread.shutdown()
            self.server_thread = None

        self.start_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self._set_status('● Idle', '#8b8fa8')
        self.log('Server stopped.')


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app = SecurityAlarmApp()
    app.mainloop()