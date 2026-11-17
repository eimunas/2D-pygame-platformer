"""Global game settings and paths."""

import os

# ---------------------------------------------------------------- window
TITLE = "Ninja - animation test"
SCREEN_W, SCREEN_H = 960, 540
FPS = 60

# ---------------------------------------------------------------- main menu
MENU_TITLE = "NINJA"
MENU_SUBTITLE = "- select a stage -"
MENU_MUSIC = "main_menu"       # assets/audio/main_menu.mp3, loops in the menu
MENU_SCROLL_SPEED = 40         # px/s the forest background drifts behind the menu

# ---------------------------------------------------------------- stages
STAGE_TITLE_TIME = 3.0         # seconds the "Stage N - name" title shows at a level start
STAGE_CLEAR_TIME = 2.0         # seconds the "Stage clear!" message shows before the next level

# ---------------------------------------------------------------- intro cutscene
PLAY_INTRO = True              # show the intro before gameplay (Enter skips it)
INTRO_HOLD_TIME = 1.1          # seconds the camera rests on each group of enemies
INTRO_PAN_SPEED = 900          # px/s camera glide speed between stops
INTRO_MIN_PAN_TIME = 0.8       # even short glides take at least this long
INTRO_GROUP_SPAN = 10 * 16 * 4 # enemies within this many px share one camera stop
INTRO_LOOK_OFFSET_Y = -48      # same framing as the gameplay camera
INTRO_BAR_HEIGHT = 56          # cinematic letterbox bars
INTRO_SOUND = "intro_scene_sound"   # assets/audio/intro_scene_sound.mp3
INTRO_SOUND_FADE_MS = 600      # fade-out when the intro ends or is skipped
INTRO_FIT_TO_SOUND = True      # stretch/shrink the scene to last exactly as long as the sound
INTRO_MIN_HOLD_TIME = 0.3      # when fitting: never hold on a stop shorter than this
INTRO_MIN_FIT_PAN_TIME = 0.4   # when fitting a very short sound: shortest glide

# ---------------------------------------------------------------- world
SCALE = 4                      # 16x16 sprites -> 64x64 on screen
TILE_SIZE = 16 * SCALE         # one tile on screen, in pixels
TREE_ANIM_FPS = 5              # gentle sway

# ---------------------------------------------------------------- player
WALK_SPEED = 120               # pixels per second
RUN_SPEED = 260
PLAYER_ANIM_FPS = {
    "idle": 6, "walk": 12, "run": 20, "jump": 10, "fall": 10, "flip": 24,
    "attack1": 20, "attack2": 20, "attack3": 16, "dash": 14, "death": 5, "bow": 16,
}
PLAYER_ANIM_ONCE = ("flip", "attack1", "attack2", "attack3", "dash", "death", "bow")   # play once, don't loop

# ---------------------------------------------------------------- combat
# Left-click combo: each click plays the next attack in this list, then wraps.
#   lunge: forward speed (px/s) at the start of the swing, fading quickly
#   shake: (strength px, duration s) of the screen shake
#   damage: health removed from an enemy (each swing hits an enemy at most once)
PLAYER_ATTACKS = [
    {"anim": "attack1", "lunge": 240, "shake": (3, 0.12), "damage": 1},   # horizontal cut
    {"anim": "attack2", "lunge": 240, "shake": (3, 0.12), "damage": 1},   # rising cut
    {"anim": "attack3", "lunge": 380, "shake": (6, 0.22), "damage": 2},   # heavy finisher
]
DASH_DAMAGE = 2
ATTACK_LUNGE_DECAY = 10        # how fast the lunge slows down (higher = shorter step)
ATTACK_QUEUE_FROM_FRAME = 2    # clicks from this frame on queue the next attack
COMBO_WINDOW = 0.4             # seconds after an attack ends to continue the combo
ATTACK_ACTIVE_FRAMES = (2, 3)  # frames where the blade can hit (for enemies later)

