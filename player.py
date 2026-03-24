# player.py — Player and ShadowClone

import pygame
import math
from assets import (WHITE, GREY, CYAN, BLUE, RED, YELLOW, GREEN,
                    draw_circle_alpha)
from weapons import WeaponSystem, EnemyShot

SCREEN_W = 800
SCREEN_H = 600

# ── Astronaut colour scheme (orange/gold spacesuit, electric-blue visor) ──────
_SUIT_BODY     = (220, 140, 50)    # warm orange — primary suit colour
_SUIT_LIGHT    = (245, 170, 70)    # lighter orange for chest highlight
_SUIT_SHADOW   = (160, 90,  30)    # darker orange for edges/legs
_HELMET        = (230, 150, 60)    # orange with slight gold tint
_VISOR_DEFAULT = (30,  160, 255)   # electric blue visor
_VISOR_SHINE   = (150, 220, 255)   # light-blue visor shine
_GLOVES_BOOTS  = (80,  50,  20)    # dark brown gloves & boots
_JETPACK       = (60,  40,  20)    # very dark brown jetpack body
_JETPACK_GLOW  = (0,   220, 255)   # cyan glow nozzle


# ── Helper: draw astronaut at (cx, cy) ────────────────────────────────────────
def draw_astronaut(surface: pygame.Surface, cx: int, cy: int,
                   alpha: int = 255, scale: float = 1.0,
                   visor_color=None) -> None:
    """Draw a cute astronaut using primitives (orange/gold suit, electric-blue visor)."""
    if visor_color is None:
        visor_color = _VISOR_DEFAULT

    def s(v: int) -> int:
        return max(1, int(v * scale))

    bw, bh = s(22), s(26)

    if alpha < 255:
        tmp_w = bw + s(40)
        tmp_h = bh + s(50)
        tmp = pygame.Surface((tmp_w, tmp_h), pygame.SRCALPHA)
        ox, oy = tmp_w // 2, tmp_h // 2

        def ts(v):
            return max(1, int(v * scale))

        # body — orange suit
        pygame.draw.rect(tmp, (*_SUIT_BODY, alpha),
                         (ox - ts(11), oy - ts(7), ts(22), ts(26)))
        # chest highlight
        pygame.draw.rect(tmp, (*_SUIT_LIGHT, alpha),
                         (ox - ts(6), oy - ts(5), ts(10), ts(14)))
        # helmet
        pygame.draw.circle(tmp, (*_HELMET, alpha), (ox, oy - ts(16)), ts(14))
        # visor
        r, g, b = visor_color
        pygame.draw.ellipse(tmp, (r, g, b, alpha),
                            (ox - ts(8), oy - ts(23), ts(16), ts(12)))
        # visor shine
        pygame.draw.ellipse(tmp, (*_VISOR_SHINE, min(alpha, 200)),
                            (ox - ts(5), oy - ts(21), ts(5), ts(4)))
        # arms
        pygame.draw.line(tmp, (*_SUIT_SHADOW, alpha),
                         (ox - ts(11), oy - ts(3)),
                         (ox - ts(20), oy + ts(8)), ts(4))
        pygame.draw.line(tmp, (*_SUIT_SHADOW, alpha),
                         (ox + ts(11), oy - ts(3)),
                         (ox + ts(20), oy + ts(8)), ts(4))
        # gloves
        pygame.draw.circle(tmp, (*_GLOVES_BOOTS, alpha),
                           (ox - ts(20), oy + ts(8)), ts(4))
        pygame.draw.circle(tmp, (*_GLOVES_BOOTS, alpha),
                           (ox + ts(20), oy + ts(8)), ts(4))
        # legs
        pygame.draw.rect(tmp, (*_SUIT_SHADOW, alpha),
                         (ox - ts(10), oy + ts(19), ts(8), ts(12)))
        pygame.draw.rect(tmp, (*_SUIT_SHADOW, alpha),
                         (ox + ts(2), oy + ts(19), ts(8), ts(12)))
        # boots
        pygame.draw.rect(tmp, (*_GLOVES_BOOTS, alpha),
                         (ox - ts(12), oy + ts(29), ts(12), ts(5)))
        pygame.draw.rect(tmp, (*_GLOVES_BOOTS, alpha),
                         (ox,          oy + ts(29), ts(12), ts(5)))
        # jetpack body
        pygame.draw.rect(tmp, (*_JETPACK, alpha),
                         (ox + ts(10), oy - ts(4), ts(7), ts(16)))
        # jetpack nozzle glow
        pygame.draw.circle(tmp, (*_JETPACK_GLOW, alpha),
                           (ox + ts(14), oy + ts(14)), ts(3))

        surface.blit(tmp, (cx - tmp_w // 2, cy - tmp_h // 2))
        return

    # ─ Opaque fast path ───────────────────────────────────────────────────────
    # body
    pygame.draw.rect(surface, _SUIT_BODY,
                     (cx - s(11), cy - s(7), s(22), s(26)))
    # chest highlight
    pygame.draw.rect(surface, _SUIT_LIGHT,
                     (cx - s(6), cy - s(5), s(10), s(14)))
    # helmet
    pygame.draw.circle(surface, _HELMET, (cx, cy - s(16)), s(14))
    # visor
    pygame.draw.ellipse(surface, visor_color,
                        (cx - s(8), cy - s(23), s(16), s(12)))
    # visor shine
    pygame.draw.ellipse(surface, _VISOR_SHINE,
                        (cx - s(5), cy - s(21), s(5), s(4)))
    # arms
    pygame.draw.line(surface, _SUIT_SHADOW,
                     (cx - s(11), cy - s(3)), (cx - s(20), cy + s(8)), s(4))
    pygame.draw.line(surface, _SUIT_SHADOW,
                     (cx + s(11), cy - s(3)), (cx + s(20), cy + s(8)), s(4))
    # gloves
    pygame.draw.circle(surface, _GLOVES_BOOTS, (cx - s(20), cy + s(8)), s(4))
    pygame.draw.circle(surface, _GLOVES_BOOTS, (cx + s(20), cy + s(8)), s(4))
    # legs
    pygame.draw.rect(surface, _SUIT_SHADOW,
                     (cx - s(10), cy + s(19), s(8), s(12)))
    pygame.draw.rect(surface, _SUIT_SHADOW,
                     (cx + s(2),  cy + s(19), s(8), s(12)))
    # boots
    pygame.draw.rect(surface, _GLOVES_BOOTS,
                     (cx - s(12), cy + s(29), s(12), s(5)))
    pygame.draw.rect(surface, _GLOVES_BOOTS,
                     (cx,         cy + s(29), s(12), s(5)))
    # jetpack body
    pygame.draw.rect(surface, _JETPACK,
                     (cx + s(10), cy - s(4), s(7), s(16)))
    # jetpack nozzle glow
    pygame.draw.circle(surface, _JETPACK_GLOW,
                       (cx + s(14), cy + s(14)), s(3))


# ── Shadow Clone ──────────────────────────────────────────────────────────────
class ShadowClone:
    TRAIL_LEN  = 30
    MAX_HEALTH = 3

    def __init__(self, player_x: float, player_y: float) -> None:
        self.trail: list[tuple] = [(player_x, player_y)] * self.TRAIL_LEN
        self.x = player_x
        self.y = player_y
        self.health = self.MAX_HEALTH
        self._dead = False
        self.shoot_cooldown = 0

    @property
    def dead(self) -> bool:
        return self._dead

    def take_hit(self) -> None:
        self.health -= 1
        if self.health <= 0:
            self._dead = True

    def update(self, player_x: float, player_y: float) -> None:
        if self._dead:
            return
        self.trail.append((player_x, player_y))
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)
        self.x, self.y = self.trail[0]
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

    def fire(self, weapon_system: WeaponSystem) -> list:
        if self._dead or self.shoot_cooldown > 0:
            return []
        self.shoot_cooldown = 12
        return weapon_system.fire((self.x, self.y))

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 18, int(self.y) - 35, 36, 65)

    def draw(self, screen: pygame.Surface) -> None:
        if self._dead:
            return
        # Blue-tinted clone — keep visor blue, suit tinted blue
        draw_astronaut(screen, int(self.x), int(self.y),
                       alpha=120, visor_color=(30, 160, 255))
        # HP bar
        for i in range(self.MAX_HEALTH):
            col = (0, 230, 255) if i < self.health else (40, 40, 80)
            pygame.draw.circle(screen, col,
                               (int(self.x) - 8 + i * 9, int(self.y) - 42), 3)


