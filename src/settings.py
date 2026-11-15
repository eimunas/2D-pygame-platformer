"""Global game settings and paths."""

import os

# ---------------------------------------------------------------- window
TITLE = "Ninja - animation test"
SCREEN_W, SCREEN_H = 960, 540
FPS = 60

# ---------------------------------------------------------------- world
SCALE = 4                      # 16x16 sprites -> 64x64 on screen
TILE_SIZE = 16 * SCALE         # one tile on screen, in pixels
TREE_ANIM_FPS = 5              # gentle sway

# ---------------------------------------------------------------- player
WALK_SPEED = 120               # pixels per second
RUN_SPEED = 260
PLAYER_ANIM_FPS = {"idle": 6, "walk": 12, "run": 20}

# ---------------------------------------------------------------- paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
