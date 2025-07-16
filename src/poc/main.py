from view import View
from presenter import Presenter

def main() -> None:
    # model = Model()
    view = View()
    presenter = Presenter(view)
    presenter.run()

if __name__ == "__main__":
    main()