# weapons.py — Projectile and weapon system

import pygame
import math
import random
from assets import CYAN, ORANGE, PURPLE, RED, WHITE, YELLOW

# ── Weapon type constants ──────────────────────────────────────────────────────
LASER    = "LASER"
FIRE     = "FIRE"
MAGNETIC = "MAGNETIC"

WEAPON_ORDER = [LASER, FIRE, MAGNETIC]


# ── Particle for fire trail ────────────────────────────────────────────────────
class Particle:
    def __init__(self, x: float, y: float) -> None:
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(0.5, 2.0)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(8, 18)
        self.max_life = self.life
        self.color = random.choice([ORANGE, YELLOW, (255, 60, 0)])
        self.radius = random.randint(1, 3)

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    @property
    def dead(self) -> bool:
        return self.life <= 0

    def draw(self, screen: pygame.Surface) -> None:
        alpha = int(255 * self.life / self.max_life)
        r, g, b = self.color
        tmp = pygame.Surface((self.radius * 2 + 2, self.radius * 2 + 2),
                              pygame.SRCALPHA)
        pygame.draw.circle(tmp, (r, g, b, alpha),
                           (self.radius + 1, self.radius + 1), self.radius)
        screen.blit(tmp, (int(self.x) - self.radius - 1,
                          int(self.y) - self.radius - 1))


# ── Base Projectile ────────────────────────────────────────────────────────────
class Projectile:
    def __init__(self, x: float, y: float, vx: float, vy: float,
                 damage: int, owner: str = "player") -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.owner = owner          # "player" or "enemy"
        self._dead = False

    @property
    def dead(self) -> bool:
        return self._dead

    def kill(self) -> None:
        self._dead = True

    def update(self, enemies=None) -> None:
        self.x += self.vx
        self.y += self.vy
        if (self.x < -50 or self.x > 850 or
                self.y < -50 or self.y > 650):
            self._dead = True

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 4, int(self.y) - 4, 8, 8)

    def draw(self, screen: pygame.Surface) -> None:
        pass


# ── Laser Shot ────────────────────────────────────────────────────────────────
class LaserShot(Projectile):
    LENGTH = 18

    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        super().__init__(x, y, vx, vy, damage=1)
        # Normalise direction for tail
        mag = math.hypot(vx, vy) or 1
        self._nx = vx / mag
        self._ny = vy / mag

    def draw(self, screen: pygame.Surface) -> None:
        ex = int(self.x - self._nx * self.LENGTH)
        ey = int(self.y - self._ny * self.LENGTH)
        pygame.draw.line(screen, CYAN, (int(self.x), int(self.y)), (ex, ey), 3)
        pygame.draw.line(screen, WHITE, (int(self.x), int(self.y)), (ex, ey), 1)


# ── Fire Shot ─────────────────────────────────────────────────────────────────
class FireShot(Projectile):
    RADIUS = 6

    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        super().__init__(x, y, vx, vy, damage=2)
        self.particles: list[Particle] = []

    def update(self, enemies=None) -> None:
        super().update(enemies)
        # Spawn trail particles
        if not self._dead:
            for _ in range(2):
                self.particles.append(Particle(self.x, self.y))
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.dead]

    def draw(self, screen: pygame.Surface) -> None:
        for p in self.particles:
            p.draw(screen)
        pygame.draw.circle(screen, ORANGE,
                           (int(self.x), int(self.y)), self.RADIUS)
        pygame.draw.circle(screen, YELLOW,
                           (int(self.x), int(self.y)), self.RADIUS - 2)


