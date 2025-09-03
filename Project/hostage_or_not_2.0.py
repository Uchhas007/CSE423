from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math, random, time, sys

WINDOW_W, WINDOW_H = 1200, 800
GRID = 1200
WALL_H = 180
FOVY_DEFAULT = 70.0
FOVY_ZOOM = 45.0
MOUSE_SENS = 0.12  
MOUSE_CAPTURE = True

# Player
PLAYER_BASE_SPEED = 220.0
RUN_MULT = 2.6   
CROUCH_MULT = 0.55
PLAYER_RADIUS = 18.0
PLAYER_EYE_HEIGHT = 46.0
PLAYER_EYE_HEIGHT_CROUCH = 22.0
PLAYER_BODY_HEIGHT = 56.0

# Barriers
BARRIER_MIN_H, BARRIER_MAX_H = 44.0, 52.0

# Bullets
BULLET_SPEED = 1200.0
RELOAD_TIME = 0.12  

# Magazine
MAG_SIZE = 6
RELOAD_DURATION = 3.0  
ammo_in_mag = MAG_SIZE
is_reloading = False
reload_timer = 0.0

SPAWN_BOUNDS = GRID - 140
MIN_SPAWN_DIST = 600                
NUM_STATIC_BARRIERS = 14

WIN_RESCUES = 15
PLAYER_MAX_HEALTH = 3


NUM_STATIC_PAIRS = 2

pz = 0.0       
pvz = 0.0      
GRAVITY = -1400.0
JUMP_VEL = 420.0

DIFFICULTIES = {
    'Easy':   {'fire_rate': 1.25, 'acc_err_deg': 10.0, 'move_speed': 95.0,  'enemy_bullet_speed': 720.0, 'mobiles': 1},
    'Medium': {'fire_rate': 0.85, 'acc_err_deg': 6.0,  'move_speed': 120.0, 'enemy_bullet_speed': 850.0, 'mobiles': 2},
    'Hard':   {'fire_rate': 0.58, 'acc_err_deg': 3.5,  'move_speed': 140.0, 'enemy_bullet_speed': 980.0, 'mobiles': 3},
}
selected_difficulty = 'Medium'   
current_difficulty = 'Medium'    

# State
rng = random.Random(20208)
last_time = time.time()
center_x, center_y = WINDOW_W//2, WINDOW_H//2

# Player state
px, py = 0.0, 0.0
pangle_yaw = 0.0   # degrees, around Z
pangle_pitch = 0.0 # degrees, up/down (clamped)
is_crouch = False
shots_cooldown = 0.0
player_health = PLAYER_MAX_HEALTH
rescues = 0
lost = False
won = False
focus_zoom = False

game_started = False

# Bullets
player_bullets = []  # each: {pos:[x,y,z], dir:[dx,dy,dz], alive}
enemy_bullets = []

barriers = []

shooters = []
hostages = []

drops = []
DROP_SPAWN_COOLDOWN = 7.5
drop_timer = 0.0
SLOW_EFFECT_DURATION = 6.0
slow_effect_timer = 0.0
slow_effect_active = False

menu_stars = []
NUM_MENU_STARS = 120

# Utilities

def now():
    return time.time()

def clamp(x, a, b):
    return a if x < a else (b if x > b else x)

def length2(x, y):
    return math.hypot(x, y)

def norm2(x, y):
    L = length2(x, y)
    return (0.0, 0.0) if L == 0 else (x/L, y/L)

def point_in_aabb(x, y, aabb):
    return aabb['minx'] <= x <= aabb['maxx'] and aabb['miny'] <= y <= aabb['maxy']

def circle_aabb_intersect(cx, cy, r, aabb):
    nx = clamp(cx, aabb['minx'], aabb['maxx'])
    ny = clamp(cy, aabb['miny'], aabb['maxy'])
    return length2(cx - nx, cy - ny) <= r

def seg_aabb_intersect(p0, p1, aabb):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1-x0, y1-y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - aabb['minx']), (dx, aabb['maxx'] - x0),
                 (-dy, y0 - aabb['miny']), (dy, aabb['maxy'] - y0)):
        if p == 0:
            if q < 0: return False
        else:
            t = q / p
            if p < 0:
                if t > t1: return False
                if t > t0: t0 = t
            else:
                if t < t0: return False
                if t < t1: t1 = t
    return True


# Draw Text
def draw_text(x, y, s, font=GLUT_BITMAP_HELVETICA_18):
    glRasterPos2f(x, y)
    for ch in s:
        glutBitmapCharacter(font, ord(ch))

