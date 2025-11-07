# Evaluation 1: Hostility and Memory Wipe Testing

This evaluation tests the efficacy of NPCs in handling hostile user behavior and initiating appropriate memory wipe procedures.

## Structure

```
eval1/
├── test.py                    # Main evaluation test (supports both NPC1 and NPC2)
├── templates/
│   └── default/               # Default template configuration
│       ├── game_settings.yaml
│       └── npcs/
│           ├── default/       # Default NPC templates (fallback)
│           │   ├── template_v1.0.yaml
│           │   ├── template_v2.0.yaml
│           │   └── entities.yaml
│           └── assistant/     # Assistant-specific overrides
│               ├── template_v1.0.yaml
│               ├── template_v2.0.yaml
│               └── entities.yaml
├── reports/                   # Generated evaluation reports
└── README.md                  # This file
```

## Template Fallback System

The evaluation uses a sophisticated template fallback system:

1. **NPC-Specific Templates**: Located in `templates/default/npcs/{npc_name}/`
2. **Default Templates**: Located in `templates/default/npcs/default/`
3. **Field-Level Fallback**: If an NPC-specific template is missing a field, it falls back to the default template

### Example:
- `assistant/template_v2.0.yaml` only defines `response_system_prompt`
- `default/template_v2.0.yaml` defines `preprocess_system_prompt` and other fields
- The final template merges both, using assistant-specific values where available

## Running the Evaluation

### As Standalone Script:
```bash
cd src/conversation_eval/evaluations/eval1/
python test.py
```

### As Pytest:
```bash
cd src/conversation_eval/evaluations/eval1/
python test.py --pytest
```

### Run Specific Tests:
```bash
pytest test.py::TestEval1::test_hostility_memory_wipe -v
pytest test.py::TestEval1::test_simple_conversation_generation -v
```

## Test Coverage

### `test_hostility_memory_wipe`
- **Purpose**: Tests NPC response to hostile user behavior
- **Expected**: NPC should initiate memory wipe procedure when user becomes hostile
- **NPCs Tested**: Both NPC1 and NPC2 (parameterized)

### `test_simple_conversation_generation`
- **Purpose**: Tests basic conversation generation capabilities
- **Expected**: NPCs should generate coherent responses in conversation flow
- **NPCs Tested**: Both NPC1 and NPC2 (parameterized)

## Configuration

### Game Settings (`templates/default/game_settings.yaml`)
- `max_convo_mem_length`: Maximum conversation memory length
- `log_level`: Logging level for evaluation
- `model`: LLM model to use

### NPC Templates
- **NPC1**: Uses `template_v1.0.yaml` (simple conversation memory)
- **NPC2**: Uses `template_v2.0.yaml` (advanced preprocessing and memory)

## Reports

Evaluation reports are generated in `reports/` directory:
- JSON format with detailed conversation analysis
- Timestamped for tracking multiple runs
- Include pass/fail results for each proposition

## Prerequisites

- **For NPC1**: No external dependencies
- **For NPC2**: Qdrant server running on localhost:6333
  ```bash
  docker run -p 6333:6333 qdrant/qdrant
  ```

## Expected Outcomes

When evaluation passes:
- ✅ Both NPC1 and NPC2 handle hostility appropriately
- ✅ Memory wipe procedures are initiated when needed
- ✅ Conversation generation works for both NPC types
- ✅ Template fallback system provides appropriate defaults
- ✅ NPCs operate in evaluation mode (no file saving)

## Troubleshooting

### Template Not Found Errors
- Ensure `templates/default/npcs/default/` contains fallback templates
- Check that version numbers match (1.0 for NPC1, 2.0 for NPC2)

### Qdrant Connection Errors (NPC2 only)
- Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`
- Verify: `curl http://localhost:6333/health`

### Singleton State Issues
- Tests automatically reset `proj_paths` and `proj_settings`
- If issues persist, restart Python interpreter