# Right-click dash attack
DASH_SPEED = 950               # px/s during the dash
DASH_TIME = 0.17               # seconds of dashing (~2.5 tiles)
DASH_RECOVERY_SPEED = 180      # forward drift right after the dash, fading out
DASH_COOLDOWN = 3           # seconds before the next dash
DASH_SHAKE = (4, 0.15)
GHOST_INTERVAL = 0.02          # seconds between afterimages
GHOST_LIFETIME = 0.22
GHOST_ALPHA = 150
GHOST_COLOR = (214, 52, 64)    # crimson, matches the headband
STREAK_LIFETIME = 0.25
PLAYER_HITBOX = (7 * SCALE, 14 * SCALE)   # the ninja's body inside his 16x16 image

# ---------------------------------------------------------------- player health
PLAYER_MAX_HEALTH = 5
PLAYER_INVULN_TIME = 1.0       # seconds of blinking invulnerability after a hit
PLAYER_HURT_TIME = 0.25        # seconds without control while knocked back
PLAYER_KNOCKBACK = (320, 420)  # (sideways, upwards) speed when hit
HURT_SHAKE = (5, 0.2)

# ---------------------------------------------------------------- defeat
# At 0 health the ninja bleeds and slowly collapses (death animation, played at
# PLAYER_ANIM_FPS["death"]), then the defeat message shows; Enter restarts stage 1.
DEATH_SHAKE = (8, 0.35)
DEATH_SOUND = "player_blood_splash"   # the killing blow (instead of hit_hurt)
DEFEAT_SOUND = "defeat_sound"         # plays once, right after the blood splash
DEFEAT_SOUND_FADE_MS = 1000           # fade-out if Enter restarts before it ends
DEATH_KNOCKBACK = 150          # px/s he staggers back from the killing blow (slows down)
DEFEAT_MESSAGE_DELAY = 0.9     # seconds after he hits the ground before the message shows
DEFEAT_FADE_TIME = 2.5         # seconds for the screen to darken (from the moment he dies)
DEFEAT_DARKEN = 150            # final darkness of the overlay (0..255)
BLOOD_COLOR = (150, 18, 24)
BLOOD_COLOR_HI = (206, 40, 40)
BLOOD_SPRAY = 14               # droplets sprayed by the killing blow
BLOOD_DRIP_INTERVAL = 0.12     # seconds between drips while he collapses
BLOOD_POOL_WIDTH = 13          # art pixels wide when fully spread
BLOOD_POOL_TIME = 3.0          # seconds for the pool to spread

# ---------------------------------------------------------------- enemy: samurai
SAMURAI_ANIM_FPS = {"idle": 6, "walk": 10, "run": 18, "attack": 14}
SAMURAI_HITBOX = PLAYER_HITBOX
SAMURAI_WALK_SPEED = 60
SAMURAI_RUN_SPEED = 210                    # a bit slower than the ninja's run
SAMURAI_JUMP_SPEED = 760                   # used to hop up 1-tile steps while chasing
SAMURAI_MAX_STEP_DOWN = 2                  # tiles he'll drop down while chasing (deeper = jump or stop)
SAMURAI_LEAP_SPEED = 820                   # jumps over pits while chasing (archers too, when backing off)
SAMURAI_LEAP_RUN_SPEED = 320               # forward speed during that jump (clears 3-tile pits)
ENEMY_MAX_LEAP_TILES = 4                   # how far past a pit's edge enemies look for ground to land on
SAMURAI_SIGHT_RANGE = 6 * TILE_SIZE        # how far ahead he can spot the ninja
SAMURAI_SIGHT_HEIGHT = 2 * TILE_SIZE       # max height difference to notice him
SAMURAI_LOSE_RANGE = 10 * TILE_SIZE        # beyond this (for a while) he gives up
SAMURAI_LOSE_TIME = 2.0
SAMURAI_ALERT_TIME = 0.3                   # pause after spotting, before charging
SAMURAI_SPOT_SHAKE = (3, 0.2)
SAMURAI_ATTACK_RANGE = 20                  # gap (px) between bodies to start a slash
# (must be < blade reach: 12 art px from his centre)
SAMURAI_ATTACK_ACTIVE_FRAMES = (2, 3)      # frames where his blade hurts
SAMURAI_ATTACK_COOLDOWN = 0.7
SAMURAI_DAMAGE = 1
SAMURAI_PATROL_WALK_TIME = (1.5, 4.0)      # random range, seconds
SAMURAI_PATROL_IDLE_TIME = (1.0, 2.5)
SAMURAI_MAX_HEALTH = 10
SAMURAI_HURT_TIME = 0.3                    # stagger after being hit (his attack is cancelled)
SAMURAI_KNOCKBACK = (240, 220)             # (sideways, upwards) speed when hit
ENEMY_SPOT_ONLY_IN_FRONT = False           # True = enemies only notice a ninja they're facing
ENEMY_HIT_SHAKE = (3, 0.1)
ENEMY_DEATH_SHAKE = (6, 0.22)
HIT_FLASH_TIME = 0.1                       # seconds an enemy flashes white when hit

