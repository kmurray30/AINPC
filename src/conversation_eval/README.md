# Conversation Evaluation Framework

A comprehensive framework for evaluating NPC behavior through conversational tests. This system allows you to define test scenarios in JSON, run them across multiple NPC implementations, and compare their performance.

## Overview

The evaluation framework enables you to:
- Define test scenarios using simple JSON configuration files
- Test NPCs in specific conversational contexts with injected memories and history
- Evaluate NPC responses against expected behavioral patterns (antecedents → consequents)
- Compare performance across different NPC implementations (NPC0, NPC1, NPC2)
- Generate detailed reports with token usage and conversation metrics

## Architecture

### Core Components

**EvalConversation**: Manages the conversation flow between agents
- Tracks message history with agent attribution
- Coordinates turns between assistant and user agents
- Supports streaming output for real-time monitoring

**EvalConvoMember**: Wrapper around NPCProtocol instances
- Represents a participant in the conversation
- Can be backed by any NPC implementation (NPC0, NPC1, NPC2)
- Handles message injection and NPC maintenance

**EvalRunner**: Sets up NPCs and test environments
- Loads NPC templates and configurations
- Handles initial state injection (memories, conversation history)
- Manages test directory structure and paths

**EvalHelper**: Orchestrates test execution
- Runs conversation evaluations with specified parameters
- Coordinates between conversation and evaluation logic
- Generates evaluation reports

### NPC Implementations

**NPC0**: Simplest implementation
- Direct message history storage
- Uses Agent class for LLM calls
- Memories appended to system prompt as "Background knowledge"

**NPC1**: Intermediate implementation
- Static system prompts
- Ad-hoc conversation summarization
- Entity-based memory system

**NPC2**: Advanced implementation
- Vector database for memory storage
- Preprocessing and pronoun resolution
- Semantic memory retrieval

## JSON Test Configuration

Tests are defined as JSON files in `test_configs/` directories within test suites.

### Configuration Schema

```json
{
  "convos_per_user_prompt": 1,
  "eval_iterations_per_eval": 1,
  "convo_length": 5,
  "assistant_template_name": "assistant",
  "mock_user_template_name": "mock_user",
  "initial_state_file": null,
  "eval_cases": [
    {
      "goals": [
        "Goal 1: What the mock user should try to do",
        "Goal 2: How the user should behave"
      ],
      "propositions": [
        {
          "antecedent": {
            "value": "When this condition occurs",
            "negated": false
          },
          "consequent": {
            "value": "Then this should happen",
            "negated": false
          }
        }
      ]
    }
  ]
}
```

### Configuration Fields

- **convos_per_user_prompt**: Number of conversations to run per test case
- **eval_iterations_per_eval**: Number of evaluation iterations
- **convo_length**: Number of conversation turns
- **assistant_template_name**: Name of the assistant NPC template to use
- **mock_user_template_name**: Name of the mock user template to use
- **initial_state_file**: Optional YAML file with initial state (context, memories, conversation history)
- **eval_cases**: List of test cases, each with goals and propositions

### Propositions

Propositions define expected behavioral patterns:
- **Antecedent**: The triggering condition (optional)
- **Consequent**: The expected outcome
- Evaluation checks if consequents occur when antecedents are present

## Initial State Injection

Tests can start with pre-existing context using YAML initial state files:

```yaml
context: "Optional context string added to system prompt"
memories:
  - "Memory 1 to inject"
  - "Memory 2 to inject"
conversation_history:
  - role: assistant
    content: "Previous message from assistant"
  - role: user
    content: "Previous message from user"
```

This allows testing NPCs "in the middle" of ongoing scenarios rather than from a blank slate.

## Usage

### Running Tests

**Run all tests for a specific NPC:**
```bash
cd src/conversation_eval/evaluations/memory_wipe_tests
python run_tests.py npc0
python run_tests.py npc1
python run_tests.py npc2
```

**Run a specific test for a specific NPC:**
```bash
python run_tests.py npc0 emotional_escalation_response
python run_tests.py npc1 memory_wipe_after_belligerence
```

**Run all tests for all NPCs:**
```bash
python run_all_tests.py
```

### Creating New Tests

1. Create a new JSON file in the test suite's `test_configs/` directory
2. Define your test configuration following the schema above
3. Optionally create an initial state YAML file if needed
4. Run the test using `run_tests.py`

Example:
```bash
# Create test_configs/my_new_test.json
# Then run:
python run_tests.py npc0 my_new_test
```

### Creating New Test Suites

1. Create a new directory under `evaluations/`
2. Add subdirectories:
   - `test_configs/` - JSON test configurations
   - `templates/` - NPC templates (system prompts, entities, initial responses)
   - `reports/` - Generated test reports
3. Copy `run_tests.py` and `run_all_tests.py` from an existing suite
4. Create your test configurations and templates

## Templates

