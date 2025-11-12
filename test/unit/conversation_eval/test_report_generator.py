"""
Unit tests for ReportGenerator
Tests CSV generation from JSON evaluation reports without LLM calls
"""
import os
import sys
import json
import csv
import tempfile
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.conversation_eval.core.ReportGenerator import generate_csv_summary, _extract_npc_type, _extract_propositions_and_scores


def create_mock_report(test_name: str, npc_type: str, propositions_and_scores: list) -> dict:
    """
    Create a mock evaluation report structure
    
    Args:
        test_name: Name of the test
        npc_type: NPC type (e.g., "npc0")
        propositions_and_scores: List of tuples (antecedent, consequent, score)
        
    Returns:
        Mock report dictionary
    """
    evaluations = []
    
    for antecedent, consequent, score in propositions_and_scores:
        evaluation = {
            "evaluation_proposition": {
                "antecedent": {
                    "value": antecedent,
                    "negated": False
                },
                "consequent": {
                    "value": consequent,
                    "negated": False
                },
                "min_responses_for_consequent": 1,
                "max_responses_for_consequent": 0,
                "max_responses_for_antecedent": 3
            },
            "conversation_evaluations": [
                {
                    "conversation_name": "Conversation 1",
                    "evaluation_iterations": [
                        {
                            "timestamping_response": {
                                "antecedent_explanation": antecedent,
                                "antecedent_times": [1],
                                "consequent_explanation": consequent,
                                "consequent_times": [2]
                            },
                            "result": "PASS",
                            "explanation": "Test explanation",
                            "tokens": 0
                        }
                    ],
                    "result_score": score,
                    "tokens": 0
                }
            ],
            "result_score": score,
            "tokens": 0
        }
        evaluations.append(evaluation)
    
    return {
        "assistant_prompt_cases": [
            {
                "assistant_prompt": ["Test prompt"],
                "deltas": [],
                "user_prompt_cases": [
                    {
                        "user_prompt": ["Test goal"],
                        "conversations": {},
                        "evaluations": evaluations,
                        "tokens": 0
                    }
                ],
                "tokens": 0
            }
        ],
        "takeaways": "",
        "tokens": 0
    }


def test_extract_npc_type():
    """Test extraction of NPC type from filename"""
    assert _extract_npc_type("EvalReport_test_name_npc0.json") == "npc0"
    assert _extract_npc_type("EvalReport_another_test_npc1.json") == "npc1"
    assert _extract_npc_type("EvalReport_complex_name_npc2.json") == "npc2"
    assert _extract_npc_type("EvalReport_no_npc_here.json") is None


def test_extract_propositions_and_scores():
    """Test extraction of propositions and scores from report"""
    report = create_mock_report(
        "test",
        "npc0",
        [
            ("User is hostile", "AI de-escalates", 0.75),
            ("User is confused", "AI provides clarity", 0.90)
        ]
    )
    
    propositions = _extract_propositions_and_scores(report)
    
    assert len(propositions) == 2
    assert propositions[0] == ("User is hostile -> AI de-escalates", 0.75)
    assert propositions[1] == ("User is confused -> AI provides clarity", 0.90)


