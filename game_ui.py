# game_ui.py — HUD and screen overlays

import pygame
import math
from assets import (WHITE, GREY, CYAN, YELLOW, RED, GREEN, PURPLE,
                    DARK_BLUE, draw_circle_alpha, draw_star_shape)
from weapons import LASER, FIRE, MAGNETIC

SCREEN_W = 800
SCREEN_H = 600

_font_cache: dict = {}

# Level flavour text
_LEVEL_FLAVOUR = {
    1: "Venture into the unknown...",
    2: "The nebula hides many dangers.",
    3: "Alien creatures swarm the hive.",
    4: "They know you're here.",
    5: "Absolute zero. Absolute danger.",
    6: "The void burns.",
    7: "There is no return.",
}


def _font(size: int) -> pygame.font.Font:
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont("consolas,courier,monospace",
                                                size, bold=True)
    return _font_cache[size]


def _text(screen: pygame.Surface, msg: str, size: int,
          color: tuple, cx: int, cy: int,
          anchor: str = "center") -> None:
    surf = _font(size).render(msg, True, color)
    r = surf.get_rect()
    if anchor == "center":
        r.center = (cx, cy)
    elif anchor == "topleft":
        r.topleft = (cx, cy)
    elif anchor == "topright":
        r.topright = (cx, cy)
    screen.blit(surf, r)


# ── Tiny astronaut icon for lives ─────────────────────────────────────────────
def _draw_mini_astronaut(screen: pygame.Surface, cx: int, cy: int,
                         alive: bool = True) -> None:
    col = WHITE if alive else (60, 60, 80)
    vis = CYAN if alive else (30, 40, 60)
    pygame.draw.circle(screen, col, (cx, cy - 8), 6)
    pygame.draw.ellipse(screen, vis, (cx - 4, cy - 12, 8, 6))
    pygame.draw.rect(screen, col, (cx - 5, cy - 2, 10, 10))
    pygame.draw.line(screen, col, (cx - 5, cy + 1), (cx - 9, cy + 6), 2)
    pygame.draw.line(screen, col, (cx + 5, cy + 1), (cx + 9, cy + 6), 2)


# ── Weapon type icon (top-right) ──────────────────────────────────────────────
def _draw_weapon_icon(screen: pygame.Surface, cx: int, cy: int,
                      shot_type: str) -> None:
    if shot_type == LASER:
        pygame.draw.line(screen, CYAN, (cx - 14, cy), (cx + 14, cy), 3)
        pygame.draw.line(screen, WHITE, (cx - 14, cy), (cx + 14, cy), 1)
    elif shot_type == FIRE:
        pygame.draw.circle(screen, (255, 120, 0), (cx, cy), 8)
        pygame.draw.circle(screen, YELLOW, (cx, cy), 4)
    elif shot_type == MAGNETIC:
        draw_circle_alpha(screen, PURPLE, (cx, cy), 12, 80)
        pygame.draw.circle(screen, PURPLE, (cx, cy), 8)
        pygame.draw.circle(screen, (200, 120, 255), (cx, cy), 4)
        pygame.draw.circle(screen, PURPLE, (cx, cy), 12, 1)


