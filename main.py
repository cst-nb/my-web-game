import pygame
import random
import sys
import asyncio

# ---------- 基础配置 ----------
WIDTH, HEIGHT = 500, 650
GRID_SIZE = 4
TILE_SIZE = 100
BOARD_OFFSET_X = 50
BOARD_OFFSET_Y = 180 
MOVE_DURATION = 0.12

# 颜色定义
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
        pygame.display.set_caption("Alchemy Strategy - Mobile Ready")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 36, bold=True)
        
        # 触屏相关变量
        self.finger_start_pos = None
        self.swipe_threshold = 0.1  # 屏幕宽度的10%
        
        self.reset_game()

    def reset_game(self):
        self.grid = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.score = 0
        self.animating = False
        self.game_over = False
        self.spawn_initial()

    def get_pixel(self, r, c):
        return BOARD_OFFSET_X + c * TILE_SIZE + 5, BOARD_OFFSET_Y + r * TILE_SIZE + 5

    def spawn_tile(self, count=1):
        empty = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.grid[r][c] is None]
        num_tiles = sum(1 for row in self.grid for t in row if t)
        for _ in range(min(count, len(empty))):
            r, c = random.choice(empty)
            empty.remove((r, c))
            base_prob = 0.06 if num_tiles >= 12 else 0.03
            if self.score > 200 and random.random() < base_prob:
                tile = Tile(bomb=True)
            else:
                color = random.choice(["RED", "GREEN", "BLUE"])
                tile = Tile(color=color, wolf=(random.random() < 0.25))
            tile.x, tile.y = self.get_pixel(r, c)
            tile.target_x, tile.target_y = tile.x, tile.y
            self.grid[r][c] = tile

    def spawn_initial(self): self.spawn_tile(6)

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
            self.prepare_animation(); self.animating = True; self.spawn_tile(random.randint(1, 2))
        elif sum(1 for row in self.grid for t in row if t) == 16: self.game_over = True

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
                else: break
        remaining = tiles[match_count:]; new_tiles = []; idx = 0
        while idx < len(remaining):
            curr = remaining[idx]
            if idx + 1 < len(remaining):
                hunter = remaining[idx + 1]
                if hunter.wolf and not curr.wolf and not curr.bomb:
                    recipe = tuple(sorted([hunter.color, curr.color]))
                    if recipe in MIX_RECIPE:
                        res = MIX_RECIPE[recipe]
                        new_tiles.append(Tile(color=res, wolf=(res != "WHITE")))
                        idx += 2; continue
            new_tiles.append(curr); idx += 1
        return [None] * match_count + new_tiles + [None] * (GRID_SIZE - match_count - len(new_tiles))

    def prepare_animation(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                t = self.grid[r][c]
                if t:
                    t.start_x, t.start_y = t.x, t.y
                    t.target_x, t.target_y = self.get_pixel(r, c); t.move_progress = 0

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
        
        # --- 1. 合成图谱 ---
        guide_x_start = 45
        base_y = 30
        recipes = [("RED", "GREEN", "YELLOW"), ("RED", "BLUE", "MAGENTA"), ("GREEN", "BLUE", "CYAN")]
        for i, (c1, c2, res) in enumerate(recipes):
            x = guide_x_start + i * 145
            pygame.draw.circle(self.screen, COLOR_MAP[c1], (x, base_y), 8)
            pygame.draw.circle(self.screen, COLOR_MAP[c2], (x + 20, base_y), 8)
            self.screen.blit(self.font.render("=", True, (150, 150, 150)), (x + 35, base_y - 12))
            pygame.draw.circle(self.screen, COLOR_MAP[res], (x + 60, base_y), 10)

        base_y_2 = 75
        final_recipes = [("YELLOW", "BLUE"), ("MAGENTA", "GREEN"), ("CYAN", "RED")]
        for i, (c1, c2) in enumerate(final_recipes):
            x = guide_x_start + i * 145
            pygame.draw.circle(self.screen, COLOR_MAP[c1], (x, base_y_2), 10)
            pygame.draw.circle(self.screen, COLOR_MAP[c2], (x + 22, base_y_2), 8)
            self.screen.blit(self.font.render("=", True, (150, 150, 150)), (x + 40, base_y_2 - 12))
            pygame.draw.circle(self.screen, COLOR_MAP["WHITE"], (x + 65, base_y_2), 11)
            pygame.draw.circle(self.screen, (0,0,0), (x + 65, base_y_2), 11, 1)

        # --- 2. 边框 ---
        pygame.draw.rect(self.screen, C_RED, (40, BOARD_OFFSET_Y, 6, 400))
        pygame.draw.rect(self.screen, C_BLUE, (454, BOARD_OFFSET_Y, 6, 400))
        pygame.draw.rect(self.screen, C_GREEN, (50, BOARD_OFFSET_Y - 10, 400, 6))
        pygame.draw.rect(self.screen, C_WHITE, (50, BOARD_OFFSET_Y + 404, 400, 6))

        # --- 3. 进化雷达 ---
        if not self.animating:
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    curr = self.grid[r][c]
                    if curr and curr.wolf:
                        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                                target = self.grid[nr][nc]
                                if target and not target.wolf and not target.bomb:
                                    recipe = tuple(sorted([curr.color, target.color]))
                                    if recipe in MIX_RECIPE:
                                        res_color = COLOR_MAP[MIX_RECIPE[recipe]]
                                        pygame.draw.line(self.screen, res_color, (int(curr.x + 45), int(curr.y + 45)), (int(target.x + 45), int(target.y + 45)), 2)

        # --- 4. 方块渲染 ---
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                bx, by = self.get_pixel(r, c)
                pygame.draw.rect(self.screen, C_EMPTY, (bx, by, TILE_SIZE - 10, TILE_SIZE - 10), border_radius=8)
                t = self.grid[r][c]
                if t:
                    rect = (int(t.x), int(t.y), TILE_SIZE - 10, TILE_SIZE - 10)
                    if t.bomb:
                        pygame.draw.rect(self.screen, (50, 50, 50), rect, border_radius=10)
                        pygame.draw.circle(self.screen, (230, 126, 34), (int(t.x + 45), int(t.y + 45)), 22, 3)
                    else:
                        pygame.draw.rect(self.screen, COLOR_MAP[t.color], rect, border_radius=10)
                        if t.wolf:
                            pygame.draw.circle(self.screen, (0, 0, 0), (int(t.x + 45), int(t.y + 45)), 14)
                            pygame.draw.circle(self.screen, (255, 255, 255), (int(t.x + 45), int(t.y + 45)), 8)

        # UI
        self.screen.blit(self.big_font.render(f"SCORE: {self.score}", True, (255, 255, 255)), (50, 125))
        self.screen.blit(self.font.render("Swipe or Arrows to Play / R to Reset", True, (100, 120, 140)), (50, HEIGHT - 35))

        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(210); overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            pygame.draw.rect(self.screen, (44, 62, 80), (100, 260, 300, 180), border_radius=15)
            t1 = self.big_font.render("GAME OVER", True, (236, 240, 241))
            t2 = self.font.render(f"Final Score: {self.score}", True, (241, 196, 15))
            t3 = self.font.render("Tap or Press 'R' to Restart", True, (200, 200, 200))
            self.screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, 290))
            self.screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, 345))
            self.screen.blit(t3, (WIDTH // 2 - t3.get_width() // 2, 385))
            
        pygame.display.flip()

    async def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: pygame.quit(); sys.exit()
                
                # 键盘处理
                if e.type == pygame.KEYDOWN:
                    if self.game_over and e.key == pygame.K_r: self.reset_game()
                    elif not self.game_over:
                        keys = {pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT", pygame.K_UP: "UP", pygame.K_DOWN: "DOWN"}
                        if e.key in keys: self.handle_move(keys[e.key])
                
                # 触屏手势处理
                elif e.type == pygame.FINGERDOWN:
                    self.finger_start_pos = (e.x, e.y)
                elif e.type == pygame.FINGERUP:
                    if self.game_over:
                        self.reset_game()
                    elif self.finger_start_pos and not self.animating:
                        dx = e.x - self.finger_start_pos[0]
                        dy = e.y - self.finger_start_pos[1]
                        if abs(dx) > self.swipe_threshold or abs(dy) > self.swipe_threshold:
                            if abs(dx) > abs(dy):
                                self.handle_move("RIGHT" if dx > 0 else "LEFT")
                            else:
                                self.handle_move("DOWN" if dy > 0 else "UP")
                        self.finger_start_pos = None

            self.update(dt)
            self.draw()
            await asyncio.sleep(0)  # 关键：Web版异步挂起，允许浏览器渲染

if __name__ == "__main__":
    game = Game()
    asyncio.run(game.run())
