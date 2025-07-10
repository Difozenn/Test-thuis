// Test C# CNC Analyzer
using System;
using System.IO;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Linq;

// Copy of the C# analyzer classes for testing
public class CNCAnalysis
{
    public string Filename { get; set; }
    public int LineCount { get; set; }
    public double TotalTime { get; set; }
    public double CuttingTime { get; set; }
    public double RapidTime { get; set; }
    public double MachineTime { get; set; }
    public int ToolChanges { get; set; }
    public int ProcessesCount { get; set; }
    public Dictionary<string, int> MovementStats { get; set; }
    public List<string> ProcessesUsed { get; set; }
    public DateTime AnalyzedAt { get; set; }
    public bool AnalysisSuccessful { get; set; }
    public string ErrorMessage { get; set; }

    public CNCAnalysis()
    {
        MovementStats = new Dictionary<string, int>();
        ProcessesUsed = new List<string>();
        AnalyzedAt = DateTime.UtcNow;
        AnalysisSuccessful = false;
    }
}

public class CNCMovement
{
    public string Code { get; set; }
    public double X { get; set; }
    public double Y { get; set; }
    public double Z { get; set; }
    public double Feedrate { get; set; }
    public double Distance { get; set; }
    public double Time { get; set; }
}

public class GCodeAnalyzer
{
    // Machine timing configuration (matching Python postprocessor)
    private const double RAPID_SPEED = 20000; // mm/min
    private const double TOOL_CHANGE_TIME = 20; // seconds
    private const double SPINDLE_START_TIME = 2; // seconds
    private const double SPINDLE_STOP_TIME = 1.5; // seconds
    private const double TCP_ON_TIME = 0.5; // seconds
    private const double TCP_OFF_TIME = 0.3; // seconds
    private const double CONTOUR_START_TIME = 0.5; // seconds
    private const double CONTOUR_END_TIME = 0.3; // seconds
    private const double DYNAMIC_SETUP_TIME = 0.5; // seconds
    private const double FLUSH_WAIT_TIME = 1.0; // seconds
    private const double COORDINATE_SETUP_TIME = 0.2; // seconds
    private const double GENERAL_CYCLE_TIME = 0.1; // seconds

    // Machine operation counters
    private class MachineOperations
    {
        public int ToolChanges { get; set; }
        public int SpindleStarts { get; set; }
        public int SpindleStops { get; set; }
        public int TcpOn { get; set; }
        public int TcpOff { get; set; }
        public int ContourStarts { get; set; }
        public int ContourEnds { get; set; }
        public int DynamicSetups { get; set; }
        public int FlushWaits { get; set; }
        public int CoordinateSetups { get; set; }
        public int OtherCycles { get; set; }
    }

    // Movement tracking
    private double _currentX = 0;
    private double _currentY = 0;
    private double _currentZ = 0;
    private double _currentFeedrate = 0;

    public async Task<CNCAnalysis> AnalyzeFileAsync(string filePath)
    {
        var analysis = new CNCAnalysis
        {
            Filename = Path.GetFileName(filePath)
        };

        try
        {
            if (!File.Exists(filePath))
            {
                analysis.ErrorMessage = "File not found";
                return analysis;
            }

            var lines = await File.ReadAllLinesAsync(filePath);
            analysis.LineCount = lines.Length;

            var machineOps = new MachineOperations();
            var movements = new List<CNCMovement>();
            
            // Reset position tracking
            _currentX = 0; _currentY = 0; _currentZ = 0; _currentFeedrate = 0;

            foreach (var line in lines)
            {
                var cleanLine = CleanGCodeLine(line);
                if (string.IsNullOrEmpty(cleanLine)) continue;

                // Count machine operations (matching Python logic)
                CountMachineOperations(cleanLine, machineOps);

                // Extract feedrate
                var feedMatch = Regex.Match(cleanLine, @"F(\d+\.?\d*)");
                if (feedMatch.Success && double.TryParse(feedMatch.Groups[1].Value, out double feed))
                {
                    _currentFeedrate = feed;
                }

                // Process movements
                var movement = ProcessMovement(cleanLine, analysis);
                if (movement != null)
                {
                    movements.Add(movement);
                }
            }

            // Calculate machine operation time
            double machineOperationTime = CalculateMachineOperationTime(machineOps);

            // Calculate movement times
            analysis.RapidTime = movements.Where(m => m.Code == "G0").Sum(m => m.Time);
            analysis.CuttingTime = movements.Where(m => m.Code == "G1" || m.Code == "G2" || m.Code == "G3").Sum(m => m.Time);
            analysis.TotalTime = movements.Sum(m => m.Time);
            
            // Set tool changes from machine operations
            analysis.ToolChanges = machineOps.ToolChanges;
            analysis.ProcessesCount = analysis.ProcessesUsed.Count;

            // Total cycle time = machine operations + cutting time + rapid time (all in seconds)
            double totalCycleTimeSeconds = machineOperationTime + (analysis.CuttingTime * 60) + (analysis.RapidTime * 60);
            
            // Convert to minutes for MachineTime
            analysis.MachineTime = totalCycleTimeSeconds / 60.0;
            
            analysis.AnalysisSuccessful = true;
            return analysis;
        }
        catch (Exception ex)
        {
            analysis.ErrorMessage = $"Analysis failed: {ex.Message}";
            return analysis;
        }
    }