# ---------------------------------------------------------------- enemy: samurai archer
ARCHER_ANIM_FPS = {"idle": 6, "walk": 10, "shoot": 9}
ARCHER_MAX_HEALTH = 3
ARCHER_SIGHT_RANGE = 11 * TILE_SIZE        # spots the ninja from far away...
ARCHER_SIGHT_HEIGHT = 4 * TILE_SIZE        # ...and from higher/lower ground
ARCHER_LOSE_RANGE = 14 * TILE_SIZE
ARCHER_KEEP_DISTANCE = 3 * TILE_SIZE       # backs away if the ninja gets closer than this
ARCHER_RETREAT_TIME = 0.8                  # max seconds per backing-off move
ARCHER_SHOOT_COOLDOWN = 1.6                # seconds between shots
ARCHER_FIRST_SHOT_DELAY = 0.5              # after spotting, before the first shot
ARCHER_RELEASE_FRAME = 4                   # shoot animation frame that looses the arrow
ARROW_SPEED_X = 470                        # horizontal arrow speed (px/s)
ARROW_GRAVITY = 900                        # pulls arrows into an arc
ARROW_MIN_FLIGHT = 0.45                    # seconds; keeps close shots arcing too
ARROW_DAMAGE = 1
ARROW_STUCK_TIME = 1.5                     # arrows stuck in the ground fade after this

# ---------------------------------------------------------------- enemy: shinobi
# An enemy ninja: quick, fragile-ish (between the archer and the samurai),
# stabs with a dagger up close and dashes into the ninja every few seconds.
SHINOBI_ANIM_FPS = {"idle": 6, "walk": 12, "run": 22, "attack": 18, "windup": 10, "dash": 16}
SHINOBI_MAX_HEALTH = 6                     # samurai 10, archer 3
SHINOBI_RUN_SPEED = 235                    # faster than the samurai, a bit slower than you
SHINOBI_SIGHT_RANGE = 8 * TILE_SIZE
SHINOBI_SIGHT_HEIGHT = 3 * TILE_SIZE
SHINOBI_ALERT_TIME = 0.15                  # reacts quickly
SHINOBI_ATTACK_RANGE = 10                  # gap (px) between bodies to start a stab
SHINOBI_ATTACK_ACTIVE_FRAMES = (2, 3)
SHINOBI_DAGGER_REACH = 9                   # art px from his centre the stab reaches
SHINOBI_DAMAGE = 1
SHINOBI_ATTACK_COOLDOWN = 0.35             # stabs come faster than katana cuts
SHINOBI_DASH_COOLDOWN = 3.0                # seconds between dashes
SHINOBI_FIRST_DASH_DELAY = 1.0             # after spotting you, before the first dash
SHINOBI_DASH_MIN_RANGE = 1 * TILE_SIZE     # gap needed to bother dashing...
SHINOBI_DASH_MAX_RANGE = 5 * TILE_SIZE     # ...and the furthest he dashes from
SHINOBI_WINDUP_TIME = 0.35                 # crouch before the dash: your warning to jump/dodge
SHINOBI_DASH_SPEED = 820                   # px/s
SHINOBI_DASH_TIME = 0.3                    # max seconds of dashing (~4 tiles)
SHINOBI_DASH_DAMAGE = 1
SHINOBI_DASH_RECOVER_TIME = 0.5            # stands still after a dash: your chance to hit back
SHINOBI_GHOST_COLOR = (132, 64, 168)       # purple afterimages
SHINOBI_JUMP_SPEED = 860                   # leaps over pits while chasing (same as your jump)
SHINOBI_LEAP_RUN_SPEED = 340               # forward speed during the leap

