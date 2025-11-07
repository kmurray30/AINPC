# NPC Integration Tests for Conversation Evaluation

This test suite validates the integration of NPC1 and NPC2 with the conversation evaluation framework.

## Test Structure

### Test Files

1. **`test_npc1_conversation_eval.py`**
   - Tests NPC1 integration with conversation evaluation
   - Validates basic conversation generation
   - Tests evaluation propositions with NPC1
   - Verifies conversation history management
   - Tests save_enabled=False behavior

2. **`test_npc2_conversation_eval.py`**
   - Tests NPC2 integration with conversation evaluation
   - Validates preprocessing functionality during evaluation
   - Tests memory system disabled state
   - Verifies longer conversation flows
   - Tests complex evaluation scenarios

3. **`test_npc_interchangeability.py`**
   - Validates that NPC1 and NPC2 can be used interchangeably
   - Tests both NPCs with identical evaluation scenarios
   - Verifies NPCProtocol interface compliance
   - Compares conversation generation between NPCs

4. **`test_conversation_framework_integration.py`**
   - Tests EvalConvoMember integration with NPC protocols
   - Validates Conversation class NPC support methods
   - Tests mixed agent types (NPC + simple agents)
   - Verifies conversation flow and history management

### Template Structure

```
templates/
├── npc1/
│   └── templates/
│       ├── game_settings.yaml
│       └── npcs/
│           └── test_assistant/
│               ├── template_v1.0.yaml
│               └── entities.yaml
└── npc2/
    └── templates/
        ├── game_settings.yaml
        └── npcs/
            └── test_assistant/
                ├── template_v2.0.yaml
                └── entities.yaml
```

## Running Tests

### Run All Tests
```bash
cd test/llm/conversation_eval/tests/npc_integration/
python run_all_tests.py
```

### Run Individual Test Files
```bash
# From project root
python -m pytest test/llm/conversation_eval/tests/npc_integration/test_npc1_conversation_eval.py -v
python -m pytest test/llm/conversation_eval/tests/npc_integration/test_npc2_conversation_eval.py -v
python -m pytest test/llm/conversation_eval/tests/npc_integration/test_npc_interchangeability.py -v
python -m pytest test/llm/conversation_eval/tests/npc_integration/test_conversation_framework_integration.py -v
```

### Run Specific Test Classes
```bash
python -m pytest test/llm/conversation_eval/tests/npc_integration/test_npc1_conversation_eval.py::TestNPC1ConversationEval::test_npc1_basic_conversation_generation -v
```

## Prerequisites

### For NPC1 Tests
- No external dependencies
- Uses simple conversation memory

### For NPC2 Tests
- Qdrant server running on localhost:6333
- Docker recommended: `docker run -p 6333:6333 qdrant/qdrant`
- Vector database functionality

### General Requirements
- All project dependencies installed
- Proper Python path configuration
- Template files in correct locations

## Test Coverage

### Core Functionality
- ✅ NPC initialization with save_enabled=False
- ✅ Conversation generation via EvalHelper
- ✅ Evaluation proposition testing
- ✅ Mixed agent type conversations (NPC + simple)
- ✅ Conversation history management

### NPC1 Specific
- ✅ Simple conversation memory
- ✅ Template loading (v1.0)
- ✅ Basic chat functionality
- ✅ State management without file saving

### NPC2 Specific  
- ✅ Preprocessing functionality
- ✅ Memory system (disabled mode)
- ✅ Template loading (v2.0)
- ✅ Vector database integration (disabled)
- ✅ Advanced chat capabilities

### Framework Integration
- ✅ EvalConvoMember NPC support methods
- ✅ Conversation.add_agent_with_npc_protocol()
- ✅ Conversation.call_agent() dual mode
- ✅ NPCProtocol interface compliance
- ✅ State isolation between conversations

## Common Issues

### Template Not Found Errors
- Ensure template files exist in correct directory structure
- Check version numbers match (1.0 for NPC1, 2.0 for NPC2)
- Verify file paths and naming conventions

### Qdrant Connection Errors (NPC2)
- Start Qdrant server: `docker run -p 6333:6333 qdrant/qdrant`
- Check server status: `curl http://localhost:6333/health`
- Verify port 6333 is available

### Singleton State Conflicts
- Tests reset proj_paths and proj_settings automatically
- If issues persist, restart test runner
- Check for global state leakage between tests

### Import Path Issues
- Ensure project root is in Python path
- Check sys.path.insert() statements
- Verify relative import paths

## Expected Outcomes

When all tests pass, you can be confident that:

1. **NPC Integration Works**: Both NPC1 and NPC2 integrate properly with conversation evaluation
2. **Interchangeability**: NPCs can be swapped without changing evaluation code
3. **Framework Compatibility**: Existing evaluation framework works with NPC-backed agents
4. **State Management**: NPCs operate correctly in evaluation mode (no file saving)
5. **Conversation Flow**: Proper message handling and history management
6. **Mixed Agents**: NPC-backed and simple agents work together in evaluations

## Troubleshooting

If tests fail:

1. Check prerequisites (Qdrant for NPC2 tests)
2. Verify template file structure and content
3. Ensure proper Python environment and dependencies
4. Check for port conflicts or permission issues
5. Review test output for specific error messages
6. Run individual tests to isolate issues
