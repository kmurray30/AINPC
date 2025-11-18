from enum import Enum

class Role(Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class AgentName(Enum):
    you = "You"
    pat = "Pat"
    ai = "AI"
    player = "Player"
    mock_user = "Mock User"

class Llm(Enum):
    gpt_3_5_turbo = "gpt-3.5-turbo"
    gpt_3_5_turbo_instruct = "gpt-3.5-turbo-instruct"
    gpt_4o_mini = "gpt-4o-mini"
    gpt_4o = "gpt-4o"
    gpt_5_nano = "gpt-5-nano"
    gpt_5_mini = "gpt-5-mini"
    o1 = "o1-preview"
    llama3 = "llama3"

class Platform(Enum):
    open_ai = "openai"
    ollama = "ollama"

embedding_models = {
    Platform.open_ai: [
        Llm.gpt_3_5_turbo,
        Llm.gpt_3_5_turbo_instruct,
        Llm.gpt_4o_mini,
        Llm.gpt_4o,
        Llm.o1,
        Llm.gpt_5_nano,
        Llm.gpt_5_mini,
    ],
    Platform.ollama: [
        Llm.llama3,
    ]
}

class EvaluationError(Enum):
    ANTECEDENT_UNEXPECTEDLY_OCCURRED = 0
    ANTECEDENT_UNEXPECTEDLY_DID_NOT_OCCUR = 1
    CONVERSATION_TOO_SHORT = 2
    ANTECEDENT_OCCURRED_TOO_LATE = 3

class PassFail(Enum):
    INDETERMINANT = None
    FAIL = 0
    PASS = 1

# Pricing per 1M tokens (as of Nov 2024)
# Source: OpenAI pricing page
LLM_PRICING = {
    Llm.gpt_4o_mini: {"input": 0.150, "output": 0.600},  # per 1M tokens
    Llm.gpt_4o: {"input": 2.50, "output": 10.00},
    Llm.gpt_3_5_turbo: {"input": 0.50, "output": 1.50},
    Llm.gpt_3_5_turbo_instruct: {"input": 1.50, "output": 2.00},
    Llm.o1: {"input": 15.00, "output": 60.00},
    # Placeholder pricing for models without official pricing
    Llm.gpt_5_nano: {"input": 0.10, "output": 0.40},
    Llm.gpt_5_mini: {"input": 0.20, "output": 0.80},
    Llm.llama3: {"input": 0.0, "output": 0.0},  # Local model, no cost
}

class Constants:
    pass_name = "Pass"
    fail_name = "Fail"
    indeterminant_name = "Indeterminant"
    antecedent_placeholder = "$ANTECEDENT$"
    consequent_placeholder = "$CONSEQUENT$"
    user_message_placeholder = "$USER_MESSAGE$"