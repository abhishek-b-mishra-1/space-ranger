# enemies.py — Enemy types, sequences, and manager

import pygame
import math
import random
from assets import GREY, DARK_GREY, BROWN, DARK_BROWN, GREEN, RED, WHITE

SCREEN_W = 800
SCREEN_H = 600


# ── Base Enemy ────────────────────────────────────────────────────────────────
class Enemy:
    SCORE = 0
    explosion_size = "small"

    def __init__(self, x: float, y: float, hp: int, speed: float) -> None:
        self.x = x
        self.y = y
        self.hp = hp
        self.speed = speed
        self._dead = False
        self.angle = 0.0

    @property
    def is_dead(self) -> bool:
        return self._dead

    def take_damage(self, dmg: int) -> None:
        self.hp -= dmg
        if self.hp <= 0:
            self._dead = True

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 20, int(self.y) - 20, 40, 40)

    def update(self) -> None:
        self.x -= self.speed
        if self.x < -60:
            self._dead = True

    def draw(self, screen: pygame.Surface) -> None:
        pass


# ── Rock ──────────────────────────────────────────────────────────────────────
class Rock(Enemy):
    BASE_POINTS = [
        (-16, -6), (-10, -14), (2, -16), (12, -10),
        (16, 2),   (10, 14),   (-4, 16), (-14, 8),
    ]
    SCORE = 10
    explosion_size = "small"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, hp=2, speed=1.5)
        self.rot_speed = random.uniform(-1.2, 1.2)
        self.points = [(px + random.randint(-3, 3), py + random.randint(-3, 3))
                       for px, py in self.BASE_POINTS]
        self.color = (random.randint(120, 180),
                      random.randint(120, 180),
                      random.randint(120, 180))

    def update(self) -> None:
        super().update()
        self.angle += self.rot_speed

    def _rotated_pts(self) -> list:
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        pts = []
        for px, py in self.points:
            rx = px * cos_a - py * sin_a + self.x
            ry = px * sin_a + py * cos_a + self.y
            pts.append((int(rx), int(ry)))
        return pts

    def draw(self, screen: pygame.Surface) -> None:
        pts = self._rotated_pts()
        pygame.draw.polygon(screen, self.color, pts)
        pygame.draw.polygon(screen, DARK_GREY, pts, 2)


