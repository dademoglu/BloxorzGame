import sys
from random import random
import queue
import glm
import numpy as np
from OpenGL import GL as gl, GLUT as glut
from IOUtilities import *
from GameUtilities import *
from StandardShader import *
from UnlitBlendShader import *
from AABBShader import *
import time
import random
from copy import deepcopy

# Initialize GLUT ------------------------------------------------------------------|

glut.glutInit()
glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGBA | glut.GLUT_MULTISAMPLE)

# Create a window
screen_size = glm.vec2(512, 512)
glut.glutCreateWindow("Bloxorz")
glut.glutReshapeWindow(int(screen_size.x), int(screen_size.y))
gl.glClearColor(0.2, 0.2, 0.2, 0)
# Configure GL -----------------------------------------------------------------------|
gl.glEnable(gl.GL_MULTISAMPLE)
# Enable depth test
gl.glEnable(gl.GL_DEPTH_TEST)
# Accept fragment if it closer to the camera than the former one
gl.glDepthFunc(gl.GL_LESS)

# This command is necessary in our case to load different type of image formats.
# Read more on https://www.khronos.org/opengl/wiki/Common_Mistakes under "Texture upload and pixel reads"
gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)

# Creating Data Buffers -----------------------------------------------------------|

# With the ability of .obj file loading, all the data will be read from the files and bound to proper buffers
primitive_objs = {
    "tiles": parse_and_bind_obj_file("Assets/Primitives/tiles.obj"),
    "cube": parse_and_bind_obj_file("Assets/Primitives/cube.obj"),
    "aabb": parse_and_bind_obj_file("Assets/Primitives/aabb.obj"),
    "plane": parse_and_bind_obj_file("Assets/Primitives/plane.obj"),
    "rectangular": parse_and_bind_obj_file("Assets/rectangular.obj")
}

collisionCounter = 0
# Create Shaders ---------------------------------------------------------------------|

standard_shader = StandardShader()
light_position = glm.vec3(0.0, 5.0, 10.0)

AABB_shader = AABBShader(deepcopy(primitive_objs["aabb"]))

UI_shader = UnlitBlendShader()

# Create Camera and Game Objects -----------------------------------------------------|

perspective_projection = glm.perspective(glm.radians(45.0), screen_size.x / screen_size.y, 0.1, 100.0)
orthogonal_projection = glm.ortho(-10.0, 10.0, -10.0, 10.0)

camera = Camera(
    Transform(
        position=glm.vec3(4.0, 10.0, 12.0),
    ),
    target=glm.vec3(2, 0.1, 0.2)
)

# Create an obj for the obstacles
cube_obj = deepcopy(primitive_objs["cube"])
texture = load_image_to_texture("Assets/Textures/cube1.png")
cube_obj.meshes[0].material.map_Ka = texture
cube_obj.meshes[0].material.map_Kd = texture

tiles_obj = deepcopy(primitive_objs["tiles"])

hearts: GameObjectSet = set()
hearts_parent = GameObject(
    Transform(
        position=glm.vec3(0.0, 5.0, 0.0),
    )
)

hearth_obj = deepcopy(primitive_objs["plane"])
hearth_obj.meshes[0].material.Kd = glm.vec3(0.0)
hearth_obj.meshes[0].material.Tr = 0.0
hearth_obj.meshes[0].material.map_Kd = load_image_to_texture("Assets/Textures/heart.png")

heart_remove_order = queue.Queue()


def createHearts():
    for i in range(3):
        heart = GameObject(
            Transform(
                position=glm.vec3(-8.0, -4.0 + i * 3.0, 0.0),
                parent=hearts_parent.transform,
            ),
            obj_data=hearth_obj,
        )
        heart.leave_set(GameObject.WithObjData)
        heart.join_set(hearts)
        heart_remove_order.put(heart)


createHearts()

t1 = load_image_to_texture("Assets/Textures/Xed1.png")
t2 = load_image_to_texture("Assets/Textures/Xed2.png")


