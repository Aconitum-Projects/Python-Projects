bl_info = {
    "name": "Modular Character Switcher",
    "author": "Giu",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Modular",
    "description": "Switch between modular character parts using collections or sub-collections",
    "category": "Object",
}

import bpy
import random


# ---------------------------------------------------
# UTIL
# ---------------------------------------------------

def get_variants(entry):
    col = entry.collection
    if not col:
        return []

    if col.children:
        return list(col.children)

    return list(col.objects)


def hide_collection(col):
    for obj in col.all_objects:
        obj.hide_set(True)
        obj.hide_render = True


def show_collection(col):
    for obj in col.all_objects:
        obj.hide_set(False)
        obj.hide_render = False


def hide_object(obj):
    obj.hide_set(True)
    obj.hide_render = True


def show_object(obj):
    obj.hide_set(False)
    obj.hide_render = False


def update_visibility(self, context):
    variants = get_variants(self)
    if not variants:
        return

    for v in variants:
        if isinstance(v, bpy.types.Collection):
            hide_collection(v)
        else:
            hide_object(v)

    if self.selected_name:
        if self.collection and self.collection.children:
            col = bpy.data.collections.get(self.selected_name)
            if col:
                show_collection(col)
        else:
            obj = bpy.data.objects.get(self.selected_name)
            if obj:
                show_object(obj)


def enum_callback(self, context):
    variants = get_variants(self)
    return [(v.name, v.name, "") for v in variants]


def auto_init_selection(entry):
    variants = get_variants(entry)
    if variants:
        entry.selected_name = variants[0].name
        update_visibility(entry, bpy.context)


# ---------------------------------------------------
# PROPERTY GROUP
# ---------------------------------------------------

class MODULAR_PG_entry(bpy.types.PropertyGroup):

    def collection_update(self, context):
        auto_init_selection(self)

    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
        update=collection_update
    )

    selected_name: bpy.props.EnumProperty(
        name="Variant",
        items=enum_callback,
        update=update_visibility
    )


# ---------------------------------------------------
# OPERATORS
# ---------------------------------------------------

class MODULAR_OT_add(bpy.types.Operator):
    bl_idname = "modular.add_entry"
    bl_label = "Add Module"

    def execute(self, context):
        context.scene.modular_entries.add()
        return {'FINISHED'}


class MODULAR_OT_reset(bpy.types.Operator):
    bl_idname = "modular.reset_entries"
    bl_label = "Reset Modules"

    def execute(self, context):
        context.scene.modular_entries.clear()
        return {'FINISHED'}


class MODULAR_OT_next(bpy.types.Operator):
    bl_idname = "modular.next_variant"
    bl_label = "Next Variant"

    index: bpy.props.IntProperty()

    def execute(self, context):
        entry = context.scene.modular_entries[self.index]
        variants = get_variants(entry)
        if not variants:
            return {'FINISHED'}

        names = [v.name for v in variants]
        if entry.selected_name in names:
            i = names.index(entry.selected_name)
            entry.selected_name = names[(i + 1) % len(names)]
        return {'FINISHED'}


class MODULAR_OT_prev(bpy.types.Operator):
    bl_idname = "modular.prev_variant"
    bl_label = "Previous Variant"

    index: bpy.props.IntProperty()

    def execute(self, context):
        entry = context.scene.modular_entries[self.index]
        variants = get_variants(entry)
        if not variants:
            return {'FINISHED'}

        names = [v.name for v in variants]
        if entry.selected_name in names:
            i = names.index(entry.selected_name)
            entry.selected_name = names[(i - 1) % len(names)]
        return {'FINISHED'}


class MODULAR_OT_randomize(bpy.types.Operator):
    bl_idname = "modular.randomize"
    bl_label = "Randomize Character"

    def execute(self, context):
        for entry in context.scene.modular_entries:
            variants = get_variants(entry)
            if variants:
                entry.selected_name = random.choice(variants).name
        return {'FINISHED'}


# ---------------------------------------------------
# UI
# ---------------------------------------------------

class VIEW3D_PT_modular(bpy.types.Panel):
    bl_label = "Modular Character"
    bl_idname = "VIEW3D_PT_modular_character"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Modular"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row(align=True)
        row.operator("modular.add_entry", text="Add")
        row.operator("modular.reset_entries", text="Reset")

        layout.operator("modular.randomize", text="Randomize")

        for i, entry in enumerate(scene.modular_entries):
            box = layout.box()
            box.prop(entry, "collection")

            if entry.collection:
                box.prop(entry, "selected_name")

                row = box.row(align=True)
                prev = row.operator("modular.prev_variant", text="◀")
                prev.index = i
                next = row.operator("modular.next_variant", text="▶")
                next.index = i


# ---------------------------------------------------
# REGISTER
# ---------------------------------------------------

classes = (
    MODULAR_PG_entry,
    MODULAR_OT_add,
    MODULAR_OT_reset,
    MODULAR_OT_next,
    MODULAR_OT_prev,
    MODULAR_OT_randomize,
    VIEW3D_PT_modular,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.modular_entries = bpy.props.CollectionProperty(type=MODULAR_PG_entry)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.modular_entries


if __name__ == "__main__":
    register()