#!/usr/bin/env python3

from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, SpeedPercent, MoveTank
from ev3dev2.sensor.lego import UltrasonicSensor, ColorSensor, GyroSensor, TouchSensor
from ev3dev2.sensor import INPUT_1, INPUT_2, INPUT_3, INPUT_4
from ev3dev2.sound import Sound
from time import sleep, time
from threading import Thread

# === THIẾT BỊ ===
motor_left = LargeMotor(OUTPUT_B)
motor_right = LargeMotor(OUTPUT_C)
motor_ultrasonic = MediumMotor(OUTPUT_A)
tank = MoveTank(OUTPUT_B, OUTPUT_C)

us = UltrasonicSensor(INPUT_2)        # Cảm biến siêu âm
color = ColorSensor(INPUT_1)          # Cảm biến màu
gyro = GyroSensor(INPUT_3)            # Con quay hồi chuyển
touch = TouchSensor(INPUT_4)          # Cảm biến chạm
sound = Sound()                       # Loa phát âm thanh

# === PID DÒ LINE ===
Kp, Ki, Kd = 1.2, 0.001, 1.0
TARGET_REFLECTION = 45  # Với line đen nền trắng
integral = 0
last_error = 0
BASE_SPEED = 20
# === CỜ TRẠNG THÁI ===
delivery_started = False
delivery_done = False

def get_color_reflection():
    return color.reflected_light_intensity

def get_raw_color():
    return color.raw

def rotate_ultrasonic():
    """Xoay cảm biến siêu âm liên tục qua lại."""
    while True:
        motor_ultrasonic.on_for_degrees(SpeedPercent(10), 60)
        motor_ultrasonic.on_for_degrees(SpeedPercent(10), -60)
    


def follow_line_until_red():
    """Robot dò line đen đến khi gặp màu đỏ (điểm giao hàng)."""
    global integral, last_error
    integral = 0
    last_error = 0
    while True:
        # Phát hiện vật cản phía trước
        if us.distance_centimeters <= 40:
            tank.stop()
            sound.play_file("/home/robot/lamontranhduong.wav")
            while us.distance_centimeters < 40:
                sleep(0.01)
            tank.on(BASE_SPEED, BASE_SPEED)

        # PID dò line
        reflection = get_color_reflection()
        error = reflection - TARGET_REFLECTION
        integral += error
        derivative = error - last_error
        turn = Kp * error + Ki * integral + Kd * derivative
        max_turn = BASE_SPEED * 0.8  # Hoặc giá trị phù hợp
        turn = max(-max_turn, min(max_turn, turn))
        left_speed = max(-100, min(100, BASE_SPEED - turn))
        right_speed = max(-100, min(100, BASE_SPEED + turn))
        tank.on(SpeedPercent(left_speed), SpeedPercent(right_speed))
        last_error = error

        # Gặp màu đỏ thì dừng lại và phát lời mời
        r, g, b = color.raw
        if r > 60 and g < 30 and b < 30:
            tank.stop()
            sound.play_file("/home/robot/moibanlayhang.wav")
            return 


def wait_for_second_press():
    """Chờ nhấn lần 2 xác nhận nhận hàng, hoặc tự động quay về sau 4 phút."""
    global delivery_done
    start = time()
    while time() - start < 60:  # Chờ tối đa 60 giây
        # Nếu nhấn cảm biến chạm, thì xác nhận nhận hàng
        # và quay về điểm xuất phát
        if touch.is_pressed:
            sleep(0.1)  # đỡ nhấn nhiều lần
            if touch.is_pressed:
                sound.play_file("/home/robot/daquayvedungvitri.wav")
                delivery_done = True
                go_back()
                return
        sleep(0.01)

    # không nhấn, thì về điểm xuất phát
    if not delivery_done:
        sound.play_file("/home/robot/khongnhanhang_toiquayve.wav")
        go_back()
    


def go_back():
    """Robot quay đầu và dò line đen quay về điểm bắt đầu (màu đỏ)."""
    
    global integral, last_error
    integral = 0
    last_error = 0
    gyro.reset()
    tank.on(SpeedPercent(20), SpeedPercent(-20))
    while abs(gyro.angle) < 175:
        sleep(0.01)
    tank.stop()

    # Tiến nhẹ vào line
    tank.on_for_seconds(SpeedPercent(20), SpeedPercent(20), 1)
    tank.stop()

    # Dò line đen đến màu đỏ
    while True:
        # Phát hiện vật cản phía trước
        if us.distance_centimeters < 40:
            tank.stop()
            sound.play_file("/home/robot/lamontranhduong.wav")
            while us.distance_centimeters < 40:
                sleep(0.01)
            tank.on(SpeedPercent(20), SpeedPercent(20))
        # PID dò line
        reflection = get_color_reflection()
        error = reflection - TARGET_REFLECTION
        integral += error
        derivative = error - last_error
        turn = Kp * error + Ki * integral + Kd * derivative
        max_turn = BASE_SPEED * 0.8  # Hoặc giá trị phù hợp
        turn = max(-max_turn, min(max_turn, turn))
        left_speed = max(-100, min(100, BASE_SPEED - turn))
        right_speed = max(-100, min(100, BASE_SPEED + turn))
        tank.on(SpeedPercent(left_speed), SpeedPercent(right_speed))
        last_error = error

        # Gặp màu đỏ thì dừng lại và nói
        r, g, b = color.raw
        if r > 60 and g < 30 and b < 30:
            tank.stop()
            sound.play_file("/home/robot/daquayvedungvitri.wav")

            # Quay đầu sẵn sàng giao lần sau
            gyro.reset()
            tank.on(SpeedPercent(20), SpeedPercent(-20))
            while abs(gyro.angle) < 175:
                sleep(0.01)
            tank.stop()
            # Tiến nhẹ vào line
            tank.on_for_seconds(SpeedPercent(20), SpeedPercent(20), 1)
            tank.stop()
            sound.play_file("/home/robot/sansangchodottieptheo.wav")
            break




# === CHƯƠNG TRÌNH CHÍNH ===
sound.play_file("/home/robot/sansang.wav")

# Chờ người nhấn 1 lần để bắt đầu giao hàng
while True:
    if touch.is_pressed:
        sleep(0.1)
        if touch.is_pressed:
            sound.play_file("/home/robot/toisedigiaohangday.wav")
            delivery_started = True
            break

# Khởi động thread quay cảm biến siêu âm
Thread(target=rotate_ultrasonic, daemon=True).start()

# Dò line tới nơi giao hàng
follow_line_until_red()

# Chờ xác nhận nhận hàng hoặc quay về
wait_for_second_press()

