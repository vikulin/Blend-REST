import bpy

def execute_boolean_difference(cmd):
    """Perform boolean difference operation with any primitive cutter"""
    bpy.ops.ed.undo_push(message="Original")
    # Create a boolean difference operation
    target_name = cmd.get("target")
    cutter_params = cmd.get("cutter", {})
    
    # Get the target object
    target_obj = bpy.data.objects.get(target_name)
    if not target_obj:
        return False
        
    # Create cutter object with any primitive type
    cutter_type = cutter_params.get("type", "cylinder")
    cutter_location = cutter_params.get("location", [0, 0, 0])
    cutter_rotation = cutter_params.get("rotation", [0, 0, 0])  # Euler angles in radians
    
    # Get all parameters excluding type, location, and rotation
    cutter_props = {k: v for k, v in cutter_params.items() if k not in ['type', 'location', 'rotation']}
    
    # Create cutter primitive based on type
    if cutter_type == "cube":
        bpy.ops.mesh.primitive_cube_add(location=cutter_location, **cutter_props)
    elif cutter_type == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(location=cutter_location, **cutter_props)
    elif cutter_type == "uv_sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(location=cutter_location, **cutter_props)
    elif cutter_type == "ico_sphere":
        bpy.ops.mesh.primitive_ico_sphere_add(location=cutter_location, **cutter_props)
    elif cutter_type == "cone":
        bpy.ops.mesh.primitive_cone_add(location=cutter_location, **cutter_props)
    elif cutter_type == "torus":
        bpy.ops.mesh.primitive_torus_add(location=cutter_location, **cutter_props)
    elif cutter_type == "plane":
        bpy.ops.mesh.primitive_plane_add(location=cutter_location, **cutter_props)
    else:
        print(f"Error: Unsupported primitive type '{cutter_type}'")
        return False
        
    cutter_obj = bpy.context.active_object
    cutter_obj.name = "BooleanCutter"
    
    # Apply rotation to cutter object (if specified)
    if cutter_rotation != [0, 0, 0]:
        cutter_obj.rotation_euler = cutter_rotation
    
    # Apply boolean modifier to target object
    bool_mod = target_obj.modifiers.new(name="BooleanDifference", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutter_obj
    
    # Apply the modifier
    bpy.context.view_layer.objects.active = target_obj
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    
    # Delete the cutter object
    bpy.data.objects.remove(cutter_obj, do_unlink=True)

    bpy.ops.ed.undo_push(message="Boolean difference created")
    return True
