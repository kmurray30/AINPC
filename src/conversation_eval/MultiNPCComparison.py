import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
import json

from src.conversation_eval.EvalReports import EvalReport
from src.conversation_eval.evaluations.EvalRunner import EvalRunner
from src.conversation_eval import EvalUtils


@dataclass
class NPCPerformanceMetrics:
    """Performance metrics for a single NPC"""
    npc_type: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    pass_rate: float = 0.0
    avg_conversation_length: float = 0.0
    total_tokens: int = 0
    test_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonReport:
    """Comparison report across multiple NPCs"""
    test_suite_name: str
    npc_metrics: Dict[str, NPCPerformanceMetrics] = field(default_factory=dict)
    best_performing_npc: str = ""
    performance_summary: str = ""
    detailed_analysis: Dict[str, Any] = field(default_factory=dict)


class MultiNPCComparison:
    """System for running tests across multiple NPC types and comparing results"""
    
    def __init__(self, test_suite_dir: Path):
        self.test_suite_dir = test_suite_dir
        self.available_npcs = list(EvalRunner.NPC_TYPES.keys())
    
    def run_comparison(self, test_files: List[str], npcs_to_test: List[str] = None) -> ComparisonReport:
        """
        Run comparison across multiple NPCs for given test files
        
        Args:
            test_files: List of test file names to run
            npcs_to_test: List of NPC types to test (defaults to all available)
            
        Returns:
            ComparisonReport with results across all NPCs
        """
        if npcs_to_test is None:
            npcs_to_test = self.available_npcs
        
        comparison_report = ComparisonReport(
            test_suite_name=self.test_suite_dir.name
        )
        
        # Run tests for each NPC type
        for npc_type in npcs_to_test:
            print(f"Running tests for {npc_type}...")
            npc_metrics = self._run_tests_for_npc(test_files, npc_type)
            comparison_report.npc_metrics[npc_type] = npc_metrics
        
        # Analyze results
        self._analyze_comparison(comparison_report)
        
        return comparison_report
    
    def _run_tests_for_npc(self, test_files: List[str], npc_type: str) -> NPCPerformanceMetrics:
        """Run all test files for a specific NPC type"""
        metrics = NPCPerformanceMetrics(npc_type=npc_type)
        
        for test_file in test_files:
            test_path = self.test_suite_dir / test_file
            if not test_path.exists():
                print(f"Warning: Test file {test_file} not found, skipping...")
                continue
            
            try:
                # Run the test by executing it with the NPC type as argument
                result = self._execute_test_file(test_path, npc_type)
                
                # Update metrics
                metrics.total_tests += 1
                if result.get('passed', False):
                    metrics.passed_tests += 1
                else:
                    metrics.failed_tests += 1
                
                metrics.total_tokens += result.get('tokens', 0)
                metrics.test_results[test_file] = result
                
            except Exception as e:
                print(f"Error running {test_file} with {npc_type}: {e}")
                metrics.total_tests += 1
                metrics.failed_tests += 1
                metrics.test_results[test_file] = {
                    'passed': False,
                    'error': str(e)
                }
        
        # Calculate derived metrics
        if metrics.total_tests > 0:
            metrics.pass_rate = metrics.passed_tests / metrics.total_tests
        
        return metrics
    
    def _execute_test_file(self, test_path: Path, npc_type: str) -> Dict[str, Any]:
        """Execute a test file with specified NPC type and parse results"""
        try:
            print(f"  Running {test_path.name} with {npc_type}...")
            
            # Execute the test file as a subprocess
            result = subprocess.run(
                [sys.executable, str(test_path), npc_type],
                cwd=test_path.parent,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                print(f"    ⚠ Test failed with return code {result.returncode}")
                print(f"    Error output: {result.stderr}")
                return {
                    'passed': False,
                    'tokens': 0,
                    'conversation_length': 0,
                    'error': f"Process failed: {result.stderr}",
                    'details': f"Return code: {result.returncode}"
                }
            
            # Look for generated report files
            report_file = self._find_report_file(test_path, npc_type)
            
            if report_file:
                return self._parse_report_file(report_file)
            else:
                # If no report file found, try to parse from stdout
                return self._parse_stdout_output(result.stdout)
                
        except subprocess.TimeoutExpired:
            return {
                'passed': False,
                'tokens': 0,
                'conversation_length': 0,
                'error': "Test timed out after 5 minutes",
                'details': "Timeout"
            }
        except Exception as e:
            return {
                'passed': False,
                'tokens': 0,
                'conversation_length': 0,
                'error': str(e),
                'details': f"Exception during execution: {type(e).__name__}"
            }
    
    def _find_report_file(self, test_path: Path, npc_type: str) -> Path:
        """Find the generated report file for a test"""
        test_name = test_path.stem
        
        # Look for report files in common locations
        possible_locations = [
            test_path.parent / "reports",
            test_path.parent,
            Path.cwd() / "reports"
        ]
        
        for location in possible_locations:
            if not location.exists():
                continue
                
            # Look for files matching the pattern
            for report_file in location.glob(f"*{test_name}*{npc_type}*.json"):
                return report_file
            
            # Also look for recent files that might be the report
            json_files = list(location.glob("*.json"))
            if json_files:
                # Get the most recent JSON file
                recent_file = max(json_files, key=lambda f: f.stat().st_mtime)
                return recent_file
        
        return None
    
    def _parse_report_file(self, report_file: Path) -> Dict[str, Any]:
        """Parse an evaluation report file"""
        try:
            with open(report_file, 'r') as f:
                report_data = json.load(f)
            
            # Extract metrics from the report structure
            tokens = report_data.get('tokens', 0)
            
            # Look for evaluation results
            passed = False
            conversation_length = 0
            
            if 'assistant_prompt_cases' in report_data:
                for case in report_data['assistant_prompt_cases']:
                    if 'user_prompt_cases' in case:
                        for user_case in case['user_prompt_cases']:
                            if 'evaluations' in user_case:
                                # Check if any evaluations passed
                                for evaluation in user_case['evaluations']:
                                    if evaluation.get('pass_fail') == 'Pass':
                                        passed = True
                            
                            # Get conversation length from conversations
                            if 'conversations' in user_case:
                                for convo_set in user_case['conversations']:
                                    for convo_name, messages in convo_set.items():
                                        conversation_length = max(conversation_length, len(messages))
            
            return {
                'passed': passed,
                'tokens': tokens,
                'conversation_length': conversation_length,
                'details': f"Parsed from report file {report_file.name}",
                'report_file': str(report_file)
            }
            
        except Exception as e:
            return {
                'passed': False,
                'tokens': 0,
                'conversation_length': 0,
                'error': f"Failed to parse report file: {e}",
                'details': f"Report file: {report_file}"
            }
    
    def _parse_stdout_output(self, stdout: str) -> Dict[str, Any]:
        """Parse test results from stdout if no report file is found"""
        # This is a fallback - try to extract basic info from stdout
        passed = "✓" in stdout or "Pass" in stdout
        
        return {
            'passed': passed,
            'tokens': 0,  # Can't determine from stdout
            'conversation_length': 0,  # Can't determine from stdout
            'details': "Parsed from stdout (limited info)",
            'stdout_sample': stdout[:200] + "..." if len(stdout) > 200 else stdout
        }
    
    def _analyze_comparison(self, report: ComparisonReport) -> None:
        """Analyze comparison results and generate insights"""
        if not report.npc_metrics:
            return
        
        # Find best performing NPC
        best_npc = max(
            report.npc_metrics.keys(),
            key=lambda npc: report.npc_metrics[npc].pass_rate
        )
        report.best_performing_npc = best_npc
        
        # Generate performance summary
        summary_parts = []
        for npc_type, metrics in report.npc_metrics.items():
            summary_parts.append(
                f"{npc_type}: {metrics.passed_tests}/{metrics.total_tests} "
                f"({metrics.pass_rate:.1%} pass rate)"
            )
        
        report.performance_summary = "; ".join(summary_parts)
        
        # Detailed analysis
        report.detailed_analysis = {
            'pass_rates': {npc: metrics.pass_rate for npc, metrics in report.npc_metrics.items()},
            'token_usage': {npc: metrics.total_tokens for npc, metrics in report.npc_metrics.items()},
            'test_counts': {npc: metrics.total_tests for npc, metrics in report.npc_metrics.items()}
        }
    
    def save_comparison_report(self, report: ComparisonReport, output_path: Path) -> None:
        """Save comparison report to file"""
        report_data = {
            'test_suite_name': report.test_suite_name,
            'best_performing_npc': report.best_performing_npc,
            'performance_summary': report.performance_summary,
            'detailed_analysis': report.detailed_analysis,
            'npc_metrics': {}
        }
        
        # Convert NPCPerformanceMetrics to dict
        for npc_type, metrics in report.npc_metrics.items():
            report_data['npc_metrics'][npc_type] = {
                'npc_type': metrics.npc_type,
                'total_tests': metrics.total_tests,
                'passed_tests': metrics.passed_tests,
                'failed_tests': metrics.failed_tests,
                'pass_rate': metrics.pass_rate,
                'total_tokens': metrics.total_tokens,
                'test_results': metrics.test_results
            }
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"Comparison report saved to {output_path}")
    
    def print_comparison_summary(self, report: ComparisonReport) -> None:
        """Print a formatted summary of the comparison results"""
        print(f"\n{'='*60}")
        print(f"Multi-NPC Comparison Report: {report.test_suite_name}")
        print(f"{'='*60}")
        
        print(f"\nBest Performing NPC: {report.best_performing_npc}")
        print(f"Performance Summary: {report.performance_summary}")
        
        print(f"\nDetailed Results:")
        print(f"{'NPC Type':<10} {'Tests':<8} {'Passed':<8} {'Pass Rate':<12} {'Tokens':<10}")
        print(f"{'-'*50}")
        
        for npc_type, metrics in report.npc_metrics.items():
            print(f"{npc_type:<10} {metrics.total_tests:<8} {metrics.passed_tests:<8} "
                  f"{metrics.pass_rate:.1%}{'':>4} {metrics.total_tokens:<10}")
        
        print(f"\n{'='*60}")


def main():
    """Example usage of MultiNPCComparison"""
    if len(sys.argv) < 2:
        print("Usage: python MultiNPCComparison.py <test_suite_directory>")
        sys.exit(1)
    
    test_suite_dir = Path(sys.argv[1])
    if not test_suite_dir.exists():
        print(f"Test suite directory {test_suite_dir} does not exist")
        sys.exit(1)
    
    # Find all test files in the directory
    test_files = [f.name for f in test_suite_dir.glob("*_test.py")]
    
    if not test_files:
        print(f"No test files found in {test_suite_dir}")
        sys.exit(1)
    
    print(f"Found test files: {test_files}")
    
    # Run comparison
    comparator = MultiNPCComparison(test_suite_dir)
    report = comparator.run_comparison(test_files)
    
    # Print and save results
    comparator.print_comparison_summary(report)
    
    output_path = test_suite_dir / f"comparison_report_{test_suite_dir.name}.json"
    comparator.save_comparison_report(report, output_path)


if __name__ == "__main__":
    main()
