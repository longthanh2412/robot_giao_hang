#!/usr/bin/env python3

from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, SpeedPercent, MoveTank # type: ignore
from ev3dev2.sensor.lego import UltrasonicSensor, ColorSensor, GyroSensor, TouchSensor # type: ignore
from ev3dev2.sensor import INPUT_1, INPUT_2, INPUT_3, INPUT_4 # type: ignore
from ev3dev2.sound import Sound # type: ignore
from time import sleep, time
from threading import Thread

# === THIẾT BỊ ===
motor_left = LargeMotor(OUTPUT_B)
motor_right = LargeMotor(OUTPUT_A)
motor_ultrasonic = MediumMotor(OUTPUT_C)
tank = MoveTank(OUTPUT_B, OUTPUT_A)

us = UltrasonicSensor(INPUT_4)        # Cảm biến siêu âm
color = ColorSensor(INPUT_1)          # Cảm biến màu
gyro = GyroSensor(INPUT_2)            # Con quay hồi chuyển
touch = TouchSensor(INPUT_3)          # Cảm biến chạm
sound = Sound()                       # Loa phát âm thanh

# === PID DÒ LINE ===
Kp, Ki, Kd = 0.3, 0, 0
TARGET_REFLECTION = 40  # Với line đen nền trắng
integral = 0
last_error = 0
BASE_SPEED_PERCENT = 30

# === CỜ TRẠNG THÁI ===
delivery_started = False
delivery_done = False


def rotate_ultrasonic():
    """Xoay cảm biến siêu âm liên tục qua lại."""
    while True:
        motor_ultrasonic.on_for_degrees(SpeedPercent(5), 60)
        motor_ultrasonic.on_for_degrees(SpeedPercent(5), 60)


def follow_line_until_red():
    """Robot dò line đen đến khi gặp màu đỏ (điểm giao hàng)."""
    global integral, last_error
    while True:
        # Phát hiện vật cản phía trước
        if us.distance_centimeters < 10:
            tank.stop()
            sound.play_file("not_succeed.wav")
            while us.distance_centimeters < 10:
                sleep(0.1)
            tank.on(SpeedPercent(20), SpeedPercent(20))

        # PID dò line
        reflection = color.reflected_light_intensity
        error = reflection - TARGET_REFLECTION
        integral += error
        derivative = error - last_error
        turn = Kp * error + Ki * integral + Kd * derivative
        MAX_TURN_MAGNITUDE = 60 
        turn = max(min(turn, MAX_TURN_MAGNITUDE), -MAX_TURN_MAGNITUDE)

        tank.on(SpeedPercent(BASE_SPEED_PERCENT - turn), SpeedPercent(BASE_SPEED_PERCENT + turn))
        last_error = error

        # Gặp màu đỏ thì dừng lại và phát lời mời
        r, g, b = color.raw
        if r > 220 and g > 200 and b < 120080: # Điều kiện để thấy màu đỏ
            tank.stop()
            sound.play_file("sounds/receive.wav")
            return


def wait_for_second_press():
    """Chờ nhấn lần 2 xác nhận nhận hàng, hoặc tự động quay về sau 4 phút."""
    global delivery_done
    start = time()
    while time() - start < 240:
        if touch.is_pressed:
            sleep(0.1)  # đỡ nhấn nhiều lần
            if touch.is_pressed:
                sound.play_file("sounds/thanks")
                delivery_done = True
                go_back()
                return
        sleep(0.1)

    # không nhấn, thì về điểm xuất phát
    if not delivery_done:
        sound.play_file("sounds/not_succeed")
        go_back()


def go_back():
    """Robot quay đầu và dò line đen quay về điểm bắt đầu (màu vàng)."""
    global integral, last_error
    gyro.reset()
    tank.on(SpeedPercent(20), SpeedPercent(-20))
    while abs(gyro.angle) < 180:
        sleep(0.01)
    tank.stop()

    # Tiến nhẹ vào line
    tank.on_for_seconds(SpeedPercent(20), SpeedPercent(20), 1)
    tank.stop()

    # Dò line đen đến màu vàng
    while True:
        reflection = color.reflected_light_intensity
        error = reflection - TARGET_REFLECTION
        integral += error
        derivative = error - last_error
        turn = Kp * error + Ki * integral + Kd * derivative
        left_speed = BASE_SPEED_PERCENT - turn
        right_speed = BASE_SPEED_PERCENT + turn
        # Đảm bảo tốc độ không âm hoặc quá cao
        left_speed = max(-100, min(left_speed, 100))
        right_speed = max(-100, min(right_speed, 100))
        tank.on(SpeedPercent(left_speed), SpeedPercent(right_speed))
        last_error = error

        r, g, b = color.raw #màu vàng
        if r > 10050 and g > 10070 and b < 132005:
            tank.stop()
            sound.play_file("sounds/return_succeed/wav")

            # Quay đầu sẵn sàng giao lần sau
            gyro.reset()
            tank.on(SpeedPercent(20), SpeedPercent(-20))
            while abs(gyro.angle) < 180:
                sleep(0.01)
            tank.stop()
            sound.play_file("sounds/done.wav")
            break




# === CHƯƠNG TRÌNH CHÍNH ===
sound.play_file("sounds/San_Sang.wav")

# Chờ người nhấn 1 lần để bắt đầu giao hàng
while True:
    if touch.is_pressed:
        sleep(0.1)
        if touch.is_pressed:
            sound.play_file("sounds/Start_Delivery")
            delivery_started = True
            break

# Khởi động thread quay cảm biến siêu âm
Thread(target=rotate_ultrasonic, daemon=True).start()

# Dò line tới nơi giao hàng
follow_line_until_red()

# Chờ xác nhận nhận hàng hoặc quay về
wait_for_second_press()