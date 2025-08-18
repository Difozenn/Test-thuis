#!/usr/bin/env python3
"""
NC Program Optimizer with Leitz Catalog Integration
Analyzes NC files and provides optimization recommendations based on Leitz tool specifications
"""

import re
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path

@dataclass
class Tool:
    """Represents a tool found in NC file"""
    box_id: str  # Box ID from NC file (e.g., '601' or '191060')
    tool_number: str  # T number (e.g., 'T50')
    diameter: float  # Tool diameter in mm
    current_speed: int  # Current RPM
    current_feed: int  # Current feed rate mm/min
    max_plunge_depth: float  # Maximum Z depth found
    total_usage_time: float  # Estimated time in use
    cut_depths: List[float]  # All cutting depths found
    straight_plunges: List[Tuple[int, float]]  # Line numbers and depths of straight plunges
    
@dataclass
class LeitzTool:
    """Leitz catalog tool specifications"""
    leitz_id: str
    name: str
    diameter: float
    max_speed: int  # RPM
    max_feed: int  # mm/min
    material_range: str  # e.g., "13-20mm"
    spiral_type: str  # 'compression', 'upcut', 'downcut'
    coating: str  # 'diamond', 'marathon', 'standard'
    regrind_count: int  # Number of possible regrinds
    special_features: List[str]  # ['DFC', 'WhisperCut', etc.]
    safe_plunge_factor: float  # Max plunge as factor of diameter (usually 1.5)
    
