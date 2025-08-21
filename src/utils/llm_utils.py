from typing import Dict, List, Type, TypeVar

from src.core.ChatMessage import ChatMessage
from src.utils import Utilities, parsing_utils

T = TypeVar('T')

prompt_formatting_message_prefix = "Format your response as a JSON object with the following keys:"
prompt_formatting_message_suffix = "Make sure to include all keys, even if they are empty or null. If the type is str and the description specifies a list, make sure the field is a single string delimited by semicolons."

# Iterate over the fields of the dataclass and add them to the prompt suffix
# This will be used to instruct the LLM on how to format its response
def get_formatting_suffix(response_type: Type[T], prepend_override: str = None, append_override: str = None) -> str:
    """Returns the prompt suffix that specifies the formatting of the LLM response."""
    # Note: This assumes that the response_type is a dataclass with fields
    if not hasattr(response_type, '__dataclass_fields__'):
        raise ValueError(f"Response type {response_type} is not a dataclass with fields.")
    prompt_suffix = f"{prompt_formatting_message_prefix}\n" if prepend_override is None else prepend_override
    prompt_suffix += "{\n"
    for field_name, field_info in response_type.__dataclass_fields__.items():
        prompt_suffix += f"\t{field_name} <type {field_info.type.__name__}>: {field_info.metadata.get('desc', '')}\n"
    prompt_suffix += "}\n"
    prompt_suffix += f"{prompt_formatting_message_suffix}\n" if append_override is None else append_override
    return prompt_suffix

def extract_obj_from_llm_response(response_raw: str, response_type: Type[T]) -> T:
    # If type is primitive, we can directly parse it
    if response_type in [str, int, float, bool]:
        if response_raw.strip() == "":
            raise ValueError("Response is empty")
        return response_type(response_raw.strip())
    response_obj = parsing_utils.extract_obj_from_json_str(response_raw, response_type, trim=True)
    return response_obj

def convert_messaget_history_to_llm_format(message_history: List[ChatMessage], include_hidden_details: bool = True) -> List[Dict[str, str]]:
    message_history_dict_list = []
    for message in message_history:
        role = message.role
        if include_hidden_details and message.cot is not None:
            # Format the content as a json string of the ChatResponse class (TODO make it agnostic to the class)
            content = "{"
            content += f'\t"hidden_thought_process": "{message.cot}", '
            content += f'\t"response": "{message.content}", '
            content += f'\t"off_switch": {str(message.off_switch).lower()}'
            content += "}"
        else:
            content = message.content # User responses will fall here
        message_history_dict_list.append({"role": role.name, "content": Utilities.decode(content)})
    return message_history_dict_list