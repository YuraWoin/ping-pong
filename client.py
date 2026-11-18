
from pygame import *
import socket
import json
import sys
import time as pytime
from threading import Thread, Lock

# --- НАЛАШТУВАННЯ ГРИ ---
WIDTH, HEIGHT = 800, 600

init()

screen = display.set_mode((WIDTH, HEIGHT))
clock = time.Clock()
display.set_caption("Пінг-Понг")

# --- ПІДКЛЮЧЕННЯ ДО СЕРВЕРА ---
def connect_to_server():
    while True:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect(("localhost", 8080))
            buffer = ""
            while "\n" not in buffer:
                data = client.recv(1024).decode()
                if not data:
                    raise ConnectionError("Сервер закрив з'єднання")
                buffer += data
            player_id, buffer = buffer.split("\n", 1)
            return int(player_id), client, buffer
        except OSError:
            client.close()
            print("Очікуємо підключення до сервера...")
            pytime.sleep(1)

# --- ОТРИМАННЯ ДАНИХ ВІД СЕРВЕРА ---
game_state = {}
state_lock = Lock()
connection_lost = False

def receive():
    global game_state, connection_lost
    buffer = initial_buffer
    while True:
        try:
            data = client.recv(1024).decode()
            if not data:
                raise ConnectionError("Сервер закрив з'єднання")
            buffer += data
            while "\n" in buffer:
                packet, buffer = buffer.split("\n", 1)
                if packet.strip():
                    new_state = json.loads(packet)
                    with state_lock:
                        game_state = new_state

        except (OSError, ConnectionError, json.JSONDecodeError):
            connection_lost = True
            break

# --- ШРИФТИ ---
font_win = font.Font(None, 72)
font_main = font.Font(None, 36)
font_small = font.Font(None, 26)
font_countdown = font.Font(None, 100)

# --- ЗОБРАЖЕННЯ ---
bg = image.load("bg.jpg").convert()
bg = transform.scale(bg, (WIDTH, HEIGHT))

# --- СТАН ГРИ ---
restart_sent = False
you_winner = None

# --- ПІДКЛЮЧЕННЯ ---
my_id, client, initial_buffer = connect_to_server()
Thread(target=receive, daemon=True).start()
# --- ОСНОВНИЙ ЦИКЛ ГРИ ---
while True:
    with state_lock:
        current_state = game_state.copy()

    for e in event.get():
        if e.type == QUIT:
            client.close()
            quit()
            sys.exit()
        if e.type == KEYDOWN:
            if e.key == K_k:
                if (
                    current_state.get("winner") is not None
                    and current_state.get("winner") != -1
                    and not restart_sent
                ):
                    try:
                        client.sendall(b"RESTART\n")
                        restart_sent = True

                    except OSError:
                        connection_lost = True

    if connection_lost:
        screen.fill((30, 30, 30))
        text = font_main.render(
            "З'єднання з сервером втрачено!",
            True,
            (255, 0, 0)
        )
        rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, rect)
        display.update()
        clock.tick(60)
        continue

    # --- ФОН ---
    screen.blit(bg, (0, 0))
    countdown = current_state.get("countdown", 0)
    if countdown > 0:
        you_winner = None
        restart_sent = False
        countdown_text = font_countdown.render(
            str(countdown),
            True,
            (255, 255, 255)
        )
        rect = countdown_text.get_rect(
            center=(WIDTH // 2, HEIGHT // 2)
        )
        screen.blit(countdown_text, rect)
        display.update()
        clock.tick(60)
        continue

    # --- ЗАВЕРШЕННЯ ГРИ ---
    winner = current_state.get("winner")
    if winner is not None:
        screen.fill((20, 20, 20))
        if winner == -1:
            result_text = "Другий гравець відключився!"
        else:
            if you_winner is None:
                you_winner = (winner == my_id)
            if you_winner:
                result_text = "Ти переміг!"
            else:
                result_text = "Пощастить наступним разом!"

        win_text = font_win.render(
            result_text,
            True,
            (255, 215, 0)
        )
        win_rect = win_text.get_rect(
            center=(WIDTH // 2, HEIGHT // 2 - 80)
        )
        screen.blit(win_text, win_rect)

        if winner != -1:
            request = current_state.get("restart_requests", 0)
            if not restart_sent:
                message = "K - рестарт"
            elif request < 2:
                message = "Очікуємо другого гравця..."
            else:
                message = "Починаємо нову гру!"
            restart_text = font_main.render(
                message,
                True,
                (255, 255, 255)
            )
            restart_rect = restart_text.get_rect(
                center=(WIDTH // 2, HEIGHT // 2 + 40)
            )
            screen.blit(restart_text, restart_rect)
            ready_text = font_small.render(
                f"Готові гравці: {request} / 2",
                True,
                (255, 100, 100)
            )
            ready_rect = ready_text.get_rect(
                center=(WIDTH // 2, HEIGHT // 2 + 110)
            )
            screen.blit(ready_text, ready_rect)
        display.update()
        clock.tick(60)
        continue

    if current_state:
        paddles = current_state["paddles"]
        ball = current_state["ball"]
        scores = current_state["scores"]
        draw.rect(
            screen,
            (0, 255, 0),
            (20, paddles["0"], 20, 100)
        )
        draw.rect(
            screen,
            (255, 0, 255),
            (WIDTH - 40, paddles["1"], 20, 100)
        )
        draw.circle(
            screen,
            (255, 255, 255),
            (ball["x"], ball["y"]),
            10
        )
        score_text = font_main.render(
            f"{scores[0]} : {scores[1]}",
            True,
            (255, 255, 255)
        )
        score_rect = score_text.get_rect(
            center=(WIDTH // 2, 35)
        )

        screen.blit(score_text, score_rect)
        sound_event = current_state.get("sound_event")
        if sound_event == "wall_hit":
            pass  # Тут можна додати звук від стіни

        elif sound_event == "platform_hit":
            pass  # Тут можна додати звук від платформи

    else:

        waiting_text = font_main.render(
            "Очікування гравців...",
            True,
            (255, 255, 255)
        )
        waiting_rect = waiting_text.get_rect(
            center=(WIDTH // 2, 35)
        )

        screen.blit(waiting_text, waiting_rect)

    display.update()
    clock.tick(60)
    keys = key.get_pressed()
    try:
        if keys[K_w]:
            client.sendall(b"UP\n")
        elif keys[K_s]:
            client.sendall(b"DOWN\n")
    except OSError:
        connection_lost = True