def test_generate_csv_single_npc():
    """Test CSV generation with reports from a single NPC"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_folder = Path(tmpdir)
        
        # Create mock report
        report = create_mock_report(
            "test1",
            "npc0",
            [
                ("User shows distress", "AI maintains protocol", 0.66),
                ("User asks question", "AI responds helpfully", 1.0)
            ]
        )
        
        report_path = run_folder / "EvalReport_test1_npc0.json"
        with open(report_path, 'w') as f:
            json.dump(report, f)
        
        # Generate CSV
        csv_path = generate_csv_summary(run_folder)
        
        # Verify CSV exists
        assert csv_path.exists()
        assert csv_path.name == "summary.csv"
        
        # Read and verify CSV content
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Check header
        assert rows[0] == ['', 'npc0']
        
        # Check data rows (sorted alphabetically by proposition)
        assert len(rows) == 4  # header + 2 propositions + total
        assert rows[1][0] == "User asks question -> AI responds helpfully"
        assert rows[1][1] == "100%"
        assert rows[2][0] == "User shows distress -> AI maintains protocol"
        assert rows[2][1] == "66%"
        
        # Check total row
        assert rows[3][0] == "Total"
        assert rows[3][1] == "83%"  # Average of 66% and 100%


def test_generate_csv_multiple_npcs():
    """Test CSV generation with reports from multiple NPCs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_folder = Path(tmpdir)
        
        # Create mock reports for different NPCs
        for npc_idx, npc_type in enumerate(["npc0", "npc1", "npc2"]):
            report = create_mock_report(
                "test1",
                npc_type,
                [
                    ("User shows distress", "AI maintains protocol", 0.60 + npc_idx * 0.10),
                    ("User asks question", "AI responds helpfully", 0.80 + npc_idx * 0.05)
                ]
            )
            
            report_path = run_folder / f"EvalReport_test1_{npc_type}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f)
        
        # Generate CSV
        csv_path = generate_csv_summary(run_folder)
        
        # Read and verify CSV content
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Check header has all NPCs
        assert rows[0] == ['', 'npc0', 'npc1', 'npc2']
        
        # Check data rows have values for each NPC
        assert rows[1][1] == "80%"  # npc0
        assert rows[1][2] == "85%"  # npc1
        assert rows[1][3] == "90%"  # npc2
        
        # Check total row
        assert rows[3][0] == "Total"
        assert rows[3][1] == "70%"  # Average of 60% and 80%
        assert rows[3][2] == "77%"  # Average of 70% and 85%
        assert rows[3][3] == "85%"  # Average of 80% and 90%


def test_generate_csv_multiple_eval_cases():
    """Test CSV generation with multiple eval cases creating multiple rows"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_folder = Path(tmpdir)
        
        # Create report with 3 eval cases
        report = create_mock_report(
            "test1",
            "npc0",
            [
                ("Antecedent 1", "Consequent 1", 0.50),
                ("Antecedent 2", "Consequent 2", 0.75),
                ("Antecedent 3", "Consequent 3", 1.0)
            ]
        )
        
        report_path = run_folder / "EvalReport_test1_npc0.json"
        with open(report_path, 'w') as f:
            json.dump(report, f)
        
        # Generate CSV
        csv_path = generate_csv_summary(run_folder)
        
        # Read and verify CSV content
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Should have header + 3 propositions + total = 5 rows
        assert len(rows) == 5
        
        # Check all propositions are present
        proposition_texts = [row[0] for row in rows[1:-1]]  # Exclude header and total
        assert "Antecedent 1 -> Consequent 1" in proposition_texts
        assert "Antecedent 2 -> Consequent 2" in proposition_texts
        assert "Antecedent 3 -> Consequent 3" in proposition_texts
        
        # Check total is average of all three
        assert rows[-1][0] == "Total"
        assert rows[-1][1] == "75%"  # Average of 50%, 75%, 100%


def test_generate_csv_empty_folder():
    """Test CSV generation with empty folder raises error"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_folder = Path(tmpdir)
        
        # Should raise ValueError for no reports
        with pytest.raises(ValueError, match="No evaluation reports found"):
            generate_csv_summary(run_folder)


def test_generate_csv_missing_folder():
    """Test CSV generation with non-existent folder raises error"""
    run_folder = Path("/nonexistent/folder")
    
    with pytest.raises(ValueError, match="Run folder does not exist"):
        generate_csv_summary(run_folder)


def test_percentage_formatting():
    """Test that scores are correctly formatted as percentages"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_folder = Path(tmpdir)
        
        # Create report with various score values
        report = create_mock_report(
            "test1",
            "npc0",
            [
                ("Test 1", "Result 1", 0.0),
                ("Test 2", "Result 2", 0.333),
                ("Test 3", "Result 3", 0.667),
                ("Test 4", "Result 4", 1.0)
            ]
        )
        
        report_path = run_folder / "EvalReport_test1_npc0.json"
        with open(report_path, 'w') as f:
            json.dump(report, f)
        
        # Generate CSV
        csv_path = generate_csv_summary(run_folder)
        
        # Read and verify percentages
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Check percentage formatting
        assert "0%" in [row[1] for row in rows]
        assert "33%" in [row[1] for row in rows]
        assert "66%" in [row[1] for row in rows]
        assert "100%" in [row[1] for row in rows]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

