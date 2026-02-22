import pygame
import random
import sys
import asyncio

WIDTH, HEIGHT = 500, 600
GRID_SIZE = 4
TILE_SIZE = 100
BOARD_OFFSET = 50
MOVE_DURATION = 0.12

C_RED, C_GREEN, C_BLUE = (192, 57, 43), (30, 80, 40), (41, 128, 185)
C_WHITE = (236, 240, 241)
C_YELLOW, C_MAGENTA, C_CYAN = (241, 196, 15), (142, 68, 173), (26, 188, 156)
C_EMPTY, C_BG = (33, 47, 61), (15, 15, 15)

COLOR_MAP = {
    "RED": C_RED, "GREEN": C_GREEN, "BLUE": C_BLUE,
    "WHITE": C_WHITE, "YELLOW": C_YELLOW,
    "MAGENTA": C_MAGENTA, "CYAN": C_CYAN
}

MIX_RECIPE = {
    tuple(sorted(["RED", "GREEN"])): "YELLOW",
    tuple(sorted(["RED", "BLUE"])): "MAGENTA",
    tuple(sorted(["GREEN", "BLUE"])): "CYAN",
    tuple(sorted(["YELLOW", "BLUE"])): "WHITE",
    tuple(sorted(["MAGENTA", "GREEN"])): "WHITE",
    tuple(sorted(["CYAN", "RED"])): "WHITE"
}


