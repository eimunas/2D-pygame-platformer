"""Entry point.

Controls:
    A / D          walk left / right
    Shift + A / D  run
    Esc            quit
"""

from src.game import Game


if __name__ == "__main__":
    Game().run()
