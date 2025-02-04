import pygame
import sys
import os
import random
import math

FPS = 50
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
width, height = screen.get_size()
clock = pygame.time.Clock()

def load_image(name):
    fullname = os.path.join('data', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    return image

def terminate():
    pygame.quit()
    sys.exit()

def load_level(filename):
    filename = os.path.join('data', filename)
    with open(filename, 'r') as mapFile:
        level_map = [line.strip() for line in mapFile]
    max_width = max(map(len, level_map))
    return [line.ljust(max_width, '.') for line in level_map]

# Загрузка основных изображений и установка размера плитки
tile_images = {
    'wall': load_image('grass.png'),
    'empty': load_image('grass.png')
}
player_image = load_image('mar.png')
metro_image = load_image('metro.png')
bu_image = load_image('bu.png')
tile_width = tile_height = 50

# Используем LayeredUpdates, чтобы задать порядок отрисовки спрайтов
all_sprites = pygame.sprite.LayeredUpdates()

# ----------------------------------------------------------------------
# КЛАССЫ СПРАЙТОВ
# ----------------------------------------------------------------------
class Tile(pygame.sprite.Sprite):
    def __init__(self, tile_type, pos_x, pos_y):
        super().__init__()
        self.image = tile_images[tile_type]
        self.rect = self.image.get_rect().move(tile_width * pos_x, tile_height * pos_y)
        # Отображаем фон на самом нижнем слое (0)
        all_sprites.add(self, layer=0)

class Player(pygame.sprite.Sprite):
    def __init__(self, pos_x, pos_y):
        super().__init__()
        self.original_image = player_image
        self.image = self.original_image
        self.rect = self.image.get_rect().move(tile_width * pos_x, tile_height * pos_y)
        self.speed = 5  # скорость в пикселях за кадр
        self.flipped = False
        # Игрок отрисовывается поверх плиток, но под драконом (слой 2)
        all_sprites.add(self, layer=2)

    def update(self, keys):
        # Горизонтальное перемещение
        if keys[pygame.K_a]:
            if not self.flipped:
                self.image = pygame.transform.flip(self.original_image, True, False)
                self.flipped = True
            self.rect.x -= self.speed
        if keys[pygame.K_d]:
            if self.flipped:
                # возвращаем исходное изображение
                self.image = pygame.transform.flip(self.original_image, False, False)
                self.flipped = False
            self.rect.x += self.speed
        # Вертикальное перемещение
        if keys[pygame.K_w]:
            self.rect.y -= self.speed
        if keys[pygame.K_s]:
            self.rect.y += self.speed

        # Ограничиваем пользователя размерами карты
        self.rect.x = max(0, min(self.rect.x, map_width * tile_width - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, map_height * tile_height - self.rect.height))

class Metro(pygame.sprite.Sprite):
    def __init__(self, pos_x, pos_y):
        super().__init__()
        self.image = metro_image
        self.rect = self.image.get_rect().move(tile_width * pos_x, tile_height * pos_y)
        # Метро размещается на слое 2 (так же, как игрок)
        all_sprites.add(self, layer=2)

class Camera:
    def __init__(self):
        self.dx = 0
        self.dy = 0

    def apply(self, obj):
        obj.rect.x += self.dx
        obj.rect.y += self.dy

    def update(self, target):
        self.dx = -(target.rect.x + target.rect.w // 2 - width // 2)
        self.dy = -(target.rect.y + target.rect.h // 2 - height // 2)

class AnimatedSprite(pygame.sprite.Sprite):
    def __init__(self, sheet, columns, rows, x, y):
        super().__init__()
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.image.get_rect()
        # Располагаем дракона по центру клетки
        self.rect.x = tile_width * x + (tile_width - self.rect.width) // 2
        self.rect.y = tile_height * y + (tile_height - self.rect.height) // 2
        self.animation_speed = 10  # каждый N-й кадр обновления анимации
        self.frame_counter = 0
        self.move_speed = 2  # скорость плавного перемещения (в пикселях за кадр)
        # Направление движения будем вычислять динамически
        self.direction = (0, 0)
        # Дракон добавляется в группу на самом верхнем слое (3)
        all_sprites.add(self, layer=3)

    def cut_sheet(self, sheet, columns, rows):
        frame_width = sheet.get_width() // columns
        frame_height = sheet.get_height() // rows
        for j in range(rows):
            for i in range(columns):
                rect = pygame.Rect(i * frame_width, j * frame_height, frame_width, frame_height)
                frame = sheet.subsurface(rect)
                frame = pygame.transform.scale(frame, (tile_width, tile_height))
                self.frames.append(frame)

    def update(self):
        global player
        # Если игрок существует, вычисляем вектор от дракона к игроку
        if player:
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            distance = math.hypot(dx, dy)
            if distance != 0:
                norm_dx = dx / distance
                norm_dy = dy / distance
            else:
                norm_dx, norm_dy = 0, 0
            self.direction = (norm_dx, norm_dy)
        # Обновляем кадр анимации
        self.frame_counter += 1
        if self.frame_counter >= self.animation_speed:
            self.frame_counter = 0
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
        # Выбираем нужный кадр и отражаем его, если движемся вправо
        frame = self.frames[self.cur_frame]
        if self.direction[0] > 0:
            self.image = pygame.transform.flip(frame, True, False)
        else:
            self.image = frame
        # Плавное перемещение по направлению к игроку
        self.rect.x += self.direction[0] * self.move_speed
        self.rect.y += self.direction[1] * self.move_speed

        # Ограничиваем дракона размерами карты (убираем зацикливание)
        self.rect.x = max(0, min(self.rect.x, map_width * tile_width - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, map_height * tile_height - self.rect.height))

# Функция генерации уровня; символы:
# '.' – пустая клетка, '#' – стена, '@' – игрок, 'M' – метро, 'D' – дракон.
def generate_level(level):
    new_player = None
    dragon = None
    for y, line in enumerate(level):
        for x, char in enumerate(line):
            if char == '.':
                Tile('empty', x, y)
            elif char == '#':
                Tile('empty', x, y)
            elif char == '@':
                Tile('empty', x, y)
                new_player = Player(x, y)
            elif char == 'M':
                Tile('empty', x, y)
                Metro(x, y)
            elif char == 'D':
                Tile('empty', x, y)
                dragon = AnimatedSprite(load_image("dragon.png"), 8, 2, x, y)
    return new_player, dragon

# Загрузка карты и вычисление её размеров (в клетках)
level_data = load_level('map.txt')
map_width = len(level_data[0])
map_height = len(level_data)

player, dragon = generate_level(level_data)

# ----------------------------------------------------------------------
# Частицы для эффекта при окончании игры
# ----------------------------------------------------------------------
screen_rect = pygame.Rect(0, 0, width, height)
class Particle(pygame.sprite.Sprite):
    # Загружаем базовую картинку звезды и создаём несколько вариантов масштаба
    fire = [load_image("star.png")]
    for scale in (5, 10, 20):
        fire.append(pygame.transform.scale(fire[0], (scale, scale)))

    def __init__(self, pos, dx, dy):
        super().__init__()
        self.image = random.choice(self.fire)
        self.rect = self.image.get_rect(center=pos)
        self.velocity = [dx, dy]
        self.gravity = 0.5
        all_sprites.add(self)  # добавляем частицу (слой не важен)

    def update(self):
        self.velocity[1] += self.gravity
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        if not screen_rect.colliderect(self.rect):
            self.kill()

def create_particles(position):
    particle_count = 20
    for _ in range(particle_count):
        dx = random.uniform(-3, 3)
        dy = random.uniform(-3, 3)
        Particle(position, dx, dy)

# ----------------------------------------------------------------------
# Меню паузы и кнопок
# ----------------------------------------------------------------------
def draw_button(screen, text, x, y, w, h, inactive_color, active_color, action=None):
    mouse = pygame.mouse.get_pos()
    font = pygame.font.SysFont('Trebuchet MS', 30)
    click = pygame.mouse.get_pressed()
    if x + w > mouse[0] > x and y + h > mouse[1] > y:
        pygame.draw.rect(screen, active_color, (x, y, w, h))
        if click[0] == 1 and action is not None:
            action()
    else:
        pygame.draw.rect(screen, inactive_color, (x, y, w, h))
    text_surf = font.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=(x + w / 2, y + h / 2))
    screen.blit(text_surf, text_rect)

pause = False  # Добавляем глобальную переменную pause

def pause_menu():
    global screen, width, height, pause
    pause = True  # Устанавливаем pause в True, когда открывается меню
    # Переключаемся на окно меньшего размера для меню
    menu_width, menu_height = 800, 600
    screen_copy = screen.copy()  # Копия экрана
    screen = pygame.display.set_mode((menu_width, menu_height))
    width, height = menu_width, menu_height
    while pause:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pause = False  # Выход из меню паузы при нажатии ESC
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    width, height = screen.get_size()
                    return  # Возвращаемся в игровой цикл
        screen.fill('white')
        # Функция продолжения теперь просто меняет значение pause
        draw_button(screen, "Продолжить", 300, 200, 200, 50, '#808080', (200, 200, 200), continue_game)
        draw_button(screen, "Выйти", 300, 300, 200, 50, '#808080', (200, 200, 200), quit_game)
        pygame.display.update()
    # Восстанавливаем состояние экрана после выхода из меню паузы
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    width, height = screen.get_size()

def quit_game():
    terminate()

def continue_game():
    global pause, screen, width, height
    pause = False  # Устанавливаем pause в False
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    width, height = screen.get_size()

def game_over_screen():
    screen.fill('black')
    font = pygame.font.SysFont('Trebuchet MS', 50)
    text = font.render("Вы проиграли", True, (255, 0, 0))
    text_rect = text.get_rect(center=(width // 2, height // 2))
    screen.blit(text, text_rect)
    pygame.display.flip()
    pygame.time.wait(3000)
    terminate()

# ----------------------------------------------------------------------
# Экран запуска и основной игровой цикл
# ----------------------------------------------------------------------
def start_screen():
    global screen, width, height, player, dragon
    # Экран заставки
    intro_text = ["Игра на pygame", "", "Нажмите space чтобы продолжить."]
    screen.fill('black')
    font_intro = pygame.font.SysFont('Trebuchet MS', 50)
    text_y = height // 3
    for line in intro_text:
        rendered = font_intro.render(line, True, pygame.Color('white'))
        # Центрируем текст по горизонтали
        text_x = (width - rendered.get_width()) // 2
        screen.blit(rendered, (text_x, text_y))
        text_y += rendered.get_height() + 10
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False
        clock.tick(FPS)

    # Инициализация игровых переменных
    level = 1
    camera = Camera()
    life = 100
    bu_collided = False

    # Основной игровой цикл
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pause_menu()

        keys = pygame.key.get_pressed()
        player.update(keys)

        # Обновление позиции камеры
        camera.update(player)
        # Применяем смещение камеры ко всем спрайтам
        for sprite in all_sprites:
            camera.apply(sprite)

        # Обновляем дракона (в его update() вычисляется вектор к игроку)
        if dragon:
            dragon.update()

        # Обработка столкновения игрока с драконом
        if dragon and player.rect.colliderect(dragon.rect):
            if not bu_collided:
                life -= 20
                bu_collided = True
        else:
            bu_collided = False

        # Отрисовка игрового поля. Отрисовываем все спрайты из layered-группы,
        # что гарантирует, что дракон всегда будет сверху.
        screen.fill('black')
        all_sprites.draw(screen)
        # Вывод уровня жизни
        font = pygame.font.SysFont('Trebuchet MS', 30)
        life_text = font.render(f'Уровень жизни: {life}%', True, pygame.Color('white'))
        screen.blit(life_text, (10, 10))
        pygame.display.flip()
        clock.tick(FPS)

        # Если жизнь кончилась – запускаем анимацию частиц и затем экран Game Over
        if life <= 0:
            center = player.rect.center
            player.kill()  # игрок исчезает
            end_time = pygame.time.get_ticks() + 3000
            while pygame.time.get_ticks() < end_time:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        terminate()
                create_particles(center)
                screen.fill('black')
                all_sprites.update()
                all_sprites.draw(screen)
                pygame.display.flip()
                clock.tick(FPS)
            game_over_screen()

if __name__ == '__main__':
    try:
        start_screen()
    except Exception as e:
        print(e)