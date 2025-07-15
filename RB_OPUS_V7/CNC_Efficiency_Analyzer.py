#!/usr/bin/env python3
"""
CNC Efficiency Classification System
Analyzes NC programs for efficiency metrics and provides optimization recommendations
"""

import os
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from CycleTimeCalculator import CycleTimeCalculator, MachineConfig

@dataclass
class EfficiencyMetrics:
    """Core efficiency metrics"""
    # Time Analysis
    total_cycle_time: float = 0.0           # seconds
    cutting_time: float = 0.0               # seconds  
    rapid_time: float = 0.0                 # seconds
    tool_change_time: float = 0.0           # seconds
    spindle_time: float = 0.0               # seconds
    overhead_time: float = 0.0              # seconds
    
    # Distance Analysis  
    total_distance: float = 0.0             # mm
    cutting_distance: float = 0.0           # mm
    rapid_distance: float = 0.0             # mm
    
    # Operations Count
    tool_changes: int = 0
    spindle_starts: int = 0
    cycle_calls: int = 0
    
    # Calculated Efficiency Ratios
    cutting_efficiency: float = 0.0         # cutting_time / total_cycle_time * 100
    tool_change_efficiency: float = 0.0     # tool_changes per minute
    spindle_efficiency: float = 0.0         # spindle utilization
    program_efficiency_score: float = 0.0   # overall score 0-100

@dataclass 
class EfficiencyClassification:
    """Efficiency classification results"""
    overall_grade: str = "UNKNOWN"          # EXCELLENT, GOOD, POOR
    cutting_grade: str = "UNKNOWN"
    tool_grade: str = "UNKNOWN"
    spindle_grade: str = "UNKNOWN"
    
    overall_score: float = 0.0              # 0-100
    strengths: List[str] = None
    weaknesses: List[str] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.strengths is None:
            self.strengths = []
        if self.weaknesses is None:
            self.weaknesses = []
        if self.recommendations is None:
            self.recommendations = []

