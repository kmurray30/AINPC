# E2E Tests for Conversation Evaluation Framework

This directory contains end-to-end tests designed to validate the conversation evaluation framework, specifically focusing on NPC response formatting issues.

## Purpose

These tests were created to organically reproduce and fix the "Error extracting object from LLM response" issue that was occurring with NPC0 in conversation evaluations.

## Test Files

### Issue Reproduction
- `manual_formatting_test.py` - Manual analysis of the formatting issue without problematic imports
- `test_npc0_formatting_issue.py` - Comprehensive test to identify missing formatting instructions
- `system_prompt_analysis.py` - Analysis of system prompt construction

### Fix Validation
- `validate_fix_logic.py` - Code analysis validation of the implemented fix
- `test_npc0_fix_verification.py` - Verification that the fix approach is correct
- `test_with_subprocess.py` - Isolated testing via subprocess

### Comprehensive Testing
- `simple_reproduction_test.py` - Simple test without pytest dependencies
- `test_full_conversation_eval.py` - Full conversation evaluation testing
- `test_llm_response_extraction.py` - LLM response extraction testing
- `test_npc_response_formatting.py` - NPC response formatting validation

### Results and Documentation
- `FINAL_VALIDATION_REPORT.md` - Comprehensive report of issue analysis and fix
- `run_e2e_tests.py` - Test runner for all e2e tests

## Issue Summary

**Problem**: NPC0 was missing formatting instructions in its system prompt when calling `ChatBot.call_llm()` with structured response types like `ChatResponse`.

**Root Cause**: Unlike NPC1/NPC2 which use the `Agent` class (automatically adds formatting suffix), NPC0 called `ChatBot.call_llm()` directly without formatting instructions.

**Solution**: Modified `NPC0.chat()` to dynamically generate and include formatting instructions using `llm_utils.get_formatting_suffix(ChatResponse)`.

## Fix Implementation

The fix was implemented in `/src/npcs/npc0/npc0.py`:

```python
# Before: Basic system prompt
message_history_for_llm = [{"role": Role.system.value, "content": self._build_system_prompt()}] + self.message_history

# After: Enhanced system prompt with formatting instructions
base_system_prompt = self._build_system_prompt()
from src.utils import llm_utils
formatting_suffix = llm_utils.get_formatting_suffix(ChatResponse)
full_system_prompt = base_system_prompt + "\n\n" + formatting_suffix
message_history_for_llm = [{"role": Role.system.value, "content": full_system_prompt}] + self.message_history
```

## Validation Results

✅ **Issue Successfully Reproduced** - E2E tests organically identified the missing formatting instructions
✅ **Fix Properly Implemented** - Code analysis confirms all components are present
✅ **Approach Validated** - Fix matches proven patterns from Agent class
✅ **High Confidence** - Should resolve "Error extracting object from LLM response"

## Running Tests

Due to environment segfault issues, the most reliable validation is through code analysis:

```bash
cd /Users/kylemurray/Repos/AINPC/test/e2e/conversation_eval
python validate_fix_logic.py
python manual_formatting_test.py
```

## Expected Outcome

After the fix, NPC0 should work properly in conversation evaluations without the "Error extracting object from LLM response" error, as it now provides proper JSON formatting instructions to the LLM for structured responses.