    private string CleanGCodeLine(string line)
    {
        // Remove comments
        var commentIndex = line.IndexOf('(');
        if (commentIndex >= 0)
        {
            line = line.Substring(0, commentIndex);
        }

        commentIndex = line.IndexOf(';');
        if (commentIndex >= 0)
        {
            line = line.Substring(0, commentIndex);
        }

        return line.Trim().ToUpper();
    }

    private void CountMachineOperations(string line, MachineOperations ops)
    {
        // Count machine operations that add to cycle time (matching Python logic)
        if (line.Contains("CH_TOOLCHANGE.NC"))
            ops.ToolChanges++;
        else if (line.Contains("CH_SPINDEL.NC"))
        {
            // Determine if start or stop based on parameters
            if (line.Contains("@P2=1")) // Spindle start
                ops.SpindleStarts++;
            else if (line.Contains("@P2=0")) // Spindle stop
                ops.SpindleStops++;
        }
        else if (line.Contains("CH_TCP_ON.NC"))
            ops.TcpOn++;
        else if (line.Contains("CH_TCP_OFF.NC"))
            ops.TcpOff++;
        else if (line.Contains("CH_CONTOUR_START.NC"))
            ops.ContourStarts++;
        else if (line.Contains("CH_CONTOUR_END.NC"))
            ops.ContourEnds++;
        else if (line.Contains("CH_DYNAMIC.NC"))
            ops.DynamicSetups++;
        else if (line.Contains("#FLUSH WAIT"))
            ops.FlushWaits++;
        else if (line.Contains("#CS ON") || line.Contains("#CS OFF") || 
                 line.Contains("#MCS ON") || line.Contains("#MCS OFF"))
            ops.CoordinateSetups++;
        else if (line.Contains("L CYCLE") && !line.Contains("CH_TOOLCHANGE") && 
                 !line.Contains("CH_SPINDEL") && !line.Contains("CH_TCP_") && 
                 !line.Contains("CH_CONTOUR_") && !line.Contains("CH_DYNAMIC") && 
                 !line.Contains("CH_CHECK_TOOL"))
            ops.OtherCycles++;
    }

    private CNCMovement ProcessMovement(string line, CNCAnalysis analysis)
    {
        CNCMovement movement = null;

        // G0 - Rapid moves
        if (Regex.IsMatch(line, @"\bG0\b|\bG00\b"))
        {
            movement = CalculateMoveTime(line, RAPID_SPEED, "G0");
            if (movement != null && analysis.MovementStats.ContainsKey("G0"))
                analysis.MovementStats["G0"]++;
            else if (movement != null)
                analysis.MovementStats["G0"] = 1;
                
            if (!analysis.ProcessesUsed.Contains("RAPID"))
                analysis.ProcessesUsed.Add("RAPID");
        }
        // G1 - Linear cutting moves
        else if (Regex.IsMatch(line, @"\bG1\b|\bG01\b"))
        {
            if (_currentFeedrate > 0)
            {
                movement = CalculateMoveTime(line, _currentFeedrate, "G1");
                if (movement != null && analysis.MovementStats.ContainsKey("G1"))
                    analysis.MovementStats["G1"]++;
                else if (movement != null)
                    analysis.MovementStats["G1"] = 1;
                    
                if (!analysis.ProcessesUsed.Contains("CUTTING"))
                    analysis.ProcessesUsed.Add("CUTTING");
            }
        }
        // G2/G3 - Arc moves
        else if (Regex.IsMatch(line, @"\bG[0]?[23]\b"))
        {
            if (_currentFeedrate > 0)
            {
                var code = Regex.IsMatch(line, @"\bG[0]?2\b") ? "G2" : "G3";
                movement = CalculateArcMoveTime(line, _currentFeedrate, code);
                if (movement != null && analysis.MovementStats.ContainsKey(code))
                    analysis.MovementStats[code]++;
                else if (movement != null)
                    analysis.MovementStats[code] = 1;
                    
                if (!analysis.ProcessesUsed.Contains("CUTTING"))
                    analysis.ProcessesUsed.Add("CUTTING");
            }
        }

        if (movement != null)
        {
            UpdatePosition(line);
        }

        return movement;
    }