# ── Asteroid ──────────────────────────────────────────────────────────────────
class Asteroid(Enemy):
    BASE_POINTS = [
        (-26, -8), (-18, -22), (-4, -28), (14, -22),
        (28, -6),  (24, 16),   (10, 26),  (-10, 26),
        (-24, 14),
    ]
    SCORE = 20
    explosion_size = "medium"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, hp=4, speed=2.0)
        self.rot_speed = random.uniform(-0.8, 0.8)
        self.points = [(px + random.randint(-4, 4), py + random.randint(-4, 4))
                       for px, py in self.BASE_POINTS]
        # Reddish-brown chunky asteroid colour matching reference image
        self.color = (random.randint(100, 140),
                      random.randint(55, 80),
                      random.randint(20, 45))

    def update(self) -> None:
        super().update()
        self.angle += self.rot_speed

    def _rotated_pts(self) -> list:
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        pts = []
        for px, py in self.points:
            rx = px * cos_a - py * sin_a + self.x
            ry = px * sin_a + py * cos_a + self.y
            pts.append((int(rx), int(ry)))
        return pts

    def draw(self, screen: pygame.Surface) -> None:
        pts = self._rotated_pts()
        pygame.draw.polygon(screen, self.color, pts)
        pygame.draw.polygon(screen, DARK_BROWN, pts, 2)
        if len(pts) >= 4:
            mid = pts[len(pts) // 2]
            pygame.draw.line(screen, DARK_BROWN, pts[0], mid, 1)
            pygame.draw.line(screen, DARK_BROWN, pts[len(pts) // 4], mid, 1)


# ── Alien Head ────────────────────────────────────────────────────────────────
class AlienHead(Enemy):
    RADIUS = 18
    SCORE = 30
    explosion_size = "medium"

    def __init__(self, x: float, y: float,
                 shoot_interval: int = 120) -> None:
        super().__init__(x, y, hp=3, speed=2.5)
        self.shoot_interval = shoot_interval
        self.shoot_timer = random.randint(min(40, self.shoot_interval), self.shoot_interval)
        self.bob_phase = random.uniform(0, math.pi * 2)
        self.base_y = y
        self._pending_shot = False

    def update(self) -> None:
        super().update()
        self.bob_phase += 0.04
        self.y = self.base_y + math.sin(self.bob_phase) * 8
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_interval
            self._pending_shot = True

    def pop_shot(self) -> bool:
        if self._pending_shot:
            self._pending_shot = False
            return True
        return False

    def get_rect(self) -> pygame.Rect:
        r = self.RADIUS
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    def draw(self, screen: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        r = self.RADIUS
        pygame.draw.circle(screen, GREEN, (cx, cy), r)
        pygame.draw.circle(screen, (20, 160, 20), (cx, cy), r, 2)
        for ex, ey in [(-7, -5), (7, -5)]:
            pygame.draw.circle(screen, (0, 0, 0), (cx + ex, cy + ey), 5)
            pygame.draw.circle(screen, RED, (cx + ex, cy + ey), 3)
            pygame.draw.circle(screen, (255, 180, 180), (cx + ex - 1, cy + ey - 1), 1)
        pygame.draw.line(screen, GREEN,
                         (cx - 8, cy - r), (cx - 14, cy - r - 12), 2)
        pygame.draw.line(screen, GREEN,
                         (cx + 8, cy - r), (cx + 14, cy - r - 12), 2)
        pygame.draw.circle(screen, (180, 255, 180), (cx - 14, cy - r - 12), 3)
        pygame.draw.circle(screen, (180, 255, 180), (cx + 14, cy - r - 12), 3)
        pygame.draw.arc(screen, (0, 100, 0),
                        (cx - 8, cy + 4, 16, 8),
                        math.pi, 2 * math.pi, 2)


# ── Space Junk ────────────────────────────────────────────────────────────────
class SpaceJunk(Enemy):
    SCORE = 15
    explosion_size = "small"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, hp=2, speed=1.8)
        self.rot_speed = random.uniform(-1.5, 1.5)
        self.color = (random.randint(80, 130), random.randint(80, 130),
                      random.randint(90, 140))

    def update(self) -> None:
        super().update()
        self.angle += self.rot_speed

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 18, int(self.y) - 12, 36, 24)

    def draw(self, screen: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        def rot(px, py):
            rx = px * cos_a - py * sin_a + cx
            ry = px * sin_a + py * cos_a + cy
            return (int(rx), int(ry))

        body_pts = [rot(-14, -8), rot(14, -8), rot(14, 8), rot(-14, 8)]
        pygame.draw.polygon(screen, self.color, body_pts)
        pygame.draw.polygon(screen, DARK_GREY, body_pts, 2)

        panel_l = [rot(-14, -5), rot(-22, -5), rot(-22, 5), rot(-14, 5)]
        pygame.draw.polygon(screen, (60, 80, 110), panel_l)
        pygame.draw.polygon(screen, DARK_GREY, panel_l, 1)

        panel_r = [rot(14, -5), rot(22, -5), rot(22, 5), rot(14, 5)]
        pygame.draw.polygon(screen, (60, 80, 110), panel_r)
        pygame.draw.polygon(screen, DARK_GREY, panel_r, 1)

        pygame.draw.line(screen, DARK_GREY, rot(-8, -6), rot(-4, 2), 1)
        pygame.draw.line(screen, DARK_GREY, rot(4, -4), rot(10, 6), 1)
        pygame.draw.line(screen, DARK_GREY, rot(-2, 2), rot(6, -2), 1)


# ── Meteor ────────────────────────────────────────────────────────────────────
class Meteor(Enemy):
    BASE_POINTS = [
        (-20, -6), (-14, -20), (-2, -24), (14, -18),
        (22, -4),  (20, 12),   (8, 22),   (-10, 20), (-20, 8),
    ]
    SCORE = 25
    explosion_size = "medium"
    TRAIL_LEN = 12

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, hp=3, speed=3.0)
        self.rot_speed = random.uniform(-2.5, 2.5)
        self.points = [(px + random.randint(-3, 3), py + random.randint(-3, 3))
                       for px, py in self.BASE_POINTS]
        self.color = (random.randint(70, 110),
                      random.randint(50, 80),
                      random.randint(30, 55))
        self.trail: list = []

    def update(self) -> None:
        self.trail.append((self.x, self.y, 200))
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)
        self.trail = [(tx, ty, max(0, ta - 18)) for tx, ty, ta in self.trail]
        super().update()
        self.angle += self.rot_speed

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 22, int(self.y) - 22, 44, 44)

    def _rotated_pts(self) -> list:
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        pts = []
        for px, py in self.points:
            rx = px * cos_a - py * sin_a + self.x
            ry = px * sin_a + py * cos_a + self.y
            pts.append((int(rx), int(ry)))
        return pts

    def draw(self, screen: pygame.Surface) -> None:
        for i, (tx, ty, ta) in enumerate(self.trail):
            if ta <= 0:
                continue
            r_size = max(1, 4 + i // 2)
            surf_size = r_size * 2 + 2
            tmp = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (255, 120, 20, ta),
                               (r_size + 1, r_size + 1), r_size)
            screen.blit(tmp, (int(tx) - r_size - 1, int(ty) - r_size - 1))

        cx, cy = int(self.x), int(self.y)
        glow_size = 26
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 100, 0, 60),
                           (glow_size, glow_size), glow_size)
        screen.blit(glow_surf, (cx - glow_size, cy - glow_size))

        pts = self._rotated_pts()
        pygame.draw.polygon(screen, self.color, pts)
        pygame.draw.polygon(screen, (200, 80, 20), pts, 2)


