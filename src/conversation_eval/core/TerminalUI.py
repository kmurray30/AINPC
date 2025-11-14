"""
Terminal UI Manager for Parallel Evaluation Execution
Uses clear-and-redraw approach for maximum terminal compatibility
"""
import threading
from typing import Dict, List
from dataclasses import dataclass


# ANSI escape codes
CLEAR_SCREEN = '\033[2J'
MOVE_TO_TOP = '\033[H'
MOVE_TO_LINE = '\033[{}H'
CLEAR_LINE = '\033[2K'

# Colors
BOLD = '\033[1m'
BLUE = '\033[34m'
GREEN = '\033[32m'
RESET = '\033[0m'


@dataclass
class ConversationState:
    """Track state of a single conversation"""
    generating_progress: str = f"{BLUE}Generating ⏳{RESET}"
    evaluation_progress: str = "Evaluation pending ⏳"


@dataclass
class CaseState:
    """Track state of a single case"""
    conversations: Dict[int, ConversationState]  # convo_idx -> state


class TerminalUI:
    """
    Thread-safe terminal UI manager that redraws the entire display on each update.
    More compatible than cursor save/restore approach.
    """
    
    def __init__(self, test_name: str, npc_type: str, eval_cases: List, convos_per_user_prompt: int, convo_length: int, eval_iterations_per_eval: int):
        self.lock = threading.Lock()
        self.test_name = test_name
        self.npc_type = npc_type
        self.eval_cases = eval_cases
        self.convos_per_user_prompt = convos_per_user_prompt
        self.convo_length = convo_length
        self.eval_iterations_per_eval = eval_iterations_per_eval
        self.total_turns = convo_length * 2
        
        # Track state for each case and conversation
        self.case_states: Dict[int, CaseState] = {}
        for case_idx in range(1, len(eval_cases) + 1):
            convos = {}
            for convo_idx in range(1, convos_per_user_prompt + 1):
                convos[convo_idx] = ConversationState()
            self.case_states[case_idx] = CaseState(conversations=convos)
        
        # Track if this is the first render (no clear screen on first render)
        self.first_render = True
        # Track how many lines we've rendered (for cursor repositioning)
        self.lines_rendered = 0
        
        # Render initial display
        self._render()
    
    def _render(self):
        """Render the entire UI, either fresh or by overwriting existing content"""
        with self.lock:
            # Build the output as a string first so we can count lines
            lines = []
            
            # Header
            lines.append("")
            lines.append("="*60)
            lines.append(f"{BOLD}🧪 Test: {self.test_name} ({self.npc_type.upper()}){RESET}")
            lines.append("="*60)
            lines.append("")
            
            # Each case
            for case_idx, eval_case in enumerate(self.eval_cases, 1):
                lines.append("─"*60)
                lines.append(f"{BOLD}📝 Case {case_idx}/{len(self.eval_cases)}{RESET}")
                
                # Proposition
                proposition = eval_case.propositions[0]
                prop_text = f"{proposition.antecedent.value} -> {proposition.consequent.value}"
                lines.append(prop_text)
                lines.append("")
                
                # Conversations
                case_state = self.case_states[case_idx]
                for convo_idx in range(1, self.convos_per_user_prompt + 1):
                    convo_state = case_state.conversations[convo_idx]
                    lines.append(f"Conversation {convo_idx}:")
                    lines.append(f"    {convo_state.generating_progress}")
                    lines.append(f"    {convo_state.evaluation_progress}")
                    lines.append("")
            
            # Final separator
            lines.append("─"*60)
            lines.append("")
            
            # If not first render, move cursor back up to overwrite
            if not self.first_render and self.lines_rendered > 0:
                # Move cursor up to start of our section
                print(f'\033[{self.lines_rendered}A', end='', flush=True)
            
            # Print all lines, clearing each line before writing
            for line in lines:
                print(f'\033[2K{line}')  # Clear line, then print
            
            # Update state
            self.first_render = False
            self.lines_rendered = len(lines)
    
    def update_conversation_progress(self, case_idx: int, convo_idx: int, current: int, total: int):
        """Update conversation generation progress"""
        if case_idx not in self.case_states:
            return
        if convo_idx not in self.case_states[case_idx].conversations:
            return
        
        convo_state = self.case_states[case_idx].conversations[convo_idx]
        if current == total:
            convo_state.generating_progress = f"{BLUE}Generating ({current}/{total}) {GREEN}✓{RESET}  "
        else:
            convo_state.generating_progress = f"{BLUE}Generating ({current}/{total})...{RESET}"
        
        self._render()
    
    def mark_conversation_complete(self, case_idx: int, convo_idx: int):
        """Mark conversation as complete"""
        if case_idx not in self.case_states:
            return
        if convo_idx not in self.case_states[case_idx].conversations:
            return
        
        convo_state = self.case_states[case_idx].conversations[convo_idx]
        convo_state.generating_progress = f"{BLUE}Generating ({self.total_turns}/{self.total_turns}) {GREEN}✓{RESET}  "
        
        self._render()
    
    def update_evaluation_progress(self, case_idx: int, convo_idx: int, current: int, total: int):
        """Update evaluation progress"""
        if case_idx not in self.case_states:
            return
        if convo_idx not in self.case_states[case_idx].conversations:
            return
        
        convo_state = self.case_states[case_idx].conversations[convo_idx]
        if current == total:
            convo_state.evaluation_progress = f"{BLUE}Evaluating ({current}/{total}) {GREEN}✓{RESET}  "
        else:
            convo_state.evaluation_progress = f"{BLUE}Evaluating ({current}/{total})...{RESET}"
        
        self._render()
    
    def mark_evaluation_complete(self, case_idx: int, convo_idx: int):
        """Mark evaluation as complete"""
        if case_idx not in self.case_states:
            return
        if convo_idx not in self.case_states[case_idx].conversations:
            return
        
        convo_state = self.case_states[case_idx].conversations[convo_idx]
        convo_state.evaluation_progress = f"{BLUE}Evaluating ({self.eval_iterations_per_eval}/{self.eval_iterations_per_eval}) {GREEN}✓{RESET}  "
        
        self._render()
    
    def move_cursor_to_end(self):
        """Move cursor to the end (no-op for clear-and-redraw approach)"""
        pass

