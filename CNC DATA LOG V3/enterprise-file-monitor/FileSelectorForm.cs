using System;
using System.Collections.Generic;
using System.Drawing;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.IO;
using System.Globalization;
using System.Linq;

namespace FileMonitorTray
{
    public static class StringExtensions
    {
        public static string ToTitleCase(this string input)
        {
            if (string.IsNullOrEmpty(input))
                return input;
            
            return CultureInfo.CurrentCulture.TextInfo.ToTitleCase(input.ToLower());
        }
    }

    public partial class FileSelectorForm : Form
    {
        private readonly HttpClient httpClient;
        private readonly string webAppUrl;
        private readonly string currentUser;
        private readonly LocalizationManager localization;

        private RadioButton fileRadioButton;
        private RadioButton directoryRadioButton;
        private TextBox pathTextBox;
        private Button browseButton;
        private CheckBox recursiveCheckBox;
        private ListBox selectedPathsListBox;
        private Button addPathButton;
        private Button removePathButton;
        private Button submitButton;
        private Button cancelButton;
        private Label countLabel;
        private TextBox descriptionTextBox;
        private Label descriptionLabel;

        private List<PathInfo> selectedPaths = new List<PathInfo>();

        public class PathInfo
        {
            public string Path { get; set; }
            public bool IsDirectory { get; set; }
            public bool Recursive { get; set; }
            public string Description { get; set; }

            public override string ToString()
            {
                string type = IsDirectory ? "📁" : "📄";
                string recursiveIndicator = IsDirectory && Recursive ? " (Recursive)" : "";
                string desc = !IsDirectory && !string.IsNullOrEmpty(Description) ? $" - {Description}" : "";
                return $"{type} {Path}{desc}{recursiveIndicator}";
            }
        }

        public FileSelectorForm(HttpClient httpClient, string webAppUrl, string currentUser, LocalizationManager localization)
        {
            this.httpClient = httpClient;
            this.webAppUrl = webAppUrl;
            this.currentUser = currentUser;
            this.localization = localization;
            
            InitializeComponent();
            InitializeControls();
        }

        private void InitializeComponent()
        {
            this.Text = "Add Files/Directories to Monitor";
            this.Size = new Size(700, 650);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.ShowIcon = false;
            this.ShowInTaskbar = false;
        }

        private void InitializeControls()
        {
            var mainPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(20),
                RowCount = 9,
                ColumnCount = 3
            };

