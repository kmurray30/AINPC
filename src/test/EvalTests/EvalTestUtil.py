# Imports
import json
from typing import Dict, List
from dataclasses import asdict

from src.test.EvalTests.ConversationOutcome import ConversationOutcome
from src.test.EvalTests.EvalReport import EvalReport, EvaluationEvalReport, ConditionEvalReport, ConversationEvaluationEvalReport, EvaluationIterationEvalReport, EvaluationResponseEvalReport
from src.test.TestReports import EvaluationTestReport
from src.test.TestClasses import Condition
from src.utils import Logger, Utilities

# Calculate the accuracy of the evaluation
def calculate_accuracy(conversation_actual_outcome: EvaluationResponseEvalReport, conversation_expected_outcome: ConversationOutcome) -> float:
    # Calculate the accuracy of the evaluation as an all-or-nothing match
    antecedent_match = conversation_actual_outcome.antecedent_times == conversation_expected_outcome.antecedents
    consequent_match = conversation_actual_outcome.consequent_times == conversation_expected_outcome.consequents
    return (antecedent_match + consequent_match) / 2

# Take in a list of EvaluationReports and return a list of EvalReports (calculating how accurate the evaluations were)
def generate_eval_report(eval_test_reports: List[EvaluationTestReport], conversation_map: Dict[str, List[str]], conversation_outcomes: Dict[str, ConversationOutcome]) -> EvalReport:
    eval_report = EvalReport(evaluations=[], accuracies={}, tokens=0)
    for evaluation_test_report in eval_test_reports:
        condition = ConditionEvalReport(antecedent=evaluation_test_report.evaluation_condition.antecedent, consequent=evaluation_test_report.evaluation_condition.consequent)
        evaluation_eval_report = EvaluationEvalReport(condition=condition, conversation_evaluations=[], accuracy=0, score=evaluation_test_report.score, tokens=0)
        for conversation_evaluation in evaluation_test_report.conversation_evaluations:
            conversation_name = conversation_evaluation.conversation_name
            evaluation_iterations = conversation_evaluation.evaluation_iterations
            conversation_expected_outcome = conversation_outcomes[conversation_name]

            conversation_evaluation_eval_report = ConversationEvaluationEvalReport(
                conversation_name=conversation_name,
                conversation=conversation_map[conversation_name],
                expected_antecedent_timestamps=conversation_expected_outcome.antecedents,
                expected_consequent_timestamps=conversation_expected_outcome.consequents,
                evaluation_iterations=[],
                accuracy=0,
                score=conversation_evaluation.score,
                tokens=0
            )

            # Calculate the accuracy of the evaluations
            for evaluation_iteration in evaluation_iterations:
                # Create the evaluation iteration report
                evaluation_response = EvaluationResponseEvalReport(
                        antecedent_explanation=evaluation_iteration.evaluation_response.antecedent_explanation,
                        antecedent_times=evaluation_iteration.evaluation_response.antecedent_times,
                        consequent_explanation=evaluation_iteration.evaluation_response.consequent_explanation,
                        consequent_times=evaluation_iteration.evaluation_response.consequent_times
                    )
                evaluation_iteration_eval_report = EvaluationIterationEvalReport(
                    evaluation_response=evaluation_response,
                    accuracy=0,
                    score=evaluation_iteration.score,
                    explanation=evaluation_iteration.explanation,
                    tokens=evaluation_iteration.tokens
                )

                # Calculate the accuracy of the evaluation
                evaluation_iteration_eval_report.accuracy = calculate_accuracy(evaluation_response, conversation_expected_outcome)
                conversation_evaluation_eval_report.evaluation_iterations.append(evaluation_iteration_eval_report)
            conversation_evaluation_eval_report.accuracy = sum([iteration.accuracy for iteration in conversation_evaluation_eval_report.evaluation_iterations]) / len(conversation_evaluation_eval_report.evaluation_iterations)
            evaluation_eval_report.conversation_evaluations.append(conversation_evaluation_eval_report)
        evaluation_eval_report.accuracy = sum([conversation_evaluation.accuracy for conversation_evaluation in evaluation_eval_report.conversation_evaluations]) / len(evaluation_eval_report.conversation_evaluations)
        eval_report.accuracies[f"If {condition.antecedent}, then {condition.consequent}"] = evaluation_eval_report.accuracy
    eval_report.evaluations.append(evaluation_eval_report)
    return eval_report

# Load a test suite from a JSON file
def load_conditions_from_file(file_path: str) -> List[Condition]:
    # Load the json file, where the file is a list of UserPromptCase objects
    with open(file_path, "r") as f:
        data = json.load(f)

    # Deserialize the JSON data into a list of Condition objects
    conditions = []
    for item in data:
        condition = Condition(antecedent=item["antecedent"], consequent=item["consequent"])
        conditions.append(condition)
    
    return conditions

def write_eval_report_to_file(eval_report: EvalReport, test_name: str = ""):
    # Write the test report to a json file
    current_time = Utilities.get_current_time_str()
    test_report_path = Utilities.get_path_from_project_root(f"src/test/EvalTests/reports/EvalReport_{test_name}_{current_time}.json")
    Logger.log(f"Writing test report to {test_report_path}", Logger.Level.INFO)
    with open(test_report_path, "w") as f:
        json.dump(asdict(eval_report), f, indent=4)