# closedButton= load_image_to_texture("Assets/Textures/closedbutton.png")
# openButton = load_image_to_texture("Assets/Textures/openbutton.png")
# openTeleport = load_image_to_texture("Assets/Textures/openportal.png")
# closedTeleport = load_image_to_texture("Assets/Textures/closedportal.png")
# laserButton = load_image_to_texture("Assets/Textures/laser.png")
# finish = load_image_to_texture("Assets/Textures/win.png")


# Create above and below obstacles
def randomTexture():
    randomNumber = random.randrange(1, 3, 1)
    if randomNumber == 2:
        return t1
    else:
        return t2


playground: GameObjectSet = set()
playground_parents: GameObjectSet = set()

parent_point = GameObject(
    Transform(
        position=glm.vec3(0.0, 0.0, 0.0)
    )
)
parent_point.join_set(playground_parents)

cube = GameObject(
    Transform(
        position=glm.vec3(0, -0.01, 0.0),
        scale=glm.vec3(0.5, 1, 0.5),
        parent=parent_point.transform,
    ),
    obj_data=cube_obj,
    aabb=ReactiveAABB.copy_from(cube_obj.AABB)
)

tilesList = []
winningTile = []
openTeleport = []
fromTeleport = []
toTeleport = []
closeLaser = []


def clearPlayground():
    playground: GameObjectSet = set()


def makeThemCool(tile):
    texture = randomTexture()
    tiles_obj.meshes[0].material.map_Kd = texture
    tiles_obj.meshes[0].material.map_Ka = texture
    tile.join_set(playground)
    tilesList.append(tile)


