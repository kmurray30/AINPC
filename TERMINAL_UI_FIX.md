# Terminal UI Fix - Cursor-Up Redraw Approach

## Problem
The original `TerminalUI` implementation used ANSI cursor save/restore (`\033[s` and `\033[u`) with relative cursor positioning to update specific lines in place. However, this approach had compatibility issues:

1. Cursor save/restore doesn't work reliably across all terminal emulators
2. In multithreaded environments, the cursor position could be corrupted between save and restore
3. When output is piped or redirected, cursor positioning breaks entirely
4. The cursor wasn't being returned to the end after each update, causing subsequent prints to appear in the wrong location

## Initial Fix Attempt
First tried using `\033[2J\033[H` (clear screen + move to home) to redraw the entire UI. This worked within a single test, but **cleared all previous test output** when running multiple tests sequentially.

## Final Solution
Replaced the cursor save/restore approach with a **cursor-up redraw** strategy:

### Key Changes
1. **State Tracking**: The UI maintains internal state for each conversation and evaluation
2. **First Render**: Initial render prints normally (no cursor movement)
3. **Subsequent Renders**: 
   - Move cursor UP by the number of lines previously rendered (`\033[NA`)
   - Clear and reprint each line (`\033[2K` + content)
   - Track new line count for next update
4. **Thread-Safe**: Uses locks to ensure only one render happens at a time
5. **Test Isolation**: Each test's UI only updates its own section, preserving previous test output

### Implementation Details
- `ConversationState`: Tracks the current display text for generating and evaluation status
- `CaseState`: Groups all conversations for a single test case
- `first_render` flag: Tracks whether this is the initial render (no cursor movement needed)
- `lines_rendered`: Tracks how many lines were printed, used for cursor-up positioning
- `_render()`: 
  1. Builds the entire UI as a list of strings
  2. If not first render, moves cursor up to overwrite previous content
  3. Prints each line with `\033[2K` (clear line) prefix
  4. Updates tracking variables

### Why This Works
- **No Clear Screen**: Unlike `\033[2J`, we never clear the entire screen, preserving all previous output
- **Relative Positioning**: `\033[NA` (cursor up N lines) is simpler and more reliable than save/restore
- **Line-by-Line Clear**: `\033[2K` clears each line before writing, ensuring clean updates
- **Self-Contained**: Each test UI manages its own section without affecting others

### Performance
Fast enough that updates appear instant on modern terminals. Each redraw is ~20-30 lines, and cursor-up is a single ANSI command.

### Benefits
- **Bulletproof**: Works on all terminals that support basic ANSI cursor movement (universal support)
- **Preserves History**: Previous tests remain visible in the terminal
- **Simpler**: State-based rendering is easier to reason about than complex cursor manipulation
- **Testable**: The `VirtualTerminal` in snapshot tests accurately represents real terminal behavior
- **Maintainable**: Adding new UI elements just requires updating the lines list in `_render()`

## Testing
All 7 snapshot tests pass with the new implementation:
- Initial render
- Conversation progress updates
- Multiple conversations in parallel
- Sequential tests with no overlap
- Evaluation progress tracking
- Multiple test cases

Run tests with:
```bash
python -m pytest test/e2e/conversation_eval/test_terminal_snapshots.py -v
```

