import glm
import numpy as np
from typing import List, Set


class Transform:
    def __init__(self, parent: 'Transform' = None, position=None, scale=None, rotation=None):
        self.__parent = None
        self.__set_parent(parent)
        self.children: List[Transform] = []

        self.__position = position or glm.vec3(0.0)
        self.__scale = scale or glm.vec3(1.0)
        self.__rotation = rotation or glm.quat(glm.vec3(0.0))

        self.__transformation_matrix = None
        self.__transformations_changed = True

    def __get_parent(self):
        return self.__parent

    def __set_parent(self, transform):
        if self.__parent is not None:
            self.__parent.children.remove(self)

        self.__parent = transform

        if self.__parent is not None:
            self.__parent.children.append(self)

    parent = property(__get_parent, __set_parent)

    def __get_position(self):
        return self.__position

    def __set_position(self, position):
        self.__position = position
        self.__transformations_changed = True

    position = property(__get_position, __set_position)

    def __get_rotation(self):
        return self.__rotation

    def __set_rotation(self, rotation):
        self.__rotation = rotation
        self.__transformations_changed = True

    rotation = property(__get_rotation, __set_rotation)

    def __get_scale(self):
        return self.__scale

    def __set_scale(self, scale):
        self.__scale = scale
        self.__transformations_changed = True

    scale = property(__get_scale, __set_scale)

    def get_final_position(self):
        return (self.get_matrix() * glm.vec4(0.0, 0.0, 0.0, 1.0)).xyz

    def get_final_scale(self):
        return self.__scale if self.__parent is None else self.__scale * self.__parent.get_final_scale()

    def get_final_rotation(self):
        return self.__rotation if self.__parent is None else self.__rotation * self.__parent.get_final_rotation()

    def get_matrix(self):
        if self.__transformations_changed:
            transformation = glm.mat4x4()
            transformation = glm.translate(transformation, self.__position)
            transformation = transformation * glm.mat4_cast(self.__rotation)
            transformation = glm.scale(transformation, self.__scale)
            self.__transformation_matrix = transformation
            self.__transformations_changed = False

        if self.__parent is None:
            return self.__transformation_matrix
        else:
            return self.__parent.get_matrix() * self.__transformation_matrix


class AABB:
    def __init__(self, points):
        points = np.array(points, dtype=np.float32)
        self.__init_min = glm.vec3(points.min(axis=0))
        self.__init_max = glm.vec3(points.max(axis=0))
        self.min = glm.vec3(self.__init_min)
        self.max = glm.vec3(self.__init_max)

    def update(self, transform: Transform):
        scale = transform.get_final_scale()
        position = transform.get_final_position()
        self.min = self.__init_min * scale + position
        self.max = self.__init_max * scale + position

    def check_collision(self, other: 'AABB'):
        return (self.min.x <= other.max.x and self.max.x >= other.min.x) \
               and (self.min.y <= other.max.y and self.max.y >= other.min.y) \
               and (self.min.z <= other.max.z and self.max.z >= other.min.z)

    def get_center(self):
        return (self.min + self.max) / 2.0

    def get_dimensions(self):
        return self.max - self.min

    def corners(self):
        for x in (self.min.x, self.max.x):
            for y in (self.min.y, self.max.y):
                for z in (self.min.z, self.max.z):
                    yield glm.vec3(x, y, z)

    def initial_corners(self):
        for x in (self.__init_min.x, self.__init_max.x):
            for y in (self.__init_min.y, self.__init_max.y):
                for z in (self.__init_min.z, self.__init_max.z):
                    yield glm.vec3(x, y, z)

    @classmethod
    def copy_from(cls, other: 'AABB'):
        return cls(tuple(map(tuple, other.corners())))

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_AABB__init_min"] = tuple(state["_AABB__init_min"])
        state["_AABB__init_max"] = tuple(state["_AABB__init_max"])
        state["min"] = tuple(state["min"])
        state["max"] = tuple(state["max"])
        return state

    def __setstate__(self, state):
        state["_AABB__init_min"] = glm.vec3(state["_AABB__init_min"])
        state["_AABB__init_max"] = glm.vec3(state["_AABB__init_max"])
        state["min"] = glm.vec3(state["min"])
        state["max"] = glm.vec3(state["max"])
        self.__dict__.update(state)


class ReactiveAABB(AABB):
    def update(self, transform: Transform, scale=glm.vec3(1)):
        transformation = transform.get_matrix()
        new_corners = [tuple((transformation * glm.vec4(corner*scale, 1.0)).xyz) for corner in self.initial_corners()]
        new_corners = np.array(new_corners, dtype=np.float32)
        self.min = glm.vec3(new_corners.min(axis=0))
        self.max = glm.vec3(new_corners.max(axis=0))


class Material:
    def __init__(self, name):
        self.properties = dict()
        self.name = name
        self.Ka = glm.vec3(0.0)
        self.Kd = glm.vec3(0.0)
        self.Ks = glm.vec3(0.0)
        self.Ns = 0.0
        self.Tr = 1.0
        self.map_Ka = None
        self.map_Kd = None

    def __getstate__(self):
        state = self.__dict__.copy()
        state["Ka"] = tuple(state["Ka"])
        state["Kd"] = tuple(state["Kd"])
        state["Ks"] = tuple(state["Ks"])
        return state

    def __setstate__(self, state):
        state["Ka"] = glm.vec3(state["Ka"])
        state["Kd"] = glm.vec3(state["Kd"])
        state["Ks"] = glm.vec3(state["Ks"])
        self.__dict__.update(state)


class Mesh:
    def __init__(self, name, material, element_array_buffer, element_array_count):
        self.name = name
        self.material = material
        self.element_array_buffer = element_array_buffer
        self.element_count = element_array_count


class ObjData:
    def __init__(self, vao: int, positions_buffer: int, texture_positions_buffer: int, normals_buffer: int, meshes: List[Mesh], aabb: AABB):
        self.vao = vao
        self.positions_buffer = positions_buffer
        self.texture_positions_buffer = texture_positions_buffer
        self.normals_buffer = normals_buffer
        self.meshes = meshes
        self.AABB = aabb


GameObjectSet = Set['GameObject']


class GameObject:
    All: GameObjectSet = set()
    WithObjData: GameObjectSet = set()
    WithAABB: GameObjectSet = set()

    def __init__(self, transform=Transform(), obj_data: ObjData = None, aabb: AABB = None):
        self.__joined_sets: List[GameObjectSet] = []
        self.transform = transform
        self.mapRotated = False
        self.rotateDirection = 'none'
        self.collisionCount = 0
        self.life = 3
        self.willRotate = False
        self.isActive = False
        self.isLocked = False
        self.join_set(GameObject.All)

        self.obj_data = obj_data
        if obj_data is not None:
            self.join_set(GameObject.WithObjData)

        self.AABB = aabb
        if aabb is not None:
            self.join_set(GameObject.WithAABB)

    def join_set(self, tracker: GameObjectSet):
        tracker.add(self)
        self.__joined_sets.append(tracker)

    def leave_set(self, tracker: GameObjectSet):
        tracker.remove(self)
        self.__joined_sets.remove(tracker)


class Camera:
    def __init__(self, transform=Transform(), target=glm.vec3(0.0, 0.0, 1.0), up=glm.vec3(0.0, 1.0, 0.0)):
        self.transform = transform
        self.target = target
        self.up = up

    def get_view(self):
        return glm.lookAt(self.transform.get_final_position(), self.target, self.up)
