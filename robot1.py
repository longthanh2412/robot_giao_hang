#!/usr/bin/env python3
"""
Example LEGO® MINDSTORMS® EV3 Robot Educator Color Sensor Down Program
----------------------------------------------------------------------

This program requires LEGO® EV3 MicroPython v2.0.
Download: https://education.lego.com/en-us/support/mindstorms-ev3/python-for-ev3

Building instructions can be found at:
https://education.lego.com/en-us/support/mindstorms-ev3/building-instructions#robot
"""
from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, SpeedPercent, MoveTank
from ev3dev2.sensor import INPUT_1, INPUT_2, INPUT_3, INPUT_4
from ev3dev2.sensor.lego import UltrasonicSensor, ColorSensor, GyroSensor, TouchSensor
from ev3dev2.sound import Sound
from time import sleep, time
from threading import Thread
from ev3dev2.display import Display 

# === THIẾT BỊ ===
motor_left = LargeMotor(OUTPUT_B)
motor_right = LargeMotor(OUTPUT_A)
motor_ultrasonic = MediumMotor(OUTPUT_C)
tank = MoveTank(OUTPUT_B, OUTPUT_A)

us = UltrasonicSensor(INPUT_4)         # Cảm biến siêu âm
color = ColorSensor(INPUT_1)           # Cảm biến màu
gyro = GyroSensor(INPUT_2)             # Con quay hồi chuyển
touch = TouchSensor(INPUT_3)           # Cảm biến chạm
sound = Sound()                        # Loa phát âm thanh
display = Display()                    # Đối tượng màn hình

# === PID DÒ LINE ===
Kp, Ki, Kd = 0.4, 0.005, 0.5
TARGET_REFLECTION = 40   # Với line đen nền trắng
integral = 0
last_error = 0
BASE_SPEED_PERCENT = 20 # Tốc độ cơ bản của robot

# === CỜ TRẠNG THÁI ===
delivery_started = False
delivery_done = False


def rotate_ultrasonic():
    """Xoay cảm biến siêu âm liên tục qua lại."""
    while True:
        motor_ultrasonic.on_for_degrees(SpeedPercent(20), 90, block=True) 
        motor_ultrasonic.on_for_degrees(SpeedPercent(20), -180, block=True)
        motor_ultrasonic.on_for_degrees(SpeedPercent(20), 90, block=True)
        sleep(0.1)


def follow_line_until_red():
    """Robot dò line đen đến khi gặp màu đỏ (điểm giao hàng)."""
    global integral, last_error
    while True:
        # Phát hiện vật cản phía trước
        if us.distance_centimeters < 50:
            tank.stop()
            sound.speak("Vat can phia truoc")
            display.clear()
            display.text_pixels("Vat can phia truoc!", x=0, y=0)
            display.update()
            while us.distance_centimeters < 50:
                sleep(0.1)
            display.clear()
            display.update()
            tank.on(SpeedPercent(BASE_SPEED_PERCENT), SpeedPercent(BASE_SPEED_PERCENT))

        # PID dò line
        reflection = color.reflected_light_intensity
        error = reflection - TARGET_REFLECTION
        integral += error
        derivative = error - last_error
        turn = Kp * error + Ki * integral + Kd * derivative

        # GIỚI HẠN GIÁ TRỊ CỦA 'turn'
        # Đảm bảo 'turn' không làm tốc độ vượt quá giới hạn [-100, 100]
        # max_turn_magnitude là giá trị tuyệt đối tối đa mà 'turn' có thể đạt được
        # Nếu BASE_SPEED_PERCENT là 20, và bạn muốn tốc độ không vượt quá 100 hoặc dưới -100,
        # thì turn tối đa có thể là 80 (để 20 + 80 = 100) và tối thiểu là -80 (để 20 - (-80) = 100)
        # Tuy nhiên, để robot rẽ mượt hơn và tránh tốc độ quá cao, 
        # thường giới hạn 'turn' nhỏ hơn.
        # Giá trị 60 là một lựa chọn an toàn cho BASE_SPEED_PERCENT = 20, 
        # cho phép tốc độ từ -40 đến 80.
        max_turn_magnitude = 60 # Giới hạn tuyệt đối của 'turn'
        turn = max(min(turn, max_turn_magnitude), -max_turn_magnitude)

        tank.on(SpeedPercent(BASE_SPEED_PERCENT - turn), SpeedPercent(BASE_SPEED_PERCENT + turn))
        last_error = error

        # Gặp màu đỏ thì dừng lại và phát lời mời
        r, g, b = color.raw
        # Điều kiện nhận diện màu ĐỎ (Cần điều chỉnh dựa trên giá trị thực tế của bạn)
        # Ví dụ: R cao, G và B thấp. Tỷ lệ R so với G và B cao.
        if r > 300 and g < 200 and b < 200 and (float(r) / (g + 1) > 2.0) and (float(r) / (b + 1) > 2.0):
            tank.stop()
            sound.speak("Moi ban lay hang")
            display.clear()
            display.text_pixels("Den diem giao hang DO!", x=0, y=0)
            display.update()
            sleep(1)
            return


