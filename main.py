import sys
import math
import random
import time
import json
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

import pygame

# -------------------------
# Config / Constants
# -------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60
TILE = 48
BG_COLOR = (18, 18, 24)
WHITE = (240, 240, 240)
BLACK = (12, 12, 16)
RED = (220, 60, 60)
GREEN = (60, 200, 110)
BLUE = (70, 140, 255)
YELLOW = (240, 210, 80)
PURPLE = (155, 95, 225)
ORANGE = (240, 140, 70)
CYAN = (80, 220, 230)
GRAY = (120, 120, 130)

FONT_NAME = "segoeui"
SAVE_FILE = "save.json"

# Gameplay tuning
PLAYER_BASE_HP = 40
PLAYER_BASE_MANA = 20
PLAYER_BASE_ATK = 8
PLAYER_BASE_MAG = 8
PLAYER_BASE_SPD = 4

LEVEL_UP_INCREASE_PERCENT = 0.025  # 2.5% per level
DASH_MANA_COST = 1
MAGIC_MANA_COST = 3
SWORD_RANGE = 50
MAGIC_SPEED = 8
MAGIC_RADIUS = 8
INVULN_TIME = 0.6

# Waves / bosses
MINION_WAVES_PER_STAGE = 5
TOTAL_BOSSES = 10
SECRET_BOSS_STAGE = 11

# Drops - Gold and EXP updated
MINION_GOLD_RANGE = (5, 8)  # Updated from (1, 2)
MINION_EXP_RANGE = (3, 7)  # Updated from (2, 5)
# Bonus stage rewards (stages 1-5) - Gold and EXP updated
BONUS_STAGE_1_5_EXP = (5, 9)  # Updated from (4, 8)
BONUS_STAGE_1_5_GOLD = (10, 13)  # Updated from (8, 14)
# Bonus stage rewards (stages 6-10) - Gold and EXP updated
BONUS_STAGE_6_10_EXP = (5, 9)  # Updated from (8, 13)
BONUS_STAGE_6_10_GOLD = (10, 13)  # Updated from (14, 19)
# Individual Boss rewards (EXP, Gold) - Gold reduced by 25%
BOSS_REWARDS = {
    "Ba'al (The Insect King)": {"exp": (25, 35), "gold": (15, 24)},
    "Trefyr Herahid (The Dark Elf)": {"exp": (25, 35), "gold": (15, 24)},
    "Viscardi (Vampire Lord)": {"exp": (25, 35), "gold": (15, 24)},
    "Rox and Tox": {"exp": (25, 35), "gold": (15, 24)},
    "Rox (Big Twin)": {"exp": (25, 35), "gold": (15, 24)},
    "Tox (Small Twin)": {"exp": (25, 35), "gold": (15, 24)},
    "Thilreriltic (Lesser Demon Prince)": {"exp": (25, 35), "gold": (15, 24)},
    "Gorzak (Fire Giant Mage)": {"exp": (35, 55), "gold": (24, 45)},
    "Dram'zuku (The Undead King)": {"exp": (35, 55), "gold": (24, 45)},
    "Alhazred (Pack Leader)": {"exp": (35, 55), "gold": (24, 45)},
    "Noaghoirth, Destroyer of Men": {"exp": (35, 55), "gold": (24, 45)},
    "Zasu (Demon King)": {"exp": (35, 55), "gold": (24, 45)},
    "Shyssa (Demon Queen)": {"exp": (60, 90), "gold": (53, 75)},
}

# Health drops
HEALTH_DROP_CHANCE_MINION = 0.25
HEALTH_DROP_CHANCE_BOSS = 0.5
HEALTH_DROP_AMOUNT_RANGE = (4, 10)

# Shop items and order
WEAPONS = {
    "starter": {"price": 0, "range": 0, "dmg": 0, "mult": 1.0, "label": "Starter"},
    "wood": {"price": 200, "range": 5, "dmg": 0, "mult": 1.0, "label": "Wood Sword"},
    "twin_daggers": {"price": 400, "range": -2, "dmg": 0, "mult": 2.0, "label": "Twin Daggers"},
    "long_sword": {"price": 1000, "range": 10, "dmg": 3, "mult": 1.5, "label": "Long Sword"},
    "war_axe": {"price": 1400, "range": 5, "dmg": 9.5, "mult": 1.3, "label": "War Axe"},
    "war_hammer": {"price": 1600, "range": 5, "dmg": 7.3, "mult": 1.5, "label": "War Hammer"},
    "god_sword": {"price": 5000, "range": 30, "dmg": 50, "mult": 5.0, "label": "God Sword"},
}
ARMORS = {
    "none": {"price": 0, "hits": 0, "label": "None"},
    "light": {"price": 200, "hits": 2, "label": "Light"},
    "medium": {"price": 400, "hits": 4, "label": "Medium"},
    "heavy": {"price": 800, "hits": 6, "label": "Heavy"},
    "super": {"price": 1600, "hits": 10, "label": "Super"},
    "god": {"price": 6000, "hits": 20, "label": "God"},
}
ORDERED_WEAPONS = ["starter", "wood", "twin_daggers", "long_sword", "war_axe", "war_hammer", "god_sword"]
ORDERED_ARMORS = ["none", "light", "medium", "heavy", "super", "god"]
BASE_SWORD_RANGE = SWORD_RANGE

def get_weapon(player: "Player"):
    return WEAPONS.get(player.weapon_id, WEAPONS["starter"])

def get_armor(player: "Player"):
    return ARMORS.get(player.armor_id, ARMORS["none"])

def apply_audio_settings(state: "GameState"):
    """Apply current audio settings to pygame mixer and sounds"""
    try:
        # Apply music volume
        if state.music_enabled and state.sound_enabled:
            pygame.mixer.music.set_volume(state.music_volume * state.volume)
        else:
            pygame.mixer.music.set_volume(0.0)
        
        # Apply SFX volume to all loaded sounds
        sfx_vol = state.sfx_volume * state.volume if state.sound_enabled else 0.0
        for sound in state.sounds.values():
            if sound:
                sound.set_volume(sfx_vol)
    except Exception:
        pass

def toggle_fullscreen(state: "GameState"):
    """Toggle fullscreen mode and return new screen surface"""
    state.fullscreen = not state.fullscreen
    try:
        if state.fullscreen:
            return pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        else:
            return pygame.display.set_mode((WIDTH, HEIGHT))
    except Exception:
        # If fullscreen fails, fall back to windowed
        state.fullscreen = False
        return pygame.display.set_mode((WIDTH, HEIGHT))

# -------------------------
# Helpers
# -------------------------
@dataclass
class StatBlock:
    hp: int
    mana: int
    atk: int
    mag: int
    spd: int

    def level_up(self, stat: str):
        if stat == "attack":
            self.atk = int(self.atk * (1 + LEVEL_UP_INCREASE_PERCENT))
        elif stat == "magic":
            self.mag = int(self.mag * (1 + LEVEL_UP_INCREASE_PERCENT))
        elif stat == "health":
            self.hp = int(self.hp * (1 + LEVEL_UP_INCREASE_PERCENT))
        elif stat == "mana":
            self.mana = int(self.mana * (1 + LEVEL_UP_INCREASE_PERCENT))

@dataclass
class Entity:
    x: float
    y: float
    w: int
    h: int
    vx: float = 0
    vy: float = 0
    hp: int = 1
    max_hp: int = 1
    color: Tuple[int, int, int] = WHITE
    name: str = ""
    invuln_timer: float = 0.0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: int
    color: Tuple[int, int, int]
    radius: int = MAGIC_RADIUS
    from_player: bool = True
    # Optional status effect applied on hit (e.g., 'bleed', 'burn_no_heal')
    effect: Optional[str] = None
    effect_value: float = 0.0       # dps or magnitude depending on effect
    effect_duration: float = 0.0    # seconds

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def pos(self):
        return (int(self.x), int(self.y))

# -------------------------
# Player and enemies
# -------------------------
@dataclass
class Player(Entity):
    mana: int = PLAYER_BASE_MANA
    max_mana: int = PLAYER_BASE_MANA
    atk: int = PLAYER_BASE_ATK
    mag: int = PLAYER_BASE_MAG
    spd: int = PLAYER_BASE_SPD
    gold: int = 0
    exp: int = 0
    level: int = 1
    weapon_id: str = "starter"
    armor_id: str = "none"
    armor_hits_remaining: int = 0
    # Status effects
    bleed_time_left: float = 0.0
    bleed_tick_accum: float = 0.0
    bleed_dps: float = 0.0
    no_heal_time_left: float = 0.0

    def center(self):
        return self.x + self.w / 2, self.y + self.h / 2

    def move(self, keys, player_index=0):
        dx = dy = 0
        
        # Player 1 (WASD)
        if player_index == 0:
            if keys[pygame.K_w]: dy -= 1
            if keys[pygame.K_s]: dy += 1
            if keys[pygame.K_a]: dx -= 1
            if keys[pygame.K_d]: dx += 1
        # Player 2 (Arrow keys)
        elif player_index == 1:
            if keys[pygame.K_UP]: dy -= 1
            if keys[pygame.K_DOWN]: dy += 1
            if keys[pygame.K_LEFT]: dx -= 1
            if keys[pygame.K_RIGHT]: dx += 1
        # Player 3 (IJKL)
        elif player_index == 2:
            if keys[pygame.K_i]: dy -= 1
            if keys[pygame.K_k]: dy += 1
            if keys[pygame.K_j]: dx -= 1
            if keys[pygame.K_l]: dx += 1
        # Player 4 (Numpad)
        elif player_index == 3:
            if keys[pygame.K_KP8]: dy -= 1
            if keys[pygame.K_KP2]: dy += 1
            if keys[pygame.K_KP4]: dx -= 1
            if keys[pygame.K_KP6]: dx += 1
            
        length = math.hypot(dx, dy) or 1
        self.vx = (dx / length) * self.spd
        self.vy = (dy / length) * self.spd
        self.x = max(0, min(WIDTH - self.w, self.x + self.vx))
        self.y = max(0, min(HEIGHT - self.h, self.y + self.vy))

    def sword_attack(self, enemies: List[Entity]):
        # Melee using weapon stats (range/damage/multiplier)
        wpn = get_weapon(self)
        cx, cy = self.center()
        melee_range = BASE_SWORD_RANGE + wpn["range"]
        base_damage = max(1, self.atk + wpn["dmg"])  # base damage plus weapon flat bonus
        damage = int(base_damage * wpn["mult"])      # apply multiplier (e.g., twin daggers)
        hit_any = False
        for e in enemies:
            if e.hp <= 0: continue
            ex, ey = e.x + e.w/2, e.y + e.h/2
            if math.hypot(ex - cx, ey - cy) <= melee_range:
                e.hp -= damage
                e.invuln_timer = INVULN_TIME
                # Track last hit source/time for enemy behaviors
                if hasattr(e, 'last_hit_time'):
                    e.last_hit_time = time.time()
                if hasattr(e, 'data'):
                    e.data['last_hit_by_sword'] = True
                hit_any = True
        return hit_any

    def cast_magic(self, target_pos) -> Optional[Projectile]:
        if self.mana < MAGIC_MANA_COST:
            return None
        self.mana -= MAGIC_MANA_COST
        cx, cy = self.center()
        tx, ty = target_pos
        dx, dy = tx - cx, ty - cy
        dist = math.hypot(dx, dy) or 1
        vx = MAGIC_SPEED * dx / dist
        vy = MAGIC_SPEED * dy / dist
        dmg = self.mag  # weapon no longer affects magic damage
        return Projectile(cx, cy, vx, vy, dmg, CYAN, from_player=True)

    def dash(self, mouse_pos):
        if self.mana < DASH_MANA_COST:
            return
        self.mana -= DASH_MANA_COST
        cx, cy = self.center()
        tx, ty = mouse_pos
        dx, dy = tx - cx, ty - cy
        dist = math.hypot(dx, dy) or 1
        dash_len = 80
        self.x = max(0, min(WIDTH - self.w, self.x + (dash_len * dx / dist)))
        self.y = max(0, min(HEIGHT - self.h, self.y + (dash_len * dy / dist)))

@dataclass
class Enemy(Entity):
    speed: float = 2.0
    damage: int = 5
    ai: str = "chase"
    # Ranged attack behavior
    shoot_interval: float = 0.0  # 0 = no shooting
    shoot_timer: float = 0.0
    projectile_speed: float = 5.0
    projectile_damage: int = 6
    projectile_color: Tuple[int, int, int] = ORANGE
    projectile_radius: int = MAGIC_RADIUS
    projectile_effect: Optional[str] = None
    projectile_effect_value: float = 0.0
    projectile_effect_duration: float = 0.0
    projectile_pattern: str = "aim"  # aim | cross4 | breath
    # On-hit status effects (melee contact)
    on_hit_effect: Optional[str] = None
    on_hit_effect_value: float = 0.0
    on_hit_effect_duration: float = 0.0
    # Self-heal behavior
    can_heal: bool = False
    heal_delay: float = 3.0
    heal_per_sec: float = 4.0
    last_hit_time: float = 0.0
    # Special flags/data
    speed_doubles_at_half: bool = False
    sped_up: bool = False
    revived_once: bool = False
    data: dict = field(default_factory=dict)
    # Animation
    anim_timer: float = 0.0

    def update(self, player: Player, obstacles=None):
        if self.hp <= 0:
            return
        
        # Update animation timer
        self.anim_timer += 1/60.0  # Assuming 60 FPS
        if self.ai == "chase":
            px, py = player.x, player.y
            dx, dy = px - self.x, py - self.y
            dist = math.hypot(dx, dy) or 1
            
            # Imps stay at distance and shoot fireballs
            if self.name == "Imp":
                ideal_distance = 150  # Stay at this distance from player
                if dist < ideal_distance:
                    # Move away from player
                    self.vx = -self.speed * dx / dist
                    self.vy = -self.speed * dy / dist
                elif dist > ideal_distance + 50:
                    # Move closer to player
                    self.vx = self.speed * dx / dist
                    self.vy = self.speed * dy / dist
                else:
                    # Stay in position and shoot
                    self.vx = 0
                    self.vy = 0
            else:
                self.vx = self.speed * dx / dist
                self.vy = self.speed * dy / dist
            
            # Try to move around obstacles more intelligently
            if obstacles:
                # Check if direct path is blocked
                test_rect = pygame.Rect(self.x + self.vx, self.y + self.vy, self.w, self.h)
                blocked = False
                for ob in obstacles:
                    # Imps ignore trees, ruins, and castle structures (they fly)
                    if self.name == "Imp" and ob.kind in ["tree", "ruin", "castle_wall", "castle_tower", "battlement"]:
                        continue
                    if test_rect.colliderect(ob.rect()):
                        blocked = True
                        break
                
                if blocked:
                    # Try alternative paths
                    alternatives = [
                        (self.vx * 0.7 + self.vy * 0.3, self.vy * 0.7 - self.vx * 0.3),  # Slight right turn
                        (self.vx * 0.7 - self.vy * 0.3, self.vy * 0.7 + self.vx * 0.3),  # Slight left turn
                        (self.vy, -self.vx),  # 90 degree turn
                        (-self.vy, self.vx),  # -90 degree turn
                    ]
                    for alt_vx, alt_vy in alternatives:
                        test_rect = pygame.Rect(self.x + alt_vx, self.y + alt_vy, self.w, self.h)
                        alt_blocked = False
                        for ob in obstacles:
                            if self.name == "Imp" and ob.kind in ["tree", "ruin", "castle_wall", "castle_tower", "battlement"]:
                                continue
                            if test_rect.colliderect(ob.rect()):
                                alt_blocked = True
                                break
                        if not alt_blocked:
                            self.vx, self.vy = alt_vx, alt_vy
                            break
            
            self.x += self.vx
            self.y += self.vy
        elif self.ai == "wander":
            self.x += self.vx
            self.y += self.vy
            if random.random() < 0.02:
                ang = random.random() * math.tau
                self.vx = math.cos(ang) * self.speed
                self.vy = math.sin(ang) * self.speed
        self.x = max(0, min(WIDTH - self.w, self.x))
        self.y = max(0, min(HEIGHT - self.h, self.y))

