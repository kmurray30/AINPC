"""
Report Generator for Conversation Evaluation
Generates CSV summary reports from JSON evaluation reports
"""
import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


def generate_csv_summary(run_folder: Path) -> Path:
    """
    Generate a CSV summary report from all JSON reports in the run folder
    
    Args:
        run_folder: Path to the folder containing JSON report files
        
    Returns:
        Path to the generated summary.csv file
        
    Raises:
        ValueError: If run_folder doesn't exist or contains no reports
    """
    if not run_folder.exists():
        raise ValueError(f"Run folder does not exist: {run_folder}")
    
    # Find all JSON report files
    report_files = list(run_folder.glob("EvalReport_*_npc*.json"))
    
    if not report_files:
        raise ValueError(f"No evaluation reports found in {run_folder}")
    
    # Parse reports and extract data
    # Structure: {proposition_text: {npc_type: score}}
    proposition_scores = defaultdict(dict)
    npc_types = set()
    
    for report_file in report_files:
        # Extract NPC type from filename (e.g., "EvalReport_test_name_npc0.json")
        npc_type = _extract_npc_type(report_file.name)
        if npc_type:
            npc_types.add(npc_type)
        
        # Parse the JSON report
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        # Extract propositions and scores
        propositions = _extract_propositions_and_scores(report)
        
        for prop_text, score in propositions:
            proposition_scores[prop_text][npc_type] = score
    
    # Sort NPC types for consistent column ordering
    npc_types_sorted = sorted(npc_types)
    
    # Generate CSV
    csv_path = run_folder / "summary.csv"
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header row
        header = [''] + npc_types_sorted
        writer.writerow(header)
        
        # Write data rows
        for prop_text in sorted(proposition_scores.keys()):
            row = [prop_text]
            for npc_type in npc_types_sorted:
                score = proposition_scores[prop_text].get(npc_type)
                if score is not None:
                    # Convert 0.0-1.0 to percentage string
                    percentage = f"{int(score * 100)}%"
                    row.append(percentage)
                else:
                    row.append('')  # Empty cell for missing data
            writer.writerow(row)
        
        # Write Total row (average of all scores per NPC)
        total_row = ['Total']
        for npc_type in npc_types_sorted:
            scores = [
                proposition_scores[prop][npc_type]
                for prop in proposition_scores
                if npc_type in proposition_scores[prop]
            ]
            if scores:
                avg_score = sum(scores) / len(scores)
                total_row.append(f"{int(avg_score * 100)}%")
            else:
                total_row.append('')
        writer.writerow(total_row)
    
    return csv_path


def _extract_npc_type(filename: str) -> str:
    """
    Extract NPC type from report filename
    
    Args:
        filename: Report filename (e.g., "EvalReport_test_name_npc0.json")
        
    Returns:
        NPC type string (e.g., "npc0") or None if not found
    """
    parts = filename.replace('.json', '').split('_')
    for part in parts:
        # Match npc followed by a digit (npc0, npc1, npc2, etc.)
        if part.startswith('npc') and len(part) > 3 and part[3:].isdigit():
            return part
    return None


def _extract_propositions_and_scores(report: dict) -> List[Tuple[str, float]]:
    """
    Extract proposition texts and their scores from a report
    
    Args:
        report: Parsed JSON report dictionary
        
    Returns:
        List of tuples (proposition_text, score)
    """
    propositions = []
    
    try:
        # Navigate to evaluations
        assistant_cases = report.get("assistant_prompt_cases", [])
        if not assistant_cases:
            return propositions
        
        user_prompt_cases = assistant_cases[0].get("user_prompt_cases", [])
        
        for user_case in user_prompt_cases:
            evaluations = user_case.get("evaluations", [])
            
            for evaluation in evaluations:
                # Extract proposition
                prop = evaluation.get("evaluation_proposition", {})
                antecedent = prop.get("antecedent", {})
                consequent = prop.get("consequent", {})
                
                # Format as "antecedent -> consequent"
                antecedent_text = antecedent.get("value", "")
                consequent_text = consequent.get("value", "")
                
                if antecedent_text and consequent_text:
                    prop_text = f"{antecedent_text} -> {consequent_text}"
                elif consequent_text:
                    # Handle case where there's no antecedent
                    prop_text = consequent_text
                else:
                    continue  # Skip if we can't form a meaningful proposition
                
                # Extract score
                score = evaluation.get("result_score", 0.0)
                
                propositions.append((prop_text, score))
    
    except (KeyError, IndexError, TypeError) as e:
        # Handle malformed reports gracefully
        print(f"Warning: Error parsing report - {e}")
    
    return propositions

