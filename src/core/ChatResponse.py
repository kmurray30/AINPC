
class ChatResponse:
    explanation: str
    response: str

    def __init__(self, explanation: str, response: str):
        self.explanation = explanation
        self.response = response