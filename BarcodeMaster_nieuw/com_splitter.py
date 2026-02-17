import serial
import threading
import time
import queue

class ComSplitter:
    def __init__(self, config, log_callback):
        self.physical_port_name = config.get('physical_port')
        self.virtual_port_1_name = config.get('virtual_port_1')
        self.virtual_port_2_name = config.get('virtual_port_2')
        self.baud_rate = int(config.get('baud_rate', 9600))
        self.log_callback = log_callback

        self.stop_event = threading.Event()
        self.data_queue = queue.Queue()
        self.main_thread = None

        self.scanner_port = None
        self.vport1 = None
        self.vport2 = None

    def _log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def start(self):
        if self.main_thread and self.main_thread.is_alive():
            self._log("Splitter is already running.")
            return
        
        self.stop_event.clear()
        self.main_thread = threading.Thread(target=self._run, daemon=True)
        self.main_thread.start()
        self._log("ComSplitter process started.")

    def stop(self):
        if not self.main_thread or not self.main_thread.is_alive():
            self._log("Splitter is not running.")
            return

        self._log("Stopping ComSplitter process...")
        self.stop_event.set()
        self.main_thread.join(timeout=3) # Wait for the thread to finish
        if self.main_thread.is_alive():
            self._log("Warning: Main thread did not terminate gracefully.")
        self._log("ComSplitter process stopped.")

    def _run(self):
        if not all([self.physical_port_name, self.virtual_port_1_name, self.virtual_port_2_name]):
            self._log("Error: All COM ports must be specified.")
            return

        try:
            self.scanner_port = serial.Serial(port=self.physical_port_name, baudrate=self.baud_rate, timeout=1)
            self.vport1 = serial.Serial(port=self.virtual_port_1_name, baudrate=self.baud_rate, timeout=1)
            self.vport2 = serial.Serial(port=self.virtual_port_2_name, baudrate=self.baud_rate, timeout=1)
            self.scanner_port.close()
            self.vport1.close()
            self.vport2.close()
        except serial.SerialException as e:
            self._log(f"Fatal: Could not initialize COM ports: {e}")
            return

        reader = threading.Thread(target=self._reader_loop, daemon=True)
        reader.start()

        self._writer_loop()

        self.stop_event.set() # Ensure reader stops if writer loop exits
        reader.join(timeout=2)
        self._cleanup_ports()

    def _reader_loop(self):
        self._log(f"Reader: Attempting to open {self.physical_port_name}...")
        while not self.stop_event.is_set():
            try:
                if not self.scanner_port.is_open:
                    self.scanner_port.open()
                self._log(f"Reader: Port {self.physical_port_name} opened successfully.")
                
                while not self.stop_event.is_set():
                    if self.scanner_port.in_waiting > 0:
                        line = self.scanner_port.readline()
                        if line:
                            self.data_queue.put(line)
                            self._log(f"Data Read: {line.strip().decode(errors='ignore')}")
                    else:
                        time.sleep(0.05)

            except serial.SerialException as e:
                self._log(f"Reader Error: {e}. Retrying in 5s.")
                if self.scanner_port.is_open: self.scanner_port.close()
                # Interruptible sleep
                for _ in range(50):
                    if self.stop_event.is_set():
                        break
                    time.sleep(0.1)
            except Exception as e:
                self._log(f"Reader Unexpected Error: {e}")
                self.stop_event.set()
                break
        self._log("Reader thread has stopped.")

    def _writer_loop(self):
        while not self.stop_event.is_set():
            try:
                line = self.data_queue.get(timeout=1)
                self._write_to_port(self.vport1, self.virtual_port_1_name, line)
                self._write_to_port(self.vport2, self.virtual_port_2_name, line)
                self.data_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self._log(f"Writer Unexpected Error: {e}")
                self.stop_event.set()
                break
        self._log("Writer loop has stopped.")

    def _write_to_port(self, port, port_name, data):
        try:
            if not port.is_open:
                port.open()
            port.write(data)
            self._log(f"Forwarded to {port_name}")
        except serial.SerialException as e:
            self._log(f"Write Error on {port_name}: {e}")
            if port.is_open: port.close()
            time.sleep(2)

    def _cleanup_ports(self):
        self._log("Cleaning up COM ports...")
        if self.scanner_port and self.scanner_port.is_open:
            self.scanner_port.close()
        if self.vport1 and self.vport1.is_open:
            self.vport1.close()
        if self.vport2 and self.vport2.is_open:
            self.vport2.close()
        self._log("Cleanup complete.")
