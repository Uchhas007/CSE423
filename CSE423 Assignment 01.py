# TASK 1

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random

w, h = 1000, 800
mode = 0.5
base = 200

def ground():
    glColor3f(1, 1, 0)
    glBegin(GL_TRIANGLES)
    glVertex2f(0, 0)
    glVertex2f(w, 0)
    glVertex2f(0, base)
    glVertex2f(0, base)
    glVertex2f(w, 0)
    glVertex2f(w, base)
    glEnd()

def house():
    glColor3f(0, 0.5, 0)
    glBegin(GL_TRIANGLES)
    glVertex2f(300, 300)
    glVertex2f(500, 300)
    glVertex2f(400, 400)
    glEnd()

    glColor3f(0.5, 0, 0)
    glBegin(GL_TRIANGLES)
    glVertex2f(300, base)
    glVertex2f(500, base)
    glVertex2f(300, 300)
    glVertex2f(300, 300)
    glVertex2f(500, base)
    glVertex2f(500, 300)
    glEnd()

    glColor3f(0, 0, 1)
    glBegin(GL_TRIANGLES)
    glVertex2f(380, base)
    glVertex2f(420, base)
    glVertex2f(380, 260)
    glVertex2f(380, 260)
    glVertex2f(420, base)
    glVertex2f(420, 260)
    glEnd()

    glBegin(GL_TRIANGLES)
    glVertex2f(320, 260)
    glVertex2f(340, 260)
    glVertex2f(320, 280)
    glVertex2f(320, 280)
    glVertex2f(340, 260)
    glVertex2f(340, 280)
    glEnd()

    glBegin(GL_TRIANGLES)
    glVertex2f(460, 260)
    glVertex2f(480, 260)
    glVertex2f(460, 280)
    glVertex2f(460, 280)
    glVertex2f(480, 260)
    glVertex2f(480, 280)
    glEnd()

raindrops = []
for i in range(100):
    x = random.randint(0, w)
    y = random.randint(h, h + 300)
    raindrops.append([x, y])

def rain():
    glColor3f(0, 0, 1)
    glBegin(GL_POINTS)
    for i in raindrops:
        glVertex2f(i[0], i[1])
    glEnd()



speed = 3
angle = 0
israining = True

def rainfall():
    for i in raindrops:
        i[0] += angle
        i[1] -= speed
        if i[1] < 0:
            i[0] = random.randint(0, w)
            i[1] = random.randint(h, h + 300)

def display():
    glClearColor(mode, mode, mode, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    ground()
    house()
    rain()
    glutSwapBuffers()

def startRain():
    if israining:
        rainfall()
    glutPostRedisplay()

def weather(key, x, y):
    global mode, israining
    if key == b'd':
        mode = min(1.0, mode + 0.1)
    elif key == b'n':
        mode = max(0.0, mode - 0.1)
    elif key == b' ':
        israining = not israining
    glutPostRedisplay()

def rainAngle(key, x, y):
    global angle
    if key == GLUT_KEY_LEFT:
        angle -= 1
    elif key == GLUT_KEY_RIGHT:
        angle += 1
    glutPostRedisplay()

def init():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, w, 0, h)
    glPointSize(3)
    glEnable(GL_POINT_SMOOTH)




#driver code
glutInit()
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
glutInitWindowSize(w, h)
glutInitWindowPosition(100, 100)
glutCreateWindow(b"Task 1")
init()
glutDisplayFunc(display)
glutIdleFunc(startRain)
glutKeyboardFunc(weather)
glutSpecialFunc(rainAngle)
glutMainLoop()



# TASK 2
# from OpenGL.GL import *
# from OpenGL.GLUT import *
# import random

# w, h = 1000, 800

# size = 8
# speed = 2
# points = []
# def generatePoints(x, y):
#     temp_x = random.choice([-1, 1])
#     temp_y = random.choice([-1, 1])
#     r = random.random()
#     g = random.random()
#     b = random.random()
#     points.append([x, y, r, g, b, temp_x, temp_y, speed])

# blink = False
# freeze = False
# c = 0
# def plotPoints():
#     glPointSize(size)
#     glBegin(GL_POINTS)
#     for i in points:
#         if not blink or (c % 1000 < 500):
#             glColor3f(i[2], i[3], i[4])
#         else:
#             glColor3f(0.0, 0.0, 0.0)
#         glVertex2f(i[0], i[1])
#     glEnd()

# def display():
#     glClear(GL_COLOR_BUFFER_BIT)
#     plotPoints()
#     glutSwapBuffers()

# def update():
#     global c
#     if not freeze:
#         for i in points:
#             i[0] += i[5] * i[7]
#             i[1] += i[6] * i[7]

#             if i[0] <= 0 or i[0] >= w:
#                 i[5] *= -1
#             if i[1] <= 0 or i[1] >= h:
#                 i[6] *= -1

#         if blink:
#             c += 16

#     glutPostRedisplay()
#     glutTimerFunc(16, lambda v: update(), 0)

# def spawn(button, state, x, y):
#     global blink, c
#     if freeze:
#         return

#     if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
#         generatePoints(x, h - y)
#     elif button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
#         blink = not blink
#         c = 0

# def acc(key, x, y):
#     if freeze:
#         return
#     if key == GLUT_KEY_UP:
#         for i in points:
#             i[7] += 0.5
#     elif key == GLUT_KEY_DOWN:
#         for i in points:
#             if i[7] > 0.5:
#                 i[7] -= 0.5

# def stop(key, x, y):
#     global freeze
#     if key == b' ':
#         freeze = not freeze

# def init():
#     glClearColor(0.0, 0.0, 0.0, 1.0)
#     glMatrixMode(GL_PROJECTION)
#     glLoadIdentity()
#     glOrtho(0, w, 0, h, -1, 1)
#     glMatrixMode(GL_MODELVIEW)


# # driver code
# glutInit()
# glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
# glutInitWindowSize(w, h)
# glutCreateWindow(b"Task 2")
# init()
# glutDisplayFunc(display)
# glutMouseFunc(spawn)
# glutSpecialFunc(acc)
# glutKeyboardFunc(stop)
# glutTimerFunc(16, lambda v: update(), 0)
# glutMainLoop()