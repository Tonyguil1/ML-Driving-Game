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

class Car:
    def __init__(self, x, y):
        # Position and dimensions
        self.x = x
        self.y = y
        self.width = 30
        self.height = 50
        
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
        pygame.draw.rect(self.original_image, RED, (0, 0, self.width, self.height), border_radius=5)
        # headlamp positions
        pygame.draw.rect(self.original_image, (255, 255, 0), (5, 40, 5, 5))
        pygame.draw.rect(self.original_image, (255, 255, 0), (20, 40, 5, 5))

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
        
        # screen boundaries
        self.x = max(0, min(WIDTH, self.x))
        self.y = max(0, min(HEIGHT, self.y))

    def draw(self, surface):
        # Rotate the vehicle surface around its center point
        rotated_image = pygame.transform.rotate(self.original_image, self.angle)
        new_rect = rotated_image.get_rect(center=(self.x, self.y))
        surface.blit(rotated_image, new_rect.topleft)


player_car = Car(WIDTH // 2, HEIGHT // 2)

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
    player_car.draw(screen)
    pygame.display.flip()  # Update screen buffer

pygame.quit()
