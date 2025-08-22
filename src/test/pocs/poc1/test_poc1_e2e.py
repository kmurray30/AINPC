import os
import sys
import time
from pathlib import Path
from dataclasses import asdict
from typing import Any, List, Dict

import pytest

from src.core.schemas.Schemas import GameSettings

# Ensure src/ on sys.path
PROJ_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJ_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.core.ChatMessage import ChatMessage
from src.poc import bootstrap, proj_settings
from src.poc import proj_paths
from src.poc.poc1.presenter import Presenter
from src.core.Constants import Role
from src.core.ResponseTypes import ChatResponse, ChatSummary
from src.utils import io_utils, llm_utils


class FakeView:
    def __init__(self, scripted_inputs: List[str] | None = None) -> None:
        self._inputs = scripted_inputs or []
        self._display_calls: List[Any] = []
        self._quit_called = False
        self._protocols = {}

    def create_ui(self, presenter: Presenter) -> None:
        self.presenter = presenter

    def protocol(self, name: str, func):
        self._protocols[name] = func

    def drain_text(self) -> str:
        return self._inputs.pop(0) if self._inputs else ""

    def clear_output(self) -> None:
        pass

    def display_chat_message(self, text: str, completion_event, cancel_token, speed=0.05, delay_before_closing=0) -> None:
        # Simulate immediate display completion
        self._display_calls.append(text)
        if hasattr(completion_event, 'set'):
            completion_event.set()

    def mainloop(self) -> None:
        # No blocking loop in tests
        pass

    def quit(self) -> None:
        self._quit_called = True


@pytest.fixture
def test_project():
    """Use in-repo test project at src/test/pocs/poc1 and let proj_paths generate all IO paths."""
    base = SRC_DIR / "test/pocs/poc1"
    # Ensure expected files exist (user requested these be under repo)
    assert (base / "game_settings.yaml").exists(), f"Missing {(base / 'game_settings.yaml')}"
    assert (base / "templates/npcs/companion/template.yaml").exists(), f"Missing template at {(base / 'templates/npcs/companion/template.yaml')}"
    (base / "saves").mkdir(parents=True, exist_ok=True)
    return base


# Identifiers for validation
first_response = "I'm closing this."
second_response = "Alright, staying open."
chat_summary_identifier = "chatsummaryidentifier"


class ChatBotMock:
    last_input_messages: List[Dict[str, str]] = []

    def __init__(self):
        self.calls: List[Any] = []
        self.response_counter = 0

    def __call__(self, messages, response_type):
        print(f"ChatBotMock called: type={getattr(response_type,'__name__',response_type)} msgs={len(messages)}")
        # Keep call record for assertions
        self.calls.append({"messages": messages, "response_type": response_type})

        if response_type is ChatResponse:
            self.last_input_messages = messages
            self.response_counter += 1
            if self.response_counter == 1:
                # First ChatBot response: rude and close
                print("ChatBotMock: returning off_switch=True")
                return ChatResponse(hidden_thought_process="rude", response=first_response, off_switch=True)
            # Subsequent: keep open
            print("ChatBotMock: returning off_switch=False")
            return ChatResponse(hidden_thought_process="ok", response=second_response, off_switch=False)
        elif response_type is ChatSummary:
            print("ChatBotMock: returning ChatSummary")
            return ChatSummary(
                conversation_overview=chat_summary_identifier,
                hidden_thought_processes="hidden",
                chronology="steps",
                standout_quotes="none",
                most_recent="recent",
            )
        else:
            raise AssertionError("Unexpected response_type")

presenters = []

