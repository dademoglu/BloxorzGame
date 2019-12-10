from typing import Iterable

from OpenGL import GL as gl
from OpenGL.GL import shaders
from GameUtilities import *


class AABBShader:
    def __init__(self, cube_obj_data: ObjData):
        self.cube_obj_data = cube_obj_data

        # Compile shaders
        vertex_shader = shaders.compileShader("""#version 330
        layout(location = 0) in vec3 vertex_position;
        uniform mat4 projection;
        uniform mat4 view;
        uniform mat4 transformation;

        void main()
        {
            //  Because the transformation matrix is 4x4, we have to construct a vec4 from position, so we an multiply them
            vec4 pos = vec4(vertex_position, 1.0);
            gl_Position = projection * view * transformation * pos;
        }
        """, gl.GL_VERTEX_SHADER)

        fragment_shader = shaders.compileShader("""#version 330
        out vec4 fragment_color;

        void main()
        {
            fragment_color = vec4(1.0, 0.41, 0.70, 1.0);
        }
        """, gl.GL_FRAGMENT_SHADER)

        # Compile the program
        self.id = shaders.compileProgram(vertex_shader, fragment_shader)

        # Get the locations
        gl.glUseProgram(self.id)
        self.transformation_location = gl.glGetUniformLocation(self.id, "transformation")
        self.view_location = gl.glGetUniformLocation(self.id, "view")
        self.projection_location = gl.glGetUniformLocation(self.id, "projection")
        gl.glUseProgram(0)

    def draw(self, projection, view, aabbs: Iterable[AABB]):
        # Set the polygon mode to lines so we can see the actual object inside the AABB
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)

        gl.glUseProgram(self.id)

        gl.glUniformMatrix4fv(self.projection_location, 1, False, glm.value_ptr(projection))
        gl.glUniformMatrix4fv(self.view_location, 1, False, glm.value_ptr(view))

        for aabb in aabbs:
            # Set the vao
            gl.glBindVertexArray(self.cube_obj_data.vao)

            AABB_transformation = glm.mat4x4()
            AABB_transformation = glm.translate(AABB_transformation, aabb.get_center())
            AABB_transformation = glm.scale(AABB_transformation, aabb.get_dimensions() / 2.0)

            # Set the transform uniform to self.transform
            gl.glUniformMatrix4fv(self.transformation_location, 1, False, glm.value_ptr(AABB_transformation))

            for mesh in self.cube_obj_data.meshes:
                # Draw the mesh with an element buffer.
                gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, mesh.element_array_buffer)
                # When the last parameter in 'None', the buffer bound to the GL_ELEMENT_ARRAY_BUFFER will be used.
                gl.glDrawElements(gl.GL_TRIANGLES, mesh.element_count, gl.GL_UNSIGNED_INT, None)

        # Set the state to its initial
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
