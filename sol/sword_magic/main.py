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

LEVEL_UP_INCREASE = 2
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

# Drops
MINION_GOLD_RANGE = (2, 5)
MINION_EXP_RANGE = (1, 3)
BOSS_1_5_EXP = (10, 50)
BOSS_6_10_EXP = (60, 100)
BOSS_GOLD_RANGE = (25, 50)
SECRET_BOSS_EXP = 150
SECRET_BOSS_GOLD = 50

# Health drops
HEALTH_DROP_CHANCE_MINION = 0.25
HEALTH_DROP_CHANCE_BOSS = 0.5
HEALTH_DROP_AMOUNT_RANGE = (4, 10)

# Shop items and order
WEAPONS = {
    "starter": {"price": 0, "range": 0, "dmg": 0, "mult": 1.0, "label": "Starter"},
    "wood": {"price": 50, "range": 5, "dmg": 0, "mult": 1.0, "label": "Wood Sword"},
    "twin_daggers": {"price": 100, "range": -2, "dmg": 0, "mult": 2.0, "label": "Twin Daggers"},
    "long_sword": {"price": 250, "range": 10, "dmg": 3, "mult": 1.5, "label": "Long Sword"},
    "war_axe": {"price": 350, "range": 5, "dmg": 9.5, "mult": 1.3, "label": "War Axe"},
    "war_hammer": {"price": 400, "range": 5, "dmg": 7.3, "mult": 1.5, "label": "War Hammer"},
    "god_sword": {"price": 1250, "range": 30, "dmg": 50, "mult": 5.0, "label": "God Sword"},
}
ARMORS = {
    "none": {"price": 0, "hits": 0, "label": "None"},
    "light": {"price": 50, "hits": 2, "label": "Light"},
    "medium": {"price": 100, "hits": 4, "label": "Medium"},
    "heavy": {"price": 200, "hits": 6, "label": "Heavy"},
    "super": {"price": 400, "hits": 10, "label": "Super"},
    "god": {"price": 1500, "hits": 20, "label": "God"},
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
            self.atk += LEVEL_UP_INCREASE
        elif stat == "magic":
            self.mag += LEVEL_UP_INCREASE
        elif stat == "health":
            self.hp += LEVEL_UP_INCREASE
        elif stat == "mana":
            self.mana += LEVEL_UP_INCREASE

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
    pending_levelups: int = 0
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

    def move(self, keys):
        dx = dy = 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1
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

    def update(self, player: Player):
        if self.hp <= 0:
            return
        if self.ai == "chase":
            px, py = player.x, player.y
            dx, dy = px - self.x, py - self.y
            dist = math.hypot(dx, dy) or 1
            self.vx = self.speed * dx / dist
            self.vy = self.speed * dy / dist
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
    ("Beetle", ORANGE),
    ("Dark Elf", PURPLE),
    ("Vampire", RED),
    ("Twin Ghouls", (120, 220, 120)),
    ("Demon Prince", (220, 120, 220)),
    ("Fire Giant", (240, 90, 40)),
    ("Undead Lich", (180, 230, 255)),
    ("Werewolf King", (120, 120, 120)),
    ("Dragon Lord", (200, 40, 40)),
    ("Demon King", (90, 40, 120)),
]
SECRET_BOSS = ("Demon Queen", (255, 70, 160))