@dataclass
class Merchant(Entity):
    # Static NPC
    pass

# -------------------------
# Content generation
# -------------------------
BOSS_LIST = [
    ("Ba'al (The Insect King)", ORANGE),
    ("Trefyr Herahid (The Dark Elf)", PURPLE),
    ("Viscardi (Vampire Lord)", RED),
    ("Rox and Tox", (120, 220, 120)),
    ("Thilreriltic (Lesser Demon Prince)", (220, 120, 220)),
    ("Gorzak (Fire Giant Mage)", (240, 90, 40)),
    ("Dram'zuku (The Undead King)", (180, 230, 255)),
    ("Alhazred (Pack Leader)", (120, 120, 120)),
    ("Noaghoirth, Destroyer of Men", (200, 40, 40)),
    ("Zasu (Demon King)", (90, 40, 120)),
]
SECRET_BOSS = ("Shyssa (Demon Queen)", (255, 70, 160))

MINIONS = [
    ("Imp", (255, 120, 60)),
    ("Skeleton", (220, 220, 220)),
    ("Demon", (200, 50, 50)),
]

# Stage-specific enemy lists
STAGE_ENEMIES = {
    1: [("Bee", (255, 255, 0)), ("Fly", (100, 100, 100)), ("Centipede", (139, 69, 19))],
    2: [("Goblin Warrior", (0, 128, 0)), ("Goblin Bomber", (128, 128, 0)), ("Hag", (128, 0, 128)), ("Ogre", (139, 69, 19))],
    3: [("Bat", (64, 64, 64)), ("Thrall", (128, 0, 0)), ("Ghoul", (105, 105, 105))],
    4: [("Zombie", (0, 100, 0)), ("Skeleton Warrior", (220, 220, 220)), ("Skeleton Archer", (200, 200, 200)), ("Ghoul", (105, 105, 105))],
    5: [("Imp", (255, 120, 60)), ("Demon", (200, 50, 50)), ("Zombie", (0, 100, 0))],
    6: [("Lava Slime", (255, 69, 0)), ("Salamander", (255, 140, 0)), ("Fire Turtle", (178, 34, 34))],
    7: [("Zombie", (0, 100, 0)), ("Undead Mage", (75, 0, 130)), ("Skeleton Warrior", (220, 220, 220))],
    8: [("Wolf", (105, 105, 105)), ("Werewolf", (139, 69, 19)), ("Dire Wolf", (64, 64, 64))],
    9: [("Drake", (128, 0, 0)), ("Salamander", (255, 140, 0))],
    10: [("Imp", (255, 120, 60)), ("Demon", (200, 50, 50)), ("Skeleton", (220, 220, 220))],  # Default mix for stage 10
}

# -------------------------
# Obstacles & Utility
# -------------------------

@dataclass
class Obstacle:
    x: int
    y: int
    w: int
    h: int
    kind: str = "tree"  # tree | ruin | rock
    color: Tuple[int, int, int] = (80, 120, 60)

    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x, self.y, self.w, self.h)


def collides_rect(rect: pygame.Rect, obstacles: List["Obstacle"]) -> bool:
    for ob in obstacles:
        if rect.colliderect(ob.rect()):
            return True
    return False


def resolve_entity_collision(entity: Entity, obstacles: List["Obstacle"], prev_x: float, prev_y: float):
    # If entity overlaps an obstacle after moving, separate by axes using previous position
    r_now = entity.rect()
    if not collides_rect(r_now, obstacles):
        return
    # Try X only
    entity.x = prev_x + entity.vx
    entity.y = prev_y
    if not collides_rect(entity.rect(), obstacles):
        return
    # Try Y only
    entity.x = prev_x
    entity.y = prev_y + entity.vy
    if not collides_rect(entity.rect(), obstacles):
        return
    # Revert fully
    entity.x = prev_x
    entity.y = prev_y


def random_free_spot(size: int, obstacles: List["Obstacle"], attempts: int = 100) -> Tuple[int, int]:
    cx, cy = WIDTH // 2, HEIGHT // 2
    for _ in range(attempts):
        x = random.randint(0, WIDTH - size)
        y = random.randint(0, HEIGHT - size)
        # keep some space from center
        if math.hypot(x - cx, y - cy) < 140:
            continue
        r = pygame.Rect(x, y, size, size)
        if not collides_rect(r, obstacles):
            return x, y
    # fallback
    return WIDTH // 2 - size // 2, HEIGHT // 2 - size // 2


