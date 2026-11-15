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
PLAYER_ANIM_FPS = {
    "idle": 6, "walk": 12, "run": 20, "jump": 10, "fall": 10, "flip": 24,
    "attack1": 20, "attack2": 20, "attack3": 16, "dash": 14,
}
PLAYER_ANIM_ONCE = ("flip", "attack1", "attack2", "attack3", "dash")   # play once, don't loop

# ---------------------------------------------------------------- combat
# Left-click combo: each click plays the next attack in this list, then wraps.
#   lunge: forward speed (px/s) at the start of the swing, fading quickly
#   shake: (strength px, duration s) of the screen shake
PLAYER_ATTACKS = [
    {"anim": "attack1", "lunge": 240, "shake": (3, 0.12)},   # horizontal cut
    {"anim": "attack2", "lunge": 240, "shake": (3, 0.12)},   # rising cut
    {"anim": "attack3", "lunge": 380, "shake": (6, 0.22)},   # heavy overhead finisher
]
ATTACK_LUNGE_DECAY = 10        # how fast the lunge slows down (higher = shorter step)
ATTACK_QUEUE_FROM_FRAME = 2    # clicks from this frame on queue the next attack
COMBO_WINDOW = 0.4             # seconds after an attack ends to continue the combo
ATTACK_ACTIVE_FRAMES = (2, 3)  # frames where the blade can hit (for enemies later)

# Right-click dash attack
DASH_SPEED = 950               # px/s during the dash
DASH_TIME = 0.17               # seconds of dashing (~2.5 tiles)
DASH_RECOVERY_SPEED = 180      # forward drift right after the dash, fading out
DASH_COOLDOWN = 0.55           # seconds before the next dash
DASH_SHAKE = (4, 0.15)
GHOST_INTERVAL = 0.02          # seconds between afterimages
GHOST_LIFETIME = 0.22
GHOST_ALPHA = 150
GHOST_COLOR = (214, 52, 64)    # crimson, matches the headband
STREAK_LIFETIME = 0.25
PLAYER_HITBOX = (7 * SCALE, 14 * SCALE)   # the ninja's body inside his 16x16 image

# ---------------------------------------------------------------- background
# (file inside assets/, (x, y) scroll speed vs. the camera), farthest first.
# 0 = fixed to the screen, 1 = moves with the tiles.
BACKGROUND_LAYERS = [
    ("background/sky.png", (0.0, 0.0)),
    ("background/mountains.png", (0.08, 0.1)),
    ("background/forest_far.png", (0.2, 0.25)),
    ("background/forest_mid.png", (0.4, 0.4)),
    ("background/forest_near.png", (0.65, 0.6)),
]

# ---------------------------------------------------------------- physics
GRAVITY = 2200                 # pixels / second^2
MAX_FALL_SPEED = 1000          # pixels / second (keeps fast falls from skipping tiles)
JUMP_SPEED = 860               # initial upward speed -> ~2.5 tiles high
AIR_JUMPS = 1                  # extra jumps in mid-air (1 = double jump)
DOUBLE_JUMP_SPEED = 760        # a bit weaker than the ground jump
JUMP_CUT = 0.45                # releasing jump early multiplies upward speed by this
COYOTE_TIME = 0.1              # seconds you can still jump after leaving a ledge
JUMP_BUFFER_TIME = 0.1         # seconds a jump press is remembered before landing
MAX_DT = 1 / 20                # cap a frame's dt (e.g. after dragging the window)

# ---------------------------------------------------------------- camera
CAMERA_SMOOTHING = 5.0         # higher = camera catches up faster
CAMERA_LOOK_AHEAD = 96         # pixels shown ahead of the player's facing direction
CAMERA_OFFSET = (0, -48)       # shift from centre; negative y shows more sky

# ---------------------------------------------------------------- paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