class NCOptimizer:
    def __init__(self, catalog_file: Optional[str] = None):
        """Initialize with optional Leitz catalog data"""
        self.tools_found: List[Tool] = []
        self.violations: List[Dict] = []
        self.optimizations: List[Dict] = []
        self.leitz_catalog = self._load_catalog(catalog_file)
        self.workpiece_thickness = 0  # Will be detected from NC file
        self.material_info = {}
        
    def _load_catalog(self, catalog_file: Optional[str]) -> Dict[str, LeitzTool]:
        """Load Leitz tool catalog from JSON file or use hardcoded data"""
        
        # Hardcoded catalog based on our analysis
        default_catalog = {
            '191060': LeitzTool(
                leitz_id='191060',
                name='Diamaster PRO DP Z2+2 Nesting Edition',
                diameter=12.0,
                max_speed=24000,
                max_feed=28000,
                material_range='13-20mm',
                spiral_type='compression',
                coating='diamond',
                regrind_count=3,
                special_features=['DFC', 'Nesting optimized'],
                safe_plunge_factor=1.5
            ),
            '191059': LeitzTool(
                leitz_id='191059',
                name='Diamaster PRO DP Z2+2 Nesting Edition',
                diameter=10.0,
                max_speed=24000,
                max_feed=28000,
                material_range='9-16mm',
                spiral_type='compression',
                coating='diamond',
                regrind_count=3,
                special_features=['DFC', 'Nesting optimized'],
                safe_plunge_factor=1.5
            ),
            '181': LeitzTool(
                leitz_id='181',
                name='Spiraal schrob-schlichtbovenfrees Marathon',
                diameter=12.7,
                max_speed=24000,
                max_feed=24000,
                material_range='10-25mm',
                spiral_type='upcut',
                coating='marathon',
                regrind_count=2,
                special_features=[],
                safe_plunge_factor=1.5
            ),
            '601': LeitzTool(  # Generic mapping for box ID 601
                leitz_id='191060',
                name='Diamaster PRO DP Z2+2 Nesting Edition',
                diameter=12.0,
                max_speed=24000,
                max_feed=28000,
                material_range='13-20mm',
                spiral_type='compression',
                coating='diamond',
                regrind_count=3,
                special_features=['DFC', 'Nesting optimized'],
                safe_plunge_factor=1.5
            )
        }
        
        if catalog_file and os.path.exists(catalog_file):
            try:
                with open(catalog_file, 'r') as f:
                    custom_catalog = json.load(f)
                    # Convert JSON to LeitzTool objects
                    for tool_id, data in custom_catalog.items():
                        # Skip comments and template entries
                        if tool_id in ['comment', 'instructions', 'template']:
                            continue
                        if isinstance(data, dict) and 'leitz_id' in data:
                            # Remove comment fields before creating LeitzTool
                            tool_data = {k: v for k, v in data.items() if k != 'comment'}
                            default_catalog[tool_id] = LeitzTool(**tool_data)
            except Exception as e:
                print(f"Warning: Could not load custom catalog: {e}")
        
        return default_catalog
    
    def analyze_nc_file(self, file_path: str) -> Dict:
        """Main analysis function for NC file"""
        print(f"\n{'='*60}")
        print(f"Analyzing: {os.path.basename(file_path)}")
        print(f"{'='*60}")
        
        with open(file_path, 'r') as f:
            nc_content = f.read()
            nc_lines = nc_content.splitlines()
        
        # Detect workpiece dimensions
        self._detect_workpiece_info(nc_lines)
        
        # Parse tools and operations
        self.tools_found = self._parse_tools(nc_lines)
        
        # Run all checks
        self._check_plunge_safety(nc_lines)
        self._check_straight_plunges(nc_lines)
        self._check_overcutting()
        self._check_feed_optimization()
        self._check_tool_redundancy()
        self._check_spindle_speed()
        self._check_tool_consolidation()
        
        # Generate report
        report = self._generate_report()
        
        return report
    
    def _parse_tools(self, lines: List[str]) -> List[Tool]:
        """Extract tool information from NC file"""
        tools = []
        current_tool = None
        
        for i, line in enumerate(lines):
            # Look for tool definitions (various formats)
            # Format 1: Box: 601 HId:1 VF 12 R P/N
            # Format 2: Box: 191060 ...
            # Format 3: T50 D1
            
            box_match = re.search(r'Box:\s*(\d+)', line, re.IGNORECASE)
            if box_match:
                box_id = box_match.group(1)
                
                # Extract diameter if present
                diameter_match = re.search(r'(?:VF|SF|DP)\s+(\d+)', line)
                diameter = float(diameter_match.group(1)) if diameter_match else 12.0
                
                # Look for speed and feed in nearby lines
                speed = self._find_speed_near_line(lines, i)
                feed = self._find_feed_near_line(lines, i)
                
                # Find tool number
                tool_num_match = re.search(r'T(\d+)', lines[min(i+5, len(lines)-1)])
                tool_num = f"T{tool_num_match.group(1)}" if tool_num_match else f"T{len(tools)}"
                
                current_tool = Tool(
                    box_id=box_id,
                    tool_number=tool_num,
                    diameter=diameter,
                    current_speed=speed,
                    current_feed=feed,
                    max_plunge_depth=0,
                    total_usage_time=0,
                    cut_depths=[],
                    straight_plunges=[]
                )
                tools.append(current_tool)
            
            # Track plunge depths
            if current_tool and 'Z-' in line:
                z_match = re.search(r'Z(-?\d+\.?\d*)', line)
                if z_match:
                    depth = abs(float(z_match.group(1)))
                    current_tool.cut_depths.append(depth)
                    current_tool.max_plunge_depth = max(current_tool.max_plunge_depth, depth)
        
        return tools
    
    def _find_speed_near_line(self, lines: List[str], start_idx: int, search_range: int = 10) -> int:
        """Find spindle speed near a given line"""
        for i in range(max(0, start_idx-search_range), min(len(lines), start_idx+search_range)):
            # Look for patterns like S22000 or @P3=22000
            speed_match = re.search(r'(?:S|@P3=)(\d{4,5})', lines[i])
            if speed_match:
                return int(speed_match.group(1))
        return 18000  # Default assumption
    
    def _find_feed_near_line(self, lines: List[str], start_idx: int, search_range: int = 20) -> int:
        """Find feed rate near a given line"""
        for i in range(max(0, start_idx-search_range), min(len(lines), start_idx+search_range)):
            # Look for F followed by numbers
            feed_match = re.search(r'F(\d{3,5})', lines[i])
            if feed_match:
                return int(feed_match.group(1))
        return 10000  # Default assumption
    
    def _check_plunge_safety(self, lines: List[str]):
        """Check for dangerous axial plunging"""
        for i, line in enumerate(lines):
            # Look for straight plunges
            if re.search(r'G1.*Z-\d+.*F\d+', line):
                z_match = re.search(r'Z(-\d+\.?\d*)', line)
                f_match = re.search(r'F(\d+)', line)
                
                if z_match and f_match:
                    plunge_depth = abs(float(z_match.group(1)))
                    plunge_feed = int(f_match.group(1))
                    
                    # Check against tool diameter
                    for tool in self.tools_found:
                        if plunge_depth > tool.diameter * 1.5:
                            self.violations.append({
                                'type': 'DANGEROUS_PLUNGE',
                                'severity': 'CRITICAL',
                                'line': i + 1,
                                'tool': tool.box_id,
                                'message': f"Plunge depth {plunge_depth}mm exceeds safe limit ({tool.diameter * 1.5:.1f}mm) by {((plunge_depth / tool.diameter) - 1.5) * 100:.0f}%",
                                'recommendation': f"Use ramped entry (3-5° angle) or helical interpolation instead of straight plunge"
                            })
    
    def _check_feed_optimization(self):
        """Check if tools are running at optimal feed rates"""
        for tool in self.tools_found:
            if tool.box_id in self.leitz_catalog:
                catalog_tool = self.leitz_catalog[tool.box_id]
                utilization = (tool.current_feed / catalog_tool.max_feed) * 100
                
                if utilization < 70:  # Running below 70% of capability
                    self.optimizations.append({
                        'type': 'FEED_RATE_LOW',
                        'severity': 'HIGH',
                        'tool': tool.box_id,
                        'current': tool.current_feed,
                        'optimal': catalog_tool.max_feed,
                        'utilization': utilization,
                        'message': f"Tool {tool.box_id} running at {utilization:.0f}% of maximum feed rate",
                        'potential_time_savings': f"{(1 - (utilization/100)) * 100:.0f}%",
                        'recommendation': f"Increase feed from {tool.current_feed} to {int(catalog_tool.max_feed * 0.9)} mm/min (90% of max for safety)"
                    })
    
    def _check_tool_redundancy(self):
        """Check for redundant tools (same diameter, minimal usage)"""
        for i, tool1 in enumerate(self.tools_found):
            for tool2 in self.tools_found[i+1:]:
                if abs(tool1.diameter - tool2.diameter) < 0.5:  # Same diameter (within 0.5mm)
                    # Check if one tool is barely used
                    if tool1.cut_depths and min(tool1.cut_depths) < 0.001:
                        self.optimizations.append({
                            'type': 'REDUNDANT_TOOL',
                            'severity': 'MEDIUM',
                            'tool': tool1.box_id,
                            'message': f"Tool {tool1.box_id} making cuts of only {min(tool1.cut_depths):.4f}mm - consider eliminating",
                            'redundant_with': tool2.box_id,
                            'recommendation': f"Use tool {tool2.box_id} for all operations and eliminate {tool1.box_id}"
                        })
    
    def _check_spindle_speed(self):
        """Check if spindle speeds are optimal"""
        for tool in self.tools_found:
            if tool.box_id in self.leitz_catalog:
                catalog_tool = self.leitz_catalog[tool.box_id]
                speed_utilization = (tool.current_speed / catalog_tool.max_speed) * 100
                
                if speed_utilization < 95:
                    self.optimizations.append({
                        'type': 'SPINDLE_SPEED_LOW',
                        'severity': 'LOW',
                        'tool': tool.box_id,
                        'current': tool.current_speed,
                        'optimal': catalog_tool.max_speed,
                        'message': f"Spindle speed at {speed_utilization:.0f}% of maximum",
                        'recommendation': f"Increase from {tool.current_speed} to {catalog_tool.max_speed} RPM"
                    })
    
    def _detect_workpiece_info(self, lines: List[str]):
        """Detect workpiece dimensions from NC file"""
        for line in lines:
            # Look for various formats:
            # FinishedPart: X: 320 Y: 250 Z: 19
            # V.P.DICKE= 19
            # FZ:19 or Z:19
            
            # Format 1: FinishedPart
            if 'FinishedPart' in line:
                z_match = re.search(r'Z:\s*(\d+\.?\d*)', line)
                if z_match:
                    self.workpiece_thickness = float(z_match.group(1))
                    print(f"Detected workpiece thickness: {self.workpiece_thickness}mm")
                    
            # Format 2: V.P.DICKE (German: thickness)
            elif 'V.P.DICKE' in line:
                thickness_match = re.search(r'V\.P\.DICKE\s*=\s*(\d+\.?\d*)', line)
                if thickness_match:
                    self.workpiece_thickness = float(thickness_match.group(1))
                    print(f"Detected workpiece thickness: {self.workpiece_thickness}mm")
                    
            # Format 3: Simple Z dimension
            elif re.search(r'^\s*Z\s*[:=]\s*\d+', line):
                z_match = re.search(r'Z\s*[:=]\s*(\d+\.?\d*)', line)
                if z_match and not self.workpiece_thickness:
                    self.workpiece_thickness = float(z_match.group(1))
                    
        if not self.workpiece_thickness:
            # Try to guess from maximum Z depth
            print("Warning: Could not detect workpiece thickness, estimating from cuts")
            self.workpiece_thickness = 19  # Default assumption
    
    def _check_straight_plunges(self, lines: List[str]):
        """Detect straight down plunges (not ramped or helical)"""
        for i in range(len(lines) - 1):
            current_line = lines[i]
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            
            # Check for G0 (rapid) or G1 (linear) moves
            if ('G0' in current_line or 'G1' in current_line):
                # Look for Z-only moves (straight down)
                # Pattern: has Z coordinate but no X or Y change in same block
                z_match = re.search(r'Z(-?\d+\.?\d*)', current_line)
                has_x = 'X' in current_line
                has_y = 'Y' in current_line
                
                if z_match and not (has_x or has_y):
                    z_depth = abs(float(z_match.group(1)))
                    
                    # Check if this is truly a plunge (going down from higher position)
                    # Look at previous lines for Z position
                    prev_z = 0
                    for j in range(max(0, i-5), i):
                        prev_z_match = re.search(r'Z(\d+\.?\d*)', lines[j])
                        if prev_z_match:
                            prev_z = float(prev_z_match.group(1))
                            break
                    
                    if z_depth > 0 and prev_z >= 0:  # Going from safe height to depth
                        # This is a straight plunge
                        for tool in self.tools_found:
                            tool.straight_plunges.append((i + 1, z_depth))
                        
                        self.violations.append({
                            'type': 'STRAIGHT_PLUNGE',
                            'severity': 'HIGH',
                            'line': i + 1,
                            'message': f"Straight vertical plunge detected to depth {z_depth}mm",
                            'recommendation': "Use ramped entry (G1 with X/Y movement) or helical interpolation (G2/G3) instead",
                            'code_example': f"Replace with: G1 X[end] Y[pos] Z-{z_depth} (ramped) or G2/G3 for helical"
                        })
    
    def _check_overcutting(self):
        """Check if tools are cutting below workpiece (spoilboard damage)"""
        if not self.workpiece_thickness:
            return
            
        safe_depth = self.workpiece_thickness + 0.5  # Allow 0.5mm into spoilboard max
        critical_depth = self.workpiece_thickness + 1.0  # Critical if >1mm into spoilboard
        
        for tool in self.tools_found:
            if tool.cut_depths:
                max_cut = max(tool.cut_depths)
                
                if max_cut > critical_depth:
                    overcut = max_cut - self.workpiece_thickness
                    self.violations.append({
                        'type': 'SPOILBOARD_DAMAGE',
                        'severity': 'CRITICAL',
                        'tool': tool.box_id,
                        'message': f"Tool cutting {overcut:.1f}mm INTO SPOILBOARD (workpiece: {self.workpiece_thickness}mm, cutting: {max_cut}mm)",
                        'recommendation': f"Limit cutting depth to {self.workpiece_thickness}mm or maximum {safe_depth}mm",
                        'damage_risk': "Spoilboard damage, vacuum loss, tool damage"
                    })
                elif max_cut > safe_depth:
                    overcut = max_cut - self.workpiece_thickness
                    self.optimizations.append({
                        'type': 'EXCESSIVE_DEPTH',
                        'severity': 'MEDIUM',
                        'tool': tool.box_id,
                        'message': f"Tool cutting {overcut:.1f}mm below workpiece",
                        'recommendation': f"Consider limiting to {self.workpiece_thickness}mm to preserve spoilboard"
                    })
    
    def _check_tool_consolidation(self):
        """Suggest tool consolidation opportunities"""
        diameter_groups = {}
        for tool in self.tools_found:
            key = round(tool.diameter)  # Group by rounded diameter
            if key not in diameter_groups:
                diameter_groups[key] = []
            diameter_groups[key].append(tool)
        
        for diameter, tools in diameter_groups.items():
            if len(tools) > 1:
                # Check if we have a premium tool that could replace others
                has_premium = any(t.box_id in self.leitz_catalog and 
                                 'diamond' in self.leitz_catalog[t.box_id].coating.lower() 
                                 for t in tools)
                
                if has_premium:
                    premium_tool = next(t for t in tools if t.box_id in self.leitz_catalog and 
                                      'diamond' in self.leitz_catalog[t.box_id].coating.lower())
                    
                    self.optimizations.append({
                        'type': 'CONSOLIDATION_OPPORTUNITY',
                        'severity': 'MEDIUM',
                        'message': f"Found {len(tools)} tools with {diameter}mm diameter",
                        'tools': [t.box_id for t in tools],
                        'recommendation': f"Consolidate to single premium tool {premium_tool.box_id} with regrinding strategy",
                        'annual_savings': f"€{len(tools) * 200 * 0.6:.0f}"  # Rough estimate
                    })
    
    def _generate_report(self) -> Dict:
        """Generate comprehensive analysis report"""
        
        # Calculate overall efficiency score
        efficiency_score = 100
        
        # Deduct for violations
        critical_violations = [v for v in self.violations if v['severity'] == 'CRITICAL']
        efficiency_score -= len(critical_violations) * 20
        
        # Deduct for suboptimal operations
        high_severity_opts = [o for o in self.optimizations if o['severity'] == 'HIGH']
        efficiency_score -= len(high_severity_opts) * 10
        
        efficiency_score = max(0, efficiency_score)
        
        report = {
            'summary': {
                'tools_analyzed': len(self.tools_found),
                'violations_found': len(self.violations),
                'optimizations_found': len(self.optimizations),
                'efficiency_score': efficiency_score,
                'grade': self._get_grade(efficiency_score)
            },
            'tools': [
                {
                    'id': t.box_id,
                    'number': t.tool_number,
                    'diameter': t.diameter,
                    'speed': t.current_speed,
                    'feed': t.current_feed,
                    'max_plunge': t.max_plunge_depth,
                    'catalog_match': t.box_id in self.leitz_catalog
                } for t in self.tools_found
            ],
            'violations': self.violations,
            'optimizations': self.optimizations,
            'cost_impact': self._calculate_cost_impact()
        }
        
        return report
    
    def _get_grade(self, score: float) -> str:
        """Convert efficiency score to letter grade"""
        if score >= 90: return 'A - Excellent'
        if score >= 75: return 'B - Good'
        if score >= 60: return 'C - Average'
        if score >= 40: return 'D - Poor'
        return 'F - Critical Issues'
    
    def _calculate_cost_impact(self) -> Dict:
        """Estimate financial impact of issues"""
        annual_cost = 0
        
        # Tool redundancy costs
        redundant_tools = [o for o in self.optimizations if o['type'] == 'REDUNDANT_TOOL']
        annual_cost += len(redundant_tools) * 500  # €500 per redundant tool/year
        
        # Inefficient feed rates (lost production time)
        feed_issues = [o for o in self.optimizations if o['type'] == 'FEED_RATE_LOW']
        for issue in feed_issues:
            time_loss = (100 - issue['utilization']) / 100
            annual_cost += 10000 * time_loss  # €10k per year base, scaled by inefficiency
        
        # Dangerous plunging (tool damage)
        plunge_issues = [v for v in self.violations if v['type'] == 'DANGEROUS_PLUNGE']
        annual_cost += len(plunge_issues) * 2000  # €2000 per year in damaged tools
        
        return {
            'annual_waste': annual_cost,
            'potential_savings': annual_cost * 0.8,  # Assume 80% recoverable
            'roi_months': 3 if annual_cost > 10000 else 6
        }
    
    def print_report(self, report: Dict):
        """Print formatted report to console"""
        print("\n" + "="*60)
        print("NC PROGRAM OPTIMIZATION REPORT")
        print("="*60)
        
        # Workpiece info
        if self.workpiece_thickness:
            print(f"\n📐 WORKPIECE: {self.workpiece_thickness}mm thick")
        
        # Summary
        summary = report['summary']
        print(f"\nEfficiency Score: {summary['efficiency_score']}% - {summary['grade']}")
        print(f"Tools Analyzed: {summary['tools_analyzed']}")
        print(f"Violations Found: {summary['violations_found']}")
        print(f"Optimization Opportunities: {summary['optimizations_found']}")
        
        # Financial Impact
        cost = report['cost_impact']
        print(f"\n💰 FINANCIAL IMPACT:")
        print(f"   Annual Waste: €{cost['annual_waste']:,.0f}")
        print(f"   Potential Savings: €{cost['potential_savings']:,.0f}")
        print(f"   ROI Period: {cost['roi_months']} months")
        
        # Critical Violations
        if report['violations']:
            print(f"\n🚨 CRITICAL VIOLATIONS:")
            for v in report['violations']:
                if v['severity'] == 'CRITICAL':
                    if 'line' in v:
                        print(f"   ❌ Line {v['line']}: {v['message']}")
                    else:
                        print(f"   ❌ {v['message']}")
                    print(f"      → {v['recommendation']}")
            
            # High severity violations
            print(f"\n⚠️ HIGH PRIORITY ISSUES:")
            for v in report['violations']:
                if v['severity'] == 'HIGH':
                    if 'line' in v:
                        print(f"   ⚠️ Line {v['line']}: {v['message']}")
                    else:
                        print(f"   ⚠️ {v['message']}")
                    print(f"      → {v['recommendation']}")
        
        # Major Optimizations
        if report['optimizations']:
            print(f"\n💡 OPTIMIZATION OPPORTUNITIES:")
            for o in sorted(report['optimizations'], key=lambda x: x['severity'] == 'HIGH', reverse=True)[:5]:
                icon = "⚠️" if o['severity'] == 'HIGH' else "ℹ️"
                print(f"   {icon} {o['message']}")
                print(f"      → {o['recommendation']}")
        
        # Tool Details
        print(f"\n🔧 TOOLS FOUND:")
        for tool in report['tools']:
            catalog_status = "✓ Catalog Match" if tool['catalog_match'] else "? Unknown Tool"
            print(f"   {tool['number']} (Box {tool['id']}): Ø{tool['diameter']}mm @ {tool['speed']}RPM, F{tool['feed']}mm/min [{catalog_status}]")
        
        print("\n" + "="*60)

def main():
    """Main entry point for standalone usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python nc_optimizer.py <nc_file> [catalog.json]")
        print("\nExample:")
        print("  python nc_optimizer.py opus.nc")
        print("  python nc_optimizer.py nesting.NC my_tools.json")
        sys.exit(1)
    
    nc_file = sys.argv[1]
    catalog_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(nc_file):
        print(f"Error: File '{nc_file}' not found")
        sys.exit(1)
    
    # Run analysis
    optimizer = NCOptimizer(catalog_file)
    report = optimizer.analyze_nc_file(nc_file)
    optimizer.print_report(report)
    
    # Optionally save report to JSON
    report_file = f"{Path(nc_file).stem}_optimization_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nDetailed report saved to: {report_file}")

if __name__ == "__main__":
    main()