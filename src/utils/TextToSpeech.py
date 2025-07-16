import os
from pathlib import Path
from os import environ

import openai
# from dotenv import load_dotenv
from openai import OpenAI

filename = os.path.splitext(os.path.basename(__file__))[0]
if __name__ == "__main__" or __name__ == filename: # If the script is being run directly
    from Utilities import init_dotenv
else: # If the script is being imported
    from .Utilities import init_dotenv

# load_dotenv()
init_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

import simpleaudio as sa

def play_audio_file(file_path):
    try:
        # Load the audio file from the provided path
        wave_obj = sa.WaveObject.from_wave_file(file_path)
        
        # Play the audio
        play_obj = wave_obj.play()
        
        # Wait for the audio to finish playing
        play_obj.wait_done()
    except Exception as e:
        print(f"An error occurred while playing the audio: {e}")

def cancel_audio():
    sa.stop_all()

def delete_audio_file(file_path):
    # only delete audio files in the generated directory
    if os.path.exists(file_path) and "/generated/" in file_path and Path(file_path).suffix == ".wav":
        os.remove(file_path)
    else:
        print("The file does not exist")

def generate_speech_file(prompt, file_path, voice = "echo"):
    with (client.audio.speech.with_streaming_response.create(
      model="tts-1",
      voice=voice,
      input=prompt,
      response_format="wav"
    )) as response:
        if response.status_code != 200:
            print(f"Failed to convert the text to speech. Status code: {response.status_code}")
            return
        print("response: ", response)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        response.stream_to_file(file_path)