def draw_text_hud(x, y, s):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix(); glLoadIdentity()
    draw_text(x, y, s, GLUT_BITMAP_HELVETICA_18)
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

# Environment

def make_barrier(x, y, w, h, bh):
    return {'minx': x - w/2, 'maxx': x + w/2, 'miny': y - h/2, 'maxy': y + h/2, 'h': bh}

def random_barriers():
    global barriers
    barriers = []
    for i in range(NUM_STATIC_BARRIERS):
        w = rng.uniform(80, 180)
        h = rng.uniform(80, 200)
        x = rng.uniform(-SPAWN_BOUNDS+120, SPAWN_BOUNDS-120)
        y = rng.uniform(-SPAWN_BOUNDS+120, SPAWN_BOUNDS-120)
        bh = rng.uniform(BARRIER_MIN_H, BARRIER_MAX_H)
        barriers.append(make_barrier(x, y, w, h, bh))

# Spawn

def far_enough(x, y):
    return length2(x-px, y-py) >= MIN_SPAWN_DIST

def spawn_pair(static=True):
    for i in range(300):
        x = rng.uniform(-SPAWN_BOUNDS, SPAWN_BOUNDS)
        y = rng.uniform(-SPAWN_BOUNDS, SPAWN_BOUNDS)
        if not far_enough(x,y):
            continue
        ok = True
        for b in barriers:
            if circle_aabb_intersect(x, y, 24, b):
                ok = False; break
        if not ok: continue
        ang = rng.uniform(0, 2*math.pi)
        r = rng.uniform(40, 90)
        hx, hy = x + math.cos(ang)*r, y + math.sin(ang)*r
        for b in barriers:
            if circle_aabb_intersect(hx, hy, 20, b):
                ok = False; break
        if not ok: continue
        shooters.append({'pos':[x,y,0.0], 'alive':True, 't_fire': now()+1.0, 'model_phase': rng.random()*10, 'mobile': not static})
        hostages.append({'pos':[hx,hy,0.0], 'alive':True})
        return True
    return False

def spawn_lone_shooter(mobile=True):
    for i in range(300):
        x = rng.uniform(-SPAWN_BOUNDS, SPAWN_BOUNDS)
        y = rng.uniform(-SPAWN_BOUNDS, SPAWN_BOUNDS)
        if not far_enough(x,y):
            continue
        ok = True
        for b in barriers:
            if circle_aabb_intersect(x, y, 24, b): ok=False; break
        if not ok: continue
        shooters.append({'pos':[x,y,0.0], 'alive':True, 't_fire': now()+rng.uniform(0.8,1.6), 'model_phase': rng.random()*10, 'mobile': mobile})
        return True
    return False

def maybe_spawn_drop(dt):
    global drop_timer
    drop_timer -= dt
    if drop_timer > 0: return
    drop_timer = DROP_SPAWN_COOLDOWN + rng.uniform(-2.0, 2.0)
    # choose a random free spot
    for i in range(150):
        x = rng.uniform(-SPAWN_BOUNDS+100, SPAWN_BOUNDS-100)
        y = rng.uniform(-SPAWN_BOUNDS+100, SPAWN_BOUNDS-100)
        if not far_enough(x,y): continue
        ok = True
        for a in barriers:
            if circle_aabb_intersect(x,y,18,a): ok=False; break
        if not ok: continue
        kind = 'health' if rng.random()<0.55 else 'slow'
        drops.append({'pos':[x,y,0.0], 'kind':kind, 'alive':True, 't_expire': now()+22.0})
        return

# Drawing

def draw_crosshair():
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix(); glLoadIdentity()
    glLineWidth(2)
    glColor3f(1,1,1)
    cx, cy = WINDOW_W/2, WINDOW_H/2
    s = 10
    glBegin(GL_LINES)
    glVertex2f(cx - s, cy); glVertex2f(cx - 2, cy)
    glVertex2f(cx + 2, cy); glVertex2f(cx + s, cy)
    glVertex2f(cx, cy - s); glVertex2f(cx, cy - 2)
    glVertex2f(cx, cy + 2); glVertex2f(cx, cy + s)
    glEnd()
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

