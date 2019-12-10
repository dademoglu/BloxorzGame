from typing import Iterable

from OpenGL import GL as gl
from OpenGL.GL import shaders
from GameUtilities import *


class UnlitBlendShader:
    def __init__(self):
        # Compile shaders
        vertex_shader = shaders.compileShader("""#version 330
        layout(location = 0) in vec3 vertex_position;
        layout(location = 1) in vec2 vertex_texture_position;
        uniform mat4 projection;
        uniform mat4 transformation;

        out vec2 texture_position;

        void main()
        {
            //  Because the transformation matrix is 4x4, we have to construct a vec4 from position, so we an multiply them
            vec4 pos = vec4(vertex_position, 1.0);
            gl_Position = projection * transformation * pos;

            texture_position = vertex_texture_position;
        }
        """, gl.GL_VERTEX_SHADER)

        fragment_shader = shaders.compileShader("""#version 420
        layout(binding = 1) uniform sampler2D diffuse_color_sampler;
        in vec2 texture_position;

        uniform vec3 diffuse_color;
        uniform float transparency;

        out vec4 fragment_color;

        void main()
        {
            fragment_color = vec4(diffuse_color, transparency) + texture(diffuse_color_sampler, texture_position);
        }
        """, gl.GL_FRAGMENT_SHADER)

        # Compile the program
        self.id = shaders.compileProgram(vertex_shader, fragment_shader)

        # Get the locations
        gl.glUseProgram(self.id)
        self.transformation_location = gl.glGetUniformLocation(self.id, "transformation")
        self.projection_location = gl.glGetUniformLocation(self.id, "projection")
        self.diffuse_color_location = gl.glGetUniformLocation(self.id, "diffuse_color")
        self.transparency_location = gl.glGetUniformLocation(self.id, "transparency")
        gl.glUseProgram(0)

    def draw(self, projection, game_objects: Iterable[GameObject]):
        # Enable transparency
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        gl.glUseProgram(self.id)

        gl.glUniformMatrix4fv(self.projection_location, 1, False, glm.value_ptr(projection))

        for game_object in game_objects:
            # Set the vao
            gl.glBindVertexArray(game_object.obj_data.vao)

            # Set the transform uniform to self.transform
            gl.glUniformMatrix4fv(self.transformation_location, 1, False, glm.value_ptr(game_object.transform.get_matrix()))

            for mesh in game_object.obj_data.meshes:
                # Set material uniforms
                gl.glUniform3fv(self.diffuse_color_location, 1, glm.value_ptr(mesh.material.Kd))
                gl.glUniform1fv(self.transparency_location, 1, mesh.material.Tr)

                # Set material textures
                gl.glActiveTexture(gl.GL_TEXTURE1)
                gl.glBindTexture(gl.GL_TEXTURE_2D, mesh.material.map_Kd)

                # Draw the mesh with an element buffer.
                gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, mesh.element_array_buffer)
                # When the last parameter in 'None', the buffer bound to the GL_ELEMENT_ARRAY_BUFFER will be used.
                gl.glDrawElements(gl.GL_TRIANGLES, mesh.element_count, gl.GL_UNSIGNED_INT, None)

        gl.glDisable(gl.GL_BLEND)