def test_poc1_e2e_flow(test_project: Path, monkeypatch):
    print("[E2E] Starting test_poc1_e2e_flow")
    # Patch ChatBot and audio to no-op
    from src.utils.ChatBot import ChatBot as ChatBotModule
    cb_mock = ChatBotMock()
    monkeypatch.setattr(ChatBotModule, "call_llm", cb_mock)

    # No-op audio
    from src.poc.poc1 import presenter as presenter_mod
    # No-op audio thread and play
    monkeypatch.setattr(presenter_mod.Presenter, "audio_thread", lambda self, text, cancel_token, audio_generated_event, audio_finished_event, delay=0, voice="fable": audio_generated_event.set())
    monkeypatch.setattr(presenter_mod.Presenter, "play_audio", lambda self, *a, **k: None)
    from src.utils import TextToSpeech
    monkeypatch.setattr(TextToSpeech, "generate_speech_file", lambda *a, **k: None)

    # Initialize app pointing at test project
    save_name = "e2e_save"
    bootstrap.init_app(save_name=save_name, project_path=test_project)

    # Helper to fetch save paths
    paths = proj_paths.get_paths()
    game_settings: GameSettings = proj_settings.get_settings().game_settings
    npc_name = paths.get_npc_names[0]

    # Serialize YAML appends across presenters to avoid interleaving writes
    # import threading
    # from src.utils import io_utils as io_mod
    # real_append = io_mod.append_to_yaml_file
    # lock = threading.Lock()
    # def locked_append(data, file_path):
    #     with lock:
    #         return real_append(data, file_path)
    # monkeypatch.setattr(io_mod, 'append_to_yaml_file', locked_append)

    # 1) First run: initial ChatBot call should close app (empty initial_response, so closing from mock chatbot call)
    view1 = FakeView()
    presenter1 = Presenter(view1, force_new_game=True)
    print("[E2E] Starting presenter1.run()")
    presenter1.run()
    presenters.append(presenter1)

    # Wait for close path to execute
    presenter1.exit_by_assistant_event.wait(timeout=3)
    # Poll for view.quit to be called (on_exit completes asynchronously)
    for _ in range(30):
        if view1._quit_called:
            break
        time.sleep(0.05)
    assert view1._quit_called, "View should be closed on first rude response"

    # Validate first ChatBot call payload contains system prompt
    first_call = next(c for c in cb_mock.calls if c["response_type"] is ChatResponse)
    msgs = first_call["messages"]
    assert msgs[0]["role"] == "system"
    assert "You are an ornery, rude" in msgs[0]["content"]
    assert "Format your response as a JSON" in msgs[0]["content"]

    # Small delay to ensure final write completes
    time.sleep(0.2)

    # Validate IO artifacts
    chat_log_path = paths.chat_log(npc_name)
    npc_state_path = paths.npc_save_state(npc_name)
    print(f"[E2E] chat_log_path={chat_log_path} exists={chat_log_path.exists()}\n[E2E] npc_state_path={npc_state_path} exists={npc_state_path.exists()}")
    assert chat_log_path.exists()
    assert npc_state_path.exists()

    from typing import List as TList, Dict as TDict, Any as TAny
    logs = io_utils.load_yaml_into_dataclass(chat_log_path, TList[TDict[str, TAny]])
    print(f"[E2E] logs loaded")
    assert any(entry["role"] == Role.system.name for entry in logs)
    assert any(entry["role"] == Role.assistant.name for entry in logs)

    state = io_utils.load_yaml_into_dataclass(npc_state_path, TDict[str, TAny])
    print(f"[E2E] state loaded")
    assert "conversation_memory" in state

    # 2) Reopen: should keep app open now; send something nice
    view2 = FakeView(scripted_inputs=["You're great!"])
    presenter2 = Presenter(view2)
    presenters.append(presenter2)
    # Reset shared event to allow maintenance
    import threading
    presenter2.exit_by_assistant_event = threading.Event()

    # Serialize YAML appends to avoid interleaving writes during multi-threaded presenter actions
    # from src.utils import io_utils as io_mod
    # real_append = io_mod.append_to_yaml_file
    # lock = threading.Lock()
    # print(f"[E2E] locking")
    # def locked_append(data, file_path):
    #     with lock:
    #         return real_append(data, file_path)
    # monkeypatch.setattr(io_mod, 'append_to_yaml_file', locked_append)
    presenter2.run()

    # Allow time for initial send_thread(None) and then user send
    # Kick a send
    print("[E2E] Trigger on_send_action #1")
    presenter2.on_send_action(None)

    # Wait for display events
    time.sleep(0.3)

    # There should be at least two more ChatBot calls now (one for chat, one possibly for summary)
    assert len(cb_mock.calls) >= 2

    # Validate system prompt and history presence again on the latest Chat call
    last_chat_call = [c for c in cb_mock.calls if c["response_type"] is ChatResponse][-1]
    msgs2 = last_chat_call["messages"]
    assert msgs2[0]["role"] == "system"
    assert "You are an ornery, rude" in msgs2[0]["content"]

    # Trigger summarization by sending enough messages to exceed memory
    for i in range(3):
        print(f"[E2E] Trigger on_send_action extra {i+1}")
        presenter2.on_send_action(None)
        time.sleep(0.2)

    # Ensure a summary call occurred
    # allow a small grace window for background thread
    for _ in range(40):
        if any(c["response_type"] is ChatSummary for c in cb_mock.calls):
            break
        time.sleep(0.05)
    assert any(c["response_type"] is ChatSummary for c in cb_mock.calls)

    # Validate the npc object contains the summary
    assert presenter2.npc.conversation_memory.get_chat_summary_as_string() is not None

    # Validate chat log appended over time
    logs2 = io_utils.load_yaml_into_dataclass(chat_log_path, List[ChatMessage])
    assert len(logs2) >= len(logs)

    # Validate the last input message contains everything expected: system prompt, summary, formatting, and truncated message history
    print(f"[E2E] last_input_messages={cb_mock.last_input_messages}")
    assert cb_mock.last_input_messages[0]["role"] == "system"
    # Assert the system prompt is present
    assert "You are an ornery, rude" in cb_mock.last_input_messages[0]["content"]
    # Assert the summary identifier is present
    assert chat_summary_identifier in cb_mock.last_input_messages[0]["content"]
    # Assert the formatting commands are present
    assert llm_utils.prompt_formatting_message_prefix in cb_mock.last_input_messages[0]["content"]
    # Assert the message count was truncated by the summary process
    message_count_lower_bound = game_settings.num_last_messages_to_retain_when_summarizing 
    message_count_upper_bound = game_settings.max_convo_mem_length
    assert len(cb_mock.last_input_messages) - 1 >= message_count_lower_bound and len(cb_mock.last_input_messages) - 1 <= message_count_upper_bound

    # Validate closing message present in logs from first run
    assert any(entry.content.startswith("Application was closed by the assistant.") for entry in logs2 if isinstance(entry, ChatMessage))

@pytest.fixture(autouse=True)
def always_teardown():
    yield
    print("[E2E] Teardown")
    for p in presenters:
        p.on_exit() # Ensure all presenters exit and close any open threads