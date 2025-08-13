from typing import Protocol
from src.poc.presenter_base import PresenterBase
from src.core.Schemas import GameSettings

class View(Protocol):
    def mainloop(self) -> None:
        ...

class Presenter(PresenterBase):
    save_path_prefix: str = "src/poc/poc1/saves"

    def __init__(self, view: View) -> None:
        super().__init__(view, self.save_path_prefix)