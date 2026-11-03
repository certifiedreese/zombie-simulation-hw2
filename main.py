# ============================================================
# main.py - Display layer
#
# Opens the window, handles the R key, and draws the agents.
# This is the ONLY place that chooses which storage to use.
# ============================================================

import pygame
from storage import InMemoryStore, SQLiteStore
from simulation import Simulation, WIDTH, HEIGHT, FPS, TIME_LIMIT

# ===== CHOOSE THE STORAGE (the only line to change) =====
store = InMemoryStore()

sim = Simulation(store)
sim.new_game()

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zombie Simulation")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)
big_font = pygame.font.SysFont(None, 60)

running = True
while running:
    # 1) INPUT
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            sim.new_game()

    # 2) UPDATE: the simulation handles all the rules
    sim.step()

    # 3) DRAW
    humans = sim.get_humans()
    zombies = sim.get_zombies()

    screen.fill((30, 30, 30))
    for h in humans:
        pygame.draw.circle(screen, (0, 200, 255), (int(h.x), int(h.y)), 6)
    for z in zombies:
        pygame.draw.circle(screen, (80, 220, 80), (int(z.x), int(z.y)), 7)

    counter = font.render(
        f"Humans: {len(humans)}   Zombies: {len(zombies)}   Time: {sim.seconds()}/{TIME_LIMIT}s",
        True, (255, 255, 255))
    screen.blit(counter, (10, 10))

    message = sim.result()
    if message:
        text = big_font.render(message, True, (255, 255, 255))
        screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        hint = font.render("Press R to restart", True, (200, 200, 200))
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50)))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()