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
        private Button btnSendRaw = null!;
        private TextBox txtRawCommand = null!;

        // Log
        private TextBox txtLog = null!;
        private Button btnClearLog = null!;

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
            Text = "BZM Scanner Client";
            Size = new Size(780, 720);
            MinimumSize = new Size(780, 720);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Segoe UI", 9f);

            int y = 10;

            // === Connection Group ===
            var grpConnection = new GroupBox
            {
                Text = "Connection",
                Location = new Point(12, y),
                Size = new Size(740, 65)
            };

            grpConnection.Controls.Add(new Label { Text = "IP:", Location = new Point(12, 27), AutoSize = true });
            txtIp = new TextBox { Text = _config.DefaultIp, Location = new Point(34, 24), Width = 130 };
            grpConnection.Controls.Add(txtIp);

            grpConnection.Controls.Add(new Label { Text = "Port:", Location = new Point(176, 27), AutoSize = true });
            txtPort = new TextBox { Text = _config.DefaultPort.ToString(), Location = new Point(214, 24), Width = 65 };
            grpConnection.Controls.Add(txtPort);

            btnConnect = new Button { Text = "Connect", Location = new Point(296, 22), Width = 85 };
            grpConnection.Controls.Add(btnConnect);

            btnSetLocal = new Button { Text = "Set Local", Location = new Point(392, 22), Width = 85 };
            btnSetLocal.Click += (s, e) =>
            {
                txtIp.Text = "127.0.0.1";
                txtPort.Text = _config.DefaultPort.ToString();
            };
            grpConnection.Controls.Add(btnSetLocal);

            lblStatus = new Label
            {
                Text = "Disconnected",
                ForeColor = Color.Red,
                Location = new Point(500, 27),
                AutoSize = true,
                Font = new Font("Segoe UI", 9f, FontStyle.Bold)
            };
            grpConnection.Controls.Add(lblStatus);
            Controls.Add(grpConnection);
            y += 74;

            // === Machine State Group ===
            var grpMachine = new GroupBox
            {
                Text = "Machine State (live)",
                Location = new Point(12, y),
                Size = new Size(740, 52)
            };

            lblMachineState = new Label
            {
                Text = "-- not polling --",
                Location = new Point(12, 22),
                Size = new Size(716, 20),
                Font = new Font("Consolas", 9f, FontStyle.Bold),
                ForeColor = Color.Gray
            };
            grpMachine.Controls.Add(lblMachineState);
            Controls.Add(grpMachine);
            y += 60;

            // === Scanner Device Group ===
            var grpDevice = new GroupBox
            {
                Text = "Scanner Device",
                Location = new Point(12, y),
                Size = new Size(740, 58)
            };

            lblScanner = new Label
            {
                Text = "No scanner selected",
                Location = new Point(12, 24),
                Size = new Size(520, 20),
                ForeColor = Color.Gray
            };
            grpDevice.Controls.Add(lblScanner);

            btnPickScanner = new Button { Text = "Select Scanner...", Location = new Point(585, 20), Width = 140 };
            grpDevice.Controls.Add(btnPickScanner);
            Controls.Add(grpDevice);
            y += 66;

            // === Settings Group ===
            var grpSettings = new GroupBox
            {
                Text = $"Settings  (Table: {_config.DefaultTable})",
                Location = new Point(12, y),
                Size = new Size(740, 55)
            };

            grpSettings.Controls.Add(new Label { Text = "Count:", Location = new Point(12, 24), AutoSize = true });
            nudCount = new NumericUpDown
            {
                Minimum = 1,
                Maximum = 9999,
                Value = 1,
                Location = new Point(58, 21),
                Width = 60
            };
            grpSettings.Controls.Add(nudCount);

            btnEditConfig = new Button { Text = "Edit Config...", Location = new Point(625, 19), Width = 100 };
            grpSettings.Controls.Add(btnEditConfig);

            var mappingInfo = new Label
            {
                Text = GetMappingSummary(),
                Location = new Point(140, 24),
                AutoSize = true,
                ForeColor = Color.DarkSlateGray,
                Font = new Font("Segoe UI", 8f)
            };
            grpSettings.Controls.Add(mappingInfo);
            Controls.Add(grpSettings);
            y += 63;

            // === Scanner Input Group ===
            var grpScanner = new GroupBox
            {
                Text = "Scanner Input (also accepts manual typing + Enter)",
                Location = new Point(12, y),
                Size = new Size(740, 108)
            };

            lblScanState = new Label
            {
                Text = "STEP 1: Scan hop file",
                Location = new Point(12, 22),
                Size = new Size(716, 22),
                Font = new Font("Segoe UI", 10f, FontStyle.Bold),
                ForeColor = Color.DarkBlue
            };
            grpScanner.Controls.Add(lblScanState);

            txtScanInput = new TextBox
            {
                Location = new Point(12, 50),
                Width = 590,
                Font = new Font("Consolas", 12f)
            };
            grpScanner.Controls.Add(txtScanInput);

            btnCancelScan = new Button
            {
                Text = "Cancel",
                Location = new Point(614, 48),
                Width = 55,
                Visible = false
            };
            grpScanner.Controls.Add(btnCancelScan);

            var btnFocus = new Button { Text = "Focus", Location = new Point(675, 48), Width = 52 };
            btnFocus.Click += (s, e) => { txtScanInput.Focus(); txtScanInput.SelectAll(); };
            grpScanner.Controls.Add(btnFocus);

            lblLastScan = new Label
            {
                Text = "",
                Location = new Point(12, 82),
                Size = new Size(716, 18),
                ForeColor = Color.DarkGreen,
                Font = new Font("Segoe UI", 8f, FontStyle.Italic)
            };
            grpScanner.Controls.Add(lblLastScan);
            Controls.Add(grpScanner);
            y += 116;

            // === Command Buttons Group ===
            var grpButtons = new GroupBox
            {
                Text = "Manual Commands",
                Location = new Point(12, y),
                Size = new Size(740, 95)
            };

            btnActiv = new Button { Text = "ACTIV", Location = new Point(12, 24), Width = 85, BackColor = Color.LightGreen };
            btnDeactiv = new Button { Text = "DEACTIV", Location = new Point(107, 24), Width = 85 };
            btnRemoveHop = new Button { Text = "Remove Hop", Location = new Point(202, 24), Width = 105 };
            btnGetStatus = new Button { Text = "Get Status", Location = new Point(317, 24), Width = 95 };

            grpButtons.Controls.Add(btnActiv);
            grpButtons.Controls.Add(btnDeactiv);
            grpButtons.Controls.Add(btnRemoveHop);
            grpButtons.Controls.Add(btnGetStatus);

            grpButtons.Controls.Add(new Label { Text = "Raw:", Location = new Point(12, 61), AutoSize = true });
            txtRawCommand = new TextBox { Location = new Point(48, 58), Width = 570 };
            grpButtons.Controls.Add(txtRawCommand);
            btnSendRaw = new Button { Text = "Send", Location = new Point(628, 56), Width = 65 };
            grpButtons.Controls.Add(btnSendRaw);
            Controls.Add(grpButtons);
            y += 104;

            // === Log Group ===
            var grpLog = new GroupBox
            {
                Text = "Response Log",
                Location = new Point(12, y),
                Size = new Size(740, ClientSize.Height - y - 10),
                Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
            };

            txtLog = new TextBox
            {
                Multiline = true,
                ReadOnly = true,
                ScrollBars = ScrollBars.Vertical,
                Location = new Point(12, 22),
                Size = new Size(654, grpLog.Height - 34),
                Font = new Font("Consolas", 9f),
                BackColor = Color.White,
                Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
            };
            grpLog.Controls.Add(txtLog);

            btnClearLog = new Button
            {
                Text = "Clear",
                Location = new Point(676, 22),
                Width = 52,
                Anchor = AnchorStyles.Top | AnchorStyles.Right
            };
            grpLog.Controls.Add(btnClearLog);
            Controls.Add(grpLog);
        }

        private void InitializeTray()
        {
            _trayMenu = new ContextMenuStrip();
            _trayMenu.Items.Add("Show", null, (s, e) => ShowFromTray());
            _trayMenu.Items.Add("-");
            _trayMenu.Items.Add("Exit", null, (s, e) => { _trayIcon.Visible = false; Application.Exit(); });

            _trayIcon = new NotifyIcon
            {
                Text = "BZM Scanner Client",
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
                    lblStatus.ForeColor = Color.Red;
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
            foreach (Control c in Controls)
            {
                if (c is GroupBox grp)
                {
                    foreach (Control child in grp.Controls)
                    {
                        if (child is Button btn && btn != btnConnect && btn != btnSetLocal && btn != btnEditConfig && btn != btnPickScanner)
                        {
                            btn.GotFocus += (s, e) =>
                                BeginInvoke(new Action(() => txtScanInput.Focus()));
                        }
                    }
                }
            }

            Shown += MainForm_Shown;
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
                    lblScanner.ForeColor = Color.DarkGreen;
                    Log("[Scanner device restored from config]");
                }
                else
                {
                    Log("[Saved scanner device not found — click 'Select Scanner' to pick one]");
                    lblScanner.Text = "Saved device not found";
                    lblScanner.ForeColor = Color.DarkRed;
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
                _trayIcon.ShowBalloonTip(2000, "BZM Scanner",
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
                lblScanner.ForeColor = Color.DarkGreen;
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
                lblScanState.ForeColor = Color.DarkBlue;
                txtScanInput.BackColor = Color.White;
                btnCancelScan.Visible = false;
            }
            else if (_pendingHopFile == "__REMOVE__")
            {
                lblScanState.Text = "STEP 2: Scan edge barcode to REMOVE hop from";
                lblScanState.ForeColor = Color.DarkRed;
                txtScanInput.BackColor = Color.MistyRose;
                btnCancelScan.Visible = true;
            }
            else
            {
                string fileName = Path.GetFileName(_pendingHopFile);
                lblScanState.Text = $"STEP 2: Scan edge barcode for \"{fileName}\"";
                lblScanState.ForeColor = Color.DarkOrange;
                txtScanInput.BackColor = Color.LightYellow;
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
                lblStatus.ForeColor = Color.Red;
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
                lblStatus.ForeColor = Color.Green;
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
                lblMachineState.ForeColor = Color.Gray;
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
                lblMachineState.ForeColor = Color.DarkOrange;
            }
            else if (active)
            {
                lblMachineState.ForeColor = Color.DarkGreen;
            }
            else if (cancelled)
            {
                lblMachineState.ForeColor = Color.DarkRed;
            }
            else
            {
                lblMachineState.ForeColor = Color.DarkSlateGray;
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
                btnActiv.BackColor = Color.LightGreen;
            }
            else
            {
                btnActiv.Text = "INACTIVE";
                btnActiv.BackColor = Color.LightCoral;
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
