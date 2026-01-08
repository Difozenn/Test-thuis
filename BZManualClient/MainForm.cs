namespace BZManualClient;

public partial class MainForm : Form
{
    private readonly BZManualComClient _client;

    public MainForm()
    {
        InitializeComponent();

        _client = new BZManualComClient();
        _client.ConnectionChanged += OnConnectionChanged;
        _client.ErrorOccurred += OnError;
        _client.LogMessage += OnLogMessage;

        // Set defaults
        txtHost.Text = "127.0.0.1";
        txtPort.Text = "100";
        txtEdge.Text = "CH";
        txtActivTable.Text = "D";
        txtActivState.Text = "1";

        UpdateConnectionStatus();
    }

    private void OnConnectionChanged(object? sender, bool connected)
    {
        if (InvokeRequired)
        {
            Invoke(() => OnConnectionChanged(sender, connected));
            return;
        }
        UpdateConnectionStatus();
    }

    private void OnError(object? sender, string error)
    {
        if (InvokeRequired)
        {
            Invoke(() => OnError(sender, error));
            return;
        }
        Log($"ERROR: {error}");
    }

    private void OnLogMessage(object? sender, string message)
    {
        if (InvokeRequired)
        {
            Invoke(() => OnLogMessage(sender, message));
            return;
        }
        Log(message);
    }

    private void UpdateConnectionStatus()
    {
        bool connected = _client.IsConnected;
        lblStatus.Text = connected ? "Connected" : "Disconnected";
        lblStatus.ForeColor = connected ? Color.Green : Color.Red;
        btnConnect.Enabled = !connected;
        btnDisconnect.Enabled = connected;

        btnAddHopFile.Enabled = connected;
        btnActiv.Enabled = connected;
        btnSendCustom.Enabled = connected;
    }

    private void Log(string message)
    {
        txtLog.AppendText($"[{DateTime.Now:HH:mm:ss}] {message}{Environment.NewLine}");
        txtLog.ScrollToCaret();
    }

    private void btnConnect_Click(object sender, EventArgs e)
    {
        _client.Configure(txtHost.Text, int.Parse(txtPort.Text));
        Log($"Connecting to {txtHost.Text}:{txtPort.Text} via BZManualX.ocx...");
        _client.Connect();
    }

    private void btnDisconnect_Click(object sender, EventArgs e)
    {
        _client.Disconnect();
    }

    private void btnBrowse_Click(object sender, EventArgs e)
    {
        using var dialog = new OpenFileDialog();
        dialog.Title = "Select Hop File";
        dialog.Filter = "All files (*.*)|*.*";
        if (dialog.ShowDialog() == DialogResult.OK)
        {
            txtFilename.Text = dialog.FileName;
        }
    }

    private void btnAddHopFile_Click(object sender, EventArgs e)
    {
        if (string.IsNullOrWhiteSpace(txtFilename.Text))
        {
            MessageBox.Show("Please select a file first", "Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        _client.AddHopFile(txtEdge.Text, txtFilename.Text);
    }

    private void btnActiv_Click(object sender, EventArgs e)
    {
        int state = int.Parse(txtActivState.Text);
        _client.Activ(txtActivTable.Text, state);
    }

    private void btnSendCustom_Click(object sender, EventArgs e)
    {
        if (string.IsNullOrWhiteSpace(txtCustomCommand.Text))
            return;

        _client.SendCommand(txtCustomCommand.Text);
    }

    private void btnClearLog_Click(object sender, EventArgs e)
    {
        txtLog.Clear();
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        _client.Dispose();
        base.OnFormClosing(e);
    }
}