def createPlayground():
    clearPlayground()

    i = 0
    xValue = 0
    yValue = -1
    zValue = 0
    # win tiles
    # XZ Tiles
    toTeleportTile = GameObject(
        Transform(
            position=glm.vec3(xValue, yValue, zValue - 1),
            scale=glm.vec3(0.5),
            parent=parent_point.transform,
        ),
        deepcopy(tiles_obj),
        ReactiveAABB.copy_from(tiles_obj.AABB)
    )
    makeThemCool(toTeleportTile)
    toTeleport.append(toTeleportTile)

    tile = GameObject(
        Transform(
            position=glm.vec3(xValue, yValue, zValue + 1),
            scale=glm.vec3(0.5),
            parent=parent_point.transform,
        ),
        deepcopy(tiles_obj),
        ReactiveAABB.copy_from(tiles_obj.AABB)
    )
    makeThemCool(tile)

    winTile = GameObject(
        Transform(
            position=glm.vec3(xValue, yValue, zValue + 2),
            scale=glm.vec3(0.5),
            parent=parent_point.transform,
        ),
        deepcopy(tiles_obj),
        ReactiveAABB.copy_from(tiles_obj.AABB)
    )
    winningTile.append(winTile)
    makeThemCool(winTile)

    # XZ Tiles
    while i < 2:
        tile = GameObject(
            Transform(
                position=glm.vec3(xValue, yValue, zValue),
                scale=glm.vec3(0.5),
                parent=parent_point.transform,
            ),
            deepcopy(tiles_obj),
            ReactiveAABB.copy_from(tiles_obj.AABB)
        )
        xValue += 1
        i += 1
        makeThemCool(tile)

    while 2 <= i < 6:
        tile = GameObject(
            Transform(
                position=glm.vec3(xValue, yValue, zValue),
                scale=glm.vec3(0.5),
                parent=parent_point.transform,
            ),
            deepcopy(tiles_obj),
            ReactiveAABB.copy_from(tiles_obj.AABB)
        )
        zValue -= 1
        i += 1
        makeThemCool(tile)

    xValue += 1
    zValue += 4

    while 5 < i < 10:
        tile = GameObject(
            Transform(
                position=glm.vec3(xValue, yValue, zValue),
                scale=glm.vec3(0.5),
                parent=parent_point.transform,
            ),
            deepcopy(tiles_obj),
            ReactiveAABB.copy_from(tiles_obj.AABB)
        )
        zValue -= 1
        i += 1
        makeThemCool(tile)

    while 9 < i < 13:
        tile = GameObject(
            Transform(
                position=glm.vec3(xValue, yValue, zValue),
                scale=glm.vec3(0.5),
                parent=parent_point.transform,
            ),
            deepcopy(tiles_obj),
            ReactiveAABB.copy_from(tiles_obj.AABB)
        )
        xValue += 1
        i += 1
        makeThemCool(tile)

    tile = GameObject(
        Transform(
            position=glm.vec3(xValue - 2, yValue, zValue + 1),
            scale=glm.vec3(0.5),
            parent=parent_point.transform,
        ),
        deepcopy(tiles_obj),
        ReactiveAABB.copy_from(tiles_obj.AABB)
    )
    makeThemCool(tile)

    # Upper Playground
    i = 0

    while i < 3:
        tile = GameObject(
            Transform(
                position=glm.vec3(xValue - 0.5, yValue + 0.5, zValue),
                scale=glm.vec3(0.5),
                parent=parent_point.transform,
                rotation=glm.quat(glm.vec3(0, 0, glm.radians(90)))
            ),
            deepcopy(tiles_obj),
            ReactiveAABB.copy_from(tiles_obj.AABB)
        )
        yValue += 1
        makeThemCool(tile)
        i += 1

    yValue -= 1
    oldZ = zValue
    while 2 < i < 7:
        tile = GameObject(
            Transform(
                position=glm.vec3(xValue - 0.5, yValue + 0.5, zValue + 1),
                scale=glm.vec3(0.5),
                parent=parent_point.transform,
                rotation=glm.quat(glm.vec3(0, 0, glm.radians(90)))
            ),
            deepcopy(tiles_obj),
            ReactiveAABB.copy_from(tiles_obj.AABB)
        )
        zValue += 1
        makeThemCool(tile)
        i += 1

    zValue = oldZ
    while 6 < i < 12:
        tile = GameObject(
            Transform(
                position=glm.vec3(xValue - 0.5, yValue + 1.5, zValue),
                scale=glm.vec3(0.5),
                parent=parent_point.transform,
                rotation=glm.quat(glm.vec3(0, 0, glm.radians(90)))
            ),
            deepcopy(tiles_obj),
            ReactiveAABB.copy_from(tiles_obj.AABB)
        )
        zValue += 1
        if i == 10:
            makeThemCool(tile)
            fromTeleport.append(tile)
        else:
            makeThemCool(tile)
        i += 1

    zValue = oldZ
    while 11 < i < 18:
        tile = GameObject(
            Transform(
                position=glm.vec3(xValue - 0.5, yValue + 2.5, zValue),
                scale=glm.vec3(0.5),
                parent=parent_point.transform,
                rotation=glm.quat(glm.vec3(0, 0, glm.radians(90)))
            ),
            deepcopy(tiles_obj),
            ReactiveAABB.copy_from(tiles_obj.AABB)
        )
        if i == 12:
            openTeleport.append(tile)
        elif i == 17:
            closeLaser.append(tile)

        makeThemCool(tile)

        zValue += 1

        i += 1


# def makeSpecialsCool():
#     winningTile = []
#     openTeleport = []
#     fromTeleport = []
#     toTeleport = []
#     closeLaser = []
#
#     for tile in openTeleport:
#         tile.meshes[0].material.map_Kd =  glm.vec3(0.8, 0.2, 0.2)
#     for tile in fromTeleport:
#         tile.meshes[0].material.map_Kd =  glm.vec3(0.8, 0.2, 0.2)
#     for tile in toTeleport:
#         tile.meshes[0].material.map_Kd = glm.vec3(0.8, 0.2, 0.2)


createPlayground()


# makeSpecialsCool()

