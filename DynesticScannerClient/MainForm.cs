using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace BzmScannerClient
{
    public class MainForm : Form
    {
        private readonly BzmTcpClient _bzm = new();
        private readonly RawInputScanner _scanner = new();
        private ScannerConfig _config = null!;

        // --- Sequential scan state ---
        private string? _pendingHopFile;
        private bool _tableActive;  // tracks ACTIV toggle state

        // --- Status polling ---
        private System.Windows.Forms.Timer? _pollTimer;
        private Label lblMachineState = null!;

        // System tray
        private NotifyIcon _trayIcon = null!;
        private ContextMenuStrip _trayMenu = null!;

        // Connection controls
        private TextBox txtIp = null!;
        private TextBox txtPort = null!;
        private Button btnConnect = null!;
        private Button btnSetLocal = null!;
        private Label lblStatus = null!;

        // Settings
        private NumericUpDown nudCount = null!;
        private Button btnEditConfig = null!;
        private Button btnPickScanner = null!;
        private Label lblScanner = null!;

        // Scanner input
        private TextBox txtScanInput = null!;
        private Label lblScanState = null!;
        private Label lblLastScan = null!;
        private Button btnCancelScan = null!;

        // Command buttons
        private Button btnActiv = null!;
        private Button btnDeactiv = null!;
        private Button btnRemoveHop = null!;
        private Button btnGetStatus = null!;
        private Button btnVacuumOn = null!;
        private Button btnMachineStart = null!;
        private Button btnScanPlc = null!;
        private Button btnSendRaw = null!;
        private TextBox txtRawCommand = null!;

        // Log
        private TextBox txtLog = null!;
        private Button btnClearLog = null!;

        // Header
        private Panel pnlHeader = null!;
        private Label lblTitle = null!;
        private Label lblCopyright = null!;

        // ================================================================
        //  Theme Colors
        // ================================================================

        private static readonly Color ClrFormBg          = Color.White;
        private static readonly Color ClrHeaderBg        = ColorTranslator.FromHtml("#1E3A5F");
        private static readonly Color ClrHeaderText      = Color.White;
        private static readonly Color ClrSectionBg       = ColorTranslator.FromHtml("#F5F6F8");
        private static readonly Color ClrSectionAccent   = ColorTranslator.FromHtml("#2D5F8A");
        private static readonly Color ClrBorder          = ColorTranslator.FromHtml("#E0E0E0");
        private static readonly Color ClrTextPrimary     = ColorTranslator.FromHtml("#1A1A1A");
        private static readonly Color ClrTextSecondary   = ColorTranslator.FromHtml("#6B7280");
        private static readonly Color ClrPrimaryBtn      = ColorTranslator.FromHtml("#2D5F8A");
        private static readonly Color ClrPrimaryBtnText  = Color.White;
        private static readonly Color ClrSecondaryBtn    = ColorTranslator.FromHtml("#E8EAED");
        private static readonly Color ClrSecondaryText   = ColorTranslator.FromHtml("#1A1A1A");
        private static readonly Color ClrAccentGreen     = ColorTranslator.FromHtml("#2D7D46");
        private static readonly Color ClrAccentRed       = ColorTranslator.FromHtml("#C0392B");
        private static readonly Color ClrWarningOrange   = ColorTranslator.FromHtml("#D97706");
        private static readonly Color ClrToggleActive    = ColorTranslator.FromHtml("#2D7D46");
        private static readonly Color ClrToggleInactive  = ColorTranslator.FromHtml("#9CA3AF");
        private static readonly Color ClrInputHighlight  = ColorTranslator.FromHtml("#FEF3C7");
        private static readonly Color ClrInputDanger     = ColorTranslator.FromHtml("#FEE2E2");

        private enum ButtonCategory
        {
            Primary,
            Secondary,
            Danger,
            ToggleActive,
            ToggleInactive
        }

        public MainForm()
        {
            _config = ScannerConfig.Load();
            InitializeControls();
            InitializeTray();
            WireEvents();
            UpdateScanStateDisplay();
            UpdateActivButton();
        }

        // ================================================================
        //  UI Setup
        // ================================================================

        private void InitializeControls()
        {
            Text = "Dynestic Scanner Client";
            Size = new Size(820, 850);
            MinimumSize = new Size(820, 850);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Segoe UI", 9f);
            BackColor = ClrFormBg;
            SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint, true);

            // === Header Bar ===
            pnlHeader = new Panel
            {
                Dock = DockStyle.Top,
                Height = 48,
                BackColor = ClrHeaderBg
            };

            lblTitle = new Label
            {
                Text = "Dynestic Scanner Client",
                ForeColor = ClrHeaderText,
                BackColor = ClrHeaderBg,
                Font = new Font("Segoe UI Semibold", 14f),
                AutoSize = true
            };
            lblTitle.Location = new Point(16, (48 - lblTitle.PreferredHeight) / 2);
            pnlHeader.Controls.Add(lblTitle);

            Controls.Add(pnlHeader);

            lblCopyright = new Label
            {
                Text = "\u00A9 RVL 2026",
                ForeColor = ClrHeaderText,
                BackColor = ClrHeaderBg,
                Font = new Font("Segoe UI", 8f),
                AutoSize = true,
                Anchor = AnchorStyles.Top | AnchorStyles.Right
            };
            lblCopyright.Location = new Point(pnlHeader.Width - lblCopyright.PreferredWidth - 16, (48 - lblCopyright.PreferredHeight) / 2);
            pnlHeader.Controls.Add(lblCopyright);

            int y = 48 + 10;

            // === Connection Section ===
            var (connOuter, connContent) = CreateSectionPanel("Connection", y, 70);
            connContent.Controls.Add(new Label { Text = "IP:", Location = new Point(0, 5), AutoSize = true, BackColor = ClrSectionBg, ForeColor = ClrTextPrimary });
            txtIp = new TextBox { Text = _config.DefaultIp, Location = new Point(24, 2), Width = 130 };
            StyleTextBox(txtIp);
            connContent.Controls.Add(txtIp);

            connContent.Controls.Add(new Label { Text = "Port:", Location = new Point(166, 5), AutoSize = true, BackColor = ClrSectionBg, ForeColor = ClrTextPrimary });
            txtPort = new TextBox { Text = _config.DefaultPort.ToString(), Location = new Point(204, 2), Width = 65 };
            StyleTextBox(txtPort);
            connContent.Controls.Add(txtPort);

            btnConnect = CreateFlatButton("Connect", 90, ButtonCategory.Primary);
            btnConnect.Location = new Point(286, 0);
            connContent.Controls.Add(btnConnect);

            btnSetLocal = CreateFlatButton("Set Local", 85, ButtonCategory.Secondary);
            btnSetLocal.Location = new Point(386, 0);
            btnSetLocal.Click += (s, e) =>
            {
                txtIp.Text = "127.0.0.1";
                txtPort.Text = _config.DefaultPort.ToString();
            };
            connContent.Controls.Add(btnSetLocal);

            lblStatus = new Label
            {
                Text = "Disconnected",
                ForeColor = ClrAccentRed,
                Location = new Point(490, 5),
                AutoSize = true,
                Font = new Font("Segoe UI", 9f, FontStyle.Bold),
                BackColor = ClrSectionBg
            };
            connContent.Controls.Add(lblStatus);
            Controls.Add(connOuter);
            y += 70 + 10;

            // === Machine State Section ===
            var (machOuter, machContent) = CreateSectionPanel("Machine State (live)", y, 56);
            lblMachineState = new Label
            {
                Text = "-- not polling --",
                Location = new Point(0, 2),
                Size = new Size(machContent.Width, 20),
                Font = new Font("Consolas", 9f, FontStyle.Bold),
                ForeColor = ClrTextSecondary,
                BackColor = ClrSectionBg,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            machContent.Controls.Add(lblMachineState);
            Controls.Add(machOuter);
            y += 56 + 10;

            // === Scanner Device Section ===
            var (devOuter, devContent) = CreateSectionPanel("Scanner Device", y, 68);
            lblScanner = new Label
            {
                Text = "No scanner selected",
                Location = new Point(0, 4),
                Size = new Size(devContent.Width - 155, 20),
                ForeColor = ClrTextSecondary,
                BackColor = ClrSectionBg,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            devContent.Controls.Add(lblScanner);

            btnPickScanner = CreateFlatButton("Select Scanner", 140, ButtonCategory.Secondary);
            btnPickScanner.Location = new Point(devContent.Width - 145, 0);
            btnPickScanner.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            devContent.Controls.Add(btnPickScanner);
            Controls.Add(devOuter);
            y += 68 + 10;

            // === Settings Section ===
            var (setOuter, setContent) = CreateSectionPanel($"Settings  (Table: {_config.DefaultTable})", y, 68);
            setContent.Controls.Add(new Label { Text = "Count:", Location = new Point(0, 5), AutoSize = true, BackColor = ClrSectionBg, ForeColor = ClrTextPrimary });
            nudCount = new NumericUpDown
            {
                Minimum = 1,
                Maximum = 9999,
                Value = 1,
                Location = new Point(48, 2),
                Width = 60
            };
            setContent.Controls.Add(nudCount);

            var mappingInfo = new Label
            {
                Text = GetMappingSummary(),
                Location = new Point(128, 5),
                AutoSize = true,
                ForeColor = ClrTextSecondary,
                Font = new Font("Segoe UI", 8f),
                BackColor = ClrSectionBg
            };
            setContent.Controls.Add(mappingInfo);

            btnEditConfig = CreateFlatButton("Edit Config", 105, ButtonCategory.Secondary);
            btnEditConfig.Location = new Point(setContent.Width - 110, 0);
            btnEditConfig.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            setContent.Controls.Add(btnEditConfig);
            Controls.Add(setOuter);
            y += 68 + 10;

            // === Scanner Input Section ===
            var (scanOuter, scanContent) = CreateSectionPanel("Scanner Input", y, 88);
            lblScanState = new Label
            {
                Text = "",
                Location = new Point(0, 0),
                Size = new Size(0, 0),
                Visible = false
            };

            txtScanInput = new TextBox
            {
                Location = new Point(0, 0),
                Width = scanContent.Width - 68,
                Font = new Font("Consolas", 12f),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            StyleTextBox(txtScanInput);
            scanContent.Controls.Add(txtScanInput);

            btnCancelScan = CreateFlatButton("Cancel", 55, ButtonCategory.Danger);
            btnCancelScan.Location = new Point(scanContent.Width - 58, 0);
            btnCancelScan.Visible = false;
            btnCancelScan.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            scanContent.Controls.Add(btnCancelScan);


            lblLastScan = new Label
            {
                Text = "",
                Location = new Point(0, 32),
                Size = new Size(scanContent.Width, 18),
                ForeColor = ClrAccentGreen,
                Font = new Font("Segoe UI", 8f, FontStyle.Italic),
                BackColor = ClrSectionBg,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            scanContent.Controls.Add(lblLastScan);
            Controls.Add(scanOuter);
            y += 88 + 10;

            // === Manual Commands Section ===
            var (cmdOuter, cmdContent) = CreateSectionPanel("Manual Commands", y, 108);
            int bx = 0;

            btnActiv = CreateFlatButton("ACTIV", 90, ButtonCategory.ToggleActive);
            btnActiv.Location = new Point(bx, 0);
            cmdContent.Controls.Add(btnActiv);
            bx += 98;

            btnDeactiv = CreateFlatButton("DEACTIV", 90, ButtonCategory.Secondary);
            btnDeactiv.Location = new Point(bx, 0);
            cmdContent.Controls.Add(btnDeactiv);
            bx += 98;

            btnRemoveHop = CreateFlatButton("Remove Hop", 105, ButtonCategory.Secondary);
            btnRemoveHop.Location = new Point(bx, 0);
            cmdContent.Controls.Add(btnRemoveHop);
            bx += 113;

            btnGetStatus = CreateFlatButton("Get Status", 95, ButtonCategory.Secondary);
            btnGetStatus.Location = new Point(bx, 0);
            cmdContent.Controls.Add(btnGetStatus);
            bx += 103;

            btnVacuumOn = CreateFlatButton("Vacuum OFF", 100, ButtonCategory.ToggleInactive);
            btnVacuumOn.Location = new Point(bx, 0);
            btnVacuumOn.Enabled = false;
            btnVacuumOn.BackColor = ClrBorder;
            cmdContent.Controls.Add(btnVacuumOn);
            bx += 108;

            btnMachineStart = CreateFlatButton("Machine Start", 115, ButtonCategory.Primary);
            btnMachineStart.Location = new Point(bx, 0);
            btnMachineStart.Enabled = false;
            btnMachineStart.BackColor = ClrBorder;
            cmdContent.Controls.Add(btnMachineStart);
            bx += 123;

            btnScanPlc = CreateFlatButton("Scan PLC", 85, ButtonCategory.Secondary);
            btnScanPlc.Location = new Point(bx, 0);
            cmdContent.Controls.Add(btnScanPlc);

            cmdContent.Controls.Add(new Label { Text = "Raw:", Location = new Point(0, 40), AutoSize = true, BackColor = ClrSectionBg, ForeColor = ClrTextPrimary });
            txtRawCommand = new TextBox { Location = new Point(38, 37), Width = cmdContent.Width - 120, Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right };
            StyleTextBox(txtRawCommand);
            cmdContent.Controls.Add(txtRawCommand);

            btnSendRaw = CreateFlatButton("Send", 70, ButtonCategory.Secondary);
            btnSendRaw.Location = new Point(cmdContent.Width - 70, 36);
            btnSendRaw.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            cmdContent.Controls.Add(btnSendRaw);
            Controls.Add(cmdOuter);
            y += 108 + 10;

            // === Response Log Section (fills remaining space) ===
            int logHeight = ClientSize.Height - y - 10;
            var (logOuter, logContent) = CreateSectionPanel("Response Log", y, logHeight);
            logOuter.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            logContent.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;

            txtLog = new TextBox
            {
                Multiline = true,
                ReadOnly = true,
                ScrollBars = ScrollBars.Vertical,
                Location = new Point(0, 0),
                Size = new Size(logContent.Width - 75, logContent.Height),
                Font = new Font("Consolas", 9f),
                BackColor = Color.White,
                BorderStyle = BorderStyle.FixedSingle,
                Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
            };
            logContent.Controls.Add(txtLog);

            btnClearLog = CreateFlatButton("Clear", 65, ButtonCategory.Secondary);
            btnClearLog.Location = new Point(logContent.Width - 68, 0);
            btnClearLog.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            logContent.Controls.Add(btnClearLog);
            Controls.Add(logOuter);
        }

        private (Panel outer, Panel content) CreateSectionPanel(string title, int y, int height)
        {
            int accentWidth = 4;
            int titleHeight = 24;
            int padding = 12;
            int panelWidth = ClientSize.Width - 24;

            var outer = new Panel
            {
                Location = new Point(12, y),
                Size = new Size(panelWidth, height),
                BackColor = ClrSectionBg,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };

            var accent = new Panel
            {
                Location = new Point(0, 0),
                Size = new Size(accentWidth, height),
                BackColor = ClrSectionAccent,
                Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left
            };
            outer.Controls.Add(accent);

            var sectionTitle = new Label
            {
                Text = title,
                Location = new Point(accentWidth + padding, 6),
                AutoSize = true,
                Font = new Font("Segoe UI", 9f, FontStyle.Bold),
                ForeColor = ClrTextPrimary,
                BackColor = ClrSectionBg
            };
            outer.Controls.Add(sectionTitle);

            var content = new Panel
            {
                Location = new Point(accentWidth + padding, titleHeight + 4),
                Size = new Size(panelWidth - accentWidth - padding - padding, height - titleHeight - 4 - 8),
                BackColor = ClrSectionBg,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            outer.Controls.Add(content);

            return (outer, content);
        }

        private Button CreateFlatButton(string text, int width, ButtonCategory category)
        {
            var btn = new Button
            {
                Text = text,
                Width = width,
                Height = 32,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Segoe UI", 9f),
                Cursor = Cursors.Hand,
                TextAlign = ContentAlignment.MiddleCenter
            };

            btn.FlatAppearance.BorderSize = 1;

            switch (category)
            {
                case ButtonCategory.Primary:
                    btn.BackColor = ClrPrimaryBtn;
                    btn.ForeColor = ClrPrimaryBtnText;
                    btn.FlatAppearance.BorderColor = ClrPrimaryBtn;
                    btn.FlatAppearance.MouseOverBackColor = ControlPaint.Light(ClrPrimaryBtn, 0.3f);
                    btn.FlatAppearance.MouseDownBackColor = ControlPaint.Dark(ClrPrimaryBtn, 0.1f);
                    break;
                case ButtonCategory.Secondary:
                    btn.BackColor = ClrSecondaryBtn;
                    btn.ForeColor = ClrSecondaryText;
                    btn.FlatAppearance.BorderColor = ClrBorder;
                    btn.FlatAppearance.MouseOverBackColor = ControlPaint.Dark(ClrSecondaryBtn, 0.05f);
                    btn.FlatAppearance.MouseDownBackColor = ControlPaint.Dark(ClrSecondaryBtn, 0.1f);
                    break;
                case ButtonCategory.Danger:
                    btn.BackColor = ClrAccentRed;
                    btn.ForeColor = Color.White;
                    btn.FlatAppearance.BorderColor = ClrAccentRed;
                    btn.FlatAppearance.MouseOverBackColor = ControlPaint.Light(ClrAccentRed, 0.3f);
                    btn.FlatAppearance.MouseDownBackColor = ControlPaint.Dark(ClrAccentRed, 0.1f);
                    break;
                case ButtonCategory.ToggleActive:
                    btn.BackColor = ClrToggleActive;
                    btn.ForeColor = Color.White;
                    btn.FlatAppearance.BorderColor = ClrToggleActive;
                    btn.FlatAppearance.MouseOverBackColor = ControlPaint.Light(ClrToggleActive, 0.3f);
                    btn.FlatAppearance.MouseDownBackColor = ControlPaint.Dark(ClrToggleActive, 0.1f);
                    break;
                case ButtonCategory.ToggleInactive:
                    btn.BackColor = ClrToggleInactive;
                    btn.ForeColor = Color.White;
                    btn.FlatAppearance.BorderColor = ClrToggleInactive;
                    btn.FlatAppearance.MouseOverBackColor = ControlPaint.Light(ClrToggleInactive, 0.3f);
                    btn.FlatAppearance.MouseDownBackColor = ControlPaint.Dark(ClrToggleInactive, 0.1f);
                    break;
            }

            return btn;
        }

        private static void StyleTextBox(TextBox tb)
        {
            tb.BorderStyle = BorderStyle.FixedSingle;
        }

        private void InitializeTray()
        {
            _trayMenu = new ContextMenuStrip();
            _trayMenu.Items.Add("Show", null, (s, e) => ShowFromTray());
            _trayMenu.Items.Add("-");
            _trayMenu.Items.Add("Exit", null, (s, e) => { _trayIcon.Visible = false; Application.Exit(); });

            _trayIcon = new NotifyIcon
            {
                Text = "Dynestic Scanner Client",
                Icon = SystemIcons.Application,
                ContextMenuStrip = _trayMenu,
                Visible = false
            };
            _trayIcon.DoubleClick += (s, e) => ShowFromTray();
        }

        private void WireEvents()
        {
            btnConnect.Click += BtnConnect_Click;
            txtScanInput.KeyDown += TxtScanInput_KeyDown;
            txtRawCommand.KeyDown += TxtRawCommand_KeyDown;
            btnCancelScan.Click += (s, e) => CancelPendingScan();
            btnPickScanner.Click += BtnPickScanner_Click;

            btnActiv.Click += (s, e) =>
            {
                _tableActive = !_tableActive;
                SendCommand(BzmCommands.Activate(_config.DefaultTable, _tableActive ? 1 : 0));
                Log($"[Table {_config.DefaultTable} {(_tableActive ? "ACTIVATED" : "DEACTIVATED")}]");
                UpdateActivButton();
            };
            btnDeactiv.Click += (s, e) =>
            {
                _tableActive = false;
                SendCommand(BzmCommands.Activate(_config.DefaultTable, 0));
                UpdateActivButton();
            };
            btnRemoveHop.Click += (s, e) =>
            {
                Log("[Remove: scan edge barcode to specify which edge to remove from]");
                _pendingHopFile = "__REMOVE__";
                UpdateScanStateDisplay();
            };
            btnGetStatus.Click += (s, e) => SendCommand(BzmCommands.GetStatus(_config.DefaultTable));
            // Vacuum and Machine Start disabled — PLC bit addresses unknown for this machine
            btnScanPlc.Click += (s, e) => ScanPlcBytes();
            btnSendRaw.Click += (s, e) => SendRawCommand();
            btnClearLog.Click += (s, e) => txtLog.Clear();
            btnEditConfig.Click += BtnEditConfig_Click;

            _bzm.DataReceived += OnDataReceived;
            _bzm.Disconnected += msg =>
            {
                Invoke(() =>
                {
                    StopStatusPolling();
                    lblStatus.Text = "Disconnected";
                    lblStatus.ForeColor = ClrAccentRed;
                    btnConnect.Text = "Connect";
                    Log($"[Disconnected] {msg}");
                });
            };

            // Raw Input: barcode scanned from USB device in background
            _scanner.BarcodeScanned += barcode =>
            {
                Invoke(() =>
                {
                    lblLastScan.Text = $"Last scan: {barcode}";
                    Log($"[SCAN] {barcode}");
                    ProcessScanInput(barcode);
                });
            };

            // Return focus to scanner input after button clicks
            WireFocusRestoration(Controls);

            Shown += MainForm_Shown;
        }

        private void WireFocusRestoration(Control.ControlCollection controls)
        {
            foreach (Control c in controls)
            {
                if (c is Button btn && btn != btnConnect && btn != btnSetLocal && btn != btnEditConfig && btn != btnPickScanner)
                {
                    btn.GotFocus += (s, e) =>
                        BeginInvoke(new Action(() => txtScanInput.Focus()));
                }

                if (c is Panel && c.HasChildren)
                {
                    WireFocusRestoration(c.Controls);
                }
            }
        }


        // ================================================================
        //  Form Lifecycle
        // ================================================================

        private void MainForm_Shown(object? sender, EventArgs e)
        {
            txtScanInput.Focus();

            // Try to restore saved scanner device
            if (!string.IsNullOrEmpty(_config.ScannerDevicePath))
            {
                if (_scanner.SelectDeviceByPath(_config.ScannerDevicePath, Handle))
                {
                    lblScanner.Text = TruncateDevicePath(_config.ScannerDevicePath);
                    lblScanner.ForeColor = ClrAccentGreen;
                    Log("[Scanner device restored from config]");
                }
                else
                {
                    Log("[Saved scanner device not found — click 'Select Scanner' to pick one]");
                    lblScanner.Text = "Saved device not found";
                    lblScanner.ForeColor = ClrAccentRed;
                }
            }
            else
            {
                Log("[No scanner device configured — click 'Select Scanner' to pick one]");
            }
        }

        /// <summary>Minimize to system tray instead of taskbar.</summary>
        protected override void OnResize(EventArgs e)
        {
            base.OnResize(e);
            if (WindowState == FormWindowState.Minimized)
            {
                Hide();
                _trayIcon.Visible = true;
                _trayIcon.ShowBalloonTip(2000, "Dynestic Scanner",
                    "Running in background. Scanner is still active.", ToolTipIcon.Info);
            }
        }

        private void ShowFromTray()
        {
            Show();
            WindowState = FormWindowState.Normal;
            _trayIcon.Visible = false;
            BringToFront();
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            StopStatusPolling();
            _trayIcon.Visible = false;
            _trayIcon.Dispose();
            _scanner.Dispose();
            _bzm.Dispose();
            base.OnFormClosing(e);
        }

        /// <summary>
        /// Override WndProc to pass WM_INPUT messages to the RawInput scanner.
        /// This is what makes background scanning work.
        /// </summary>
        protected override void WndProc(ref Message m)
        {
            if (m.Msg == RawInputScanner.WM_INPUT_MSG)
            {
                _scanner.ProcessRawInput(m);
            }
            base.WndProc(ref m);
        }

        // ================================================================
        //  Scanner Device Picker
        // ================================================================

        private void BtnPickScanner_Click(object? sender, EventArgs e)
        {
            var devices = RawInputScanner.GetKeyboardDevices();
            if (devices.Count == 0)
            {
                MessageBox.Show("No keyboard/scanner HID devices found.", "No Devices",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            using var picker = new Form
            {
                Text = "Select Scanner Device",
                Size = new Size(600, 350),
                StartPosition = FormStartPosition.CenterParent,
                FormBorderStyle = FormBorderStyle.FixedDialog,
                MaximizeBox = false,
                MinimizeBox = false
            };

            var lbl = new Label
            {
                Text = "Select the USB barcode scanner from the list below.\n" +
                       "Tip: unplug the scanner, note which entry disappears, plug it back in.",
                Location = new Point(12, 12),
                Size = new Size(560, 40)
            };
            picker.Controls.Add(lbl);

            var listBox = new ListBox
            {
                Location = new Point(12, 55),
                Size = new Size(560, 210)
            };
            foreach (var d in devices)
                listBox.Items.Add(d);
            if (listBox.Items.Count > 0)
                listBox.SelectedIndex = 0;
            picker.Controls.Add(listBox);

            var btnOk = new Button { Text = "OK", DialogResult = DialogResult.OK, Location = new Point(410, 275), Width = 75 };
            var btnCancel = new Button { Text = "Cancel", DialogResult = DialogResult.Cancel, Location = new Point(495, 275), Width = 75 };
            picker.Controls.Add(btnOk);
            picker.Controls.Add(btnCancel);
            picker.AcceptButton = btnOk;
            picker.CancelButton = btnCancel;

            if (picker.ShowDialog(this) == DialogResult.OK && listBox.SelectedItem is DeviceInfo selected)
            {
                _scanner.SelectDevice(selected.Handle, Handle);
                _config.ScannerDevicePath = selected.DevicePath;
                _config.Save();

                lblScanner.Text = TruncateDevicePath(selected.DevicePath);
                lblScanner.ForeColor = ClrAccentGreen;
                Log($"[Scanner selected: {selected.DisplayName}]");
                Log("[Scanner input is now captured globally — even when minimized]");
            }
        }

        // ================================================================
        //  Sequential Scan State Machine
        // ================================================================

        private void TxtScanInput_KeyDown(object? sender, KeyEventArgs e)
        {
            if (e.KeyCode != Keys.Enter)
                return;

            e.SuppressKeyPress = true;
            string input = txtScanInput.Text.Trim();
            txtScanInput.Clear();

            if (string.IsNullOrEmpty(input))
                return;

            lblLastScan.Text = $"Last scan: {input}";
            ProcessScanInput(input);
        }

        private void ProcessScanInput(string input)
        {
            string upper = input.ToUpperInvariant();

            // --- hhcmd= barcode ---
            if (upper.StartsWith("HHCMD="))
            {
                CancelPendingScan();
                ExecuteCommandFile(input.Substring(6).Trim());
                return;
            }

            // --- Check config mappings ---
            if (_config.IsEdgeMapping(input, out string edge))
            {
                HandleEdgeScan(edge);
                return;
            }

            if (_config.IsCommandMapping(input, out string command))
            {
                HandleCommandScan(command);
                return;
            }

            // --- File path scans ---
            if (upper.EndsWith(".HOP"))
            {
                _pendingHopFile = input;
                Log($"[File queued: {input}]");
                Log("[Waiting for edge barcode...]");
                UpdateScanStateDisplay();
                return;
            }

            if (upper.EndsWith(".JLX"))
            {
                CancelPendingScan();
                SendCommand(BzmCommands.LoadMachineload(input));
                return;
            }

            if (upper.EndsWith(".JOB"))
            {
                CancelPendingScan();
                SendCommand(BzmCommands.LoadJoblist(input));
                return;
            }

            if (upper == "CANCEL")
            {
                CancelPendingScan();
                return;
            }

            // --- Fallback: raw ---
            string raw = input.Replace("|", "\t").Replace(";", "\t");
            SendCommand(raw);
        }

        private void HandleEdgeScan(string edge)
        {
            if (_pendingHopFile == "__REMOVE__")
            {
                SendCommand(BzmCommands.RemoveHopFile(edge));
                Log($"[Removed hop from edge {edge}]");
                _pendingHopFile = null;
                UpdateScanStateDisplay();
            }
            else if (_pendingHopFile != null)
            {
                // Auto-deactivate table before loading new file
                SendCommand(BzmCommands.Activate(_config.DefaultTable, 0));
                _tableActive = false;
                Log($"[Auto-deactivated table {_config.DefaultTable}]");

                string cmd = BzmCommands.AddHopFile(edge, _pendingHopFile, (int)nudCount.Value);
                SendCommand(cmd);
                Log($"[Added {Path.GetFileName(_pendingHopFile)} on edge {edge}]");
                _pendingHopFile = null;
                UpdateScanStateDisplay();
                UpdateActivButton();
            }
            else
            {
                Log($"[Edge {edge} scanned but no hop file pending. Scan a .hop file first.]");
            }
        }

        private void HandleCommandScan(string command)
        {
            switch (command)
            {
                case "ACTIV":
                    // Toggle: if active → deactivate, if inactive → activate
                    _tableActive = !_tableActive;
                    SendCommand(BzmCommands.Activate(_config.DefaultTable, _tableActive ? 1 : 0));
                    Log($"[Table {_config.DefaultTable} {(_tableActive ? "ACTIVATED" : "DEACTIVATED")}]");
                    UpdateActivButton();
                    break;
                case "DEACTIV":
                    _tableActive = false;
                    SendCommand(BzmCommands.Activate(_config.DefaultTable, 0));
                    UpdateActivButton();
                    break;
                case "GET_STATUS":
                    SendCommand(BzmCommands.GetStatus(_config.DefaultTable));
                    break;
                case "REMOVE":
                    CancelPendingScan();
                    Log("[Remove: scan edge barcode next]");
                    _pendingHopFile = "__REMOVE__";
                    UpdateScanStateDisplay();
                    break;
                case "VACUUM_ON":
                    Log("[Vacuum disabled — PLC bit addresses not yet configured for this machine]");
                    break;
                case "MACHINE_START":
                    Log("[Machine Start disabled — PLC bit addresses not yet configured for this machine]");
                    break;
                default:
                    SendCommand(command);
                    break;
            }
        }

        private void CancelPendingScan()
        {
            if (_pendingHopFile != null)
            {
                Log("[Pending scan cancelled]");
                _pendingHopFile = null;
                UpdateScanStateDisplay();
            }
        }

        private void UpdateScanStateDisplay()
        {
            if (_pendingHopFile == null)
            {
                lblScanState.Text = "STEP 1: Scan hop file or command barcode";
                lblScanState.ForeColor = ClrPrimaryBtn;
                txtScanInput.BackColor = Color.White;
                btnCancelScan.Visible = false;
            }
            else if (_pendingHopFile == "__REMOVE__")
            {
                lblScanState.Text = "STEP 2: Scan edge barcode to REMOVE hop from";
                lblScanState.ForeColor = ClrAccentRed;
                txtScanInput.BackColor = ClrInputDanger;
                btnCancelScan.Visible = true;
            }
            else
            {
                string fileName = Path.GetFileName(_pendingHopFile);
                lblScanState.Text = $"STEP 2: Scan edge barcode for \"{fileName}\"";
                lblScanState.ForeColor = ClrWarningOrange;
                txtScanInput.BackColor = ClrInputHighlight;
                btnCancelScan.Visible = true;
            }
        }

        // ================================================================
        //  Connection
        // ================================================================

        private void BtnConnect_Click(object? sender, EventArgs e)
        {
            if (_bzm.IsConnected)
            {
                _bzm.Disconnect();
                StopStatusPolling();
                lblStatus.Text = "Disconnected";
                lblStatus.ForeColor = ClrAccentRed;
                btnConnect.Text = "Connect";
                Log("[Disconnected]");
                return;
            }

            if (!int.TryParse(txtPort.Text, out int port))
            {
                MessageBox.Show("Invalid port number.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            try
            {
                _bzm.Connect(txtIp.Text.Trim(), port);
                lblStatus.Text = "Connected";
                lblStatus.ForeColor = ClrAccentGreen;
                btnConnect.Text = "Disconnect";
                Log($"[Connected to {txtIp.Text}:{port}]");
                StartStatusPolling();
                txtScanInput.Focus();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Connection failed:\n{ex.Message}", "Error",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                Log($"[Connection failed: {ex.Message}]");
            }
        }

        // ================================================================
        //  Status Polling (GET_STATUS)
        // ================================================================

        private void StartStatusPolling()
        {
            StopStatusPolling();

            if (_config.PollIntervalMs <= 0)
                return;

            _pollTimer = new System.Windows.Forms.Timer
            {
                Interval = _config.PollIntervalMs
            };
            _pollTimer.Tick += (s, e) => PollStatus();
            _pollTimer.Start();
            Log($"[Status polling started ({_config.PollIntervalMs}ms)]");
        }

        private void StopStatusPolling()
        {
            if (_pollTimer != null)
            {
                _pollTimer.Stop();
                _pollTimer.Dispose();
                _pollTimer = null;
                lblMachineState.Text = "-- not polling --";
                lblMachineState.ForeColor = ClrTextSecondary;
            }
        }

        private void PollStatus()
        {
            if (!_bzm.IsConnected)
                return;

            try
            {
                // GET_STATUS for the configured table (A or D)
                _bzm.Send(BzmCommands.GetStatus(_config.DefaultTable));
            }
            catch
            {
                // Connection lost — handled by Disconnected event
            }
        }

        /// <summary>
        /// Handles all incoming data. Parses GET_STATUS responses to update
        /// machine state, and logs everything else.
        /// </summary>
        private void OnDataReceived(string msg)
        {
            string trimmed = msg.Trim();

            // Try to parse GET_STATUS response
            // Expected format: GET_STATUS\t<table>\t<value>
            if (TryParseStatusResponse(trimmed, out int statusValue))
            {
                Invoke(() => UpdateMachineState(statusValue));
                return; // don't spam the log with polling responses
            }

            // Log all other responses
            InvokeLog($"< {trimmed}");
        }

        private bool TryParseStatusResponse(string msg, out int value)
        {
            value = 0;

            // Response may use tabs or spaces as separators
            string[] parts = msg.Split(new[] { '\t', ' ' },
                StringSplitOptions.RemoveEmptyEntries);

            // Looking for: GET_STATUS <table> <value>
            if (parts.Length >= 3
                && parts[0].Equals("GET_STATUS", StringComparison.OrdinalIgnoreCase))
            {
                return int.TryParse(parts[parts.Length - 1], out value);
            }

            return false;
        }


        /// <summary>
        /// Updates the UI based on GET_STATUS bit flags.
        /// Bit 6: Tisch Aktiv, Bit 1: Running, Bit 2: Finished,
        /// Bit 3: Cancelled, Bit 0: Ready
        /// </summary>
        private void UpdateMachineState(int status)
        {
            bool active    = (status & (1 << 6)) != 0;
            bool ready     = (status & (1 << 0)) != 0;
            bool running   = (status & (1 << 1)) != 0;
            bool finished  = (status & (1 << 2)) != 0;
            bool cancelled = (status & (1 << 3)) != 0;

            // Sync the toggle state with reality
            _tableActive = active;
            UpdateActivButton();

            // Build status display
            var parts = new System.Collections.Generic.List<string>();

            if (active)   parts.Add("ACTIVE");
            else          parts.Add("INACTIVE");

            if (running)   parts.Add("| RUNNING");
            if (finished)  parts.Add("| FINISHED");
            if (cancelled) parts.Add("| CANCELLED");
            if (ready)     parts.Add("| READY");

            string display = string.Join(" ", parts);
            lblMachineState.Text = $"Table {_config.DefaultTable}: {display}  (raw: {status})";

            if (running)
            {
                lblMachineState.ForeColor = ClrWarningOrange;
            }
            else if (active)
            {
                lblMachineState.ForeColor = ClrAccentGreen;
            }
            else if (cancelled)
            {
                lblMachineState.ForeColor = ClrAccentRed;
            }
            else
            {
                lblMachineState.ForeColor = ClrTextSecondary;
            }
        }

        // ================================================================
        //  Command File Execution
        // ================================================================

        private void ExecuteCommandFile(string filePath)
        {
            Log($"[Executing command file: {filePath}]");

            if (!File.Exists(filePath))
            {
                Log($"[ERROR: File not found: {filePath}]");
                return;
            }

            try
            {
                string[] lines = File.ReadAllLines(filePath);
                foreach (string line in lines)
                {
                    string trimmed = line.Trim();
                    if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith("#"))
                        continue;

                    string tcpCommand = trimmed.Replace(";", "\t");
                    SendCommand(tcpCommand);
                    System.Threading.Thread.Sleep(200);
                }
                Log("[Command file execution complete]");
            }
            catch (Exception ex)
            {
                Log($"[ERROR reading command file: {ex.Message}]");
            }
        }

        // ================================================================
        //  Raw Command
        // ================================================================

        private void TxtRawCommand_KeyDown(object? sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Enter)
            {
                e.SuppressKeyPress = true;
                SendRawCommand();
            }
        }

        private void ScanPlcBytes()
        {
            if (!_bzm.IsConnected)
            {
                Log("[Scan PLC: not connected]");
                return;
            }

            Log("[Scan PLC: reading all 32 bytes (read-only)...]");
            try
            {
                for (int i = 0; i < 32; i++)
                {
                    _bzm.Send(BzmCommands.GetByte(i));
                }
            }
            catch
            {
                Log("[Scan PLC: connection lost during scan]");
            }
        }

        private void SendRawCommand()
        {
            string cmd = txtRawCommand.Text.Trim();
            if (string.IsNullOrEmpty(cmd))
                return;

            cmd = cmd.Replace("|", "\t").Replace(";", "\t");
            SendCommand(cmd);
            txtRawCommand.Clear();
        }

        // ================================================================
        //  Config
        // ================================================================

        private void BtnEditConfig_Click(object? sender, EventArgs e)
        {
            string configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "scanconfig.json");
            if (!File.Exists(configPath))
                _config.Save();

            try
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = configPath,
                    UseShellExecute = true
                });
                Log($"[Config opened: {configPath}]");
                Log("[Save the file, then restart the app to apply changes]");
            }
            catch (Exception ex)
            {
                Log($"[Could not open config: {ex.Message}]");
            }
        }

        // ================================================================
        //  Helpers
        // ================================================================

        private void UpdateActivButton()
        {
            if (_tableActive)
            {
                btnActiv.Text = "ACTIVE";
                btnActiv.BackColor = ClrToggleActive;
                btnActiv.ForeColor = Color.White;
                btnActiv.FlatAppearance.BorderColor = ClrToggleActive;
            }
            else
            {
                btnActiv.Text = "INACTIVE";
                btnActiv.BackColor = ClrToggleInactive;
                btnActiv.ForeColor = Color.White;
                btnActiv.FlatAppearance.BorderColor = ClrToggleInactive;
            }
        }


        private void SendCommand(string command)
        {
            if (!_bzm.IsConnected)
            {
                Log("[Not connected]");
                return;
            }

            try
            {
                _bzm.Send(command);
                string display = command.Replace("\t", " | ");
                Log($"> {display}");
            }
            catch (Exception ex)
            {
                Log($"[Send error: {ex.Message}]");
            }
        }

        private void Log(string message)
        {
            if (InvokeRequired)
            {
                Invoke(() => Log(message));
                return;
            }

            txtLog.AppendText($"[{DateTime.Now:HH:mm:ss}] {message}{Environment.NewLine}");
        }

        private void InvokeLog(string message)
        {
            if (InvokeRequired)
                Invoke(() => Log(message));
            else
                Log(message);
        }

        private string GetMappingSummary()
        {
            var parts = new List<string>();
            foreach (var kvp in _config.BarcodeMappings)
                parts.Add($"{kvp.Key}={kvp.Value}");
            string summary = string.Join("  ", parts);
            return summary.Length > 60 ? summary.Substring(0, 57) + "..." : summary;
        }

        private static string TruncateDevicePath(string path)
        {
            // Show VID/PID portion if present
            string upper = path.ToUpperInvariant();
            int vidIdx = upper.IndexOf("VID_");
            if (vidIdx >= 0)
            {
                string sub = path.Substring(vidIdx);
                return sub.Length > 50 ? sub.Substring(0, 47) + "..." : sub;
            }
            return path.Length > 50 ? path.Substring(0, 47) + "..." : path;
        }
    }
}
