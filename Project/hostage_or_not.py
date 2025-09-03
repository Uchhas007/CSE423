from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import math, random, time

win_w, win_h = 1200, 800
aspect = win_w / float(win_h)
fov_y = 70.0
target_fov = 70.0

random.seed(1337)

# -----------------------------
# Colors
# -----------------------------
black = (0.0, 0.0, 0.0)
white = (1.0, 1.0, 1.0)
dark_yellow = (0.78, 0.72, 0.28)
room_tint = (0.06, 0.05, 0.03)
enemy_skin = (0.95, 0.9, 0.85)
enemy_cloth = (0.05, 0.05, 0.05)
hostage_cloth = (0.1, 0.9, 0.95)
bullet_color = (0.0, 0.0, 0.0)
enemy_bullet_color = (0.9, 0.2, 0.2)

# -----------------------------
# Game State
# -----------------------------
state_menu = 0
state_game = 1
state_game_over = 2
state_win = 3

game_state = state_menu
menu_show_diff = False

difficulty = "Medium"

player_pos = [0.0, 20.0, 0.0]   # y ~ standing height
player_yaw = 0.0
player_pitch = 0.0
player_speed = 240.0
player_hp = 100
eye_height = 58.0

player_vel_y = 0.0
gravity = -900.0
jump_impulse = 380.0
on_ground = True

right_mouse_down = False
left_mouse_down = False

mag_capacity = 100
mag_ammo = mag_capacity
reload_time = 2.2
reloading = False
reload_end_time = 0.0

player_shot_cd = 0.08
last_player_shot = 0.0

enemy_count = 10
hostage_count = 3

enemies = []    # dict: pos[x,y,z], hp, next_shot_t
hostages = []   # dict: pos[x,y,z]
bullets = []    # dict: pos[x,y,z], dir[x,y,z], speed, from_enemy(bool), born_t

enemy_speed = 120.0
enemy_fire_cd = 1.0
enemy_accuracy = 0.92

enemy_bullet_speed = 420.0
player_bullet_speed = 800.0
bullet_radius = 6.0

quadric = None

last_t = None

keys = set()

mouse_last_x = None
mouse_last_y = None
mouse_sensitivity = 0.15

rooms = []
walls = []

# -----------------------------
# Difficulty Setup
# -----------------------------
def applyDifficulty(name):
    global enemy_speed, enemy_fire_cd, enemy_accuracy
    if name == "Easy":
        enemy_speed = 90.0
        enemy_fire_cd = 1.4
        enemy_accuracy = 0.70
    elif name == "Medium":
        enemy_speed = 120.0
        enemy_fire_cd = 1.0
        enemy_accuracy = 0.88
    else:
        enemy_speed = 150.0
        enemy_fire_cd = 0.66
        enemy_accuracy = 0.97

# -----------------------------
# Math Helpers
# -----------------------------
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

def vectorSubtraction(a, b):
    return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]

def vectorLength(v):
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])

def vectorNormal(v):
    m = vectorLength(v)
    if m <= 1e-8:
        return [0.0, 0.0, 0.0]
    return [v[0]/m, v[1]/m, v[2]/m]

def addScaled(a, b, s):
    return [a[0] + b[0]*s, a[1] + b[1]*s, a[2] + b[2]*s]

# -----------------------------
# Primitive Draw
# -----------------------------
def drawCuboid(w, h, d, color=None):
    if color:
        glColor3f(*color)
    glPushMatrix()
    glScalef(w, h, d)
    glutSolidCube(1.0)
    glPopMatrix()

def drawSphere(r, color=None):
    if color:
        glColor3f(*color)
    gluSphere(quadric, r, 16, 16)

def drawText2D(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=(1,1,1)):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, win_w, 0, win_h)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_LIGHTING)

    glColor3f(color[0], color[1], color[2])
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

    glEnable(GL_LIGHTING)
    glPopMatrix()

    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# -----------------------------