def display():
    # print(cube.collisionCount)
    # for e in playground_parents:
    # print(e.transform.rotation,e.transform.get_final_rotation(), e.transform.rotation * glm.quat(glm.vec3(0, 0, glm.radians(90))))
    # AABB update
    for collider in GameObject.WithAABB:
        collider.AABB.update(collider.transform)

    for tilesXZ in tilesList:
        tilesXZ.AABB.update(tilesXZ.transform, glm.vec3(0.8, 1, 0.8))

    cube.collisionCount = 0
    for tile in playground:
        winningTile[0].obj_data.meshes[0].material.Kd = glm.vec3(0, 1, 0)
        openTeleport[0].obj_data.meshes[0].material.Kd = glm.vec3(0, 0, 1)
        toTeleport[0].obj_data.meshes[0].material.Kd = glm.vec3(0, 0.5, 0.5)
        fromTeleport[0].obj_data.meshes[0].material.Kd = glm.vec3(0, 0.5, 0.5)
        closeLaser[0].obj_data.meshes[0].material.Kd = glm.vec3(1, 0, 0)
        if cube.AABB.check_collision(tile.AABB):
            cube.collisionCount += 1
            tile.obj_data.meshes[0].material.Kd = glm.vec3(0.9, 0.2, 0.2)
        else:
            tile.obj_data.meshes[0].material.Kd = glm.vec3(0.9, 0.9, 0.9)



    # Drawing part
    # Clear screen
    gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

    # Draw objects in a standard way
    standard_shader.draw(
        perspective_projection,
        camera.get_view(),
        camera.transform.get_final_position(),
        light_position,
        GameObject.WithObjData
    )

    # # Draw AABB debuggers
    # AABB_shader.draw(
    #     perspective_projection,
    #     camera.get_view(),
    #     (game_object.AABB for game_object in GameObject.WithAABB)
    # )

    UI_shader.draw(
        orthogonal_projection,
        hearts
    )

    # Swap the buffer we just drew on with the one showing on the screen
    glut.glutSwapBuffers()


glut.glutDisplayFunc(display)
glut.glutIdleFunc(display)


def resize(width, height):
    gl.glViewport(0, 0, width, height)
    screen_size.x = width
    screen_size.y = height
    global perspective_projection
    perspective_projection = glm.perspective(glm.radians(45.0), screen_size.x / screen_size.y, 0.1, 100.0)


glut.glutReshapeFunc(resize)


def makeInitialFallEffect(acceleration=0):
    parent_point.transform.rotation = glm.quat(glm.vec3(0, 0, 0))
    cube.mapRotated = False

    cube.transform.rotation = glm.quat(glm.vec3(0, 0, 0))
    cube.transform.position = glm.vec3(0, 3.0, 0.0)

    while cube.transform.position.y > 0:
        cube.transform.position -= glm.vec3(0, acceleration, 0)
        acceleration += 0.0007
        display()
    cube.transform.position = glm.vec3(cube.transform.position.x,
                                       (cube.transform.position.y * 0) - 0.01,
                                       cube.transform.position.z)
    display()

    cube.rotateDirection = 'none'


def fallDown(isDead):
    acceleration = 0

    if not cube.mapRotated:
        while cube.transform.position.y > -30:
            cube.transform.position -= glm.vec3(0, acceleration, 0)
            acceleration += 0.0007
            display()
    else:
        while cube.transform.position.x < 30:
            cube.transform.position += glm.vec3(acceleration, 0, 0)
            acceleration += 0.0007
            display()

    cube.transform.position = glm.vec3(0, 20, 0)

    if not isDead:
        while cube.transform.position.y > 6:
            cube.transform.position -= glm.vec3(0, acceleration, 0)
            acceleration += 0.0007
            display()

        makeInitialFallEffect(acceleration)


def tilesFallDown():
    for tile in playground:
        acceleration = 0
        while tile.transform.position.y > -30:
            tile.transform.position -= glm.vec3(0, acceleration, 0)
            acceleration += 0.7
            display()


def checkLives():
    if not heart_remove_order.empty():
        heart_to_remove = heart_remove_order.get()
        heart_to_remove.leave_set(hearts)
        cube.life -= 1
        if cube.life == 2:
            gl.glClearColor(0.3, 0.1, 0.1, 0)
            display()
        elif cube.life == 1:
            gl.glClearColor(0.6, 0.1, 0.1, 0)
            display()
        return False
    if heart_remove_order.empty():
        gl.glClearColor(1, 0.1, 0.1, 0)
        display()
        tilesFallDown()
        return True


def checkCollision(key):
    cube.willRotate = False
    rotation = cube.transform.rotation
    if cube.rotateDirection == 'none' and cube.collisionCount == 0:
        fallDown(checkLives())
    elif cube.rotateDirection != 'none' and cube.collisionCount < 1:
        fallDown(checkLives())
    elif cube.rotateDirection != 'none' and cube.collisionCount == 1:
        fallDown(checkLives())
    elif cube.collisionCount > 2.5:
        cube.willRotate = True


