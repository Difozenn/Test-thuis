using System.Runtime.InteropServices;

namespace BZManualClient;

/// <summary>
/// COM Interop client that uses BZManualX.ocx directly.
/// Requires: regsvr32 BZManualX.ocx (run as admin)
/// ProgID: BzmanualX.BzmanualXCtrl.1
///
/// Commands use SEMICOLON separators: ADD_HOP_FILE;CH;filename
/// </summary>
public class BZManualComClient : IDisposable
{
    private dynamic? _control;
    private Type? _comType;

    public string Host { get; private set; } = "127.0.0.1";
    public int Port { get; private set; } = 100;
    public bool IsConnected { get; private set; }

    public event EventHandler<string>? LogMessage;
    public event EventHandler<string>? ErrorOccurred;
    public event EventHandler<bool>? ConnectionChanged;

    public void Configure(string host, int port)
    {
        Host = host;
        Port = port;
    }

    public bool CreateControl()
    {
        try
        {
            _comType = Type.GetTypeFromProgID("BzmanualX.BzmanualXCtrl.1");

            if (_comType == null)
            {
                ErrorOccurred?.Invoke(this, "BzmanualX.BzmanualXCtrl.1 not found. Run: regsvr32 BZManualX.ocx");
                return false;
            }

            _control = Activator.CreateInstance(_comType);
            LogMessage?.Invoke(this, "COM control created successfully");
            return _control != null;
        }
        catch (COMException ex)
        {
            ErrorOccurred?.Invoke(this, $"COM Error: {ex.Message} (0x{ex.ErrorCode:X8})");
            return false;
        }
        catch (Exception ex)
        {
            ErrorOccurred?.Invoke(this, $"Failed to create COM control: {ex.Message}");
            return false;
        }
    }

    public bool Connect()
    {
        try
        {
            if (_control == null && !CreateControl())
                return false;

            LogMessage?.Invoke(this, $"Calling TcpConnect({Host}, {Port})...");
            _control!.TcpConnect(Host, (short)Port);

            System.Threading.Thread.Sleep(100);
            IsConnected = CheckConnection();

            ConnectionChanged?.Invoke(this, IsConnected);
            return IsConnected;
        }
        catch (COMException ex)
        {
            ErrorOccurred?.Invoke(this, $"TcpConnect failed: {ex.Message} (0x{ex.ErrorCode:X8})");
            ConnectionChanged?.Invoke(this, false);
            return false;
        }
        catch (Exception ex)
        {
            ErrorOccurred?.Invoke(this, $"Connect failed: {ex.Message}");
            ConnectionChanged?.Invoke(this, false);
            return false;
        }
    }

    public bool CheckConnection()
    {
        try
        {
            if (_control == null) return false;
            var result = _control.TcpCheckConnect();
            LogMessage?.Invoke(this, $"TcpCheckConnect returned: {result}");
            return Convert.ToInt32(result) != 0;
        }
        catch (Exception ex)
        {
            ErrorOccurred?.Invoke(this, $"TcpCheckConnect failed: {ex.Message}");
            return false;
        }
    }

    public void Disconnect()
    {
        try
        {
            if (_control != null)
            {
                LogMessage?.Invoke(this, "Calling TcpDisConnect()...");
                _control.TcpDisConnect();
            }
        }
        catch (Exception ex)
        {
            ErrorOccurred?.Invoke(this, $"TcpDisConnect failed: {ex.Message}");
        }

        IsConnected = false;
        ConnectionChanged?.Invoke(this, false);
    }

    /// <summary>
    /// Send raw command via TcpSendString
    /// </summary>
    public bool SendCommand(string command)
    {
        if (_control == null)
        {
            ErrorOccurred?.Invoke(this, "Control not initialized");
            return false;
        }

        try
        {
            LogMessage?.Invoke(this, $"TcpSendString: {command}");
            _control.TcpSendString(command);
            return true;
        }
        catch (COMException ex)
        {
            ErrorOccurred?.Invoke(this, $"TcpSendString failed: {ex.Message} (0x{ex.ErrorCode:X8})");
            return false;
        }
        catch (Exception ex)
        {
            ErrorOccurred?.Invoke(this, $"TcpSendString failed: {ex.Message}");
            return false;
        }
    }

    /// <summary>
    /// Add hop file: ADD_HOP_FILE;edge;filename
    /// </summary>
    public bool AddHopFile(string edge, string filename)
    {
        string command = $"ADD_HOP_FILE;{edge};{filename}";
        return SendCommand(command);
    }

    /// <summary>
    /// Remove hop file: REMOVE_HOP_FILE;filename
    /// </summary>
    public bool RemoveHopFile(string filename)
    {
        string command = $"REMOVE_HOP_FILE;{filename}";
        return SendCommand(command);
    }

    /// <summary>
    /// Get hop file: GET_HOP_FILE;filename
    /// </summary>
    public bool GetHopFile(string filename)
    {
        string command = $"GET_HOP_FILE;{filename}";
        return SendCommand(command);
    }

    /// <summary>
    /// Activate: ACTIV;table;state
    /// </summary>
    public bool Activ(string table, int state)
    {
        string command = $"ACTIV;{table};{state}";
        return SendCommand(command);
    }

    /// <summary>
    /// Set bit: SET_BIT;address;value
    /// </summary>
    public bool SetBit(int address, int value)
    {
        string command = $"SET_BIT;{address};{value}";
        return SendCommand(command);
    }

    /// <summary>
    /// Set byte: SET_BYTE;address;value
    /// </summary>
    public bool SetByte(int address, int value)
    {
        string command = $"SET_BYTE;{address};{value}";
        return SendCommand(command);
    }

    /// <summary>
    /// Set int: SET_INT;address;value
    /// </summary>
    public bool SetInt(int address, int value)
    {
        string command = $"SET_INT;{address};{value}";
        return SendCommand(command);
    }

    /// <summary>
    /// Set float: SET_FLOAT;address;value
    /// </summary>
    public bool SetFloat(int address, float value)
    {
        string command = $"SET_FLOAT;{address};{value:F2}";
        return SendCommand(command);
    }

    /// <summary>
    /// Receive response string
    /// </summary>
    public string? ReceiveString()
    {
        if (_control == null) return null;

        try
        {
            string result = _control.TcpReceiveString();
            if (!string.IsNullOrEmpty(result))
            {
                LogMessage?.Invoke(this, $"TcpReceiveString: {result}");
            }
            return result;
        }
        catch (Exception ex)
        {
            ErrorOccurred?.Invoke(this, $"TcpReceiveString failed: {ex.Message}");
            return null;
        }
    }

    public void Dispose()
    {
        Disconnect();

        if (_control != null)
        {
            try
            {
                Marshal.ReleaseComObject(_control);
            }
            catch { }
            _control = null;
        }
    }
}