MINIONS = [
    ("Imp", (255, 120, 60)),
    ("Skeleton", (220, 220, 220)),
    ("Demon", (200, 50, 50)),
]

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

    # Trees (circular-ish, represented by rect for collision)
    for _ in range(count // 2):
        w = h = random.randint(36, 56)
        x = random.randint(0, WIDTH - w)
        y = random.randint(0, HEIGHT - h)
        add_if_free(x, y, w, h, "tree", (70, 140, 70))

    # Ruin walls
    for _ in range(max(2, count // 3)):
        if random.random() < 0.5:
            w, h = random.randint(140, 220), 20
        else:
            w, h = 20, random.randint(140, 220)
        x = random.randint(0, WIDTH - w)
        y = random.randint(0, HEIGHT - h)
        add_if_free(x, y, w, h, "ruin", (110, 110, 120))

    # Rocks
    for _ in range(count // 3):
        w = h = random.randint(28, 42)
        x = random.randint(0, WIDTH - w)
        y = random.randint(0, HEIGHT - h)
        add_if_free(x, y, w, h, "rock", (130, 130, 140))

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
    play_time: float = 0.0
    paused: bool = False
    menu_page: str = "pause"  # pause | settings | controls
    menu_index: int = 0
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

    # Health regen timers
    hp_regen_timer: float = 0.0
    hp_regen_interval: float = 1.0
    hp_regen_amount: int = 1

    def message(self, txt: str, t: float = 2.0):
        self.info_message = txt
        self.info_timer = t

    def serialize(self):
        return {
            "stage": self.stage,
            "wave": self.wave,
            "in_safe_area": self.in_safe_area,
            "score": self.score,
            "play_time": self.play_time,
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
                "exp": self.player.exp, "level": self.player.level, "pending": self.player.pending_levelups,
                "weapon_id": self.player.weapon_id, "armor_id": self.player.armor_id,
                "armor_hits": self.player.armor_hits_remaining
            }
        }

    def deserialize(self, data):
        self.stage = data.get("stage", 1)
        self.wave = data.get("wave", 1)
        self.in_safe_area = data.get("in_safe_area", False)
        self.score = data.get("score", 0)
        self.play_time = data.get("play_time", 0.0)
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
        self.player.pending_levelups = p.get("pending", self.player.pending_levelups)
        self.player.weapon_id = p.get("weapon_id", self.player.weapon_id)
        self.player.armor_id = p.get("armor_id", self.player.armor_id)
        self.player.armor_hits_remaining = p.get("armor_hits", self.player.armor_hits_remaining)

# -------------------------
# Spawning and waves
# -------------------------

def spawn_minion(stage: int, obstacles: List["Obstacle"]) -> Enemy:
    name, color = random.choice(MINIONS)
    size = 26
    hp = 8 + stage * 3
    dmg = 4 + stage
    speed = 1.8 + 0.05 * stage
    
    # Demons are 2x faster, 1.5x harder hitting, and have double health
    if name == 'Demon':
        speed *= 2.0
        dmg = int(dmg * 1.5)
        hp *= 2
    
    x, y = random_free_spot(size, obstacles)
    enemy = Enemy(x=x, y=y, w=size, h=size, hp=hp, max_hp=hp, color=color, name=name, speed=speed, damage=dmg)
    # Imp shoots fireballs aimed at player
    if name == 'Imp':
        enemy.shoot_interval = 1.8
        enemy.projectile_speed = 6.0
        enemy.projectile_damage = max(3, 2 + stage)
        enemy.projectile_color = ORANGE
        enemy.projectile_effect = None
        enemy.projectile_pattern = 'aim'
    return enemy


def spawn_boss(stage: int, obstacles: List["Obstacle"]) -> List[Enemy]:
    if stage == SECRET_BOSS_STAGE:
        name, color = SECRET_BOSS
        size = 80
        hp = 600
        dmg = 28
        speed = 2.2
        x, y = random_free_spot(size, obstacles)
        queen = Enemy(x=x, y=y, w=size, h=size, hp=hp, max_hp=hp, color=color, name=name, speed=speed, damage=dmg)
        # Demon Queen: summons allies and must be finished by sword (tracked via data)
        queen.shoot_interval = 2.8
        queen.projectile_speed = 6.0
        queen.projectile_damage = 10
        queen.projectile_color = PURPLE
        queen.projectile_pattern = 'aim'
        queen.data['summon_thresholds'] = {0.8: False, 0.6: False, 0.4: False, 0.2: False}
        queen.data['must_die_by_sword'] = True
        queen.data['revive_once'] = False
        return [queen]
    idx = min(stage-1, len(BOSS_LIST)-1)
    name, color = BOSS_LIST[idx]
    size = 72
    base_hp = 200 + stage * 20
    base_dmg = 12 + stage
    base_speed = 2.0 + 0.05 * stage
    x, y = random_free_spot(size, obstacles)
    e = Enemy(x=x, y=y, w=size, h=size, hp=base_hp, max_hp=base_hp, color=color, name=name, speed=base_speed, damage=base_dmg)
    # Configure boss behaviors
    if name == 'Beetle':  # Boss 1: shoot fireballs
        e.shoot_interval = 1.8
        e.projectile_speed = 6.5
        e.projectile_damage = 10
        e.projectile_color = ORANGE
        e.projectile_pattern = 'aim'
    elif name == 'Dark Elf':  # Boss 2: shoot arrows
        e.shoot_interval = 1.2
        e.projectile_speed = 8.0
        e.projectile_damage = 9
        e.projectile_color = YELLOW
        e.projectile_pattern = 'aim'
    elif name == 'Vampire':  # Boss 3: cause bleed -2 dps for 10s on hit
        e.on_hit_effect = 'bleed'
        e.on_hit_effect_value = 2.0
        e.on_hit_effect_duration = 10.0
    elif name == 'Twin Ghouls':  # Boss 4: twin buff on death
        e.data['twin_buff_on_death'] = True
    elif name == 'Demon Prince':  # Boss 5: at 30% HP, shoot in 4 directions
        e.shoot_interval = 2.2
        e.projectile_speed = 6.0
        e.projectile_damage = 11
        e.projectile_color = ORANGE
        e.projectile_pattern = 'aim'
        e.data['cross4_threshold'] = 0.3
    elif name == 'Fire Giant':  # Boss 6: big fireballs; sword causes burn (no heal 10s)
        e.shoot_interval = 2.4
        e.projectile_speed = 5.0
        e.projectile_damage = 14
        e.projectile_color = ORANGE
        e.projectile_radius = MAGIC_RADIUS + 4
        e.projectile_pattern = 'aim'
        e.on_hit_effect = 'no_heal'
        e.on_hit_effect_duration = 10.0
    elif name == 'Undead Lich':  # Boss 7: fireball and self-heal if not attacked 3s
        e.shoot_interval = 1.8
        e.projectile_speed = 6.0
        e.projectile_damage = 11
        e.projectile_color = CYAN
        e.projectile_pattern = 'aim'
        e.can_heal = True
        e.heal_delay = 3.0
        e.heal_per_sec = 6.0
    elif name == 'Werewolf King':  # Boss 8: speed doubles at 50%
        e.speed_doubles_at_half = True
    elif name == 'Dragon Lord':  # Boss 9: fire breath
        e.shoot_interval = 0.25
        e.projectile_speed = 7.0
        e.projectile_damage = 6
        e.projectile_color = ORANGE
        e.projectile_pattern = 'breath'
    elif name == 'Demon King':  # Boss 10: summon allies at 80/60/40/20 and revive once
        e.data['summon_thresholds'] = {0.8: False, 0.6: False, 0.4: False, 0.2: False}
        e.revived_once = False
    enemies = [e]
    if name == "Twin Ghouls":
        # add a twin
        x2, y2 = random_free_spot(size-10, obstacles)
        e2 = Enemy(x=x2, y=y2, w=size-10, h=size-10, hp=base_hp-80, max_hp=base_hp-80, color=color, name=name, speed=base_speed+0.2, damage=base_dmg-2)
        e2.data['twin_buff_on_death'] = True
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

def drop_rewards(state: GameState, is_boss: bool, stage: int):
    px, py = state.player.center()
    x = int(px + random.randint(-40, 40))
    y = int(py + random.randint(-40, 40))
    if is_boss:
        gold = random.randint(*BOSS_GOLD_RANGE)
        if stage <= 5:
            exp = random.randint(*BOSS_1_5_EXP)
        elif stage <= 10:
            exp = random.randint(*BOSS_6_10_EXP)
        else:
            exp = SECRET_BOSS_EXP
            gold = SECRET_BOSS_GOLD
        drop_health = random.random() < HEALTH_DROP_CHANCE_BOSS
    else:
        gold = random.randint(*MINION_GOLD_RANGE)
        exp = random.randint(*MINION_EXP_RANGE)
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
                state.message(f"+{amount} gold")
            elif kind == 'exp':
                p.exp += amount
                state.message(f"+{amount} exp")
                # Level up with scaling EXP requirements
                exp_needed = get_exp_needed_for_level(p.level)
                while p.exp >= exp_needed:
                    p.exp -= exp_needed
                    p.level += 1
                    p.pending_levelups += 1
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
        player.atk += LEVEL_UP_INCREASE
    elif choice == "Magic":
        player.mag += LEVEL_UP_INCREASE
    elif choice == "Health":
        player.max_hp += LEVEL_UP_INCREASE
        player.hp = min(player.max_hp, player.hp + LEVEL_UP_INCREASE)
    elif choice == "Mana":
        player.max_mana += LEVEL_UP_INCREASE
        player.mana = min(player.max_mana, player.mana + LEVEL_UP_INCREASE)


def replenish_armor(player: Player):
    """Replenish armor hits to full if player has armor equipped"""
    if player.armor_id != "none":
        armor = get_armor(player)
        player.armor_hits_remaining = armor["hits"]

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


def draw_enemy(surface, e: Enemy):
    pygame.draw.rect(surface, e.color, e.rect())
    # HP bar
    ratio = e.hp / max(1, e.max_hp)
    draw_bar(surface, e.x, e.y - 8, e.w, 6, ratio, RED)


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


def draw_hud(surface, font_small, player: Player, state: GameState):
    # HP/Mana bars
    draw_bar(surface, 20, 20, 220, 16, player.hp / max(1, player.max_hp), RED)
    draw_bar(surface, 20, 40, 220, 16, player.mana / max(1, player.max_mana), BLUE)

    # Equipment info (left side, below bars)
    wpn = get_weapon(player)
    arm = get_armor(player)
    
    # Armor display - show "Broken" if no hits remaining, otherwise show armor name
    armor_display = "Broken" if player.armor_hits_remaining <= 0 else arm['label']
    
    weapon_txt = font_small.render(f"Weapon: {wpn['label']}", True, WHITE)
    surface.blit(weapon_txt, (20, 64))
    armor_txt = font_small.render(f"Armor: {armor_display}", True, WHITE)
    surface.blit(armor_txt, (20, 86))

    # Gold, EXP, Level (top right, next to HP/Mana bars)
    exp_needed = get_exp_needed_for_level(player.level)
    
    # Create colored text for gold (gold color), exp (RGB), and level (purple)
    gold_color = (255, 215, 0)  # Gold color
    exp_color = (255, 0, 255)   # Magenta/RGB color  
    level_color = (128, 0, 128) # Purple color
    
    gold_txt = font_small.render(f"Gold: {player.gold}", True, gold_color)
    exp_txt = font_small.render(f"EXP: {player.exp}/{exp_needed}", True, exp_color)
    level_txt = font_small.render(f"Lv: {player.level}", True, level_color)
    
    # Position these to the right of the HP/Mana bars
    surface.blit(gold_txt, (260, 20))
    surface.blit(exp_txt, (260, 40))
    surface.blit(level_txt, (260, 60))

    # Game info (stage, wave, time, score) - moved up
    time_secs = int(state.play_time)
    mins = time_secs // 60
    secs = time_secs % 60
    game_info = font_small.render(
        f"Stage: {state.stage}  Wave: {state.wave if not state.in_safe_area else 'Safe'}  Time: {mins:02d}:{secs:02d}  Score: {state.score}",
        True, WHITE)
    surface.blit(game_info, (20, 108))

    if player.pending_levelups > 0:
        lvl = font_small.render("LEVEL UP! Choose: [1]Attack [2]Magic [3]Health [4]Mana", True, YELLOW)
        surface.blit(lvl, (20, 130))

    if state.info_timer > 0 and state.info_message:
        msg = font_small.render(state.info_message, True, WHITE)
        surface.blit(msg, (WIDTH//2 - msg.get_width()//2, 20))


def draw_stage_banner(surface, font_big, text):
    banner = font_big.render(text, True, WHITE)
    surface.blit(banner, (WIDTH//2 - banner.get_width()//2, 120))

# -------------------------
# Main Loop
# -------------------------

def main():
    pygame.init()
    
    # Initialize state first to load settings
    state = GameState()
    
    # Try to load saved settings
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                state.deserialize(data)
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
    state.font_big = font_big
    state.font_small = font_small

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

    # safe area at game start
    in_safe_area_setup(state)
    state.message("Welcome! Near Merchant: Q=Weapon, E=Armor. P=Pause Menu (P to Resume)", 4)

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
                if event.key == pygame.K_1 and state.player.pending_levelups > 0:
                    apply_levelup_choice(state.player, "Attack")
                    state.player.pending_levelups -= 1
                if event.key == pygame.K_2 and state.player.pending_levelups > 0:
                    apply_levelup_choice(state.player, "Magic")
                    state.player.pending_levelups -= 1
                if event.key == pygame.K_3 and state.player.pending_levelups > 0:
                    apply_levelup_choice(state.player, "Health")
                    state.player.pending_levelups -= 1
                if event.key == pygame.K_4 and state.player.pending_levelups > 0:
                    apply_levelup_choice(state.player, "Mana")
                    state.player.pending_levelups -= 1
                # Merchant quick-buy keys (only in safe area and near merchant)
                if state.in_safe_area and state.player.rect().colliderect(merchant_rect):
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

        # If paused, handle menu and draw overlay, skip gameplay updates
        if state.paused:
            # Simple pause menu pages
            screen.fill(BG_COLOR)
            title = font_big.render("Paused", True, WHITE)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 180))

            if state.menu_page == "pause":
                lines = [
                    "Resume",
                    "Settings",
                    "Controls",
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
                lines = [
                    "Controls:",
                    "Movement: W/A/S/D keys",
                    "Combat: LMB = Slash, F = Magic, L = Dash",
                    "Interaction: E = Interact with Merchant",
                    "Shopping: Q/E = Buy Weapon/Armor at Merchant",
                    "Level Up: [1]Attack [2]Magic [3]Health [4]Mana",
                    "Game: N = Start Stage, P = Pause/Resume",
                    "Display: F11 = Toggle Fullscreen",
                    "Save: Shift+Q = Save & Quit",
                    "Back",
                ]

            # Determine which lines are selectable for navigation
            if state.menu_page == "pause":
                selectable = [0, 1, 2, 3]
            elif state.menu_page == "settings":
                selectable = [1, 2, 3, 4, 5, 6, 7]  # All settings options + Back
            else:  # controls
                selectable = [9]  # Only "Back" is selectable (now at index 9)

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

            # Handle menu navigation with arrow keys and activation with Enter
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    # Debounce navigation
                    if time.time() - state.menu_last_nav_time >= state.menu_nav_delay:
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
                        elif state.menu_index == 3:  # Save & Quit
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
                        elif state.menu_index == 3:  # Sound Effects toggle
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
                            snd = state.sounds.get('menu_back')
                            if snd:
                                snd.play()
                    elif state.menu_page == "controls":
                        # Only "Back" is selectable on controls page
                        state.menu_page = "pause"
                        snd = state.sounds.get('menu_back')
                        if snd:
                            snd.play()
                # ESC still resumes when paused
                if event.key == pygame.K_ESCAPE:
                    pass  # ESC no longer resumes; P resumes
                # P toggles pause state off when already paused
                if event.key == pygame.K_p:
                    state.paused = False
                # F11 toggles fullscreen
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen(state)

            # Settings interactions
            if state.menu_page == "settings":
                settings_changed = False
                
                # Master Volume adjustments: +/-, Left/Right arrows
                master_inc = (keys[pygame.K_EQUALS] or keys[pygame.K_PLUS] or keys[pygame.K_RIGHT])
                master_dec = (keys[pygame.K_MINUS] or keys[pygame.K_LEFT])
                if master_inc:
                    state.volume = min(1.0, state.volume + 0.02)
                    settings_changed = True
                if master_dec:
                    state.volume = max(0.0, state.volume - 0.02)
                    settings_changed = True
                
                # SFX Volume adjustments: A/D keys
                sfx_inc = keys[pygame.K_d]
                sfx_dec = keys[pygame.K_a]
                if sfx_inc:
                    state.sfx_volume = min(1.0, state.sfx_volume + 0.02)
                    settings_changed = True
                if sfx_dec:
                    state.sfx_volume = max(0.0, state.sfx_volume - 0.02)
                    settings_changed = True
                
                # Music Volume adjustments: Q/E keys
                music_inc = keys[pygame.K_e]
                music_dec = keys[pygame.K_q]
                if music_inc:
                    state.music_volume = min(1.0, state.music_volume + 0.02)
                    settings_changed = True
                if music_dec:
                    state.music_volume = max(0.0, state.music_volume - 0.02)
                    settings_changed = True
                
                # Play tick sound and apply settings (throttled)
                if settings_changed and time.time() - state.volume_last_time >= state.volume_tick_delay:
                    snd = state.sounds.get('menu_tick')
                    if snd:
                        snd.play()
                    state.volume_last_time = time.time()
                    apply_audio_settings(state)

            pygame.display.flip()
            continue

        # Unpaused: accumulate timer
        state.play_time += dt

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
                leave_safe_area(state)
                # generate obstacles for this stage
                obstacles = generate_arena_obstacles(state.stage)
                state.message(f"Stage {state.stage}: Fight 5 waves!", 3)
        else:
            # Combat update: spawn waves, update enemies
            alive = []
            for e in state.enemies:
                prev_x, prev_y = e.x, e.y
                e.update(state.player)
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
                # Boss 5 cross4 at 30% health
                if 'cross4_threshold' in e.data and e.hp <= e.max_hp * e.data['cross4_threshold'] and not e.data.get('did_cross4', False):
                    e.data['did_cross4'] = True
                    ex, ey = e.x + e.w/2, e.y + e.h/2
                    for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                        vx = e.projectile_speed * dx
                        vy = e.projectile_speed * dy
                        state.projectiles.append(Projectile(ex, ey, vx, vy, e.projectile_damage, e.projectile_color, radius=e.projectile_radius, from_player=False))
                # Demon King/Queen summon thresholds
                if 'summon_thresholds' in e.data:
                    for frac, done in list(e.data['summon_thresholds'].items()):
                        if not done and e.hp <= e.max_hp * float(frac):
                            e.data['summon_thresholds'][frac] = True
                            # summon helpers
                            count = 3
                            state.enemies.extend(spawn_minion(state.stage, obstacles) for _ in range(count))
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
                    if e.name == 'Demon King' and not getattr(e, 'revived_once', False):
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
                    if e.name == 'Twin Ghouls':
                        for oth in state.enemies:
                            if oth is not e and oth.name == 'Twin Ghouls' and oth.hp > 0:
                                oth.damage = int(oth.damage * 1.5)
                                break
                    # drop rewards
                    is_boss = (state.wave == MINION_WAVES_PER_STAGE + 1)
                    drop_rewards(state, is_boss, state.stage)
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
                        count = 3 + state.stage  # ramp up
                        state.enemies = [spawn_minion(state.stage, obstacles) for _ in range(count)]
                        state.wave += 1
                        state.pending_spawn = False
                elif state.wave == MINION_WAVES_PER_STAGE + 1:
                    if not state.pending_spawn:
                        state.pending_spawn = True
                        state.wave_cooldown = 5.0
                        state.message("Final wave cleared. Boss in 5s.", 2)
                    elif state.wave_cooldown == 0.0:
                        # spawn boss
                        state.enemies = spawn_boss(state.stage, obstacles)
                        state.wave += 1
                        state.pending_spawn = False
                else:
                    # Stage clear
                    state.stage += 1
                    if state.stage == SECRET_BOSS_STAGE:
                        state.message("A portal opens... The Demon Queen awaits.", 4)
                    if state.stage > SECRET_BOSS_STAGE:
                        state.message("You have conquered all. GG!", 6)
                    # Replenish armor after boss defeat
                    replenish_armor(state.player)
                    in_safe_area_setup(state)
                    obstacles = []

        # Mana regen slow
        if not state.in_safe_area and random.random() < 0.02:
            state.player.mana = min(state.player.max_mana, state.player.mana + 1)
        # Health regen over time (in and out of combat), disabled during no-heal
        if not state.paused and state.player.no_heal_time_left <= 0:
            state.hp_regen_timer += dt
            if state.hp_regen_timer >= state.hp_regen_interval:
                state.hp_regen_timer -= state.hp_regen_interval
                state.player.hp = min(state.player.max_hp, state.player.hp + state.hp_regen_amount)

        # Pickups
        check_pickups(state)

        # Death check
        if state.player.hp <= 0:
            in_safe_area_setup(state)
            state.player.hp = state.player.max_hp
            state.player.mana = state.player.max_mana
            state.message("You fell... Returning to safe area.", 3)

        # Draw
        screen.fill(BG_COLOR)

        if state.in_safe_area:
            # Draw a simple hub and merchant
            pygame.draw.rect(screen, (25, 40, 25), (0, 100, WIDTH, HEIGHT-200))
            pygame.draw.rect(screen, (60, 60, 20), merchant_rect)
            # Draw merchant NPC
            pygame.draw.rect(screen, (40, 40, 10), merchant_rect, 2)
            pygame.draw.rect(screen, merchant.color, merchant.rect())
            label = font_small.render("Merchant: Q=Buy Next Weapon | E=Buy Next Armor | N=Start Stage", True, WHITE)
            screen.blit(label, (WIDTH//2 - label.get_width()//2, 120))
            if state.player.rect().colliderect(merchant_rect):
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
            draw_enemy(screen, e)
        for pr in state.projectiles:
            pygame.draw.circle(screen, pr.color, pr.pos(), pr.radius)
        draw_pickups(screen, state.drops)

        draw_hud(screen, font_small, state.player, state)
        if not state.in_safe_area and state.wave == MINION_WAVES_PER_STAGE + 2:
            draw_stage_banner(screen, font_big, "Stage Cleared!")
        if state.stage <= len(BOSS_LIST) and state.wave == MINION_WAVES_PER_STAGE + 1 and not state.in_safe_area:
            draw_stage_banner(screen, font_big, f"Boss: {BOSS_LIST[state.stage-1][0]}")
        if state.stage == SECRET_BOSS_STAGE and not state.in_safe_area:
            draw_stage_banner(screen, font_big, f"Secret Boss: {SECRET_BOSS[0]}")

        pygame.display.flip()

if __name__ == "__main__":
    main()