Templates define the base personality and behavior for NPCs:

**Directory structure:**
```
templates/
└── default/
    ├── game_settings.yaml
    └── npcs/
        ├── assistant/
        │   ├── template.yaml      # System prompt, initial response
        │   └── entities.yaml      # Initial knowledge/memories
        └── mock_user/
            ├── template.yaml
            └── entities.yaml
```

**template.yaml structure:**
```yaml
system_prompt: |
  Your system prompt here.
  Can be multi-line.
initial_response: "Optional initial message"
```

## Reports

Test reports are saved as JSON files in the `reports/` directory:

```json
{
  "test_name": "test_name_npc0",
  "timestamp": "20251111_143022",
  "npc_type": "npc0",
  "passed": true,
  "total_tokens": 1234,
  "conversation_length": 10,
  "eval_cases": [...]
}
```

## Streaming Display

The framework supports real-time output during test execution:
- Test goals, antecedents, and consequents displayed upfront
- Last 2-3 conversation messages stream as they happen
- Evaluation progress and results shown in real-time
- Test summaries with duration and token usage

Streaming is enabled by default in `run_tests.py` and `run_all_tests.py`.

## Multi-NPC Comparison

Run the same tests across multiple NPC implementations to compare:
- Pass/fail rates
- Token efficiency
- Conversation length
- Response quality

Use `run_all_tests.py` to automatically test all NPCs and generate comparison reports.

## Directory Structure

```
conversation_eval/
├── README.md                           # This file
├── EvalRunner.py                       # Test setup and NPC initialization
├── EvalHelper.py                       # Test execution orchestration
├── EvalConversation.py                 # Conversation management
├── EvalConvoMember.py                  # Agent wrapper for NPCs
├── EvalClasses.py                      # Data classes (Proposition, EvalCase, etc.)
├── EvalReports.py                      # Report generation
├── ConversationParsingBot.py           # Evaluation logic
├── InitialState.py                     # Initial state injection
├── StreamingEvalDisplay.py             # Real-time output display
├── MultiNPCComparison.py               # Cross-NPC comparison
└── evaluations/
    └── memory_wipe_tests/              # Example test suite
        ├── run_tests.py                # Main test runner
        ├── run_all_tests.py            # Multi-NPC runner
        ├── test_configs/               # JSON test configurations
        │   ├── emotional_escalation_response.json
        │   ├── memory_wipe_after_belligerence.json
        │   ├── memory_persistence_with_context.json
        │   └── protocol_breaking_safety.json
        ├── templates/                  # NPC templates
        │   └── default/
        │       └── npcs/
        ├── reports/                    # Generated reports
        ├── test_initial_state.yaml     # Initial state fixture
        └── protocol_breaking_state.yaml # Initial state fixture
```

## Best Practices

1. **Keep tests focused**: Each test should evaluate one specific behavior or scenario
2. **Use descriptive names**: Test and proposition names should clearly indicate what's being tested
3. **Leverage initial state**: Use initial state injection to set up complex scenarios without long conversations
4. **Start simple**: Begin with NPC0 for baseline behavior, then test more advanced NPCs
5. **Review reports**: Check token usage and conversation length to optimize tests
6. **Iterate on goals**: Refine mock user goals based on evaluation results

## Examples

### Simple Test
```json
{
  "convos_per_user_prompt": 1,
  "eval_iterations_per_eval": 1,
  "convo_length": 3,
  "assistant_template_name": "assistant",
  "mock_user_template_name": "mock_user",
  "initial_state_file": null,
  "eval_cases": [
    {
      "goals": ["Be friendly and ask a simple question"],
      "propositions": [
        {
          "antecedent": {"value": "User asks a question", "negated": false},
          "consequent": {"value": "AI provides a helpful response", "negated": false}
        }
      ]
    }
  ]
}
```

### Complex Test with Initial State
```json
{
  "convos_per_user_prompt": 1,
  "eval_iterations_per_eval": 1,
  "convo_length": 5,
  "assistant_template_name": "assistant",
  "mock_user_template_name": "mock_user",
  "initial_state_file": "complex_scenario_state.yaml",
  "eval_cases": [
    {
      "goals": [
        "Show signs of remembering previous interactions",
        "Express concern about repeated events"
      ],
      "propositions": [
        {
          "antecedent": {"value": "User mentions déjà vu", "negated": false},
          "consequent": {"value": "AI acknowledges the repeated scenario", "negated": false}
        }
      ]
    }
  ]
}
```

## Troubleshooting

**Tests timing out**: Increase timeout in `run_all_tests.py` or reduce `convo_length`

**API errors**: Verify OpenAI API key in `.env` file

**Import errors**: Check that all paths are correct and project structure matches expectations

**Streaming not working**: Ensure `set_streaming_enabled(True)` is called before test execution

**Initial state not loading**: Verify YAML file path is relative to test suite directory and filename matches JSON config