# ---------------------------------------------------------------- mini-boss: stone golem
# Guards the ancient caves (stage "Golem's Gate"). A rune seal (level char S) blocks
# the arena until every other enemy is defeated; walking past it plays the boss
# cutscene (the golem drops from the sky onto B) and the seal closes behind you.
GOLEM_ANIM_FPS = {"idle": 5, "walk": 8, "attack": 10, "crouch": 6, "air": 6, "land": 10}
GOLEM_HITBOX = (22 * SCALE, 42 * SCALE)
GOLEM_MAX_HEALTH = 50                      # katana 1-2, dash 2, arrow 2, bomb 5
GOLEM_WALK_SPEED = 70                      # slow...
GOLEM_ATTACK_RANGE = 1 * TILE_SIZE         # gap (px) between bodies to start a fist slam
GOLEM_ATTACK_ACTIVE_FRAMES = (3, 4)        # "attack" frames where the fists hurt
GOLEM_FIST_REACH = 28                      # art px in front of his centre the slam covers
GOLEM_FIST_DAMAGE = 2                      # ...but it hits hard (you have 5 HP)
GOLEM_ATTACK_COOLDOWN = 0.9
GOLEM_SLAM_SHAKE = (6, 0.25)               # fists hitting the ground
GOLEM_JUMP_COOLDOWN = 8.0                  # seconds between jump attacks
GOLEM_FIRST_JUMP_DELAY = 5.0               # after the fight starts
GOLEM_CROUCH_TIME = 0.5                    # gathers himself before jumping: your warning
GOLEM_JUMP_SPEED = 1250                    # take-off speed (px/s up) -> ~5.5 tiles high
GOLEM_JUMP_MAX_SPEED_X = 700               # how far he can travel during the jump
GOLEM_LANDING_DAMAGE = 3                   # caught under him or in the shockwave
GOLEM_SHOCKWAVE = 1.4 * TILE_SIZE          # reach of the shockwave past his body (on the ground)
GOLEM_LAND_SHAKE = (16, 0.6)
GOLEM_LAND_RECOVER = 1.0                   # stands still after landing: punish him!
GOLEM_STEP_SHAKE = (2, 0.12)               # every footstep
GOLEM_LEASH = 14 * TILE_SIZE               # never walks/jumps further than this from where he landed
GOLEM_DEATH_SHAKE = (18, 1.0)
GOLEM_NAME = "Stone Golem"
GOLEM_TITLE = "Guardian of the Ancient Caves"

