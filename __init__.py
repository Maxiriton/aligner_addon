# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Vertex Aligner & Planarizer",
    "author": "Benjamin Louis, Henri Hebeisen",
    "description": "Align vertices to custom axis and planarize selected vertices.",
    "blender": (4, 3, 2),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector
from bpy.types import Operator, PropertyGroup, Panel
from bpy.props import BoolProperty, FloatVectorProperty


# Storage Classes

class VertexAxisAligner(PropertyGroup):
    axis_defined = BoolProperty(name="Axis Defined", default=False)
    p1 = FloatVectorProperty(name="Point 1")
    p2 = FloatVectorProperty(name="Point 2")
    axis = FloatVectorProperty(name="Axis")

class VertexPlaneAligner(PropertyGroup):
    plane_defined = BoolProperty(name="Plane Defined", default=False)
    p1 = FloatVectorProperty(name="Point 1")
    p2 = FloatVectorProperty(name="Point 2")
    p3 = FloatVectorProperty(name="Point 3")
    normal = FloatVectorProperty(name="Normal")
    

class OBJECT_OT_define_axis(Operator):
    """Define Axis using Selected 2 Vertices"""
    bl_idname = "mesh.define_axis"
    bl_label = "Set Axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return  context.mode == 'EDIT_MESH'

    def execute(self, context):
        bm = bmesh.from_edit_mesh(context.object.data)
        selected_verts = [v for v in bm.verts if v.select == True]

        if len(selected_verts) < 2:
            bmesh.update_edit_mesh(context.object.data)
            self.report({'ERROR'}, "Select exactly two vertices to define the axis.")
            return {'CANCELLED'}

        aa = context.scene.axis_aligner
        # Update the axis
        aa.p1 = Vector(selected_verts[0].co)
        aa.p2 = Vector(selected_verts[1].co)
        aa.axis = (selected_verts[1].co - selected_verts[0].co).normalized()
        aa.axis_defined = True
        bmesh.update_edit_mesh(context.object.data)
        self.report({'INFO'}, f"Axis Defined Successfully : {aa.axis}")
        return {'FINISHED'}


class OBJECT_OT_align_vertices_on_axis(Operator):
    """Align Selected Vertices to the Defined Axis"""
    bl_idname = "mesh.align_vertices"
    bl_label = "Align"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return  context.mode == 'EDIT_MESH' and context.scene.axis_aligner.axis_defined is True

    def execute(self, context):
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)
        selected_verts = [v for v in bm.verts if v.select == True]

        if len(selected_verts) < 1:
            bmesh.update_edit_mesh(obj.data)
            self.report({'ERROR'}, "Select at least one vertex to align.")
            return {'CANCELLED'}

        aa = context.scene.axis_aligner
        for v in selected_verts:
            projection = aa.p1 + (v.co - aa.p1).dot(aa.axis) * aa.axis
            v.co = projection

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, "Vertices Aligned Successfully.")
        return {'FINISHED'}

# --- Operator Classes for PLANARIZER --- #

class OBJECT_OT_define_plane(Operator):
    """Define Plane using Selected 3 Vertices"""    
    bl_idname = "object.define_plane"
    bl_label = "Set Plane"

    @classmethod
    def poll(cls, context):
        return  context.mode == 'EDIT_MESH'

    def execute(self, context):
        bm = bmesh.from_edit_mesh(context.object.data)
        selected_verts = [v for v in bm.verts if v.select == True]

        if len(selected_verts) != 3 :
            bmesh.update_edit_mesh(context.object.data)
            self.report({'ERROR'}, "You must define a plane first by selecting 3 vertices.")
            return {'CANCELLED'}

        pa = context.scene.plane_aligner
        # Update the Plane
        pa.p1 = Vector(selected_verts[0].co)
        pa.p2 = Vector(selected_verts[1].co)
        pa.p2 = Vector(selected_verts[2].co)
        pa.normal =  (selected_verts[1].co - selected_verts[0].co).cross(selected_verts[2].co - selected_verts[0].co).normalized()
        pa.plane_defined = True
        bmesh.update_edit_mesh(context.object.data)
        self.report({'INFO'}, f"Plane Defined Successfully : {pa.normal}")
        return {'FINISHED'}


class OBJECT_OT_planarize_vertices(Operator):
    """Planarize Selected Vertices to the Defined Plane"""    
    bl_idname = "object.apply_planarize"
    bl_label = "Planarize"

    @classmethod
    def poll(cls, context):
        return  context.mode == 'EDIT_MESH' and context.scene.plane_aligner.plane_defined == True

    def execute(self, context):
        bm = bmesh.from_edit_mesh(context.object.data)
        selected_verts = [v for v in bm.verts if v.select == True]

        pa = context.scene.plane_aligner
        for vertex in selected_verts:
            displacement = (vertex.co - pa.p1).dot(pa.normal) * pa.normal
            vertex.co -= displacement
        
        bmesh.update_edit_mesh(context.object.data)
        self.report({'INFO'}, f"Applied planarize (flattening) to {len(selected_verts)} selected vertices.")
        return {'FINISHED'}


# --- UI Panel --- #
class VIEW3D_PT_vertex_aligner_planarizer_panel(Panel):
    """Panel for Vertex Aligner and Planarizer"""
    bl_label = "Vertex Aligner & Planarizer"
    bl_idname = "VIEW3D_PT_vertex_aligner_planarizer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_context = "mesh_edit"

    def draw(self, context):
        layout = self.layout

        # ALIGNER section
        layout.label(text="ALIGNER: Select 2 vertices to define axis.")
        row = layout.row()  # Creates a row for side-by-side buttons
        row.operator("mesh.define_axis", text="Set Axis", icon="EMPTY_AXIS")
        row.operator("mesh.align_vertices", text="Align", icon="SNAP_MIDPOINT")

        # PLANARIZER section
        layout.label(text="PLANARIZER: Select 3 vertices to define plane.")
        row = layout.row()  # Another row for side-by-side buttons
        row.operator("object.define_plane", text="Set Plane", icon="AXIS_TOP")
        row.operator("object.apply_planarize", text="Planarize", icon="SNAP_FACE_CENTER")


### Registration
classes = (
    OBJECT_OT_define_axis,
    OBJECT_OT_align_vertices_on_axis,
    OBJECT_OT_define_plane,
    OBJECT_OT_planarize_vertices,
    VIEW3D_PT_vertex_aligner_planarizer_panel,
    VertexAxisAligner,
    VertexPlaneAligner
)

def register():
    for cl in classes:
        bpy.utils.register_class(cl)

    bpy.types.Scene.axis_aligner = VertexAxisAligner
    bpy.types.Scene.plane_aligner = VertexPlaneAligner


def unregister():
    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)

    del bpy.types.Scene.axis_aligner
    del bpy.types.Scene.plane_aligner


if __name__ == "__main__":
    register()