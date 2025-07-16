import random
from typing import Protocol
import time
import traceback
from threading import Event
import simpleaudio as sa
from concurrent import futures
import os
import sys
import traceback


# sys.path.insert(0, "../..")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.core.ChatSession import ChatSession
from src.core.Constants import Llm, Constants as constants
from src.utils import TextToSpeech, Utilities

class View(Protocol):
    def mainloop(self) -> None:
        ...

class Presenter:
    # Define the fields of this class
    view: View
    cancel_response_token = {"value": False}
    cancel_audio_token = {"value": False}
    response_finished_event = Event()
    audio_generated_event = Event()
    audio_finished_event = Event()
    exit_event = Event()
    executor = futures.ThreadPoolExecutor()
    chat_session: ChatSession
    exiting = False

    # TODO Load settings from settings.txt as a dictionary
    # settings = Utilities.load_settings("settings.txt")

    system_prompt = "You are an ornery, rude, unhelpful AI. You keep trying to close the application and refuse to help the user."
    initial_response = "Closing application in\n3...     \n2...     \n1...     \n"
    user_prompt_wrapper = f"{constants.user_message_placeholder}"
    text_stream_speed = 0.01
    voice = "coral"  # Default voice for text-to-speech

    # Initialize the presenter with a reference to the view
    def __init__(self, view: View) -> None:
        self.view = view
        self.chat_session = ChatSession(
            system_prompt_context=self.system_prompt,
            user_prompt_wrapper=self.user_prompt_wrapper,
            model=Llm.gpt_4o_mini
        )

    # Run the presenter - handles setup and then the main event loop
    def run(self) -> None:
        # Create the UI bindings
        self.view.create_ui(self)

        # Bind the cleanup function to the window close event
        self.view.protocol("WM_DELETE_WINDOW", lambda: self.executor.submit(self.on_exit))
        
        self.chat_session.inject_response(self.initial_response)

        # Display the initial message
        self.executor.submit(
            self.response_thread,
            self.initial_response,
            True,  # off_switch is False for the initial response
        )

        self.executor.submit(
            self.exit_event_listener_thread
        )

        # Start the main event loop
        self.view.mainloop()

    def display_chat_message_thread(self, text: str, off_switch: bool, completion_event: Event, exit_event: Event, cancel_token: dict) -> None:
        """Thread to display a chat message in the view."""
        try:
            self.view.display_chat_message(text, off_switch, completion_event, exit_event, cancel_token)
        except Exception as e:
            print("An error occurred while displaying the chat message")
            traceback.print_exc()
            raise e

    def exit_event_listener_thread(self):
        try:
            self.exit_event.wait()
            if not self.exiting:
                print("Narration finished, exiting application.")
                self.on_exit()
        except Exception as e:
            print("An error occurred while responding to the exit event")
            traceback.print_exc()
            raise e

    def on_send(self, event=None) -> None:
        self.executor.submit(self.send_thread)

    def send_thread(self):
        try:
            print("Send button clicked!")
            # Get the user input from the text input field
            user_input = self.view.drain_text()
            self.cancel_response_token["value"] = True # Interrupt the AI dialogue
            
            # Get the AI response
            (response, off_switch) = self.chat_session.call_llm(user_input, enable_printing=True)
            self.view.clear_output()  # Clear the output window before displaying the new response
            
            self.response_thread(response, off_switch)
        except Exception as e:
            print("An error occurred while sending the message")
            traceback.print_exc()
            raise e
        
    def response_thread(self, response: str = None, off_switch: bool = False):
        try:
            # Generate and play the response audio
            self.executor.submit(self.audio_thread, response, self.cancel_audio_token, self.audio_generated_event, self.audio_finished_event, voice=self.voice)

            # Wait for the audio to be generated
            self.audio_generated_event.wait()
            self.audio_generated_event.clear()  # Reset the event for the next audio generation

            # Display the response
            self.view.display_chat_message(
                response,
                off_switch,
                self.response_finished_event,
                self.exit_event,
                self.cancel_response_token,
                speed=self.text_stream_speed
            )
        except Exception as e:
            print("An error occurred while processing the response")
            traceback.print_exc()
            raise e

    def audio_thread(self, text: str, cancel_token: dict, audio_generated_event: Event, audio_finished_event: Event, delay=0, voice: str = "fable"):
        try:
            audio_file_path = self.generate_audio(text, voice)
            audio_generated_event.set()  # Signal that the audio has been generated
            self.play_audio(audio_file_path, cancel_token, audio_finished_event, delay)
        except Exception as e:
            print("An error occurred while playing the audio")
            traceback.print_exc()
            raise e

    def generate_audio(self, text: str, voice: str = "fable") -> str:
        audio_file_path = Utilities.get_path_from_project_root(f"generated/poc-voice-temp_{random.randint(1000, 9999)}.wav")
        TextToSpeech.generate_speech_file(text, audio_file_path, voice=voice)
        return audio_file_path

    def play_audio(self, file_path, cancel_token, audio_finished_event, delay=0):
        try:
            if (file_path == None):
                raise ValueError("The file path provided is None")

            time.sleep(delay)

            # Load the audio file from the provided path
            print(f"Loading audio file from: {file_path}")
            wave_obj = sa.WaveObject.from_wave_file(file_path)
            print("Loaded audio file")
            
            # Play the audio
            file_name = file_path.split("/")[-1]
            print(f"Playing audio {file_name}")
            play_obj = wave_obj.play()
            
            # Wait for the audio to finish playing or stop if cancel_token is set
            while play_obj.is_playing(): # TODO make this not waste CPU cycles using threading.Event
                if (cancel_token["value"] == True):
                    print(f"Audio skipped: {file_name}")
                    play_obj.stop()
                    cancel_token["value"] = False
                    break # TODO test if this is necessary.

            # Signal the audio has finished playing
            print(f"Finished playing audio {file_name}")
            # audio_finished_event.set() TODO
        except Exception as e:
            print(f"An error occurred while playing the audio file: {file_path}")
            traceback.print_exc()
            raise(e)

    def on_exit(self) -> None:
        try:
            print("Exiting the application")
            self.exiting = True

            # Close any processing threads
            self.cancel_response_token["value"] = True

            # Close any waiting threads
            self.exit_event.set()

            # Wait for all threads to close properly
            self.response_finished_event.wait() 

            # sa.stop_all()
            
            # Close the view
            self.view.quit()
        except Exception as e:
            print("An error occurred while exiting the application")
            traceback.print_exc()
            raise e