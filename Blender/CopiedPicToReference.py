import bpy
import copykitten
import PIL.Image
import datetime
import tempfile, os
from mathutils import Vector


class PASTEIMAGE_OT_reference_from_clipboard(bpy.types.Operator):
    """Colle une image depuis le presse-papiers et crée une image de référence alignée sur la vue"""
    bl_idname = "view3d.paste_image_reference"
    bl_label = "Coller Image Référence (Copykitten)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            image_copiee = copykitten.paste_image()
        except Exception as e:
            self.report({'ERROR'}, f"Erreur lors du collage : {e}")
            return {'CANCELLED'}

        if not image_copiee:
            self.report({'ERROR'}, "Aucune image copiée depuis le presse-papiers.")
            return {'CANCELLED'}

        image_donnees_pixels, image_largeur, image_hauteur = image_copiee
        heure_actuelle = datetime.datetime.now()

        tempdir = tempfile.gettempdir()
        chemin_image_collee = os.path.join(
            tempdir,
            f"image_reference_{heure_actuelle:%Y-%m-%d_%H-%M-%S}.png"
        )

        if not isinstance(image_donnees_pixels, (bytes, bytearray)):
            image_donnees_pixels = bytes(image_donnees_pixels)

        image = PIL.Image.frombytes("RGBA", [image_largeur, image_hauteur], image_donnees_pixels)
        image.save(chemin_image_collee)

        # Crée une image Blender
        image_blender = bpy.data.images.load(chemin_image_collee)

        # Crée un empty de type image
        ref = bpy.data.objects.new("ImageRef", None)
        ref.empty_display_type = 'IMAGE'
        ref.data = None
        ref.empty_display_size = 5.0  # taille par défaut, ajustable
        ref.empty_image_offset = (0.0, 0.0)

        # Affecte l'image à l'empty
        ref.data = None
        ref.empty_display_type = 'IMAGE'
        ref.data = None
        ref.empty_image = image_blender
        ref.empty_image_show_perspective = True
        ref.empty_image_show_orthographic = True
        ref.empty_image_depth = 'FRONT'

        # Note : certaines propriétés (comme empty_image_use_alpha) ont été supprimées de l’API.
        # Blender gère la transparence automatiquement via le canal alpha de l’image.

        # Place l’empty selon la vue actuelle
        region_data = context.space_data.region_3d
        view_direction = region_data.view_rotation @ Vector((0.0, 0.0, -1.0))
        ref.location = region_data.view_location + view_direction * 10
        ref.rotation_euler = region_data.view_rotation.to_euler()

        # Ajoute à la scène
        context.collection.objects.link(ref)

        self.report({'INFO'}, f"Image de référence créée : {chemin_image_collee}")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(PASTEIMAGE_OT_reference_from_clipboard)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)


def unregister():
    bpy.utils.unregister_class(PASTEIMAGE_OT_reference_from_clipboard)
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)


def menu_func(self, context):
    self.layout.operator("view3d.paste_image_reference", icon='IMAGE_DATA')


if __name__ == "__main__":
    register()