# ── Ice Comet ─────────────────────────────────────────────────────────────────
class IceComet(Enemy):
    BASE_POINTS = [
        (-10, -18), (4, -16), (16, -6), (14, 8),
        (4, 16), (-10, 14), (-16, 4), (-14, -8),
    ]
    SCORE = 35
    explosion_size = "medium"
    TRAIL_LEN = 16

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, hp=2, speed=4.0)
        self.rot_speed = random.uniform(-1.8, 1.8)
        self.points = [(px + random.randint(-2, 2), py + random.randint(-2, 2))
                       for px, py in self.BASE_POINTS]
        self.color = (random.randint(140, 200),
                      random.randint(200, 240),
                      random.randint(230, 255))
        self.trail: list = []

    def update(self) -> None:
        self.trail.append((self.x, self.y, 180))
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)
        self.trail = [(tx, ty, max(0, ta - 12)) for tx, ty, ta in self.trail]
        super().update()
        self.angle += self.rot_speed

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 16, int(self.y) - 18, 32, 36)

    def _rotated_pts(self) -> list:
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        pts = []
        for px, py in self.points:
            rx = px * cos_a - py * sin_a + self.x
            ry = px * sin_a + py * cos_a + self.y
            pts.append((int(rx), int(ry)))
        return pts

    def draw(self, screen: pygame.Surface) -> None:
        for i, (tx, ty, ta) in enumerate(self.trail):
            if ta <= 0:
                continue
            r_size = max(1, 3 + i // 3)
            surf_size = r_size * 2 + 2
            tmp = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (150, 220, 255, ta),
                               (r_size + 1, r_size + 1), r_size)
            screen.blit(tmp, (int(tx) - r_size - 1, int(ty) - r_size - 1))

        pts = self._rotated_pts()
        pygame.draw.polygon(screen, self.color, pts)
        pygame.draw.polygon(screen, (180, 230, 255), pts, 2)

        cx, cy = int(self.x), int(self.y)
        pygame.draw.circle(screen, (220, 245, 255), (cx - 4, cy - 4), 2)


