using System;
using System.Collections.Generic;
using System.Drawing;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.IO;

namespace FileMonitorTray
{
    public partial class ManualEntryForm : Form
    {
        private readonly HttpClient httpClient;
        private readonly string webAppUrl;
        private readonly string currentUser;
        private readonly LocalizationManager localization;

        private NumericUpDown amountNumeric;
        private ComboBox categoryComboBox;
        private TextBox descriptionTextBox;
        private Button submitButton;
        private Button cancelButton;

        public ManualEntryForm(HttpClient httpClient, string webAppUrl, string currentUser, LocalizationManager localization)
        {
            this.httpClient = httpClient;
            this.webAppUrl = webAppUrl;
            this.currentUser = currentUser;
            this.localization = localization;
            
            InitializeComponent();
            InitializeControls();
            LoadCategories();
        }

        private void InitializeComponent()
        {
            this.Text = localization.T("manual_entry_title");
            this.Size = new Size(550, 350);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.ShowIcon = false;
            this.ShowInTaskbar = false;
        }

        private void InitializeControls()
        {
            // Main panel
            var mainPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(20),
                RowCount = 6,
                ColumnCount = 3
            };

            // Configure rows
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // User info
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 15)); // Spacer
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Description
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Amount
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Category
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Buttons

            // Configure columns
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));

            // User info
            var userLabel = new Label
            {
                Text = $"Logged in as: {currentUser}",
                Font = new Font("Segoe UI", 9, FontStyle.Italic),
                ForeColor = Color.Gray,
                Dock = DockStyle.Fill
            };
            mainPanel.Controls.Add(userLabel, 0, 0);
            mainPanel.SetColumnSpan(userLabel, 3);

            // Description (Optional)
            var descriptionLabel = new Label
            {
                Text = "Description (Optional):",
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(descriptionLabel, 0, 2);

            descriptionTextBox = new TextBox
            {
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5)
            };
            mainPanel.Controls.Add(descriptionTextBox, 1, 2);
            mainPanel.SetColumnSpan(descriptionTextBox, 2);

            // Amount
            var amountLabel = new Label
            {
                Text = "Amount:",
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(amountLabel, 0, 3);

            amountNumeric = new NumericUpDown
            {
                Minimum = 1,
                Maximum = 100,
                Value = 1,
                Width = 80,
                Margin = new Padding(0, 5, 0, 5)
            };
            mainPanel.Controls.Add(amountNumeric, 1, 3);

            // Category
            var categoryLabel = new Label
            {
                Text = "Category:",
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(categoryLabel, 0, 4);

            categoryComboBox = new ComboBox
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5)
            };
            mainPanel.Controls.Add(categoryComboBox, 1, 4);
            mainPanel.SetColumnSpan(categoryComboBox, 2);

            // Buttons
            var buttonPanel = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.RightToLeft,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 20, 0, 0)
            };

            cancelButton = new Button
            {
                Text = "Cancel",
                Size = new Size(80, 30),
                DialogResult = DialogResult.Cancel
            };
            cancelButton.Click += (s, e) => this.Close();

            submitButton = new Button
            {
                Text = "Submit",
                Size = new Size(80, 30),
                Margin = new Padding(10, 0, 0, 0)
            };
            submitButton.Click += SubmitButton_Click;

            buttonPanel.Controls.Add(cancelButton);
            buttonPanel.Controls.Add(submitButton);

            mainPanel.Controls.Add(buttonPanel, 0, 5);
            mainPanel.SetColumnSpan(buttonPanel, 3);

            this.Controls.Add(mainPanel);

            // Set default button
            this.AcceptButton = submitButton;
            this.CancelButton = cancelButton;

            // Focus on amount
            this.Load += (s, e) => amountNumeric.Focus();

            // Enter key handling
            descriptionTextBox.KeyDown += (s, e) =>
            {
                if (e.KeyCode == Keys.Enter)
                {
                    amountNumeric.Focus();
                }
            };

            amountNumeric.KeyDown += (s, e) =>
            {
                if (e.KeyCode == Keys.Enter)
                {
                    categoryComboBox.Focus();
                }
            };

            categoryComboBox.KeyDown += (s, e) =>
            {
                if (e.KeyCode == Keys.Enter)
                {
                    SubmitButton_Click(s, e);
                }
            };
        }

        private async void LoadCategories()
        {
            try
            {
                var response = await httpClient.GetAsync($"{webAppUrl}/api/categories");
                if (response.IsSuccessStatusCode)
                {
                    string json = await response.Content.ReadAsStringAsync();
                    var categories = JsonSerializer.Deserialize<JsonElement[]>(json);

                    categoryComboBox.Items.Clear();
                    foreach (var category in categories)
                    {
                        string name = category.GetProperty("name").GetString();
                        categoryComboBox.Items.Add(name);
                    }

                    if (categoryComboBox.Items.Count > 0)
                    {
                        categoryComboBox.SelectedIndex = 0;
                    }
                }
                else
                {
                    categoryComboBox.Items.Add("Default");
                    categoryComboBox.SelectedIndex = 0;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error loading categories: {ex.Message}", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                categoryComboBox.Items.Add("Default");
                categoryComboBox.SelectedIndex = 0;
            }
        }

        private async void SubmitButton_Click(object sender, EventArgs e)
        {
            // Validation - only category is required
            if (categoryComboBox.SelectedItem == null)
            {
                MessageBox.Show("Please select a category", "Validation Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                categoryComboBox.Focus();
                return;
            }

            // Capture form data
            var description = descriptionTextBox.Text.Trim();
            var category = categoryComboBox.SelectedItem.ToString();
            var amount = (int)amountNumeric.Value;

            // Close form immediately
            this.DialogResult = DialogResult.OK;
            this.Close();

            // Submit in background using Task.Run
            Task.Run(async () =>
            {
                try
                {
                    var data = new
                    {
                        description = description,
                        category = category,
                        amount = amount
                    };

                    string json = JsonSerializer.Serialize(data);
                    var content = new StringContent(json, Encoding.UTF8, "application/json");

                    // Set a longer timeout for large amounts
                    var requestTimeout = TimeSpan.FromSeconds(Math.Max(30, amount * 3));
                    using (var cts = new System.Threading.CancellationTokenSource(requestTimeout))
                    {
                        var response = await httpClient.PostAsync($"{webAppUrl}/api/manual_entry", content, cts.Token);
                        
                        if (!response.IsSuccessStatusCode)
                        {
                            // Log error but don't show message box from background thread
                            Console.WriteLine($"Manual entry failed: {response.StatusCode}");
                        }
                    }
                }
                catch (Exception ex)
                {
                    // Log error but don't show message box from background thread
                    Console.WriteLine($"Error submitting manual entry: {ex.Message}");
                }
            });
        }
    }
}