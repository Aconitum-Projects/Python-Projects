import bpy


#SCRIPT QUI MARCHE PAS :)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))


# --- CONFIG ---
body_name = "body"
armature_name = "Armature"
clothes_prefix = "Cloth_"

def debug_message(msg, title="Debug"):
    bpy.context.window_manager.popup_menu(
        lambda self, context: self.layout.label(text=msg),
        title=title,
        icon='INFO'
    )

body = bpy.data.objects.get(body_name)
armature = bpy.data.objects.get(armature_name)

if not body or not armature:
    debug_message(f"❌ Vérifie les noms de 'body_name' et 'armature_name'")
else:
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            debug_message(f"⛔ {obj.name} ignoré : pas un mesh")
            continue
        if obj == body:
            debug_message(f"⛔ {obj.name} ignoré : c'est le body")
            continue
        if clothes_prefix and not obj.name.startswith(clothes_prefix):
            debug_message(f"⛔ {obj.name} ignoré : ne commence pas par '{clothes_prefix}'")
            continue

        debug_message(f"👕 Préparation de {obj.name}...")

        # Parentage à l'armature si pas déjà fait
        if obj.parent != armature:
            obj.parent = armature
            obj.parent_type = 'ARMATURE'

        # Vérifie le modificateur Armature
        arm_mod = None
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                arm_mod = mod
                break
        if not arm_mod:
            arm_mod = obj.modifiers.new(name="Armature", type='ARMATURE')
        arm_mod.object = armature

        # Copie les vertex groups du body
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        body.select_set(True)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        bpy.ops.object.data_transfer(
            data_type='VGROUP_WEIGHTS',
            use_create=True,
            vert_mapping='NEAREST',    # transfert par vertex le plus proche
            layers_select_src='ALL',   # tous les vertex groups du body
            layers_select_dst='NAME'   # créer/correspondre aux noms des groupes
        )

        bpy.ops.object.mode_set(mode='OBJECT')

        debug_message(f"✅ {obj.name} prêt et parenté à l’armature !")

    debug_message("🎉 Tous les vêtements sont parentés et ont reçu le weight paint.", title="Fin")