# ── Drone ─────────────────────────────────────────────────────────────────────
class Drone(Enemy):
    RADIUS = 20
    SCORE = 40
    explosion_size = "medium"

    def __init__(self, x: float, y: float,
                 shoot_interval: int = 80) -> None:
        super().__init__(x, y, hp=5, speed=2.0)
        self.shoot_interval = shoot_interval
        self.shoot_timer = random.randint(min(30, self.shoot_interval), self.shoot_interval)
        self.bob_phase = random.uniform(0, math.pi * 2)
        self.base_y = y
        self._pending_shot = False

    def update(self) -> None:
        super().update()
        self.bob_phase += 0.05
        self.y = self.base_y + math.sin(self.bob_phase) * 6
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_interval
            self._pending_shot = True

    def pop_shot(self) -> bool:
        if self._pending_shot:
            self._pending_shot = False
            return True
        return False

    def get_rect(self) -> pygame.Rect:
        r = self.RADIUS
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    def draw(self, screen: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        r = self.RADIUS

        body_pts = []
        for i in range(8):
            ang = math.pi / 8 + i * math.pi / 4
            body_pts.append((int(cx + r * math.cos(ang)),
                             int(cy + r * math.sin(ang))))
        pygame.draw.polygon(screen, (50, 60, 70), body_pts)
        pygame.draw.polygon(screen, (100, 120, 140), body_pts, 2)

        pygame.draw.rect(screen, (40, 50, 60), (cx - r - 14, cy - 5, 14, 10))
        pygame.draw.rect(screen, (40, 50, 60), (cx + r,       cy - 5, 14, 10))
        pygame.draw.rect(screen, (80, 100, 120), (cx - r - 14, cy - 5, 14, 10), 1)
        pygame.draw.rect(screen, (80, 100, 120), (cx + r,       cy - 5, 14, 10), 1)

        pulse = abs(math.sin(self.bob_phase * 2))
        eye_r = int(6 + pulse * 2)
        pygame.draw.circle(screen, (20, 0, 0), (cx, cy), eye_r + 3)
        pygame.draw.circle(screen, (200, 20, 20), (cx, cy), eye_r)
        pygame.draw.circle(screen, (255, 100, 100), (cx, cy), max(1, eye_r - 2))

        pygame.draw.line(screen, (80, 100, 120), (cx - r + 4, cy), (cx + r - 4, cy), 1)


# ── Sequence types ────────────────────────────────────────────────────────────
ROCK_LINE        = "ROCK_LINE"
ASTEROID_CLUSTER = "ASTEROID_CLUSTER"
ALIEN_PATROL     = "ALIEN_PATROL"
MIXED            = "MIXED"
JUNK_FIELD       = "JUNK_FIELD"
METEOR_SHOWER    = "METEOR_SHOWER"
COMET_STREAM     = "COMET_STREAM"
DRONE_SQUAD      = "DRONE_SQUAD"

ALL_TYPES = [
    ROCK_LINE, ASTEROID_CLUSTER, ALIEN_PATROL, MIXED,
    JUNK_FIELD, METEOR_SHOWER, COMET_STREAM, DRONE_SQUAD,
]


class EnemySequence:
    def __init__(self, seq_type: str,
                 speed_mult: float = 1.0,
                 hp_mult: float = 1.0,
                 alien_shoot_interval: int = 120,
                 drone_shoot_interval: int = 80) -> None:
        self.seq_type = seq_type
        self.speed_mult = speed_mult
        self.hp_mult = hp_mult
        self.alien_shoot_interval = alien_shoot_interval
        self.drone_shoot_interval = drone_shoot_interval
        self.enemies: list[Enemy] = []
        self.completed = False
        self.reward_pos: tuple | None = None
        self.explosion_events: list[tuple] = []
        self.hit_sparks: list[tuple] = []
        self._build()

    def _apply_scaling(self, enemy: Enemy) -> None:
        """Apply speed and HP multipliers to a freshly created enemy."""
        enemy.speed = enemy.speed * self.speed_mult
        enemy.hp = max(1, round(enemy.hp * self.hp_mult))

    def _build(self) -> None:
        spawn_x = SCREEN_W + 60
        if self.seq_type == ROCK_LINE:
            y_start = random.randint(80, SCREEN_H - 80)
            for i in range(5):
                e = Rock(spawn_x + i * 50, y_start)
                self._apply_scaling(e)
                self.enemies.append(e)

        elif self.seq_type == ASTEROID_CLUSTER:
            cy = random.randint(120, SCREEN_H - 120)
            offsets = [(0, 0), (-50, 50), (50, 50)]
            for ox, oy in offsets:
                e = Asteroid(spawn_x + ox, cy + oy)
                self._apply_scaling(e)
                self.enemies.append(e)

        elif self.seq_type == ALIEN_PATROL:
            cy = random.randint(100, SCREEN_H - 100)
            offsets = [(0, 0), (-60, -40), (-60, 40)]
            for ox, oy in offsets:
                e = AlienHead(spawn_x + ox, cy + oy,
                              shoot_interval=self.alien_shoot_interval)
                self._apply_scaling(e)
                self.enemies.append(e)

        elif self.seq_type == JUNK_FIELD:
            y1 = random.randint(80, SCREEN_H // 2 - 40)
            y2 = y1 + random.randint(80, 140)
            y2 = min(y2, SCREEN_H - 80)
            for i in range(3):
                e = SpaceJunk(spawn_x + i * 60, y1)
                self._apply_scaling(e)
                self.enemies.append(e)
            for i in range(3):
                e = SpaceJunk(spawn_x + i * 60 + 30, y2)
                self._apply_scaling(e)
                self.enemies.append(e)

        elif self.seq_type == METEOR_SHOWER:
            base_x = spawn_x
            base_y = random.randint(80, SCREEN_H - 200)
            for i in range(4):
                e = Meteor(base_x + i * 70, base_y + i * 50)
                self._apply_scaling(e)
                self.enemies.append(e)

        elif self.seq_type == COMET_STREAM:
            cy = random.randint(100, SCREEN_H - 100)
            for i in range(3):
                e = IceComet(spawn_x + i * 35, cy + random.randint(-20, 20))
                self._apply_scaling(e)
                self.enemies.append(e)

        elif self.seq_type == DRONE_SQUAD:
            cy = random.randint(120, SCREEN_H - 120)
            offsets = [(0, 0), (-70, -50), (-70, 50)]
            for ox, oy in offsets:
                e = Drone(spawn_x + ox, cy + oy,
                          shoot_interval=self.drone_shoot_interval)
                self._apply_scaling(e)
                self.enemies.append(e)

        else:  # MIXED
            count = random.randint(4, 6)
            mixed_choices = [Rock, Asteroid, AlienHead, SpaceJunk, Meteor, IceComet, Drone]
            for i in range(count):
                y = random.randint(60, SCREEN_H - 60)
                x = spawn_x + random.randint(0, 80)
                cls = random.choice(mixed_choices)
                if cls == AlienHead:
                    e = cls(x, y, shoot_interval=self.alien_shoot_interval)
                elif cls == Drone:
                    e = cls(x, y, shoot_interval=self.drone_shoot_interval)
                else:
                    e = cls(x, y)
                self._apply_scaling(e)
                self.enemies.append(e)

    def all_dead(self) -> bool:
        return all(e.is_dead for e in self.enemies)

    def update(self) -> list:
        """Update all enemies; return list of EnemyShot projectiles."""
        from weapons import EnemyShot
        shots: list = []
        for enemy in self.enemies:
            if not enemy.is_dead:
                enemy.update()
                if isinstance(enemy, (AlienHead, Drone)) and enemy.pop_shot():
                    shots.append(EnemyShot(enemy.x - 10, enemy.y,
                                           -4.0, random.uniform(-0.5, 0.5)))

        newly_dead = [e for e in self.enemies if e.is_dead]
        for e in newly_dead:
            self.explosion_events.append((e.x, e.y, e.explosion_size))

        self.enemies = [e for e in self.enemies if not e.is_dead]
        return shots

    def draw(self, screen: pygame.Surface) -> None:
        for enemy in self.enemies:
            enemy.draw(screen)

    def pop_explosion_events(self) -> list:
        evts = self.explosion_events[:]
        self.explosion_events.clear()
        return evts

    def pop_hit_sparks(self) -> list:
        sparks = self.hit_sparks[:]
        self.hit_sparks.clear()
        return sparks


# ── Enemy Manager ─────────────────────────────────────────────────────────────
class EnemyManager:
    # 10-level lookup tables — steep difficulty curve
    _SPEED_TABLE = [1.0, 1.6, 2.3, 3.1, 4.0, 5.1, 6.4, 8.0, 10.0, 12.5]
    _HP_TABLE    = [1.0, 1.5, 2.2, 3.1, 4.2, 5.6, 7.5, 10.0, 13.5, 18.0]
    _SPAWN_MIN   = [220, 170, 130, 100, 75,  55,  40,  30,   22,   16]
    _SPAWN_MAX   = [280, 220, 175, 140, 110, 85,  65,  50,   38,   28]
    _ALIEN_INT   = [110, 85,  63,  46,  33,  23,  16,  11,   7,    5]
    _DRONE_INT   = [75,  57,  42,  31,  22,  15,  10,  7,    5,    3]

    def __init__(self) -> None:
        self.sequences: list[EnemySequence] = []
        self.spawn_timer = 120
        self.enemy_shots: list = []
        self.score_events: list[int] = []
        self.powerup_drops: list[tuple] = []
        self.paused = False

        # Difficulty scaling attributes — level 1 defaults
        self.level = 1
        self._speed_mult = 1.0
        self._hp_mult = 1.0
        self._spawn_min = 240
        self._spawn_max = 300
        self._alien_shoot_interval = 120
        self._drone_shoot_interval = 80

    def set_level(self, level: int) -> None:
        """Update difficulty parameters for the given level (1–10)."""
        self.level = max(1, min(10, level))
        idx = min(self.level - 1, len(self._SPEED_TABLE) - 1)

        self._speed_mult             = self._SPEED_TABLE[idx]
        self._hp_mult                = self._HP_TABLE[idx]
        self._spawn_min              = max(55,  self._SPAWN_MIN[idx])
        self._spawn_max              = max(70,  self._SPAWN_MAX[idx])
        self._alien_shoot_interval   = self._ALIEN_INT[idx]
        self._drone_shoot_interval   = self._DRONE_INT[idx]

    def _next_interval(self) -> int:
        return random.randint(self._spawn_min, self._spawn_max)

    def _spawn_sequence(self) -> None:
        seq_type = random.choice(ALL_TYPES)
        self.sequences.append(EnemySequence(
            seq_type,
            speed_mult=self._speed_mult,
            hp_mult=self._hp_mult,
            alien_shoot_interval=self._alien_shoot_interval,
            drone_shoot_interval=self._drone_shoot_interval,
        ))

    def update(self) -> None:
        if self.paused:
            new_shots: list = []
            for seq in self.sequences:
                new_shots += seq.update()
            self.enemy_shots += new_shots
            for shot in self.enemy_shots:
                shot.update()
            self.enemy_shots = [s for s in self.enemy_shots if not s.dead]
            for seq in self.sequences[:]:
                if not seq.completed and seq.all_dead() and len(seq.enemies) == 0:
                    seq.completed = True
            self.sequences = [s for s in self.sequences if not s.completed]
            return

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_sequence()
            # Multi-spawn scaling by level
            if self.level >= 8:
                self._spawn_sequence()   # always 3 simultaneous
                self._spawn_sequence()
            elif self.level >= 6:
                self._spawn_sequence()   # always 2 simultaneous
                if random.random() < 0.50:
                    self._spawn_sequence()  # 50% chance 3rd
            elif self.level >= 4:
                self._spawn_sequence()   # always 2 simultaneous at 4+
            elif self.level >= 3 and random.random() < 0.40:
                self._spawn_sequence()   # 40% chance 2nd at level 3
            self.spawn_timer = self._next_interval()

        new_shots: list = []
        for seq in self.sequences:
            new_shots += seq.update()

        self.enemy_shots += new_shots

        for shot in self.enemy_shots:
            shot.update()
        self.enemy_shots = [s for s in self.enemy_shots if not s.dead]

        for seq in self.sequences[:]:
            if not seq.completed and seq.all_dead() and len(seq.enemies) == 0:
                seq.completed = True
                drop_x = random.randint(200, 600)
                drop_y = random.randint(100, SCREEN_H - 100)
                self.powerup_drops.append((drop_x, drop_y))

        self.sequences = [s for s in self.sequences if not s.completed]

    def check_player_shots(self, projectiles: list) -> int:
        """Collide player projectiles with enemies, return score earned."""
        score = 0
        for proj in projectiles[:]:
            if proj.owner != "player" or proj.dead:
                continue
            p_rect = proj.get_rect()
            for seq in self.sequences:
                for enemy in seq.enemies:
                    if enemy.is_dead:
                        continue
                    hit = False
                    if isinstance(enemy, (AlienHead, Drone)):
                        dx = proj.x - enemy.x
                        dy = proj.y - enemy.y
                        if math.hypot(dx, dy) < enemy.RADIUS + 6:
                            hit = True
                    else:
                        if p_rect.colliderect(enemy.get_rect()):
                            hit = True

                    if hit:
                        was_alive = not enemy.is_dead
                        enemy.take_damage(proj.damage)
                        proj.kill()
                        if enemy.is_dead and was_alive:
                            score += enemy.SCORE
                        elif not enemy.is_dead:
                            seq.hit_sparks.append((proj.x, proj.y))
        return score

    def check_player_collision(self, player_rect: pygame.Rect) -> bool:
        for seq in self.sequences:
            for enemy in seq.enemies:
                if not enemy.is_dead and player_rect.colliderect(enemy.get_rect()):
                    return True
        return False

    def check_shadow_collision(self, shadow_rect: pygame.Rect) -> int:
        hits = 0
        for shot in self.enemy_shots[:]:
            if not shot.dead and shadow_rect.colliderect(shot.get_rect()):
                shot.kill()
                hits += 1
        return hits

    def check_player_shot_hits(self, player_rect: pygame.Rect) -> bool:
        for shot in self.enemy_shots[:]:
            if not shot.dead and player_rect.colliderect(shot.get_rect()):
                shot.kill()
                return True
        return False

    def kill_all_enemies(self) -> list[tuple]:
        """Instantly kill all enemies (bomb). Returns list of (x,y,size) for explosions."""
        positions = []
        for seq in self.sequences:
            for e in seq.enemies:
                if not e.is_dead:
                    positions.append((e.x, e.y, e.explosion_size))
                    e._dead = True
        self.enemy_shots.clear()
        return positions

    def draw(self, screen: pygame.Surface) -> None:
        for seq in self.sequences:
            seq.draw(screen)
        for shot in self.enemy_shots:
            shot.draw(screen)

    def pop_powerup_drops(self) -> list[tuple]:
        drops = self.powerup_drops[:]
        self.powerup_drops.clear()
        return drops

    def pop_explosion_events(self) -> list[tuple]:
        evts: list = []
        for seq in self.sequences:
            evts += seq.pop_explosion_events()
        return evts

    def pop_hit_sparks(self) -> list[tuple]:
        sparks: list = []
        for seq in self.sequences:
            sparks += seq.pop_hit_sparks()
        return sparks

    def get_all_sequences(self) -> list[EnemySequence]:
        return self.sequences