def movement(direction, currentStance, nextStance):
    if not cube.mapRotated:
        if cube.willRotate:
            if direction == 'd':
                parent_point.transform.rotation = glm.quat(glm.vec3(0, 0, glm.radians(-90)))
                cube.mapRotated = True
            else:
                movementXZ(direction, currentStance, nextStance)
        else:
            movementXZ(direction, currentStance, nextStance)
    else:
        if cube.willRotate:
            if direction == 'a':
                parent_point.transform.rotation = glm.quat(glm.vec3(0, 0, 0))
                cube.mapRotated = False
            else:
                movementYZ(direction, currentStance, nextStance)
        else:
            movementYZ(direction, currentStance, nextStance)


# cube.transform.get_final_rotation()
def movementXZ(direction, currentStance, nextStance):
    if currentStance == 'none':
        if nextStance == 'horizontal':
            if direction == 'd':
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, glm.radians(90)))
                cube.transform.position += glm.vec3(1.5, -0.5, 0)
            else:
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, glm.radians(-90)))
                cube.transform.position -= glm.vec3(1.5, 0.5, 0)
        if nextStance == 'vertical':
            if direction == 'w':
                cube.transform.rotation = glm.quat(glm.vec3(glm.radians(90), 0, 0))
                cube.transform.position += glm.vec3(0, -0.5, -1.5)
            else:
                cube.transform.rotation = glm.quat(glm.vec3(glm.radians(-90), 0, 0))
                cube.transform.position -= glm.vec3(0, 0.5, -1.5)
    if currentStance == 'vertical':
        if nextStance == 'vertical':
            if direction == 'd':
                # cube.transform.rotation *= glm.quat(glm.vec3(0, 0, glm.radians(90)))
                cube.transform.position += glm.vec3(1, 0, 0)
            else:
                # cube.transform.rotation *= glm.quat(glm.vec3(0, 0, glm.radians(-90)))
                cube.transform.position -= glm.vec3(1, 0, 0)
        if nextStance == 'none':
            if direction == 'w':
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, 0))
                cube.transform.position += glm.vec3(0, 0.5, -1.5)
            else:
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, 0))
                cube.transform.position += glm.vec3(0, 0.5, 1.5)
    if currentStance == 'horizontal':
        if nextStance == 'horizontal':
            if direction == 'w':
                # cube.transform.rotation *= glm.quat(glm.vec3(0, glm.radians(90), 0))
                cube.transform.position += glm.vec3(0, 0, -1)
            else:
                # cube.transform.rotation *= glm.quat(glm.vec3(0, glm.radians(-90), 0))
                cube.transform.position -= glm.vec3(0, 0, -1)
        if nextStance == 'none':
            if direction == 'd':
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, 0))
                cube.transform.position += glm.vec3(1.5, 0.5, 0)
            else:
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, 0))
                cube.transform.position -= glm.vec3(1.5, -0.5, 0)