# Environment (Backrooms-like)
# -----------------------------
def buildRooms():
    global rooms, walls
    rooms = []
    walls = []

    # We define rooms as AABBs and create walls for their boundaries + inner partitions
    # Coordinate space: X and Z span [-1200..1200], Y fixed
    # Room blocks
    rooms.append((-900, -300, -900, -200))   # (x1,x2,z1,z2)
    rooms.append((-200,  400, -900, -200))
    rooms.append(( 450, 1100, -900, -200))

    rooms.append((-900, -200, -100,  600))
    rooms.append((-100,  500,  -50,  600))
    rooms.append(( 600, 1100,    0,  600))

    # Convert room bounds to walls around edges (simple perimeter walls)
    wall_h = 220.0
    wall_t = 20.0

    for rx1, rx2, rz1, rz2 in rooms:
        walls.append(((rx1, 0, rz1), (rx2-rx1, wall_h, wall_t)))       # south wall
        walls.append(((rx1, 0, rz2), (rx2-rx1, wall_h, wall_t)))       # north wall
        walls.append(((rx1, 0, rz1), (wall_t, wall_h, rz2-rz1)))       # west wall
        walls.append(((rx2, 0, rz1), (wall_t, wall_h, rz2-rz1)))       # east wall

    # Create a few "openings" (doorways) by not placing a wall segment there.
    # For simplicity, we will carve two corridor gaps by removing overlapping small wall blocks.
    # Practical trick: We'll add "gap markers" that deactivate collision in those areas.
    # To keep it straightforward, we won't subtract; instead we'll just avoid placing additional blockers there.

    # Add internal standalone walls to create narrow backrooms feeling
    walls.append(((-450, 0, -500), (20, wall_h, 600)))
    walls.append(((  50, 0, -300), (20, wall_h, 700)))
    walls.append((( 700, 0, -200), (20, wall_h, 700)))
    walls.append(((-700, 0,  200), (400, wall_h, 20)))
    walls.append((( 300, 0,  320), (500, wall_h, 20)))

def drawRooms():
    glColor3f(dark_yellow[0]*0.8, dark_yellow[1]*0.8, dark_yellow[2]*0.8)
    glDisable(GL_CULL_FACE)

    # Floor slabs (one per room)
    i = 0
    while i < len(rooms):
        rx1, rx2, rz1, rz2 = rooms[i]
        glPushMatrix()
        glTranslatef((rx1+rx2)/2.0, -1.0, (rz1+rz2)/2.0)
        drawCuboid(rx2-rx1, 2.0, rz2-rz1)
        glPopMatrix()
        i = i + 1

    glEnable(GL_CULL_FACE)

    # Walls
    j = 0
    while j < len(walls):
        pos, size = walls[j]
        glPushMatrix()
        glTranslatef(pos[0] + size[0]/2.0, size[1]/2.0, pos[2] + size[2]/2.0)
        glColor3f(dark_yellow[0], dark_yellow[1], dark_yellow[2])
        drawCuboid(size[0], size[1], size[2])
        glPopMatrix()
        j = j + 1

# -----------------------------
# Collision Helpers
# -----------------------------
def clampInsideAABB(pos, half_extents_min, half_extents_max):
    pos[0] = clamp(pos[0], half_extents_min[0], half_extents_max[0])
    pos[2] = clamp(pos[2], half_extents_min[2], half_extents_max[2])