def wait_for_second_press():
    """Chờ nhấn lần 2 xác nhận nhận hàng, hoặc tự động quay về sau 4 phút."""
    global delivery_done
    start = time()
    while time() - start < 240:
        if touch.is_pressed:
            sleep(0.1)  # Chống dội nút
            if touch.is_pressed:
                sound.speak("Cam on ban da nhan hang")
                display.clear()
                display.text_pixels("Cam on ban da nhan hang!", x=0, y=0)
                display.update()
                sleep(1)
                delivery_done = True
                go_back()
                return
        sleep(0.1)

    if not delivery_done:
        sound.speak("Khong nhan hang. Quay ve")
        display.clear()
        display.text_pixels("Khong nhan hang. Quay ve.", x=0, y=0)
        display.update()
        sleep(1)
        go_back()


def go_back():
    """Robot quay đầu và dò line đen quay về điểm bắt đầu (màu vàng)."""
    global integral, last_error
    gyro.reset()
    tank.on(SpeedPercent(BASE_SPEED_PERCENT), SpeedPercent(-BASE_SPEED_PERCENT))
    while abs(gyro.angle) < 180:
        sleep(0.01)
    tank.stop()

    tank.on_for_seconds(SpeedPercent(BASE_SPEED_PERCENT), SpeedPercent(BASE_SPEED_PERCENT), 1)
    tank.stop()

    while True:
        reflection = color.reflected_light_intensity
        error = reflection - TARGET_REFLECTION
        integral += error
        derivative = error - last_error
        turn = Kp * error + Ki * integral + Kd * derivative
        
        # GIỚI HẠN GIÁ TRỊ CỦA 'turn'
        max_turn_magnitude = 60 # Sử dụng lại giá trị giới hạn
        turn = max(min(turn, max_turn_magnitude), -max_turn_magnitude)

        tank.on(SpeedPercent(BASE_SPEED_PERCENT - turn), SpeedPercent(BASE_SPEED_PERCENT + turn))
        last_error = error

        r, g, b = color.raw #màu vàng
        # Điều kiện nhận diện màu VÀNG (Cần điều chỉnh dựa trên giá trị thực tế của bạn)
        # Ví dụ: R và G cao, B thấp. R và G gần bằng nhau.
        if r > 500 and g > 500 and b < 250 and (abs(r - g) < 150):
            tank.stop()
            sound.speak("Da quay ve vi tri xuat phat")
            display.clear()
            display.text_pixels("Da quay ve VT xuat phat!", x=0, y=0)
            display.update()
            sleep(1)

            gyro.reset()
            tank.on(SpeedPercent(BASE_SPEED_PERCENT), SpeedPercent(-BASE_SPEED_PERCENT))
            while abs(gyro.angle) < 180:
                sleep(0.01)
            tank.stop()
            sound.speak("San sang cho dot tiep theo")
            display.clear()
            display.text_pixels("San sang dot tiep theo!", x=0, y=0)
            display.update()
            sleep(1)
            break


# === CHƯƠNG TRÌNH CHÍNH ===
sound.speak("sound/Sẵn sàng.wav")
display.clear()
display.text_pixels("San sang...", x=0, y=0)
display.text_pixels("Nhan cam bien cham de bat dau", x=0, y=20)
display.update()


# Chờ người nhấn 1 lần để bắt đầu giao hàng
while True:
    if touch.is_pressed:
        sleep(0.1) 
        if touch.is_pressed: 
            sound.speak("Toi se di giao hang")
            display.clear()
            display.text_pixels("Dang di giao hang...", x=0, y=0)
            display.update()
            sleep(1)
            delivery_started = True
            break

# Khởi động thread quay cảm biến siêu âm
# motor_ultrasonic.on_for_degrees(SpeedPercent(20), 0)
# Thread(target=rotate_ultrasonic, daemon=True).start() 

# Dò line tới nơi giao hàng
follow_line_until_red()

# Chờ xác nhận nhận hàng hoặc quay về
wait_for_second_press()

# Kết thúc chương trình
display.clear()
display.text_pixels("Nhiem vu hoan thanh!", x=0, y=0)
display.update()
sleep(1)