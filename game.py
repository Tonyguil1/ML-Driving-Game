import pygame
import math

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Colors
GREEN = (34, 139, 34)
RED = (220, 20, 60)
BLACK = (0, 0, 0)
GRAY = (90, 90, 90)
WHITE = (255, 255, 255)


def catmull_rom_point(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
               (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
               (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
    y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
               (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
               (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
    return (x, y)


class Track:
    # Control points for the track's centerline (closed loop). The dip near
    # the top and the kink on the right side keep this from being a plain
    # oval, without needing hard right-angle corners.
    CONTROL_POINTS = [
        (160, 480), (90, 380), (90, 220), (180, 120), (300, 90),
        (370, 150), (430, 150), (500, 90), (620, 90), (710, 180),
        (710, 300), (650, 350), (650, 390), (710, 440), (650, 520),
        (480, 560), (300, 540),
    ]
    HALF_WIDTH = 30
    SUBDIVISIONS = 12

    def __init__(self):
        self.centerline = self._smooth(self.CONTROL_POINTS, self.SUBDIVISIONS)
        self.outer, self.inner = self._boundaries(self.centerline, self.HALF_WIDTH)
        self.road_polygon = self.outer + list(reversed(self.inner))

    @staticmethod
    def _smooth(points, subdivisions):
        n = len(points)
        smoothed = []
        for i in range(n):
            p0, p1 = points[(i - 1) % n], points[i]
            p2, p3 = points[(i + 1) % n], points[(i + 2) % n]
            for j in range(subdivisions):
                smoothed.append(catmull_rom_point(p0, p1, p2, p3, j / subdivisions))
        return smoothed

    @staticmethod
    def _boundaries(points, half_width):
        n = len(points)
        outer, inner = [], []
        for i in range(n):
            prev_p, next_p = points[(i - 1) % n], points[(i + 1) % n]
            dx, dy = next_p[0] - prev_p[0], next_p[1] - prev_p[1]
            length = math.hypot(dx, dy) or 1
            nx, ny = -dy / length, dx / length
            px, py = points[i]
            outer.append((px + nx * half_width, py + ny * half_width))
            inner.append((px - nx * half_width, py - ny * half_width))
        return outer, inner

    def constrain_position(self, x, y, radius):
        """Push (x, y) back inside the road if it strays past the curbs."""
        nearest_i = min(
            range(len(self.centerline)),
            key=lambda i: (self.centerline[i][0] - x) ** 2 + (self.centerline[i][1] - y) ** 2,
        )
        cx, cy = self.centerline[nearest_i]
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy)
        max_dist = max(0.0, self.HALF_WIDTH - radius)
        if dist > max_dist and dist > 0:
            scale = max_dist / dist
            x = cx + dx * scale
            y = cy + dy * scale
        return x, y

    def start_pose(self):
        """Center point and facing angle (degrees, Car convention) at the start line."""
        center = self.centerline[0]
        prev_p, next_p = self.centerline[-1], self.centerline[1]
        tx, ty = next_p[0] - prev_p[0], next_p[1] - prev_p[1]
        length = math.hypot(tx, ty) or 1
        tx, ty = tx / length, ty / length
        angle = math.degrees(math.atan2(ty, -tx)) - 90
        return center, angle

    def draw(self, surface):
        pygame.draw.polygon(surface, GRAY, self.road_polygon)
        pygame.draw.lines(surface, WHITE, True, self.outer, 3)
        pygame.draw.lines(surface, WHITE, True, self.inner, 3)
        self._draw_start_line(surface)

    def _draw_start_line(self, surface):
        center = self.centerline[0]
        prev_p, next_p = self.centerline[-1], self.centerline[1]
        dx, dy = next_p[0] - prev_p[0], next_p[1] - prev_p[1]
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length, dx / length
        segments = 8
        for i in range(segments):
            t0 = -self.HALF_WIDTH + (2 * self.HALF_WIDTH) * i / segments
            t1 = -self.HALF_WIDTH + (2 * self.HALF_WIDTH) * (i + 1) / segments
            p0 = (center[0] + nx * t0, center[1] + ny * t0)
            p1 = (center[0] + nx * t1, center[1] + ny * t1)
            color = WHITE if i % 2 == 0 else BLACK
            pygame.draw.line(surface, color, p0, p1, 8)


class Car:
    def __init__(self, x, y, track):
        # Position and dimensions
        self.x = x
        self.y = y
        self.width = 18
        self.height = 30
        self.collision_radius = (self.width + self.height) / 4
        self.track = track

        # Movement physics vectors
        self.speed = 0
        self.max_speed = 6
        self.acceleration = 0.15
        self.brake_deceleration = 0.2
        self.friction = 0.05

        # Steering parameters
        self.angle = 0  # In degrees
        self.turn_speed = 4

        # car surface
        self.original_image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(self.original_image, RED, (0, 0, self.width, self.height), border_radius=3)
        # headlamp positions
        lamp = max(2, self.width // 6)
        lamp_y = self.height - lamp - 3
        pygame.draw.rect(self.original_image, (255, 255, 0), (self.width // 6, lamp_y, lamp, lamp))
        pygame.draw.rect(self.original_image, (255, 255, 0), (self.width - self.width // 6 - lamp, lamp_y, lamp, lamp))

    def update(self, keys):
        # Steering (Only steer if moving)
        if self.speed != 0:
            # Reverse steering logic when backing up
            direction_modifier = 1 if self.speed > 0 else -1
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.angle += self.turn_speed * direction_modifier
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.angle -= self.turn_speed * direction_modifier

        # Acceleration and Braking
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            if self.speed < self.max_speed:
                self.speed += self.acceleration
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            if self.speed > -self.max_speed / 2:  # Reverse is slower
                self.speed -= self.brake_deceleration
        else:
            # slows the car when no keys are pressed
            if self.speed > 0:
                self.speed = max(0, self.speed - self.friction)
            elif self.speed < 0:
                self.speed = min(0, self.speed + self.friction)

        # vector offsets
        radians = math.radians(self.angle + 90)
        self.x -= self.speed * math.cos(radians)
        self.y += self.speed * math.sin(radians)

        # keep the car on the road, between the inner and outer curbs
        self.x, self.y = self.track.constrain_position(self.x, self.y, self.collision_radius)

    def draw(self, surface):
        # Rotate the vehicle surface around its center point
        rotated_image = pygame.transform.rotate(self.original_image, self.angle)
        new_rect = rotated_image.get_rect(center=(self.x, self.y))
        surface.blit(rotated_image, new_rect.topleft)


track = Track()
start_pos, start_angle = track.start_pose()
player_car = Car(*start_pos, track)
player_car.angle = start_angle

# Main Game Loop
running = True
while running:
    clock.tick(60)  # Lock framerate to 60 FPS
    
    # Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Input state retrieval
    keys = pygame.key.get_pressed()
    
    # Physics & Draw Pipeline
    player_car.update(keys)
    
    screen.fill(GREEN)  # Clear background frame
    track.draw(screen)
    player_car.draw(screen)
    pygame.display.flip()  # Update screen buffer

pygame.quit()
