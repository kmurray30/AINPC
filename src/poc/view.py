import time
import tkinter as tk
from typing import Protocol, Callable
from threading import Event

class Presenter(Protocol):
    ...

# Make View a subclass of Tkinter's Tk class
class View(tk.Tk):
    
    # Define the widgets for global access
    output_text_window: tk.Text
    input_text_window: tk.Entry

    # Presenter functions needed for toggling the send button
    send_function: Callable[[], None]

    # Initialize the view
    def __init__(self) -> None:

        # Initialize the parent class
        super().__init__()

        # Root config
        self.title("Companion-1_Decommissioned")

        # Create chat frame
        self.output_text_window = tk.Text(self, height=10, width=50)
        self.output_text_window.pack()

        # Create input frame
        self.input_text_window = tk.Entry(self)
        self.input_text_window.pack()

        # Set chat window settings
        # self.output_text_window.config(state=DISABLED) # Disable the chat window for typing

    # Set up the UI with the presenter bindings
    def create_ui(self, presenter: Presenter) -> None:
        self.send_function = presenter.on_send
        self.input_text_window.bind("<Return>", self.send_function)

    # Start the main event loop
    def mainloop(self) -> None:
        # Call mainloop of the parent class TK
        super().mainloop()

    def drain_text(self) -> str:
        user_prompt = "" + self.input_text_window.get() # Get the user input from the input field
        if user_prompt == "":
            return # Skip if the input is empty
        self.input_text_window.delete(0, tk.END) # Clear the input field
        return user_prompt

    def stream_text(self, text_widget: tk.Text, text: str, off_switch: bool, completion_event: Event, exit_event: Event, cancel_token: dict, speed=0.05, delay_before_closing=1.0):
        cancel_token["value"] = False  # Reset the cancel token for this thread, so it can only be turned on outside this thread
        off_switch = False # DEBUG
        spaces_for_delay = int(delay_before_closing // speed)
        text += " " * spaces_for_delay  # Add spaces to the end of the text for delay
        for c in text:
            if cancel_token["value"]:
                cancel_token["value"] = False  # Reset the cancel token
                return
            text_widget.insert(tk.END, c)
            text_widget.see(tk.END)
            time.sleep(speed)
        if off_switch:
            exit_event.set()

    def clear_output(self):
        self.output_text_window.delete("1.0", tk.END)

    def display_chat_message(self, text: str, off_switch: bool, completion_event: Event, exit_event: Event, cancel_token: dict, speed=0.05) -> None:
        self.stream_text(self.output_text_window, text, off_switch, completion_event, exit_event, cancel_token, speed=speed)
        completion_event.set()
