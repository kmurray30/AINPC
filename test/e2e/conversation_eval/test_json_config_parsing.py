#!/usr/bin/env python3
"""
E2E test to verify JSON test config parsing works correctly
This test reproduces the parsing error with TestConfig dataclass
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.conversation_eval.EvalClasses import TestConfig
from src.utils import io_utils


def test_parse_simple_test_config():
    """Test parsing a simple test config with no initial state"""
    # Create a minimal test config JSON in memory
    test_config_dir = Path(__file__).parent / "test_fixtures"
    test_config_dir.mkdir(exist_ok=True)
    
    test_config_path = test_config_dir / "simple_test.json"
    test_config_content = """{
    "convos_per_user_prompt": 1,
    "eval_iterations_per_eval": 1,
    "convo_length": 3,
    "assistant_template_name": "assistant",
    "mock_user_template_name": "mock_user",
    "initial_context": null,
    "background_knowledge": [],
    "initial_conversation_history": [],
    "eval_cases": [
        {
            "goals": ["Be friendly"],
            "propositions": [
                {
                    "antecedent": {
                        "value": "User asks a question",
                        "negated": false
                    },
                    "consequent": {
                        "value": "AI responds helpfully",
                        "negated": false
                    }
                }
            ]
        }
    ]
}"""
    
    with open(test_config_path, 'w') as f:
        f.write(test_config_content)
    
    try:
        # This should parse successfully without errors
        config = io_utils.load_json_into_dataclass(test_config_path, TestConfig)
        
        # Verify basic fields
        assert config.convos_per_user_prompt == 1
        assert config.eval_iterations_per_eval == 1
        assert config.convo_length == 3
        assert config.assistant_template_name == "assistant"
        assert config.mock_user_template_name == "mock_user"
        
        # Verify eval_cases structure
        assert len(config.eval_cases) == 1
        assert len(config.eval_cases[0].goals) == 1
        assert config.eval_cases[0].goals[0] == "Be friendly"
        assert len(config.eval_cases[0].propositions) == 1
        
        print("✅ Simple test config parsing successful")
        return True
        
    except Exception as e:
        print(f"❌ Failed to parse test config: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if test_config_path.exists():
            test_config_path.unlink()
        if test_config_dir.exists() and not any(test_config_dir.iterdir()):
            test_config_dir.rmdir()


def test_parse_actual_test_config():
    """Test parsing an actual test config from the test suite"""
    # Use the actual emotional_escalation_response.json
    test_config_path = Path(__file__).parent.parent.parent.parent / \
                       "src/conversation_eval/evaluations/memory_wipe_tests/test_configs/emotional_escalation_response.json"
    
    if not test_config_path.exists():
        print(f"⚠️  Test config not found at {test_config_path}, skipping")
        return True
    
    try:
        config = io_utils.load_json_into_dataclass(test_config_path, TestConfig)
        
        # Verify it loaded
        assert config.convos_per_user_prompt == 1
        assert len(config.eval_cases) == 2  # This test has 2 eval cases
        
        print("✅ Actual test config parsing successful")
        return True
        
    except Exception as e:
        print(f"❌ Failed to parse actual test config: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing JSON Config Parsing")
    print("=" * 60)
    
    test1 = test_parse_simple_test_config()
    test2 = test_parse_actual_test_config()
    
    if test1 and test2:
        print("\n✅ All JSON parsing tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some JSON parsing tests failed")
        sys.exit(1)


