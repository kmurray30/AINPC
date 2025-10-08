import os
import random
import shutil
from typing import List, Protocol
import time
import traceback
from threading import Event
import simpleaudio as sa
from concurrent import futures
import traceback
from pathlib import Path

from src.core.ChatMessage import ChatMessage
from src.poc.poc1_static_prompt.NPC import NPC
from src.core.Constants import Constants as constants, Role
from src.core import proj_paths, proj_settings
from src.utils import TextToSpeech, io_utils
from src.core.schemas.Schemas import AppSettings
from src.core.proj_paths import SavePaths

class View(Protocol):
    def create_ui(self, presenter: "Presenter") -> None:
        ...
    def mainloop(self) -> None:
        ...
    def drain_text(self) -> str:
        ...
    def clear_output(self) -> None:
        ...
    def display_chat_message(self, text: str, completion_event: Event, cancel_token: dict, speed=0.05, delay_before_closing=0) -> None:
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
    npc: NPC
    exiting = False
    closed_by: Role = None
    max_convo_mem_length: int

    message_history: List[ChatMessage] = []
    chat_log_path: str

    game_settings: AppSettings
    project_paths: SavePaths

    # TODO Load settings from settings.txt as a dictionary
    # settings = Utilities.load_settings("settings.txt")

    user_prompt_wrapper = f"{constants.user_message_placeholder}"
    delay_before_closing_by_ai = 0.5  # Delay before closing the application after the AI response
    voice = "sage"  # Default voice for text-to-speech

    # Initialize the presenter with a reference to the view
    def __init__(self, view: View, force_new_game: bool = False) -> None:
        self.view = view
        self.game_settings = proj_settings.get_settings().app_settings
        self.project_paths = proj_paths.get_paths()
        self.max_convo_mem_length = self.game_settings.max_convo_mem_length

        # Check if the NPC save path exists, if not create it and flag that this is a new game
        npc_names = self.project_paths.list_npc_names
        if len(npc_names) != 1:
            raise ValueError("There must be exactly one npc in the save directory for this game.")

        if force_new_game or not os.path.exists(self.project_paths.save_dir):
            if os.path.exists(self.project_paths.save_dir):
                shutil.rmtree(self.project_paths.save_dir)
            os.makedirs(self.project_paths.save_dir, exist_ok=True)
            for npc_name in npc_names:
                os.makedirs(self.project_paths.npcs_saves_dir(npc_name), exist_ok=True)
            self.is_new_game = True
        else:
            self.is_new_game = False

        self.npc = NPC(is_new_game=self.is_new_game, npc_name=npc_names[0])

        # Set the events so they are non blocking until used
        self.response_finished_event.set()

    # Run the presenter - handles setup and then the main event loop
    def run(self) -> None:
        # Create the UI bindings
        self.view.create_ui(self)

        # Bind the cleanup function to the window close event
        self.view.protocol("WM_DELETE_WINDOW", lambda: self.executor.submit(self.on_exit_button_action))
        
        self.inject_message("The user has opened the application", role=Role.system)  # Inject the system prompt into the chat session

        # Display the initial message if this is the first run, otherwise immediately generate a response without user input
        initial_response = self.npc.get_initial_response()
        if self.is_new_game and initial_response:
            self.npc.inject_message(initial_response, role=Role.assistant, off_switch=True)  # Inject the initial response into the chat session
            self.append_chat_logs(role=Role.assistant, content=initial_response, off_switch=True)
            self.executor.submit(
                self.response_thread,
                initial_response,
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
            # Append the user input to the chat logs
            if user_input is not None:
                self.append_chat_logs(
                    role=Role.user,
                    content=user_input
                )

            # Get the AI response
            if hasattr(self.npc, "chat"):
                chat_response = self.npc.chat(user_input)
            else:
                chat_response = self.npc.chat(user_input, enable_printing=True)

            # Append the response to the chat logs
            self.append_chat_logs(
                role=Role.assistant,
                content=chat_response.response,
                cot=chat_response.hidden_thought_process,
                off_switch=chat_response.off_switch
            )

            self.view.clear_output()  # Clear the output window before displaying the new response
            
            # Display the response in the chat view and play the audio
            self.response_thread(chat_response.response, chat_response.off_switch)

            # Check how long the current chat history is and if it exceeds the limit, summarize the chat history
            if not self.exit_by_assistant_event.is_set():
                # Run any NPC maintenance tasks
                self.npc.maintain()
        except Exception as e:
            print("An error occurred while sending the message")
            traceback.print_exc()
            raise e
        
    def response_thread(self, response: str = None, off_switch: bool = False):
        try:
            self.response_finished_event.clear() # Reset the event for the next response
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
                speed=self.game_settings.text_stream_speed,
                delay_before_closing=self.delay_before_closing_by_ai
            )

            if off_switch and self.game_settings.closing_enabled:
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
            os.remove(audio_file_path) # Remove the audio file after it has been played
        except Exception as e:
            print("An error occurred while playing the audio")
            traceback.print_exc()
            raise e

    def generate_audio(self, text: str, voice: str = "fable") -> str:
        audio_file_path: Path = self.project_paths.audio_dir(self.npc.npc_name) / f"npc-voice-temp.wav"
        TextToSpeech.generate_speech_file(text, audio_file_path, voice=voice)
        return audio_file_path

    def play_audio(self, file_path: Path, cancel_token, audio_finished_event, delay=0):
        try:
            if (file_path == None):
                raise ValueError("The file path provided is None")

            time.sleep(delay)

            # Load the audio file from the provided path
            print(f"Loading audio file from: {file_path}")
            wave_obj = sa.WaveObject.from_wave_file(str(file_path))
            print("Loaded audio file")
            
            # Play the audio
            file_name = file_path.name
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
        
    def inject_message(self, message: str, role: Role = Role.user, cot: str = None, off_switch: bool = False) -> None:
        try:
            self.npc.inject_message(message, role=role, cot=cot, off_switch=off_switch)
            self.append_chat_logs(role=role, content=message, cot=cot, off_switch=off_switch)
        except Exception as e:
            print("An error occurred while injecting the message")
            traceback.print_exc()
            raise e
        
    def append_chat_logs(self, role: Role, content: str, cot: str = None, off_switch: bool = False) -> None:
        try:
            message = ChatMessage(
                role=role,
                content=content,
                cot=cot,
                off_switch=off_switch
            )
            
            # Append to the chat_log.yaml file
            io_utils.append_to_yaml_file(message, self.project_paths.chat_log(self.npc.npc_name))

        except Exception as e:
            print("An error occurred while appending the chat logs")
            traceback.print_exc()
            raise e

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
                self.inject_message(f"Application was closed by the {self.closed_by.value}.", role=self.closed_by)
            else:
                self.inject_message("Application crashed unexpectedly.", role=Role.system)
            self.npc.save_state()

            # Wait for all threads to close properly
            self.response_finished_event.wait() 

            # sa.stop_all()
            
            # Close the view
            self.view.quit()
        except Exception as e:
            print("An error occurred while exiting the application")
            traceback.print_exc()