def generate_arena_obstacles(stage: int) -> List["Obstacle"]:
    obstacles: List[Obstacle] = []
    random.seed(stage * 1337)
    count = 8 + min(6, stage // 2)

    def add_if_free(x, y, w, h, kind, color):
        r = pygame.Rect(x, y, w, h)
        if r.left < 0 or r.right > WIDTH or r.top < 0 or r.bottom > HEIGHT:
            return False
        if collides_rect(r, obstacles):
            return False
        if math.hypot(x - WIDTH//2, y - HEIGHT//2) < 120:
            return False
        obstacles.append(Obstacle(x, y, w, h, kind, color))
        return True

    # Determine terrain theme based on stage
    if stage <= 4:
        # Forest theme (Boss 1-4)
        # More trees, some rocks, minimal ruins
        for _ in range(count * 2 // 3):  # More trees
            w = h = random.randint(36, 56)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "tree", (70, 140, 70))
        
        # Add some larger trees for variety
        for _ in range(count // 4):
            w = h = random.randint(60, 80)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "tree", (60, 120, 60))
        
        # Few rocks scattered around
        for _ in range(count // 4):
            w = h = random.randint(28, 42)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "rock", (130, 130, 140))
            
    elif stage <= 9:
        # Ruined city theme (Boss 5-9)
        # More ruins, fewer trees, some rocks
        for _ in range(count * 2 // 3):  # More ruins
            if random.random() < 0.6:
                w, h = random.randint(140, 280), random.randint(15, 25)
            else:
                w, h = random.randint(15, 25), random.randint(140, 280)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "ruin", (110, 110, 120))
        
        # Add some broken pillars (square ruins)
        for _ in range(count // 4):
            w = h = random.randint(40, 60)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "ruin", (100, 100, 110))
        
        # Few dead trees
        for _ in range(count // 5):
            w = h = random.randint(30, 45)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "tree", (80, 70, 60))  # Dead tree color
        
        # Rubble (rocks)
        for _ in range(count // 4):
            w = h = random.randint(25, 40)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "rock", (120, 120, 130))
            
    else:
        # Castle theme (Boss 10 & Secret Boss)
        # Castle walls, towers, and fortifications
        
        # Add castle walls (long rectangular structures)
        for _ in range(count // 3):
            if random.random() < 0.7:
                w, h = random.randint(200, 350), random.randint(25, 35)
            else:
                w, h = random.randint(25, 35), random.randint(200, 350)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "castle_wall", (90, 90, 100))
        
        # Add castle towers (square structures)
        for _ in range(count // 3):
            w = h = random.randint(60, 90)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "castle_tower", (80, 80, 90))
        
        # Add some battlements (smaller wall segments)
        for _ in range(count // 4):
            if random.random() < 0.5:
                w, h = random.randint(80, 120), random.randint(20, 30)
            else:
                w, h = random.randint(20, 30), random.randint(80, 120)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "battlement", (100, 100, 110))
        
        # Add some castle debris
        for _ in range(count // 5):
            w = h = random.randint(35, 50)
            x = random.randint(0, WIDTH - w)
            y = random.randint(0, HEIGHT - h)
            add_if_free(x, y, w, h, "rock", (110, 110, 120))

    return obstacles


def draw_obstacles(surface, obstacles: List["Obstacle"]):
    for ob in obstacles:
        r = ob.rect()
        if ob.kind == "tree":
            # trunk
            trunk_w = max(6, ob.w // 6)
            pygame.draw.rect(surface, (120, 80, 40), (ob.x + ob.w//2 - trunk_w//2, ob.y + ob.h - 12, trunk_w, 12))
            # crown
            pygame.draw.ellipse(surface, ob.color, (ob.x, ob.y, ob.w, ob.h))
            pygame.draw.rect(surface, (20, 60, 20), r, 2)
        elif ob.kind == "ruin":
            pygame.draw.rect(surface, ob.color, r)
            pygame.draw.rect(surface, (200, 200, 210), r, 2)
        elif ob.kind == "rock":
            pygame.draw.ellipse(surface, ob.color, r)
            pygame.draw.rect(surface, (200, 200, 210), r, 1)
        elif ob.kind == "castle_wall":
            # Draw castle wall with stone texture
            pygame.draw.rect(surface, ob.color, r)
            pygame.draw.rect(surface, (160, 160, 170), r, 3)
            # Add some stone block details
            if ob.w > ob.h:  # Horizontal wall
                for i in range(0, ob.w, 40):
                    pygame.draw.line(surface, (160, 160, 170), (ob.x + i, ob.y), (ob.x + i, ob.y + ob.h))
            else:  # Vertical wall
                for i in range(0, ob.h, 40):
                    pygame.draw.line(surface, (160, 160, 170), (ob.x, ob.y + i), (ob.x + ob.w, ob.y + i))
        elif ob.kind == "castle_tower":
            # Draw castle tower with crenellations
            pygame.draw.rect(surface, ob.color, r)
            pygame.draw.rect(surface, (160, 160, 170), r, 3)
            # Add crenellations on top
            cren_w = ob.w // 6
            for i in range(0, ob.w, cren_w * 2):
                pygame.draw.rect(surface, ob.color, (ob.x + i, ob.y - 8, cren_w, 8))
                pygame.draw.rect(surface, (160, 160, 170), (ob.x + i, ob.y - 8, cren_w, 8), 2)
        elif ob.kind == "battlement":
            # Draw battlement wall
            pygame.draw.rect(surface, ob.color, r)
            pygame.draw.rect(surface, (160, 160, 170), r, 2)
            # Add crenellation pattern
            if ob.w > ob.h:  # Horizontal battlement
                cren_w = 15
                for i in range(0, ob.w, cren_w * 2):
                    pygame.draw.rect(surface, ob.color, (ob.x + i, ob.y - 6, cren_w, 6))
            else:  # Vertical battlement
                cren_h = 15
                for i in range(0, ob.h, cren_h * 2):
                    pygame.draw.rect(surface, ob.color, (ob.x - 6, ob.y + i, 6, cren_h))
        else:
            pygame.draw.rect(surface, ob.color, r)

# -------------------------
# Utility draw
# -------------------------

def draw_bar(surface, x, y, w, h, ratio, color_fg, color_bg=BLACK):
    pygame.draw.rect(surface, color_bg, (x, y, w, h))
    pygame.draw.rect(surface, color_fg, (x, y, int(w * max(0, min(1, ratio))), h))
    pygame.draw.rect(surface, WHITE, (x, y, w, h), 2)

# -------------------------
# Game flow and state
# -------------------------
@dataclass
class GameState:
    stage: int = 1
    wave: int = 1
    in_safe_area: bool = False
    enemies: List[Enemy] = field(default_factory=list)
    projectiles: List[Projectile] = field(default_factory=list)
    drops: List[Tuple[int,int,str,int]] = field(default_factory=list)  # (x, y, type: gold|exp|heal, amount)
    last_spawn: float = 0.0
    show_stats: bool = False  # Stats page toggle
    player: Player = field(default_factory=lambda: Player(
        x=WIDTH//2-16, y=HEIGHT//2-16, w=32, h=32,
        hp=PLAYER_BASE_HP, max_hp=PLAYER_BASE_HP,
        mana=PLAYER_BASE_MANA, max_mana=PLAYER_BASE_MANA,
        atk=PLAYER_BASE_ATK, mag=PLAYER_BASE_MAG, spd=PLAYER_BASE_SPD,
        color=(90,200,120), name="Hero"
    ))
    font_big: Optional[pygame.font.Font] = None
    font_small: Optional[pygame.font.Font] = None
    info_message: str = ""
    info_timer: float = 0.0

    # New: score, timer, pause/menu, sounds
    score: int = 0
    stage_start_score: int = 0  # Score at beginning of current stage
    play_time: float = 0.0
    new_game_plus: int = 0  # Track how many times secret boss was killed
    post_boss_10_delay: float = 0.0  # 20 second delay after boss 10
    paused: bool = False
    in_main_menu: bool = True  # Start in main menu
    menu_page: str = "main"  # main | pause | settings | controls
    menu_index: int = 0
    controls_expanded: bool = False
    sounds: dict = field(default_factory=dict)
    volume: float = 0.6
    # Display settings
    fullscreen: bool = False
    # Sound settings
    sound_enabled: bool = True
    music_enabled: bool = True
    music_volume: float = 0.5
    sfx_volume: float = 0.7
    # Menu input debouncing
    menu_last_nav_time: float = 0.0
    menu_nav_delay: float = 0.15
    # Volume adjust tick throttle
    volume_last_time: float = 0.0
    volume_tick_delay: float = 0.08

    # Waves: inter-wave cooldown and pending spawn flag
    wave_cooldown: float = 0.0
    pending_spawn: bool = False
    
    # Sprite images
    imp_sprites: List[pygame.Surface] = field(default_factory=list)
    bee_sprites: List[pygame.Surface] = field(default_factory=list)
    fly_sprites: List[pygame.Surface] = field(default_factory=list)

    # Health regen timers
    hp_regen_timer: float = 0.0
    hp_regen_interval: float = 1.0
    hp_regen_amount: int = 1
    
    # Floating messages that follow player
    floating_messages: List[Tuple[str, float, float, float]] = field(default_factory=list)  # (text, timer, offset_x, offset_y)

    def message(self, txt: str, t: float = 2.0):
        self.info_message = txt
        self.info_timer = t
    
    def floating_message(self, txt: str, t: float = 1.5):
        """Add a floating message that follows the player"""
        import random
        offset_x = random.uniform(-20, 20)
        offset_y = random.uniform(-40, -10)
        self.floating_messages.append((txt, t, offset_x, offset_y))

    def serialize(self):
        return {
            "stage": self.stage,
            "wave": self.wave,
            "in_safe_area": self.in_safe_area,
            "score": self.score,
            "stage_start_score": self.stage_start_score,
            "play_time": self.play_time,
            "new_game_plus": self.new_game_plus,
            "post_boss_10_delay": self.post_boss_10_delay,
            "settings": {
                "volume": self.volume,
                "fullscreen": self.fullscreen,
                "sound_enabled": self.sound_enabled,
                "music_enabled": self.music_enabled,
                "music_volume": self.music_volume,
                "sfx_volume": self.sfx_volume
            },
            "player": {
                "x": self.player.x, "y": self.player.y, "hp": self.player.hp, "max_hp": self.player.max_hp,
                "mana": self.player.mana, "max_mana": self.player.max_mana, "atk": self.player.atk,
                "mag": self.player.mag, "spd": self.player.spd, "gold": self.player.gold,
                "exp": self.player.exp, "level": self.player.level,
                "weapon_id": self.player.weapon_id, "armor_id": self.player.armor_id,
                "armor_hits": self.player.armor_hits_remaining
            }
        }

    def deserialize(self, data):
        self.stage = data.get("stage", 1)
        self.wave = data.get("wave", 1)
        self.in_safe_area = data.get("in_safe_area", False)
        self.score = data.get("score", 0)
        self.stage_start_score = data.get("stage_start_score", 0)
        self.play_time = data.get("play_time", 0.0)
        self.new_game_plus = data.get("new_game_plus", 0)
        self.post_boss_10_delay = data.get("post_boss_10_delay", 0.0)
        # Load settings
        settings = data.get("settings", {})
        self.volume = settings.get("volume", 0.6)
        self.fullscreen = settings.get("fullscreen", False)
        self.sound_enabled = settings.get("sound_enabled", True)
        self.music_enabled = settings.get("music_enabled", True)
        self.music_volume = settings.get("music_volume", 0.5)
        self.sfx_volume = settings.get("sfx_volume", 0.7)
        # Load player data
        p = data.get("player", {})
        self.player.x = p.get("x", self.player.x)
        self.player.y = p.get("y", self.player.y)
        self.player.hp = p.get("hp", self.player.hp)
        self.player.max_hp = p.get("max_hp", self.player.max_hp)
        self.player.mana = p.get("mana", self.player.mana)
        self.player.max_mana = p.get("max_mana", self.player.max_mana)
        self.player.atk = p.get("atk", self.player.atk)
        self.player.mag = p.get("mag", self.player.mag)
        self.player.spd = p.get("spd", self.player.spd)
        self.player.gold = p.get("gold", self.player.gold)
        self.player.exp = p.get("exp", self.player.exp)
        self.player.level = p.get("level", self.player.level)
        self.player.weapon_id = p.get("weapon_id", self.player.weapon_id)
        self.player.armor_id = p.get("armor_id", self.player.armor_id)
        self.player.armor_hits_remaining = p.get("armor_hits", self.player.armor_hits_remaining)



# -------------------------
# Spawning and waves
# -------------------------

def spawn_minion(stage: int, obstacles: List["Obstacle"], ng_plus: int = 0) -> Enemy:
    # Use stage-specific enemies if available, otherwise fall back to default MINIONS
    enemy_list = STAGE_ENEMIES.get(stage, MINIONS)
    name, color = random.choice(enemy_list)
    
    # Base stats
    size = 26
    hp = 8 + stage * 3
    dmg = 4 + stage
    speed = 1.8 + 0.05 * stage
    
    # Stage 1 enemies
    if name == 'Bee':
        size = 40
        hp = int(hp * 0.8)
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.shoot_interval = 2.0
        enemy.projectile_speed = 6.0
        enemy.projectile_damage = max(2, 1 + stage)
        enemy.projectile_color = YELLOW
        enemy.projectile_pattern = 'aim'
        return enemy
    elif name == 'Fly':
        size = 32
        hp = int(hp * 0.5)
        dmg = int(dmg * 0.7)
        speed *= 1.5  # Faster than player
        return create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
    elif name == 'Centipede':
        size = 32
        hp = int(hp * 1.2)
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.shoot_interval = 2.5
        enemy.projectile_speed = 5.0
        enemy.projectile_damage = max(3, 2 + stage)
        enemy.projectile_color = GREEN
        enemy.projectile_effect = 'poison'
        enemy.projectile_effect_value = 1.0
        enemy.projectile_effect_duration = 3.0
        enemy.projectile_pattern = 'aim'
        return enemy
    
    # Stage 2 enemies
    elif name == 'Goblin Warrior':
        size = 24
        return create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
    elif name == 'Goblin Bomber':
        size = 24
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.shoot_interval = 3.0
        enemy.projectile_speed = 4.0
        enemy.projectile_damage = max(5, 3 + stage)
        enemy.projectile_color = RED
        enemy.projectile_pattern = 'bomb'  # Special bomb pattern
        return enemy
    elif name == 'Hag':
        size = 28
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.shoot_interval = 2.8
        enemy.projectile_speed = 5.5
        enemy.projectile_damage = max(2, 1 + stage)
        enemy.projectile_color = PURPLE
        enemy.projectile_effect = 'poison'
        enemy.projectile_effect_value = 1.0
        enemy.projectile_effect_duration = 3.0
        enemy.projectile_pattern = 'aim'
        return enemy
    elif name == 'Ogre':
        size = 40
        hp = int(hp * 1.8)
        dmg = int(dmg * 1.5)
        speed *= 0.6  # Slow but powerful
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.on_hit_effect = 'knockback'
        enemy.on_hit_effect_value = 125.0  # Knockback range
        return enemy
    
    # Stage 3 enemies
    elif name == 'Bat':
        size = 18
        hp = 1  # Dies in one hit
        speed *= 1.8
        return create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
    elif name == 'Thrall':
        size = 26
        hp = int(hp * 0.8)
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.on_hit_effect = 'bleed'
        enemy.on_hit_effect_value = 0.5
        enemy.on_hit_effect_duration = 2.0
        return enemy
    elif name == 'Ghoul':
        size = 28
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.data['ghoul_buff'] = True  # Special ghoul buffing behavior
        return enemy
    
    # Stage 4 enemies
    elif name == 'Zombie':
        size = 30
        hp = int(hp * 1.3)
        speed *= 0.8
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.on_hit_effect = 'slow'
        enemy.on_hit_effect_duration = 2.0
        return enemy
    elif name == 'Skeleton Warrior':
        size = 26
        return create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
    elif name == 'Skeleton Archer':
        size = 26
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.shoot_interval = 2.2
        enemy.projectile_speed = 7.0
        enemy.projectile_damage = max(3, 2 + stage)
        enemy.projectile_color = WHITE
        enemy.projectile_pattern = 'aim'
        return enemy
    
    # Stage 6 enemies
    elif name == 'Lava Slime':
        size = 24
        speed *= 0.5  # Very slow
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.data['lava_trail'] = True  # Leaves lava trails
        return enemy
    elif name == 'Salamander':
        size = 30
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.shoot_interval = 2.0
        enemy.projectile_speed = 6.0
        enemy.projectile_damage = max(4, 3 + stage)
        enemy.projectile_color = ORANGE
        enemy.projectile_effect = 'burn'
        enemy.projectile_effect_value = 1.0
        enemy.projectile_effect_duration = 5.0
        enemy.projectile_pattern = 'breath'
        return enemy
    elif name == 'Fire Turtle':
        size = 32
        hp = int(hp * 1.4)
        speed *= 0.7
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.on_hit_effect = 'burn'
        enemy.on_hit_effect_value = 1.0
        enemy.on_hit_effect_duration = 5.0
        return enemy
    
    # Stage 7 enemies
    elif name == 'Undead Mage':
        size = 28
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.shoot_interval = 2.5
        enemy.projectile_speed = 6.5
        enemy.projectile_damage = max(4, 3 + stage)
        enemy.projectile_color = CYAN
        enemy.projectile_pattern = 'aim'
        return enemy
    
    # Stage 8 enemies
    elif name == 'Wolf':
        size = 24
        speed *= 1.3
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.data['flee_when_weak'] = True
        return enemy
    elif name == 'Werewolf':
        size = 30
        hp = int(hp * 1.2)
        dmg = int(dmg * 1.1)
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.on_hit_effect = 'trauma'  # Slow + bleed chance
        enemy.on_hit_effect_value = 0.5  # 50% chance
        enemy.on_hit_effect_duration = 3.0
        return enemy
    elif name == 'Dire Wolf':
        size = 26
        speed *= 1.2
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.data['flee_when_weak'] = True
        return enemy
    
    # Stage 9 enemies
    elif name == 'Drake':
        size = 36
        hp = int(hp * 1.5)
        dmg = int(dmg * 1.3)
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.shoot_interval = 1.8
        enemy.projectile_speed = 6.5
        enemy.projectile_damage = max(5, 4 + stage)
        enemy.projectile_color = BLUE  # Ice/fire/toxic mix
        enemy.projectile_pattern = 'triple'  # Shoots 3 different types
        return enemy
    
    # Default enemies (Imp, Skeleton, Demon)
    elif name == 'Demon':
        speed *= 2.0
        dmg = int(dmg * 1.5)
        hp *= 2
        return create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
    elif name == 'Imp':
        enemy = create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)
        enemy.shoot_interval = 1.8
        enemy.projectile_speed = 8.0
        enemy.projectile_damage = max(3, 2 + stage)
        if ng_plus > 0:
            enemy.projectile_damage = int(enemy.projectile_damage * (2 ** ng_plus))
        enemy.projectile_color = ORANGE
        enemy.projectile_pattern = 'aim'
        return enemy
    else:
        # Default skeleton or other
        return create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus)

def create_enemy_with_stats(name, color, size, hp, dmg, speed, obstacles, ng_plus):
    """Helper function to create enemy with NG+ scaling"""
    if ng_plus > 0:
        hp = int(hp * (2 ** ng_plus))
        dmg = int(dmg * (2 ** ng_plus))
    
    x, y = random_free_spot(size, obstacles)
    return Enemy(x=x, y=y, w=size, h=size, hp=hp, max_hp=hp, color=color, name=name, speed=speed, damage=dmg)


def spawn_boss(stage: int, obstacles: List["Obstacle"], ng_plus: int = 0) -> List[Enemy]:
    if stage == SECRET_BOSS_STAGE:
        name, color = SECRET_BOSS
        size = 40
        hp = 600
        dmg = 28
        speed = 2.2
        

        
        # Apply New Game+ scaling
        if ng_plus > 0:
            hp = int(hp * (2 ** ng_plus))
            dmg = int(dmg * (2 ** ng_plus))
        
        x, y = random_free_spot(size, obstacles)
        queen = Enemy(x=x, y=y, w=size, h=size, hp=hp, max_hp=hp, color=color, name=name, speed=speed, damage=dmg)
        # Demon Queen: summons allies and must be finished by sword (tracked via data)
        queen.shoot_interval = 2.8
        queen.projectile_speed = 6.0
        queen.projectile_damage = 10
        # Apply NG+ scaling to projectile damage
        if ng_plus > 0:
            queen.projectile_damage = int(queen.projectile_damage * (2 ** ng_plus))
        queen.projectile_color = PURPLE
        queen.projectile_pattern = 'aim'
        queen.data['summon_thresholds'] = {0.8: False, 0.6: False, 0.4: False, 0.2: False}
        queen.data['must_die_by_sword'] = True
        queen.data['revive_once'] = False
        return [queen]
    idx = min(stage-1, len(BOSS_LIST)-1)
    name, color = BOSS_LIST[idx]
    size = 40
    base_hp = 650 + stage * 20
    
    # Reduce health by 25% for first 5 bosses
    if stage <= 5:
        base_hp = int(base_hp * 0.75)
    
    base_dmg = 12 + stage
    base_speed = 2.0 + 0.05 * stage
    

    
    # Apply New Game+ scaling
    if ng_plus > 0:
        base_hp = int(base_hp * (2 ** ng_plus))
        base_dmg = int(base_dmg * (2 ** ng_plus))
    
    x, y = random_free_spot(size, obstacles)
    e = Enemy(x=x, y=y, w=size, h=size, hp=base_hp, max_hp=base_hp, color=color, name=name, speed=base_speed, damage=base_dmg)
    # Configure boss behaviors
    if name == "Ba'al (The Insect King)":  # Boss 1: shoot stingers
        e.shoot_interval = 1.8
        e.projectile_speed = 6.5
        e.projectile_damage = 10
        if ng_plus > 0:
            e.projectile_damage = int(e.projectile_damage * (2 ** ng_plus))
        e.projectile_color = ORANGE
        e.projectile_pattern = 'aim'
        e.data['summon_thresholds'] = {0.7: False, 0.4: False}
    elif name == "Trefyr Herahid (The Dark Elf)":  # Boss 2: shoot arrows
        e.shoot_interval = 1.2
        e.projectile_speed = 8.0
        e.projectile_damage = 9
        if ng_plus > 0:
            e.projectile_damage = int(e.projectile_damage * (2 ** ng_plus))
        e.projectile_color = YELLOW
        e.projectile_pattern = 'aim'
        e.data['summon_thresholds'] = {0.6: False, 0.3: False}
    elif name == "Viscardi (Vampire Lord)":  # Boss 3: cause bleed -2 dps for 10s on hit
        e.on_hit_effect = 'bleed'
        e.on_hit_effect_value = 2.0
        if ng_plus > 0:
            e.on_hit_effect_value = e.on_hit_effect_value * (2 ** ng_plus)
        e.on_hit_effect_duration = 10.0
        e.data['summon_thresholds'] = {0.5: False, 0.2: False}
    elif name == "Rox and Tox":  # Boss 4: twin buff on death
        e.data['twin_buff_on_death'] = True
        e.data['summon_thresholds'] = {0.6: False, 0.3: False}
    elif name == "Thilreriltic (Lesser Demon Prince)":  # Boss 5: shoots fireballs in 8 directions until dead, heals to 80%
        e.shoot_interval = 1.5
        e.projectile_speed = 6.0
        e.projectile_damage = 11
        if ng_plus > 0:
            e.projectile_damage = int(e.projectile_damage * (2 ** ng_plus))
        e.projectile_color = ORANGE
        e.projectile_pattern = 'cross8'  # 8 directions
        e.data['heal_to_80_percent'] = True
        e.data['summon_thresholds'] = {0.7: False, 0.4: False}
    elif name == "Gorzak (Fire Giant Mage)":  # Boss 6: big fireballs; sword causes burn (no heal 10s)
        e.shoot_interval = 2.4
        e.projectile_speed = 5.0
        e.projectile_damage = 14
        if ng_plus > 0:
            e.projectile_damage = int(e.projectile_damage * (2 ** ng_plus))
        e.projectile_color = ORANGE
        e.projectile_radius = MAGIC_RADIUS + 4
        e.projectile_pattern = 'aim'
        e.on_hit_effect = 'no_heal'
        e.on_hit_effect_duration = 10.0
        e.data['summon_thresholds'] = {0.6: False, 0.3: False}
    elif name == "Dram'zuku (The Undead King)":  # Boss 7: fireball and self-heal if not attacked 3s
        e.shoot_interval = 1.8
        e.projectile_speed = 6.0
        e.projectile_damage = 11
        if ng_plus > 0:
            e.projectile_damage = int(e.projectile_damage * (2 ** ng_plus))
        e.projectile_color = CYAN
        e.projectile_pattern = 'aim'
        e.can_heal = True
        e.heal_delay = 3.0
        e.heal_per_sec = 6.0
        if ng_plus > 0:
            e.heal_per_sec = e.heal_per_sec * (2 ** ng_plus)
        e.data['summon_thresholds'] = {0.5: False, 0.2: False}
    elif name == "Alhazred (Pack Leader)":  # Boss 8: speed doubles at 50%
        e.speed_doubles_at_half = True
        e.data['summon_thresholds'] = {0.6: False, 0.3: False}
    elif name == "Noaghoirth, Destroyer of Men":  # Boss 9: fire breath
        e.shoot_interval = 0.25
        e.projectile_speed = 7.0
        e.projectile_damage = 6
        if ng_plus > 0:
            e.projectile_damage = int(e.projectile_damage * (2 ** ng_plus))
        e.projectile_color = ORANGE
        e.projectile_pattern = 'breath'
        e.data['summon_thresholds'] = {0.7: False, 0.4: False}
    elif name == "Zasu (Demon King)":  # Boss 10: summon allies at 80/60/40/20 and revive once
        e.data['summon_thresholds'] = {0.8: False, 0.6: False, 0.4: False, 0.2: False}
        e.revived_once = False
    enemies = [e]
    if name == "Rox and Tox":
        # Rox is the bigger twin (already created as 'e')
        e.name = "Rox (Big Twin)"
        # add Tox, the smaller twin
        x2, y2 = random_free_spot(size-10, obstacles)
        twin_hp = base_hp - 80
        twin_dmg = base_dmg - 2
        # Note: base_hp and base_dmg already have NG+ scaling applied above
        e2 = Enemy(x=x2, y=y2, w=size-10, h=size-10, hp=twin_hp, max_hp=twin_hp, color=color, name="Tox (Small Twin)", speed=base_speed+0.2, damage=twin_dmg)
        e2.data['twin_buff_on_death'] = True
        e2.data['summon_thresholds'] = {0.6: False, 0.3: False}
        enemies.append(e2)
    return enemies

# -------------------------
# Combat and collisions
# -------------------------

def entity_hit_player(e: Enemy, p: Player, dt):
    if e.hp <= 0:
        return
    if p.invuln_timer > 0:
        return
    if e.rect().colliderect(p.rect()):
        # Armor absorbs hits first
        if p.armor_hits_remaining > 0:
            p.armor_hits_remaining -= 1
        else:
            p.hp -= e.damage
        p.invuln_timer = INVULN_TIME
        # Apply on-hit status effects from enemy (e.g., bleed, no-heal burn)
        if e.on_hit_effect == 'bleed':
            p.bleed_time_left = max(p.bleed_time_left, e.on_hit_effect_duration)
            p.bleed_dps = max(p.bleed_dps, e.on_hit_effect_value)
        if e.on_hit_effect == 'no_heal':
            p.no_heal_time_left = max(p.no_heal_time_left, e.on_hit_effect_duration)


def projectile_hits(enemies: List[Enemy], projs: List[Projectile], player: Player, obstacles: List["Obstacle"]):
    remove = []
    for i, pr in enumerate(projs):
        pr.update()
        # obstacle collision
        if collides_rect(pygame.Rect(int(pr.x - pr.radius), int(pr.y - pr.radius), pr.radius*2, pr.radius*2), obstacles):
            remove.append(i)
            continue
        if pr.x < 0 or pr.x > WIDTH or pr.y < 0 or pr.y > HEIGHT:
            remove.append(i)
            continue
        if pr.from_player:
            for e in enemies:
                if e.hp <= 0: continue
                if e.rect().collidepoint(pr.pos()):
                    e.hp -= pr.damage
                    e.invuln_timer = INVULN_TIME
                    # Mark last hit time
                    if hasattr(e, 'last_hit_time'):
                        e.last_hit_time = time.time()
                    if hasattr(e, 'data'):
                        e.data['last_hit_by_sword'] = False
                    remove.append(i)
                    break
        else:
            # Check collision with player
            if player.rect().collidepoint(pr.pos()) and player.invuln_timer <= 0:
                player.hp -= pr.damage
                player.invuln_timer = INVULN_TIME
                # Apply projectile effects to player
                if pr.effect == 'bleed':
                    player.bleed_time_left = max(player.bleed_time_left, pr.effect_duration)
                    player.bleed_dps = max(player.bleed_dps, pr.effect_value)
                elif pr.effect == 'no_heal':
                    player.no_heal_time_left = max(player.no_heal_time_left, pr.effect_duration)
                remove.append(i)
    for i in reversed(sorted(set(remove))):
        del projs[i]

# -------------------------
# XP / Gold / Level up / Shop
# -------------------------

def drop_rewards(state: GameState, is_boss: bool, stage: int, boss_name: str = None):
    px, py = state.player.center()
    x = int(px + random.randint(-40, 40))
    y = int(py + random.randint(-40, 40))
    if is_boss:
        # Use individual boss rewards if boss name is provided
        if boss_name and boss_name in BOSS_REWARDS:
            rewards = BOSS_REWARDS[boss_name]
            exp = random.randint(*rewards["exp"])
            gold = random.randint(*rewards["gold"])
        else:
            # Fallback to old system if boss name not found - Gold reduced by 25%
            if stage <= 5:
                gold = random.randint(14, 30)  # Reduced from (18, 40)
                exp = random.randint(13, 33)
            elif stage <= 10:
                gold = random.randint(34, 51)  # Reduced from (45, 68)
                exp = random.randint(35, 55)
            else:
                exp = random.randint(65, 80)
                gold = random.randint(60, 83)  # Reduced from (80, 110)
        drop_health = random.random() < HEALTH_DROP_CHANCE_BOSS
    else:
        # Use bonus stage rewards for minions
        if stage <= 5:
            gold = random.randint(*BONUS_STAGE_1_5_GOLD)
            exp = random.randint(*BONUS_STAGE_1_5_EXP)
        else:
            gold = random.randint(*BONUS_STAGE_6_10_GOLD)
            exp = random.randint(*BONUS_STAGE_6_10_EXP)
        drop_health = random.random() < HEALTH_DROP_CHANCE_MINION
    # store pickups: gold, exp, optional heal
    state.drops.append((x, y, 'gold', gold))
    state.drops.append((x+10, y, 'exp', exp))
    if drop_health:
        heal_amt = random.randint(*HEALTH_DROP_AMOUNT_RANGE)
        state.drops.append((x+5, y-12, 'heal', heal_amt))


def get_exp_needed_for_level(level: int) -> int:
    """Calculate EXP needed for next level. Doubles every 5 levels."""
    base_exp = 20
    # Every 5 levels, double the requirement
    multiplier = 2 ** (level // 5)
    return base_exp * multiplier

def check_pickups(state: GameState):
    p = state.player
    new = []
    for (x, y, kind, amount) in state.drops:
        if pygame.Rect(x-6, y-6, 12, 12).colliderect(p.rect()):
            if kind == 'gold':
                p.gold += amount
                state.floating_message(f"+{amount} gold")
            elif kind == 'exp':
                p.exp += amount
                state.floating_message(f"+{amount} exp")
                # Level up with scaling EXP requirements - automatic stat increases
                exp_needed = get_exp_needed_for_level(p.level)
                while p.exp >= exp_needed:
                    p.exp -= exp_needed
                    p.level += 1
                    # Automatic stat increase in sequence: Attack → Magic → Health → Mana
                    stat_cycle = ["Attack", "Magic", "Health", "Mana"]
                    stat_to_increase = stat_cycle[(p.level - 1) % 4]
                    apply_levelup_choice(p, stat_to_increase)
                    state.floating_message(f"Level {p.level}! +{stat_to_increase}")
                    exp_needed = get_exp_needed_for_level(p.level)
            elif kind == 'heal':
                old = p.hp
                p.hp = min(p.max_hp, p.hp + amount)
                healed = p.hp - old
                if healed > 0:
                    state.message(f"+{healed} HP")
            continue
        new.append((x, y, kind, amount))
    state.drops = new


def apply_levelup_choice(player: Player, choice: str):
    if choice == "Attack":
        player.atk = int(player.atk * (1 + LEVEL_UP_INCREASE_PERCENT))
    elif choice == "Magic":
        player.mag = int(player.mag * (1 + LEVEL_UP_INCREASE_PERCENT))
    elif choice == "Health":
        old_max_hp = player.max_hp
        player.max_hp = int(player.max_hp * (1 + LEVEL_UP_INCREASE_PERCENT))
        hp_increase = player.max_hp - old_max_hp
        player.hp = min(player.max_hp, player.hp + hp_increase)
    elif choice == "Mana":
        old_max_mana = player.max_mana
        player.max_mana = int(player.max_mana * (1 + LEVEL_UP_INCREASE_PERCENT))
        mana_increase = player.max_mana - old_max_mana
        player.mana = min(player.max_mana, player.mana + mana_increase)


def replenish_armor(player: Player):
    """Replenish armor hits to full if player has armor equipped"""
    if player.armor_id != "none":
        armor = get_armor(player)
        player.armor_hits_remaining = armor["hits"]

def has_god_equipment(player: Player):
    """Check if player has both god sword and god armor"""
    return player.weapon_id == "god_sword" and player.armor_id == "god"

def in_safe_area_setup(state: GameState):
    state.in_safe_area = True
    state.enemies.clear()
    state.projectiles.clear()
    state.wave = 0
    state.player.x, state.player.y = WIDTH//2 - 16, HEIGHT - 120
    # Replenish armor when entering safe area (before boss levels)
    replenish_armor(state.player)


def leave_safe_area(state: GameState):
    state.in_safe_area = False
    state.wave = 1
    state.enemies = []
    # start wave spawn after short cooldown
    state.wave_cooldown = 0.5
    state.pending_spawn = True


def try_buy_weapon(player: Player, key: str) -> bool:
    if key not in WEAPONS:
        return False
    w = WEAPONS[key]
    if player.gold < w["price"]:
        return False
    # Purchase: replace current weapon
    player.gold -= w["price"]
    player.weapon_id = key
    return True


def try_buy_armor(player: Player, key: str) -> bool:
    if key not in ARMORS:
        return False
    a = ARMORS[key]
    if player.gold < a["price"]:
        return False
    # Purchase: replace and reset armor hits
    player.gold -= a["price"]
    player.armor_id = key
    player.armor_hits_remaining = a["hits"]
    return True

# -------------------------
# Rendering
# -------------------------

def draw_player(surface, p: Player):
    pygame.draw.rect(surface, p.color, p.rect())
    # simple sword indicator
    pygame.draw.circle(surface, YELLOW, (int(p.x + p.w/2), int(p.y)), 4)
    # armor outline effect if armor equipped
    if p.armor_id != "none":
        pygame.draw.rect(surface, (200, 200, 255), p.rect(), 2)


def draw_enemy(surface, e: Enemy, state=None):
    # Use sprites if available
    if e.name == "Imp" and state and state.imp_sprites:
        # Animate between the two sprites (switch every 0.5 seconds)
        sprite_index = int(e.anim_timer * 2) % len(state.imp_sprites)
        sprite = state.imp_sprites[sprite_index]
        surface.blit(sprite, (e.x, e.y))
    elif e.name == "Bee" and state and state.bee_sprites:
        # Use bee sprite
        sprite = state.bee_sprites[0]
        surface.blit(sprite, (e.x, e.y))
    elif e.name == "Fly" and state and state.fly_sprites:
        # Use fly sprite
        sprite = state.fly_sprites[0]
        surface.blit(sprite, (e.x, e.y))
    else:
        # Default rectangle drawing for other enemies
        pygame.draw.rect(surface, e.color, e.rect())
    
    # HP bar
    ratio = e.hp / max(1, e.max_hp)
    draw_bar(surface, e.x, e.y - 8, e.w, 6, ratio, RED)
    
    # Display boss name above boss enemies
    boss_names = ["Ba'al (The Insect King)", "Trefyr Herahid (The Dark Elf)", "Viscardi (Vampire Lord)", "Rox (Big Twin)", "Tox (Small Twin)", "Thilreriltic (Lesser Demon Prince)", 
                  "Gorzak (Fire Giant Mage)", "Dram'zuku (The Undead King)", "Alhazred (Pack Leader)", "Noaghoirth, Destroyer of Men", 
                  "Zasu (Demon King)", "Shyssa (Demon Queen)"]
    if e.name in boss_names:
        font = pygame.font.SysFont("Arial", 16, bold=True)
        name_surface = font.render(e.name, True, WHITE)
        name_x = e.x + e.w//2 - name_surface.get_width()//2
        name_y = e.y - 30
        surface.blit(name_surface, (name_x, name_y))


def draw_pickups(surface, drops):
    for (x, y, kind, amount) in drops:
        if kind == 'gold':
            c = YELLOW
        elif kind == 'exp':
            c = PURPLE
        elif kind == 'heal':
            c = GREEN
        else:
            c = WHITE
        pygame.draw.circle(surface, c, (x, y), 6)


def draw_status_effect_icons(surface, player: Player, x_start, y_start):
    """Draw status effect icons in the HUD"""
    icon_size = 24
    icon_spacing = 30
    current_x = x_start
    
    # Bleeding effect - Red droplet icon
    if player.bleed_time_left > 0:
        # Draw red circle with darker red center (blood droplet)
        pygame.draw.circle(surface, (200, 0, 0), (current_x + icon_size//2, y_start + icon_size//2), icon_size//2)
        pygame.draw.circle(surface, (100, 0, 0), (current_x + icon_size//2, y_start + icon_size//2), icon_size//3)
        # Add timer text below
        timer_text = pygame.font.SysFont("Arial", 12).render(f"{player.bleed_time_left:.1f}s", True, WHITE)
        surface.blit(timer_text, (current_x, y_start + icon_size + 2))
        current_x += icon_spacing
    
    # No Heal effect - Purple cross with X
    if player.no_heal_time_left > 0:
        # Draw purple square background
        pygame.draw.rect(surface, (128, 0, 128), (current_x, y_start, icon_size, icon_size))
        # Draw white cross
        pygame.draw.line(surface, WHITE, (current_x + 6, y_start + icon_size//2), (current_x + icon_size - 6, y_start + icon_size//2), 3)
        pygame.draw.line(surface, WHITE, (current_x + icon_size//2, y_start + 6), (current_x + icon_size//2, y_start + icon_size - 6), 3)
        # Draw red X over it
        pygame.draw.line(surface, RED, (current_x + 4, y_start + 4), (current_x + icon_size - 4, y_start + icon_size - 4), 2)
        pygame.draw.line(surface, RED, (current_x + icon_size - 4, y_start + 4), (current_x + 4, y_start + icon_size - 4), 2)
        # Add timer text below
        timer_text = pygame.font.SysFont("Arial", 12).render(f"{player.no_heal_time_left:.1f}s", True, WHITE)
        surface.blit(timer_text, (current_x, y_start + icon_size + 2))
        current_x += icon_spacing
    
    # Invulnerability effect - Golden shield
    if player.invuln_timer > 0:
        # Draw golden shield shape
        shield_points = [
            (current_x + icon_size//2, y_start + 2),  # Top
            (current_x + icon_size - 2, y_start + icon_size//3),  # Top right
            (current_x + icon_size - 2, y_start + 2*icon_size//3),  # Bottom right
            (current_x + icon_size//2, y_start + icon_size - 2),  # Bottom
            (current_x + 2, y_start + 2*icon_size//3),  # Bottom left
            (current_x + 2, y_start + icon_size//3),  # Top left
        ]
        pygame.draw.polygon(surface, (255, 215, 0), shield_points)  # Gold
        pygame.draw.polygon(surface, (200, 170, 0), shield_points, 2)  # Darker gold border
        # Add timer text below
        timer_text = pygame.font.SysFont("Arial", 12).render(f"{player.invuln_timer:.1f}s", True, WHITE)
        surface.blit(timer_text, (current_x, y_start + icon_size + 2))
        current_x += icon_spacing


def draw_hud(surface, font_small, player: Player, state: GameState):
    # Create bold font for HUD
    font_bold = pygame.font.SysFont("Arial", 20, bold=True)
    
    # Wave countdown at top center (bold)
    if not state.in_safe_area and state.wave_cooldown > 0:
        countdown_text = font_bold.render(f"Next Wave in: {int(state.wave_cooldown + 1)}", True, YELLOW)
        surface.blit(countdown_text, (WIDTH//2 - countdown_text.get_width()//2, 10))
    
    # HP/Mana bars
    draw_bar(surface, 20, 20, 220, 16, player.hp / max(1, player.max_hp), RED)
    draw_bar(surface, 20, 40, 220, 16, player.mana / max(1, player.max_mana), BLUE)
    
    # Status effect icons (below mana bar)
    draw_status_effect_icons(surface, player, 20, 60)

    # Equipment info (left side, below status icons) - bold text
    wpn = get_weapon(player)
    arm = get_armor(player)
    
    # Armor display - show "Broken" if no hits remaining, otherwise show armor name
    armor_display = "Broken" if player.armor_hits_remaining <= 0 else arm['label']
    
    weapon_txt = font_bold.render(f"Weapon: {wpn['label']}", True, WHITE)
    surface.blit(weapon_txt, (20, 104))  # Moved down to make room for status icons
    armor_txt = font_bold.render(f"Armor: {armor_display}", True, WHITE)
    surface.blit(armor_txt, (20, 126))  # Moved down to make room for status icons

    # Gold, EXP, Level (top right, next to HP/Mana bars) - bold text
    exp_needed = get_exp_needed_for_level(player.level)
    
    # Create colored text for gold (gold color), exp (RGB), and level (purple)
    gold_color = (255, 215, 0)  # Gold color
    exp_color = (255, 0, 255)   # Magenta/RGB color  
    level_color = (128, 0, 128) # Purple color
    
    gold_txt = font_bold.render(f"Gold: {player.gold}", True, gold_color)
    exp_txt = font_bold.render(f"EXP: {player.exp}/{exp_needed}", True, exp_color)
    level_txt = font_bold.render(f"Lv: {player.level}", True, level_color)
    
    # Position these to the right of the HP/Mana bars
    surface.blit(gold_txt, (260, 20))
    surface.blit(exp_txt, (260, 40))
    surface.blit(level_txt, (260, 60))

    # Game info (stage, wave, time, score) - bold text
    time_secs = int(state.play_time)
    mins = time_secs // 60
    secs = time_secs % 60
    game_info = font_bold.render(
        f"Stage: {state.stage}  Wave: {state.wave if not state.in_safe_area else 'Safe'}  Time: {mins:02d}:{secs:02d}  Score: {state.score}",
        True, WHITE)
    surface.blit(game_info, (20, 148))  # Moved down to make room for equipment info



    if state.info_timer > 0 and state.info_message:
        msg = font_bold.render(state.info_message, True, WHITE)
        surface.blit(msg, (WIDTH//2 - msg.get_width()//2, 35))
    
    # Draw floating messages that follow player
    for text, timer, offset_x, offset_y in state.floating_messages:
        alpha = min(255, int(timer * 255))  # Fade out
        color = (255, 255, 255, alpha) if "gold" in text.lower() else (255, 255, 0, alpha)
        if "gold" in text.lower():
            color = (255, 215, 0)  # Gold color for gold pickups
        elif "exp" in text.lower():
            color = (255, 0, 255)  # Magenta for exp pickups
        else:
            color = (255, 255, 255)  # White for other messages
            
        msg_surface = font_bold.render(text, True, color)
        x = player.x + player.w//2 + offset_x - msg_surface.get_width()//2
        y = player.y + offset_y
        surface.blit(msg_surface, (x, y))


def draw_stats_page(surface, font_small, player: Player, state: GameState):
    """Draw the stats page overlay"""
    # Create semi-transparent background
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))
    
    # Create fonts
    font_title = pygame.font.SysFont("Arial", 32, bold=True)
    font_header = pygame.font.SysFont("Arial", 24, bold=True)
    font_stat = pygame.font.SysFont("Arial", 18)
    font_small_stat = pygame.font.SysFont("Arial", 16)
    
    # Get equipment data
    weapon = get_weapon(player)
    armor = get_armor(player)
    
    # Title
    title = font_title.render("PLAYER STATS", True, WHITE)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 30))
    
    # Left Column - Basic Stats
    left_x = 80
    y_offset = 90
    
    basic_header = font_header.render("Basic Stats", True, YELLOW)
    surface.blit(basic_header, (left_x, y_offset))
    y_offset += 35
    
    # Calculate effective damage values
    base_sword_damage = max(1, player.atk + weapon['dmg'])
    effective_sword_damage = int(base_sword_damage * weapon['mult'])
    effective_magic_damage = player.mag
    effective_sword_range = BASE_SWORD_RANGE + weapon['range']
    
    # Calculate stat increases from base values
    atk_increase = player.atk - PLAYER_BASE_ATK
    mag_increase = player.mag - PLAYER_BASE_MAG
    mana_increase = player.max_mana - PLAYER_BASE_MANA
    hp_increase = player.max_hp - PLAYER_BASE_HP
    
    # Player stats
    stats_text = [
        f"Health: {player.hp}/{player.max_hp}" + (f" (+{hp_increase})" if hp_increase > 0 else ""),
        f"Mana: {player.mana:.1f}/{player.max_mana:.1f}" + (f" (+{mana_increase})" if mana_increase > 0 else ""),
        f"Base Attack: {player.atk:.1f}" + (f" (+{atk_increase})" if atk_increase > 0 else ""),
        f"Base Magic: {player.mag:.1f}" + (f" (+{mag_increase})" if mag_increase > 0 else ""),
        f"Speed: {player.spd:.1f}",
        f"Level: {player.level}",
        f"Experience: {player.exp}/{get_exp_needed_for_level(player.level)}",
        f"Gold: {player.gold}"
    ]
    
    for stat in stats_text:
        stat_surface = font_stat.render(stat, True, WHITE)
        surface.blit(stat_surface, (left_x + 20, y_offset))
        y_offset += 22
    
    # Combat Stats Section
    y_offset += 15
    combat_header = font_header.render("Combat Stats", True, YELLOW)
    surface.blit(combat_header, (left_x, y_offset))
    y_offset += 35
    
    combat_stats = [
        f"Sword Damage: {effective_sword_damage:.1f}",
        f"Sword Range: {effective_sword_range:.1f}",
        f"Magic Damage: {effective_magic_damage:.1f}",
        f"Magic Cost: {MAGIC_MANA_COST:.1f} mana",
        f"Dash Cost: {DASH_MANA_COST:.1f} mana"
    ]
    
    for stat in combat_stats:
        stat_surface = font_stat.render(stat, True, CYAN)
        surface.blit(stat_surface, (left_x + 20, y_offset))
        y_offset += 22
    
    # Status Effects Section
    y_offset += 15
    status_header = font_header.render("Status Effects", True, YELLOW)
    surface.blit(status_header, (left_x, y_offset))
    y_offset += 35
    
    # Check for active status effects
    status_effects = []
    if player.bleed_time_left > 0:
        status_effects.append(f"Bleeding: {player.bleed_time_left:.1f}s ({player.bleed_dps:.1f} DPS)")
    if player.no_heal_time_left > 0:
        status_effects.append(f"No Heal: {player.no_heal_time_left:.1f}s")
    if player.invuln_timer > 0:
        status_effects.append(f"Invulnerable: {player.invuln_timer:.1f}s")
    
    if status_effects:
        for effect in status_effects:
            effect_surface = font_stat.render(effect, True, RED)
            surface.blit(effect_surface, (left_x + 20, y_offset))
            y_offset += 22
    else:
        no_effects = font_stat.render("None", True, GREEN)
        surface.blit(no_effects, (left_x + 20, y_offset))
    
    # Right Column - Equipment
    right_x = WIDTH // 2 + 40
    y_offset = 90
    
    equipment_header = font_header.render("Equipment", True, YELLOW)
    surface.blit(equipment_header, (right_x, y_offset))
    y_offset += 35
    
    # Weapon info
    weapon_text = font_stat.render(f"Weapon: {weapon['label']}", True, WHITE)
    surface.blit(weapon_text, (right_x + 20, y_offset))
    y_offset += 25
    
    weapon_stats = [
        f"  Damage Bonus: +{weapon['dmg']}",
        f"  Range Bonus: +{weapon['range']}",
        f"  Damage Multiplier: {weapon['mult']:.1f}x",
        f"  Cost: {weapon['price']} gold"
    ]
    
    for stat in weapon_stats:
        stat_surface = font_small_stat.render(stat, True, (200, 200, 200))
        surface.blit(stat_surface, (right_x + 20, y_offset))
        y_offset += 18
    
    y_offset += 15
    
    # Armor info
    armor_display = "Broken" if player.armor_hits_remaining <= 0 else armor['label']
    armor_color = RED if player.armor_hits_remaining <= 0 else WHITE
    armor_text = font_stat.render(f"Armor: {armor_display}", True, armor_color)
    surface.blit(armor_text, (right_x + 20, y_offset))
    y_offset += 25
    
    if player.armor_hits_remaining > 0:
        armor_stats = [
            f"  Max Hits: {armor['hits']}",
            f"  Hits Remaining: {player.armor_hits_remaining}/{armor['hits']}",
            f"  Cost: {armor['price']} gold"
        ]
        
        for stat in armor_stats:
            stat_surface = font_small_stat.render(stat, True, (200, 200, 200))
            surface.blit(stat_surface, (right_x + 20, y_offset))
            y_offset += 18
    else:
        broken_text = font_small_stat.render("  Armor is broken!", True, RED)
        surface.blit(broken_text, (right_x + 20, y_offset))
    
    # Game Progress Section
    y_offset += 30
    progress_header = font_header.render("Game Progress", True, YELLOW)
    surface.blit(progress_header, (right_x, y_offset))
    y_offset += 35
    
    progress_stats = [
        f"Current Stage: {state.stage}",
        f"Current Wave: {state.wave}",
        f"In Safe Area: {'Yes' if state.in_safe_area else 'No'}"
    ]
    
    for stat in progress_stats:
        stat_surface = font_stat.render(stat, True, WHITE)
        surface.blit(stat_surface, (right_x + 20, y_offset))
        y_offset += 22
    
    # Instructions
    instruction = font_stat.render("Press TAB to close", True, YELLOW)
    surface.blit(instruction, (WIDTH//2 - instruction.get_width()//2, HEIGHT - 40))


def draw_stage_banner(surface, font_big, text):
    banner = font_big.render(text, True, WHITE)
    surface.blit(banner, (WIDTH//2 - banner.get_width()//2, 120))


def load_imp_sprites():
    """Load imp sprites and remove background"""
    sprites = []
    try:
        # Load both imp images
        for filename in ["imp.jpeg", "imp1.jpeg"]:
            # Get the full path to the image file
            image_path = os.path.join(os.path.dirname(__file__), filename)
            # Load the image
            image = pygame.image.load(image_path)
            
            # Convert to a format that supports per-pixel alpha
            image = image.convert_alpha()
            
            # Scale to appropriate size (32x32 to match enemy size)
            image = pygame.transform.scale(image, (32, 32))
            
            # Remove background by making white/light colors transparent
            # This assumes the background is white or light colored
            for x in range(image.get_width()):
                for y in range(image.get_height()):
                    r, g, b, a = image.get_at((x, y))
                    # If the pixel is very light (likely background), make it transparent
                    # More selective: only pure white or very close to white
                    if r > 240 and g > 240 and b > 240:
                        image.set_at((x, y), (r, g, b, 0))  # Set alpha to 0 (transparent)
            
            sprites.append(image)
    except Exception as e:
        print(f"Could not load imp sprites: {e}")
        # Return empty list if loading fails
        return []
    
    return sprites


def load_bee_sprites():
    """Load bee sprites and remove background"""
    sprites = []
    try:
        # Load bee image
        filename = "evil-bee.png"
        # Get the full path to the image file
        image_path = os.path.join(os.path.dirname(__file__), filename)
        # Load the image
        image = pygame.image.load(image_path)
        
        # Convert to a format that supports per-pixel alpha
        image = image.convert_alpha()
        
        # Scale to appropriate size (40x40 to double bee enemy size)
        image = pygame.transform.scale(image, (40, 40))
        
        # Remove background by making white/light colors transparent
        for x in range(image.get_width()):
            for y in range(image.get_height()):
                r, g, b, a = image.get_at((x, y))
                # If the pixel is very light (likely background), make it transparent
                if r > 240 and g > 240 and b > 240:
                    image.set_at((x, y), (r, g, b, 0))  # Set alpha to 0 (transparent)
        
        sprites.append(image)
    except Exception as e:
        print(f"Could not load bee sprites: {e}")
        # Return empty list if loading fails
        return []
    
    return sprites


def load_fly_sprites():
    """Load fly sprites and remove background"""
    sprites = []
    try:
        # Load fly image
        filename = "evil-fly.png"
        # Get the full path to the image file
        image_path = os.path.join(os.path.dirname(__file__), filename)
        # Load the image
        image = pygame.image.load(image_path)
        
        # Convert to a format that supports per-pixel alpha
        image = image.convert_alpha()
        
        # Scale to appropriate size (32x32 to double fly enemy size)
        image = pygame.transform.scale(image, (32, 32))
        
        # Remove background by making white/light colors transparent
        for x in range(image.get_width()):
            for y in range(image.get_height()):
                r, g, b, a = image.get_at((x, y))
                # If the pixel is very light (likely background), make it transparent
                if r > 240 and g > 240 and b > 240:
                    image.set_at((x, y), (r, g, b, 0))  # Set alpha to 0 (transparent)
        
        sprites.append(image)
    except Exception as e:
        print(f"Could not load fly sprites: {e}")
        # Return empty list if loading fails
        return []
    
    return sprites

# -------------------------
# Main Loop
# -------------------------

def main():
    pygame.init()
    
    # Initialize state first to load settings
    state = GameState()
    
    # Try to load saved settings only (not game state)
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Only load settings, not game state
                settings = data.get("settings", {})
                state.volume = settings.get("volume", 0.6)
                state.fullscreen = settings.get("fullscreen", False)
                state.sound_enabled = settings.get("sound_enabled", True)
                state.music_enabled = settings.get("music_enabled", True)
                state.music_volume = settings.get("music_volume", 0.5)
                state.sfx_volume = settings.get("sfx_volume", 0.7)
    except Exception:
        pass
    
    # Set up display based on settings
    if state.fullscreen:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Sword & Magic")
    clock = pygame.time.Clock()

    # Audio mixer
    try:
        pygame.mixer.init()
    except Exception:
        pass
    font_big = pygame.font.SysFont(FONT_NAME, 36, bold=True)
    font_small = pygame.font.SysFont(FONT_NAME, 20)
    font_small_bold = pygame.font.SysFont(FONT_NAME, 20, bold=True)
    state.font_big = font_big
    state.font_small = font_small

    # Load sprites
    state.imp_sprites = load_imp_sprites()
    state.bee_sprites = load_bee_sprites()
    state.fly_sprites = load_fly_sprites()

    # Load sounds (placeholders if missing)
    snd_dir = os.path.join(os.path.dirname(__file__), 'sounds')
    def load_sound(name):
        path = os.path.join(snd_dir, name)
        if os.path.exists(path):
            try:
                return pygame.mixer.Sound(path)
            except Exception:
                return None
        return None
    state.sounds = {
        'swing': load_sound('swing.wav'),
        'fireball': load_sound('fireball.wav'),
        'imp_die': load_sound('imp_die.wav'),
        'undead_die': load_sound('undead_die.wav'),
        'boss_explode': load_sound('boss_explode.wav'),
        'menu_move': load_sound('menu_move.wav'),
        'menu_tick': load_sound('menu_tick.wav'),
        'menu_confirm': load_sound('menu_confirm.wav'),
        'menu_back': load_sound('menu_back.wav'),
    }
    
    # Apply loaded audio settings
    apply_audio_settings(state)

    # Obstacles for arena (regenerated each stage)
    obstacles: List[Obstacle] = []

    # Merchant (will be set up when entering safe area)
    merchant_rect = pygame.Rect(WIDTH//2 - 40, 160, 80, 80)
    merchant = Merchant(x=merchant_rect.x+16, y=merchant_rect.y+16, w=48, h=48, hp=1, max_hp=1, color=(200, 200, 80), name="Merchant")

    last_attack = 0
    last_magic = 0

    while True:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # autosave
                try:
                    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(state.serialize(), f)
                except Exception:
                    pass
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                # Pause: open menu
                if event.key == pygame.K_p:
                    state.paused = True
                    state.menu_page = "pause"
                # Save & Quit from anywhere with Shift+Q (quick)
                if event.key == pygame.K_q and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    try:
                        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                            json.dump(state.serialize(), f)
                    except Exception:
                        pass
                    pygame.quit()
                    sys.exit(0)
                # ESC does nothing (no resume, no load)
                if event.key == pygame.K_ESCAPE:
                    pass
                # F11 toggles fullscreen
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen(state)
                # Tab toggles stats page (only during gameplay)
                if event.key == pygame.K_TAB and not state.in_main_menu and not state.paused:
                    state.show_stats = not state.show_stats

                # Handle main menu navigation and actions
                if state.in_main_menu:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        # Debounce navigation
                        if time.time() - state.menu_last_nav_time >= state.menu_nav_delay:
                            # Determine which lines are selectable for navigation
                            if state.menu_page == "main":
                                selectable = [0, 1, 2, 3, 4, 5]
                            elif state.menu_page == "settings":
                                selectable = [1, 2, 3, 4, 5, 6, 7]  # All settings options + Back
                            else:  # controls
                                if state.controls_expanded:
                                    selectable = [0, 8]  # Controls header and Back
                                else:
                                    selectable = [0, 1]  # Controls header and Back
                            # Move selection up to previous selectable
                            prev = [i for i in selectable if i < state.menu_index]
                            if prev:
                                state.menu_index = prev[-1]
                                snd = state.sounds.get('menu_move')
                                if snd:
                                    snd.play()
                            state.menu_last_nav_time = time.time()
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        # Debounce navigation
                        if time.time() - state.menu_last_nav_time >= state.menu_nav_delay:
                            # Determine which lines are selectable for navigation
                            if state.menu_page == "main":
                                selectable = [0, 1, 2, 3, 4, 5]
                            elif state.menu_page == "settings":
                                selectable = [1, 2, 3, 4, 5, 6, 7]  # All settings options + Back
                            else:  # controls
                                if state.controls_expanded:
                                    selectable = [0, 8]  # Controls header and Back
                                else:
                                    selectable = [0, 1]  # Controls header and Back
                            # Move selection down to next selectable
                            nxt = [i for i in selectable if i > state.menu_index]
                            if nxt:
                                state.menu_index = nxt[0]
                                snd = state.sounds.get('menu_move')
                                if snd:
                                    snd.play()
                            state.menu_last_nav_time = time.time()
                    if event.key == pygame.K_RETURN:
                        # Activate current selection
                        if state.menu_page == "main":
                            if state.menu_index == 0:  # New Game
                                # Reset game state
                                state.in_main_menu = False
                                state.player = Player(
                                    x=WIDTH//2, y=HEIGHT//2, w=20, h=20,
                                    hp=PLAYER_BASE_HP, max_hp=PLAYER_BASE_HP,
                                    mana=PLAYER_BASE_MANA, max_mana=PLAYER_BASE_MANA,
                                    atk=PLAYER_BASE_ATK, mag=PLAYER_BASE_MAG, spd=PLAYER_BASE_SPD,
                                    color=(90,200,120), name="Hero"
                                )
                                # Clear enemies and projectiles
                                state.enemies = []
                                state.projectiles = []
                                state.pickups = []
                                state.floating_messages = []
                                # Setup safe area
                                in_safe_area_setup(state)
                                state.message("Welcome! Near Merchant: Q=Weapon, E=Armor. P=Pause Menu (P to Resume)", 4)
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 1:  # Continue
                                # Try to load saved game
                                try:
                                    with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                    state.deserialize(data)
                                    state.in_main_menu = False
                                    snd = state.sounds.get('menu_confirm')
                                    if snd:
                                        snd.play()
                                except Exception:
                                    state.message("No save file found!", 2)
                            elif state.menu_index == 2:  # Settings
                                state.menu_page = "settings"
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 3:  # Controls
                                state.menu_page = "controls"
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 4:  # Quit Game
                                pygame.quit()
                                sys.exit(0)
                        elif state.menu_page == "settings":
                            if state.menu_index == 1:  # Fullscreen toggle
                                screen = toggle_fullscreen(state)
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 3:  # Sound toggle
                                state.sound_enabled = not state.sound_enabled
                                apply_audio_settings(state)
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 5:  # Music toggle
                                state.music_enabled = not state.music_enabled
                                apply_audio_settings(state)
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 7:  # Back
                                state.menu_page = "main"
                                state.menu_index = 0
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                        elif state.menu_page == "controls":
                            if state.menu_index == 0:  # Controls header - toggle expansion
                                state.controls_expanded = not state.controls_expanded
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif (state.controls_expanded and state.menu_index == 8) or (not state.controls_expanded and state.menu_index == 1):  # Back
                                state.menu_page = "main"
                                state.menu_index = 0
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 4:  # Back
                                state.menu_page = "main"
                                state.menu_index = 1  # Go back to main menu
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                    # Volume controls for main menu settings
                    if state.menu_page == "settings":
                        # Master Volume
                        if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_RIGHT) and state.menu_index == 2:
                            state.volume = min(1.0, state.volume + 0.1)
                            apply_audio_settings(state)
                        if event.key in (pygame.K_MINUS, pygame.K_LEFT) and state.menu_index == 2:
                            state.volume = max(0.0, state.volume - 0.1)
                            apply_audio_settings(state)
                        # SFX Volume
                        if event.key == pygame.K_d and state.menu_index == 4:
                            state.sfx_volume = min(1.0, state.sfx_volume + 0.1)
                            apply_audio_settings(state)
                        if event.key == pygame.K_a and state.menu_index == 4:
                            state.sfx_volume = max(0.0, state.sfx_volume - 0.1)
                            apply_audio_settings(state)
                        # Music Volume
                        if event.key == pygame.K_e and state.menu_index == 6:
                            state.music_volume = min(1.0, state.music_volume + 0.1)
                            apply_audio_settings(state)
                        if event.key == pygame.K_q and state.menu_index == 6:
                            state.music_volume = max(0.0, state.music_volume - 0.1)
                            apply_audio_settings(state)

                # Handle pause menu navigation and actions
                elif state.paused:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        # Debounce navigation
                        if time.time() - state.menu_last_nav_time >= state.menu_nav_delay:
                            # Determine which lines are selectable for navigation
                            if state.menu_page == "pause":
                                selectable = [0, 1, 2, 3, 4]
                            elif state.menu_page == "settings":
                                selectable = [1, 2, 3, 4, 5, 6, 7]  # All settings options + Back
                            else:  # controls
                                if state.controls_expanded:
                                    selectable = [0, 8]  # Controls header and Back
                                else:
                                    selectable = [0, 1]  # Controls header and Back
                            # Move selection up to previous selectable
                            prev = [i for i in selectable if i < state.menu_index]
                            if prev:
                                state.menu_index = prev[-1]
                                snd = state.sounds.get('menu_move')
                                if snd:
                                    snd.play()
                            state.menu_last_nav_time = time.time()
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        # Debounce navigation
                        if time.time() - state.menu_last_nav_time >= state.menu_nav_delay:
                            # Determine which lines are selectable for navigation
                            if state.menu_page == "pause":
                                selectable = [0, 1, 2, 3, 4]
                            elif state.menu_page == "settings":
                                selectable = [1, 2, 3, 4, 5, 6, 7]  # All settings options + Back
                            else:  # controls
                                if state.controls_expanded:
                                    selectable = [0, 8]  # Controls header and Back
                                else:
                                    selectable = [0, 1]  # Controls header and Back
                            # Move selection down to next selectable
                            nxt = [i for i in selectable if i > state.menu_index]
                            if nxt:
                                state.menu_index = nxt[0]
                                snd = state.sounds.get('menu_move')
                                if snd:
                                    snd.play()
                            state.menu_last_nav_time = time.time()
                    if event.key == pygame.K_RETURN:
                        # Activate current selection
                        if state.menu_page == "pause":
                            if state.menu_index == 0:  # Resume
                                state.paused = False
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 1:  # Settings
                                state.menu_page = "settings"
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 2:  # Controls
                                state.menu_page = "controls"
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 3:  # Return to Main Menu
                                state.paused = False
                                state.in_main_menu = True
                                state.menu_page = "main"
                                state.menu_index = 0
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 4:  # Save & Quit
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                                try:
                                    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                                        json.dump(state.serialize(), f)
                                except Exception:
                                    pass
                                pygame.quit()
                                sys.exit(0)
                        elif state.menu_page == "settings":
                            if state.menu_index == 1:  # Fullscreen toggle
                                screen = toggle_fullscreen(state)
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 3:  # Sound toggle
                                state.sound_enabled = not state.sound_enabled
                                apply_audio_settings(state)
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 5:  # Music toggle
                                state.music_enabled = not state.music_enabled
                                apply_audio_settings(state)
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif state.menu_index == 7:  # Back
                                state.menu_page = "pause"
                                state.menu_index = 0
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                        elif state.menu_page == "controls":
                            if state.menu_index == 0:  # Controls header - toggle expansion
                                state.controls_expanded = not state.controls_expanded
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                            elif (state.controls_expanded and state.menu_index == 8) or (not state.controls_expanded and state.menu_index == 1):  # Back
                                state.menu_page = "pause"
                                state.menu_index = 0
                                snd = state.sounds.get('menu_confirm')
                                if snd:
                                    snd.play()
                    # Volume controls for pause menu settings
                    if state.menu_page == "settings":
                        # Master Volume
                        if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_RIGHT) and state.menu_index == 2:
                            state.volume = min(1.0, state.volume + 0.1)
                            apply_audio_settings(state)
                        if event.key in (pygame.K_MINUS, pygame.K_LEFT) and state.menu_index == 2:
                            state.volume = max(0.0, state.volume - 0.1)
                            apply_audio_settings(state)
                        # SFX Volume
                        if event.key == pygame.K_d and state.menu_index == 4:
                            state.sfx_volume = min(1.0, state.sfx_volume + 0.1)
                            apply_audio_settings(state)
                        if event.key == pygame.K_a and state.menu_index == 4:
                            state.sfx_volume = max(0.0, state.sfx_volume - 0.1)
                            apply_audio_settings(state)
                        # Music Volume
                        if event.key == pygame.K_e and state.menu_index == 6:
                            state.music_volume = min(1.0, state.music_volume + 0.1)
                            apply_audio_settings(state)
                        if event.key == pygame.K_q and state.menu_index == 6:
                            state.music_volume = max(0.0, state.music_volume - 0.1)
                            apply_audio_settings(state)

                # Merchant quick-buy keys (only in safe area and near merchant, and not with god equipment)
                if state.in_safe_area and state.player.rect().colliderect(merchant_rect) and not has_god_equipment(state.player):
                    if event.key == pygame.K_q:  # weapon cycle forward
                        curr_idx = ORDERED_WEAPONS.index(state.player.weapon_id)
                        next_id = ORDERED_WEAPONS[(curr_idx + 1) % len(ORDERED_WEAPONS)]
                        if try_buy_weapon(state.player, next_id):
                            state.message(f"Bought {WEAPONS[next_id]['label']}!")
                        else:
                            state.message("Not enough gold.")
                    if event.key == pygame.K_e:  # armor cycle forward
                        curr_idx = ORDERED_ARMORS.index(state.player.armor_id)
                        next_id = ORDERED_ARMORS[(curr_idx + 1) % len(ORDERED_ARMORS)]
                        if try_buy_armor(state.player, next_id):
                            state.message(f"Bought {ARMORS[next_id]['label']} Armor!")
                        else:
                            state.message("Not enough gold.")

        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pos()
        mb = pygame.mouse.get_pressed()

        # Update message timer
        if state.info_timer > 0:
            state.info_timer -= dt
        
        # Update floating messages
        new_floating = []
        for text, timer, offset_x, offset_y in state.floating_messages:
            timer -= dt
            if timer > 0:
                new_floating.append((text, timer, offset_x, offset_y - dt * 20))  # Float upward
        state.floating_messages = new_floating

        # If in main menu, handle main menu and skip gameplay updates
        if state.in_main_menu:
            screen.fill(BG_COLOR)
            title = font_big.render("Sword & Magic", True, WHITE)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 120))

            if state.menu_page == "main":
                lines = [
                    "New Game",
                    "Continue",
                    "Settings",
                    "Controls",
                    "Quit Game",
                ]
            elif state.menu_page == "settings":
                fullscreen_text = "ON" if state.fullscreen else "OFF"
                sound_text = "ON" if state.sound_enabled else "OFF"
                music_text = "ON" if state.music_enabled else "OFF"
                lines = [
                    "Settings:",
                    f"Fullscreen: {fullscreen_text}  [F11 or Enter to toggle]",
                    f"Master Volume: {int(state.volume*100)}%  [+/- or Left/Right]",
                    f"Sound Effects: {sound_text}  [Enter to toggle]",
                    f"SFX Volume: {int(state.sfx_volume*100)}%  [A/D to adjust]",
                    f"Music: {music_text}  [Enter to toggle]",
                    f"Music Volume: {int(state.music_volume*100)}%  [Q/E to adjust]",
                    "Back",
                ]
            else:  # controls
                if state.controls_expanded:
                    lines = [
                        "Controls: [Enter to collapse]",
                        "Movement: W/A/S/D keys",
                        "Combat: LMB = Slash, F = Magic, L = Dash",
                        "Interaction: E = Interact with Merchant",
                        "Shopping: Q/E = Buy Weapon/Armor at Merchant",
                        "Game: N = Start Stage, P = Pause/Resume",
                        "Display: F11 = Toggle Fullscreen",
                        "Save: Shift+Q = Save & Quit",
                        "Back",
                    ]
                else:
                    lines = [
                        "Controls: [Enter to expand]",
                        "Back",
                    ]

            # Determine which lines are selectable for navigation
            if state.menu_page == "main":
                selectable = [0, 1, 2, 3, 4, 5]
            elif state.menu_page == "settings":
                selectable = [1, 2, 3, 4, 5, 6, 7]  # All settings options + Back

            else:  # controls
                if state.controls_expanded:
                    selectable = [0, 8]  # Controls header and Back
                else:
                    selectable = [0, 1]  # Controls header and Back

            # Ensure current selection is valid
            if state.menu_index not in selectable:
                state.menu_index = selectable[0]

            # Draw lines with highlight and cursor for the selected option
            y = 200
            for i, ln in enumerate(lines):
                is_sel = (i == state.menu_index)
                color = YELLOW if is_sel else WHITE
                label = ("> " + ln) if is_sel else ("  " + ln)
                t = font_small.render(label, True, color)
                screen.blit(t, (WIDTH//2 - t.get_width()//2, y))
                y += 28

            pygame.display.flip()
            continue

        # If paused, handle menu and draw overlay, skip gameplay updates
        elif state.paused:
            # Simple pause menu pages
            screen.fill(BG_COLOR)
            title = font_big.render("Paused", True, WHITE)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 180))

            if state.menu_page == "pause":
                lines = [
                    "Resume",
                    "Settings", 
                    "Controls",
                    "Return to Main Menu",
                    "Save & Quit",
                ]
            elif state.menu_page == "settings":
                fullscreen_text = "ON" if state.fullscreen else "OFF"
                sound_text = "ON" if state.sound_enabled else "OFF"
                music_text = "ON" if state.music_enabled else "OFF"
                lines = [
                    "Settings:",
                    f"Fullscreen: {fullscreen_text}  [F11 or Enter to toggle]",
                    f"Master Volume: {int(state.volume*100)}%  [+/- or Left/Right]",
                    f"Sound Effects: {sound_text}  [Enter to toggle]",
                    f"SFX Volume: {int(state.sfx_volume*100)}%  [A/D to adjust]",
                    f"Music: {music_text}  [Enter to toggle]",
                    f"Music Volume: {int(state.music_volume*100)}%  [Q/E to adjust]",
                    "Back",
                ]
            else:  # controls
                if state.controls_expanded:
                    lines = [
                        "Controls: [Enter to collapse]",
                        "Movement: W/A/S/D keys",
                        "Combat: LMB = Slash, F = Magic, L = Dash",
                        "Interaction: E = Interact with Merchant",
                        "Shopping: Q/E = Buy Weapon/Armor at Merchant",
                        "Level Up: Automatic (Attack→Magic→Health→Mana)",
                        "Game: N = Start Stage, P = Pause/Resume",
                        "Display: F11 = Toggle Fullscreen",
                        "Save: Shift+Q = Save & Quit",
                        "Back",
                    ]
                else:
                    lines = [
                        "Controls: [Enter to expand]",
                        "Back",
                    ]

            # Determine which lines are selectable for navigation
            if state.menu_page == "pause":
                selectable = [0, 1, 2, 3, 4]
            elif state.menu_page == "settings":
                selectable = [1, 2, 3, 4, 5, 6, 7]  # All settings options + Back
            else:  # controls
                if state.controls_expanded:
                    selectable = [0, 9]  # Controls header and Back
                else:
                    selectable = [0, 1]  # Controls header and Back

            # Ensure current selection is valid
            if state.menu_index not in selectable:
                state.menu_index = selectable[0]

            # Draw lines with highlight and cursor for the selected option
            y = 240
            for i, ln in enumerate(lines):
                is_sel = (i == state.menu_index)
                color = YELLOW if is_sel else WHITE
                label = ("> " + ln) if is_sel else ("  " + ln)
                t = font_small.render(label, True, color)
                screen.blit(t, (WIDTH//2 - t.get_width()//2, y))
                y += 28

            pygame.display.flip()
            continue

        # If paused, handle menu and draw overlay, skip gameplay updates
        elif state.paused:
            # Simple pause menu pages
            screen.fill(BG_COLOR)
            title = font_big.render("Paused", True, WHITE)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 180))

            if state.menu_page == "pause":
                lines = [
                    "Resume",
                    "Settings",
                    "Controls",
                    "Return to Main Menu",
                    "Save & Quit",
                ]
            elif state.menu_page == "settings":
                fullscreen_text = "ON" if state.fullscreen else "OFF"
                sound_text = "ON" if state.sound_enabled else "OFF"
                music_text = "ON" if state.music_enabled else "OFF"
                lines = [
                    "Settings:",
                    f"Fullscreen: {fullscreen_text}  [F11 or Enter to toggle]",
                    f"Master Volume: {int(state.volume*100)}%  [+/- or Left/Right]",
                    f"Sound Effects: {sound_text}  [Enter to toggle]",
                    f"SFX Volume: {int(state.sfx_volume*100)}%  [A/D to adjust]",
                    f"Music: {music_text}  [Enter to toggle]",
                    f"Music Volume: {int(state.music_volume*100)}%  [Q/E to adjust]",
                    "Back",
                ]
            else:  # controls
                if state.controls_expanded:
                    lines = [
                        "Controls: [Enter to collapse]",
                        "Movement: W/A/S/D keys",
                        "Combat: LMB = Slash, F = Magic, L = Dash",
                        "Interaction: E = Interact with Merchant",
                        "Shopping: Q/E = Buy Weapon/Armor at Merchant",
                        "Level Up: Automatic (Attack→Magic→Health→Mana)",
                        "Game: N = Start Stage, P = Pause/Resume",
                        "Display: F11 = Toggle Fullscreen",
                        "Save: Shift+Q = Save & Quit",
                        "Back",
                    ]
                else:
                    lines = [
                        "Controls: [Enter to expand]",
                        "Back",
                    ]

            # Determine which lines are selectable for navigation
            if state.menu_page == "pause":
                selectable = [0, 1, 2, 3, 4]
            elif state.menu_page == "settings":
                selectable = [1, 2, 3, 4, 5, 6, 7]  # All settings options + Back
            else:  # controls
                if state.controls_expanded:
                    selectable = [0, 9]  # Controls header and Back
                else:
                    selectable = [0, 1]  # Controls header and Back

            # Ensure current selection is valid
            if state.menu_index not in selectable:
                state.menu_index = selectable[0]

            # Draw lines with highlight and cursor for the selected option
            y = 240
            for i, ln in enumerate(lines):
                is_sel = (i == state.menu_index)
                color = YELLOW if is_sel else WHITE
                label = ("> " + ln) if is_sel else ("  " + ln)
                t = font_small.render(label, True, color)
                screen.blit(t, (WIDTH//2 - t.get_width()//2, y))
                y += 28

            pygame.display.flip()
            continue

        # Unpaused: accumulate timer (only when not in safe area)
        if not state.in_safe_area:
            state.play_time += dt
        
        # Handle post-boss 10 delay
        if state.post_boss_10_delay > 0:
            state.post_boss_10_delay -= dt
            if state.post_boss_10_delay <= 0:
                state.message("A portal opens... Shyssa awaits.", 4)

        # Player update
        state.player.invuln_timer = max(0, state.player.invuln_timer - dt)
        # Status effects: bleed and no-heal timers
        if state.player.bleed_time_left > 0:
            state.player.bleed_time_left = max(0.0, state.player.bleed_time_left - dt)
            state.player.bleed_tick_accum += dt
            while state.player.bleed_tick_accum >= 0.5 and state.player.hp > 0:
                state.player.bleed_tick_accum -= 0.5
                # Deal small chunks based on dps
                state.player.hp = max(0, state.player.hp - int(max(1.0, state.player.bleed_dps * 0.5)))
        if state.player.no_heal_time_left > 0:
            state.player.no_heal_time_left = max(0.0, state.player.no_heal_time_left - dt)
        # Move with obstacle collision
        prev_px, prev_py = state.player.x, state.player.y
        state.player.move(keys)
        resolve_entity_collision(state.player, obstacles, prev_px, prev_py)

        # Attacks
        # Sword -> Left mouse click
        if mb[0] and time.time() - last_attack > 0.25:
            if state.player.sword_attack(state.enemies):
                state.message("Slash!")
                # Score for melee hit
                state.score += 1
                # Play swing
                snd = state.sounds.get('swing')
                if snd:
                    snd.play()
            last_attack = time.time()
        # Magic -> F key
        if keys[pygame.K_f] and time.time() - last_magic > 0.35:
            pr = state.player.cast_magic(mouse)
            if pr:
                state.projectiles.append(pr)
                state.message("Cast!")
                # Play fireball
                snd = state.sounds.get('fireball')
                if snd:
                    snd.play()
                last_magic = time.time()
        if keys[pygame.K_l]:
            state.player.dash(mouse)

        # Safe area logic
        if state.in_safe_area:
            # Interact with merchant (Q/E to cycle and buy next item)
            if state.player.rect().colliderect(merchant_rect):
                pass
            # Proceed to next stage
            if state.wave == 0 and keys[pygame.K_n]:
                # Check if we're trying to start secret boss stage but delay isn't over
                if state.stage == SECRET_BOSS_STAGE and state.post_boss_10_delay > 0:
                    state.message(f"Portal still forming... {int(state.post_boss_10_delay + 1)} seconds remaining", 2)
                else:
                    # Record score at start of stage for death reset
                    state.stage_start_score = state.score
                    leave_safe_area(state)
                    # generate obstacles for this stage
                    obstacles = generate_arena_obstacles(state.stage)
                    if state.stage == SECRET_BOSS_STAGE:
                        state.message(f"Secret Boss Stage: The final battle!", 3)
                    else:
                        boss_name = BOSS_LIST[min(state.stage-1, len(BOSS_LIST)-1)][0]
                        state.message(f"Bonus Stage {state.stage} - Stage Clear with boss: {boss_name}", 3)
        else:
            # Combat update: spawn waves, update enemies
            alive = []
            for e in state.enemies:
                prev_x, prev_y = e.x, e.y
                e.update(state.player, obstacles)
                # Shooting behaviors
                if getattr(e, 'shoot_interval', 0.0) > 0.0:
                    e.shoot_timer += dt
                    if e.shoot_timer >= e.shoot_interval:
                        e.shoot_timer -= e.shoot_interval
                        ex, ey = e.x + e.w/2, e.y + e.h/2
                        # Pattern selection
                        if e.projectile_pattern == 'aim':
                            px, py = state.player.x + state.player.w/2, state.player.y + state.player.h/2
                            dx, dy = px - ex, py - ey
                            dist = math.hypot(dx, dy) or 1
                            vx = e.projectile_speed * dx / dist
                            vy = e.projectile_speed * dy / dist
                            state.projectiles.append(Projectile(ex, ey, vx, vy, e.projectile_damage, e.projectile_color, radius=e.projectile_radius, from_player=False, effect=e.projectile_effect, effect_value=e.projectile_effect_value, effect_duration=e.projectile_effect_duration))
                        elif e.projectile_pattern == 'cross4':
                            dirs = [(1,0),(-1,0),(0,1),(0,-1)]
                            for dx, dy in dirs:
                                vx = e.projectile_speed * dx
                                vy = e.projectile_speed * dy
                                state.projectiles.append(Projectile(ex, ey, vx, vy, e.projectile_damage, e.projectile_color, radius=e.projectile_radius, from_player=False, effect=e.projectile_effect, effect_value=e.projectile_effect_value, effect_duration=e.projectile_effect_duration))
                        elif e.projectile_pattern == 'cross8':
                            # 8 directions (4 cardinal + 4 diagonal)
                            dirs = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]
                            for dx, dy in dirs:
                                # Normalize diagonal directions
                                length = math.hypot(dx, dy)
                                vx = e.projectile_speed * dx / length
                                vy = e.projectile_speed * dy / length
                                state.projectiles.append(Projectile(ex, ey, vx, vy, e.projectile_damage, e.projectile_color, radius=e.projectile_radius, from_player=False, effect=e.projectile_effect, effect_value=e.projectile_effect_value, effect_duration=e.projectile_effect_duration))
                        elif e.projectile_pattern == 'breath':
                            # short-range fan aimed at player
                            px, py = state.player.x + state.player.w/2, state.player.y + state.player.h/2
                            dx, dy = px - ex, py - ey
                            base = math.atan2(dy, dx)
                            for ang_off in (-0.4, -0.2, 0, 0.2, 0.4):
                                ang = base + ang_off
                                vx = e.projectile_speed * math.cos(ang)
                                vy = e.projectile_speed * math.sin(ang)
                                state.projectiles.append(Projectile(ex, ey, vx, vy, e.projectile_damage, e.projectile_color, radius=max(6, e.projectile_radius-2), from_player=False, effect=e.projectile_effect, effect_value=e.projectile_effect_value, effect_duration=e.projectile_effect_duration))
                # One-off transitions
                # Boss 5 (Demon Prince) heal to 80% once when low on health
                if 'heal_to_80_percent' in e.data and e.hp <= e.max_hp * 0.2 and not e.data.get('did_heal', False):
                    e.data['did_heal'] = True
                    e.hp = int(e.max_hp * 0.8)
                    state.message("Thilreriltic heals!", 2)
                # Demon King/Queen summon thresholds
                if 'summon_thresholds' in e.data:
                    for frac, done in list(e.data['summon_thresholds'].items()):
                        if not done and e.hp <= e.max_hp * float(frac):
                            e.data['summon_thresholds'][frac] = True
                            # summon helpers
                            count = 3
                            state.enemies.extend(spawn_minion(state.stage, obstacles, state.new_game_plus) for _ in range(count))
                # Enemy special: heal over time if not hit (Lich)
                if getattr(e, 'can_heal', False):
                    last_hit = getattr(e, 'last_hit_time', 0.0)
                    if time.time() - last_hit >= getattr(e, 'heal_delay', 3.0):
                        e.hp = min(e.max_hp, e.hp + e.heal_per_sec * dt)
                # Enemy special: speed double at 50%
                if getattr(e, 'speed_doubles_at_half', False) and not getattr(e, 'sped_up', False):
                    if e.hp <= e.max_hp * 0.5:
                        e.speed *= 2.0
                        e.sped_up = True
                resolve_entity_collision(e, obstacles, prev_x, prev_y)
                
                entity_hit_player(e, state.player, dt)
                if e.hp > 0:
                    alive.append(e)
                else:
                    # Demon King: revive once on death (phase 2)
                    if e.name == 'Zasu (Demon King)' and not getattr(e, 'revived_once', False):
                        e.revived_once = True
                        e.hp = int(e.max_hp * 0.75)
                        e.damage = int(e.damage * 1.2)
                        e.speed += 0.3
                        alive.append(e)
                        continue
                    # Demon Queen: require sword for final blow
                    if e.name == SECRET_BOSS[0] and e.data.get('must_die_by_sword', False):
                        if not e.data.get('last_hit_by_sword', False):
                            # Prevent death; leave at 1 HP
                            e.hp = 1
                            alive.append(e)
                            state.message('The Queen can only be felled by the sword!', 2)
                            continue
                    # Twin Ghouls: buff twin on death
                    if e.name in ["Rox (Big Twin)", "Tox (Small Twin)"]:
                        for oth in state.enemies:
                            if oth is not e and oth.name in ["Rox (Big Twin)", "Tox (Small Twin)"] and oth.hp > 0:
                                oth.damage = int(oth.damage * 1.5)
                                break
                    # drop rewards
                    is_boss = (state.wave == MINION_WAVES_PER_STAGE + 1)
                    # Only drop boss rewards when boss is actually killed
                    if is_boss:
                        drop_rewards(state, True, state.stage, e.name)
                    else:
                        drop_rewards(state, False, state.stage)
                    # Score for kill and death sounds
                    state.score += 10 if is_boss else 3
                    if is_boss:
                        snd = state.sounds.get('boss_explode')
                        if snd:
                            snd.play()
                    else:
                        # choose sound by enemy name
                        if e.name == 'Imp':
                            snd = state.sounds.get('imp_die')
                        elif e.name in ('Skeleton', 'Undead Lich'):
                            snd = state.sounds.get('undead_die')
                        else:
                            snd = None
                        if snd:
                            snd.play()
            state.enemies = alive

            projectile_hits(state.enemies, state.projectiles, state.player, obstacles)

            # Inter-wave cooldown countdown
            if state.pending_spawn and state.wave_cooldown > 0:
                state.wave_cooldown = max(0.0, state.wave_cooldown - dt)

            # Spawn logic with 5s delay between waves
            if not state.enemies:
                if state.wave <= MINION_WAVES_PER_STAGE:
                    if not state.pending_spawn:
                        # just finished a wave; start cooldown and reset armor
                        state.pending_spawn = True
                        state.wave_cooldown = 5.0
                        # regen armor to current armor's hits
                        curr_armor = get_armor(state.player)
                        state.player.armor_hits_remaining = curr_armor["hits"]
                        state.message("Wave cleared. Next wave in 5s.", 2)
                    elif state.wave_cooldown == 0.0:
                        # spawn a wave of minions
                        base_count = 3 + state.stage  # ramp up
                        count = int(base_count * (1.3 ** (state.wave - 1)))  # 30% increase each wave
                        state.enemies = [spawn_minion(state.stage, obstacles, state.new_game_plus) for _ in range(count)]
                        state.wave += 1
                        state.pending_spawn = False
                elif state.wave == MINION_WAVES_PER_STAGE + 1:
                    if not state.pending_spawn:
                        state.pending_spawn = True
                        state.wave_cooldown = 5.0
                        state.message("Final wave cleared. Boss in 5s.", 2)
                    elif state.wave_cooldown == 0.0:
                        # spawn boss
                        state.enemies = spawn_boss(state.stage, obstacles, state.new_game_plus)
                        state.wave += 1
                        state.pending_spawn = False
                else:
                    # Stage clear
                    if state.stage == 10:
                        # Just defeated boss 10, start 20 second delay
                        state.post_boss_10_delay = 20.0
                        state.message("You Are not done yet!!", 3)
                        state.stage += 1
                    elif state.stage == SECRET_BOSS_STAGE:
                        # Secret boss defeated - New Game+
                        state.new_game_plus += 1
                        state.message(f"You have won! Starting New Game+ {state.new_game_plus}...", 4)
                        # Reset to stage 1 but keep player stats and increase difficulty
                        state.stage = 1
                        state.wave = 1
                        # Clear equipment and reopen merchant
                        state.player.weapon_id = "starter"
                        state.player.armor_id = "none"
                        state.player.armor_hits_remaining = 0
                        # Double all enemy health and damage for this NG+ run
                        # This will be handled in spawn functions
                    else:
                        state.stage += 1
                        if state.stage == SECRET_BOSS_STAGE:
                            state.message("A portal opens... Shyssa awaits.", 4)
                    
                    # Replenish armor after boss defeat
                    replenish_armor(state.player)
                    in_safe_area_setup(state)
                    obstacles = []

        # Mana regen slow
        if not state.in_safe_area and random.random() < 0.02:
            state.player.mana = min(state.player.max_mana, state.player.mana + 1)
        
        # Health regen over time (in and out of combat), disabled during no-heal
        if not state.paused:
            state.hp_regen_timer += dt
            if state.hp_regen_timer >= state.hp_regen_interval:
                state.hp_regen_timer -= state.hp_regen_interval
                if state.player.no_heal_time_left <= 0:
                    state.player.hp = min(state.player.max_hp, state.player.hp + state.hp_regen_amount)

        # Pickups
        check_pickups(state)

        # Death check
        if state.player.hp <= 0:
            # Reset score to beginning of stage and lose 50% gold
            state.score = state.stage_start_score
            state.player.gold = int(state.player.gold * 0.5)
            in_safe_area_setup(state)
            state.player.hp = state.player.max_hp
            state.player.mana = state.player.max_mana
            state.message("You fell... Returning to safe area. Lost 50% gold!", 3)

        # Draw
        screen.fill(BG_COLOR)

        if state.in_safe_area:
            # Draw a simple hub and merchant
            pygame.draw.rect(screen, (25, 40, 25), (0, 100, WIDTH, HEIGHT-200))
            pygame.draw.rect(screen, (60, 60, 20), merchant_rect)
            # Draw merchant NPC
            pygame.draw.rect(screen, (40, 40, 10), merchant_rect, 2)
            pygame.draw.rect(screen, merchant.color, merchant.rect())
            if has_god_equipment(state.player):
                label = font_small.render("Merchant: You have achieved ultimate power! | N=Start Stage", True, WHITE)
            else:
                label = font_small.render("Merchant: Q=Buy Next Weapon | E=Buy Next Armor | N=Start Stage", True, WHITE)
            screen.blit(label, (WIDTH//2 - label.get_width()//2, 120))
            if state.player.rect().colliderect(merchant_rect) and not has_god_equipment(state.player):
                # Show next items and prices
                w_idx = ORDERED_WEAPONS.index(state.player.weapon_id)
                a_idx = ORDERED_ARMORS.index(state.player.armor_id)
                next_w = ORDERED_WEAPONS[(w_idx + 1) % len(ORDERED_WEAPONS)]
                next_a = ORDERED_ARMORS[(a_idx + 1) % len(ORDERED_ARMORS)]
                w = WEAPONS[next_w]
                a = ARMORS[next_a]
                hint1 = font_small.render(f"Next Weapon: {w['label']} ({w['price']}g)  Range {w['range']}  +DMG {w['dmg']}  x{w['mult']}", True, YELLOW)
                hint2 = font_small.render(f"Next Armor: {a['label']} ({a['price']}g)  Hits {a['hits']}", True, YELLOW)
                screen.blit(hint1, (WIDTH//2 - hint1.get_width()//2, 145))
                screen.blit(hint2, (WIDTH//2 - hint2.get_width()//2, 165))
        else:
            # Arena
            pygame.draw.rect(screen, (30, 30, 35), (0, 0, WIDTH, HEIGHT))
            draw_obstacles(screen, obstacles)

        draw_player(screen, state.player)
        
        for e in state.enemies:
            draw_enemy(screen, e, state)
        
        for pr in state.projectiles:
            pygame.draw.circle(screen, pr.color, pr.pos(), pr.radius)
        
        draw_pickups(screen, state.drops)
        draw_hud(screen, font_small, state.player, state)
        
        if state.boss_stage and state.boss_banner_timer > 0:
            banner_text = font_large.render("BOSS STAGE", True, RED)
            screen.blit(banner_text, (WIDTH//2 - banner_text.get_width()//2, HEIGHT//2 - 50))
        
        if state.secret_boss_stage and state.boss_banner_timer > 0:
            banner_text = font_large.render("SECRET BOSS", True, PURPLE)
            screen.blit(banner_text, (WIDTH//2 - banner_text.get_width()//2, HEIGHT//2 - 50))
        
        if show_stats:
            draw_stats_page(screen, font_small, state.player)
        
        pygame.display.flip()
