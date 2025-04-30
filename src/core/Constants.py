from enum import Enum

class Role(Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class AgentName(Enum):
    you = "You"
    pat = "Pat"
    mock_user = "Mock User"

class Llm(Enum):
    gpt_3_5_turbo = "gpt-3.5-turbo"
    gpt_3_5_turbo_instruct = "gpt-3.5-turbo-instruct"
    gpt_4o_mini = "gpt-4o-mini"
    gpt_4o = "gpt-4o"
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

class Constants:
    pass_name = "Pass"
    fail_name = "Fail"
    indeterminant_name = "Indeterminant"
    antecedent_placeholder = "$ANTECEDENT$"
    consequent_placeholder = "$CONSEQUENT$"