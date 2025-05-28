
class KeyMatch:
    key: str
    similarity: float

    def __init__(self, key: str, similarity: float):
        self.key = key
        self.similarity = similarity

class BrainResultContent:
    highest_match: float = 0
    key_matches: list[KeyMatch] = []

    def add_key_match(self, key: str, similarity: float):
        if similarity > self.highest_match:
            self.highest_match = similarity
        self.key_matches.append(KeyMatch(key, similarity))

class BrainResults:
    query_results: dict[str, BrainResultContent] = []

    def add_query_result(self, content: str, key: str, similarity: float):
        if key not in self.query_results:
            key_match = KeyMatch(key, similarity)
            brain_result_content = BrainResultContent()

            self.query_results[key] = BrainResultContent()