# ── Level transition overlay ──────────────────────────────────────────────────
def draw_level_transition(screen: pygame.Surface, level: int,
                          world_name: str, timer: int) -> None:
    """Draw the level transition banner.

    timer counts down 180 → 0 at 60 fps (3 seconds).
      180–150  (0.5 s): slide in from top
      150–30   (2.0 s): fully visible
       30–0    (0.5 s): fade out
    """
    overlay_h = 300
    overlay_y_final = (SCREEN_H - overlay_h) // 2   # centred vertically

    # Slide-in phase: timer 180 → 150
    if timer > 150:
        progress = (180 - timer) / 30.0          # 0.0 → 1.0
        # Ease out: smoothstep
        progress = progress * progress * (3 - 2 * progress)
        overlay_y = -overlay_h + int((overlay_y_final + overlay_h) * progress)
        alpha = 255
    elif timer > 30:
        overlay_y = overlay_y_final
        alpha = 255
    else:
        # Fade out: timer 30 → 0
        overlay_y = overlay_y_final
        alpha = int(255 * (timer / 30.0))

    alpha = max(0, min(255, alpha))

    # Dark panel
    panel = pygame.Surface((SCREEN_W, overlay_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, min(alpha, 210)))
    # Cyan top and bottom border lines
    border_a = min(alpha, 255)
    pygame.draw.line(panel, (0, 220, 255, border_a), (0, 0), (SCREEN_W, 0), 2)
    pygame.draw.line(panel, (0, 220, 255, border_a), (0, overlay_h - 2),
                     (SCREEN_W, overlay_h - 2), 2)
    screen.blit(panel, (0, overlay_y))

    # Text drawn only when at least partially visible
    if alpha < 10:
        return

    text_alpha = alpha

    def _alpha_text(msg: str, size: int, color: tuple, cx: int, cy: int) -> None:
        surf = _font(size).render(msg, True, color)
        if text_alpha < 255:
            surf.set_alpha(text_alpha)
        r = surf.get_rect(center=(cx, cy))
        screen.blit(surf, r)

    centre_y = overlay_y + overlay_h // 2
    _alpha_text(f"LEVEL {level}", 50, (0, 230, 255),
                SCREEN_W // 2, centre_y - 50)
    _alpha_text(world_name, 32, (255, 220, 0),
                SCREEN_W // 2, centre_y)
    flavour = _LEVEL_FLAVOUR.get(level, "")
    _alpha_text(flavour, 18, (180, 180, 200),
                SCREEN_W // 2, centre_y + 46)


# ── Main HUD ──────────────────────────────────────────────────────────────────
def draw_hud(screen: pygame.Surface, player, weapon_system,
             score: int, level: int = 1, bombs: int = 0) -> None:
    # ─ Lives (top-left) ───────────────────────────────────────────────────────
    for i in range(player.MAX_LIVES):
        alive = i < player.lives
        _draw_mini_astronaut(screen, 22 + i * 28, 22, alive)

    # ─ HP dots (below lives) ──────────────────────────────────────────────────
    for i in range(player.MAX_HP):
        col = RED if i < player.hp else (60, 20, 20)
        pygame.draw.circle(screen, col, (18 + i * 14, 44), 5)
        pygame.draw.circle(screen, WHITE, (18 + i * 14, 44), 5, 1)

    # ─ Score + Level (top-centre) ─────────────────────────────────────────────
    _text(screen, f"LVL {level}  SCORE  {score:06d}", 20, YELLOW,
          SCREEN_W // 2, 14)

    # ─ Weapon info (top-right) ────────────────────────────────────────────────
    wx = SCREEN_W - 14
    _draw_weapon_icon(screen, wx - 60, 16, weapon_system.shot_type)
    _text(screen, weapon_system.shot_type, 16, CYAN, wx - 36, 16,
          anchor="topright")

    spd_str = f"SPD x{weapon_system.bullet_speed_multiplier:.1f}"
    _text(screen, spd_str, 14, GREY, wx, 34, anchor="topright")

    multi_str = f"MULTI x{weapon_system.multishot_count}"
    _text(screen, multi_str, 14, GREY, wx, 50, anchor="topright")

    # Shadow clone indicator
    if (player.shadow_clone and not player.shadow_clone.dead):
        _text(screen, "CLONE", 14, (100, 150, 255),
              wx, 66, anchor="topright")

    # Bombs (bottom-left)
    bomb_x = 12
    bomb_y = SCREEN_H - 24
    _text(screen, "BOMBS:", 14, (255, 120, 0), bomb_x, bomb_y, anchor="topleft")
    for i in range(bombs):
        bx = bomb_x + 62 + i * 18
        pygame.draw.circle(screen, (30, 30, 30), (bx, bomb_y + 7), 7)
        pygame.draw.circle(screen, (255, 120, 0), (bx, bomb_y + 7), 7, 2)
        pygame.draw.line(screen, (200, 160, 40), (bx, bomb_y), (bx + 3, bomb_y - 4), 2)
    if bombs == 0:
        _text(screen, "NONE", 14, (80, 60, 40), bomb_x + 62, bomb_y, anchor="topleft")


# ── Menu ──────────────────────────────────────────────────────────────────────
def draw_menu(screen: pygame.Surface) -> None:
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 20, 160))
    screen.blit(overlay, (0, 0))

    draw_circle_alpha(screen, CYAN, (SCREEN_W // 2, 180), 120, 25)

    title_surf = _font(64).render("SPACE RANGER", True, CYAN)
    shadow_surf = _font(64).render("SPACE RANGER", True, (0, 60, 100))
    tr = title_surf.get_rect(center=(SCREEN_W // 2, 160))
    screen.blit(shadow_surf, (tr.x + 3, tr.y + 3))
    screen.blit(title_surf, tr)

    _text(screen, "Side-Scrolling Space Shooter", 20, GREY,
          SCREEN_W // 2, 210)

    box_rect = pygame.Rect(SCREEN_W // 2 - 200, 250, 400, 210)
    pygame.draw.rect(screen, (10, 10, 40), box_rect, border_radius=8)
    pygame.draw.rect(screen, CYAN, box_rect, 1, border_radius=8)

    controls = [
        ("WASD / Arrows", "Move"),
        ("SPACE / LMB",   "Shoot"),
        ("B",             "Deploy Bomb"),
        ("ESC",           "Pause"),
        ("R",             "Restart  (Game Over)"),
    ]
    for i, (key, desc) in enumerate(controls):
        y = 268 + i * 38
        _text(screen, key, 16, YELLOW, SCREEN_W // 2 - 20, y,
              anchor="topright")
        _text(screen, f"  {desc}", 16, WHITE, SCREEN_W // 2 - 14, y,
              anchor="topleft")

    ticks = pygame.time.get_ticks()
    if (ticks // 500) % 2 == 0:
        _text(screen, "Press  ENTER  to  Start", 22, GREEN,
              SCREEN_W // 2, 490)

    draw_star_shape(screen, YELLOW, (120, 120), 22, 9, 5,
                    math.radians(ticks / 20))
    draw_star_shape(screen, PURPLE, (680, 100), 16, 7, 5,
                    math.radians(-ticks / 25))


# ── Game Over ─────────────────────────────────────────────────────────────────
def draw_game_over(screen: pygame.Surface, score: int) -> None:
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    _text(screen, "GAME  OVER", 60, RED, SCREEN_W // 2, 210)
    _text(screen, f"Final Score:  {score:06d}", 28, YELLOW,
          SCREEN_W // 2, 300)
    _text(screen, "Press  R  to  Restart", 22, WHITE, SCREEN_W // 2, 370)
    _text(screen, "Press  ESC  for  Menu", 18, GREY, SCREEN_W // 2, 410)


# ── Pause ─────────────────────────────────────────────────────────────────────
def draw_pause(screen: pygame.Surface) -> None:
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 30, 160))
    screen.blit(overlay, (0, 0))

    _text(screen, "P A U S E D", 52, CYAN, SCREEN_W // 2, SCREEN_H // 2 - 30)
    _text(screen, "Press  ESC  to  Resume", 20, GREY,
          SCREEN_W // 2, SCREEN_H // 2 + 30)
