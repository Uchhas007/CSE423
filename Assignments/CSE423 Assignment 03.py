from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import math, random, time

WIN_W, WIN_H = 1000, 800
ASPECT = WIN_W / float(WIN_H)
FOV_Y = 70.0

half_grid = 600.0
wall_h = 200.0
wall_thickness = 10.0

player_pos = [0.0, 0.0, 0.0]
player_radii = 30.0
player_speed = 220.0
gun_angle = 0.0

enemy_count = 5
enemies = []
enemies_radii = 20.0
enemies_speed = 60.0

bullets = []
bullets_speed = 600.0
bullets_size = 8.0
bullets_cd = 0.10
last_shot = 0.0
missed = 0
score = 0
life = 5
game_over = False
INVULN_TIL = 0.0

cheat_mode = False
cheat_vision = False

fpv = False
cam_angle = -40.0
cam_height = 260.0
cam_dist = 900.0

LAST_T = None

quad = None

keys = set()

white = (1.0, 1.0, 1.0)
purple = (0.7, 0.5, 0.95)
red = (1.0, 0.2, 0.2)
blue = (0.2, 0.5, 1.0)
cyan = (0.0, 1.0, 1.0)
green = (0.0, 1.0, 0.0)

random.seed(423)

def clamp(x, low, high):
    if x < low:
        return low
    else:
        if x > high:
            return high
        else:
            return x

def angleVector(deg):
    r = math.radians(deg)
    return [math.cos(r), 0.0, math.sin(r)]

def vectorNormal(v):
    m = math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])
    if m <= 1e-8:
        return [0.0,0.0,0.0]
    return [v[0]/m, v[1]/m, v[2]/m]

def vectorSubtraction(a,b):
    return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]

def vectorLength(v):
    return math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])

def dot(a,b):
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]

def drawText(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glMatrixMode(GL_PROJECTION); glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_LIGHTING)
    glColor3f(1,1,1)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glEnable(GL_LIGHTING)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def drawSquare(size=1.0):
    glBegin(GL_QUADS)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(size, 0.0, 0.0)
    glVertex3f(size, 0.0, size)
    glVertex3f(0.0, 0.0, size)
    glEnd()

def drawCuboid(w,h,d, color=None):
    if color:
        glColor3f(*color)
    glPushMatrix()
    glScalef(w,h,d)
    glutSolidCube(1.0)
    glPopMatrix()

def drawCylinder(radius, height, color=None):
    if color:
        glColor3f(*color)
    glPushMatrix()
    glRotatef(-90, 1,0,0)
    gluCylinder(quad, radius, radius, height, 16, 2)
    glPopMatrix()

def drawSphere(radius, color=None):
    if color:
        glColor3f(*color)
    gluSphere(quad, radius, 16, 16)

def drawGround():
    tiles = 20
    size = (2.0*half_grid)/tiles
    lighting_was = glIsEnabled(GL_LIGHTING)
    if lighting_was:
        glDisable(GL_LIGHTING)
    glDisable(GL_CULL_FACE)
    for i in range(tiles):
        for j in range(tiles):
            x0 = -half_grid + i*size
            z0 = -half_grid + j*size
            if (i + j) % 2 == 0:
                glColor3f(*white)
            else:
                glColor3f(*purple)
            glPushMatrix()
            glTranslatef(x0, 0.0, z0)
            drawSquare(size)
            glPopMatrix()
    glEnable(GL_CULL_FACE)
    if lighting_was:
        glEnable(GL_LIGHTING)

def drawWalls():
    glPushMatrix()
    glTranslatef(half_grid+wall_thickness*0.5, wall_h*0.5, 0.0)
    glColor3f(0.0, 0.0, 1.0)
    glScalef(wall_thickness, wall_h, 2*half_grid+wall_thickness)
    glutSolidCube(1.0)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(-(half_grid+wall_thickness*0.5), wall_h*0.5, 0.0)
    glColor3f(0.0, 1.0, 1.0)
    glScalef(wall_thickness, wall_h, 2*half_grid+wall_thickness)
    glutSolidCube(1.0)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.0, wall_h*0.5, half_grid+wall_thickness*0.5)
    glColor3f(0.0, 1.0, 0.0)
    glScalef(2*half_grid+wall_thickness, wall_h, wall_thickness)
    glutSolidCube(1.0)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.0, wall_h*0.5, -(half_grid+wall_thickness*0.5))
    glColor3f(1.0, 0.0, 0.0)
    glScalef(2*half_grid+wall_thickness, wall_h, wall_thickness)
    glutSolidCube(1.0)
    glPopMatrix()

