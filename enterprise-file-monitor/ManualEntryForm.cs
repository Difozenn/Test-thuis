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
        private Label categoryLabel;
        private Label categoryValueLabel;
        private ComboBox pathComboBox;
        private TextBox descriptionTextBox;
        private Button submitButton;
        private Button cancelButton;
        private bool cncAnalysisEnabled = true;
        private CNCAnalysis currentCNCAnalysis = null;
        private int? matchedCategoryId = null;
        private string matchedKeyword = null;
        private List<CategoryInfo> categories = new List<CategoryInfo>();
        
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
        
        private class CategoryInfo
        {
            public int id { get; set; }
            public string name { get; set; }
            public string color { get; set; }
            public List<string> keywords { get; set; }
            public List<string> file_patterns { get; set; }
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
            this.Size = new Size(550, 450); // Reduced height - no separate CNC file selector
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
                RowCount = 8,
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

            // Category (auto-detected)
            categoryLabel = new Label
            {
                Text = "Category:",
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 8, 10, 0)
            };
            mainPanel.Controls.Add(categoryLabel, 0, 4);

            categoryValueLabel = new Label
            {
                Text = "Not detected yet",
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                ForeColor = Color.Gray,
                Font = new Font("Segoe UI", 9, FontStyle.Italic),
                Margin = new Padding(0, 8, 0, 0)
            };
            mainPanel.Controls.Add(categoryValueLabel, 1, 4);
            mainPanel.SetColumnSpan(categoryValueLabel, 2);

            // Monitored Path (CNC File Selection)
            var pathLabel = new Label
            {
                Text = "CNC File:",
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
                Margin = new Padding(10, 0, 0, 0),
                Enabled = false  // Initially disabled until CNC analysis is complete
            };
            submitButton.Click += SubmitButton_Click;

            buttonPanel.Controls.Add(cancelButton);
            buttonPanel.Controls.Add(submitButton);

            mainPanel.Controls.Add(buttonPanel, 0, 7);
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
                    
                    var categoriesJson = JsonSerializer.Deserialize<JsonElement[]>(json);

                    categories.Clear();
                    foreach (var catJson in categoriesJson)
                    {
                        var category = new CategoryInfo
                        {
                            id = catJson.GetProperty("id").GetInt32(),
                            name = catJson.GetProperty("name").GetString(),
                            color = catJson.GetProperty("color").GetString(),
                            keywords = new List<string>(),
                            file_patterns = new List<string>()
                        };
                        
                        // Get keywords if available
                        if (catJson.TryGetProperty("keywords", out var keywordsElement))
                        {
                            foreach (var keyword in keywordsElement.EnumerateArray())
                            {
                                category.keywords.Add(keyword.GetString());
                            }
                        }
                        
                        // Get file patterns if available
                        if (catJson.TryGetProperty("file_patterns", out var patternsElement))
                        {
                            foreach (var pattern in patternsElement.EnumerateArray())
                            {
                                category.file_patterns.Add(pattern.GetString());
                            }
                        }
                        
                        categories.Add(category);
                    }

                    if (categories.Count == 0)
                    {
                        // No categories found - user must set up categories first
                        MessageBox.Show("No categories found for your account. Please set up categories in the web interface first.", 
                            "No Categories", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        this.DialogResult = DialogResult.Cancel;
                        this.Close();
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
                MessageBox.Show($"Error loading categories: {ex.Message}\n\nManual entry requires categories to be set up.", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                
                // Cannot proceed without categories
                this.DialogResult = DialogResult.Cancel;
                this.Close();
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

                    // Don't auto-select - force user to choose a path
                    pathComboBox.SelectedIndex = -1;
                }
                else
                {
                    string errorContent = await response.Content.ReadAsStringAsync();
                    Console.WriteLine($"Error loading monitored paths: {response.StatusCode} - {response.ReasonPhrase}");
                    
                    // Just show empty if loading fails
                    pathComboBox.Items.Clear();
                    MessageBox.Show("Failed to load monitored paths. Please check your connection.", "Warning", 
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error loading monitored paths: {ex.Message}");
                
                // Just show empty if loading fails
                pathComboBox.Items.Clear();
                MessageBox.Show($"Error loading monitored paths: {ex.Message}", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private async void SubmitButton_Click(object sender, EventArgs e)
        {            
            // Validate path selection
            if (pathComboBox.SelectedItem == null || !(pathComboBox.SelectedItem is PathItem selectedPath) || selectedPath.Id <= 0)
            {
                MessageBox.Show("Please select a CNC file", "Validation Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                pathComboBox.Focus();
                return;
            }
            
            // Validate CNC analysis was completed
            if (currentCNCAnalysis == null)
            {
                MessageBox.Show("CNC analysis is still processing. Please wait for it to complete.", "Validation Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            // Capture form data
            var description = descriptionTextBox.Text.Trim();
            var amount = (int)amountNumeric.Value;
            
            // Get selected path (now guaranteed to be valid)
            int pathId = ((PathItem)pathComboBox.SelectedItem).Id;

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
                        category_id = matchedCategoryId,
                        matched_keyword = matchedKeyword,
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
                            Console.WriteLine($"Manual entry submitted successfully: {amount} item(s)");
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

        private async void PathComboBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            // Clear previous analysis
            currentCNCAnalysis = null;
            submitButton.Enabled = false;
            submitButton.Text = "Analyzing...";
            
            // Check if selected path is valid
            if (pathComboBox.SelectedItem is PathItem selectedPath && selectedPath.Id > 0)
            {
                try
                {
                    // Check if the path itself is a CNC file (not a directory)
                    if (!selectedPath.IsDirectory && File.Exists(selectedPath.Path))
                    {
                        string extension = Path.GetExtension(selectedPath.Path).ToLower();
                        if (CNC_EXTENSIONS.Contains(extension))
                        {
                            // Path is a CNC file - analyze it directly
                            await AnalyzeFile(selectedPath.Path);
                        }
                        else
                        {
                            MessageBox.Show("Selected file is not a CNC file (.nc, .gcode, etc.)", "Invalid File Type", 
                                MessageBoxButtons.OK, MessageBoxIcon.Warning);
                            submitButton.Text = "Submit";
                        }
                    }
                    else if (selectedPath.IsDirectory && Directory.Exists(selectedPath.Path))
                    {
                        // For directories, find the most recent CNC file and analyze it
                        var cncFile = Directory.GetFiles(selectedPath.Path, "*.*", SearchOption.AllDirectories)
                            .Where(f => CNC_EXTENSIONS.Contains(Path.GetExtension(f).ToLower()))
                            .OrderByDescending(f => new FileInfo(f).LastWriteTime)
                            .FirstOrDefault();
                        
                        if (cncFile != null)
                        {
                            await AnalyzeFile(cncFile);
                        }
                        else
                        {
                            MessageBox.Show("No CNC files found in the selected directory", "No Files Found", 
                                MessageBoxButtons.OK, MessageBoxIcon.Warning);
                            submitButton.Text = "Submit";
                        }
                    }
                    else
                    {
                        MessageBox.Show("Selected path does not exist", "Path Error", 
                            MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        submitButton.Text = "Submit";
                    }
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Error accessing path: {ex.Message}", "Error", 
                        MessageBoxButtons.OK, MessageBoxIcon.Error);
                    submitButton.Text = "Submit";
                }
            }
            else
            {
                submitButton.Text = "Submit";
            }
        }

        private async Task AnalyzeFile(string filePath)
        {
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath))
            {
                MessageBox.Show("File does not exist", "File Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                submitButton.Text = "Submit";
                return;
            }

            // Disable submit during analysis
            submitButton.Enabled = false;

            try
            {
                // First do CNC analysis
                var analysis = await gCodeAnalyzer.AnalyzeFileAsync(filePath);
                
                if (analysis.AnalysisSuccessful)
                {
                    currentCNCAnalysis = analysis;
                    
                    // Now do category matching based on file content
                    await MatchCategoryFromFileContent(filePath);
                    
                    // Enable submit button now that analysis is complete
                    submitButton.Enabled = true;
                    submitButton.Text = "Submit";
                }
                else
                {
                    currentCNCAnalysis = null;
                    submitButton.Enabled = false;
                    submitButton.Text = "Submit";
                    MessageBox.Show($"CNC Analysis failed: {analysis.ErrorMessage}", "Analysis Error", 
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            }
            catch (Exception ex)
            {
                currentCNCAnalysis = null;
                submitButton.Enabled = false;
                submitButton.Text = "Submit";
                MessageBox.Show($"Error during analysis: {ex.Message}", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private async Task MatchCategoryFromFileContent(string filePath)
        {
            matchedCategoryId = null;
            matchedKeyword = null;

            try
            {
                // Read file content
                string content = await File.ReadAllTextAsync(filePath);
                string contentLower = content.ToLower();
                
                // Try to match categories based on content keywords
                foreach (var category in categories)
                {
                    if (category.keywords != null)
                    {
                        foreach (var keyword in category.keywords)
                        {
                            if (contentLower.Contains(keyword.ToLower()))
                            {
                                matchedCategoryId = category.id;
                                matchedKeyword = $"Content: {keyword}";
                                
                                // Find the line containing the keyword for context
                                var lines = content.Split('\n');
                                for (int i = 0; i < lines.Length; i++)
                                {
                                    if (lines[i].ToLower().Contains(keyword.ToLower()))
                                    {
                                        string contextLine = lines[i].Trim();
                                        if (contextLine.Length > 50)
                                        {
                                            contextLine = contextLine.Substring(0, 47) + "...";
                                        }
                                        matchedKeyword = $"Content: {keyword} (Line {i + 1}: {contextLine})";
                                        break;
                                    }
                                }
                                
                                // Update UI to show matched category
                                categoryValueLabel.Text = $"{category.name} (Matched: {keyword})";
                                categoryValueLabel.ForeColor = Color.Black;
                                categoryValueLabel.Font = new Font("Segoe UI", 9, FontStyle.Regular);
                                
                                return; // Found a match, stop searching
                            }
                        }
                    }
                }
                
                // No match found - will default to "Allerlei" on server side
                categoryValueLabel.Text = "No category matched (will use default)";
                categoryValueLabel.ForeColor = Color.Gray;
                categoryValueLabel.Font = new Font("Segoe UI", 9, FontStyle.Italic);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error matching category: {ex.Message}");
                categoryValueLabel.Text = "Error detecting category";
                categoryValueLabel.ForeColor = Color.Red;
            }
        }
    }
}