def draw_floor_and_walls():
    glBegin(GL_QUADS)
    glColor3f(0.9,0.9,0.9)
    glVertex3f(-GRID, GRID, 0); glVertex3f(0, GRID, 0); glVertex3f(0,0,0); glVertex3f(-GRID,0,0)
    glVertex3f(GRID, -GRID, 0); glVertex3f(0, -GRID, 0); glVertex3f(0,0,0); glVertex3f(GRID,0,0)
    glColor3f(0.75,0.6,0.95)
    glVertex3f(-GRID,-GRID,0); glVertex3f(-GRID,0,0); glVertex3f(0,0,0); glVertex3f(0,-GRID,0)
    glVertex3f(GRID, GRID, 0); glVertex3f(GRID,0,0); glVertex3f(0,0,0); glVertex3f(0, GRID,0)
    glEnd()
    glColor3f(0.25,0.25,0.25)
    def wall(x,y,sx,sy):
        glPushMatrix(); glTranslatef(x,y,WALL_H/2); glScalef(sx,sy,WALL_H); glutSolidCube(1.0); glPopMatrix()
    wall(-GRID, 0, 10, GRID*2)
    wall(GRID, 0, 10, GRID*2)
    wall(0, GRID, GRID*2, 10)
    wall(0,-GRID, GRID*2, 10)

def draw_barrier(a):
    glColor3f(0.45,0.45,0.45)
    cx = (a['minx']+a['maxx'])/2; cy = (a['miny']+a['maxy'])/2
    sx = a['maxx']-a['minx']; sy = a['maxy']-a['miny']
    glPushMatrix(); glTranslatef(cx, cy, a['h']/2); glScalef(sx, sy, a['h']); glutSolidCube(1.0); glPopMatrix()

# Models

def cube(x,y,z,sx,sy,sz,color):
    glColor3f(*color)
    glPushMatrix(); glTranslatef(x,y,z); glScalef(sx,sy,sz); glutSolidCube(1.0); glPopMatrix()


def draw_player_viewmodel():
    # Player's gun in first-person view (bigger and clearer)
    glPushMatrix()
    glTranslatef(20, -6, -20)
    glColor3f(0.1, 0.1, 0.1)  # Dark gun color
    # Handle
    glPushMatrix(); glScalef(8, 8, 4); glutSolidCube(1.0); glPopMatrix()
    # Barrel
    glPushMatrix(); glTranslatef(12, 0, 0); glScalef(24, 4, 4); glutSolidCube(1.0); glPopMatrix()
    # Muzzle
    glPushMatrix(); glTranslatef(24, 0, 0); glScalef(6, 3, 3); glutSolidCube(1.0); glPopMatrix()
    glPopMatrix()

def draw_shooter(sh):
    x,y,_ = sh['pos']
    t = now() + sh['model_phase']
    bob = (math.sin(t*3.0)*0.5+0.5)
    cube(x, y-5, 18, 10, 6, 36, (0.2,0.2,0.8))
    cube(x, y+5, 18, 10, 6, 36, (0.2,0.2,0.8))
    cube(x, y, 42+bob*2, 18, 12, 28, (0.1,0.6,0.2))
    cube(x, y, 60+bob*2, 12, 10, 12, (0.95,0.88,0.78))

def draw_hostage(ho):
    x,y,_ = ho['pos']
    cube(x, y, 32, 16, 12, 24, (0.85,0.15,0.15))
    cube(x, y, 50, 10, 10, 10, (0.98,0.92,0.86))

def draw_bullet(b, enemy=False):
    x,y,z = b['pos']
    if enemy:
        glColor3f(1.0,0.6,0.2)
    else:
        glColor3f(1.0,0.9,0.1)
    glPushMatrix(); glTranslatef(x,y,z); glScalef(6,6,6); glutSolidCube(1.0); glPopMatrix()

def draw_drop(d):
    x,y,_ = d['pos']
    if d['kind'] == 'health':
        col = (0.2, 0.9, 0.25)
        h = 18
    else:
        col = (0.2, 0.7, 1.0)
        h = 14
    cube(x, y, h, 12, 12, h, col)

# Camera Setup

def camera_pos_and_dir():
    eye_z = (PLAYER_EYE_HEIGHT_CROUCH if is_crouch else PLAYER_EYE_HEIGHT) + pz
    yaw_r = math.radians(pangle_yaw)
    pit_r = math.radians(pangle_pitch)
    dx = math.cos(yaw_r)*math.cos(pit_r)
    dy = math.sin(yaw_r)*math.cos(pit_r)
    dz = math.sin(pit_r)
    return (px, py, eye_z), (dx, dy, dz)

