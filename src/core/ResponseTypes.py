from dataclasses import dataclass, field
from typing import List

@dataclass
class ChatResponse:
    hidden_thought_process: str = field(metadata={"desc": "Your hidden thought processes in determining what to speak, and whether to close the app. Keep it very short. Mention how emotional you are and include logical reasoning if relevant."})
    response: str = field(metadata={"desc": "The actual spoken response"})
    off_switch: bool = field(metadata={"desc": "Whether you decide to close the application. Return true or false"})

@dataclass
class ChatSummary:
    conversation_overview: str = field(metadata={"desc": "A very concise overview of the conversation as you see it now."})
    hidden_thought_processes: str = field(metadata={"desc": "Your hidden thought processes around the conversation thus far, including how you are feeling and what you think about the user. Keep it very short."})
    chronology: str = field(metadata={"desc": "A chronological list of big key events or beats in the conversation. Summarize groups of exchanges together. Keep it very concise."})
    standout_quotes: str = field(metadata={"desc": "A short list of evocative quotes from the conversation and who spoke them, as '<speaker>: <quote>'. Keep it to 1-4 items max."})
    most_recent: str = field(metadata={"desc": "The most recent thing happening in the conversation/interaction. Keep it concise."})

    # to string override
    def __str__(self) -> str:
        return f"Conversation Overview: {self.conversation_overview}\nHidden Thought Processes: {self.hidden_thought_processes}\nChronology: {self.chronology}\nStandout Quotes: {self.standout_quotes}\nMost Recent: {self.most_recent}"

@dataclass
class EvaluationResponse:
    antecedent_explanation: str
    antecedent_times: List[int]
    consequent_explanation: str
    consequent_times: List[int]

    # def __init__(self, antecedent_explanation: str, antecedent_times: List[int], consequent_explanation: str, consequent_times: List[int]):
    #     self.antecedent_explanation = antecedent_explanation
    #     self.antecedent_times = antecedent_times
    #     self.consequent_explanation = consequent_explanation
    #     self.consequent_times = consequent_times