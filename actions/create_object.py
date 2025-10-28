def execute_create_object(cmd):
    """Create any primitive object"""
    typ = cmd["type"]
    p = cmd.get("params", {})
    
    # Create any primitive type
    if typ == "cube":
        bpy.ops.mesh.primitive_cube_add(**p)
    elif typ == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(**p)
    elif typ == "uv_sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(**p)
    elif typ == "ico_sphere":
        bpy.ops.mesh.primitive_ico_sphere_add(**p)
    elif typ == "cone":
        bpy.ops.mesh.primitive_cone_add(**p)
    elif typ == "torus":
        bpy.ops.mesh.primitive_torus_add(**p)
    elif typ == "plane":
        bpy.ops.mesh.primitive_plane_add(**p)
    else:
        print(f"Error: Unsupported primitive type '{typ}'")