            // Configure rows
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // User info
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 15)); // Spacer
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Radio buttons
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Path input
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Description input
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Options
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); // Selected paths list
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Count
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Buttons

            // Configure columns
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));

            // User info
            var userLabel = new Label
            {
                Text = $"Adding monitoring paths for: {currentUser}",
                Font = new Font("Segoe UI", 9, FontStyle.Italic),
                ForeColor = Color.Gray,
                Dock = DockStyle.Fill
            };
            mainPanel.Controls.Add(userLabel, 0, 0);
            mainPanel.SetColumnSpan(userLabel, 3);

            // Type selection
            var typePanel = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.LeftToRight,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5)
            };

            fileRadioButton = new RadioButton
            {
                Text = "📄 Monitor specific file",
                AutoSize = true,
                Checked = true,
                Margin = new Padding(0, 0, 20, 0)
            };

            directoryRadioButton = new RadioButton
            {
                Text = "📁 Monitor directory",
                AutoSize = true
            };

            typePanel.Controls.Add(fileRadioButton);
            typePanel.Controls.Add(directoryRadioButton);

            mainPanel.Controls.Add(typePanel, 0, 2);
            mainPanel.SetColumnSpan(typePanel, 3);

            // Path input
            var pathLabel = new Label
            {
                Text = "Path:",
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(pathLabel, 0, 3);

            pathTextBox = new TextBox
            {
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 5, 5),
                PlaceholderText = "Enter file or directory path..."
            };
            mainPanel.Controls.Add(pathTextBox, 1, 3);

            browseButton = new Button
            {
                Text = "Browse...",
                Size = new Size(80, 25),
                Margin = new Padding(0, 5, 0, 5)
            };
            browseButton.Click += BrowseButton_Click;
            mainPanel.Controls.Add(browseButton, 2, 3);

            // Description input (for files)
            descriptionLabel = new Label
            {
                Text = "Description:",
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(descriptionLabel, 0, 4);

            descriptionTextBox = new TextBox
            {
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 5, 5),
                PlaceholderText = "Optional description for files (used in charts)"
            };
            mainPanel.Controls.Add(descriptionTextBox, 1, 4);
            mainPanel.SetColumnSpan(descriptionTextBox, 2);

            // Options
            var optionsPanel = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.LeftToRight,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5)
            };

            recursiveCheckBox = new CheckBox
            {
                Text = "Monitor subdirectories recursively",
                AutoSize = true,
                Checked = true,
                Enabled = false // Initially disabled for file mode
            };

            addPathButton = new Button
            {
                Text = "Add to List",
                Size = new Size(100, 30),
                Margin = new Padding(20, 0, 0, 0)
            };
            addPathButton.Click += AddPathButton_Click;

            optionsPanel.Controls.Add(recursiveCheckBox);
            optionsPanel.Controls.Add(addPathButton);

            mainPanel.Controls.Add(optionsPanel, 0, 5);
            mainPanel.SetColumnSpan(optionsPanel, 3);

            // Selected paths list
            var listLabel = new Label
            {
                Text = "Paths to Monitor:",
                AutoSize = true,
                Anchor = AnchorStyles.Left | AnchorStyles.Top,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(listLabel, 0, 6);

            var listPanel = new Panel
            {
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 5, 5)
            };

            selectedPathsListBox = new ListBox
            {
                Dock = DockStyle.Fill,
                SelectionMode = SelectionMode.MultiExtended,
                IntegralHeight = false
            };
            listPanel.Controls.Add(selectedPathsListBox);
            mainPanel.Controls.Add(listPanel, 1, 6);

            removePathButton = new Button
            {
                Text = "Remove\nSelected",
                Size = new Size(80, 50),
                Margin = new Padding(0, 5, 0, 5),
                Anchor = AnchorStyles.Top,
                Enabled = false
            };
            removePathButton.Click += RemovePathButton_Click;
            mainPanel.Controls.Add(removePathButton, 2, 6);

            // Count
            countLabel = new Label
            {
                Text = "0 paths selected",
                ForeColor = Color.Gray,
                AutoSize = true,
                Margin = new Padding(0, 5, 0, 5)
            };
            mainPanel.Controls.Add(countLabel, 1, 7);

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
                Text = "Add Monitoring",
                Size = new Size(120, 30),
                Margin = new Padding(10, 0, 0, 0),
                Enabled = false
            };
            submitButton.Click += SubmitButton_Click;

            buttonPanel.Controls.Add(cancelButton);
            buttonPanel.Controls.Add(submitButton);

            mainPanel.Controls.Add(buttonPanel, 0, 8);
            mainPanel.SetColumnSpan(buttonPanel, 3);

            this.Controls.Add(mainPanel);

            // Set default button
            this.AcceptButton = submitButton;
            this.CancelButton = cancelButton;

            // Event handlers for type changes
            fileRadioButton.CheckedChanged += TypeRadioButton_CheckedChanged;
            directoryRadioButton.CheckedChanged += TypeRadioButton_CheckedChanged;

            // Event handlers
            pathTextBox.KeyDown += (s, e) =>
            {
                if (e.KeyCode == Keys.Enter)
                {
                    AddPathButton_Click(s, e);
                }
            };

            selectedPathsListBox.SelectedIndexChanged += (s, e) =>
            {
                removePathButton.Enabled = selectedPathsListBox.SelectedItems.Count > 0;
            };

            // Focus on path input
            this.Load += (s, e) => pathTextBox.Focus();

            // Initial state
            TypeRadioButton_CheckedChanged(fileRadioButton, EventArgs.Empty);
        }

        private void TypeRadioButton_CheckedChanged(object sender, EventArgs e)
        {
            if (fileRadioButton.Checked)
            {
                recursiveCheckBox.Enabled = false;
                recursiveCheckBox.Checked = false;
                browseButton.Text = "Browse File...";
                pathTextBox.PlaceholderText = "Enter file path...";
                
                // Show description controls for files
                descriptionTextBox.Visible = true;
                descriptionLabel.Visible = true;
            }
            else
            {
                recursiveCheckBox.Enabled = true;
                recursiveCheckBox.Checked = true;
                browseButton.Text = "Browse Folder...";
                pathTextBox.PlaceholderText = "Enter directory path...";
                
                // Hide description controls for directories
                descriptionTextBox.Visible = false;
                descriptionLabel.Visible = false;
            }
        }

        private void BrowseButton_Click(object sender, EventArgs e)
        {
            if (fileRadioButton.Checked)
            {
                using (var openFileDialog = new OpenFileDialog())
                {
                    openFileDialog.Title = "Select File to Monitor";
                    openFileDialog.Filter = "All Files (*.*)|*.*";
                    openFileDialog.RestoreDirectory = true;

                    if (openFileDialog.ShowDialog() == DialogResult.OK)
                    {
                        pathTextBox.Text = openFileDialog.FileName;
                    }
                }
            }
            else
            {
                using (var folderDialog = new FolderBrowserDialog())
                {
                    folderDialog.Description = "Select Directory to Monitor";
                    folderDialog.ShowNewFolderButton = false;

                    if (folderDialog.ShowDialog() == DialogResult.OK)
                    {
                        pathTextBox.Text = folderDialog.SelectedPath;
                    }
                }
            }
        }

        private void AddPathButton_Click(object sender, EventArgs e)
        {
            string path = pathTextBox.Text.Trim();
            if (string.IsNullOrEmpty(path))
            {
                MessageBox.Show("Please enter a path.", "Validation Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                pathTextBox.Focus();
                return;
            }

            if (!File.Exists(path) && !Directory.Exists(path))
            {
                MessageBox.Show("The specified path does not exist.", "Path Not Found", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                pathTextBox.Focus();
                return;
            }

            bool isDirectory = Directory.Exists(path);
            if (fileRadioButton.Checked && isDirectory)
            {
                MessageBox.Show("You selected 'Monitor specific file' but chose a directory. Please select a file or change to directory mode.", 
                    "Type Mismatch", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            if (directoryRadioButton.Checked && !isDirectory)
            {
                MessageBox.Show("You selected 'Monitor directory' but chose a file. Please select a directory or change to file mode.", 
                    "Type Mismatch", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            // Check for duplicates
            if (selectedPaths.Exists(p => p.Path.Equals(path, StringComparison.OrdinalIgnoreCase)))
            {
                MessageBox.Show("This path is already in the list.", "Duplicate Path", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            // Get description for files
            string description = "";
            if (!isDirectory)
            {
                description = descriptionTextBox.Text.Trim();
                if (string.IsNullOrEmpty(description))
                {
                    // Auto-generate description from filename
                    description = Path.GetFileNameWithoutExtension(path)
                        .Replace('_', ' ')
                        .Replace('-', ' ')
                        .ToTitleCase();
                }
            }

            var pathInfo = new PathInfo
            {
                Path = path,
                IsDirectory = isDirectory,
                Recursive = isDirectory && recursiveCheckBox.Checked,
                Description = description
            };

            selectedPaths.Add(pathInfo);
            selectedPathsListBox.Items.Add(pathInfo);
            
            pathTextBox.Clear();
            descriptionTextBox.Clear();
            pathTextBox.Focus();
            
            UpdateCount();
        }

        private void RemovePathButton_Click(object sender, EventArgs e)
        {
            if (selectedPathsListBox.SelectedItems.Count > 0)
            {
                var selectedIndices = new List<int>();
                foreach (int index in selectedPathsListBox.SelectedIndices)
                {
                    selectedIndices.Add(index);
                }

                // Remove in reverse order to maintain indices
                selectedIndices.Sort((a, b) => b.CompareTo(a));
                foreach (int index in selectedIndices)
                {
                    selectedPaths.RemoveAt(index);
                    selectedPathsListBox.Items.RemoveAt(index);
                }
                
                UpdateCount();
            }
        }

        private void UpdateCount()
        {
            int count = selectedPaths.Count;
            int fileCount = selectedPaths.Count(p => !p.IsDirectory);
            int dirCount = selectedPaths.Count(p => p.IsDirectory);
            
            string description = "";
            if (fileCount > 0 && dirCount > 0)
            {
                description = $"{fileCount} file(s) and {dirCount} directory(s)";
            }
            else if (fileCount > 0)
            {
                description = $"{fileCount} file(s)";
            }
            else if (dirCount > 0)
            {
                description = $"{dirCount} directory(s)";
            }
            else
            {
                description = "No paths";
            }

            countLabel.Text = $"{count} paths selected ({description})";
            submitButton.Enabled = count > 0;
        }

        private async void SubmitButton_Click(object sender, EventArgs e)
        {
            if (selectedPaths.Count == 0)
            {
                MessageBox.Show("Please add at least one path to monitor.", "No Paths Selected", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            submitButton.Enabled = false;
            submitButton.Text = "Adding...";

            int successCount = 0;
            int errorCount = 0;
            var errors = new List<string>();

            try
            {
                foreach (var pathInfo in selectedPaths)
                {
                    try
                    {
                        var response = await httpClient.PostAsync($"{webAppUrl}/path/add", 
                            new FormUrlEncodedContent(new[]
                            {
                                new KeyValuePair<string, string>("path", pathInfo.Path),
                                new KeyValuePair<string, string>("recursive", pathInfo.Recursive ? "on" : "off"),
                                new KeyValuePair<string, string>("description", pathInfo.Description ?? "")
                            }));

                        if (response.IsSuccessStatusCode)
                        {
                            successCount++;
                        }
                        else
                        {
                            errorCount++;
                            errors.Add($"{pathInfo.Path}: Server error");
                        }
                    }
                    catch (Exception ex)
                    {
                        errorCount++;
                        errors.Add($"{pathInfo.Path}: {ex.Message}");
                    }
                }

                // Show results
                string message = $"Successfully added {successCount} path(s)";
                if (errorCount > 0)
                {
                    message += $"\n{errorCount} error(s) occurred:";
                    var firstFiveErrors = errors.Take(5).ToList();
                    foreach (string error in firstFiveErrors)
                    {
                        message += $"\n• {error}";
                    }
                    if (errors.Count > 5)
                    {
                        message += $"\n... and {errors.Count - 5} more";
                    }
                }

                MessageBox.Show(message, "Results", MessageBoxButtons.OK, 
                    errorCount > 0 ? MessageBoxIcon.Warning : MessageBoxIcon.Information);

                if (successCount > 0)
                {
                    this.DialogResult = DialogResult.OK;
                    this.Close();
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error adding paths: {ex.Message}", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                submitButton.Enabled = true;
                submitButton.Text = "Add Monitoring";
            }
        }
    }
}