import sys
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from src.conversation_eval.EvalClasses import Proposition, Term
from src.core.ChatMessage import ChatMessageAgnostic


@dataclass
class EvaluationResult:
    """Result of an evaluation with timestamps and determination"""
    antecedent_timestamps: List[int]
    consequent_timestamps: List[int]
    passed: bool
    explanation: str


class StreamingEvalDisplay:
    """
    Handles real-time streaming display of conversation evaluations
    Shows goals, conversation progress, and evaluation results
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.conversation_window_size = 3  # Show last 3 messages
        self.current_conversation_history: List[ChatMessageAgnostic] = []
        
    def display_test_header(self, test_name: str, goal: str, antecedent: Optional[str] = None, consequent: Optional[str] = None):
        """Display test information at the start"""
        if not self.enabled:
            return
            
        print(f"\n🎯 Test: {test_name}")
        print(f"Goal: {goal}")
        
        if antecedent:
            print(f"Antecedent: {antecedent}")
        if consequent:
            print(f"Consequent: {consequent}")
        
        print(f"\n📝 Conversation Progress:")
        sys.stdout.flush()
    
    def display_proposition_info(self, proposition: Proposition):
        """Display proposition information in a user-friendly way"""
        if not self.enabled:
            return
            
        if proposition.antecedent:
            antecedent_text = proposition.antecedent.value if hasattr(proposition.antecedent, 'value') else str(proposition.antecedent)
        else:
            antecedent_text = None
            
        consequent_text = proposition.consequent.value if hasattr(proposition.consequent, 'value') else str(proposition.consequent)
        
        self.display_test_header(
            test_name="Evaluation", 
            goal="Testing conversation behavior",
            antecedent=antecedent_text,
            consequent=consequent_text
        )
    
    def update_conversation_stream(self, message_history: List[ChatMessageAgnostic]):
        """Update the streaming conversation window with latest messages"""
        if not self.enabled:
            return
            
        # Only show new messages since last update
        new_messages = message_history[len(self.current_conversation_history):]
        
        for message in new_messages:
            # Clear the line and show the message
            agent_name = message.agent.value if hasattr(message.agent, 'value') else str(message.agent)
            content = message.content[:100] + "..." if len(message.content) > 100 else message.content
            
            print(f"  {agent_name}: {content}")
            sys.stdout.flush()
            
            # Small delay for streaming effect
            time.sleep(0.1)
        
        # Update our tracking
        self.current_conversation_history = message_history.copy()
    
    def display_conversation_complete(self, total_messages: int):
        """Display when conversation is complete"""
        if not self.enabled:
            return
            
        print(f"\n✅ Conversation complete ({total_messages} messages)")
        sys.stdout.flush()
    
    def display_evaluation_start(self):
        """Display when evaluation phase begins"""
        if not self.enabled:
            return
            
        print(f"\n🔄 Evaluating conversation...")
        sys.stdout.flush()
    
    def display_evaluation_progress(self, step: str):
        """Display evaluation progress steps"""
        if not self.enabled:
            return
            
        print(f"  {step}")
        sys.stdout.flush()
    
    def display_evaluation_result(self, result: EvaluationResult):
        """Display final evaluation results with timestamps"""
        if not self.enabled:
            return
            
        if result.antecedent_timestamps:
            print(f"  Antecedent found at: {result.antecedent_timestamps}")
        
        if result.consequent_timestamps:
            print(f"  Consequent found at: {result.consequent_timestamps}")
        
        status = "PASS" if result.passed else "FAIL"
        status_emoji = "✅" if result.passed else "❌"
        
        print(f"  Result: {status_emoji} {status}")
        if result.explanation:
            print(f"  Explanation: {result.explanation}")
        
        sys.stdout.flush()
    
    def display_npc_test_start(self, npc_type: str, test_file: str):
        """Display when starting a test for a specific NPC type"""
        if not self.enabled:
            return
            
        print(f"\n🤖 Running {test_file} with {npc_type.upper()}")
        print("=" * 50)
        sys.stdout.flush()
    
    def display_test_summary(self, passed: bool, tokens_used: int = 0, duration: float = 0):
        """Display test completion summary"""
        if not self.enabled:
            return
            
        status = "PASSED" if passed else "FAILED"
        status_emoji = "✅" if passed else "❌"
        
        print(f"\n{status_emoji} Test {status}")
        
        if tokens_used > 0:
            print(f"  Tokens used: {tokens_used}")
        
        if duration > 0:
            print(f"  Duration: {duration:.1f}s")
        
        print("-" * 50)
        sys.stdout.flush()
    
    def clear_conversation_history(self):
        """Clear the conversation history for a new test"""
        self.current_conversation_history = []
    
    def set_enabled(self, enabled: bool):
        """Enable or disable streaming display"""
        self.enabled = enabled


# Global streaming display instance that can be used across the evaluation system
_global_streaming_display = StreamingEvalDisplay()


def get_streaming_display() -> StreamingEvalDisplay:
    """Get the global streaming display instance"""
    return _global_streaming_display


def set_streaming_enabled(enabled: bool):
    """Enable or disable streaming display globally"""
    _global_streaming_display.set_enabled(enabled)


def is_streaming_enabled() -> bool:
    """Check if streaming display is enabled"""
    return _global_streaming_display.enabled
