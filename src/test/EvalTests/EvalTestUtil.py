# Imports
import json
from typing import Dict, List
from dataclasses import asdict

from src.test.TestHelper import TestHelper
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
    eval_report = EvalReport(evaluations={}, accuracies={}, tokens=0)
    for evaluation_test_report in eval_test_reports:
        condition_er = ConditionEvalReport(antecedent=evaluation_test_report.evaluation_condition.antecedent, consequent=evaluation_test_report.evaluation_condition.consequent)
        evaluation_er = EvaluationEvalReport(condition=condition_er, conversation_evaluations=[], accuracy=0, score=evaluation_test_report.score, tokens=0)
        for conversation_evaluation in evaluation_test_report.conversation_evaluations:
            conversation_name = conversation_evaluation.conversation_name
            evaluation_iterations = conversation_evaluation.evaluation_iterations
            conversation_expected_outcome = conversation_outcomes[conversation_name]

            conversation_er = ConversationEvaluationEvalReport(
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
                conversation_er.evaluation_iterations.append(evaluation_iteration_eval_report)
            conversation_er.evaluation_iterations.sort(key=lambda x: x.accuracy)
            conversation_er.accuracy = sum([iteration.accuracy for iteration in conversation_er.evaluation_iterations]) / len(conversation_er.evaluation_iterations)
            evaluation_er.conversation_evaluations.append(conversation_er)
        evaluation_er.conversation_evaluations.sort(key=lambda x: x.accuracy)
        evaluation_er.accuracy = sum([conversation_evaluation.accuracy for conversation_evaluation in evaluation_er.conversation_evaluations]) / len(evaluation_er.conversation_evaluations)
        eval_report.accuracies[str(condition_er)] = evaluation_er.accuracy
        eval_report.evaluations[str(evaluation_er.condition)] = evaluation_er
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

def generate_eval_report_and_write_to_file(condition: Condition, conversations_path: str, conversations_and_outcomes: Dict[str, ConversationOutcome], eval_iterations_per_eval: int):
    
    # Load the pre-written conversations to be used for the evaluation evaluation
    conversation_map = {}
    for conversation_name in conversations_and_outcomes.keys():
        conversation_file_name = f"{conversation_name}.json"
        conversation_file_path = Utilities.get_path_from_project_root(f"{conversations_path}/{conversation_file_name}")
        print(f"Loading {conversation_file_path}")
        conversation = Utilities.load_json_from_file(conversation_file_path)
        conversation_map[conversation_name] = conversation

    # Run the evaluations
    evaluation_test_reports = TestHelper.run_evaluations_on_conversation(conversation_map, [condition], eval_iterations_per_eval)

    # Generate the evaluation report
    eval_report = generate_eval_report(evaluation_test_reports, conversation_map, conversations_and_outcomes)

    # Write the test report to a file
    write_eval_report_to_file(eval_report)