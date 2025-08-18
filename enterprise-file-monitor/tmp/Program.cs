using System;
using System.Windows.Forms;
using System.Runtime.InteropServices;

namespace FileMonitorTray
{
    internal static class Program
    {
        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        static extern bool AllocConsole();
        
        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        static extern bool AttachConsole(int dwProcessId);
        
        private const int ATTACH_PARENT_PROCESS = -1;
        
        /// <summary>
        /// The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main()
        {
            // Try to attach to parent console first (if run from cmd/powershell)
            // If that fails, allocate a new console
            if (!AttachConsole(ATTACH_PARENT_PROCESS))
            {
                AllocConsole();
            }
            
            // Redirect console output
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] FileMonitor starting...");
            Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] Console output enabled");
            
            // Enable visual styles for modern appearance
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            
            // Set application-wide exception handling
            Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
            Application.ThreadException += Application_ThreadException;
            AppDomain.CurrentDomain.UnhandledException += CurrentDomain_UnhandledException;
            
            // Create and run the main form (which will be hidden)
            using (var mainForm = new FileMonitorTrayApp())
            {
                Application.Run();
            }
        }
        
        private static void Application_ThreadException(object sender, System.Threading.ThreadExceptionEventArgs e)
        {
            ShowError("Application Error", e.Exception);
        }
        
        private static void CurrentDomain_UnhandledException(object sender, UnhandledExceptionEventArgs e)
        {
            if (e.ExceptionObject is Exception ex)
            {
                ShowError("Unhandled Error", ex);
            }
        }
        
        private static void ShowError(string title, Exception ex)
        {
            string message = $"An error occurred:\n\n{ex.Message}";
            if (ex.InnerException != null)
            {
                message += $"\n\nInner Exception: {ex.InnerException.Message}";
            }
            
            MessageBox.Show(message, title, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}