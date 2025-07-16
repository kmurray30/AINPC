import os
import sys
from typing import Dict, List
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils import TextToSpeech, Utilities

speaker_to_text: Dict[str, List[str]] = {}

def read_aloud(speaker: str, voice: str, i: int):
    message = speaker_to_text[speaker][i]
    print(f"Speaker: {speaker}")
    print(f"Message: {message}")

    audio_file_path = Utilities.get_path_from_project_root(f"generated/{speaker}{i}.wav")
    TextToSpeech.generate_speech_file(message, audio_file_path, voice)
    TextToSpeech.play_audio_file(audio_file_path)

# Extract the text from the text file
text_file_path = Utilities.get_path_from_project_root("notes/chat_history_1.txt")
with open(text_file_path, "r") as file:
    text = file.read()

# Convert the text to a map of speaker to text
for line in text.split("\n"):
    if line and ": " in line:
        speaker, message = line.split(": ", 1)
        if speaker in speaker_to_text:
            # Add to the list
            speaker_to_text[speaker] += [message]
        else:
            # Create a new list
            speaker_to_text[speaker] = [message]

# Speack the text for each speaker
max_messages = max(len(messages) for messages in speaker_to_text.values())
for i in range(max_messages):
    read_aloud("Pat", "nova", i)
    read_aloud("Mock User", "sage", i)
    