namespace BZManualClient;

partial class MainForm
{
    private System.ComponentModel.IContainer components = null;

    protected override void Dispose(bool disposing)
    {
        if (disposing && (components != null))
        {
            components.Dispose();
        }
        base.Dispose(disposing);
    }

    private void InitializeComponent()
    {
        grpConnection = new GroupBox();
        lblHost = new Label();
        txtHost = new TextBox();
        lblPort = new Label();
        txtPort = new TextBox();
        btnConnect = new Button();
        btnDisconnect = new Button();
        lblStatusLabel = new Label();
        lblStatus = new Label();

        grpHopFile = new GroupBox();
        lblEdge = new Label();
        txtEdge = new TextBox();
        lblFilename = new Label();
        txtFilename = new TextBox();
        btnBrowse = new Button();
        btnAddHopFile = new Button();

        grpActiv = new GroupBox();
        lblActivTable = new Label();
        txtActivTable = new TextBox();
        lblActivState = new Label();
        txtActivState = new TextBox();
        btnActiv = new Button();

        grpCustom = new GroupBox();
        txtCustomCommand = new TextBox();
        btnSendCustom = new Button();

        grpLog = new GroupBox();
        txtLog = new TextBox();
        btnClearLog = new Button();

        SuspendLayout();
        ClientSize = new Size(550, 520);
        Text = "BZManual Client";
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;

        // Connection Group
        grpConnection.Location = new Point(12, 12);
        grpConnection.Size = new Size(520, 75);
        grpConnection.Text = "Connection (BZManualX.ocx)";

        lblHost.Location = new Point(10, 28);
        lblHost.Size = new Size(35, 20);
        lblHost.Text = "Host:";

        txtHost.Location = new Point(50, 25);
        txtHost.Size = new Size(120, 23);

        lblPort.Location = new Point(180, 28);
        lblPort.Size = new Size(35, 20);
        lblPort.Text = "Port:";

        txtPort.Location = new Point(215, 25);
        txtPort.Size = new Size(60, 23);

        btnConnect.Location = new Point(300, 24);
        btnConnect.Size = new Size(80, 25);
        btnConnect.Text = "Connect";
        btnConnect.Click += btnConnect_Click;

        btnDisconnect.Location = new Point(385, 24);
        btnDisconnect.Size = new Size(80, 25);
        btnDisconnect.Text = "Disconnect";
        btnDisconnect.Enabled = false;
        btnDisconnect.Click += btnDisconnect_Click;

        lblStatusLabel.Location = new Point(10, 52);
        lblStatusLabel.Size = new Size(45, 20);
        lblStatusLabel.Text = "Status:";

        lblStatus.Location = new Point(60, 52);
        lblStatus.Size = new Size(100, 20);
        lblStatus.Text = "Disconnected";
        lblStatus.ForeColor = Color.Red;
        lblStatus.Font = new Font(lblStatus.Font, FontStyle.Bold);

        grpConnection.Controls.AddRange(new Control[] {
            lblHost, txtHost, lblPort, txtPort, btnConnect, btnDisconnect, lblStatusLabel, lblStatus
        });

        // Add Hop File Group
        grpHopFile.Location = new Point(12, 93);
        grpHopFile.Size = new Size(520, 85);
        grpHopFile.Text = "Add Hop File (ADD_HOP_FILE;edge;filename)";

        lblEdge.Location = new Point(10, 25);
        lblEdge.Size = new Size(40, 20);
        lblEdge.Text = "Edge:";

        txtEdge.Location = new Point(55, 22);
        txtEdge.Size = new Size(50, 23);

        lblFilename.Location = new Point(115, 25);
        lblFilename.Size = new Size(60, 20);
        lblFilename.Text = "Filename:";

        txtFilename.Location = new Point(175, 22);
        txtFilename.Size = new Size(240, 23);

        btnBrowse.Location = new Point(420, 21);
        btnBrowse.Size = new Size(30, 25);
        btnBrowse.Text = "...";
        btnBrowse.Click += btnBrowse_Click;

        btnAddHopFile.Location = new Point(175, 52);
        btnAddHopFile.Size = new Size(120, 25);
        btnAddHopFile.Text = "Send";
        btnAddHopFile.Enabled = false;
        btnAddHopFile.Click += btnAddHopFile_Click;

        grpHopFile.Controls.AddRange(new Control[] {
            lblEdge, txtEdge, lblFilename, txtFilename, btnBrowse, btnAddHopFile
        });

        // Activ Group
        grpActiv.Location = new Point(12, 184);
        grpActiv.Size = new Size(520, 55);
        grpActiv.Text = "Activ (ACTIV;table;state)";

        lblActivTable.Location = new Point(10, 22);
        lblActivTable.Size = new Size(40, 20);
        lblActivTable.Text = "Table:";

        txtActivTable.Location = new Point(55, 19);
        txtActivTable.Size = new Size(50, 23);

        lblActivState.Location = new Point(115, 22);
        lblActivState.Size = new Size(40, 20);
        lblActivState.Text = "State:";

        txtActivState.Location = new Point(160, 19);
        txtActivState.Size = new Size(50, 23);

        btnActiv.Location = new Point(230, 18);
        btnActiv.Size = new Size(80, 25);
        btnActiv.Text = "Send";
        btnActiv.Enabled = false;
        btnActiv.Click += btnActiv_Click;

        grpActiv.Controls.AddRange(new Control[] {
            lblActivTable, txtActivTable, lblActivState, txtActivState, btnActiv
        });

        // Custom Command Group
        grpCustom.Location = new Point(12, 245);
        grpCustom.Size = new Size(520, 55);
        grpCustom.Text = "Custom Command";

        txtCustomCommand.Location = new Point(10, 19);
        txtCustomCommand.Size = new Size(400, 23);

        btnSendCustom.Location = new Point(420, 18);
        btnSendCustom.Size = new Size(80, 25);
        btnSendCustom.Text = "Send";
        btnSendCustom.Enabled = false;
        btnSendCustom.Click += btnSendCustom_Click;

        grpCustom.Controls.AddRange(new Control[] {
            txtCustomCommand, btnSendCustom
        });

        // Log Group
        grpLog.Location = new Point(12, 306);
        grpLog.Size = new Size(520, 205);
        grpLog.Text = "Log";

        txtLog.Location = new Point(10, 22);
        txtLog.Size = new Size(500, 140);
        txtLog.Multiline = true;
        txtLog.ScrollBars = ScrollBars.Vertical;
        txtLog.ReadOnly = true;
        txtLog.Font = new Font("Consolas", 9);

        btnClearLog.Location = new Point(10, 170);
        btnClearLog.Size = new Size(80, 25);
        btnClearLog.Text = "Clear Log";
        btnClearLog.Click += btnClearLog_Click;

        grpLog.Controls.AddRange(new Control[] {
            txtLog, btnClearLog
        });

        Controls.AddRange(new Control[] {
            grpConnection, grpHopFile, grpActiv, grpCustom, grpLog
        });

        ResumeLayout(false);
    }

    private GroupBox grpConnection;
    private Label lblHost;
    private TextBox txtHost;
    private Label lblPort;
    private TextBox txtPort;
    private Button btnConnect;
    private Button btnDisconnect;
    private Label lblStatusLabel;
    private Label lblStatus;

    private GroupBox grpHopFile;
    private Label lblEdge;
    private TextBox txtEdge;
    private Label lblFilename;
    private TextBox txtFilename;
    private Button btnBrowse;
    private Button btnAddHopFile;

    private GroupBox grpActiv;
    private Label lblActivTable;
    private TextBox txtActivTable;
    private Label lblActivState;
    private TextBox txtActivState;
    private Button btnActiv;

    private GroupBox grpCustom;
    private TextBox txtCustomCommand;
    private Button btnSendCustom;

    private GroupBox grpLog;
    private TextBox txtLog;
    private Button btnClearLog;
}
