from typing import Protocol
from src.poc.PresenterBase import PresenterBase
from src.poc.Settings import Settings

class View(Protocol):
    def mainloop(self) -> None:
        ...

class Presenter(PresenterBase):

    def __init__(self, view: View, settings: Settings) -> None:
        super().__init__(view, settings)