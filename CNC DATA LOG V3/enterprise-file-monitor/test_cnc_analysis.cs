using System;
using System.IO;
using System.Threading.Tasks;

namespace FileMonitorTray
{
    class TestCNCAnalysis
    {
        static async Task Main(string[] args)
        {
            var analyzer = new GCodeAnalyzer();
            var result = await analyzer.AnalyzeFileAsync("Field1.nc");
            
            Console.WriteLine($"Analysis Successful: {result.AnalysisSuccessful}");
            if (result.AnalysisSuccessful)
            {
                Console.WriteLine($"Line Count: {result.LineCount}");
                Console.WriteLine($"Tool Changes: {result.ToolChanges}");
                Console.WriteLine($"Rapid Time: {result.RapidTime:F2} min");
                Console.WriteLine($"Cutting Time: {result.CuttingTime:F2} min");
                Console.WriteLine($"Total Time: {result.TotalTime:F2} min");
                Console.WriteLine($"Machine Time: {result.MachineTime:F2} min");
                Console.WriteLine($"Formatted Time: {result.GetFormattedTime()}");
                
                Console.WriteLine("\nMovement Stats:");
                foreach (var kvp in result.MovementStats)
                {
                    Console.WriteLine($"  {kvp.Key}: {kvp.Value}");
                }
            }
            else
            {
                Console.WriteLine($"Error: {result.ErrorMessage}");
            }
        }
    }
}