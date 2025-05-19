import pygame
import time
if __name__ == '__main__':
    from led_on_pi5 import sc
else:
    from scripts.led_on_pi5 import sc

def f(r,g,b,t):
    sc(r,g,b)
    time.sleep(t)

def play():
    print("我是奶龙")
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.load("static/sounds/milk.mp3")
    pygame.mixer.music.play()

    f(253,160,0,1.2)
    f(0,0,0,0.05)
    f(253,160,0,1.4)
    f(0,0,0,0.05)

    # 我会喷火，你会吗
    f(253,160,0,2.6)

    f(255,30,0,0.1)
    f(0,0,0,0.1)
    f(255,30,0,0.1)
    f(0,0,0,0.1)

    f(253,160,0,0.5)


    for _ in range(3):
        f(255,30,0,0.07)
        f(0,0,0,0.07)

    for _ in range(6):
        f(255,30,0,0.05)
        f(0,0,0,0.05)

    # 我还会变色呢
    f(253,160,0,3.5)

    for _ in range(2):
        f(232,41,189,0.28)
        f(41,141,232,0.28)
        f(80,232,41,0.28)
        f(232,41,93,0.28)

    f(253,160,0,2.3)

    pygame.mixer.music.stop()

if __name__ == '__main__':
    pygame.mixer.init()
    play()