def collideWithWalls(point, radius):
    x = point[0]
    z = point[2]
    k = 0
    while k < len(walls):
        pos, size = walls[k]
        wx = pos[0]
        wy = pos[1]
        wz = pos[2]
        sx = size[0]
        sy = size[1]
        sz = size[2]

        minx = wx
        maxx = wx + sx
        minz = wz
        maxz = wz + sz

        closest_x = clamp(x, minx - radius, maxx + radius)
        closest_z = clamp(z, minz - radius, maxz + radius)

        inside_x = (x > minx - radius) and (x < maxx + radius)
        inside_z = (z > minz - radius) and (z < maxz + radius)

        if inside_x and inside_z:
            dx = min(abs(x - (minx - radius)), abs(x - (maxx + radius)))
            dz = min(abs(z - (minz - radius)), abs(z - (maxz + radius)))
            if dx < dz:
                if abs(x - (minx - radius)) < abs(x - (maxx + radius)):
                    x = minx - radius
                else:
                    x = maxx + radius
            else:
                if abs(z - (minz - radius)) < abs(z - (maxz + radius)):
                    z = minz - radius
                else:
                    z = maxz + radius
        k = k + 1

    point[0] = x
    point[2] = z

# -----------------------------
# Models: Minecraft-like
# -----------------------------
def drawBlockHuman(skin_col, cloth_col):
    glPushMatrix()
    glTranslatef(0.0, 35.0, 0.0)
    drawCuboid(18, 70, 10, cloth_col)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0.0, 80.0, 0.0)
    drawCuboid(20, 20, 20, skin_col)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(-12.0, 60.0, 0.0)
    drawCuboid(8, 35, 8, cloth_col)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(12.0, 60.0, 0.0)
    drawCuboid(8, 35, 8, cloth_col)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(-6.0, 20.0, 0.0)
    drawCuboid(8, 40, 8, cloth_col)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(6.0, 20.0, 0.0)
    drawCuboid(8, 40, 8, cloth_col)
    glPopMatrix()

def drawEnemy(enemy):
    glPushMatrix()
    glTranslatef(enemy["pos"][0], enemy["pos"][1], enemy["pos"][2])
    drawBlockHuman(enemy_skin, enemy_cloth)
    glPopMatrix()

def drawHostage(h):
    glPushMatrix()
    glTranslatef(h["pos"][0], h["pos"][1], h["pos"][2])
    drawBlockHuman(enemy_skin, hostage_cloth)
    glPopMatrix()

# -----------------------------
# Gun (viewmodel)
# -----------------------------
def getCameraVectors():
    yaw_r = math.radians(player_yaw)
    pitch_r = math.radians(player_pitch)

    fx = math.cos(pitch_r) * math.cos(yaw_r)
    fy = math.sin(pitch_r)
    fz = math.cos(pitch_r) * math.sin(yaw_r)
    fwd = [fx, fy, fz]
    fwd = vectorNormal(fwd)

    right = [fwd[2], 0.0, -fwd[0]]
    right = vectorNormal(right)

    up = [-right[1]*fwd[2] + right[2]*fwd[1],
          -right[2]*fwd[0] + right[0]*fwd[2],
          -right[0]*fwd[1] + right[1]*fwd[0]]

    return fwd, right, up

def drawGun():
    anim = 1.0 if (right_mouse_down or left_mouse_down) else 0.0

    fwd, right_v, up_v = getCameraVectors()
    eye = [player_pos[0], player_pos[1] + eye_height, player_pos[2]]

    base_pos = addScaled(eye, right_v, 18.0)
    base_pos = addScaled(base_pos, fwd, 12.0)
    base_pos = addScaled(base_pos, up_v, -8.0)

    aim_forward = addScaled(eye, fwd, 28.0)
    aim_forward = addScaled(aim_forward, right_v, 8.0)
    aim_forward = addScaled(aim_forward, up_v, -6.0)

    t = anim
    gun_pos = [base_pos[0]*(1.0-t) + aim_forward[0]*t,
               base_pos[1]*(1.0-t) + aim_forward[1]*t,
               base_pos[2]*(1.0-t) + aim_forward[2]*t]

    glPushMatrix()
    glTranslatef(gun_pos[0], gun_pos[1], gun_pos[2])

    if anim >= 0.5:
        angle_y = player_yaw
    else:
        angle_y = player_yaw - 90.0*(1.0 - anim*2.0)

    glRotatef(angle_y, 0, 1, 0)
    glColor3f(0.1, 0.2, 0.7)
    drawCuboid(6, 6, 20)
    glPushMatrix()
    glTranslatef(0.0, 0.0, 12.0)
    drawCuboid(4, 4, 20)
    glPopMatrix()

    glPopMatrix()

