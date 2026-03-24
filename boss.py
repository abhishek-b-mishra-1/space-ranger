# boss.py — Boss enemies with health bars, phases, and special attacks

import pygame
import math
import random
from assets import (WHITE, GREY, DARK_GREY, RED, ORANGE, YELLOW,
                    GREEN, CYAN, BLUE, BROWN, DARK_BROWN, draw_circle_alpha)

SCREEN_W = 800
SCREEN_H = 600


# ── Boss Base Class ────────────────────────────────────────────────────────────
class Boss:
    STOP_X = 550          # x position where boss stops
    SCORE  = 0
    explosion_size = "boss"

    def __init__(self, tier: int = 1) -> None:
        self.x = float(SCREEN_W + 120)
        self.y = float(SCREEN_H // 2)
        self.tier = max(1, tier)   # 1=normal, 2=hard, 3=brutal
        self.hp = 1
        self.max_hp = 1
        self.phase = 1
        self.is_active = False    # True once boss reaches stop position
        self._dead = False
        self.boss_shots: list = []
        self.angle = 0.0

    def _t(self, v1, v2=None, v3=None):
        """Return value scaled to current tier."""
        vals = [v1, v2 if v2 is not None else v1, v3 if v3 is not None else (v2 or v1)]
        return vals[min(self.tier - 1, 2)]

    @property
    def is_dead(self) -> bool:
        return self._dead

    def take_damage(self, dmg: int) -> None:
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self._dead = True
        elif self.hp <= self.max_hp // 2 and self.phase == 1:
            self.phase = 2

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 60, int(self.y) - 50, 120, 100)

    def pop_shots(self) -> list:
        shots = self.boss_shots[:]
        self.boss_shots.clear()
        return shots

    def draw_health_bar(self, screen: pygame.Surface) -> None:
        bar_w = 400
        bar_h = 18
        bx = SCREEN_W // 2 - bar_w // 2
        by = 48

        # Background
        pygame.draw.rect(screen, (40, 0, 0), (bx - 2, by - 2, bar_w + 4, bar_h + 4),
                         border_radius=4)
        pygame.draw.rect(screen, (80, 0, 0), (bx, by, bar_w, bar_h), border_radius=3)

        # HP fill
        if self.max_hp > 0:
            fill_w = int(bar_w * self.hp / self.max_hp)
            fill_w = max(0, fill_w)
            if fill_w > 0:
                # Color changes with HP
                ratio = self.hp / self.max_hp
                if ratio > 0.6:
                    fill_color = (50, 220, 50)
                elif ratio > 0.3:
                    fill_color = (220, 180, 0)
                else:
                    fill_color = (220, 40, 40)
                pygame.draw.rect(screen, fill_color,
                                 (bx, by, fill_w, bar_h), border_radius=3)

        # Phase 2 indicator line at 50%
        mid_x = bx + bar_w // 2
        pygame.draw.line(screen, (255, 100, 0),
                         (mid_x, by), (mid_x, by + bar_h), 2)

        # Border
        pygame.draw.rect(screen, (200, 200, 200),
                         (bx, by, bar_w, bar_h), 2, border_radius=3)

        # Boss name label — override in subclass for name
        label = getattr(self, 'BOSS_NAME', 'BOSS')
        phase_str = f"  [PHASE {self.phase}]"
        try:
            font = pygame.font.SysFont("consolas,courier,monospace", 14, bold=True)
            surf = font.render(label + phase_str, True, YELLOW)
            screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, by + bar_h + 3))
        except Exception:
            pass

    def update_behavior(self, player_rect: pygame.Rect) -> None:
        """Override in subclass."""
        pass

    def draw_body(self, screen: pygame.Surface) -> None:
        """Override in subclass."""
        pass

    def update(self, player_rect: pygame.Rect) -> None:
        # Move boss to stop position
        if self.x > self.STOP_X:
            self.x -= self._entry_speed()
            if self.x <= self.STOP_X:
                self.x = float(self.STOP_X)
                self.is_active = True
        else:
            self.is_active = True

        if not self._dead:
            self.update_behavior(player_rect)

        # Clean up dead boss shots
        self.boss_shots = [s for s in self.boss_shots if not s.dead]

    # ── Shared movement helpers ────────────────────────────────────────────────
    def _track_player_y(self, player_rect: pygame.Rect, speed: float = 1.2) -> None:
        """Smoothly chase the player vertically."""
        target_y = float(player_rect.centery)
        dy = target_y - self.y
        if abs(dy) > speed:
            self.y += speed * (1 if dy > 0 else -1)

    def _strafe(self, amplitude: float = 80, speed: float = 0.02) -> None:
        """Sinusoidal vertical strafing around screen centre."""
        self._strafe_phase = getattr(self, '_strafe_phase', 0.0) + speed
        centre = SCREEN_H / 2
        self.y = centre + math.sin(self._strafe_phase) * amplitude
        self.y = max(80, min(SCREEN_H - 80, self.y))

    def _x_pulse(self, near: float = 500, far: float = 620, speed: float = 0.015) -> None:
        """Pulse the boss horizontally — closer and farther from player."""
        self._x_pulse_phase = getattr(self, '_x_pulse_phase', 0.0) + speed
        self.x = near + (far - near) * (0.5 + 0.5 * math.sin(self._x_pulse_phase))

    def _entry_speed(self) -> float:
        return 2.0

    def draw(self, screen: pygame.Surface) -> None:
        if not self._dead:
            self.draw_body(screen)


