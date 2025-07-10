using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
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
        private readonly GCodeAnalyzer gCodeAnalyzer;

        private NumericUpDown amountNumeric;
        private ComboBox categoryComboBox;
        private ComboBox pathComboBox;
        private TextBox descriptionTextBox;
        private Button submitButton;
        private Button cancelButton;
        private ComboBox cncFileComboBox;
        private Button browseCNCButton;
        private Button analyzeCNCButton;
        private TextBox cncAnalysisTextBox;
        private Label cncAnalysisLabel;
        private bool cncAnalysisEnabled = true;
        private CNCAnalysis currentCNCAnalysis = null;
        
        // CNC file extensions
        private readonly HashSet<string> CNC_EXTENSIONS = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            ".nc", ".gcode", ".tap", ".mpf", ".ptp", ".cls", ".lst", ".prg", ".sub", ".cnc"
        };
        
        private class PathItem
        {
            public int Id { get; set; }
            public string Path { get; set; }
            public string Description { get; set; }
            public bool IsDirectory { get; set; }
            
            public override string ToString()
            {
                return string.IsNullOrEmpty(Description) ? Path : $"{Description} ({Path})";
            }
        }

        public ManualEntryForm(HttpClient httpClient, string webAppUrl, string currentUser, LocalizationManager localization)
        {
            this.httpClient = httpClient;
            this.webAppUrl = webAppUrl;
            this.currentUser = currentUser;
            this.localization = localization;
            this.gCodeAnalyzer = new GCodeAnalyzer();
            
            InitializeComponent();
            InitializeControls();
            LoadCategories();
            _ = LoadMonitoredPaths();
        }

        private void InitializeComponent()
        {
            this.Text = localization.T("manual_entry_title");
            this.Size = new Size(550, 650); // Increased height for CNC analysis
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
                RowCount = 11,
                ColumnCount = 3
            };

            // Configure rows
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // User info
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 15)); // Spacer
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Description
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Amount
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Category
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // Path
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 15)); // Spacer
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // CNC File
            mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize)); // CNC Analysis button
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); // CNC Analysis results
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

            // Monitored Path
            var pathLabel = new Label
            {
                Text = "Monitored Path (Optional):",
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(pathLabel, 0, 5);

            pathComboBox = new ComboBox
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5)
            };
            pathComboBox.SelectedIndexChanged += PathComboBox_SelectedIndexChanged;
            mainPanel.Controls.Add(pathComboBox, 1, 5);
            mainPanel.SetColumnSpan(pathComboBox, 2);

            // CNC File Selection
            var cncFileLabel = new Label
            {
                Text = "CNC File (Optional):",
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(cncFileLabel, 0, 7);

            cncFileComboBox = new ComboBox
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5),
                Enabled = false
            };
            cncFileComboBox.SelectedIndexChanged += CncFileComboBox_SelectedIndexChanged;
            mainPanel.Controls.Add(cncFileComboBox, 1, 7);

            browseCNCButton = new Button
            {
                Text = "Browse...",
                Width = 80,
                Margin = new Padding(5, 5, 0, 5)
            };
            browseCNCButton.Click += BrowseCNCButton_Click;
            mainPanel.Controls.Add(browseCNCButton, 2, 7);

            // CNC Analysis Button
            analyzeCNCButton = new Button
            {
                Text = "Analyze CNC File",
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5),
                Enabled = false,
                Visible = cncAnalysisEnabled
            };
            analyzeCNCButton.Click += AnalyzeCNCButton_Click;
            mainPanel.Controls.Add(analyzeCNCButton, 1, 8);
            mainPanel.SetColumnSpan(analyzeCNCButton, 2);

            // CNC Analysis Results
            cncAnalysisLabel = new Label
            {
                Text = "CNC Analysis Results:",
                AutoSize = true,
                Anchor = AnchorStyles.Left | AnchorStyles.Top,
                Margin = new Padding(0, 8, 10, 0),
                Visible = cncAnalysisEnabled
            };
            mainPanel.Controls.Add(cncAnalysisLabel, 0, 9);

            cncAnalysisTextBox = new TextBox
            {
                Multiline = true,
                ReadOnly = true,
                Dock = DockStyle.Fill,
                Margin = new Padding(0, 5, 0, 5),
                ScrollBars = ScrollBars.Vertical,
                BackColor = Color.White,
                Visible = cncAnalysisEnabled
            };
            mainPanel.Controls.Add(cncAnalysisTextBox, 1, 9);
            mainPanel.SetColumnSpan(cncAnalysisTextBox, 2);

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

            mainPanel.Controls.Add(buttonPanel, 0, 10);
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
                    pathComboBox.Focus();
                }
            };

            pathComboBox.KeyDown += (s, e) =>
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
                    
                    // Check if response is actually JSON and not HTML error page
                    if (string.IsNullOrWhiteSpace(json) || json.TrimStart().StartsWith("<"))
                    {
                        throw new InvalidOperationException("Server returned HTML instead of JSON. Check if you're logged in and the server is running properly.");
                    }
                    
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
                    else
                    {
                        // No categories found, add default
                        categoryComboBox.Items.Add("Default");
                        categoryComboBox.SelectedIndex = 0;
                    }
                }
                else
                {
                    string errorContent = await response.Content.ReadAsStringAsync();
                    throw new HttpRequestException($"Server returned {response.StatusCode}: {response.ReasonPhrase}. Content: {errorContent.Substring(0, Math.Min(200, errorContent.Length))}");
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error loading categories: {ex.Message}\n\nUsing default category instead.", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                
                categoryComboBox.Items.Clear();
                categoryComboBox.Items.Add("Default");
                categoryComboBox.SelectedIndex = 0;
            }
        }

        private async Task LoadMonitoredPaths()
        {
            try
            {
                var response = await httpClient.GetAsync($"{webAppUrl}/api/monitored_paths");
                if (response.IsSuccessStatusCode)
                {
                    string json = await response.Content.ReadAsStringAsync();
                    
                    // Check if response is actually JSON and not HTML error page
                    if (string.IsNullOrWhiteSpace(json) || json.TrimStart().StartsWith("<"))
                    {
                        throw new InvalidOperationException("Server returned HTML instead of JSON. Check if you're logged in and the server is running properly.");
                    }
                    
                    var paths = JsonSerializer.Deserialize<JsonElement[]>(json);

                    pathComboBox.Items.Clear();
                    
                    // Add default "None" option
                    pathComboBox.Items.Add(new PathItem { Id = 0, Path = "None - Manual Entry", Description = "" });
                    
                    foreach (var path in paths)
                    {
                        var pathItem = new PathItem
                        {
                            Id = path.GetProperty("id").GetInt32(),
                            Path = path.GetProperty("path").GetString(),
                            Description = path.GetProperty("description").GetString(),
                            IsDirectory = path.GetProperty("is_directory").GetBoolean()
                        };
                        pathComboBox.Items.Add(pathItem);
                    }

                    pathComboBox.SelectedIndex = 0;
                }
                else
                {
                    string errorContent = await response.Content.ReadAsStringAsync();
                    Console.WriteLine($"Error loading monitored paths: {response.StatusCode} - {response.ReasonPhrase}");
                    
                    // Just add the default option if loading fails
                    pathComboBox.Items.Clear();
                    pathComboBox.Items.Add(new PathItem { Id = 0, Path = "None - Manual Entry", Description = "" });
                    pathComboBox.SelectedIndex = 0;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error loading monitored paths: {ex.Message}");
                
                // Just add the default option if loading fails
                pathComboBox.Items.Clear();
                pathComboBox.Items.Add(new PathItem { Id = 0, Path = "None - Manual Entry", Description = "" });
                pathComboBox.SelectedIndex = 0;
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
            
            // Get selected path
            int? pathId = null;
            if (pathComboBox.SelectedItem is PathItem selectedPath && selectedPath.Id > 0)
            {
                pathId = selectedPath.Id;
            }

            // Close form immediately
            this.DialogResult = DialogResult.OK;
            this.Close();

            // Submit in background using Task.Run
            _ = Task.Run(async () =>
            {
                try
                {
                    var data = new
                    {
                        description = description,
                        category = category,
                        amount = amount,
                        path_id = pathId,
                        cnc_analysis = currentCNCAnalysis
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
                            string errorContent = await response.Content.ReadAsStringAsync();
                            // Log detailed error information
                            Console.WriteLine($"Manual entry failed: {response.StatusCode} - {response.ReasonPhrase}");
                            Console.WriteLine($"Error content: {errorContent}");
                            
                            // Show user-friendly message on UI thread
                            this.Invoke((MethodInvoker)delegate
                            {
                                MessageBox.Show($"Failed to submit manual entry.\nStatus: {response.StatusCode}\nPlease check if you're logged in and try again.", 
                                    "Submission Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                            });
                        }
                        else
                        {
                            // Success - could show a brief success message if needed
                            Console.WriteLine($"Manual entry submitted successfully: {amount} item(s) for category '{category}'");
                        }
                    }
                }
                catch (Exception ex)
                {
                    // Log error and show user-friendly message
                    Console.WriteLine($"Error submitting manual entry: {ex.Message}");
                    
                    // Show error message on UI thread
                    this.Invoke((MethodInvoker)delegate
                    {
                        MessageBox.Show($"Error submitting manual entry: {ex.Message}\n\nPlease check your connection and try again.", 
                            "Submission Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    });
                }
            });
        }

        private void PathComboBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            // Clear CNC file selection when path changes
            cncFileComboBox.Items.Clear();
            cncFileComboBox.Enabled = false;
            analyzeCNCButton.Enabled = false;
            cncAnalysisTextBox.Clear();
            currentCNCAnalysis = null;

            // Load CNC files from selected path
            if (pathComboBox.SelectedItem is PathItem selectedPath && selectedPath.Id > 0)
            {
                LoadCNCFilesFromPath(selectedPath.Path);
            }
        }

        private void CncFileComboBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            // Enable analyze button when a valid file is selected
            analyzeCNCButton.Enabled = cncFileComboBox.SelectedIndex > 0;
            
            // Clear previous analysis
            cncAnalysisTextBox.Clear();
            currentCNCAnalysis = null;
        }

        private void LoadCNCFilesFromPath(string path)
        {
            try
            {
                if (Directory.Exists(path))
                {
                    var cncFiles = Directory.GetFiles(path, "*.*", SearchOption.AllDirectories)
                        .Where(f => CNC_EXTENSIONS.Contains(Path.GetExtension(f)))
                        .OrderByDescending(f => new FileInfo(f).LastWriteTime)
                        .Take(20) // Limit to 20 most recent files
                        .ToList();

                    if (cncFiles.Any())
                    {
                        cncFileComboBox.Items.Clear();
                        cncFileComboBox.Items.Add("Select CNC File...");
                        
                        foreach (var file in cncFiles)
                        {
                            cncFileComboBox.Items.Add(new FileInfo(file).Name + " - " + file);
                        }
                        
                        cncFileComboBox.SelectedIndex = 0;
                        cncFileComboBox.Enabled = true;
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error loading CNC files from path: {ex.Message}");
            }
        }

        private void BrowseCNCButton_Click(object sender, EventArgs e)
        {
            using (var openFileDialog = new OpenFileDialog())
            {
                openFileDialog.Filter = "CNC Files (*.nc;*.gcode;*.tap;*.mpf;*.ptp;*.cls;*.lst;*.prg;*.sub;*.cnc)|*.nc;*.gcode;*.tap;*.mpf;*.ptp;*.cls;*.lst;*.prg;*.sub;*.cnc|All Files (*.*)|*.*";
                openFileDialog.FilterIndex = 1;
                openFileDialog.RestoreDirectory = true;

                if (openFileDialog.ShowDialog() == DialogResult.OK)
                {
                    var fileName = Path.GetFileName(openFileDialog.FileName);
                    cncFileComboBox.Items.Clear();
                    cncFileComboBox.Items.Add(fileName + " - " + openFileDialog.FileName);
                    cncFileComboBox.SelectedIndex = 0;
                    cncFileComboBox.Enabled = true;
                    analyzeCNCButton.Enabled = true;
                }
            }
        }

        private async void AnalyzeCNCButton_Click(object sender, EventArgs e)
        {
            if (cncFileComboBox.SelectedItem == null || cncFileComboBox.SelectedIndex == 0)
            {
                MessageBox.Show("Please select a CNC file first", "No File Selected", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            var selectedItem = cncFileComboBox.SelectedItem.ToString();
            var filePath = selectedItem.Split(new[] { " - " }, StringSplitOptions.None).LastOrDefault();

            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath))
            {
                MessageBox.Show("Selected file does not exist", "File Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // Disable button during analysis
            analyzeCNCButton.Enabled = false;
            analyzeCNCButton.Text = "Analyzing...";
            cncAnalysisTextBox.Text = "Analyzing CNC file, please wait...";

            try
            {
                var analysis = await gCodeAnalyzer.AnalyzeFileAsync(filePath);
                
                if (analysis.AnalysisSuccessful)
                {
                    currentCNCAnalysis = analysis;
                    
                    var result = new StringBuilder();
                    result.AppendLine($"File: {analysis.Filename}");
                    result.AppendLine($"Lines: {analysis.LineCount:N0}");
                    result.AppendLine($"Total Time: {analysis.TotalTime:F2} minutes");
                    result.AppendLine($"Cutting Time: {analysis.CuttingTime:F2} minutes");
                    result.AppendLine($"Rapid Time: {analysis.RapidTime:F2} minutes");
                    result.AppendLine($"Machine Time: {analysis.MachineTime:F2} minutes");
                    result.AppendLine($"Tool Changes: {analysis.ToolChanges}");
                    result.AppendLine($"Processes: {analysis.ProcessesCount}");
                    
                    if (analysis.MovementStats.Any())
                    {
                        result.AppendLine("\nMovement Statistics:");
                        foreach (var stat in analysis.MovementStats)
                        {
                            result.AppendLine($"  {stat.Key}: {stat.Value:N0}");
                        }
                    }
                    
                    if (analysis.ProcessesUsed.Any())
                    {
                        result.AppendLine($"\nProcesses Used: {string.Join(", ", analysis.ProcessesUsed)}");
                    }
                    
                    cncAnalysisTextBox.Text = result.ToString();
                    
                    // Auto-suggest amount based on machine time (e.g., 1 item per minute)
                    var suggestedAmount = Math.Max(1, (int)Math.Round(analysis.MachineTime));
                    amountNumeric.Value = Math.Min(suggestedAmount, amountNumeric.Maximum);
                }
                else
                {
                    cncAnalysisTextBox.Text = $"Analysis failed: {analysis.ErrorMessage}";
                    currentCNCAnalysis = null;
                }
            }
            catch (Exception ex)
            {
                cncAnalysisTextBox.Text = $"Error during analysis: {ex.Message}";
                currentCNCAnalysis = null;
            }
            finally
            {
                analyzeCNCButton.Enabled = true;
                analyzeCNCButton.Text = "Analyze CNC File";
            }
        }
    }
}