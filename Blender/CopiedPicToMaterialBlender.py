import bpy
import copykitten
import PIL.Image
import datetime
import tempfile, os


class PASTEIMAGE_OT_from_clipboard(bpy.types.Operator):
    """Colle une image depuis le presse-papiers et l’applique aux objets sélectionnés"""
    bl_idname = "object.paste_image_material"
    bl_label = "Coller Image (Copykitten)"
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
            f"image_collee_{heure_actuelle:%Y-%m-%d_%H-%M-%S}.png"
        )

        if not isinstance(image_donnees_pixels, (bytes, bytearray)):
            image_donnees_pixels = bytes(image_donnees_pixels)

        image = PIL.Image.frombytes("RGBA", [image_largeur, image_hauteur], image_donnees_pixels)
        image.save(chemin_image_collee)

        mat = bpy.data.materials.new("PastedMat")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        shader = nodes.new("ShaderNodeBsdfPrincipled")
        output = nodes.new("ShaderNodeOutputMaterial")
        tex = nodes.new("ShaderNodeTexImage")

        material_image = bpy.data.images.load(chemin_image_collee)
        tex.image = material_image

        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        links.new(tex.outputs["Color"], shader.inputs["Base Color"])

        for obj in context.selected_objects:
            if obj.type == "MESH":
                obj.data.materials.clear()
                obj.data.materials.append(mat)

        self.report({'INFO'}, f"Image collée : {chemin_image_collee}")
        return {'FINISHED'}


# Enregistrement
def register():
    bpy.utils.register_class(PASTEIMAGE_OT_from_clipboard)

def unregister():
    bpy.utils.unregister_class(PASTEIMAGE_OT_from_clipboard)

if __name__ == "__main__":
    register()

def menu_func(self, context):
    self.layout.operator("object.paste_image_material", icon='IMAGE_DATA')

# Ajout au menu clic droit dans la vue 3D
bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)