class Tile:
    def __init__(self, color=None, wolf=False, bomb=False):
        self.color = color
        self.wolf = wolf
        self.bomb = bomb
        self.x, self.y = 0, 0
        self.start_x, self.start_y = 0, 0
        self.target_x, self.target_y = 0, 0
        self.move_progress = 1


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 40, bold=True)
        self.reset_game()

    def reset_game(self):
        self.grid = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.score = 0
        self.animating = False
        self.game_over = False
        self.spawn_initial()

    def get_pixel(self, r, c):
        return BOARD_OFFSET + c * TILE_SIZE + 5, BOARD_OFFSET + r * TILE_SIZE + 5

    def spawn_tile(self, count=1):
        empty = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.grid[r][c] is None]
        num_tiles = sum(1 for row in self.grid for t in row if t)
        for _ in range(min(count, len(empty))):
            r, c = random.choice(empty)
            empty.remove((r, c))
            prob = 0.06 if num_tiles >= 12 else 0.03
            if self.score > 200 and random.random() < prob:
                tile = Tile(bomb=True)
            else:
                color = random.choice(["RED", "GREEN", "BLUE"])
                tile = Tile(color=color, wolf=(random.random() < 0.25))
            tile.x, tile.y = self.get_pixel(r, c)
            tile.target_x, tile.target_y = tile.x, tile.y
            self.grid[r][c] = tile

    def spawn_initial(self):
        self.spawn_tile(6)

    def handle_move(self, direction):
        if self.animating or self.game_over: return
        old_state = [[(t.color, t.wolf, t.bomb) if t else None for t in row] for row in self.grid]
        border_map = {"LEFT": "RED", "RIGHT": "BLUE", "UP": "GREEN", "DOWN": "WHITE"}
        target_color = border_map[direction]
        triggered_bombs = []

        for i in range(GRID_SIZE):
            if direction in ["LEFT", "RIGHT"]:
                line = self.grid[i][:]
                if direction == "RIGHT": line.reverse()
                tiles = [t for t in line if t is not None]
                if tiles and tiles[0].bomb: triggered_bombs.append(('ROW', i))
                new_line = self.process_logic(line, target_color)
                if direction == "RIGHT": new_line.reverse()
                self.grid[i] = new_line
            else:
                line = [self.grid[r][i] for r in range(GRID_SIZE)]
                if direction == "DOWN": line.reverse()
                tiles = [t for t in line if t is not None]
                if tiles and tiles[0].bomb: triggered_bombs.append(('COL', i))
                new_line = self.process_logic(line, target_color)
                if direction == "DOWN": new_line.reverse()
                for r in range(GRID_SIZE): self.grid[r][i] = new_line[r]

        for b_type, idx in triggered_bombs:
            if b_type == 'ROW':
                for c in range(GRID_SIZE): self.grid[idx][c] = None
            else:
                for r in range(GRID_SIZE): self.grid[r][idx] = None
            self.score += 80

        if [[(t.color, t.wolf, t.bomb) if t else None for t in row] for row in self.grid] != old_state:
            self.prepare_animation()
            self.animating = True
            self.spawn_tile(random.randint(1, 2))
        elif sum(1 for row in self.grid for t in row if t) == 16:
            self.game_over = True

    def process_logic(self, line, border_color):
        tiles = [t for t in line if t is not None]
        if not tiles: return [None] * GRID_SIZE
        if tiles[0].bomb: return [None] * GRID_SIZE

        match_count = 0
        if tiles[0].color == border_color:
            for t in tiles:
                if t.color == border_color:
                    match_count += 1
                    self.score += 100 if t.color == "WHITE" else 20
                else:
                    break

        remaining = tiles[match_count:]
        new_tiles = []
        idx = 0
        while idx < len(remaining):
            curr = remaining[idx]
            if idx + 1 < len(remaining):
                hunter = remaining[idx + 1]
                if hunter.wolf and not curr.wolf and not curr.bomb:
                    recipe = tuple(sorted([hunter.color, curr.color]))
                    if recipe in MIX_RECIPE:
                        res = MIX_RECIPE[recipe]
                        new_tiles.append(Tile(color=res, wolf=(res != "WHITE")))
                        idx += 2
                        continue
            new_tiles.append(curr)
            idx += 1
        return [None] * match_count + new_tiles + [None] * (GRID_SIZE - match_count - len(new_tiles))

    def prepare_animation(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                t = self.grid[r][c]
                if t:
                    t.start_x, t.start_y = t.x, t.y
                    t.target_x, t.target_y = self.get_pixel(r, c)
                    t.move_progress = 0

    def update(self, dt):
        if not self.animating: return
        done = True
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                t = self.grid[r][c]
                if t and t.move_progress < 1:
                    t.move_progress += dt / MOVE_DURATION
                    p = min(1, t.move_progress)
                    t.x = t.start_x + (t.target_x - t.start_x) * (1 - pow(1 - p, 3))
                    t.y = t.start_y + (t.target_y - t.start_y) * (1 - pow(1 - p, 3))
                    if t.move_progress < 1: done = False
        if done: self.animating = False

    def draw(self):
        self.screen.fill(C_BG)
        self.screen.blit(self.font.render(f"SCORE: {self.score}", True, (255, 255, 255)), (25, 12))
        pygame.draw.rect(self.screen, C_GREEN, (50, 40, 400, 10))
        pygame.draw.rect(self.screen, C_WHITE, (50, 450, 400, 10))
        pygame.draw.rect(self.screen, C_RED, (40, 50, 10, 400))
        pygame.draw.rect(self.screen, C_BLUE, (450, 50, 10, 400))

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                bx, by = self.get_pixel(r, c)
                pygame.draw.rect(self.screen, C_EMPTY, (bx, by, TILE_SIZE - 10, TILE_SIZE - 10), border_radius=8)
                t = self.grid[r][c]
                if t:
                    rect = (t.x, t.y, TILE_SIZE - 10, TILE_SIZE - 10)
                    if t.bomb:
                        pygame.draw.rect(self.screen, (50, 50, 50), rect, border_radius=10)
                        pygame.draw.circle(self.screen, (230, 126, 34), (int(t.x + 45), int(t.y + 45)), 22, 3)
                    else:
                        pygame.draw.rect(self.screen, COLOR_MAP[t.color], rect, border_radius=10)
                        if t.wolf:
                            pygame.draw.circle(self.screen, (0, 0, 0), (int(t.x + 45), int(t.y + 45)), 12)
                            pygame.draw.circle(self.screen, (255, 255, 255), (int(t.x + 45), int(t.y + 45)), 8)

        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT));
            overlay.set_alpha(210);
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            box = pygame.Rect(WIDTH // 2 - 160, HEIGHT // 2 - 110, 320, 220)
            pygame.draw.rect(self.screen, (44, 62, 80), box, border_radius=15)
            pygame.draw.rect(self.screen, (236, 240, 241), box, 3, border_radius=15)
            v1 = self.big_font.render(f"{self.score}", True, (241, 196, 15))
            v2 = self.font.render("RESTART", True, (236, 240, 241))
            v3 = self.font.render("Click or Press R", True, (149, 165, 166))
            self.screen.blit(v1, (WIDTH // 2 - v1.get_width() // 2, box.y + 45))
            self.screen.blit(v2, (WIDTH // 2 - v2.get_width() // 2, box.y + 110))
            self.screen.blit(v3, (WIDTH // 2 - v3.get_width() // 2, box.y + 155))
        pygame.display.flip()


async def main():
    game = Game()
    start_pos = None

    while True:
        dt = game.clock.tick(60) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return

            if e.type == pygame.KEYDOWN:
                if game.game_over and e.key == pygame.K_r:
                    game.reset_game()
                elif not game.game_over:
                    keys = {pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT", pygame.K_UP: "UP", pygame.K_DOWN: "DOWN"}
                    if e.key in keys: game.handle_move(keys[e.key])

            elif e.type in [pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN]:
                if game.game_over:
                    game.reset_game()
                else:
                    px = getattr(e, 'x', e.pos[0] / WIDTH if hasattr(e, 'pos') else 0) * WIDTH
                    py = getattr(e, 'y', e.pos[1] / HEIGHT if hasattr(e, 'pos') else 0) * HEIGHT
                    start_pos = (px, py)

            elif e.type in [pygame.MOUSEBUTTONUP, pygame.FINGERUP]:
                if start_pos:
                    px = getattr(e, 'x', e.pos[0] / WIDTH if hasattr(e, 'pos') else 0) * WIDTH
                    py = getattr(e, 'y', e.pos[1] / HEIGHT if hasattr(e, 'pos') else 0) * HEIGHT
                    dx, dy = px - start_pos[0], py - start_pos[1]
                    if abs(dx) > 35 or abs(dy) > 35:
                        if abs(dx) > abs(dy):
                            game.handle_move("RIGHT" if dx > 0 else "LEFT")
                        else:
                            game.handle_move("DOWN" if dy > 0 else "UP")
                    start_pos = None

        game.update(dt)
        game.draw()
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())