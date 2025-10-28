def execute_bisect_plane(cmd):
    import mathutils
    """Perform bisect plane operation assuming faces are already selected"""
    # Perform bisect plane operation assuming faces are already selected
    bisect_params = cmd.get("params", {})
    target_object = bisect_params.get("target")  # Object to bisect
    factor = bisect_params.get("factor", 0.0)   # Offset along cylinder axis
    
    # Get the target object
    obj = bpy.data.objects.get(target_object)
    if not obj:
        print(f"Error: Object '{target_object}' not found")
        return False
    
    # Create BMesh from edit mesh
    bm = bmesh.from_edit_mesh(obj.data)
    
    # Get selected faces (assumes selection was already made via select_faces)
    selected_faces = [f for f in bm.faces if f.select]
    
    if not selected_faces:
        print("Error: No faces selected for1.0 bisect operation")
        bpy.ops.object.mode_set(mode='OBJECT')
        return False
    
    # Debug output: show selected faces
    print(f"Number of selected faces: {len(selected_faces)}")
    for i, face in enumerate(selected_faces):
        print(f"Face {i} center: {face.calc_center_median()}, area: {face.calc_area()}")
    
    # Calculate weighted center of selected faces
    total_area = 0.0
    weighted_center = mathutils.Vector((0, 0, 0))
    
    for face in selected_faces:
        face_center = face.calc_center_median()
        face_area = face.calc_area()
        weighted_center += face_center * face_area
        total_area += face_area
    
    if total_area > 0:
        plane_co = weighted_center / total_area
    else:
        plane_co = selected_faces[0].calc_center_median()
    
    # Debug output: show weighted center calculation
    print(f"Weighted center calculation: total_area={total_area}, weighted_center={weighted_center}, plane_co={plane_co}")
    
    # Calculate the proper perpendicular direction for cylindrical geometry
    # Collect all face normals
    normals = [face.normal for face in selected_faces]
    print(f"Collected {len(normals)} face normals")
    
    # Find two face normals with approximately 90 degree angle
    best_pair = None
    best_angle = float('inf')  # Looking for dot product closest to 0
    
    for i in range(len(normals)):
        for j in range(i + 1, len(normals)):
            dot_product = abs(normals[i].dot(normals[j]))
            if dot_product < best_angle:
                best_angle = dot_product
                best_pair = (normals[i], normals[j])
    
    if best_pair and best_angle < 0.3:  # ~90 degree angle (dot < 0.3)
        # Calculate cross product to get cylinder axis (perpendicular to both normals)
        cylinder_axis = best_pair[0].cross(best_pair[1]).normalized()
        print(f"Using cross product method: best_angle={best_angle}, cylinder_axis={cylinder_axis}")
    else:
        # Fallback: find vector most orthogonal to all normals
        best_axis = None
        min_max_dot = float('inf')
        
        candidates = [
            mathutils.Vector((1, 0, 0)),
            mathutils.Vector((0, 1, 0)), 
            mathutils.Vector((0, 0, 1)),
            mathutils.Vector((-1, 0, 0)),
            mathutils.Vector((0, -1, 0)),
            mathutils.Vector((0, 0, -1))
        ]
        
        for candidate in candidates:
            max_dot = max(abs(candidate.dot(normal)) for normal in normals)
            if max_dot < min_max_dot:
                min_max_dot = max_dot
                best_axis = candidate
        
        cylinder_axis = best_axis
        print(f"Using fallback method: min_max_dot={min_max_dot}, cylinder_axis={cylinder_axis}")
    
    # Apply factor offset along the cylinder axis
    plane_co = plane_co + cylinder_axis * factor
    print(f"Final plane position with offset: plane_co={plane_co}")
    
    # Perform bisect operation
    try:
        bpy.ops.mesh.bisect(
            plane_co=plane_co,
            plane_no=cylinder_axis,
            use_fill=False,
            clear_inner=False,
            clear_outer=False,
            threshold=0.0001
        )
        print(f"Bisect plane applied to '{target_object}' at position {plane_co} with offset {factor}")
    except Exception as e:
        print(f"Error applying bisect: {e}")
        return False
    finally:
        # Return to object mode
        print("done")
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.ed.undo_push(message="Bisect plane applied")
    return True
