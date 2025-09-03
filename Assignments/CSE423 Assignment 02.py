from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import time
import math

w, h = 400, 700
cw, ch = 60, 10
dsize = 30
btn_size = 50

cpos = w // 2
dmx = random.randint(0, w - dsize)
dmy = h
dspeed = 150
score = 0
playing = True
paused = False
game_over = False
last_time = time.time()

colour = []
for i in range(3):
    c = random.random()
    colour.append(c)


restart_btn = [20, h - 50, btn_size, btn_size]
pause_btn = [w//2 - btn_size//2, h - 50, btn_size, btn_size]
exit_btn = [w - 50, h - 50, btn_size, btn_size]

def drawDiamond():
    x = dmx
    y = int(dmy)
    half = dsize // 2
    glColor3f(*colour)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y + half) 
    glVertex2f(x + half, y) 
    glVertex2f(x, y - half) 
    glVertex2f(x - half, y) 
    glEnd()

def drawCatcher():
    global cpos
    x = cpos
    y = 40
    half = cw // 2
    if game_over:
        color = (1, 0, 0)
    else: 
        color = (1, 1, 1)
        
    glColor3f(*color)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x - half, y)
    glVertex2f(x + half, y)
    glVertex2f(x + half, y + ch)
    glVertex2f(x - half, y + ch)
    glEnd()

def drawPausePlayBtn():
    glColor3f(1, 0.75, 0)
    cx = pause_btn[0] + btn_size // 2
    cy = pause_btn[1] + btn_size // 2

    if paused:
        glBegin(GL_LINE_LOOP)
        glVertex2f(cx - 5, cy - 6)
        glVertex2f(cx - 5, cy + 6)
        glVertex2f(cx + 6, cy)
        glEnd()
    else:
        glBegin(GL_LINES)
        glVertex2f(cx - 6, cy - 6)
        glVertex2f(cx - 6, cy + 6)
        glVertex2f(cx + 3, cy - 6)
        glVertex2f(cx + 3, cy + 6)
        glEnd()

def drawExitBtn():
    glColor3f(1, 0, 0) 
    cx = exit_btn[0] + btn_size // 2
    cy = exit_btn[1] + btn_size // 2
    size = 7
    glBegin(GL_LINES)
    glVertex2f(cx - size, cy - size)
    glVertex2f(cx + size, cy + size)
    glVertex2f(cx + size, cy - size)
    glVertex2f(cx - size, cy + size)
    glEnd()

def drawRestartBtn():
    glColor3f(0, 1, 1)
    cx = restart_btn[0] + btn_size // 2
    cy = restart_btn[1] + btn_size // 2
    glBegin(GL_LINES)
    glVertex2f(cx + 6, cy)
    glVertex2f(cx - 6, cy)
    glVertex2f(cx - 6, cy)
    glVertex2f(cx - 2, cy + 4)
    glVertex2f(cx - 6, cy)
    glVertex2f(cx - 2, cy - 4)
    glEnd()

def draw_buttons():
    drawRestartBtn()
    drawPausePlayBtn()
    drawExitBtn()

def update():
    global dmy, dmx, colour, score, dspeed
    global game_over, last_time
    current_time = time.time()
    dt = current_time - last_time
    last_time = current_time
    if playing and not paused and not game_over:
        dmy -= dspeed * dt
        if collision():
            score += 1
            print("Score:", score)
            resetDiamond()
            dspeed += 10
        elif dmy - dsize // 2 <= 40:
            print("Game Over. Final Score:", score)
            game_over = True
    glutPostRedisplay()
    glutTimerFunc(16, lambda x: update(), 0)

def collision():
    diamond_half = dsize // 2
    diamond_box = (dmx - diamond_half, dmy - diamond_half, dsize, dsize)
    catcher_box = (cpos - cw // 2, 40, cw, ch)
    return (
        diamond_box[0] < catcher_box[0] + catcher_box[2] and diamond_box[0] + diamond_box[2] > catcher_box[0] and diamond_box[1] < catcher_box[1] + catcher_box[3] and diamond_box[1] + diamond_box[3] > catcher_box[1]
    )

def resetDiamond():
    global dmx, dmy, colour
    dmx = random.randint(dsize, w - dsize)
    dmy = h
    colour = [random.uniform(0.3, 1.0) for _ in range(3)]

def mouse(button, state, x, y):
    global paused, score, dspeed, game_over
    if state == GLUT_DOWN:
        y = h - y
        if inside(x, y, restart_btn):
            print("Starting Over")
            score = 0
            dspeed = 150
            game_over = False
            paused = False
            resetDiamond()
        elif inside(x, y, pause_btn):
            paused = not paused
        elif inside(x, y, exit_btn):
            print("Goodbye. Final Score:", score)
            glutLeaveMainLoop()

def inside(x, y, rect):
    return rect[0] <= x <= rect[0]+rect[2] and rect[1] <= y <= rect[1]+rect[3]

def keyboard(key, x, y):
    global cpos
    if game_over or paused:
        return
    if key == GLUT_KEY_LEFT:
        cpos = max(cpos - 20, cw//2)
    elif key == GLUT_KEY_RIGHT:
        cpos = min(cpos + 20, w - cw//2)

def display():
    glClear(GL_COLOR_BUFFER_BIT)
    drawDiamond()
    drawCatcher()
    draw_buttons()
    glutSwapBuffers()

def init():
    glClearColor(0.1, 0.1, 0.1, 1)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, w, 0, h)
    glPointSize(2)
    glLineWidth(2)
    
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(w, h)
    glutCreateWindow(b"Catch the Diamonds!")
    init()
    glutDisplayFunc(display)
    glutSpecialFunc(keyboard)
    glutMouseFunc(mouse)
    glutTimerFunc(16, lambda x: update(), 0)
    glutMainLoop()

main()