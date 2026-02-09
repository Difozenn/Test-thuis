using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace BzmScannerClient
{
    public class ScannerConfig
    {
        public string DefaultIp { get; set; } = "10.0.0.103";
        public int DefaultPort { get; set; } = 50000;
        public string DefaultTable { get; set; } = "D";

        /// <summary>
        /// Device path of the selected USB scanner. Saved so you don't have to
        /// pick it every time. Set automatically when you select a device.
        /// </summary>
        public string ScannerDevicePath { get; set; } = "";

        /// <summary>
        /// GET_STATUS polling interval in milliseconds. Set to 0 to disable.
        /// </summary>
        public int PollIntervalMs { get; set; } = 1000;

        /// <summary>
        /// Maps scanned barcode strings to edge identifiers or special commands.
        /// Edge values: AH, AV, DH, DV
        /// Special commands: ACTIV, DEACTIV, GET_STATUS, REMOVE
        /// </summary>
        public Dictionary<string, string> BarcodeMappings { get; set; } = new(StringComparer.OrdinalIgnoreCase)
        {
            ["@VOOR"]    = "DV",
            ["@ACHTER"]  = "DH",
            ["@ACTIV"]   = "ACTIV",
            ["@DEACTIV"] = "DEACTIV",
            ["@STATUS"]  = "GET_STATUS",
            ["@REMOVE"]  = "REMOVE",
        };

        private static readonly JsonSerializerOptions _jsonOpts = new()
        {
            WriteIndented = true,
            ReadCommentHandling = JsonCommentHandling.Skip,
            DefaultIgnoreCondition = JsonIgnoreCondition.Never
        };

        private static string ConfigPath =>
            Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "scanconfig.json");

        public static ScannerConfig Load()
        {
            string path = ConfigPath;
            if (!File.Exists(path))
            {
                // Create default config file so the user can edit it
                var cfg = new ScannerConfig();
                cfg.Save();
                return cfg;
            }

            try
            {
                string json = File.ReadAllText(path);
                var cfg = JsonSerializer.Deserialize<ScannerConfig>(json, _jsonOpts);
                return cfg ?? new ScannerConfig();
            }
            catch
            {
                return new ScannerConfig();
            }
        }

        public void Save()
        {
            string json = JsonSerializer.Serialize(this, _jsonOpts);
            File.WriteAllText(ConfigPath, json);
        }

        /// <summary>
        /// Returns true if the barcode maps to an edge (AH/AV/DH/DV).
        /// Returns false if it maps to a special command (ACTIV, etc.) or is unknown.
        /// </summary>
        public bool IsEdgeMapping(string barcode, out string edge)
        {
            edge = "";
            if (!BarcodeMappings.TryGetValue(barcode, out string? mapped))
                return false;

            string upper = mapped.ToUpperInvariant();
            if (upper is "AH" or "AV" or "DH" or "DV")
            {
                edge = upper;
                return true;
            }
            return false;
        }

        /// <summary>
        /// Returns true if the barcode maps to a special command like ACTIV, DEACTIV, etc.
        /// </summary>
        public bool IsCommandMapping(string barcode, out string command)
        {
            command = "";
            if (!BarcodeMappings.TryGetValue(barcode, out string? mapped))
                return false;

            string upper = mapped.ToUpperInvariant();
            if (upper is not "AH" and not "AV" and not "DH" and not "DV")
            {
                command = upper;
                return true;
            }
            return false;
        }
    }
}
