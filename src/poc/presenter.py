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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))) # Adjust the path to the project root
from src.core.ChatSession import ChatSession
from src.core.Constants import Llm, Constants as constants, Role
from src.utils import TextToSpeech, Utilities
from src.utils import Logger
from src.utils.Logger import Level

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
    exit_by_assistant_event = Event()
    executor = futures.ThreadPoolExecutor()
    chat_session: ChatSession
    exiting = False
    closed_by: Role = None
    max_chat_history_length = 10

    # TODO Load settings from settings.txt as a dictionary
    # settings = Utilities.load_settings("settings.txt")

    initial_response = "Closing application"
    user_prompt_wrapper = f"{constants.user_message_placeholder}"
    text_stream_speed = 0.01
    delay_before_closing_by_ai = 0.5  # Delay before closing the application after the AI response
    voice = "sage"  # Default voice for text-to-speech

    # Initialize the presenter with a reference to the view
    def __init__(self, view: View) -> None:
        self.view = view
        self.chat_session = ChatSession(
            system_prompt_context=None,  # Use the default system prompt context
            user_prompt_wrapper=self.user_prompt_wrapper,
            model=Llm.gpt_4o_mini,
            load_old_session_flag=True,  # Load existing chat session if available
        )

    # Run the presenter - handles setup and then the main event loop
    def run(self) -> None:
        # Create the UI bindings
        self.view.create_ui(self)

        # Bind the cleanup function to the window close event
        self.view.protocol("WM_DELETE_WINDOW", lambda: self.executor.submit(self.on_exit_button_action))
        
        self.chat_session.inject_message("The user has opened the application", role=Role.system)  # Inject the system prompt into the chat session

        # Display the initial message if this is the first run, otherwise immediately generate a response without user input
        if not self.chat_session.get_whether_previous_session_found():
            self.chat_session.inject_message(self.initial_response, role=Role.assistant, off_switch=True)  # Inject the initial response into the chat session
            self.executor.submit(
                self.response_thread,
                self.initial_response,
                off_switch=True
            )
        else:
            self.executor.submit(
                self.send_thread,
                None
            )

        self.executor.submit(
            self.exit_event_listener_thread
        )

        # Start the main event loop
        self.view.mainloop()

    def exit_event_listener_thread(self):
        try:
            self.exit_by_assistant_event.wait()
            if not self.exiting:
                self.exiting = True
                self.closed_by = Role.assistant
                print("Narration finished, exiting application.")
                self.on_exit()
        except Exception as e:
            print("An error occurred while responding to the exit event")
            traceback.print_exc()
            raise e
        
    def on_exit_button_action(self) -> None:
        print("Exit button clicked!")
        if not self.exiting:
            self.exiting = True
            self.closed_by = Role.user
            self.executor.submit(self.on_exit)

    def on_send_action(self, event: Event) -> None:
        print("Send button clicked!")
        # Get the user input from the text input field
        user_input = self.view.drain_text()
        self.cancel_response_token["value"] = True # Interrupt the AI dialogue
        self.executor.submit(self.send_thread, user_input)

    def send_thread(self, user_input: str = None):
        try:
            # Get the AI response
            (response, off_switch) = self.chat_session.call_llm_for_chat(user_input, enable_printing=True)
            self.view.clear_output()  # Clear the output window before displaying the new response
            
            # Display the response in the chat view and play the audio
            self.response_thread(response, off_switch)

            # Check how long the current chat history is and if it exceeds the limit, summarize the chat history
            if not self.exit_by_assistant_event.is_set():
                # Save chat history after each message
                Logger.log(f"Saving chat session", Level.INFO)
                self.chat_session.save_session()
                current_chat_length = self.chat_session.get_current_chat_history_length()
                if current_chat_length > self.max_chat_history_length:
                    Logger.log(f"Chat history length exceeded {self.max_chat_history_length}. Summarizing chat history.", Level.INFO)
                    self.chat_session.summarize_message_history(include_cot=True, num_last_messages_to_retain=4, enable_printing=True)
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
                self.response_finished_event,
                self.cancel_response_token,
                speed=self.text_stream_speed,
                delay_before_closing=self.delay_before_closing_by_ai
            )

            if off_switch:
                self.exit_by_assistant_event.set()
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
            self.exit_by_assistant_event.set()

            # Add the closing message to the chat session and save the message history
            if self.closed_by is not None:
                self.chat_session.inject_message(f"Application was closed by the {self.closed_by.value}.", role=self.closed_by)
            else:
                self.chat_session.inject_message("Application crashed unexpectedly.", role=Role.system)
            self.chat_session.save_session()

            # Wait for all threads to close properly
            self.response_finished_event.wait() 

            # sa.stop_all()
            
            # Close the view
            self.view.quit()
        except Exception as e:
            print("An error occurred while exiting the application")
            traceback.print_exc()
            raise e