    private CNCMovement CalculateMoveTime(string line, double feedRate, string code)
    {
        var newX = _currentX;
        var newY = _currentY;
        var newZ = _currentZ;

        // Extract coordinates
        var xMatch = Regex.Match(line, @"X([-+]?\d*\.?\d+)");
        if (xMatch.Success && double.TryParse(xMatch.Groups[1].Value, out double x))
            newX = x;

        var yMatch = Regex.Match(line, @"Y([-+]?\d*\.?\d+)");
        if (yMatch.Success && double.TryParse(yMatch.Groups[1].Value, out double y))
            newY = y;

        var zMatch = Regex.Match(line, @"Z([-+]?\d*\.?\d+)");
        if (zMatch.Success && double.TryParse(zMatch.Groups[1].Value, out double z))
            newZ = z;

        // Calculate distance
        var distance = Math.Sqrt(
            Math.Pow(newX - _currentX, 2) +
            Math.Pow(newY - _currentY, 2) +
            Math.Pow(newZ - _currentZ, 2)
        );

        // Calculate time in minutes
        var time = feedRate > 0 ? distance / feedRate : 0;

        return new CNCMovement
        {
            Code = code,
            X = newX,
            Y = newY,
            Z = newZ,
            Feedrate = feedRate,
            Distance = distance,
            Time = time
        };
    }

    private CNCMovement CalculateArcMoveTime(string line, double feedRate, string code)
    {
        // Simplified arc calculation for testing
        return CalculateMoveTime(line, feedRate, code);
    }

    private void UpdatePosition(string line)
    {
        var xMatch = Regex.Match(line, @"X([-+]?\d*\.?\d+)");
        if (xMatch.Success && double.TryParse(xMatch.Groups[1].Value, out double x))
            _currentX = x;

        var yMatch = Regex.Match(line, @"Y([-+]?\d*\.?\d+)");
        if (yMatch.Success && double.TryParse(yMatch.Groups[1].Value, out double y))
            _currentY = y;

        var zMatch = Regex.Match(line, @"Z([-+]?\d*\.?\d+)");
        if (zMatch.Success && double.TryParse(zMatch.Groups[1].Value, out double z))
            _currentZ = z;
    }

    private double CalculateMachineOperationTime(MachineOperations ops)
    {
        // Calculate total machine operation time in seconds (matching Python logic)
        return ops.ToolChanges * TOOL_CHANGE_TIME +
               ops.SpindleStarts * SPINDLE_START_TIME +
               ops.SpindleStops * SPINDLE_STOP_TIME +
               ops.TcpOn * TCP_ON_TIME +
               ops.TcpOff * TCP_OFF_TIME +
               ops.ContourStarts * CONTOUR_START_TIME +
               ops.ContourEnds * CONTOUR_END_TIME +
               ops.DynamicSetups * DYNAMIC_SETUP_TIME +
               ops.FlushWaits * FLUSH_WAIT_TIME +
               ops.CoordinateSetups * COORDINATE_SETUP_TIME +
               ops.OtherCycles * GENERAL_CYCLE_TIME;
    }
}

class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("=".PadLeft(60, '='));
        Console.WriteLine("Testing C# CNC Analysis with Field1.nc");
        Console.WriteLine("=".PadLeft(60, '='));
        
        var analyzer = new GCodeAnalyzer();
        var field1Path = "/home/difusion/Projects/CNC DATA LOG V3/enterprise-file-monitor/Field1.nc";
        
        Console.WriteLine($"Analyzing file: {field1Path}");
        Console.WriteLine("-".PadLeft(40, '-'));
        
        var analysis = await analyzer.AnalyzeFileAsync(field1Path);
        
        if (analysis.AnalysisSuccessful)
        {
            Console.WriteLine("✅ Analysis SUCCESSFUL!");
            Console.WriteLine($"📄 File: {analysis.Filename}");
            Console.WriteLine($"📝 Lines: {analysis.LineCount:N0}");
            Console.WriteLine($"⏱️  Total Time: {analysis.TotalTime:F2} minutes");
            Console.WriteLine($"🔥 Cutting Time: {analysis.CuttingTime:F2} minutes");
            Console.WriteLine($"⚡ Rapid Time: {analysis.RapidTime:F2} minutes");
            Console.WriteLine($"🏭 Machine Time: {analysis.MachineTime:F2} minutes");
            Console.WriteLine($"🔧 Tool Changes: {analysis.ToolChanges}");
            Console.WriteLine($"⚙️  Processes: {analysis.ProcessesCount}");
            
            if (analysis.MovementStats.Any())
            {
                Console.WriteLine("\n📊 Movement Statistics:");
                foreach (var stat in analysis.MovementStats)
                {
                    Console.WriteLine($"   {stat.Key}: {stat.Value:N0} movements");
                }
            }
            
            if (analysis.ProcessesUsed.Any())
            {
                Console.WriteLine($"\n🔄 Processes Used: {string.Join(", ", analysis.ProcessesUsed)}");
            }
            
            Console.WriteLine($"\n🕐 Analyzed at: {analysis.AnalyzedAt}");
            
            // Show expected vs actual
            Console.WriteLine($"\n📋 Comparison:");
            Console.WriteLine($"   Python result: 3.5 minutes (210.4 seconds)");
            Console.WriteLine($"   C# result: {analysis.MachineTime:F1} minutes ({analysis.MachineTime * 60:F1} seconds)");
        }
        else
        {
            Console.WriteLine("❌ Analysis FAILED!");
            Console.WriteLine($"Error: {analysis.ErrorMessage}");
        }
        
        Console.WriteLine("=".PadLeft(60, '='));
    }
}