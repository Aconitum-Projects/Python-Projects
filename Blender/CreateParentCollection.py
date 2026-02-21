bl_info = {
    "name": "Create Parent Collection (Smart)",
    "author": "Giu",
    "version": (1, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Right Click (Object Context Menu)",
    "description": "Create parent collections depending on selection count",
    "category": "Object",
}

import bpy
import os


class OBJECT_OT_create_parent_collection(bpy.types.Operator):
    bl_idname = "object.create_parent_collection"
    bl_label = "Create Parent Collection"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.EnumProperty(
        name="Multi-Object Mode",
        items=[
            ('GROUP', "Group in one collection", "Group all objects in one collection"),
            ('INDIVIDUAL', "One collection per object", "Create one collection per object"),
        ],
        default='GROUP'
    )

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'OBJECT'
            and context.selected_objects
        )

    def create_and_link_collection(self, name, objects, scene_collection):
        if name in bpy.data.collections:
            collection = bpy.data.collections[name]
        else:
            collection = bpy.data.collections.new(name)
            scene_collection.children.link(collection)

        for obj in objects:
            for col in obj.users_collection:
                col.objects.unlink(obj)
            collection.objects.link(obj)

    def execute(self, context):
        selected = context.selected_objects
        scene_collection = context.scene.collection

        # ─────────────
        # SINGLE OBJECT
        # ─────────────
        if len(selected) == 1:
            obj = selected[0]
            self.create_and_link_collection(
                obj.name,
                [obj],
                scene_collection
            )
            return {'FINISHED'}

        # ─────────────
        # MULTI OBJECTS
        # ─────────────
        if self.mode == 'GROUP':
            blend_name = os.path.splitext(
                os.path.basename(bpy.data.filepath)
            )[0] or "Collection"

            self.create_and_link_collection(
                blend_name,
                selected,
                scene_collection
            )

        elif self.mode == 'INDIVIDUAL':
            for obj in selected:
                self.create_and_link_collection(
                    obj.name,
                    [obj],
                    scene_collection
                )

        return {'FINISHED'}

    def draw(self, context):
        if len(context.selected_objects) > 1:
            layout = self.layout
            layout.prop(self, "mode", expand=True)


def menu_func(self, context):
    self.layout.separator()
    self.layout.operator(
        OBJECT_OT_create_parent_collection.bl_idname,
        icon='OUTLINER_COLLECTION'
    )


def register():
    bpy.utils.register_class(OBJECT_OT_create_parent_collection)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.utils.unregister_class(OBJECT_OT_create_parent_collection)


if __name__ == "__main__":
    register()