def drawGun(color=None):
    if color:
        glColor3f(*color)
    drawCuboid(10, 10, 30, None)
    glPushMatrix()
    glTranslatef(0, 0, 20)
    drawCuboid(6, 6, 20, None)
    glPopMatrix()

def drawPlayer(lie_down=False):
    glPushMatrix()
    glTranslatef(player_pos[0], 0.0, player_pos[2])
    if lie_down:
        glRotatef(90, 0,0,1)
    glRotatef(gun_angle, 0,1,0)
    glPushMatrix()
    glTranslatef(-10, 25, 0)
    drawCylinder(5, 50, blue)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(10, 25, 0)
    drawCylinder(5, 50, blue)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0, 70, 0)
    drawCylinder(12, 60, (0.5, 0.5, 0.0))
    glPopMatrix()
    glPushMatrix()
    glTranslatef(-18, 85, 0)
    glRotatef(90, 1,0,0)
    drawCylinder(4, 45, (1.0, 0.8, 0.7))
    glPopMatrix()
    glPushMatrix()
    glTranslatef(18, 85, 0)
    glRotatef(90, 1,0,0)
    drawCylinder(4, 45, (1.0, 0.8, 0.7))
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0, 110, 0)
    drawSphere(14, (0.0, 0.0, 0.0))
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0, 95, 35)
    drawGun(blue)
    glPopMatrix()
    glPopMatrix()

def drawEnemy(enemy):
    pos = enemy["pos"]
    scale = enemy["scale_now"]
    r_body = enemies_radii * scale
    r_head = (enemies_radii*0.6) * scale
    glPushMatrix()
    glTranslatef(pos[0], 0.0, pos[2])
    glPushMatrix()
    glTranslatef(0, r_body, 0)
    drawSphere(r_body, red)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0, r_body*2 + r_head, 0)
    drawSphere(r_head, red)
    glPopMatrix()
    glPopMatrix()

def drawBullet(bullet):
    glPushMatrix()
    glTranslatef(bullet["pos"][0], bullet["pos"][1], bullet["pos"][2])
    glColor3f(1.0, 1.0, 0.2)
    drawCuboid(bullets_size, bullets_size, bullets_size)
    glPopMatrix()

def randomPositon():
    while True:
        x = random.uniform(-half_grid+40, half_grid-40)
        z = random.uniform(-half_grid+40, half_grid-40)
        if vectorLength([x-player_pos[0], 0.0, z-player_pos[2]]) > 220.0:
            return [x, 0.0, z]

def spawnEnemies():
    global enemies
    enemies = []
    for i in range(enemy_count):
        pos = randomPositon()
        enemies.append({
            "pos": pos,
            "phase": random.uniform(0, math.pi*2.0),
            "base_r": enemies_radii,
            "speed": enemies_speed,
            "scale_now": 1.0
        })

def resetGame():
    global player_pos, gun_angle, bullets, missed, score, life, game_over, INVULN_TIL
    player_pos = [0.0, 0.0, 0.0]
    gun_angle = 0.0
    bullets = []
    missed = 0
    score = 0
    life = 5
    game_over = False
    INVULN_TIL = 0.0
    spawnEnemies()

def arena(p, radius=0.0):
    p[0] = clamp(p[0], -half_grid+wall_thickness+radius, half_grid-wall_thickness-radius)
    p[2] = clamp(p[2], -half_grid+wall_thickness+radius, half_grid-wall_thickness-radius)

def updatePlayer(dt):
    global player_pos
    if game_over:
        return
    move = 0.0
    if b'w' in keys:
        move += player_speed
    if b's' in keys:
        move -= player_speed
    if abs(move) > 0.0:
        f = angleVector(gun_angle)
        player_pos[0] += f[0] * move * dt
        player_pos[2] += f[2] * move * dt
        arena(player_pos, player_radii*0.6)