BOSS_TRIGGER_DISTANCE = 1.5 * TILE_SIZE    # walk this far past the seal -> boss cutscene
BOSS_FIGHT_HEAL = True                     # the ninja starts the fight at full health
BOSS_MUSIC = "giant-boss-fight-bg-music"   # loops during the fight (after the cutscene)
BOSS_SPAWN_HEIGHT = 9 * TILE_SIZE          # the golem falls from this far above his landing spot
BOSS_FALL_SPEED = 1500                     # px/s at the start of his fall (accelerates)
BOSS_CUTSCENE_SOUND = "cutscene_giant_sound"
BOSS_CUTSCENE_LAND_SOUND = "cutscene_giant_fall_on_ground_sound"
BOSS_FOOTSTEP_SOUND = "giant_footstep"
BOSS_LAUGH_SOUND = "giant_laugh"
BOSS_LAUGH_INTERVAL = (10.0, 15.0)         # random seconds between laughs during the fight
BOSS_CUTSCENE_SHAKE = (18, 0.9)
BOSS_SEAL_COLOR = (120, 220, 255)
BOSS_SEAL_HEIGHT = 5 * TILE_SIZE

# night levels: a dark blue veil over the world (the background has its own night art)
NIGHT_TINT = (8, 12, 40, 95)

# ---------------------------------------------------------------- coins & shop
# Coins are rare: each stage hides LEVELS[i]["coins"] of them (1 in every
# stage) at a random spot, and each can only be collected ONCE
# (remembered in the save file) - so a full run earns 5: a bow plus 2 bombs.
COIN_ANIM_FPS = 10
COIN_BOB = (6, 2.2)                        # (pixels, speed) of the floating bob
COIN_SAFE_FROM_SPAWN = 8                   # tiles: no coin right next to the start...
COIN_SAFE_FROM_EXIT = 3                    # ...or the exit gate
TRADER_TALK_RANGE = (1.6 * TILE_SIZE, TILE_SIZE)   # (sideways, up/down) to press E
SHOP_ITEMS = [
    # id = icon file in assets/items/ and the inventory key; unique = can only own one;
    # held = what the trader says if you try to buy a unique item you already have
    {"id": "bow", "name": "Bow", "price": 3, "unique": True,
     "desc": "Strike from afar, like the archers do."},
    # bomb: you carry one at a time; once it's thrown you can buy a new one
    {"id": "bomb", "name": "Bomb", "price": 1, "unique": True,
     "desc": "Throw it to blast every enemy nearby. Light it and run.",
     "held": "One bomb at a time - throw that one first!"},
]

# ---------------------------------------------------------------- weapons
# Mouse wheel scrolls through the weapons (a bar pops up); landing on one equips it.
# "item" = what you must own (bought from the trader); None = always available.
# "consumable" = using it uses up the item (then you're back on the katana).
WEAPONS = [
    {"id": "katana", "name": "Katana", "item": None},
    {"id": "bow", "name": "Bow", "item": "bow"},
    {"id": "bomb", "name": "Bomb", "item": "bomb", "consumable": True},
]
WEAPON_BAR_TIME = 1.4                      # seconds the bar stays after the last scroll
PLAYER_BOW_RELEASE_FRAME = 4               # "bow" animation frame that looses the arrow
PLAYER_BOW_COOLDOWN = 0.3                  # extra pause after a shot
PLAYER_ARROW_SPEED = 900                   # px/s - much faster and flatter than the archers'
PLAYER_ARROW_LIFT = 60                     # small upward kick so long shots arc a little
PLAYER_ARROW_GRAVITY = 450
PLAYER_ARROW_DAMAGE = 2

# Bomb (weapon slot 3, LMB throws it - one use, buy another from the trader)
BOMB_THROW_SPEED = (430, 520)              # (forward, upward) px/s; plus a bit of your run speed
BOMB_FUSE = 1.3                            # seconds until it blows (touching an enemy blows it early)
BOMB_RADIUS = 2.2 * TILE_SIZE              # blast reach (px) - every enemy inside gets hit
BOMB_DAMAGE = 5                            # archer 3 HP, shinobi 6, samurai 10
BOMB_PLAYER_DAMAGE = 1                     # if YOU stand in the blast too (0 = harmless to you)
BOMB_HITBOX = 5 * SCALE
BOMB_IMAGE_SCALE = 2                       # the 16 px item icon, drawn at half the sprites' scale
BOMB_BOUNCE = 0.35                         # keeps this much of its falling speed when bouncing
BOMB_MIN_BOUNCE = 160                      # slower landings just stop
BOMB_GROUND_FRICTION = 6.0                 # rolling slows down (higher = stops sooner)
BOMB_THROW_COOLDOWN = 0.35
BOMB_SHAKE = (10, 0.35)
BOMB_EXPLOSION_TIME = 0.7                  # seconds the blast + smoke effect lasts

