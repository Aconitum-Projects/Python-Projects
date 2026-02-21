bl_info = {
    "name": "Rename Data to ObjectNameShape",
    "author": "Giu + GPT",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "Right-click > Rename Data to Shape",
    "description": "Renomme le data block de chaque objet sélectionné avec le nom de l’objet + 'Shape' (duplique le mesh si partagé)",
    "category": "Object",
}

import bpy


class OBJECT_OT_rename_data_shape(bpy.types.Operator):
    bl_idname = "object.rename_data_shape"
    bl_label = "Rename Data to Shape"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0

        for obj in context.selected_objects:
            # Ignore objects without data (empties, lights, etc.)
            if not hasattr(obj, "data") or obj.data is None:
                continue

            # Make data unique if shared
            if obj.data.users > 1:
                obj.data = obj.data.copy()

            obj.data.name = f"{obj.name}Shape"
            count += 1

        self.report({'INFO'}, f"Renamed {count} data blocks.")
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(
        OBJECT_OT_rename_data_shape.bl_idname,
        icon="OUTLINER_DATA_MESH"
    )


def register():
    bpy.utils.register_class(OBJECT_OT_rename_data_shape)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.utils.unregister_class(OBJECT_OT_rename_data_shape)


if __name__ == "__main__":
    register()
