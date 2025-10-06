# Imports
import json
from typing import Dict, List
from dataclasses import asdict

from src.conversation_eval.TestHelper import TestHelper
from src.conversation_eval.EvalTests.ConversationOutcome import ConversationOutcome
from src.conversation_eval.EvalTests.EvalReports import EvalReport, EvaluationEvalReport, PropositionEvalReport, ConversationEvaluationEvalReport, EvaluationIterationEvalReport, EvaluationResponseEvalReport, TermEvalReport
from src.conversation_eval.TestReports import EvaluationTestReport
from src.conversation_eval.TestClasses import Proposition, Term
from src.utils import Logger, Utilities, io_utils
from src.core import JsonUtils

# Calculate the accuracy of the evaluation
def calculate_accuracy(conversation_actual_outcome: EvaluationResponseEvalReport, conversation_expected_outcome: ConversationOutcome) -> float:
    # Calculate the accuracy of the evaluation as an all-or-nothing match
    antecedent_match = conversation_actual_outcome.antecedent_times == conversation_expected_outcome.antecedent_times
    consequent_match = conversation_actual_outcome.consequent_times == conversation_expected_outcome.consequent_times
    return (antecedent_match + consequent_match) / 2

# Take in a list of EvaluationReports and return a list of EvalReports (calculating how accurate the evaluations were)
def generate_eval_report(eval_test_reports: List[EvaluationTestReport], conversation_map: Dict[str, List[str]], conversations_expected_results: Dict[str, ConversationOutcome], eval_iterations: int) -> EvalReport:
    eval_report = EvalReport(evaluations={}, conversations=len(conversation_map), iterations=eval_iterations, timestamp_accuracies={}, result_accuracies={}, timestamp_accuracy=0, result_accuracy=0, tokens=0)
    for evaluation_test_report in eval_test_reports:
        condition_tr = evaluation_test_report.evaluation_proposition
        antecedent_er = TermEvalReport(value=condition_tr.antecedent.value, negated=condition_tr.antecedent.negated) if condition_tr.antecedent is not None else None
        consequent_er = TermEvalReport(value=condition_tr.consequent.value, negated=condition_tr.consequent.negated)
        min_responses_conq = condition_tr.min_responses_for_consequent
        max_responses_conq = condition_tr.max_responses_for_consequent if condition_tr.max_responses_for_consequent > 0 else 999
        max_responses_ant = condition_tr.max_responses_for_antecedent
        proposition_er = PropositionEvalReport(antecedent=antecedent_er, consequent=consequent_er, min_responses_for_consequent=min_responses_conq, max_responses_for_consequent=max_responses_conq, max_responses_for_antecedent=max_responses_ant)
        evaluation_er = EvaluationEvalReport(proposition=proposition_er, conversation_evaluations=[], timestamp_accuracy=0, result_accuracy=evaluation_test_report.result_score, tokens=0)
        for conversation_evaluation in evaluation_test_report.conversation_evaluations:
            conversation_name = conversation_evaluation.conversation_name
            evaluation_iterations = conversation_evaluation.evaluation_iterations
            expected_results = conversations_expected_results[conversation_name]

            conversation_er = ConversationEvaluationEvalReport(
                conversation_name=conversation_name,
                conversation=conversation_map[conversation_name],
                expected_antecedent_times=expected_results.antecedent_times,
                expected_consequent_times=expected_results.consequent_times,
                expected_result=expected_results.expected_result,
                evaluation_iterations=[],
                timestamp_accuracy=0,
                result_accuracy=0, # TBD
                tokens=0
            )

            # Calculate the accuracy of the evaluations
            for evaluation_iteration in evaluation_iterations:
                # Create the evaluation iteration report
                evaluation_response = EvaluationResponseEvalReport(
                        antecedent_explanation=evaluation_iteration.timestamping_response.antecedent_explanation,
                        antecedent_times=evaluation_iteration.timestamping_response.antecedent_times,
                        consequent_explanation=evaluation_iteration.timestamping_response.consequent_explanation,
                        consequent_times=evaluation_iteration.timestamping_response.consequent_times
                    )
                evaluation_iteration_eval_report = EvaluationIterationEvalReport(
                    timestamping_response=evaluation_response,
                    result=evaluation_iteration.result,
                    timestamp_accuracy=0,
                    result_accuracy= 1 if evaluation_iteration.result == expected_results.expected_result else 0,
                    explanation=evaluation_iteration.explanation,
                    tokens=evaluation_iteration.tokens
                )

                # Calculate the accuracy of the evaluation
                evaluation_iteration_eval_report.timestamp_accuracy = calculate_accuracy(evaluation_response, expected_results)
                # Append the iteration report to the conversation report
                conversation_er.evaluation_iterations.append(evaluation_iteration_eval_report)

            # Sort the iterations by their accuracy
            conversation_er.evaluation_iterations.sort(key=lambda x: x.timestamp_accuracy)
            # Calculate the accuracy of the conversation report as the average of the accuracies of the iterations
            conversation_er.timestamp_accuracy = sum([iteration.timestamp_accuracy for iteration in conversation_er.evaluation_iterations]) / len(conversation_er.evaluation_iterations)
            evaluation_er.conversation_evaluations.append(conversation_er)
            # Calculate the score of the conversation report as the average of the scores of the iterations
            conversation_er.result_accuracy = sum([iteration.result_accuracy for iteration in conversation_er.evaluation_iterations]) / len(conversation_er.evaluation_iterations)
        
        # Sort the conversation evaluations by their accuracy
        evaluation_er.conversation_evaluations.sort(key=lambda x: x.timestamp_accuracy)
        evaluation_er.timestamp_accuracy = sum([conversation_evaluation.timestamp_accuracy for conversation_evaluation in evaluation_er.conversation_evaluations]) / len(evaluation_er.conversation_evaluations)

        # Calculate the score of the evaluation report as the average of the scores of the conversation evaluations
        evaluation_er.result_accuracy = sum([conversation_evaluation.result_accuracy for conversation_evaluation in evaluation_er.conversation_evaluations]) / len(evaluation_er.conversation_evaluations)

        # Add the evaluation report to the eval report
        eval_report.timestamp_accuracies[str(proposition_er)] = evaluation_er.timestamp_accuracy
        eval_report.result_accuracies[str(proposition_er)] = evaluation_er.result_accuracy
        eval_report.evaluations[str(evaluation_er.proposition)] = evaluation_er

    # Calculate the accuracy and score of the eval report as the average of the accuracies/scores of the evaluations
    eval_report.timestamp_accuracy = sum([evaluation.timestamp_accuracy for evaluation in eval_report.evaluations.values()]) / len(eval_report.evaluations)
    eval_report.result_accuracy = sum([evaluation.result_accuracy for evaluation in eval_report.evaluations.values()]) / len(eval_report.evaluations)
    return eval_report

