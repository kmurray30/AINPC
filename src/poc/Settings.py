from dataclasses import dataclass, fields
import yaml

@dataclass
class Settings:
    game_title: str
    text_stream_speed: float
    summarization_prompt: str
    system_prompt_context: str
    initial_response: str
    closing_enabled: bool
    save_name: str = ""
    
    def validate(self) -> bool:
        for field in fields(self):
            if getattr(self, field.name) is None or getattr(self, field.name) == "":
                raise ValueError(f"Invalid settings: {field.name} must be provided.")
        return True