def playerMuzzleWorld():
    fwd, right_v, up_v = getCameraVectors()
    eye = [player_pos[0], player_pos[1] + eye_height, player_pos[2]]

    aim_forward = addScaled(eye, fwd, 32.0)
    aim_forward = addScaled(aim_forward, right_v, 8.0)
    aim_forward = addScaled(aim_forward, up_v, -6.0)
    return aim_forward, fwd

# -----------------------------
# Spawn / Reset
# -----------------------------
def randomPointInRooms():
    if len(rooms) == 0:
        return [0.0, 0.0, 0.0]
    idx = random.randint(0, len(rooms)-1)
    rx1, rx2, rz1, rz2 = rooms[idx]
    x = random.uniform(rx1+60, rx2-60)
    z = random.uniform(rz1+60, rz2-60)
    return [x, 0.0, z]

def resetGame():
    global player_pos, player_yaw, player_pitch, player_hp
    global enemies, hostages, bullets
    global mag_ammo, reloading, reload_end_time
    global right_mouse_down, left_mouse_down
    global on_ground, player_vel_y
    global game_state

    player_pos = [0.0, 20.0, 0.0]
    player_yaw = 0.0
    player_pitch = 0.0
    player_hp = 100

    on_ground = True
    player_vel_y = 0.0

    mag_ammo = mag_capacity
    reloading = False
    reload_end_time = 0.0

    right_mouse_down = False
    left_mouse_down = False

    enemies = []
    hostages = []
    bullets = []

    i = 0
    while i < enemy_count:
        p = randomPointInRooms()
        epos = [p[0], 0.0, p[2]]
        enemies.append({"pos": epos, "hp": 100, "next_shot": 0.5})
        i = i + 1

    j = 0
    while j < hostage_count:
        p = randomPointInRooms()
        hpos = [p[0], 0.0, p[2]]
        hostages.append({"pos": hpos})
        j = j + 1

    game_state = state_game

# -----------------------------
# Shooting / Bullets
# -----------------------------
def tryPlayerShoot(now):
    global last_player_shot, mag_ammo, reloading, reload_end_time

    if reloading:
        if now >= reload_end_time:
            reloading = False
            mag_ammo = mag_capacity
        else:
            return

    if mag_ammo <= 0:
        reloading = True
        reload_end_time = now + reload_time
        return

    if now - last_player_shot < player_shot_cd:
        return

    muzzle, fwd = playerMuzzleWorld()
    bullets.append({
        "pos": [muzzle[0], muzzle[1], muzzle[2]],
        "dir": vectorNormal([fwd[0], fwd[1], fwd[2]]),
        "speed": player_bullet_speed,
        "from_enemy": False,
        "born_t": now
    })
    last_player_shot = now
    mag_ammo = mag_ammo - 1

def enemyTryShoot(e, now):
    if now < e["next_shot"]:
        return

    to_p = vectorSubtraction([player_pos[0], player_pos[1] + eye_height, player_pos[2]],
                             [e["pos"][0], e["pos"][1] + 60.0, e["pos"][2]])
    dirv = vectorNormal(to_p)

    if enemy_accuracy < 0.999:
        spread = (1.0 - enemy_accuracy) * 0.35
        jitter_x = random.uniform(-spread, spread)
        jitter_y = random.uniform(-spread, spread) * 0.5
        jitter_z = random.uniform(-spread, spread)
        dirv = vectorNormal([dirv[0] + jitter_x, dirv[1] + jitter_y, dirv[2] + jitter_z])

    origin = [e["pos"][0], e["pos"][1] + 60.0, e["pos"][2]]
    bullets.append({
        "pos": origin,
        "dir": dirv,
        "speed": enemy_bullet_speed,
        "from_enemy": True,
        "born_t": now
    })

    e["next_shot"] = now + enemy_fire_cd

