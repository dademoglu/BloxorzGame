from os import path
from collections import OrderedDict
from typing import Dict

from OpenGL import GL as gl
import glm
import numpy as np
from PIL import Image
from GameUtilities import *


def load_image_to_texture(image_file_name, mag_filter=gl.GL_LINEAR, min_filter=gl.GL_LINEAR_MIPMAP_LINEAR):
    # Read image data
    # The y-coordinates of image data and what OpenGL is expecting are reversed. So we flip the y-coordinates
    image = Image.open(image_file_name).transpose(Image.FLIP_TOP_BOTTOM)
    # Load the data into a numpy array so we can pass it to OpenGL
    image_data = np.array(image.getdata(), dtype=np.uint8)

    # Create a texture
    texture = gl.glGenTextures(1)

    # Bind to it
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)

    # Set its parameters
    gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
    gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
    gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, mag_filter)
    gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, min_filter)

    # Check if the texture has an Alpha (transparency) chanel or not. It won't work properly with the wrong type.
    if image.mode == "RGBA":
        image_type = gl.GL_RGBA
    else:
        image_type = gl.GL_RGB
    # Send the image data to be used as texture
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image.size[0], image.size[1], 0, image_type, gl.GL_UNSIGNED_BYTE, image_data)

    # Generate mipmaps for the texture
    gl.glGenerateMipmap(gl.GL_TEXTURE_2D)

    # Don't forget to close the image (i.e. free the memory)
    image.close()

    # return the texture id
    return texture


def parse_material_file(material_file_name, obj_file_path=""):
    with open(path.join(obj_file_path, material_file_name), "r") as material_file:
        materials: Dict[str, Material] = dict()
        current_material: Material = None

        for line in material_file.readlines():
            tokens = line.strip().split()

            if tokens[0] == "newmtl":
                new_material = Material(name=tokens[1])
                materials[tokens[1]] = new_material
                current_material = new_material

            elif tokens[0] == "Ka":
                current_material.Ka = glm.vec3(tuple(map(float, tokens[1:])))

            elif tokens[0] == "Kd":
                current_material.Kd = glm.vec3(tuple(map(float, tokens[1:])))

            elif tokens[0] == "Ks":
                current_material.Ks = glm.vec3(tuple(map(float, tokens[1:])))

            elif tokens[0] == "Ns":
                current_material.Ns = float(tokens[1])

            elif tokens[0] == "Tr":
                current_material.Tr = float(tokens[1])
            elif tokens[0] == "d":  # An alternative to Tr
                current_material.Tr = 1.0 - float(tokens[1])

            elif tokens[0] == "map_Ka":
                current_material.map_Ka = path.join(obj_file_path, tokens[1])

            elif tokens[0] == "map_Kd":
                current_material.map_Kd = path.join(obj_file_path, tokens[1])

            else:
                current_material.properties[tokens[0]] = tokens[1]

    return materials


class ParsedMesh:
    def __init__(self, name, material, vertex_indices):
        self.name = name
        self.material = material
        self.vertex_indices = vertex_indices


class ParsedObjData:
    def __init__(self, positions: np.ndarray, texture_positions: np.ndarray, normals: np.ndarray, meshes: List[ParsedMesh]):
        self.positions = positions
        self.AABB = AABB(positions)
        self.texture_positions = texture_positions
        self.normals = normals
        self.meshes = meshes


def parse_obj_file(obj_file_name) -> ParsedObjData:
    obj_file_path, obj_file_name = path.split(obj_file_name)

    if not obj_file_name.endswith(".obj"):
        raise RuntimeError(f"Can't load '{obj_file_name}', because it is not an .obj file")

    positions = []
    texture_positions = []
    normals = []

    faces = []

    meshes: List[ParsedMesh] = []

    materials: Dict[str, Material] = dict()
    current_material = None

    current_mesh_name = "unnamed"

    with open(path.join(obj_file_path, obj_file_name), "r") as obj_file:
        for line in obj_file.readlines():
            tokens = line.strip().split()

            if len(tokens) == 0 or tokens[0] == "#":
                continue

            elif tokens[0] == "o" or tokens[0] == "g":
                current_mesh_name = "unnamed" if len(tokens) == 1 else tokens[1]

            elif tokens[0] == "v":
                positions.append(tuple(map(float, tokens[1:])))

            elif tokens[0] == "vt":
                texture_positions.append(tuple(map(float, tokens[1:])))

            elif tokens[0] == "vn":
                normals.append(tuple(map(float, tokens[1:])))

            elif tokens[0] == "f":
                vertices = []
                for vertex in tokens[1:]:
                    vertices.append(tuple(map(int, vertex.split("/"))))

                for i in range(2, len(vertices)):
                    faces.append(vertices[0])
                    faces.append(vertices[i - 1])
                    faces.append(vertices[i])

            elif tokens[0] == "usemtl":
                if current_material is None:
                    current_material = materials[tokens[1]]

                else:
                    meshes.append(
                        ParsedMesh(
                            current_mesh_name,
                            current_material,
                            faces[:]
                        )
                    )

                    current_material = materials[tokens[1]]
                    faces = []

            elif tokens[0] == "mtllib":
                materials.update(parse_material_file(tokens[1], obj_file_path))

    # Create a mesh from remaining faces
    meshes.append(
        ParsedMesh(
            current_mesh_name,
            current_material,
            faces[:]
        )
    )

    # Data parsing is done
    # Format the face data for draw elements

    unique_vertices = OrderedDict()
    index = 0

    for mesh in meshes:
        for vertex in mesh.vertex_indices:
            if vertex in unique_vertices:
                continue

            unique_vertices[vertex] = index
            index += 1

    formatted_positions = []
    formatted_texture_positions = []
    formatted_normals = []

    # Create position, texture_position and normal arrays in the order
    for vertex in unique_vertices.keys():
        formatted_positions.append(positions[vertex[0] - 1])
        formatted_texture_positions.append(texture_positions[vertex[1] - 1])
        formatted_normals.append(normals[vertex[2] - 1])

    formatted_meshes = []

    # Create meshes with element indexing
    for mesh in meshes:
        formatted_indices = []
        for vertex in mesh.vertex_indices:
            formatted_indices.append(unique_vertices[vertex])

        formatted_meshes.append(
            ParsedMesh(mesh.name, mesh.material, formatted_indices)
        )

    return ParsedObjData(
        np.array(formatted_positions, dtype=np.float32),
        np.array(formatted_texture_positions, dtype=np.float32),
        np.array(formatted_normals, dtype=np.float32),
        formatted_meshes
    )