def movementYZ(direction, currentStance, nextStance):
    if currentStance == 'none':
        if nextStance == 'horizontal':
            if direction == 'd':
                cube.transform.rotation = glm.quat(glm.vec3(0, glm.radians(90), 0))
                cube.transform.position += glm.vec3(0.5, 1.5, 0)
            else:
                cube.transform.rotation = glm.quat(glm.vec3(0, glm.radians(-90), 0))
                cube.transform.position -= glm.vec3(-0.5, 1.5, 0)
        if nextStance == 'vertical':
            if direction == 'w':
                cube.transform.rotation = glm.quat(glm.vec3(glm.radians(90), 0, 0))
                cube.transform.position += glm.vec3(0.5, 0, -1.5)
            else:
                cube.transform.rotation = glm.quat(glm.vec3(glm.radians(-90), 0, 0))
                cube.transform.position += glm.vec3(0.5, 0, 1.5)
    if currentStance == 'vertical':
        if nextStance == 'vertical':
            if direction == 'd':
                # cube.transform.rotation *= glm.quat(glm.vec3(0, 0, glm.radians(90)))
                cube.transform.position += glm.vec3(0, 1, 0)
            else:
                # cube.transform.rotation *= glm.quat(glm.vec3(0, 0, glm.radians(-90)))
                cube.transform.position -= glm.vec3(0, 1, 0)
        if nextStance == 'none':
            if direction == 'w':
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, glm.radians(90)))
                cube.transform.position += glm.vec3(-0.5, 0, -1.5)
            else:
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, glm.radians(-90)))
                cube.transform.position += glm.vec3(-0.5, 0, 1.5)
    if currentStance == 'horizontal':
        if nextStance == 'horizontal':
            if direction == 'w':
                # cube.transform.rotation *= glm.quat(glm.vec3(0, glm.radians(90), 0))
                cube.transform.position += glm.vec3(0, 0, -1)
            else:
                # cube.transform.rotation *= glm.quat(glm.vec3(0, glm.radians(-90), 0))
                cube.transform.position -= glm.vec3(0, 0, -1)
        if nextStance == 'none':
            if direction == 'd':
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, glm.radians(90)))
                cube.transform.position += glm.vec3(-0.5, 1.5, 0)
            else:
                cube.transform.rotation = glm.quat(glm.vec3(0, 0, glm.radians(-90)))
                cube.transform.position -= glm.vec3(0.5, 1.5, 0)


def keyboard_input(key, x, y):
    if key == b'\x1b':
        sys.exit()
    if key == b' ':
        if cube.life == 0:
            gl.glClearColor(0.2, 0.2, 0.2, 0)
            createHearts()
            createPlayground()
            cube.life = 3
        makeInitialFallEffect()
    if key == b'd':
        if cube.rotateDirection == 'horizontal':
            print('press d hor to none')
            movement('d', 'horizontal', 'none')
            cube.rotateDirection = 'none'
        elif cube.rotateDirection == 'vertical':
            print('press d ver to ver')
            movement('d', 'vertical', 'vertical')
        elif cube.rotateDirection == 'none':
            print('press d none to hor')
            movement('d', 'none', 'horizontal')
            cube.rotateDirection = 'horizontal'
        display()
        cube.lastPressed = 'd'
    elif key == b'w':
        if cube.rotateDirection == 'none':
            print('press w none to ver')
            movement('w', 'none', 'vertical')
            cube.rotateDirection = 'vertical'
        elif cube.rotateDirection == 'vertical':
            print('press w ver to none')
            movement('w', 'vertical', 'none')
            cube.rotateDirection = 'none'
        elif cube.rotateDirection == 'horizontal':
            print('press w hor to hor')
            movement('w', 'horizontal', 'horizontal')
            cube.rotateDirection = 'horizontal'
        display()
        cube.lastPressed = 'w'
    elif key == b'a':
        if cube.rotateDirection == 'horizontal':
            print('press a hor to none')
            movement('a', 'horizontal', 'none')
            cube.rotateDirection = 'none'
        elif cube.rotateDirection == 'none':
            print('press a none to hor')
            movement('a', 'none', 'horizontal')
            cube.rotateDirection = 'horizontal'
        elif cube.rotateDirection == 'vertical':
            print('press a ver to ver')
            movement('a', 'vertical', 'vertical')
            cube.isRotrotateDirectionated = 'vertical'
        display()
        cube.lastPressed = 'a'
    elif key == b's':
        if cube.rotateDirection == 'none':
            print('press s none to ver')
            movement('s', 'none', 'vertical')
            cube.rotateDirection = 'vertical'
        elif cube.rotateDirection == 'horizontal':
            print('press s hor to hor')
            movement('s', 'horizontal', 'horizontal')
            cube.rotateDirection = 'horizontal'
        elif cube.rotateDirection == 'vertical':
            print('press s ver to none')
            movement('s', 'vertical', 'none')
            cube.rotateDirection = 'none'
        display()
        cube.lastPressed = 's'
    checkCollision(key)


glut.glutKeyboardFunc(keyboard_input)

# Start the Main Loop ----------------------------------------------------------------|

glut.glutMainLoop()

# I WILL ROTATE THE MAP ACCORDING TO X, Y POSITIONS OF TILES