# -----------------------------
# Update Logic
# -----------------------------
def updatePlayer(dt):
    global on_ground, player_vel_y

    move_dir = [0.0, 0.0, 0.0]
    forward = angleVector(player_yaw)
    right_v = [forward[2], 0.0, -forward[0]]

    if b'w' in keys or GLUT_KEY_UP in keys:
        move_dir[0] += forward[0]
        move_dir[2] += forward[2]
    if b's' in keys or GLUT_KEY_DOWN in keys:
        move_dir[0] -= forward[0]
        move_dir[2] -= forward[2]
    if b'd' in keys or GLUT_KEY_RIGHT in keys:
        move_dir[0] -= right_v[0]
        move_dir[2] -= right_v[2]
    if b'a' in keys or GLUT_KEY_LEFT in keys:
        move_dir[0] += right_v[0]
        move_dir[2] += right_v[2]

    move_dir = vectorNormal(move_dir)
    player_pos[0] += move_dir[0] * player_speed * dt
    player_pos[2] += move_dir[2] * player_speed * dt

    collideWithWalls(player_pos, 16.0)

    if on_ground:
        if b' ' in keys:
            on_ground = False
            player_vel_y = jump_impulse
    else:
        player_vel_y += gravity * dt
        player_pos[1] += player_vel_y * dt
        if player_pos[1] <= 20.0:
            player_pos[1] = 20.0
            player_vel_y = 0.0
            on_ground = True

def updateEnemies(now, dt):
    i = 0
    while i < len(enemies):
        e = enemies[i]
        to_p = vectorSubtraction([player_pos[0], e["pos"][1], player_pos[2]], e["pos"])
        d = vectorLength(to_p)
        if d > 1e-5:
            v = [to_p[0]/d, 0.0, to_p[2]/d]
            e["pos"][0] += v[0] * enemy_speed * dt
            e["pos"][2] += v[2] * enemy_speed * dt
            collideWithWalls(e["pos"], 16.0)

        enemyTryShoot(e, now)
        i = i + 1

def updateBullets(now, dt):
    global player_hp, game_state

    alive = []
    i = 0
    while i < len(bullets):
        b = bullets[i]
        b["pos"][0] += b["dir"][0] * b["speed"] * dt
        b["pos"][1] += b["dir"][1] * b["speed"] * dt
        b["pos"][2] += b["dir"][2] * b["speed"] * dt

        hit = False

        w = 0
        while w < len(walls):
            pos, size = walls[w]
            minx = pos[0]
            maxx = pos[0] + size[0]
            miny = pos[1]
            maxy = pos[1] + size[1]
            minz = pos[2]
            maxz = pos[2] + size[2]
            bx = b["pos"][0]
            by = b["pos"][1]
            bz = b["pos"][2]
            if bx > minx and bx < maxx and by > miny and by < maxy and bz > minz and bz < maxz:
                hit = True
                break
            w = w + 1

        if not hit:
            if b["from_enemy"] == False:
                j = 0
                while j < len(enemies):
                    e = enemies[j]
                    center = [e["pos"][0], e["pos"][1] + 50.0, e["pos"][2]]
                    dist = vectorLength(vectorSubtraction(center, b["pos"]))
                    if dist <= 28.0:
                        e["hp"] -= 10
                        hit = True
                        break
                    j = j + 1

                if not hit:
                    k = 0
                    while k < len(hostages):
                        h = hostages[k]
                        centerh = [h["pos"][0], h["pos"][1] + 50.0, h["pos"][2]]
                        dist = vectorLength(vectorSubtraction(centerh, b["pos"]))
                        if dist <= 28.0:
                            game_state = state_game_over
                            hit = True
                            break
                        k = k + 1
            else:
                center_p = [player_pos[0], player_pos[1] + eye_height, player_pos[2]]
                distp = vectorLength(vectorSubtraction(center_p, b["pos"]))
                if distp <= 24.0:
                    player_hp -= 10
                    hit = True
                    if player_hp <= 0:
                        game_state = state_game_over

        if not hit:
            if now - b["born_t"] < 4.0:
                alive.append(b)

        i = i + 1

    bullets[:] = alive

    enemies[:] = [e for e in enemies if e["hp"] > 0]
    if len(enemies) == 0 and game_state == state_game:
        game_state = state_win

