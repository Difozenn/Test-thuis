using System;
using System.Drawing;
using System.Windows.Forms;

namespace FileMonitorTray
{
    public partial class LoginForm : Form
    {
        public string Username { get; private set; } = "";
        public string Password { get; private set; } = "";

        private TextBox usernameTextBox;
        private TextBox passwordTextBox;
        private CheckBox rememberCheckBox;
        private Button loginButton;
        private Button cancelButton;
        private LocalizationManager localization;

        public LoginForm(string defaultUsername = "")
        {
            localization = LocalizationManager.Instance;
            InitializeComponent();
            InitializeControls(defaultUsername);
        }

        private void InitializeComponent()
        {
            this.Text = localization.T("login_title");
            this.Size = new Size(400, 280);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.ShowIcon = false;
            this.ShowInTaskbar = false;
        }

        private void InitializeControls(string defaultUsername)
        {
            // Main panel
            var mainPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(20),
                RowCount = 6,
                ColumnCount = 2
            };

            // Configure rows
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Title
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 20)); // Spacer
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Username
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Password
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Remember checkbox
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Buttons

            // Configure columns
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

            // Title label
            var titleLabel = new Label
            {
                Text = localization.T("please_login"),
                Font = new Font("Segoe UI", 10, FontStyle.Bold),
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleCenter
            };
            mainPanel.Controls.Add(titleLabel, 0, 0);
            mainPanel.SetColumnSpan(titleLabel, 2);

            // Username
            var usernameLabel = new Label
            {
                Text = localization.T("username"),
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(usernameLabel, 0, 2);

            usernameTextBox = new TextBox
            {
                Text = defaultUsername,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5)
            };
            mainPanel.Controls.Add(usernameTextBox, 1, 2);

            // Password
            var passwordLabel = new Label
            {
                Text = localization.T("password"),
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(passwordLabel, 0, 3);

            passwordTextBox = new TextBox
            {
                UseSystemPasswordChar = true,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5)
            };
            mainPanel.Controls.Add(passwordTextBox, 1, 3);

            // Remember me checkbox
            rememberCheckBox = new CheckBox
            {
                Text = localization.T("remember_me"),
                Checked = true,
                AutoSize = true,
                Margin = new Padding(0, 10, 0, 10)
            };
            mainPanel.Controls.Add(rememberCheckBox, 1, 4);

            // Buttons panel
            var buttonPanel = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.RightToLeft,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 15, 0, 0)
            };

            cancelButton = new Button
            {
                Text = localization.T("cancel"),
                Size = new Size(75, 30),
                DialogResult = DialogResult.Cancel
            };
            cancelButton.Click += CancelButton_Click;

            loginButton = new Button
            {
                Text = localization.T("login"),
                Size = new Size(75, 30),
                Margin = new Padding(10, 0, 0, 0)
            };
            loginButton.Click += LoginButton_Click;

            buttonPanel.Controls.Add(cancelButton);
            buttonPanel.Controls.Add(loginButton);

            mainPanel.Controls.Add(buttonPanel, 0, 5);
            mainPanel.SetColumnSpan(buttonPanel, 2);

            this.Controls.Add(mainPanel);

            // Set accept/cancel buttons
            this.AcceptButton = loginButton;
            this.CancelButton = cancelButton;

            // Focus handling
            this.Load += (s, e) =>
            {
                if (string.IsNullOrEmpty(defaultUsername))
                {
                    usernameTextBox.Focus();
                }
                else
                {
                    passwordTextBox.Focus();
                }
            };

            // Enter key handling
            usernameTextBox.KeyDown += (s, e) =>
            {
                if (e.KeyCode == Keys.Enter)
                {
                    passwordTextBox.Focus();
                }
            };

            passwordTextBox.KeyDown += (s, e) =>
            {
                if (e.KeyCode == Keys.Enter)
                {
                    LoginButton_Click(s, e);
                }
            };
        }

        private void LoginButton_Click(object sender, EventArgs e)
        {
            if (string.IsNullOrWhiteSpace(usernameTextBox.Text))
            {
                MessageBox.Show(localization.T("enter_username"), localization.T("validation_error"), 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                usernameTextBox.Focus();
                return;
            }

            if (string.IsNullOrWhiteSpace(passwordTextBox.Text))
            {
                MessageBox.Show(localization.T("enter_password"), localization.T("validation_error"), 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                passwordTextBox.Focus();
                return;
            }

            Username = usernameTextBox.Text.Trim();
            Password = passwordTextBox.Text;

            this.DialogResult = DialogResult.OK;
            this.Close();
        }

        private void CancelButton_Click(object sender, EventArgs e)
        {
            this.DialogResult = DialogResult.Cancel;
            this.Close();
        }
    }
}