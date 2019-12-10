from typing import Iterable

from OpenGL import GL as gl
from OpenGL.GL import shaders
from GameUtilities import *


class StandardShader:
    def __init__(self):
        # Compile shaders
        vertex_shader = shaders.compileShader("""#version 330
        layout(location = 0) in vec3 vertex_position;
        layout(location = 1) in vec2 vertex_texture_position;
        layout(location = 2) in vec3 vertex_normal;
        uniform mat4 projection;
        uniform mat4 view;
        uniform mat4 transformation;

        out vec2 texture_position;
        out vec3 normal;
        out vec3 world_position;

        void main()
        {
            //  Because the transformation matrix is 4x4, we have to construct a vec4 from position, so we an multiply them
            vec4 pos = vec4(vertex_position, 1.0);
            gl_Position = projection * view * transformation * pos;

            texture_position = vertex_texture_position;

            vec4 transformed_normal = transpose(inverse(transformation)) * vec4(vertex_normal, 0.0);
            normal = normalize(transformed_normal.xyz);

            world_position = (transformation * pos).xyz;
        }
        """, gl.GL_VERTEX_SHADER)

        fragment_shader = shaders.compileShader("""#version 420
        layout(binding = 0) uniform sampler2D ambient_color_sampler;
        layout(binding = 1) uniform sampler2D diffuse_color_sampler;
        in vec2 texture_position;
        in vec3 normal;
        in vec3 world_position;
        uniform vec3 light_position;
        uniform vec3 camera_position;

        uniform vec3 ambient_color;
        uniform vec3 diffuse_color;
        uniform vec3 specular_color;
        uniform float shininess;

        out vec4 fragment_color;

        void main()
        {
            float ambient_intensity = 0.1;

            vec3 color = (ambient_color + texture(ambient_color_sampler, texture_position).xyz) * ambient_intensity;


            float diffuse_intensity = 0.9;
            float light_intensity = dot(
                normalize(light_position - world_position),
                normal
            );

            color += (diffuse_color + texture(diffuse_color_sampler, texture_position).xyz) * diffuse_intensity * max(0.0, light_intensity);


            if (light_intensity > 0.0)
            {
                float specular_intensity = 1.0;
                vec3 light_reflection = reflect(
                    normalize(world_position - light_position),
                    normal
                );
                float reflection_intensity = dot(
                    normalize(camera_position - world_position),
                    light_reflection
                );

                color += specular_color * specular_intensity * max(0.0, pow(max(0.0, reflection_intensity), shininess));
            }

            fragment_color = vec4(color, 1.0);
        }
        """, gl.GL_FRAGMENT_SHADER)

        # Compile the program
        self.id = shaders.compileProgram(vertex_shader, fragment_shader)

        # Get the locations
        gl.glUseProgram(self.id)
        self.transformation_location = gl.glGetUniformLocation(self.id, "transformation")
        self.view_location = gl.glGetUniformLocation(self.id, "view")
        self.projection_location = gl.glGetUniformLocation(self.id, "projection")
        self.light_position_location = gl.glGetUniformLocation(self.id, "light_position")
        self.camera_position_location = gl.glGetUniformLocation(self.id, "camera_position")
        self.ambient_color_location = gl.glGetUniformLocation(self.id, "ambient_color")
        self.diffuse_color_location = gl.glGetUniformLocation(self.id, "diffuse_color")
        self.specular_color_location = gl.glGetUniformLocation(self.id, "specular_color")
        self.shininess_location = gl.glGetUniformLocation(self.id, "shininess")
        gl.glUseProgram(0)

    def draw(self, projection, view, camera_position, light_position, game_objects: Iterable[GameObject]):
        gl.glUseProgram(self.id)

        gl.glUniformMatrix4fv(self.projection_location, 1, False, glm.value_ptr(projection))
        gl.glUniformMatrix4fv(self.view_location, 1, False, glm.value_ptr(view))
        gl.glUniform3fv(self.camera_position_location, 1, glm.value_ptr(camera_position))
        gl.glUniform3fv(self.light_position_location, 1, glm.value_ptr(light_position))

        for game_object in game_objects:
            # Set the vao
            gl.glBindVertexArray(game_object.obj_data.vao)

            # Set the transform uniform to self.transform
            gl.glUniformMatrix4fv(self.transformation_location, 1, False, glm.value_ptr(game_object.transform.get_matrix()))

            for mesh in game_object.obj_data.meshes:
                # Set material uniforms
                gl.glUniform3fv(self.ambient_color_location, 1, glm.value_ptr(mesh.material.Ka))
                gl.glUniform3fv(self.diffuse_color_location, 1, glm.value_ptr(mesh.material.Kd))
                gl.glUniform3fv(self.specular_color_location, 1, glm.value_ptr(mesh.material.Ks))
                gl.glUniform1fv(self.shininess_location, 1, mesh.material.Ns)

                # Set material textures
                gl.glActiveTexture(gl.GL_TEXTURE0)
                gl.glBindTexture(gl.GL_TEXTURE_2D, mesh.material.map_Ka)
                gl.glActiveTexture(gl.GL_TEXTURE1)
                gl.glBindTexture(gl.GL_TEXTURE_2D, mesh.material.map_Kd)

                # Draw the mesh with an element buffer.
                gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, mesh.element_array_buffer)
                # When the last parameter in 'None', the buffer bound to the GL_ELEMENT_ARRAY_BUFFER will be used.
                gl.glDrawElements(gl.GL_TRIANGLES, mesh.element_count, gl.GL_UNSIGNED_INT, None)
