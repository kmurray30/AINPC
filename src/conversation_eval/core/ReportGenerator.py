"""
Report Generator for Conversation Evaluation
Generates CSV summary reports from JSON evaluation reports
"""
import json
import csv
import math
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


def format_cost_usd(cost_usd: float) -> str:
    """
    Format cost in USD with 2 significant figures to the right of decimal point.
    
    Examples: $435.34, $0.043, $0.00012
    
    Args:
        cost_usd: Cost in USD
        
    Returns:
        Formatted cost string
    """
    if cost_usd == 0.0:
        return "$0.00"
    
    # For costs >= $1, use 2 decimal places
    if cost_usd >= 1.0:
        return f"${cost_usd:.2f}"
    
    # For costs < $1, find how many decimal places we need for 2 sig figs
    if cost_usd > 0:
        # Number of decimal places needed = leading zeros + 2 sig figs
        decimal_places = -math.floor(math.log10(cost_usd)) + 1
        return f"${cost_usd:.{decimal_places}f}"
    
    return "$0.00"


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
    # Structure: {npc_type: total_cost}
    proposition_scores = defaultdict(dict)
    proposition_costs = defaultdict(dict)  # Track costs per proposition per NPC
    npc_total_costs = defaultdict(float)  # Track total cost per NPC
    npc_types = set()
    
    for report_file in report_files:
        # Extract NPC type from filename (e.g., "EvalReport_test_name_npc0.json")
        npc_type = _extract_npc_type(report_file.name)
        if npc_type:
            npc_types.add(npc_type)
        
        # Parse the JSON report
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        # Extract propositions, scores, and costs
        propositions = _extract_propositions_scores_and_costs(report)
        
        for prop_text, score, cost in propositions:
            proposition_scores[prop_text][npc_type] = score
            proposition_costs[prop_text][npc_type] = cost
            npc_total_costs[npc_type] += cost
    
    # Sort NPC types for consistent column ordering
    npc_types_sorted = sorted(npc_types)
    
    # Generate CSV
    csv_path = run_folder / "summary.csv"
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header row (includes "cost" column)
        header = [''] + npc_types_sorted + ['cost']
        writer.writerow(header)
        
        # Write data rows (includes cost per row)
        for prop_text in sorted(proposition_scores.keys()):
            row = [prop_text]
            row_cost = 0.0
            
            for npc_type in npc_types_sorted:
                score = proposition_scores[prop_text].get(npc_type)
                if score is not None:
                    # Convert 0.0-1.0 to percentage string
                    percentage = f"{int(score * 100)}%"
                    row.append(percentage)
                    # Add cost for this cell
                    row_cost += proposition_costs[prop_text].get(npc_type, 0.0)
                else:
                    row.append('')  # Empty cell for missing data
            
            # Add row cost
            row.append(format_cost_usd(row_cost))
            writer.writerow(row)
        
        # Write Total row (average of all scores per NPC)
        total_row = ['total']
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
        total_row.append('')  # Empty cell for total row cost column
        writer.writerow(total_row)
        
        # Write Cost row (total cost per NPC column)
        cost_row = ['cost']
        grand_total = 0.0
        for npc_type in npc_types_sorted:
            cost = npc_total_costs.get(npc_type, 0.0)
            cost_row.append(format_cost_usd(cost))
            grand_total += cost
        cost_row.append(format_cost_usd(grand_total))  # Grand total in bottom-right
        writer.writerow(cost_row)
    
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


def _extract_propositions_scores_and_costs(report: dict) -> List[Tuple[str, float, float]]:
    """
    Extract proposition texts, scores, and costs from a report
    
    Args:
        report: Parsed JSON report dictionary
        
    Returns:
        List of tuples (proposition_text, score, cost_usd)
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
                
                # Extract cost from tokens list
                tokens_list = evaluation.get("tokens", [])
                cost = sum(token.get("cost", 0.0) for token in tokens_list)
                
                propositions.append((prop_text, score, cost))
    
    except (KeyError, IndexError, TypeError) as e:
        # Handle malformed reports gracefully
        print(f"Warning: Error parsing report - {e}")
    
    return propositions

