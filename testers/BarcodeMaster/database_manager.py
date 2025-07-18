import threading
import requests
import time
from urllib.parse import urljoin
from config_utils import get_config

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.connection_status = 'Niet verbonden'
        self.connection_color = 'red'
        self.logs = []
        self.running = True
        self.status_thread = threading.Thread(target=self._connection_checker, daemon=True)
        self.status_thread.start()
        self.logs_thread = threading.Thread(target=self._logs_poller, daemon=True)
        self.logs_thread.start()

    def _connection_checker(self):
        while self.running:
            config = get_config()
            if config.get('database_enabled', True):
                base_url = config.get('api_url', '').strip()
                if base_url:
                    url = urljoin(base_url, 'logs')
                    try:
                        resp = requests.get(url, timeout=3)
                        if resp.status_code == 200:
                            self.connection_status = 'Verbonden'
                            self.connection_color = 'green'
                        else:
                            self.connection_status = 'Niet verbonden'
                            self.connection_color = 'red'
                    except Exception:
                        self.connection_status = 'Niet verbonden'
                        self.connection_color = 'red'
                else:
                    self.connection_status = 'Niet verbonden'
                    self.connection_color = 'red'
            else:
                self.connection_status = 'Niet verbonden'
                self.connection_color = 'red'
            time.sleep(5)

    def _logs_poller(self):
        while self.running:
            config = get_config()
            if config.get('database_enabled', True):
                base_url = config.get('api_url', '').strip()
                if base_url:
                    url = urljoin(base_url, 'logs')
                    try:
                        resp = requests.get(url, timeout=5)
                        if resp.status_code == 200:
                            self.logs = resp.json()
                    except Exception:
                        pass
                else:
                    self.logs = []
            else:
                self.logs = []
            time.sleep(10)

    def get_status(self):
        return self.connection_status, self.connection_color

    def get_logs(self):
        return list(self.logs)

    def stop(self):
        self.running = False