# ── Boss Asteroid ─────────────────────────────────────────────────────────────
class BossAsteroid(Boss):
    BOSS_NAME = "ASTEROID PRIME"
    SCORE     = 500
    BASE_POINTS = [
        (-55, -15), (-40, -48), (-10, -58), (25, -48),
        (58, -12),  (52,  30),  (22,  58),  (-18, 58),
        (-50, 30),
    ]

    def __init__(self, tier: int = 1) -> None:
        super().__init__(tier)
        base_hp = self._t(60, 110, 180)
        self.hp     = base_hp
        self.max_hp = base_hp
        self.rot_speed = self._t(0.4, 0.7, 1.1)
        self.points = [(px + random.randint(-5, 5), py + random.randint(-5, 5))
                       for px, py in self.BASE_POINTS]
        self.color  = (random.randint(80, 110),
                       random.randint(55, 75),
                       random.randint(20, 40))
        self.shoot_timer = self._t(90, 60, 35)
        self.y_vel = 0.0
        self.y_dir = 1.0

    def _entry_speed(self) -> float:
        return 0.8

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 60, int(self.y) - 60, 120, 120)

    def _rotated_pts(self) -> list:
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        pts = []
        for px, py in self.points:
            rx = px * cos_a - py * sin_a + self.x
            ry = px * sin_a + py * cos_a + self.y
            pts.append((int(rx), int(ry)))
        return pts

    def update_behavior(self, player_rect: pygame.Rect) -> None:
        from weapons import EnemyShot
        self.angle += self.rot_speed

        # Phase 1: strafe slowly and pulse x; Phase 2: track player + faster pulse
        if self.is_active:
            if self.phase == 1:
                self._strafe(amplitude=110, speed=0.018)
                self._x_pulse(near=510, far=650, speed=0.012)
            else:
                self._track_player_y(player_rect, speed=1.8)
                self._x_pulse(near=470, far=620, speed=0.022)

        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            if self.phase == 1:
                self.shoot_timer = self._t(75, 50, 28)
                spread   = self._t(3, 5, 7)
                interval = self._t(22, 18, 14)
                spd      = self._t(5.0, 6.5, 8.0)
            else:
                self.shoot_timer = self._t(45, 28, 16)
                spread   = self._t(6, 9, 12)
                interval = self._t(14, 12, 10)
                spd      = self._t(5.5, 7.0, 9.5)

            for i in range(spread):
                half = (spread - 1) / 2.0
                rad = math.radians(180 + (i - half) * interval)
                self.boss_shots.append(
                    EnemyShot(self.x - 60, self.y,
                              math.cos(rad) * spd, math.sin(rad) * spd)
                )

    def draw_body(self, screen: pygame.Surface) -> None:
        pts = self._rotated_pts()
        # Crater detail shadow
        pygame.draw.polygon(screen, self.color, pts)
        pygame.draw.polygon(screen, DARK_BROWN, pts, 3)

        # Crater circles
        cx, cy = int(self.x), int(self.y)
        for cpos, cr in [((cx - 18, cy - 10), 10), ((cx + 15, cy + 5), 7),
                         ((cx - 5,  cy + 20), 8),  ((cx + 22, cy - 22), 5)]:
            pygame.draw.circle(screen, DARK_BROWN, cpos, cr, 2)

        # Detail lines
        if len(pts) >= 4:
            mid = pts[len(pts) // 2]
            pygame.draw.line(screen, DARK_BROWN, pts[0], mid, 2)
            pygame.draw.line(screen, DARK_BROWN, pts[len(pts) // 4], mid, 2)


# ── Boss Alien Cruiser ─────────────────────────────────────────────────────────
class BossAlienCruiser(Boss):
    BOSS_NAME = "ALIEN CRUISER"
    SCORE     = 1000

    def __init__(self, tier: int = 1) -> None:
        super().__init__(tier)
        base_hp = self._t(100, 190, 300)
        self.hp     = base_hp
        self.max_hp = base_hp
        self.shoot_timer = self._t(70, 45, 25)
        self.spawn_timer = self._t(180, 120, 70)
        self.scan_angle = 0.0
        self.beam_timer = 0
        self.beam_active = False
        self.beam_y = 0.0
        self.pending_minions: list = []

    def _entry_speed(self) -> float:
        return 1.5

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 80, int(self.y) - 50, 160, 100)

    def update_behavior(self, player_rect: pygame.Rect) -> None:
        from weapons import EnemyShot
        self.scan_angle = (self.scan_angle + 2.5) % 360.0

        # Active movement: phase 1 tracks player; phase 2 full strafe + x-pulse
        if self.is_active:
            if self.phase == 1:
                self._track_player_y(player_rect, speed=1.4)
                self._x_pulse(near=490, far=660, speed=0.014)
            else:
                self._track_player_y(player_rect, speed=2.5)
                self._x_pulse(near=440, far=620, speed=0.025)
                self._strafe(amplitude=60, speed=0.03)   # extra weave on top

        # Aim toward player
        px = player_rect.centerx
        py = player_rect.centery
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy) or 1

        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            if self.phase == 1:
                self.shoot_timer = self._t(65, 40, 20)
                spd = self._t(5.5, 7.0, 9.5)
                burst = self._t(1, 2, 3)
                for b in range(burst):
                    ang_off = (b - burst // 2) * 10
                    rad = math.atan2(dy, dx) + math.radians(ang_off)
                    self.boss_shots.append(
                        EnemyShot(self.x - 80, self.y,
                                  math.cos(rad) * spd, math.sin(rad) * spd)
                    )
            else:
                self.shoot_timer = self._t(38, 22, 12)
                spd = self._t(9.0, 11.0, 13.0)
                offsets = self._t([-8, 0, 8], [-12, -4, 4, 12], [-15,-8,0,8,15])
                for ang_off in offsets:
                    rad = math.atan2(dy, dx) + math.radians(ang_off)
                    self.boss_shots.append(
                        EnemyShot(self.x - 80, self.y,
                                  math.cos(rad) * spd, math.sin(rad) * spd)
                    )

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self._t(100, 70, 45) if self.phase == 2 else self._t(180, 120, 70)
            self.pending_minions.append((self.x - 60, self.y - 40))
            self.pending_minions.append((self.x - 60, self.y + 40))
            if self.tier >= 3:   # tier 3 spawns 4 minions
                self.pending_minions.append((self.x - 60, self.y - 80))
                self.pending_minions.append((self.x - 60, self.y + 80))

    def pop_minions(self) -> list:
        m = self.pending_minions[:]
        self.pending_minions.clear()
        return m

    def draw_body(self, screen: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)

        # Wing polygons
        left_wing = [(cx - 20, cy - 10), (cx - 80, cy - 50),
                     (cx - 85, cy + 5),  (cx - 20, cy + 10)]
        right_wing = [(cx - 20, cy - 10), (cx - 80, cy - 50),
                      (cx - 85, cy + 5),  (cx - 20, cy + 10)]
        # Flip for right side — mirror across cy
        right_wing = [(cx - 20, cy + 10), (cx - 80, cy + 50),
                      (cx - 85, cy - 5),  (cx - 20, cy - 10)]
        pygame.draw.polygon(screen, (40, 60, 40), left_wing)
        pygame.draw.polygon(screen, (20, 160, 20), left_wing, 2)
        pygame.draw.polygon(screen, (40, 60, 40), right_wing)
        pygame.draw.polygon(screen, (20, 160, 20), right_wing, 2)

        # Central hull
        hull = pygame.Rect(cx - 80, cy - 30, 160, 60)
        pygame.draw.rect(screen, (30, 80, 30), hull, border_radius=8)
        pygame.draw.rect(screen, (50, 200, 50), hull, 2, border_radius=8)

        # Engine glow circles (back)
        for ey_off in [-20, 0, 20]:
            draw_circle_alpha(screen, (0, 255, 50), (cx + 70, cy + ey_off), 10, 80)
            pygame.draw.circle(screen, (100, 255, 100), (cx + 70, cy + ey_off), 5)

        # Scanning eye (front)
        eye_rad = math.radians(self.scan_angle)
        eye_cx = cx - 50
        eye_cy = cy
        pygame.draw.circle(screen, (20, 0, 0), (eye_cx, eye_cy), 12)
        pygame.draw.circle(screen, (220, 30, 30), (eye_cx, eye_cy), 9)
        pygame.draw.circle(screen, (255, 100, 100), (eye_cx, eye_cy), 5)
        # Scan line
        scan_end_x = eye_cx + int(math.cos(eye_rad) * 20)
        scan_end_y = eye_cy + int(math.sin(eye_rad) * 20)
        pygame.draw.line(screen, (255, 80, 80, 180),
                         (eye_cx, eye_cy), (scan_end_x, scan_end_y), 2)


# ── Boss Mecha Titan ───────────────────────────────────────────────────────────
class BossMechaTitan(Boss):
    BOSS_NAME = "MECHA TITAN"
    SCORE     = 2000

    def __init__(self, tier: int = 1) -> None:
        super().__init__(tier)
        base_hp = self._t(150, 260, 400)
        self.hp     = base_hp
        self.max_hp = base_hp
        self.shoot_timer = self._t(100, 65, 35)
        self.charge_timer = 0
        self.charging = False
        self.charge_speed = 0.0
        self.eye_blink = 0
        self.arm_phase = 0.0

    def _entry_speed(self) -> float:
        return 1.2

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 55, int(self.y) - 70, 110, 140)

    def update_behavior(self, player_rect: pygame.Rect) -> None:
        from weapons import EnemyShot
        self.arm_phase = (self.arm_phase + 0.06) % (math.pi * 2)
        self.eye_blink = (self.eye_blink + 1) % 60

        px = player_rect.centerx
        py = player_rect.centery
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy) or 1

        if self.charging:
            # Charge forward (leftward) — also track player vertically during charge
            charge_spd = self._t(8.0, 11.0, 15.0)
            self.x -= charge_spd
            self._track_player_y(player_rect, speed=self._t(3.5, 5.0, 7.0))
            self.charge_timer -= 1
            if self.charge_timer <= 0 or self.x < 200:
                self.charging = False
                self.x = float(self.STOP_X)

            # Fire spread during charge
            fire_every = self._t(8, 5, 3)
            if self.charge_timer % fire_every == 0:
                spread = self._t(3, 5, 7) if self.phase == 2 else self._t(3, 3, 5)
                for ang_off in range(-(spread//2), spread//2 + 1):
                    rad = math.radians(180 + ang_off * 15)
                    spd = self._t(6.0, 8.0, 11.0) if self.phase == 2 else self._t(4.5, 6.0, 8.0)
                    self.boss_shots.append(
                        EnemyShot(self.x - 55, self.y,
                                  math.cos(rad) * spd, math.sin(rad) * spd)
                    )
        else:
            # Idle movement: track player + strafe
            if self.is_active:
                if self.phase == 1:
                    self._track_player_y(player_rect, speed=self._t(1.6, 2.4, 3.5))
                    self._x_pulse(near=500, far=640, speed=self._t(0.016, 0.024, 0.034))
                else:
                    self._track_player_y(player_rect, speed=self._t(2.8, 4.0, 6.0))
                    self._x_pulse(near=450, far=600, speed=self._t(0.028, 0.040, 0.055))
                    self._strafe(amplitude=self._t(50, 75, 100), speed=self._t(0.04, 0.06, 0.09))

            self.shoot_timer -= 1
            if self.shoot_timer <= 0:
                if self.phase == 1:
                    self.shoot_timer = self._t(85, 55, 28)
                    spd = self._t(5.0, 7.0, 10.0)
                    shot_count = self._t(1, 2, 3)
                    for i in range(shot_count):
                        ang_off = (i - shot_count // 2) * 12
                        rad = math.atan2(dy, dx) + math.radians(ang_off)
                        self.boss_shots.append(
                            EnemyShot(self.x - 55, self.y,
                                      math.cos(rad) * spd, math.sin(rad) * spd)
                        )
                else:
                    self.shoot_timer = self._t(55, 32, 15)
                    spd = self._t(6.0, 9.0, 13.0)
                    # Homing missile + flanking spread
                    self.boss_shots.append(
                        EnemyShot(self.x - 55, self.y,
                                  dx / dist * spd, dy / dist * spd)
                    )
                    flanks = self._t([-30, 30], [-40, -15, 15, 40], [-45, -25, 0, 25, 45])
                    for ang_off in flanks:
                        rad = math.radians(180 + ang_off)
                        self.boss_shots.append(
                            EnemyShot(self.x - 55, self.y,
                                      math.cos(rad) * spd, math.sin(rad) * spd)
                        )

                    # Phase 2: frequent charges
                    charge_chance = self._t(0.45, 0.60, 0.75)
                    if random.random() < charge_chance:
                        self.charging = True
                        self.charge_timer = self._t(50, 40, 30)

    def draw_body(self, screen: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)

        # Body (main rectangle)
        pygame.draw.rect(screen, (50, 55, 60),
                         (cx - 35, cy - 40, 70, 80), border_radius=4)
        pygame.draw.rect(screen, (100, 110, 120),
                         (cx - 35, cy - 40, 70, 80), 2, border_radius=4)

        # Arm rectangles — bob slightly
        arm_bob = int(math.sin(self.arm_phase) * 4)
        # Left arm
        pygame.draw.rect(screen, (40, 45, 50),
                         (cx - 70, cy - 25 + arm_bob, 35, 20), border_radius=3)
        pygame.draw.rect(screen, (90, 100, 110),
                         (cx - 70, cy - 25 + arm_bob, 35, 20), 1, border_radius=3)
        # Right arm
        pygame.draw.rect(screen, (40, 45, 50),
                         (cx + 35, cy - 25 - arm_bob, 35, 20), border_radius=3)
        pygame.draw.rect(screen, (90, 100, 110),
                         (cx + 35, cy - 25 - arm_bob, 35, 20), 1, border_radius=3)

        # Head (circle)
        pygame.draw.circle(screen, (55, 60, 70), (cx, cy - 55), 22)
        pygame.draw.circle(screen, (100, 110, 120), (cx, cy - 55), 22, 2)

        # Angry eyes
        for ex, ey_off in [(-9, -58), (9, -58)]:
            blink_open = self.eye_blink < 54
            if blink_open:
                pygame.draw.circle(screen, (20, 0, 0),
                                   (cx + ex, cy + ey_off), 6)
                pygame.draw.circle(screen, (220, 30, 30),
                                   (cx + ex, cy + ey_off), 4)
                pygame.draw.circle(screen, (255, 80, 80),
                                   (cx + ex, cy + ey_off), 2)
            else:
                # Blink — just a line
                pygame.draw.line(screen, (200, 200, 200),
                                 (cx + ex - 5, cy + ey_off),
                                 (cx + ex + 5, cy + ey_off), 2)

        # Chest details
        pygame.draw.rect(screen, (30, 35, 40),
                         (cx - 20, cy - 20, 40, 30), border_radius=2)
        pygame.draw.rect(screen, (0, 150, 200),
                         (cx - 20, cy - 20, 40, 30), 1, border_radius=2)
        # Core glow
        draw_circle_alpha(screen, CYAN, (cx, cy - 5), 10, 80)
        pygame.draw.circle(screen, (100, 200, 255), (cx, cy - 5), 5)

        # Legs
        pygame.draw.rect(screen, (45, 50, 55), (cx - 28, cy + 40, 22, 30), border_radius=2)
        pygame.draw.rect(screen, (45, 50, 55), (cx + 6,  cy + 40, 22, 30), border_radius=2)
        pygame.draw.rect(screen, (80, 90, 100), (cx - 28, cy + 40, 22, 30), 1, border_radius=2)
        pygame.draw.rect(screen, (80, 90, 100), (cx + 6,  cy + 40, 22, 30), 1, border_radius=2)


# ── Boss Tentacle Alien ────────────────────────────────────────────────────────
class BossTentacleAlien(Boss):
    BOSS_NAME = "LEVIATHAN"
    SCORE     = 1500

    # 6 tentacle base angles (degrees)
    _TENTACLE_BASES = [30, 90, 150, 210, 270, 330]

    def __init__(self, tier: int = 1) -> None:
        super().__init__(tier)
        base_hp = self._t(160, 280, 450)
        self.hp     = base_hp
        self.max_hp = base_hp
        self.shoot_timer = self._t(80, 55, 30)
        self.spawn_timer = self._t(150, 100, 60)
        self.time_counter = 0
        self.pending_minions: list = []
        # Player last-known position for aiming
        self._player_x = float(SCREEN_W // 2)
        self._player_y = float(SCREEN_H // 2)

    def _entry_speed(self) -> float:
        return 1.0

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 55, int(self.y) - 55, 110, 110)

    def update_behavior(self, player_rect: pygame.Rect) -> None:
        from weapons import EnemyShot
        self.time_counter += 1
        self._player_x = float(player_rect.centerx)
        self._player_y = float(player_rect.centery)

        if self.is_active:
            if self.phase == 1:
                self._strafe(amplitude=130, speed=0.016)
                self._x_pulse(near=480, far=660, speed=0.012)
            else:
                self._strafe(amplitude=130, speed=0.026)
                self._x_pulse(near=460, far=640, speed=0.018)
                self._track_player_y(player_rect, speed=1.5)

        dx = self._player_x - self.x
        dy = self._player_y - self.y
        dist = math.hypot(dx, dy) or 1

        fire_interval = self._t(50, 35, 20) if self.phase == 2 else self._t(80, 55, 30)
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = fire_interval
            shot_count = self._t(6, 6, 6) if self.phase == 2 else self._t(4, 5, 6)
            spd = self._t(5.0, 7.0, 10.0)
            # Fire blobs from tentacle tips toward player
            for i in range(shot_count):
                base_ang = math.radians(self._TENTACLE_BASES[i % 6])
                tip_x = self.x + math.cos(base_ang) * 55
                tip_y = self.y + math.sin(base_ang) * 55
                tdx = self._player_x - tip_x
                tdy = self._player_y - tip_y
                tdist = math.hypot(tdx, tdy) or 1
                self.boss_shots.append(
                    EnemyShot(tip_x, tip_y, tdx / tdist * spd, tdy / tdist * spd)
                )
            # Tier 3: extra direct shot at player
            if self.tier >= 3:
                self.boss_shots.append(
                    EnemyShot(self.x, self.y, dx / dist * (spd + 2), dy / dist * (spd + 2))
                )

        # Phase 2: spawn minions
        if self.phase == 2:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                self.spawn_timer = self._t(150, 100, 60)
                self.pending_minions.append((self.x - 60, self.y - 30))
                if self.tier >= 2:
                    self.pending_minions.append((self.x - 60, self.y + 30))
                if self.tier >= 3:
                    self.pending_minions.append((self.x - 80, self.y))

    def pop_minions(self) -> list:
        m = self.pending_minions[:]
        self.pending_minions.clear()
        return m

    def draw_body(self, screen: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        t = self.time_counter

        # Draw tentacles (behind body)
        for i, base_deg in enumerate(self._TENTACLE_BASES):
            base_rad = math.radians(base_deg)
            seg_len = 22
            px_seg, py_seg = float(cx), float(cy)
            angle_acc = base_rad
            for seg in range(4):
                sway = math.sin(t * 0.05 + seg * 0.8 + i * 1.1) * math.radians(25)
                angle_acc = base_rad + sway
                nx = px_seg + math.cos(angle_acc) * seg_len
                ny = py_seg + math.sin(angle_acc) * seg_len
                r_seg = max(2, 10 - seg * 2)
                # Draw connecting line
                pygame.draw.line(screen, (0, 80, 30),
                                 (int(px_seg), int(py_seg)),
                                 (int(nx), int(ny)), max(1, r_seg - 2))
                # Draw joint circle
                pygame.draw.circle(screen, (0, 100, 40),
                                   (int(nx), int(ny)), r_seg)
                px_seg, py_seg = nx, ny

        # Main body — large dark green/purple circular body
        draw_circle_alpha(screen, (30, 120, 80), (cx, cy), 60, 60)
        pygame.draw.circle(screen, (20, 60, 40), (cx, cy), 55)
        pygame.draw.circle(screen, (60, 160, 80), (cx, cy), 55, 3)
        # Purple tint overlay
        draw_circle_alpha(screen, (80, 0, 100), (cx, cy), 40, 40)

        # Two large glowing eyes (yellow/red)
        for ex_off in [-18, 18]:
            # Outer glow
            draw_circle_alpha(screen, (200, 180, 0), (cx + ex_off, cy - 10), 14, 60)
            pygame.draw.circle(screen, (40, 20, 0), (cx + ex_off, cy - 10), 11)
            pygame.draw.circle(screen, (220, 200, 0), (cx + ex_off, cy - 10), 8)
            pygame.draw.circle(screen, (255, 60, 0), (cx + ex_off, cy - 10), 5)
            pygame.draw.circle(screen, (255, 200, 100), (cx + ex_off - 2, cy - 12), 2)

        # Mouth slit
        pygame.draw.arc(screen, (0, 60, 20),
                        (cx - 18, cy + 10, 36, 18),
                        math.pi, 2 * math.pi, 3)


# ── Boss Warship ──────────────────────────────────────────────────────────────
class BossWarship(Boss):
    BOSS_NAME = "DREADNOUGHT"
    SCORE     = 2200

    def __init__(self, tier: int = 1) -> None:
        super().__init__(tier)
        base_hp = self._t(220, 380, 600)
        self.hp     = base_hp
        self.max_hp = base_hp
        # 3 turret timers staggered, turret angles all start pointing left
        stagger = self._t(33, 22, 12)
        self.turret_timers = [0, stagger, stagger * 2]
        self.turret_angles = [180.0, 180.0, 180.0]   # degrees
        self._player_x = float(SCREEN_W // 2)
        self._player_y = float(SCREEN_H // 2)
        self._lateral_dash_timer = 0
        self._dash_vy = 0.0

    def _entry_speed(self) -> float:
        return 0.8

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 100, int(self.y) - 35, 200, 70)

    # Turret x offsets from centre
    _TURRET_OX = [-60, 0, 60]

    def update_behavior(self, player_rect: pygame.Rect) -> None:
        from weapons import EnemyShot
        self._player_x = float(player_rect.centerx)
        self._player_y = float(player_rect.centery)

        if self.is_active:
            if self.phase == 1:
                self._strafe(amplitude=self._t(100, 120, 150),
                             speed=self._t(0.014, 0.022, 0.034))
                self._x_pulse(near=self._t(460, 430, 400),
                               far=self._t(640, 660, 680),
                               speed=self._t(0.011, 0.018, 0.028))
            else:
                self._strafe(amplitude=self._t(100, 130, 170),
                             speed=self._t(0.020, 0.032, 0.050))
                self._x_pulse(near=self._t(440, 410, 380),
                               far=self._t(620, 640, 660),
                               speed=self._t(0.016, 0.026, 0.042))
                # Lateral dashes — more frequent and faster at higher tiers
                self._lateral_dash_timer -= 1
                dash_interval_lo = self._t(80, 50, 25)
                dash_interval_hi = self._t(150, 90, 45)
                if self._lateral_dash_timer <= 0:
                    self._lateral_dash_timer = random.randint(dash_interval_lo, dash_interval_hi)
                    dash_spd = self._t(4.0, 7.0, 12.0)
                    self._dash_vy = random.choice([-dash_spd, dash_spd])
                if abs(self._dash_vy) > 0.1:
                    self.y += self._dash_vy
                    self.y = max(80, min(SCREEN_H - 80, self.y))
                    self._dash_vy *= self._t(0.85, 0.88, 0.92)   # dampen

        # Update turret angles — track player; tier 3 snaps fast
        for i, ox in enumerate(self._TURRET_OX):
            tx = self.x + ox
            ty = self.y - 28
            tdx = self._player_x - tx
            tdy = self._player_y - ty
            target_angle = math.degrees(math.atan2(tdy, tdx))
            diff = (target_angle - self.turret_angles[i] + 180) % 360 - 180
            lag = self._t(3.0, 5.0, 10.0) if self.phase == 1 else self._t(5.0, 8.0, 15.0)
            self.turret_angles[i] += max(-lag, min(lag, diff))

        # Fire timers per turret
        fire_interval = self._t(60, 35, 12) if self.phase == 2 else self._t(100, 60, 22)
        for i in range(3):
            self.turret_timers[i] -= 1
            if self.turret_timers[i] <= 0:
                self.turret_timers[i] = fire_interval
                tx = self.x + self._TURRET_OX[i]
                ty = self.y - 28
                rad = math.radians(self.turret_angles[i])
                spd = self._t(6.0, 8.5, 12.0) if self.phase == 2 else self._t(5.0, 7.0, 10.0)

                # Tier 3: 5-way spread per turret; tier 2: 3-way; tier 1: single shot
                spread_offsets = self._t([0], [-10, 0, 10], [-20, -10, 0, 10, 20])
                for ang_off in spread_offsets:
                    shot_rad = rad + math.radians(ang_off)
                    self.boss_shots.append(
                        EnemyShot(tx, ty, math.cos(shot_rad) * spd, math.sin(shot_rad) * spd)
                    )

                # Phase 2: torpedoes from prow
                if self.phase == 2:
                    torp_count = self._t(2, 4, 6)
                    torp_vys = []
                    if torp_count == 2:
                        torp_vys = [-2.0, 2.0]
                    elif torp_count == 4:
                        torp_vys = [-4.0, -1.5, 1.5, 4.0]
                    else:
                        torp_vys = [-5.0, -3.0, -1.0, 1.0, 3.0, 5.0]
                    torp_spd = self._t(5.5, 7.5, 10.0)
                    for vy_torp in torp_vys:
                        self.boss_shots.append(
                            EnemyShot(self.x - 100, self.y, -torp_spd, vy_torp)
                        )

    def draw_body(self, screen: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)

        # Engine pods at rear (back = right side since boss faces left)
        for ey_off in [-18, 18]:
            draw_circle_alpha(screen, ORANGE, (cx + 90, cy + ey_off), 14, 80)
            pygame.draw.circle(screen, (255, 140, 0), (cx + 90, cy + ey_off), 8)
            pygame.draw.circle(screen, (255, 200, 100), (cx + 90, cy + ey_off), 4)

        # Main hull
        pygame.draw.rect(screen, (45, 50, 60),
                         (cx - 100, cy - 28, 200, 56), border_radius=4)
        pygame.draw.rect(screen, (100, 110, 130),
                         (cx - 100, cy - 28, 200, 56), 2, border_radius=4)

        # Armour plating lines across hull
        for off in [-50, 0, 50]:
            pygame.draw.line(screen, (70, 80, 95),
                             (cx + off - 10, cy - 28),
                             (cx + off + 10, cy + 28), 1)

        # Prow triangle pointing left
        prow_pts = [
            (cx - 100, cy),
            (cx - 80,  cy - 20),
            (cx - 80,  cy + 20),
        ]
        pygame.draw.polygon(screen, (60, 65, 75), prow_pts)
        pygame.draw.polygon(screen, (120, 130, 150), prow_pts, 2)

        # 3 gun turrets on top
        for i, ox in enumerate(self._TURRET_OX):
            tx = cx + ox
            ty = cy - 28
            # Turret base
            pygame.draw.rect(screen, (35, 40, 50),
                             (tx - 8, ty - 8, 16, 16), border_radius=2)
            pygame.draw.rect(screen, (90, 100, 120),
                             (tx - 8, ty - 8, 16, 16), 1, border_radius=2)
            # Barrel pointing toward player
            angle_rad = math.radians(self.turret_angles[i])
            bx_end = tx + int(math.cos(angle_rad) * 18)
            by_end = ty + int(math.sin(angle_rad) * 18)
            pygame.draw.line(screen, (120, 130, 150),
                             (tx, ty), (bx_end, by_end), 3)
            pygame.draw.circle(screen, (80, 90, 110), (tx, ty), 5)


# ── Boss Manager ───────────────────────────────────────────────────────────────
class BossManager:
    # (score_threshold, boss_class, tier)  — each boss type appears exactly once
    # Level boundaries: 3k, 7.5k, 14k, 23k, 36k, 54k, 78k, 110k, 150k
    THRESHOLDS = [
        (1500,  BossAsteroid,      1),  # mid-level 1
        (5200,  BossAlienCruiser,  1),  # mid-level 2
        (10500, BossMechaTitan,    2),  # mid-level 3 — harder
        (18000, BossTentacleAlien, 2),  # mid-level 4 — hard
        (29000, BossWarship,       3),  # mid-level 5 — almost unplayable
    ]

    def __init__(self) -> None:
        self.current_boss: Boss | None = None
        self.defeated_scores: set = set()
        self.warning_timer: int = 0
        self.warning_active: bool = False
        self._pending_boss_class = None
        self._pending_boss_tier: int = 1
        self._boss_death_events: list[tuple] = []   # (x, y) for explosion
        self._score_events: list[int] = []
        # Pending minion spawns from bosses that have pop_minions
        self._pending_minions: list[tuple] = []

    @property
    def boss_active(self) -> bool:
        return self.current_boss is not None and not self.current_boss.is_dead

    def check_spawn(self, score: int) -> None:
        """Check if score crossed a new threshold. Trigger warning if so."""
        if self.boss_active or self.warning_active:
            return
        for threshold, boss_cls, tier in self.THRESHOLDS:
            if score >= threshold and threshold not in self.defeated_scores:
                self.warning_active = True
                self.warning_timer = 120
                self._pending_boss_class = boss_cls
                self._pending_boss_tier = tier
                break

    def update(self, player_rect: pygame.Rect) -> None:
        # Warning countdown
        if self.warning_active:
            self.warning_timer -= 1
            if self.warning_timer <= 0:
                self.warning_active = False
                if self._pending_boss_class is not None:
                    self.current_boss = self._pending_boss_class(self._pending_boss_tier)
                    self._pending_boss_class = None

        if self.current_boss is None:
            return

        if self.current_boss.is_dead:
            # Record death event
            ex, ey = int(self.current_boss.x), int(self.current_boss.y)
            self._boss_death_events.append((ex, ey))
            # Track defeated threshold
            for threshold, boss_cls, _tier in self.THRESHOLDS:
                if threshold not in self.defeated_scores and \
                        isinstance(self.current_boss, boss_cls):
                    self.defeated_scores.add(threshold)
                    self._score_events.append(self.current_boss.SCORE)
                    break
            self.current_boss = None
            return

        self.current_boss.update(player_rect)

        # Collect minion spawns from any boss that supports pop_minions
        if hasattr(self.current_boss, 'pop_minions'):
            self._pending_minions += self.current_boss.pop_minions()

    def pop_minions(self) -> list:
        m = self._pending_minions[:]
        self._pending_minions.clear()
        return m

    def check_player_shots(self, projectiles: list) -> int:
        """Damage boss from player projectiles; return score if killed."""
        if self.current_boss is None or self.current_boss.is_dead:
            return 0
        score = 0
        boss_rect = self.current_boss.get_rect()
        for proj in projectiles:
            if proj.owner != "player" or proj.dead:
                continue
            if proj.get_rect().colliderect(boss_rect):
                self.current_boss.take_damage(proj.damage)
                proj.kill()
                if self.current_boss.is_dead:
                    # Score collected in update() on next frame
                    break
        return score

    def pop_score_events(self) -> list[int]:
        evts = self._score_events[:]
        self._score_events.clear()
        return evts

    def check_player_shot_hits(self, player_rect: pygame.Rect) -> bool:
        """Check if any boss shot hits the player. Returns True if hit."""
        if self.current_boss is None:
            return False
        for shot in self.current_boss.boss_shots[:]:
            if not shot.dead and player_rect.colliderect(shot.get_rect()):
                shot.kill()
                return True
        return False

    def pop_shots(self) -> list:
        if self.current_boss is None:
            return []
        return self.current_boss.pop_shots()

    def pop_boss_death_events(self) -> list[tuple]:
        evts = self._boss_death_events[:]
        self._boss_death_events.clear()
        return evts

    def draw(self, screen: pygame.Surface) -> None:
        if self.warning_active:
            self.draw_warning(screen)

        if self.current_boss and not self.current_boss.is_dead:
            self.current_boss.draw(screen)
            # Draw boss shots
            for shot in self.current_boss.boss_shots:
                shot.draw(screen)

    def draw_health_bar(self, screen: pygame.Surface) -> None:
        if self.current_boss and not self.current_boss.is_dead:
            self.current_boss.draw_health_bar(screen)

    def draw_warning(self, screen: pygame.Surface) -> None:
        """Flashing BOSS APPROACHING warning at screen centre."""
        ticks = pygame.time.get_ticks()
        blink_on = (ticks // 300) % 2 == 0

        # Dim overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((40, 0, 0, 80))
        screen.blit(overlay, (0, 0))

        try:
            font_big  = pygame.font.SysFont("consolas,courier,monospace", 42, bold=True)
            font_small = pygame.font.SysFont("consolas,courier,monospace", 20, bold=True)

            if blink_on:
                txt_surf = font_big.render("!! BOSS APPROACHING !!", True, RED)
            else:
                txt_surf = font_big.render("!! BOSS APPROACHING !!", True, YELLOW)

            cx = SCREEN_W // 2
            cy = SCREEN_H // 2

            # Shadow
            shadow = font_big.render("!! BOSS APPROACHING !!", True, (60, 0, 0))
            screen.blit(shadow, (cx - shadow.get_width() // 2 + 3,
                                 cy - shadow.get_height() // 2 + 3))
            screen.blit(txt_surf, (cx - txt_surf.get_width() // 2,
                                   cy - txt_surf.get_height() // 2))

            sub = font_small.render("PREPARE FOR BATTLE", True, YELLOW)
            screen.blit(sub, (cx - sub.get_width() // 2, cy + 35))
        except Exception:
            pass
