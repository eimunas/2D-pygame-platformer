"""Entry point.

Controls:
    A / D          walk left / right
    Shift + A / D  run
    W / Space      jump (press again in the air: double jump)
    Left click     katana combo,  right click: dash attack
    Esc            back to the main menu (in the menu: quit)
"""

from src.game import Game


if __name__ == "__main__":
    Game(menu=True).run()