# ---------------------------------------------------------------- health bars
HEALTH_FILL = (204, 52, 58)
HEALTH_FILL_HI = (240, 112, 100)           # highlight stripe on top of the fill
HEALTH_TRAIL = (255, 232, 196)             # recently lost health, shrinks after a moment
HEALTH_EMPTY = (58, 36, 42)
HEALTH_FRAME = (20, 14, 20)
HEALTH_TRAIL_DELAY = 0.35                  # seconds before the trail starts shrinking
HEALTH_TRAIL_SPEED = 4.0                   # HP per second the trail shrinks
ENEMY_BAR_SIZE = (44, 6)

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
# Background themes: name -> folder inside assets/ holding the same five layer
# files. A level picks one with LEVELS[i]["background"] (default "day"; the
# menu always uses "day"). Make new ones with tools/generate_background.py --theme.
BACKGROUND_THEMES = {
    "day": "background",
    "evening": "background/evening",
    "night": "background/night",
}

# ---------------------------------------------------------------- audio
MASTER_VOLUME = 0.6            # 0..1, applies to every sound
SOUND_VOLUMES = {              # per-sound volume (file name without extension)
    "attack": 1.0,
    "jump": 0.8,
    "dash_attack": 1.0,
    "enemy_attack": 0.8,       # samurai spots the ninja
    "shinobi_spot": 0.5,       # shinobi spots the ninja (quiet dagger draw)
    "hit_hurt": 0.9,           # ninja or enemy takes damage
    "arrow": 0.7,              # archer looses an arrow
    "intro_scene_sound": 0.7,  # intro cutscene
    "player_blood_splash": 1.0,  # ninja's killing blow
    "defeat_sound": 0.7,       # after he dies (plays once)
    "explosion": 0.9,          # the ninja's bomb
    "cutscene_giant_sound": 1.0,                  # the golem lands (boss cutscene)
    "cutscene_giant_fall_on_ground_sound": 1.0,   # ...the ground impact (also his jump attack)
    "giant_footstep": 0.75,                       # every golem step
    "giant_laugh": 1.0,                           # the golem laughs now and then during the fight
}

# Background music is streamed from disk (not preloaded like the effects above).
MUSIC_FILES = {"level_bg_music", "main_menu", "giant-boss-fight-bg-music"}   # files in assets/audio that are music, not effects
LEVEL_MUSIC = "level_bg_music"      # loops during gameplay on every stage
MUSIC_VOLUME = 0.3                  # x MASTER_VOLUME - quiet, so it stays in the background
MUSIC_FADE_IN_MS = 1500             # when gameplay starts (after the intro)
MUSIC_FADE_OUT_MS = 800             # at "Stage clear" / "Victory"

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
STEP_HEIGHT = 5 * SCALE        # ledges up to this high are walked up automatically

# ---------------------------------------------------------------- camera
CAMERA_SMOOTHING = 5.0         # higher = camera catches up faster
CAMERA_LOOK_AHEAD = 96         # pixels shown ahead of the player's facing direction
CAMERA_OFFSET = (0, -48)       # shift from centre; negative y shows more sky

# ---------------------------------------------------------------- paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
# cleared stages are remembered here (NINJA_SAVE_FILE overrides it, e.g. for tests)
SAVE_FILE = os.environ.get("NINJA_SAVE_FILE") or os.path.join(ROOT_DIR, "save_data.json")