# -----------------------------
# Camera
# -----------------------------
def applyCamera():
    f = player_pos[:]
    f[1] = player_pos[1] + eye_height

    yaw_r = math.radians(player_yaw)
    pitch_r = math.radians(player_pitch)
    fx = math.cos(pitch_r) * math.cos(yaw_r)
    fy = math.sin(pitch_r)
    fz = math.cos(pitch_r) * math.sin(yaw_r)
    look = [f[0] + fx, f[1] + fy, f[2] + fz]
    gluLookAt(f[0], f[1], f[2], look[0], look[1], look[2], 0, 1, 0)

# -----------------------------
# Render
# -----------------------------
def drawHUD():
    drawText2D(12, win_h - 28, f"HP: {player_hp}", GLUT_BITMAP_HELVETICA_18, (1,1,1))
    drawText2D(12, win_h - 52, f"Ammo: {mag_ammo}/{mag_capacity}", GLUT_BITMAP_HELVETICA_18, (1,1,0.6))
    if reloading:
        drawText2D(12, win_h - 76, f"Reloading...", GLUT_BITMAP_HELVETICA_18, (1,0.6,0.2))
    drawText2D(12, win_h - 100, f"Enemies Left: {len(enemies)}", GLUT_BITMAP_HELVETICA_18, (0.8,1,0.8))

def drawBullets():
    i = 0
    while i < len(bullets):
        b = bullets[i]
        glPushMatrix()
        glTranslatef(b["pos"][0], b["pos"][1], b["pos"][2])
        if b["from_enemy"]:
            glColor3f(*enemy_bullet_color)
        else:
            glColor3f(*bullet_color)
        drawSphere(bullet_radius)
        glPopMatrix()
        i = i + 1

def drawGame():
    drawRooms()

    i = 0
    while i < len(enemies):
        drawEnemy(enemies[i])
        i = i + 1

    j = 0
    while j < len(hostages):
        drawHostage(hostages[j])
        j = j + 1

    drawBullets()
    drawGun()
    drawHUD()

# -----------------------------
# Menu
# -----------------------------
def drawMenu():
    glDisable(GL_LIGHTING)
    drawText2D(win_w/2 - 140, win_h - 120, "BACKROOMS FPS", GLUT_BITMAP_HELVETICA_18, (1,1,0.4))
    drawText2D(win_w/2 - 100, win_h - 180, "[ Start Game ]", GLUT_BITMAP_HELVETICA_18, (0.8,1,0.8))
    drawText2D(win_w/2 - 120, win_h - 220, "[ Choose Difficulty ]", GLUT_BITMAP_HELVETICA_18, (0.8,0.9,1.0))
    drawText2D(win_w/2 - 90, win_h - 260, f"Current: {difficulty}", GLUT_BITMAP_HELVETICA_18, (1,0.8,0.5))

    if menu_show_diff:
        drawText2D(win_w/2 - 60, win_h - 320, "Easy", GLUT_BITMAP_HELVETICA_18, (0.7,1,0.7))
        drawText2D(win_w/2 - 60, win_h - 350, "Medium", GLUT_BITMAP_HELVETICA_18, (0.9,0.9,1.0))
        drawText2D(win_w/2 - 60, win_h - 380, "Hard", GLUT_BITMAP_HELVETICA_18, (1.0,0.6,0.6))
    glEnable(GL_LIGHTING)