# ── Magnetic Shot ─────────────────────────────────────────────────────────────
class MagneticShot(Projectile):
    RADIUS = 8
    PULL_RANGE = 150
    PULL_START = 40   # frames until it starts pulling
    EXPLODE_AT = 60   # frames until explosion

    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        super().__init__(x, y, vx, vy, damage=3)
        self.frame = 0
        self.pulse = 0.0
        self._exploded = False
        self._pulled_enemies: list = []   # filled by EnemyManager

    @property
    def pulling(self) -> bool:
        return self.PULL_START <= self.frame < self.EXPLODE_AT

    @property
    def exploding(self) -> bool:
        return self.frame >= self.EXPLODE_AT and not self._exploded

    def update(self, enemies=None) -> None:
        self.frame += 1
        self.pulse = (self.pulse + 0.25) % (math.pi * 2)

        if self.frame >= self.EXPLODE_AT:
            if not self._exploded:
                self._exploded = True
                self._dead = True
            return

        # Stop moving while pulling
        if not self.pulling:
            super().update(enemies)
        else:
            # Pull enemies
            if enemies:
                for seq in enemies:
                    for enemy in seq.enemies:
                        dx = self.x - enemy.x
                        dy = self.y - enemy.y
                        dist = math.hypot(dx, dy)
                        if 0 < dist < self.PULL_RANGE:
                            force = 1.5
                            enemy.x += dx / dist * force
                            enemy.y += dy / dist * force

    def draw(self, screen: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        glow = int(self.RADIUS + 4 + math.sin(self.pulse) * 3)
        from assets import draw_circle_alpha
        draw_circle_alpha(screen, PURPLE, (cx, cy), glow + 6, 60)
        pygame.draw.circle(screen, PURPLE, (cx, cy), self.RADIUS)
        pygame.draw.circle(screen, (200, 120, 255), (cx, cy), self.RADIUS - 3)
        # concentric ring
        pygame.draw.circle(screen, PURPLE, (cx, cy), glow, 1)


# ── Enemy projectile (red dot) ─────────────────────────────────────────────────
class EnemyShot(Projectile):
    RADIUS = 4

    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        super().__init__(x, y, vx, vy, damage=1, owner="enemy")

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), self.RADIUS)
        pygame.draw.circle(screen, (255, 120, 120),
                           (int(self.x), int(self.y)), self.RADIUS - 1)


# ── Weapon System ─────────────────────────────────────────────────────────────
class WeaponSystem:
    MAX_SPEED_MULT = 3.0
    MAX_MULTISHOT  = 5
    SPREAD_ANGLE   = 15   # degrees between multishot rays

    def __init__(self) -> None:
        self.shot_type: str = LASER
        self.bullet_speed_multiplier: float = 1.0
        self.multishot_count: int = 1

    # ── Factory ───────────────────────────────────────────────────────────────
    def _make_shot(self, x: float, y: float,
                   vx: float, vy: float) -> Projectile:
        if self.shot_type == LASER:
            return LaserShot(x, y, vx, vy)
        elif self.shot_type == FIRE:
            return FireShot(x, y, vx, vy)
        else:
            return MagneticShot(x, y, vx, vy)

    def _base_speed(self) -> float:
        if self.shot_type == LASER:
            return 12.0
        elif self.shot_type == FIRE:
            return 8.0
        else:
            return 6.0

    # ── Fire ──────────────────────────────────────────────────────────────────
    def fire(self, player_pos: tuple, direction: tuple = (1, 0)) -> list:
        """Return a list of new Projectile objects."""
        shots: list[Projectile] = []
        base_angle = math.atan2(direction[1], direction[0])
        speed = self._base_speed() * self.bullet_speed_multiplier

        # Compute spread angles
        if self.multishot_count == 1:
            angles = [base_angle]
        else:
            spread_rad = math.radians(self.SPREAD_ANGLE)
            half = (self.multishot_count - 1) / 2.0
            angles = [base_angle + spread_rad * (i - half)
                      for i in range(self.multishot_count)]

        px, py = player_pos
        for angle in angles:
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            shots.append(self._make_shot(px + 20, py, vx, vy))

        return shots

    # ── Upgrades ──────────────────────────────────────────────────────────────
    def upgrade_speed(self) -> None:
        self.bullet_speed_multiplier = min(
            self.bullet_speed_multiplier * 1.3, self.MAX_SPEED_MULT)

    def upgrade_multishot(self) -> None:
        self.multishot_count = min(self.multishot_count + 1, self.MAX_MULTISHOT)

    def upgrade_type(self) -> None:
        idx = WEAPON_ORDER.index(self.shot_type)
        self.shot_type = WEAPON_ORDER[(idx + 1) % len(WEAPON_ORDER)]

    # ── Global projectile list helpers ────────────────────────────────────────
    def update_projectiles(self, projectiles: list,
                           enemy_sequences=None) -> None:
        for p in projectiles:
            p.update(enemy_sequences)
        # Remove dead
        for p in projectiles[:]:
            if p.dead:
                projectiles.remove(p)

    def draw_projectiles(self, screen: pygame.Surface,
                         projectiles: list) -> None:
        for p in projectiles:
            p.draw(screen)
