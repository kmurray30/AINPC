# Simple UI Tests

This directory contains comprehensive tests for the `simple_ui` application located at `src/apps/simple_ui/simple_ui.py`.

## Test Structure

### TestSimpleUIArgumentParsing
Tests CLI argument parsing and validation:
- Valid arguments for NPC1 and NPC2
- --no-save flag handling
- Invalid NPC types
- Insufficient/too many arguments
- Invalid path formats (templates_dir_name and save_name with slashes)
- Invalid flags

### TestSimpleUICommands
Tests interactive commands:
- Exit commands (`/exit`, `/quit`, `/bye`)
- Path command (`/path`)
- Save command (`/save`)
- Load command (`/load <npc_name>`)
- Unknown command handling

### TestSimpleUIIntegration
Tests integration with NPCs and core functionality:
- NPC1 and NPC2 integration
- Save enabled/disabled functionality
- Template directory validation
- File creation when saving is enabled

### TestSimpleUIErrorHandling
Tests error handling:
- Graceful error handling
- Keyboard interrupt handling (Ctrl+C)

### TestSimpleUISpecialCommands
Tests special commands:
- List command (`/list`) - displays NPC memories
- Clear command (`/clear`) - clears NPC brain memory

## Test Templates

The tests use template files located in `templates/default/`:
- `app_settings.yaml` - Application settings
- `npcs/john/template.yaml` - John NPC template with friendly personality
- `npcs/john/entities.yaml` - John's default entities/memories
- `npcs/default/entities.yaml` - Default fallback entities

## Running Tests

```bash
# Run all simple_ui tests
python -m pytest test/unit/apps/simple_ui/test_simple_ui.py -v

# Run specific test class
python -m pytest test/unit/apps/simple_ui/test_simple_ui.py::TestSimpleUIArgumentParsing -v

# Run specific test
python -m pytest test/unit/apps/simple_ui/test_simple_ui.py::TestSimpleUIArgumentParsing::test_valid_arguments_npc1 -v
```

## Test Coverage

The tests cover:
- ✅ CLI argument parsing and validation
- ✅ All interactive commands
- ✅ NPC1 and NPC2 integration
- ✅ Save enabled/disabled functionality
- ✅ Error handling and edge cases
- ✅ Template validation
- ✅ File I/O operations

## Notes

- Tests use subprocess calls to test the actual CLI behavior
- Each test runs in isolation with proper cleanup
- Tests validate both stdout and stderr output
- Timeouts are set to prevent hanging tests
- Color codes in output are handled properly