class CNCEfficiencyAnalyzer:
    """Main efficiency analyzer class"""
    
    def __init__(self, nc_file_path: str, config: Optional[MachineConfig] = None):
        self.nc_file_path = nc_file_path
        self.config = config or MachineConfig()
        self.calculator = CycleTimeCalculator(nc_file_path, self.config)
        self.metrics = EfficiencyMetrics()
        self.classification = EfficiencyClassification()
        
        # Efficiency thresholds
        self.thresholds = {
            'cutting_efficiency': {
                'excellent': 70.0,   # >70% cutting time
                'good': 50.0,        # 50-70% cutting time
                'poor': 50.0         # <50% cutting time
            },
            'tool_changes_per_min': {
                'excellent': 1.5,    # <1.5 changes/min
                'good': 2.5,         # 1.5-2.5 changes/min  
                'poor': 2.5          # >2.5 changes/min
            },
            'spindle_efficiency': {
                'excellent': 80.0,   # >80% spindle utilization
                'good': 60.0,        # 60-80% utilization
                'poor': 60.0         # <60% utilization
            }
        }
    
    def analyze_efficiency(self) -> Tuple[EfficiencyMetrics, EfficiencyClassification]:
        """Complete efficiency analysis"""
        print(f"🔍 Analyzing efficiency for: {os.path.basename(self.nc_file_path)}")
        
        # Step 1: Calculate cycle time data
        self.calculator.load_machine_config_from_ini()
        self.calculator.parse_nc_file()
        results = self.calculator.calculate_cycle_time()
        
        # Step 2: Extract metrics
        self._extract_metrics(results)
        
        # Step 3: Calculate efficiency ratios
        self._calculate_efficiency_ratios()
        
        # Step 4: Classify efficiency
        self._classify_efficiency()
        
        # Step 5: Generate recommendations
        self._generate_recommendations()
        
        return self.metrics, self.classification
    
    def _extract_metrics(self, cycle_results: Dict) -> None:
        """Extract raw metrics from cycle time calculation"""
        # Time metrics (convert to seconds)
        self.metrics.total_cycle_time = cycle_results.get('total_time', 0.0)
        self.metrics.cutting_time = cycle_results.get('cutting_time', 0.0)
        self.metrics.rapid_time = cycle_results.get('rapid_time', 0.0)
        self.metrics.tool_change_time = cycle_results.get('tool_change_time', 0.0)
        self.metrics.spindle_time = cycle_results.get('spindle_time', 0.0)
        
        # Calculate overhead (non-cutting time)
        self.metrics.overhead_time = (
            self.metrics.total_cycle_time - 
            self.metrics.cutting_time
        )
        
        # Distance metrics
        self.metrics.total_distance = self.calculator.total_distance
        self.metrics.cutting_distance = self.calculator.total_cutting_distance  
        self.metrics.rapid_distance = self.calculator.total_rapid_distance
        
        # Operations count
        self.metrics.tool_changes = self.calculator.tool_changes
        self.metrics.spindle_starts = self.calculator.spindle_starts
        self.metrics.cycle_calls = self.calculator.cycle_calls
        
    def _calculate_efficiency_ratios(self) -> None:
        """Calculate efficiency ratios and percentages"""
        
        # Cutting Efficiency: cutting_time / total_cycle_time * 100
        if self.metrics.total_cycle_time > 0:
            self.metrics.cutting_efficiency = (
                self.metrics.cutting_time / self.metrics.total_cycle_time * 100
            )
        
        # Tool Change Efficiency: tool_changes per minute of cycle time
        if self.metrics.total_cycle_time > 0:
            cycle_minutes = self.metrics.total_cycle_time / 60.0
            self.metrics.tool_change_efficiency = (
                self.metrics.tool_changes / cycle_minutes if cycle_minutes > 0 else 0
            )
            
        # Spindle Efficiency: active spindle time / total time
        if self.metrics.total_cycle_time > 0:
            self.metrics.spindle_efficiency = (
                self.metrics.spindle_time / self.metrics.total_cycle_time * 100
            )
            
        # Program Efficiency Score: weighted combination
        cutting_score = min(self.metrics.cutting_efficiency / 70 * 100, 100)  # normalize to 70% target
        tool_penalty = max(0, 100 - (self.metrics.tool_change_efficiency * 20))  # penalty for excess tools
        spindle_score = min(self.metrics.spindle_efficiency / 80 * 100, 100)  # normalize to 80% target
        
        self.metrics.program_efficiency_score = (
            cutting_score * 0.5 +      # 50% weight on cutting efficiency
            tool_penalty * 0.3 +       # 30% weight on tool efficiency
            spindle_score * 0.2        # 20% weight on spindle efficiency
        )
        
    def _classify_efficiency(self) -> None:
        """Classify efficiency into grades"""
        
        # Overall Cycle Efficiency Classification
        cutting_eff = self.metrics.cutting_efficiency
        if cutting_eff >= self.thresholds['cutting_efficiency']['excellent']:
            self.classification.cutting_grade = "🟢 EXCELLENT"
        elif cutting_eff >= self.thresholds['cutting_efficiency']['good']:
            self.classification.cutting_grade = "🟡 GOOD"
        else:
            self.classification.cutting_grade = "🔴 POOR"
            
        # Tool Change Efficiency Classification  
        tool_rate = self.metrics.tool_change_efficiency
        if tool_rate <= self.thresholds['tool_changes_per_min']['excellent']:
            self.classification.tool_grade = "🟢 EXCELLENT"
        elif tool_rate <= self.thresholds['tool_changes_per_min']['good']:
            self.classification.tool_grade = "🟡 GOOD" 
        else:
            self.classification.tool_grade = "🔴 POOR"
            
        # Spindle Efficiency Classification
        spindle_eff = self.metrics.spindle_efficiency  
        if spindle_eff >= self.thresholds['spindle_efficiency']['excellent']:
            self.classification.spindle_grade = "🟢 EXCELLENT"
        elif spindle_eff >= self.thresholds['spindle_efficiency']['good']:
            self.classification.spindle_grade = "🟡 GOOD"
        else:
            self.classification.spindle_grade = "🔴 POOR"
            
        # Overall Grade (based on program efficiency score)
        overall_score = self.metrics.program_efficiency_score
        self.classification.overall_score = overall_score
        
        if overall_score >= 80:
            self.classification.overall_grade = "🟢 EXCELLENT"
        elif overall_score >= 60:
            self.classification.overall_grade = "🟡 GOOD"
        else:
            self.classification.overall_grade = "🔴 POOR"
            
    def _generate_recommendations(self) -> None:
        """Generate optimization recommendations"""
        
        # Analyze strengths
        if self.metrics.cutting_efficiency >= 70:
            self.classification.strengths.append("High cutting efficiency - excellent material removal rate")
        if self.metrics.tool_change_efficiency <= 1.5:
            self.classification.strengths.append("Optimized tool usage - minimal tool changes")
        if self.metrics.spindle_efficiency >= 80:
            self.classification.strengths.append("Excellent spindle utilization")
        if self.metrics.rapid_distance < self.metrics.cutting_distance * 2:
            self.classification.strengths.append("Minimal rapid traverse - good path optimization")
            
        # Analyze weaknesses and generate recommendations
        if self.metrics.cutting_efficiency < 50:
            self.classification.weaknesses.append("Low cutting efficiency - excessive overhead time")
            self.classification.recommendations.extend([
                "Reduce tool changes by combining operations",
                "Optimize rapid traverse paths",
                "Review cycle selection - consider more efficient cycles"
            ])
            
        if self.metrics.tool_change_efficiency > 2.5:
            self.classification.weaknesses.append("Excessive tool changes per minute")
            self.classification.recommendations.extend([
                "Consolidate operations using fewer tools",
                "Group operations by tool to minimize changes",
                "Consider multi-purpose tools"
            ])
            
        if self.metrics.spindle_efficiency < 60:
            self.classification.weaknesses.append("Poor spindle utilization")
            self.classification.recommendations.extend([
                "Reduce spindle start/stop cycles", 
                "Group cutting operations to maintain spindle running",
                "Optimize feed rates for continuous cutting"
            ])
            
        if self.metrics.rapid_distance > self.metrics.cutting_distance * 3:
            self.classification.weaknesses.append("Excessive rapid traverse distance")
            self.classification.recommendations.extend([
                "Optimize part positioning and clamping",
                "Review operation sequence for better path planning",
                "Consider different approach angles"
            ])
            
        # Generic recommendations based on overall score
        if self.classification.overall_score < 60:
            self.classification.recommendations.extend([
                "Consider CAM strategy review for better efficiency",
                "Analyze part setup for reduced non-cutting time",
                "Review postprocessor settings for optimization"
            ])
            
    def generate_detailed_report(self) -> str:
        """Generate comprehensive efficiency report"""
        report_lines = [
            f"CNC EFFICIENCY ANALYSIS REPORT",
            f"=" * 50,
            f"Program: {os.path.basename(self.nc_file_path)}",
            f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"📊 OVERALL EFFICIENCY CLASSIFICATION",
            f"Overall Grade: {self.classification.overall_grade} ({self.classification.overall_score:.1f}/100)",
            f"",
            f"📈 DETAILED METRICS",
            f"Cycle Time Analysis:",
            f"  Total Cycle Time:     {self.metrics.total_cycle_time/60:.1f} min ({self.metrics.total_cycle_time:.0f} sec)",
            f"  Cutting Time:         {self.metrics.cutting_time/60:.1f} min ({self.metrics.cutting_time:.0f} sec)",
            f"  Rapid Time:          {self.metrics.rapid_time/60:.1f} min ({self.metrics.rapid_time:.0f} sec)",
            f"  Tool Change Time:    {self.metrics.tool_change_time/60:.1f} min ({self.metrics.tool_change_time:.0f} sec)",
            f"  Overhead Time:       {self.metrics.overhead_time/60:.1f} min ({self.metrics.overhead_time:.0f} sec)",
            f"",
            f"Distance Analysis:",
            f"  Total Distance:      {self.metrics.total_distance:.0f} mm",
            f"  Cutting Distance:    {self.metrics.cutting_distance:.0f} mm",
            f"  Rapid Distance:      {self.metrics.rapid_distance:.0f} mm",
            f"",
            f"Operations Count:",
            f"  Tool Changes:        {self.metrics.tool_changes}",
            f"  Spindle Starts:      {self.metrics.spindle_starts}",
            f"  Cycle Calls:         {self.metrics.cycle_calls}",
            f"",
            f"🎯 EFFICIENCY CLASSIFICATIONS",
            f"Cutting Efficiency:      {self.classification.cutting_grade} ({self.metrics.cutting_efficiency:.1f}%)",
            f"  Target: >70% cutting time | Current: {self.metrics.cutting_efficiency:.1f}%",
            f"",
            f"Tool Change Efficiency:  {self.classification.tool_grade} ({self.metrics.tool_change_efficiency:.2f} changes/min)",
            f"  Target: <1.5 changes/min | Current: {self.metrics.tool_change_efficiency:.2f}",
            f"",
            f"Spindle Efficiency:      {self.classification.spindle_grade} ({self.metrics.spindle_efficiency:.1f}%)",
            f"  Target: >80% utilization | Current: {self.metrics.spindle_efficiency:.1f}%",
            f"",
        ]
        
        # Add strengths
        if self.classification.strengths:
            report_lines.extend([
                f"✅ STRENGTHS",
                *[f"  • {strength}" for strength in self.classification.strengths],
                f"",
            ])
            
        # Add weaknesses  
        if self.classification.weaknesses:
            report_lines.extend([
                f"⚠️  AREAS FOR IMPROVEMENT",
                *[f"  • {weakness}" for weakness in self.classification.weaknesses],
                f"",
            ])
            
        # Add recommendations
        if self.classification.recommendations:
            report_lines.extend([
                f"💡 OPTIMIZATION RECOMMENDATIONS",
                *[f"  • {rec}" for rec in self.classification.recommendations],
                f"",
            ])
            
        return '\n'.join(report_lines)
        
    def save_analysis_results(self, output_dir: str = ".") -> Tuple[str, str]:
        """Save analysis results to files"""
        base_name = os.path.splitext(os.path.basename(self.nc_file_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed report
        report_file = os.path.join(output_dir, f"{base_name}_efficiency_report.txt")
        with open(report_file, 'w') as f:
            f.write(self.generate_detailed_report())
            
        # Save raw data as JSON
        data_file = os.path.join(output_dir, f"{base_name}_efficiency_data.json")
        analysis_data = {
            'program': os.path.basename(self.nc_file_path),
            'analysis_timestamp': datetime.now().isoformat(),
            'metrics': asdict(self.metrics),
            'classification': asdict(self.classification),
            'machine_config': asdict(self.config)
        }
        
        with open(data_file, 'w') as f:
            json.dump(analysis_data, f, indent=2)
            
        return report_file, data_file

def analyze_multiple_programs(nc_files: List[str], output_dir: str = ".") -> None:
    """Analyze multiple NC programs and generate comparison report"""
    
    all_results = []
    
    print(f"🔍 Analyzing {len(nc_files)} NC programs for efficiency...")
    
    for nc_file in nc_files:
        try:
            analyzer = CNCEfficiencyAnalyzer(nc_file)
            metrics, classification = analyzer.analyze_efficiency()
            
            all_results.append({
                'program': os.path.basename(nc_file),
                'metrics': metrics,
                'classification': classification
            })
            
            # Save individual analysis
            analyzer.save_analysis_results(output_dir)
            
        except Exception as e:
            print(f"❌ Error analyzing {nc_file}: {e}")
            
    # Generate comparison report
    if all_results:
        _generate_comparison_report(all_results, output_dir)
        
def _generate_comparison_report(results: List[Dict], output_dir: str) -> None:
    """Generate comparison report for multiple programs"""
    
    report_lines = [
        "CNC EFFICIENCY COMPARISON REPORT",
        "=" * 60,
        f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Programs Analyzed: {len(results)}",
        "",
        "📊 EFFICIENCY COMPARISON",
        f"{'Program':<20} {'Overall':<12} {'Cutting%':<10} {'Tools/min':<10} {'Score':<8}",
        "-" * 60
    ]
    
    for result in sorted(results, key=lambda x: x['metrics'].program_efficiency_score, reverse=True):
        program = result['program'][:18]  # Truncate long names
        overall = result['classification'].overall_grade.split()[1]  # Remove emoji
        cutting = f"{result['metrics'].cutting_efficiency:.1f}%"
        tools = f"{result['metrics'].tool_change_efficiency:.2f}"
        score = f"{result['metrics'].program_efficiency_score:.1f}"
        
        report_lines.append(f"{program:<20} {overall:<12} {cutting:<10} {tools:<10} {score:<8}")
        
    # Save comparison report
    comparison_file = os.path.join(output_dir, f"efficiency_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(comparison_file, 'w') as f:
        f.write('\n'.join(report_lines))
        
    print(f"📋 Comparison report saved: {comparison_file}")

def main():
    """Main function for command line usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("CNC Efficiency Analyzer")
        print("Usage: python CNC_Efficiency_Analyzer.py <nc_file> [output_dir]")
        print("   or: python CNC_Efficiency_Analyzer.py *.nc [output_dir]")
        return
        
    nc_files = sys.argv[1:-1] if len(sys.argv) > 2 else [sys.argv[1]]
    output_dir = sys.argv[-1] if len(sys.argv) > 2 and not sys.argv[-1].endswith('.nc') else "."
    
    if len(nc_files) == 1:
        # Single file analysis
        analyzer = CNCEfficiencyAnalyzer(nc_files[0])
        metrics, classification = analyzer.analyze_efficiency()
        
        print(analyzer.generate_detailed_report())
        
        report_file, data_file = analyzer.save_analysis_results(output_dir)
        print(f"\n📄 Report saved: {report_file}")
        print(f"📄 Data saved: {data_file}")
        
    else:
        # Multiple file analysis
        analyze_multiple_programs(nc_files, output_dir)

if __name__ == "__main__":
    main()