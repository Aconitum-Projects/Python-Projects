bl_info = {
    "name": "Custom Incremental Rename (_00, _01, etc.)",
    "author": "Giu + ChatGPT",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "Right Click > Custom Rename (_00)",
    "description": "Renomme uniquement les objets sélectionnés selon le format _00, _01, etc.",
    "category": "Object",
}

import bpy

def rename_selected_objects_custom(context):
    selected_objects = context.selected_objects
    for i, obj in enumerate(selected_objects):
        base_name = obj.name.split('.')[0].split('_')[0]
        obj.name = f"{base_name}_{i:02d}"

class OBJECT_OT_custom_rename(bpy.types.Operator):
    bl_idname = "object.custom_incremental_rename"
    bl_label = "Custom Rename (_00)"
    bl_description = "Renomme uniquement les objets sélectionnés selon le format _00, _01, etc."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        rename_selected_objects_custom(context)
        self.report({'INFO'}, "Renommage des objets sélectionnés terminé.")
        return {'FINISHED'}

# Ajout au menu contextuel du clic droit
def menu_func(self, context):
    self.layout.separator()
    self.layout.operator(OBJECT_OT_custom_rename.bl_idname, icon="OUTLINER_OB_EMPTY")

def register():
    bpy.utils.register_class(OBJECT_OT_custom_rename)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_custom_rename)
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)

if __name__ == "__main__":
    register()