def drawGameOver():
    glDisable(GL_LIGHTING)
    drawText2D(win_w/2 - 80, win_h/2 + 10, "GAME OVER", GLUT_BITMAP_HELVETICA_18, (1,0.5,0.5))
    drawText2D(win_w/2 - 120, win_h/2 - 20, "Press ENTER to return to menu", GLUT_BITMAP_HELVETICA_18, (1,1,1))
    glEnable(GL_LIGHTING)

def drawWin():
    glDisable(GL_LIGHTING)
    drawText2D(win_w/2 - 60, win_h/2 + 10, "YOU WIN!", GLUT_BITMAP_HELVETICA_18, (0.7,1.0,0.7))
    drawText2D(win_w/2 - 120, win_h/2 - 20, "Press ENTER to return to menu", GLUT_BITMAP_HELVETICA_18, (1,1,1))
    glEnable(GL_LIGHTING)

# -----------------------------
# GLUT Callbacks
# -----------------------------
def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if game_state == state_menu:
        glDisable(GL_DEPTH_TEST)
        drawMenu()
        glEnable(GL_DEPTH_TEST)
    elif game_state == state_game:
        applyCamera()
        drawGame()
    elif game_state == state_game_over:
        glDisable(GL_DEPTH_TEST)
        drawGameOver()
        glEnable(GL_DEPTH_TEST)
    elif game_state == state_win:
        glDisable(GL_DEPTH_TEST)
        drawWin()
        glEnable(GL_DEPTH_TEST)

    glutSwapBuffers()

def reshape(w, h):
    global win_w, win_h, aspect
    win_w = max(1, w)
    win_h = max(1, h)
    aspect = win_w / float(win_h)
    glViewport(0, 0, win_w, win_h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fov_y, aspect, 1.0, 5000.0)
    glMatrixMode(GL_MODELVIEW)

def idle():
    global last_t, fov_y, target_fov, reloading

    now = time.time()
    if last_t is None:
        last_t = now
    dt = now - last_t
    dt = clamp(dt, 0.0, 0.05)
    last_t = now

    if left_mouse_down:
        target_fov = 50.0
    else:
        target_fov = 70.0

    if abs(fov_y - target_fov) > 0.1:
        if fov_y < target_fov:
            fov_y += 120.0 * dt
            if fov_y > target_fov:
                fov_y = target_fov
        else:
            fov_y -= 120.0 * dt
            if fov_y < target_fov:
                fov_y = target_fov

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(fov_y, aspect, 1.0, 5000.0)
        glMatrixMode(GL_MODELVIEW)

    if game_state == state_game:
        updatePlayer(dt)
        updateEnemies(now, dt)
        updateBullets(now, dt)

        if right_mouse_down:
            tryPlayerShoot(now)

        if reloading:
            if now >= reload_end_time:
                reloading = False

    glutPostRedisplay()

def keyboardDown(key, x, y):
    global game_state, menu_show_diff, difficulty
    global reloading, reload_end_time

    if game_state == state_menu:
        if key == b'\r':
            applyDifficulty(difficulty)
            resetGame()
        elif key == b'1':
            difficulty = "Easy"
        elif key == b'2':
            difficulty = "Medium"
        elif key == b'3':
            difficulty = "Hard"
        elif key == b' ':
            menu_show_diff = not menu_show_diff
        elif key == b'\x1b':
            try:
                from OpenGL.GLUT import glutLeaveMainLoop
                glutLeaveMainLoop()
            except Exception:
                import sys
                sys.exit(0)
        return

    if game_state in (state_game_over, state_win):
        if key == b'\r':
            switchToMenu()
        elif key == b'\x1b':
            safeExit()
        return

    keys.add(key)
    if key == b'r':
        if not reloading:
            reloading = True
            reload_end_time = time.time() + reload_time
    elif key == b'\x1b':
        safeExit()