def send_data_to_vertex_buffer(data, location) -> int:
    # Turn data into a np array so we can send it to a GPU buffer
    vertex_data = np.array(
        data,
        dtype=np.float32
    )
    # Get properties of the vertex data
    data_count = vertex_data.shape[1]       # the count of floats per vertex data
    data_stride = vertex_data.strides[0]    # bytes to skip for the next vertex data
    data_offset = gl.ctypes.c_void_p(0)     # beginning offset

    # Request a buffer slot from GPU
    vertex_buffer = gl.glGenBuffers(1)

    # Describe how the position attribute will parse this buffer
    # 1. First, tell where the data will be read from
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertex_buffer)
    # 2. Second, tell how the data should be read and where to be sent
    gl.glVertexAttribPointer(location, data_count, gl.GL_FLOAT, False, data_stride, data_offset)

    # Enable the attribute
    gl.glEnableVertexAttribArray(location)

    # Send vertex data (which is on CPU memory) to vertex buffer (which is on GPU memory)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, gl.GL_STATIC_DRAW)

    # Bind the GL_ARRAY_BUFFER to 0 (default) to keep the state clear
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

    return vertex_buffer


def send_indices_to_element_buffer(data) -> int:
    # Turn data into a np array so we can send it to a GPU buffer
    element_data = np.array(
        data,
        dtype=np.uint32
    )

    element_buffer = gl.glGenBuffers(1)

    # Unlike other buffers, it is bound to the GL_ELEMENT_ARRAY_BUFFER
    gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, element_buffer)

    # Send element data (which is on CPU memory) to element buffer (which is on GPU memory)
    gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, element_data.nbytes, element_data, gl.GL_STATIC_DRAW)

    # Bind GL_ELEMENT_ARRAY_BUFFER to 0 (default) to keep the state clear
    gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

    return element_buffer


def normalize_positions(obj_data: ParsedObjData):
    # Normalize positions
    data_max = obj_data.positions.max()
    data_min = obj_data.positions.min()
    obj_data.positions = (obj_data.positions - data_min) / (data_max - data_min) * 2.0 - 1.0

    # Also update the AABB
    obj_data.AABB.min = (obj_data.AABB.min - data_min) / (data_max - data_min) * 2.0 - 1.0
    obj_data.AABB.max = (obj_data.AABB.max - data_min) / (data_max - data_min) * 2.0 - 1.0


def bind_material_textures(material: Material):
    if material.map_Ka is not None:
        material.map_Ka = load_image_to_texture(material.map_Ka)
    else:
        material.map_Ka = 0

    if material.map_Kd is not None:
        material.map_Kd = load_image_to_texture(material.map_Kd)
    else:
        material.map_Kd = 0

    return material


def bind_mesh_data(obj_data: ParsedObjData) -> ObjData:
    # Create and bind a Vertex Array Object to save the Vertex Buffer configurations we will make
    vao = gl.glGenVertexArrays(1)
    gl.glBindVertexArray(vao)

    # Create the position buffer. It will store 3D position of each vertex at location 0
    position_buffer = send_data_to_vertex_buffer(
        obj_data.positions,
        0
    )

    # Create the texture positions buffer. It will store 2D texture position of each vertex at location 1
    texture_positions_buffer = send_data_to_vertex_buffer(
        obj_data.texture_positions,
        1
    )

    # Create the normals buffer. It will store 3D normal vector of each vertex at location 2
    normals_buffer = send_data_to_vertex_buffer(
        obj_data.normals,
        2
    )

    # Create the element buffers for each mesh
    meshes = []

    for mesh in obj_data.meshes:
        meshes.append(
            Mesh(
                mesh.name,
                bind_material_textures(mesh.material),
                send_indices_to_element_buffer(
                    mesh.vertex_indices
                ),
                len(mesh.vertex_indices)
            )
        )

    # Bind Vertex Array to 0 (default) to keep the state clear
    gl.glBindVertexArray(0)

    return ObjData(vao, position_buffer, texture_positions_buffer, normals_buffer, meshes, obj_data.AABB)


def parse_and_bind_obj_file(obj_file_name, should_normalize_positions=True):
    obj_data = parse_obj_file(obj_file_name)

    if should_normalize_positions:
        normalize_positions(obj_data)

    return bind_mesh_data(obj_data)
