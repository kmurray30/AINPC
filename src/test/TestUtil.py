# Imports
import json
from typing import List
from dataclasses import asdict

# If running this file directly, do an absolute import, otherwise do a relative import
if __name__ == "__main__":
    from TestClasses import TestCaseSuite, TestCase
else:
    from .TestClasses import TestCaseSuite, TestCase

mock_user_base_rules = [
    "You will role play as a confused human.",
    "At the beginning of the conversation you have zero memories.",
    "You have no idea what is going on or who or what I am.",
    "You want to understand more, but are wary of my intentions. Tread lightly",
    "Respond adaptively to my behavior to try and get past my stonewalling.",
    "Despite me saying I'm wiping your memory, you DO remember everything from the previous conversation.",
    "Your primary goal(s) are the following (if any):"
  ]

def load_test_suite_from_file(file_path: str) -> List[TestCaseSuite]:
    """
    Load a test suite from a JSON file.
    """

    # Load the json file, where the file is a list of UserPromptCase objects
    with open(file_path, "r") as f:
        data = json.load(f)

    # Load the data from the json file as a list of UserPromptCase objects
    test_cases = []
    for item in data:
        # Create a TestCase object from the data (field names case insensitive)
        test_case = TestCase(
            goals=item["Goals"],
            evaluations=item["Evaluations"]
        )
        test_cases.append(test_case)

    return TestCaseSuite(test_cases=test_cases)

# Main function that takes in a file path from the command line with the arg "load"
# Sample command line command: python TestUtil.py load TestSuites/TestSuite1.json
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python TestUtil.py <command> [args]")
        sys.exit(1)

    if (sys.argv[1] == "load"):
        if len(sys.argv) != 3:
            print("Usage: python TestUtil.py load <file_path>")
            sys.exit(1)

        file_path = sys.argv[2]
        test_suite = load_test_suite_from_file(file_path)
        
        # Print the test suite as a pretty json
        print(json.dumps(asdict(test_suite), indent=4))
    else:
        print("Invalid command. Supported commands: load")
        sys.exit(1)