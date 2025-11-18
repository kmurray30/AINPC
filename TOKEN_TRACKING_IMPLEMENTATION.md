# Token Tracking and Cost Calculation Implementation

## Overview
Implemented comprehensive token tracking and cost calculations throughout the evaluation system, with real-time cost display in the table UI and summary reports.

## What Was Implemented

### 1. TokenCount Class (EvalReports.py)
- **`TokenCount` dataclass** tracks:
  - `model: Llm` - Model used for the LLM call
  - `input_tokens: int` - Input token count
  - `output_tokens: int` - Output token count
  - `cost: float` - Calculated cost in USD

- **Static methods**:
  - `calculate_cost()` - Calculates cost from token counts and model pricing
  - `create()` - Factory method that auto-calculates cost

- **Helper function**:
  - `aggregate_token_counts()` - Aggregates list of TokenCount objects to return total cost

### 2. Pricing Dictionary (Constants.py)
Added `LLM_PRICING` dict with pricing per 1M tokens for all models:
```python
LLM_PRICING = {
    Llm.gpt_4o_mini: {"input": 0.150, "output": 0.600},
    Llm.gpt_4o: {"input": 2.50, "output": 10.00},
    Llm.gpt_3_5_turbo: {"input": 0.50, "output": 1.50},
    # ... etc
}
```

### 3. Token Counting Utility (token_counter.py)
New file using `tiktoken` for accurate token counting:
- `count_tokens_for_messages()` - Counts tokens in message list
- `count_tokens_for_text()` - Counts tokens in text string
- Handles different model encodings (o200k_base, cl100k_base)

### 4. ChatBot Token Return (ChatBot.py)
- Modified `_call_llm_internal()` to return `Tuple[str, TokenCount]`
- Counts input tokens before API call
- Counts output tokens from response
- Returns both response and TokenCount
- Updated all internal callers to handle tuple return

### 5. Agent Token Tracking (Agent.py)
- Added `last_token_count: TokenCount` field to track most recent LLM call
- Updated `chat_with_history()` to store token count from ChatBot
- Token count accessible via `agent.last_token_count`

### 6. Evaluation Pipeline Token Threading
Updated all report dataclasses to use `tokens: List[TokenCount]` instead of `tokens: int`:
- `EvaluationIterationEvalReport`
- `ConversationEvaluationEvalReport`
- `EvaluationEvalReport`
- `UserPromptEvalReport`
- `AssistantPromptEvalReport`
- `EvalReport`

Token aggregation flows bottom-up:
1. Each evaluation iteration stores its TokenCount
2. Conversation evaluation aggregates from all iterations
3. Evaluation report aggregates from all conversations
4. User prompt report aggregates from all evaluations
5. Assistant prompt report aggregates from all user prompts
6. Final EvalReport aggregates from assistant prompts

### 7. Table UI Cost Display (TableTerminalUI.py)
Enhanced terminal UI to show costs:
- Added `cost_usd: float` field to `CellProgress`
- Added `cost_col_width = 12` for cost column width
- **New "cost" column** (rightmost) showing USD per row
- **New "cost" row** (bottom) showing USD per column
- **Bottom-right cell** shows grand total cost
- Costs display only when all cells in row/column are "done"
- Format: `$X.XX` with 2 decimal places

Updated methods:
- `set_results()` - Now accepts `cost_usd` parameter
- `_render()` - Builds cost column and row
- `_calculate_cost_row()` - Calculates cost totals per NPC column
- `_format_cost()` - Formats USD with 2 decimals
- `get_table_string()` - Includes costs in saved table

### 8. CSV Summary with Costs (ReportGenerator.py)
Enhanced CSV generation to include cost data:
- Added "cost" column showing row totals
- Added "cost" row showing column totals
- Bottom-right cell shows grand total
- Renamed `_extract_propositions_and_scores()` to `_extract_propositions_scores_and_costs()`
- Returns tuples of (prop_text, score, cost)

### 9. Integration Updates
- **ParallelEvalRunner.py**: Thread tokens through entire parallel execution pipeline
- **ConversationParsingBot.py**: Return TokenCount with evaluation results
- **EvalHelper.py**: Aggregate tokens at each level
- **ConversationMemory.py**: Handle tuple return from summarization (tokens not tracked for summarization)

## Cost Calculation Formula
```python
cost = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
```

## Token Counting Method
Uses `tiktoken` library (OpenAI's official tokenizer):
- Fast and accurate
- Handles different model encodings
- Accounts for message formatting overhead
- Works for both OpenAI and non-OpenAI models (with fallback encoding)

## Table Format
```
+--------------------------------+----------+----------+----------+--------------+
|                                | npc0     | npc1     | npc2     | cost         |
+--------------------------------+----------+----------+----------+--------------+
| test_name case 1               | 1/1      | 1/1      | 1/1      | $0.12        |
| test_name case 2               | 0/1      | 1/1      | 0/1      | $0.09        |
+--------------------------------+----------+----------+----------+--------------+
| total                          | 1/2      | 2/2      | 1/2      |              |
| cost                           | $0.05    | $0.08    | $0.08    | $0.21        |
+--------------------------------+----------+----------+----------+--------------+
```

## Files Modified
1. `src/core/Constants.py` - Added LLM_PRICING dict
2. `src/conversation_eval/core/EvalReports.py` - Added TokenCount class, changed all tokens fields to List[TokenCount]
3. `src/utils/token_counter.py` - NEW FILE - Token counting utilities
4. `requirements.txt` - Added tiktoken==0.8.0
5. `src/utils/ChatBot.py` - Return TokenCount from all LLM calls
6. `src/core/Agent.py` - Track and expose last_token_count
7. `src/conversation_eval/core/ConversationParsingBot.py` - Return TokenCount with evaluations
8. `src/conversation_eval/core/ParallelEvalRunner.py` - Aggregate tokens throughout pipeline
9. `src/conversation_eval/core/EvalHelper.py` - Aggregate tokens in legacy evaluation path
10. `src/core/ConversationMemory.py` - Handle tuple return from summarization
11. `src/conversation_eval/core/TableTerminalUI.py` - Display costs in table
12. `src/conversation_eval/core/ReportGenerator.py` - Include costs in CSV summary

## Testing
To test, run:
```bash
python src/conversation_eval/evaluations/memory_wipe_tests/run_tests.py npc0
```

You should see:
- Cost column appearing on the right
- Cost row appearing at the bottom
- Grand total in bottom-right corner
- Costs displayed when tests complete

## Notes
- Ollama (llama3) has $0.00 cost (local model)
- Future GPT-5 models have placeholder pricing
- Token counting adds minimal overhead (tiktoken is very fast)
- All costs stored as floats in JSON, formatted as strings in display

