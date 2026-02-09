using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace BzmScannerClient
{
    public class BzmTcpClient : IDisposable
    {
        private TcpClient? _client;
        private NetworkStream? _stream;
        private Thread? _receiveThread;
        private volatile bool _running;
        private string _host = "";
        private int _port;

        public bool IsConnected => _client?.Connected == true && _running;

        /// <summary>Fired when data is received from the server.</summary>
        public event Action<string>? DataReceived;

        /// <summary>Fired when the connection is lost.</summary>
        public event Action<string>? Disconnected;

        public void Connect(string host, int port)
        {
            Disconnect();

            _host = host;
            _port = port;
            _client = new TcpClient();
            _client.Connect(host, port);
            _stream = _client.GetStream();
            _running = true;

            _receiveThread = new Thread(ReceiveLoop)
            {
                IsBackground = true,
                Name = "BzmReceive"
            };
            _receiveThread.Start();
        }

        /// <summary>
        /// Send a raw TCP command string. The caller is responsible for
        /// formatting with tab separators.
        /// </summary>
        public void Send(string command)
        {
            if (_stream == null || !IsConnected)
                throw new InvalidOperationException("Not connected.");

            byte[] data = Encoding.ASCII.GetBytes(command);
            _stream.Write(data, 0, data.Length);
        }

        /// <summary>
        /// Send a command and wait up to <paramref name="timeoutMs"/> ms
        /// for a response line.
        /// </summary>
        public string SendAndReceive(string command, int timeoutMs = 5000)
        {
            if (_stream == null || !IsConnected)
                throw new InvalidOperationException("Not connected.");

            // Drain any pending data first
            while (_stream.DataAvailable)
            {
                byte[] discard = new byte[1024];
                _stream.Read(discard, 0, discard.Length);
            }

            byte[] data = Encoding.ASCII.GetBytes(command);
            _stream.Write(data, 0, data.Length);

            // Wait for response
            _stream.ReadTimeout = timeoutMs;
            try
            {
                byte[] buffer = new byte[4096];
                int bytesRead = _stream.Read(buffer, 0, buffer.Length);
                if (bytesRead > 0)
                    return Encoding.ASCII.GetString(buffer, 0, bytesRead);
            }
            catch (IOException)
            {
                // Timeout
            }
            finally
            {
                _stream.ReadTimeout = Timeout.Infinite;
            }

            return "";
        }

        public void Disconnect()
        {
            _running = false;

            try { _stream?.Close(); } catch { }
            try { _client?.Close(); } catch { }

            _stream = null;
            _client = null;

            _receiveThread?.Join(2000);
            _receiveThread = null;
        }

        /// <summary>
        /// Reconnect to a new port (used when server sends NEWPORT=xxxxx).
        /// </summary>
        public void Reconnect(int newPort)
        {
            Disconnect();
            Connect(_host, newPort);
        }

        private void ReceiveLoop()
        {
            byte[] buffer = new byte[4096];

            while (_running)
            {
                try
                {
                    if (_stream == null || _client == null || !_client.Connected)
                        break;

                    if (!_stream.DataAvailable)
                    {
                        Thread.Sleep(50);
                        continue;
                    }

                    int bytesRead = _stream.Read(buffer, 0, buffer.Length);
                    if (bytesRead == 0)
                        break;

                    string message = Encoding.ASCII.GetString(buffer, 0, bytesRead);

                    // Handle port negotiation (from Server.au3 protocol)
                    if (message.StartsWith("NEWPORT=", StringComparison.OrdinalIgnoreCase))
                    {
                        if (int.TryParse(message.Substring(8).Trim(), out int newPort))
                        {
                            DataReceived?.Invoke($"Server requested port change to {newPort}");
                            Reconnect(newPort);
                            return;
                        }
                    }

                    // Skip keep-alive responses
                    if (message.Contains("KEEP_ALIVE", StringComparison.OrdinalIgnoreCase))
                        continue;

                    DataReceived?.Invoke(message);
                }
                catch (IOException)
                {
                    break;
                }
                catch (ObjectDisposedException)
                {
                    break;
                }
            }

            if (_running)
            {
                _running = false;
                Disconnected?.Invoke("Connection lost.");
            }
        }

        public void Dispose()
        {
            Disconnect();
        }
    }
}