def updateEnemies(t, dt):
    global life, INVULN_TIL, game_over
    if game_over:
        return
    for enemy in enemies:
        scale = 1.0 + 0.22*math.sin(t*2.0 + enemy["phase"])
        enemy["scale_now"] = scale
        to_p = vectorSubtraction([player_pos[0], 0.0, player_pos[2]], enemy["pos"])
        d = vectorLength(to_p)
        if d > 1e-3:
            v = [to_p[0]/d, 0.0, to_p[2]/d]
            spd = enemy["speed"]
            enemy["pos"][0] += v[0]*spd*dt
            enemy["pos"][2] += v[2]*spd*dt
            arena(enemy["pos"], enemies_radii*scale)
        if time.time() > INVULN_TIL:
            pr = player_radii
            er = enemies_radii*scale
            if vectorLength([enemy["pos"][0]-player_pos[0], 0.0, enemy["pos"][2]-player_pos[2]]) <= (pr+er)*0.8:
                life -= 1
                print(f"Remaining player life: {life}")
                INVULN_TIL = time.time() + 0.6
                enemy["pos"] = randomPositon()

def updateBullets(dt):
    global missed, score
    if game_over:
        return
    alive = []
    for bullet in bullets:
        if cheat_mode and bullet.get("target") is not None:
            target = bullet["target"]
            v = vectorSubtraction(target["pos"], bullet["pos"])
            v[1] = 0.0
            bullet["dir"] = vectorNormal(v)
        bullet["pos"][0] += bullet["dir"][0]*bullet["speed"]*dt
        bullet["pos"][1] += bullet["dir"][1]*bullet["speed"]*dt
        bullet["pos"][2] += bullet["dir"][2]*bullet["speed"]*dt
        out = (abs(bullet["pos"][0]) > half_grid+50 or
               abs(bullet["pos"][2]) > half_grid+50)
        hit = False
        if not out:
            br = bullets_size*0.7
            for enemy in enemies:
                er = enemies_radii*enemy["scale_now"]
                if vectorLength([enemy["pos"][0]-bullet["pos"][0], 0.0, enemy["pos"][2]-bullet["pos"][2]]) <= (er + br):
                    score += 1
                    enemy["pos"] = randomPositon()
                    hit = True
                    break
        if (not cheat_mode) and out and not hit:
            missed += 1
            print(f"Bullet missed: {missed}")
        if (not out) and (not hit) and (time.time()-bullet["born_t"] < 4.0):
            alive.append(bullet)
    bullets[:] = alive

def enemyDirection(muzzle_pos):
    best_d = 1e18
    best_enemy = None
    for enemy in enemies:
        v = vectorSubtraction(enemy["pos"], muzzle_pos)
        v[1] = 0.0
        d = vectorLength(v)
        if d < best_d:
            best_d = d
            best_enemy = enemy
    if best_enemy is None:
        return ([1.0,0.0,0.0], None)
    return (vectorNormal(vectorSubtraction(best_enemy["pos"], muzzle_pos)), best_enemy)

def shoot():
    global last_shot, bullets
    if game_over:
        return
    now = time.time()
    if now - last_shot < bullets_cd:
        return
    last_shot = now
    local = [0.0, 95.0, 55.0]
    r = math.radians(gun_angle)
    cos_r, sin_r = math.cos(r), math.sin(r)
    world_offset = [
        local[0]*cos_r - local[2]*sin_r,
        local[1],
        local[0]*sin_r + local[2]*cos_r
    ]
    muzzle = [
        player_pos[0] + world_offset[0],
        world_offset[1],
        player_pos[2] + world_offset[2]
    ]

    print("Player Bullet Fired!")

    if cheat_mode:
        dir_vec, target = enemyDirection(muzzle)
        bullets.append({
            "pos": muzzle[:],
            "dir": vectorNormal(dir_vec),
            "speed": bullets_speed,
            "born_t": now,
            "target": target
        })
    else:
        fd = angleVector(gun_angle)
        bullets.append({
            "pos": muzzle[:],
            "dir": vectorNormal(fd),
            "speed": bullets_speed,
            "born_t": now
        })

def cheatMode(t, dt):
    global gun_angle
    if not cheat_mode or game_over:
        return
    gun_angle = (gun_angle + 300.0*dt) % 360.0
    shoot()

