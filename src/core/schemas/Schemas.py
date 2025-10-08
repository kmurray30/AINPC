from dataclasses import dataclass, fields
from src.core.Constants import Llm
from src.utils import Logger


@dataclass
class AppSettings:
    game_title: str
    text_stream_speed: float
    summarization_prompt: str
    num_last_messages_to_retain_when_summarizing: int
    closing_enabled: bool
    model: Llm
    log_level: Logger.Level
    max_convo_mem_length: int
    save_name: str = ""