# ── Player ────────────────────────────────────────────────────────────────────
class Player:
    SPEED        = 5
    MAX_HP       = 5
    MAX_LIVES    = 5
    INVINCIBLE_F = 60
    FIRE_COOLDOWN = 10

    def __init__(self) -> None:
        self.x = 120.0
        self.y = SCREEN_H / 2
        self.hp    = self.MAX_HP
        self.lives = self.MAX_LIVES
        self.invincibility_frames = 0
        self.fire_cooldown = 0
        self.weapon_system = WeaponSystem()
        self.shadow_clone: ShadowClone | None = None
        self._flash_on = True
        self._flash_timer = 0
        self.reversed_controls: bool = False
        self.bombs: int = 1   # start with one bomb

    # ── Collision rect ────────────────────────────────────────────────────────
    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 18, int(self.y) - 35, 36, 65)

    # ── Properties ────────────────────────────────────────────────────────────
    @property
    def is_dead(self) -> bool:
        return self.lives <= 0

    @property
    def invincible(self) -> bool:
        return self.invincibility_frames > 0

    # ── Damage ────────────────────────────────────────────────────────────────
    def take_damage(self) -> None:
        if self.invincible:
            return
        self.hp -= 1
        self.invincibility_frames = self.INVINCIBLE_F
        if self.hp <= 0:
            self.lives -= 1
            self.hp = self.MAX_HP if self.lives > 0 else 0

    # ── Power-ups ────────────────────────────────────────────────────────────
    def add_shadow(self) -> None:
        if self.shadow_clone is None or self.shadow_clone.dead:
            self.shadow_clone = ShadowClone(self.x, self.y)

    def upgrade_weapon(self, w_type: str | None = None) -> None:
        if w_type:
            self.weapon_system.shot_type = w_type
        else:
            self.weapon_system.upgrade_type()

    def upgrade_speed(self) -> None:
        self.weapon_system.upgrade_speed()

    def upgrade_multishot(self) -> None:
        self.weapon_system.upgrade_multishot()

    def heal(self, amount: int = 2) -> None:
        self.hp = min(self.hp + amount, self.MAX_HP)

    def add_bomb(self) -> None:
        self.bombs = min(self.bombs + 1, 9)

    # ── Update ───────────────────────────────────────────────────────────────
    def update(self, keys: pygame.key.ScancodeWrapper) -> list:
        """Move player and return new projectiles."""
        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += 1

        # Apply reversed controls before diagonal normalise
        if self.reversed_controls:
            dx, dy = -dx, -dy

        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071

        speed = self.SPEED
        self.x = max(20, min(SCREEN_W - 20, self.x + dx * speed))
        self.y = max(40, min(SCREEN_H - 40, self.y + dy * speed))

        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1
            self._flash_timer += 1
            if self._flash_timer >= 5:
                self._flash_on = not self._flash_on
                self._flash_timer = 0
        else:
            self._flash_on = True

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        new_shots: list = []
        if self.shadow_clone and not self.shadow_clone.dead:
            self.shadow_clone.update(self.x, self.y)

        return new_shots

    def handle_shoot(self, keys: pygame.key.ScancodeWrapper,
                     mouse_buttons: tuple) -> list:
        """Return new projectiles if the player shoots this frame."""
        shooting = keys[pygame.K_SPACE] or mouse_buttons[0]
        if not shooting or self.fire_cooldown > 0:
            return []
        self.fire_cooldown = self.FIRE_COOLDOWN
        shots = self.weapon_system.fire((self.x, self.y))
        if self.shadow_clone and not self.shadow_clone.dead:
            shots += self.shadow_clone.fire(self.weapon_system)
        return shots

    # ── Draw ─────────────────────────────────────────────────────────────────
    def draw(self, screen: pygame.Surface) -> None:
        if self.shadow_clone and not self.shadow_clone.dead:
            self.shadow_clone.draw(screen)

        if not self._flash_on:
            return

        draw_astronaut(screen, int(self.x), int(self.y))

        # HP dots below the sprite
        for i in range(self.MAX_HP):
            col = RED if i < self.hp else (60, 20, 20)
            pygame.draw.circle(screen, col,
                               (int(self.x) - 10 + i * 10, int(self.y) + 44), 4)