def camera():
    if fpv:
        head_y = 110.0
        fd = angleVector(gun_angle)
        right = [fd[2], 0.0, -fd[0]]
        side_offset = 20.0
        back_offset = 15.0
        up_offset = 5.0
        if cheat_mode and cheat_vision:
            y_boost = 12.0
        else:
            y_boost = 0.0
        if cheat_mode and cheat_vision:
            back_offset -= 4.0
        cam_pos = [
            player_pos[0] - fd[0]*back_offset + right[0]*side_offset,
            head_y + up_offset + y_boost,
            player_pos[2] - fd[2]*back_offset + right[2]*side_offset
        ]
        look_at = [
            cam_pos[0] + fd[0]*100.0,
            cam_pos[1] + 0.0,
            cam_pos[2] + fd[2]*100.0
        ]
        gluLookAt(cam_pos[0], cam_pos[1], cam_pos[2],
                  look_at[0], look_at[1], look_at[2],
                  0,1,0)
    else:
        r = math.radians(cam_angle)
        cx = math.cos(r)*cam_dist
        cz = math.sin(r)*cam_dist
        cam_pos = [cx, cam_height, cz]
        gluLookAt(cam_pos[0], cam_pos[1], cam_pos[2],
                  0, 0, 0,
                  0, 1, 0)

def battleground():
    drawGround()
    drawWalls()
    for enemy in enemies:
        drawEnemy(enemy)
    drawPlayer(lie_down=game_over)
    for bullet in bullets:
        drawBullet(bullet)

def displayText():
    glDisable(GL_LIGHTING)
    if game_over:
        drawText(10, WIN_H-30, f"Game is Over. Your score is {score}")
        drawText(10, WIN_H-55, f"Press R to RESTART the game.")
    else:
        drawText(10, WIN_H-30, f"Player life Remaining: {life}")
        drawText(10, WIN_H-55, f"Game score: {score}")
        drawText(10, WIN_H-80, f"Player Bullet missed: {missed}")
    glEnable(GL_LIGHTING)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    camera()
    battleground()
    displayText()
    glutSwapBuffers()

def reshape(w,h):
    global WIN_W, WIN_H, ASPECT
    WIN_W, WIN_H = max(1,w), max(1,h)
    ASPECT = WIN_W/float(WIN_H)
    glViewport(0,0,WIN_W,WIN_H)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(FOV_Y, ASPECT, 1.0, 5000.0)
    glMatrixMode(GL_MODELVIEW)

def idle():
    global LAST_T, game_over
    now = time.time()
    if LAST_T is None:
        LAST_T = now
    dt = now - LAST_T
    dt = clamp(dt, 0.0, 0.05)
    LAST_T = now
    if not game_over:
        updatePlayer(dt)
        updateEnemies(now, dt)
        updateBullets(dt)
        cheatMode(now, dt)
        if life <= 0 or missed >= 10:
            game_over = True
    glutPostRedisplay()

def keyboardListenerD(key, x, y):
    global gun_angle, cheat_mode, cheat_vision
    keys.add(key)
    if key == b'a':
        gun_angle = (gun_angle - 15.0) % 360.0
    elif key == b'd':
        gun_angle = (gun_angle + 15.0) % 360.0
    elif key == b'c':
        cheat_mode = not cheat_mode
    elif key == b'v':
        cheat_vision = not cheat_vision
    elif key in (b'r', b'R'):
        resetGame()
    elif key == b'\x1b':
        try:
            from OpenGL.GLUT import glutLeaveMainLoop
            glutLeaveMainLoop()
        except Exception:
            import sys; sys.exit(0)

def keyboardListenerU(key, x, y):
    if key in keys:
        keys.remove(key)

def specialKeyListener(key, x, y):
    global cam_angle, cam_height
    if key == GLUT_KEY_LEFT:
        cam_angle -= 3.0
    elif key == GLUT_KEY_RIGHT:
        cam_angle += 3.0
    elif key == GLUT_KEY_UP:
        cam_height = clamp(cam_height + 12.0, 80.0, 800.0)
    elif key == GLUT_KEY_DOWN:
        cam_height = clamp(cam_height - 12.0, 80.0, 800.0)

def mouseListener(button, state, x, y):
    global fpv
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        shoot()
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        fpv = not fpv

def showScreen():
    global quad
    glClearColor(0.06, 0.08, 0.12, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION,  (500.0, 800.0, 500.0, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE,   (0.9, 0.9, 0.9, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR,  (0.6, 0.6, 0.6, 1.0))
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    quad = gluNewQuadric()
    gluQuadricNormals(quad, GLU_SMOOTH)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutCreateWindow(b"Assignment 03")
    showScreen()
    resetGame()
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(FOV_Y, ASPECT, 1.0, 5000.0)
    glMatrixMode(GL_MODELVIEW)
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboardListenerD)
    glutKeyboardUpFunc(keyboardListenerU)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutMainLoop()

if __name__ == "__main__":
    main()
