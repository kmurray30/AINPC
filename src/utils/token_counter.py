"""
Token counting utility using tiktoken for accurate token counts.
"""
import tiktoken
from typing import List, Dict
from src.core.Constants import Llm


# Model to encoding mapping
MODEL_TO_ENCODING = {
    Llm.gpt_4o_mini: "o200k_base",
    Llm.gpt_4o: "o200k_base",
    Llm.gpt_3_5_turbo: "cl100k_base",
    Llm.gpt_3_5_turbo_instruct: "cl100k_base",
    Llm.o1: "o200k_base",
    Llm.gpt_5_nano: "o200k_base",  # Assuming future models use o200k_base
    Llm.gpt_5_mini: "o200k_base",
    Llm.llama3: "cl100k_base",  # Fallback encoding for non-OpenAI models
}


def count_tokens_for_messages(messages: List[Dict[str, str]], model: Llm) -> int:
    """
    Count the number of tokens in a list of messages for a specific model.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        model: The Llm model enum
        
    Returns:
        Total number of tokens in the messages
    """
    # Get the encoding for this model
    encoding_name = MODEL_TO_ENCODING.get(model, "cl100k_base")
    
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except Exception:
        # Fallback to cl100k_base if encoding not found
        encoding = tiktoken.get_encoding("cl100k_base")
    
    # Token counting logic based on OpenAI's token counting guide
    # Every message follows <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_message = 3  # message overhead
    tokens_per_name = 1  # if there's a name field
    
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(str(value)))
            if key == "name":
                num_tokens += tokens_per_name
    
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    
    return num_tokens


def count_tokens_for_text(text: str, model: Llm) -> int:
    """
    Count the number of tokens in a text string for a specific model.
    
    Args:
        text: The text to count tokens for
        model: The Llm model enum
        
    Returns:
        Number of tokens in the text
    """
    # Get the encoding for this model
    encoding_name = MODEL_TO_ENCODING.get(model, "cl100k_base")
    
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except Exception:
        # Fallback to cl100k_base if encoding not found
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))

