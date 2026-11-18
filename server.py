
import socket
import json
import threading
import time
import random


# --- НАЛАШТУВАННЯ ---
WIDTH, HEIGHT = 800, 600

BALL_SPEED = 5
PADDLE_SPEED = 10
COUNTDOWN_START = 3


class GameServer:
    def __init__(self, host="localhost", port=8080):
        self.server = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        self.server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )
        self.server.bind((host, port))
        self.server.listen(2)
        print("🎮 Server started")
        self.clients = {
            0: None,
            1: None
        }
        self.connected = {
            0: False,
            1: False
        }
        self.lock = threading.RLock()
        self.restart_requests = set()
        self.reset_game_state()
        self.sound_event = None

    def reset_game_state(self):
        self.paddles = {
            0: 250,
            1: 250
        }
        self.scores = [0, 0]
        self.ball = {
            "x": WIDTH // 2,
            "y": HEIGHT // 2,
            "vx": BALL_SPEED * random.choice([-1, 1]),
            "vy": BALL_SPEED * random.choice([-1, 1])
        }
        self.countdown = COUNTDOWN_START
        self.game_over = False
        self.winner = None
        self.sound_event = None

    def handle_client(self, pid):
        conn = self.clients[pid]
        buffer = ""
        try:
            while True:
                data = conn.recv(1024).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    command, buffer = buffer.split("\n", 1)
                    command = command.strip()
                    with self.lock:
                        if command == "RESTART":
                            if self.game_over:
                                if pid not in self.restart_requests:
                                    self.restart_requests.add(pid)
                                    print(
                                        f"Гравець {pid} погодився на рестарт!"
                                    )
                        elif command == "UP":
                            if not self.game_over:
                                self.paddles[pid] = max(
                                    60,
                                    self.paddles[pid] - PADDLE_SPEED
                                )
                        elif command == "DOWN":
                            if not self.game_over:
                                self.paddles[pid] = min(
                                    HEIGHT - 100,
                                    self.paddles[pid] + PADDLE_SPEED
                                )

        except OSError:
            pass
        finally:
            with self.lock:
                self.connected[pid] = False
                if not self.game_over:
                    self.game_over = True
                    if self.connected[1 - pid]:
                        self.winner = 1 - pid
                    else:
                        self.winner = None

                print(f"Гравець {pid} відключився")

            try:
                conn.close()
            except OSError:
                pass

            self.broadcast_state()

    def broadcast_state(self):
        with self.lock:
            state = json.dumps({
                "paddles": self.paddles,
                "ball": self.ball,
                "scores": self.scores,
                "countdown": max(self.countdown, 0),
                "winner": self.winner if self.game_over else None,
                "sound_event": self.sound_event,
                "restart_requests": len(self.restart_requests)
            }) + "\n"
            message = state.encode()
            clients = list(self.clients.items())

        for pid, conn in clients:
            if conn and self.connected[pid]:
                try:
                    conn.sendall(message)
                except OSError:
                    with self.lock:
                        self.connected[pid] = False
                        self.game_over = True
                        if self.connected[1 - pid]:
                            self.winner = 1 - pid

    def ball_logic(self):
        while self.countdown > 0:
            time.sleep(1)
            with self.lock:
                if self.game_over:
                    return
                self.countdown -= 1
                self.broadcast_state()

        while not self.game_over:
            with self.lock:
                if self.game_over:
                    break

                self.ball["x"] += self.ball["vx"]
                self.ball["y"] += self.ball["vy"]

                if (
                    self.ball["y"] <= 60
                    or self.ball["y"] >= HEIGHT - 10
                ):
                    self.ball["vy"] *= -1
                    self.sound_event = "wall_hit"
                if (
                    (
                        self.ball["x"] <= 40
                        and self.paddles[0]
                        <= self.ball["y"]
                        <= self.paddles[0] + 100
                    )
                    or
                    (
                        self.ball["x"] >= WIDTH - 40
                        and self.paddles[1]
                        <= self.ball["y"]
                        <= self.paddles[1] + 100
                    )

                ):
                    self.ball["vx"] *= -1
                    self.sound_event = "platform_hit"

                if self.ball["x"] < 0:
                    self.scores[1] += 1
                    self.reset_ball()
                elif self.ball["x"] > WIDTH:
                    self.scores[0] += 1
                    self.reset_ball()

                if self.scores[0] >= 10:
                    self.game_over = True
                    self.winner = 0
                elif self.scores[1] >= 10:
                    self.game_over = True
                    self.winner = 1

                self.broadcast_state()
                self.sound_event = None

            time.sleep(0.016)

    def reset_ball(self):
        self.ball = {
            "x": WIDTH // 2,
            "y": HEIGHT // 2,
            "vx": BALL_SPEED * random.choice([-1, 1]),
            "vy": BALL_SPEED * random.choice([-1, 1])
        }

    def accept_players(self):
        for pid in [0, 1]:
            print(f"Очікуємо гравця {pid}...")
            conn, address = self.server.accept()
            self.clients[pid] = conn
            self.connected[pid] = True
            # Відправляємо ID гравця
            conn.sendall((str(pid) + "\n").encode())
            print(f"Гравець {pid} приєднався: {address}")
            threading.Thread(
                target=self.handle_client,
                args=(pid,),
                daemon=True
            ).start()

    # --- ГОЛОВНИЙ ЦИКЛ СЕРВЕРА ---
    def run(self):
        while True:
            self.accept_players()
            while True:
                with self.lock:
                    self.reset_game_state()
                    self.restart_requests.clear()
                print("\nНова гра починається!")
                self.broadcast_state()
                game_thread = threading.Thread(
                    target=self.ball_logic
                )
                game_thread.start()
                while (
                    not self.game_over
                    and all(self.connected.values())
                ):
                    time.sleep(0.1)
                game_thread.join()
                if not all(self.connected.values()):
                    print("Гравець відключився. Завершуємо сесію.")
                    break
                print(
                    f"\nГра завершена! Переміг гравець {self.winner}"
                )
                print("Очікуємо підтвердження обох гравців...")
                while (
                    len(self.restart_requests) < 2
                    and all(self.connected.values())
                ):
                    self.broadcast_state()
                    time.sleep(0.1)
                if not all(self.connected.values()):
                    print("З'єднання втрачено.")
                    break

                print("\nОбидва гравці погодились на рестарт!")
            for pid in [0, 1]:
                conn = self.clients[pid]
                if conn:
                    try:
                        conn.close()
                    except OSError:
                        pass

                self.clients[pid] = None
                self.connected[pid] = False

            print("\nОчікуємо нових гравців...")

GameServer().run()