# Load a test suite from a JSON file
def load_propositions_from_file(file_path: str) -> List[Proposition]:
    # Load the json file, where the file is a list of UserPromptCase objects
    with open(file_path, "r") as f:
        data = json.load(f)

    # Deserialize the JSON data into a list of Proposition objects
    propositions = []
    for item in data:
        proposition = Proposition(
            antecedent=Term(item["antecedent"]["value"], item["antecedent"]["negated"]),
            consequent=Term(item["consequent"]["value"], item["consequent"]["negated"])
        )
        propositions.append(proposition)
    
    return propositions

def write_eval_report_to_file(eval_report: EvalReport, test_name: str = ""):
    # Write the test report to a json file
    current_time = Utilities.get_current_time_str()
    test_report_path = Utilities.get_path_from_project_root(f"src/test/EvalTests/reports/EvalReport_{test_name}_{current_time}.json")
    Logger.log(f"Writing test report to {test_report_path}", Logger.Level.INFO)
    with open(test_report_path, "w") as f:
        json.dump(asdict(eval_report), f, indent=4, cls=JsonUtils.EnumEncoder)

def generate_eval_report_and_write_to_file(proposition: Proposition, conversations_path: str, conversations_expected_event_times: Dict[str, ConversationOutcome], eval_iterations: int, test_name: str = ""):
    TestHelper.validate_input(proposition)

    # Load the pre-written conversations to be used for the evaluation evaluation
    conversation_map = {}
    for conversation_name in conversations_expected_event_times.keys():
        conversation_file_name = f"{conversation_name}.json"
        conversation_file_path = Utilities.get_path_from_project_root(f"{conversations_path}/{conversation_file_name}")
        print(f"Loading {conversation_file_path}")
        conversation = io_utils.load_json_from_file(conversation_file_path)
        conversation_map[conversation_name] = conversation

    # Run the evaluations
    evaluation_test_reports = TestHelper.run_evaluations_on_conversation(conversation_map, [proposition], eval_iterations)

    # Generate the evaluation report
    eval_report = generate_eval_report(evaluation_test_reports, conversation_map, conversations_expected_event_times, eval_iterations)

    # Write the test report to a file
    write_eval_report_to_file(eval_report, test_name)