def keyboardUp(key, x, y):
    if key in keys:
        keys.remove(key)

def specialDown(key, x, y):
    keys.add(key)

def specialUp(key, x, y):
    if key in keys:
        keys.remove(key)

def mouseButton(button, state, x, y):
    global right_mouse_down, left_mouse_down, game_state, menu_show_diff, difficulty

    if game_state == state_menu:
        if state == GLUT_DOWN and button == GLUT_LEFT_BUTTON:
            mx = x
            my = win_h - y
            if hitRect(mx, my, win_w/2 - 120, win_h - 190, 240, 28):
                applyDifficulty(difficulty)
                resetGame()
            elif hitRect(mx, my, win_w/2 - 160, win_h - 230, 320, 28):
                menu_show_diff = not menu_show_diff
            elif menu_show_diff:
                if hitRect(mx, my, win_w/2 - 60, win_h - 330, 120, 22):
                    difficulty = "Easy"
                elif hitRect(mx, my, win_w/2 - 60, win_h - 360, 120, 22):
                    difficulty = "Medium"
                elif hitRect(mx, my, win_w/2 - 60, win_h - 390, 120, 22):
                    difficulty = "Hard"
        return

    if game_state != state_game:
        return

    if button == GLUT_RIGHT_BUTTON:
        if state == GLUT_DOWN:
            right_mouse_down = True
            tryPlayerShoot(time.time())
        else:
            right_mouse_down = False
    elif button == GLUT_LEFT_BUTTON:
        if state == GLUT_DOWN:
            left_mouse_down = True
        else:
            left_mouse_down = False

def mouseMove(x, y):
    global mouse_last_x, mouse_last_y, player_yaw, player_pitch

    if mouse_last_x is None:
        mouse_last_x = x
        mouse_last_y = y
        return

    dx = x - mouse_last_x
    dy = y - mouse_last_y
    mouse_last_x = x
    mouse_last_y = y

    if game_state == state_game:
        player_yaw += dx * mouse_sensitivity
        player_pitch -= dy * mouse_sensitivity
        player_pitch = clamp(player_pitch, -85.0, 85.0)

def hitRect(mx, my, rx, ry, rw, rh):
    if mx >= rx and mx <= rx + rw and my >= ry and my <= ry + rh:
        return True
    else:
        return False

def switchToMenu():
    global game_state, menu_show_diff
    game_state = state_menu
    menu_show_diff = False

def safeExit():
    try:
        from OpenGL.GLUT import glutLeaveMainLoop
        glutLeaveMainLoop()
    except Exception:
        import sys
        sys.exit(0)

# -----------------------------
# Init GL
# -----------------------------
def initGL():
    global quadric

    glClearColor(room_tint[0], room_tint[1], room_tint[2], 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION,  (400.0, 800.0, 400.0, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE,   (0.9, 0.9, 0.9, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR,  (0.6, 0.6, 0.6, 1.0))

    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    quadric = gluNewQuadric()
    gluQuadricNormals(quadric, GLU_SMOOTH)

    buildRooms()

# -----------------------------
# Main
# -----------------------------
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(win_w, win_h)
    glutCreateWindow(b"Backrooms FPS - Broski Edition")

    initGL()

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fov_y, aspect, 1.0, 5000.0)
    glMatrixMode(GL_MODELVIEW)

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboardDown)
    glutKeyboardUpFunc(keyboardUp)
    glutSpecialFunc(specialDown)
    glutSpecialUpFunc(specialUp)
    glutMouseFunc(mouseButton)
    glutPassiveMotionFunc(mouseMove)

    glutMainLoop()

if __name__ == "__main__":
    main()
