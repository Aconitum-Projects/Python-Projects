bl_info = {
    "name": "Remove All Vertex Groups",
    "author": "Giu",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "Object > Right Click",
    "category": "Object",
}

import bpy


class OBJECT_OT_remove_vertex_groups(bpy.types.Operator):
    bl_idname = "object.remove_all_vertex_groups"
    bl_label = "Remove All Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        for ob in context.selected_objects:
            if ob.type == 'MESH':
                ob.vertex_groups.clear()
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(
        OBJECT_OT_remove_vertex_groups.bl_idname,
        icon='TRASH'
    )

def register():
    bpy.utils.register_class(OBJECT_OT_remove_vertex_groups)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.utils.unregister_class(OBJECT_OT_remove_vertex_groups)


if __name__ == "__main__":
    register()
