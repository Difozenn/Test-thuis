namespace BzmScannerClient
{
    /// <summary>
    /// Builds tab-separated TCP command strings for the BZM Server protocol.
    /// Reference: TCP_Server.pdf, Section 5 (Summary of Commands).
    /// </summary>
    public static class BzmCommands
    {
        private const char Sep = '\t';

        // --- Section 5.1: Add Hopfile ---
        // Edge: AH, AV, DH, DV | Filename: path to .hop | Count: number of parts
        public static string AddHopFile(string edge, string filename, int count = 1)
            => $"ADD_HOP_FILE{Sep}{edge}{Sep}{filename}{Sep}{count}";

        // --- Section 5.2: Remove Hopfile ---
        public static string RemoveHopFile(string edge)
            => $"REMOVE_HOP_FILE{Sep}{edge}";

        // --- Section 5.3: Activate table ---
        // Table: A or D | State: 0=deactivate, 1=activate
        public static string Activate(string table, int state)
            => $"ACTIV{Sep}{table}{Sep}{state}";

        // --- Section 5.4: Get Hop File ---
        public static string GetHopFile(string edge)
            => $"GET_HOP_FILE{Sep}{edge}";

        // --- Section 5.5: Get Status ---
        public static string GetStatus(string table)
            => $"GET_STATUS{Sep}{table}";

        // --- Section 5.6: Write variables ---
        // Write before activating the hop file
        public static string WriteVar(string edge, string variable, string value)
            => $"WRITEVAR{Sep}{edge}{Sep}{variable}{Sep}{value}";

        // --- Section 5.7: Rotate Hopfile ---
        // Rotation: 1=90, 2=180, 3=270
        public static string Rotate(string edge, int rotation)
            => $"ROTATE{Sep}{edge}{Sep}{rotation}";

        // --- Section 5.8: Mirror Hopfile ---
        // Mirror: 1=X, 2=Y, 3=X/Y
        public static string Mirror(string edge, int mirrorMode)
            => $"MIRROR{Sep}{edge}{Sep}{mirrorMode}";

        // --- Section 5.9: Save Machineload ---
        public static string SaveMachineload(string filename)
            => $"SAVE_MACHINELOAD{Sep}{filename}";

        // --- Section 5.10: Load Machineload ---
        public static string LoadMachineload(string filename)
            => $"LOAD_MACHINELOAD{Sep}{filename}";

        // --- Section 5.11: Load joblist ---
        public static string LoadJoblist(string filename)
            => $"LOADJOBLIST{Sep}{filename}";

        // --- Section 5.12: End joblist mode ---
        public static string EndJoblist()
            => "ENDJOBLIST";

        // --- Section 5.13: Set Laser Mode ---
        // Mode: 0=none, 1=point, 2=3D, 3=both
        public static string SetLaserMode(int mode)
            => $"SET_LASER_MODE{Sep}{mode}";

        // --- Section 5.14/5.15: Backup / Restore ---
        public static string Backup() => "BACKUP";
        public static string Restore() => "RESTORE";

        // --- Section 6: PLC Commands ---

        // Vacuum: Table A = byte 10 bit 6 (global 86), Table D = byte 15 bit 6 (global 126)
        public static string VacuumOn(string table)
            => SetBit(table == "A" ? 86 : 126, 1);

        public static string VacuumOff(string table)
            => SetBit(table == "A" ? 86 : 126, 0);

        // Machine Start: Table A = byte 10 bit 0 (global 80), Table D = byte 15 bit 0 (global 120)
        public static string MachineStart(string table)
            => SetBit(table == "A" ? 80 : 120, 1);

        public static string SetBit(int bit, int value)
            => $"SET_BIT{Sep}{bit}{Sep}{value}";

        public static string SetByte(int byteNum, int value)
            => $"SET_BYTE{Sep}{byteNum}{Sep}{value}";

        public static string SetInt(int index, int value)
            => $"SET_INT{Sep}{index}{Sep}{value}";

        public static string SetFloat(int index, float value)
            => $"SET_FLOAT{Sep}{index}{Sep}{value}";

        public static string GetBit(int bit)
            => $"GET_BIT{Sep}{bit}";

        public static string GetByte(int byteNum)
            => $"GET_BYTE{Sep}{byteNum}";

        public static string GetInt(int index)
            => $"GET_INT{Sep}{index}";

        public static string GetFloat(int index)
            => $"GET_FLOAT{Sep}{index}";

        // --- Generic send (for custom commands) ---
        public static string Raw(string command)
            => command;
    }
}
