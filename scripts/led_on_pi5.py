import time

import adafruit_pixelbuf
import board
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.rainbowsparkle import RainbowSparkle
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_raspberry_pi5_neopixel_write import neopixel_write
import threading

NEOPIXEL = board.D13
num_pixels = 32 

class Pi5Pixelbuf(adafruit_pixelbuf.PixelBuf):
    def __init__(self, pin, size, **kwargs):
        self._pin = pin
        super().__init__(size=size, **kwargs)

    def _transmit(self, buf):
        neopixel_write(self._pin, buf)

pixels = Pi5Pixelbuf(NEOPIXEL, num_pixels, auto_write=True, byteorder="BGR")

rainbow = Rainbow(pixels, speed=0.02, period=2)
rainbow_chase = RainbowChase(pixels, speed=0.02, size=5, spacing=3)
rainbow_comet = RainbowComet(pixels, speed=0.02, tail_length=7, bounce=True)
rainbow_sparkle = RainbowSparkle(pixels, speed=0.02, num_sparkles=15)


animations = AnimationSequence(
    rainbow,
    # rainbow_chase,
    # rainbow_comet,
    # rainbow_sparkle,
    # advance_interval=5,
    auto_clear=True,
)

playing = True
# stop_event = threading.Event()
lock = threading.Lock()
animation_thread = None
milking = False

def start():
    global playing
    with lock:
        playing = True

def pause():
    global playing
    with lock:
        playing = False

# def stop():
#     stop_event.set()

def play_animation():
    print("fff")
    # while not stop_event.is_set():
    while True:
        with lock:
            if milking:
                pass
            elif playing:
                animations.animate()
            else:
                pixels.fill((255,255,255))
                pixels.show()
        # time.sleep(1)

def init_animation_thread():
    global animation_thread
    # if animation_thread is None or not animation_thread.is_alive():
    animation_thread = threading.Thread(target=play_animation, daemon=True)
    animation_thread.start()


def operate_led(state):
    print(state)
    if state == "on":
        start()
    else:
        pause()

def sc(r,g,b):
    global milking
    milking = True
    print("setting color")
    pixels.fill((b,r,g))
    pixels.show()