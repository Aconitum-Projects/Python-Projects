bl_info = {
    "name":        "FBX Individual Exporter",
    "author":      "Giu & Claude",
    "version":     (1, 2, 0),
    "blender":     (3, 0, 0),
    "location":    "Vue 3D > Sidebar (N) > FBX Exporter  |  Clic droit > FBX Individual Exporter",
    "description": "Exporte chaque mesh sélectionné en FBX séparé avec rig, préfixe et suffixe",
    "category":    "Import-Export",
}

import bpy
import os
from bpy.props import StringProperty, BoolProperty, FloatProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup


# ─────────────────────────────────────────────
#  Propriétés stockées sur la scène (persistent)
# ─────────────────────────────────────────────

class FBXExporterProps(PropertyGroup):

    output_dir: StringProperty(
        name        = "Dossier",
        description = "Dossier de destination des FBX",
        default     = "C:/Exports/Fish",
        subtype     = 'DIR_PATH',
    )
    prefix: StringProperty(
        name    = "Préfixe",
        default = "SKM_",
    )
    suffix: StringProperty(
        name    = "Suffixe",
        default = "",
    )
    apply_scale: BoolProperty(
        name    = "Appliquer l'échelle",
        default = True,
    )
    fbx_scale: FloatProperty(
        name    = "Échelle",
        default = 1.0,
        min     = 0.001,
        max     = 1000.0,
    )
    bake_anim: BoolProperty(
        name    = "Exporter les animations",
        default = False,
    )


# ─────────────────────────────────────────────
#  Opérateur d'export
# ─────────────────────────────────────────────

class OBJECT_OT_fbx_individual_export(Operator):
    bl_idname      = "object.fbx_individual_export"
    bl_label       = "Exporter les FBX"
    bl_description = "Exporte chaque mesh sélectionné en FBX séparé avec le rig"
    bl_options     = {'REGISTER', 'UNDO'}

    def get_armature(self, meshes):
        for obj in meshes:
            if obj.parent and obj.parent.type == 'ARMATURE':
                return obj.parent
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                return obj
        return None

    def execute(self, context):
        props  = context.scene.fbx_exporter_props
        meshes = [o for o in context.selected_objects if o.type == 'MESH']

        if not meshes:
            self.report({'ERROR'}, "Aucun mesh sélectionné !")
            return {'CANCELLED'}

        armature = self.get_armature(meshes)
        if armature is None:
            self.report({'ERROR'}, "Aucune armature trouvée dans la scène !")
            return {'CANCELLED'}

        output_dir = bpy.path.abspath(props.output_dir)
        os.makedirs(output_dir, exist_ok=True)

        exported = []

        for mesh in meshes:
            final_name = f"{props.prefix}{mesh.name}{props.suffix}"
            filepath   = os.path.join(output_dir, final_name + ".fbx")

            bpy.ops.object.select_all(action='DESELECT')
            mesh.select_set(True)
            armature.select_set(True)
            context.view_layer.objects.active = mesh

            bpy.ops.export_scene.fbx(
                filepath                 = filepath,
                use_selection            = True,
                object_types             = {'ARMATURE', 'MESH'},
                apply_scale_options      = 'FBX_SCALE_ALL' if props.apply_scale else 'FBX_SCALE_NONE',
                global_scale             = props.fbx_scale,
                axis_forward             = '-Z',
                axis_up                  = 'Y',
                bake_anim                = props.bake_anim,
                add_leaf_bones           = False,
                primary_bone_axis        = 'Y',
                secondary_bone_axis      = 'X',
                use_mesh_modifiers       = True,
                mesh_smooth_type         = 'OFF',
                use_armature_deform_only = True,
            )
            exported.append(final_name + ".fbx")

        # Remet la sélection initiale
        bpy.ops.object.select_all(action='DESELECT')
        for mesh in meshes:
            mesh.select_set(True)

        self.report({'INFO'}, f"✅ {len(exported)} FBX exporté(s) dans {output_dir}")
        return {'FINISHED'}


# ─────────────────────────────────────────────
#  Panneau Sidebar (touche N)
# ─────────────────────────────────────────────

class VIEW3D_PT_fbx_exporter(Panel):
    bl_label       = "FBX Exporter"
    bl_idname      = "VIEW3D_PT_fbx_exporter"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "FBX Export"

    def draw(self, context):
        layout = self.layout
        props  = context.scene.fbx_exporter_props
        meshes = [o for o in context.selected_objects if o.type == 'MESH']

        # Info sélection
        box = layout.box()
        icon = 'CHECKMARK' if meshes else 'ERROR'
        box.label(text=f"{len(meshes)} mesh(es) sélectionné(s)", icon=icon)

        layout.separator()

        # Dossier
        layout.label(text="Dossier de sortie :", icon='FILE_FOLDER')
        layout.prop(props, "output_dir", text="")

        layout.separator()

        # Nommage
        layout.label(text="Nommage :", icon='SORTALPHA')
        row = layout.row(align=True)
        row.prop(props, "prefix", text="Préfixe")
        row.prop(props, "suffix", text="Suffixe")

        # Aperçu
        if meshes:
            box2 = layout.box()
            box2.label(text=f"→ {props.prefix}{meshes[0].name}{props.suffix}.fbx", icon='INFO')

        layout.separator()

        # Options
        layout.label(text="Options :", icon='SETTINGS')
        row2 = layout.row()
        row2.prop(props, "apply_scale")
        row2.prop(props, "fbx_scale")
        layout.prop(props, "bake_anim")

        layout.separator()

        # Bouton Export
        col = layout.column()
        col.scale_y = 2.0
        col.enabled = len(meshes) > 0
        col.operator(
            OBJECT_OT_fbx_individual_export.bl_idname,
            text = f"EXPORTER {len(meshes)} FBX",
            icon = "EXPORT",
        )


# ─────────────────────────────────────────────
#  Menu clic droit (raccourci rapide)
# ─────────────────────────────────────────────

def menu_func(self, context):
    if any(o.type == 'MESH' for o in context.selected_objects):
        self.layout.separator()
        self.layout.operator(
            OBJECT_OT_fbx_individual_export.bl_idname,
            text = "FBX Individual Exporter",
            icon = "EXPORT",
        )


# ─────────────────────────────────────────────
#  Register / Unregister
# ─────────────────────────────────────────────

classes = [
    FBXExporterProps,
    OBJECT_OT_fbx_individual_export,
    VIEW3D_PT_fbx_exporter,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fbx_exporter_props = PointerProperty(type=FBXExporterProps)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.fbx_exporter_props
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)

if __name__ == "__main__":
    register()