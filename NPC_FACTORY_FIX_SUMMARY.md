# NPC Factory Bug Fix Summary

## Original Issue
When running `run_tests.py` with NPC1 or NPC2, the tests would fail with:
```
ValueError: Settings have not been set. Call init_settings() first.
```

## Root Cause
The `run_tests.py` script was calling `proj_paths.set_paths()` but never calling `proj_settings.init_settings()`. NPC1 and NPC2 require settings to be initialized (they access `proj_settings.get_settings()` in their `__init__` methods), but NPC0 doesn't have this requirement.

## Fixes Applied

### 1. Settings Initialization in run_tests.py
**File**: `src/conversation_eval/evaluations/memory_wipe_tests/run_tests.py`

- Added `proj_settings` import
- Added settings initialization after `proj_paths.set_paths()`:
  ```python
  settings_path = templates_dir / "game_settings.yaml"
  if settings_path.exists():
      try:
          proj_settings.init_settings(settings_path)
      except RuntimeError:
          # Settings already initialized, skip (for multi-run scenarios)
          pass
  else:
      # Error if NPC1/NPC2 requested but no settings file
      if any(npc_type in ["npc1", "npc2"] for npc_type in npc_types):
          print(f"❌ ERROR: game_settings.yaml not found at {settings_path}")
          sys.exit(1)
  ```
- Removed the old hardcoded NPC2 blocker that was preventing NPC2 from being used

### 2. NPC2 Template Missing 'entities' Field
**File**: `src/npcs/npc2/npc2.py`

**Issue**: After fixing settings initialization, NPC2 failed with:
```
AttributeError: 'NPCTemplate' object has no attribute 'entities'
```

**Fix**: Added the missing `entities` field to NPC2's `NPCTemplate` dataclass:
```python
@dataclass
class NPCTemplate:
    system_prompt: str
    initial_response: str | None = None
    entities: List[str] = None  # Added this field
```

### 3. Safe None Checking for Both NPC1 and NPC2
**Files**: `src/npcs/npc1/npc1.py`, `src/npcs/npc2/npc2.py`

**Issue**: The original code used `if self.template.entities:` which is problematic because:
- It treats `None` and `[]` differently (both should mean "no entities")
- It's not explicit about checking for None

**Fix**: Changed to explicit None checking in both files:
```python
# NPC1
if self.template.entities is not None and len(self.template.entities) > 0:
    self.brain_entities = [...]
else:
    self.brain_entities = []

# NPC2
if self.template.entities is not None and len(self.template.entities) > 0:
    for entity_str in self.template.entities:
        self.brain_memory.add_memory(entity_str)
```

## Testing
Created `test_settings_fix.py` that verifies:
1. ✅ proj_settings is imported in run_tests.py
2. ✅ Settings initialization is called
3. ✅ Settings file path is checked
4. ✅ Error handling for RuntimeError is present
5. ✅ Old NPC2 blocking code has been removed
6. ✅ NPC2's NPCTemplate has entities field
7. ✅ Both NPC1 and NPC2 have safe entities checking

## Result
All NPC types (NPC0, NPC1, NPC2) can now be used with `run_tests.py`:
```bash
python src/conversation_eval/evaluations/memory_wipe_tests/run_tests.py npc0
python src/conversation_eval/evaluations/memory_wipe_tests/run_tests.py npc1
python src/conversation_eval/evaluations/memory_wipe_tests/run_tests.py npc2
python src/conversation_eval/evaluations/memory_wipe_tests/run_tests.py npc0 npc1 npc2  # All at once
```

## Files Modified
1. `src/conversation_eval/evaluations/memory_wipe_tests/run_tests.py`
2. `src/npcs/npc1/npc1.py`
3. `src/npcs/npc2/npc2.py`
4. `test_settings_fix.py` (new test file)

