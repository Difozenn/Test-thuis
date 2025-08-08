using System;
using System.Windows.Forms;

namespace FileMonitorTray
{
    internal static class Program
    {
        /// <summary>
        /// The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main()
        {
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