def setup_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    fovy = FOVY_ZOOM if focus_zoom else FOVY_DEFAULT
    aspect = float(WINDOW_W)/float(WINDOW_H)
    gluPerspective(fovy, aspect, 0.1, 4000.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    if not game_started:
        # menu spectator camera
        gluLookAt(0, -1000, 520, 0, 0, 0, 0, 0, 1)
    else:
        (cx,cy,cz),(dx,dy,dz) = camera_pos_and_dir()
        gluLookAt(cx,cy,cz, cx+dx*10, cy+dy*10, cz+dz*10, 0,0,1)

# Game Mechanics

def try_move(nx, ny):
    nx = clamp(nx, -GRID+20, GRID-20)
    ny = clamp(ny, -GRID+20, GRID-20)
    for a in barriers:
        if circle_aabb_intersect(nx, ny, PLAYER_RADIUS, a):
            return False
    global px, py
    px, py = nx, ny
    return True

def begin_reload():
    global is_reloading, reload_timer
    if is_reloading: return
    if ammo_in_mag == MAG_SIZE: return
    is_reloading = True
    reload_timer = RELOAD_DURATION

def finish_reload():
    global ammo_in_mag, is_reloading, reload_timer
    ammo_in_mag = MAG_SIZE
    is_reloading = False
    reload_timer = 0.0

def fire_player_bullet():
    global shots_cooldown, ammo_in_mag
    if not game_started or won or lost: return
    if is_reloading: return
    if shots_cooldown > 0: return
    if ammo_in_mag <= 0:
        begin_reload()
        return
    (cx,cy,cz),(dx,dy,dz) = camera_pos_and_dir()
    start = [cx + dx*24, cy + dy*24, cz + dz*4]
    player_bullets.append({'pos': start[:], 'dir':[dx,dy,dz], 'alive':True})
    shots_cooldown = RELOAD_TIME
    ammo_in_mag -= 1
    if ammo_in_mag == 0:
        begin_reload()

def enemy_los_blocked(sx, sy):
    (cx,cy,cz),(dx,dy,dz) = camera_pos_and_dir()
    for a in barriers:
        if seg_aabb_intersect((sx, sy), (cx, cy), a):
            if (PLAYER_EYE_HEIGHT_CROUCH if is_crouch else PLAYER_EYE_HEIGHT) + pz < a['h']:
                return True
    return False

def fire_enemy(sh):
    if not game_started: return
    (cx,cy,cz),(pdx,pdy,pdz) = camera_pos_and_dir()
    sx, sy, _ = sh['pos']
    if enemy_los_blocked(sx, sy):
        return
    dirx, diry = (cx - sx, cy - sy)
    L = math.hypot(dirx, diry)
    if L < 1e-5: return
    dirx, diry = dirx/L, diry/L
    acc_err = DIFFICULTIES[current_difficulty]['acc_err_deg']
    err = math.radians(rng.uniform(-acc_err, acc_err))
    c, s = math.cos(err), math.sin(err)
    ex, ey = dirx*c - diry*s, dirx*s + diry*c
    enemy_bullets.append({'pos':[sx,sy, (PLAYER_EYE_HEIGHT_CROUCH if is_crouch else PLAYER_EYE_HEIGHT)+pz], 'dir':[ex,ey,0.0], 'alive':True})

def move_shooters(dt):
    ms = DIFFICULTIES[current_difficulty]['move_speed']
    for sh in shooters:
        if not sh['alive']: continue
        if sh['mobile']:
            dx, dy = px - sh['pos'][0], py - sh['pos'][1]
            dist = math.hypot(dx, dy)
            if dist > 1e-4:
                ndx, ndy = dx/dist, dy/dist
            else:
                ndx, ndy = 0.0, 0.0
            jx = rng.uniform(-0.5,0.5)
            jy = rng.uniform(-0.5,0.5)
            vx, vy = (ndx*ms + jx*35, ndy*ms + jy*35)
            nx = sh['pos'][0] + vx*dt
            ny = sh['pos'][1] + vy*dt
            blocked = False
            for a in barriers:
                if circle_aabb_intersect(nx, ny, 16.0, a):
                    blocked = True; break
            if not blocked and abs(nx) < GRID-20 and abs(ny) < GRID-20:
                sh['pos'][0], sh['pos'][1] = nx, ny
        if now() >= sh['t_fire']:
            # slow effect increases time between shots on the fly
            base = DIFFICULTIES[current_difficulty]['fire_rate']
            if slow_effect_active:
                base *= 3.2
            sh['t_fire'] = now() + base
            fire_enemy(sh)

def update_bullets(dt):
    global lost, player_health
    # player bullets
    for b in player_bullets:
        if not b['alive']: continue
        old = b['pos'][:]
        b['pos'][0] += b['dir'][0]*BULLET_SPEED*dt
        b['pos'][1] += b['dir'][1]*BULLET_SPEED*dt
        b['pos'][2] += b['dir'][2]*BULLET_SPEED*dt
        if abs(b['pos'][0])>GRID or abs(b['pos'][1])>GRID:
            b['alive']=False; continue
        for a in barriers:
            if seg_aabb_intersect((old[0], old[1]), (b['pos'][0], b['pos'][1]), a):
                b['alive']=False; break
        if not b['alive']: continue
        for sh in shooters:
            if not sh['alive']: continue
            if length2(b['pos'][0]-sh['pos'][0], b['pos'][1]-sh['pos'][1]) < 18.0:
                sh['alive']=False; b['alive']=False; break
        if not b['alive']: continue
        for ho in hostages:
            if not ho['alive']: continue
            if length2(b['pos'][0]-ho['pos'][0], b['pos'][1]-ho['pos'][1]) < 16.0:
                ho['alive']=False; b['alive']=False; lost=True; break

    # enemy bullets 
    base_speed = DIFFICULTIES[current_difficulty]['enemy_bullet_speed']
    eb_speed = base_speed * (0.33 if slow_effect_active else 1.0)
    for b in enemy_bullets:
        if not b['alive']: continue
        old = b['pos'][:]
        b['pos'][0] += b['dir'][0]*eb_speed*dt
        b['pos'][1] += b['dir'][1]*eb_speed*dt
        for a in barriers:
            if seg_aabb_intersect((old[0], old[1]), (b['pos'][0], b['pos'][1]), a):
                b['alive']=False; break
        if not b['alive']: continue
        if length2(b['pos'][0]-px, b['pos'][1]-py) < PLAYER_RADIUS*0.9:
            player_health -= 1
            b['alive']=False

    player_bullets[:] = [b for b in player_bullets if b['alive']]
    enemy_bullets[:]  = [b for b in enemy_bullets if b['alive']]

def rescue_check():
    global rescues, won
    for ho in hostages:
        if not ho['alive']: continue
        if length2(ho['pos'][0]-px, ho['pos'][1]-py) < 20.0:
            ho['alive'] = False
            rescues += 1
            if rescues >= WIN_RESCUES:
                won = True

def maintain_exact_counts():
    alive_hostages = [h for h in hostages if h['alive']]
    alive_static_shooters = [s for s in shooters if s['alive'] and not s['mobile']]
    alive_mobile_shooters = [s for s in shooters if s['alive'] and s['mobile']]
    # Two pairs of Shooter-Hostage
    while len(alive_hostages) < NUM_STATIC_PAIRS:
        if spawn_pair(static=True):
            alive_hostages = [h for h in hostages if h['alive']]
        else:
            break
    # Mobile Enemies
    target_mobiles = DIFFICULTIES[current_difficulty]['mobiles']
    while len(alive_mobile_shooters) < target_mobiles:
        if spawn_lone_shooter(mobile=True):
            alive_mobile_shooters = [s for s in shooters if s['alive'] and s['mobile']]
        else:
            break

def update_drops_and_effects(dt):
    global slow_effect_timer, slow_effect_active, player_health
    # expire drops
    for d in drops:
        if not d['alive']: continue
        if now() >= d['t_expire']:
            d['alive'] = False
    # pickup
    for d in drops:
        if not d['alive']: continue
        if length2(d['pos'][0]-px, d['pos'][1]-py) < 18.0:
            d['alive'] = False
            if d['kind'] == 'health':
                if player_health < PLAYER_MAX_HEALTH:
                    player_health += 1
            else:
                slow_effect_active = True
                slow_effect_timer = SLOW_EFFECT_DURATION
    # effect timer
    if slow_effect_active:
        slow_effect_timer -= dt
        if slow_effect_timer <= 0.0:
            slow_effect_active = False
            slow_effect_timer = 0.0
    # purge
    drops[:] = [d for d in drops if d['alive']]

# Control Settings

keys_down = set()

def key_down(k, x, y):
    global is_crouch, selected_difficulty, current_difficulty
    global focus_zoom, game_started
    global pz, pvz

    if k == b'\x1b':  # Escape key
        try:
            glutLeaveMainLoop()
        except:
            import os
            os._exit(0)

    # Menu: difficulty selection and start
    if not game_started:
        if k in (b'1', b'2', b'3'):
            selected_difficulty = {
                b'1': 'Easy',
                b'2': 'Medium',
                b'3': 'Hard'
            }[k]
        elif k in (b'\r', b'\n'):  # Enter / Return key
            if selected_difficulty:
                current_difficulty = selected_difficulty
                game_started = True
                restart_game()
                # center mouse
                if MOUSE_CAPTURE:
                    glutWarpPointer(center_x, center_y)
        return

    # In game keys
    if k in (b'w', b'W', b's', b'S', b'a', b'A', b'd', b'D'):
        keys_down.add(k.lower())
    elif k == b'	':  # TAB
        is_crouch = not is_crouch
    elif k in (b'r', b'R'):
        begin_reload()
    elif k in (b'f', b'F'): 
        restart_game()
    elif k == b' ':
        if pz <= 0.001:
            pvz = JUMP_VEL

def key_up(k, x, y):
    if not game_started:
        return
    if k in (b'w', b'W', b's', b'S', b'a', b'A', b'd', b'D'):
        keys_down.discard(k.lower())

def special_down(k, x, y):
    pass

def mouse_button(btn, state, x, y):
    global focus_zoom
    if btn == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_player_bullet()
    elif btn == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        focus_zoom = not focus_zoom

def passive_motion(x, y):
    global pangle_yaw, pangle_pitch
    if not MOUSE_CAPTURE or not game_started: return
    dx = x - center_x
    dy = y - center_y
    if dx == 0 and dy == 0: 
        return
    pangle_yaw -= dx * MOUSE_SENS
    pangle_pitch -= dy * MOUSE_SENS
    pangle_pitch = clamp(pangle_pitch, -70.0, 70.0)
    glutWarpPointer(center_x, center_y)

# Game Loop

def apply_movement(dt):
    spd = PLAYER_BASE_SPEED
    if glutGetModifiers() & GLUT_ACTIVE_SHIFT:
        spd *= RUN_MULT + 1.3
    if is_crouch:
        spd *= CROUCH_MULT
    vx = vy = 0.0
    def isdown(ch):
        return ch.encode() in keys_down
    yaw = math.radians(pangle_yaw)
    fx, fy = math.cos(yaw), math.sin(yaw)
    rx, ry = -math.sin(yaw), math.cos(yaw)
    if isdown('w'): vx += fx; vy += fy
    if isdown('s'): vx -= fx; vy -= fy
    if isdown('a'): vx += rx; vy += ry
    if isdown('d'): vx -= rx; vy -= ry
    L = math.hypot(vx, vy)
    if L > 0:
        vx, vy = vx/L, vy/L
        try_move(px + vx*spd*dt, py + vy*spd*dt)

def apply_jump(dt):
    global pz, pvz
    pvz += GRAVITY * dt
    pz += pvz * dt
    if pz < 0:
        pz = 0.0; pvz = 0.0

def update(dt):
    global shots_cooldown, lost, reload_timer, is_reloading
    if not game_started:
        return
    if won or lost: return
    if shots_cooldown > 0: 
        shots_cooldown -= dt
    apply_movement(dt)
    apply_jump(dt)
    move_shooters(dt)
    update_bullets(dt)
    rescue_check()
    if player_health <= 0:
        lost = True
    maintain_exact_counts()
    # drops
    maybe_spawn_drop(dt)
    update_drops_and_effects(dt)
    # reload logic
    if is_reloading:
        reload_timer -= dt
        if reload_timer <= 0.0:
            finish_reload()

# Minimap

def draw_minimap():
    glDisable(GL_DEPTH_TEST)
    map_w, map_h = 220, 220
    margin = 16
    x0 = WINDOW_W - map_w - margin
    y0 = WINDOW_H - map_h - margin

    def world_to_map(wx, wy):
        mx = (wx + GRID) / (2*GRID)
        my = (wy + GRID) / (2*GRID)
        return x0 + mx*map_w, y0 + my*map_h

    glMatrixMode(GL_PROJECTION)
    glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix(); glLoadIdentity()

    # panel
    glColor3f(0.05,0.05,0.05)
    glBegin(GL_QUADS)
    glVertex2f(x0-2, y0-2); glVertex2f(x0+map_w+2, y0-2); glVertex2f(x0+map_w+2, y0+map_h+2); glVertex2f(x0-2, y0+map_h+2)
    glEnd()
    glColor3f(0.15,0.15,0.15)
    glBegin(GL_QUADS)
    glVertex2f(x0, y0); glVertex2f(x0+map_w, y0); glVertex2f(x0+map_w, y0+map_h); glVertex2f(x0, y0+map_h)
    glEnd()

    # barriers as white blocks
    glColor3f(1.0,1.0,1.0)
    for a in barriers:
        mx1, my1 = world_to_map(a['minx'], a['miny'])
        mx2, my2 = world_to_map(a['maxx'], a['maxy'])
        glBegin(GL_QUADS)
        glVertex2f(mx1, my1); glVertex2f(mx2, my1); glVertex2f(mx2, my2); glVertex2f(mx1, my2)
        glEnd()

    # dots
    glPointSize(6)
    glBegin(GL_POINTS)
    glColor3f(1.0, 0.95, 0.0)
    mx, my = world_to_map(px, py)
    glVertex2f(mx, my)
    glColor3f(1.0, 0.2, 0.2)
    for sh in shooters:
        if sh['alive']:
            mx, my = world_to_map(sh['pos'][0], sh['pos'][1])
            glVertex2f(mx, my)
    glColor3f(0.2, 0.6, 1.0)
    for ho in hostages:
        if ho['alive']:
            mx, my = world_to_map(ho['pos'][0], ho['pos'][1])
            glVertex2f(mx, my)
    # drops
    glColor3f(0.4, 1.0, 0.6)
    for d in drops:
        if d['alive']:
            mx, my = world_to_map(d['pos'][0], d['pos'][1])
            glVertex2f(mx, my)
    glEnd()

    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

# Menu

def init_menu_stars():
    global menu_stars
    menu_stars = []
    for i in range(NUM_MENU_STARS):
        x = rng.uniform(0, WINDOW_W)
        y = rng.uniform(0, WINDOW_H)
        s = rng.uniform(0.6, 2.0)
        spd = rng.uniform(40, 120)
        menu_stars.append({'x':x, 'y':y, 's':s, 'spd':spd})

def update_menu_stars(dt):
    for st in menu_stars:
        st['y'] -= st['spd'] * dt
        if st['y'] < -4:
            st['y'] = WINDOW_H + rng.uniform(0, 60)
            st['x'] = rng.uniform(0, WINDOW_W)

def draw_menu_stars():
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix(); glLoadIdentity()
    glBegin(GL_QUADS)
    for st in menu_stars:
        x = st['x']; y = st['y']; s = st['s']
        glColor3f(1.0, 1.0, 1.0)
        glVertex2f(x-s, y-s); glVertex2f(x+s, y-s); glVertex2f(x+s, y+s); glVertex2f(x-s, y+s)
    glEnd()
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

# Render Screen

def display_menu_overlay():
    # stars
    draw_menu_stars()

    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix(); glLoadIdentity()

    # Dark overlay
    glColor4f(0.0, 0.0, 0.0, 0.65)
    glBegin(GL_QUADS)
    glVertex2f(0, 0); glVertex2f(WINDOW_W, 0)
    glVertex2f(WINDOW_W, WINDOW_H); glVertex2f(0, WINDOW_H)
    glEnd()

    # Title
    glColor3f(1.0, 0.85, 0.2)
    draw_text(WINDOW_W//2 - 180, WINDOW_H//2 + 180, "HOSTAGE OR NOT", GLUT_BITMAP_TIMES_ROMAN_24)
    glColor3f(1.0, 1.0, 1.0)
    draw_text(WINDOW_W//2 - 120, WINDOW_H//2 + 140, "Group 9 Project", GLUT_BITMAP_HELVETICA_18)

    # Difficulty options
    options = ["Easy", "Medium", "Hard"]
    y_start = WINDOW_H//2 + 60
    for i, opt in enumerate(options):
        color = (1.0, 0.3, 0.3) if opt == selected_difficulty else (0.8, 0.8, 0.8)
        glColor3f(*color)
        draw_text(WINDOW_W//2 - 80, y_start - i*40, f"[{i+1}] {opt}", GLUT_BITMAP_HELVETICA_18)

    # Instructions
    glColor3f(0.8, 0.9, 1.0)
    draw_text(WINDOW_W//2 - 220, WINDOW_H//2 - 120, "Press ENTER to Start — Difficulty locks on start", GLUT_BITMAP_HELVETICA_18)
    draw_text(WINDOW_W//2 - 220, WINDOW_H//2 - 160, "Controls: WASD move, SHIFT sprint, TAB crouch, Space jump", GLUT_BITMAP_HELVETICA_18)
    draw_text(WINDOW_W//2 - 220, WINDOW_H//2 - 200, "Mouse1 shoot, Mouse2 focus, R reload, F restart, ESC quit", GLUT_BITMAP_HELVETICA_18)

    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    setup_camera()

    # World
    draw_floor_and_walls()
    for a in barriers: draw_barrier(a)

    # Actors & bullets
    for ho in hostages:
        if ho['alive']: draw_hostage(ho)
    for sh in shooters:
        if sh['alive']: draw_shooter(sh)
    for b in player_bullets: draw_bullet(b, enemy=False)
    for b in enemy_bullets: draw_bullet(b, enemy=True)
    for d in drops:
        if d['alive']: draw_drop(d)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    draw_player_viewmodel()
    glPopMatrix()

    # HUD
    draw_crosshair()
    glDisable(GL_DEPTH_TEST)
    ammo_text = f"Ammo: {ammo_in_mag}/{MAG_SIZE}"
    if is_reloading:
        ammo_text += "  [RELOADING...]"
    status = f"Health: {player_health}/{PLAYER_MAX_HEALTH}  Rescues: {rescues}/{WIN_RESCUES}  Difficulty: {current_difficulty if game_started else '---'}"
    draw_text_hud(10, WINDOW_H-24, status)
    draw_text_hud(10, WINDOW_H-48, ammo_text)
    draw_text_hud(10, 10, "F: Reload  |  F: Restart  |  ESC/Q: Quit")
    if not game_started:
        display_menu_overlay()
    if won:
        draw_text_hud(WINDOW_W/2 - 70, WINDOW_H/2 + 20, "MISSION COMPLETE!")
        draw_text_hud(WINDOW_W/2 - 140, WINDOW_H/2 - 4, "You rescued 15 hostages. Press F to restart")
    if lost:
        draw_text_hud(WINDOW_W/2 - 40, WINDOW_H/2 + 20, "MISSION FAILED")
        draw_text_hud(WINDOW_W/2 - 260, WINDOW_H/2 - 4, "A hostage died or you were eliminated. Press F to restart or ESC to quit")
    glEnable(GL_DEPTH_TEST)

    draw_minimap()

    glutSwapBuffers()

def idle():
    global last_time
    t = now(); dt = t - last_time
    if dt > 0.05: dt = 0.05
    last_time = t
    if not game_started:
        update_menu_stars(dt)
    update(dt)
    glutPostRedisplay()


def is_valid_player_pos(x, y):
    if abs(x) > GRID-20 or abs(y) > GRID-20: return False
    for a in barriers:
        if circle_aabb_intersect(x, y, PLAYER_RADIUS+2, a): return False
    return True

def find_valid_player_spawn():
    if is_valid_player_pos(0.0, 0.0): return 0.0, 0.0
    steps = 30
    rad_step = 24
    for r in range(24, 900, rad_step):
        for angdeg in range(0, 360, 15):
            rad = math.radians(angdeg)
            x = math.cos(rad)*r
            y = math.sin(rad)*r
            if is_valid_player_pos(x, y):
                return x, y
    for i in range(500):
        x = rng.uniform(-220, 220); y = rng.uniform(-220, 220)
        if is_valid_player_pos(x, y): return x, y
    return 0.0, 0.0

# Game Initialization

def restart_game():
    global px, py, pangle_yaw, pangle_pitch, is_crouch, shots_cooldown
    global player_health, rescues, lost, won, focus_zoom, pz, pvz
    global shooters, hostages, player_bullets, enemy_bullets, drops
    global ammo_in_mag, is_reloading, reload_timer, drop_timer
    pz = 0.0; pvz = 0.0
    pangle_yaw = 0.0; pangle_pitch = 0.0
    is_crouch = False; shots_cooldown = 0.0
    player_health = PLAYER_MAX_HEALTH
    rescues = 0
    lost = False; won = False
    focus_zoom = False
    shooters = []; hostages = []
    player_bullets = []; enemy_bullets = []
    drops = []; drop_timer = rng.uniform(2.0, 4.0)
    ammo_in_mag = MAG_SIZE; is_reloading = False; reload_timer = 0.0
    random_barriers()

    sx, sy = find_valid_player_spawn()
    px, py = sx, sy

    for i in range(NUM_STATIC_PAIRS): spawn_pair(static=True)
    for i in range(DIFFICULTIES[current_difficulty]['mobiles']): spawn_lone_shooter(mobile=True)

def init_gl():
    glClearColor(0,0,0,1)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    init_menu_stars()

def reshape(w, h):
    global WINDOW_W, WINDOW_H, center_x, center_y
    WINDOW_W, WINDOW_H = max(1,w), max(1,h)
    center_x, center_y = WINDOW_W//2, WINDOW_H//2
    glViewport(0,0,WINDOW_W,WINDOW_H)

def start_projection():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutCreateWindow(b"Hostage or Not")
    init_gl()

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(key_down)
    glutKeyboardUpFunc(key_up)
    glutSpecialFunc(special_down)
    glutMouseFunc(mouse_button)
    glutPassiveMotionFunc(passive_motion)
    glutIdleFunc(idle)

    if MOUSE_CAPTURE:
        glutWarpPointer(center_x, center_y)

    glutMainLoop()

start_projection()