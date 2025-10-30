import bpy
import bmesh
import mathutils

def execute_bisect_plane(cmd):
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
    
    # Calculate cylinder axis using bounding box method (more reliable than face normals)
    # Get the bounding box of selected faces to determine cylinder orientation
    bbox_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    bbox_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
    
    for face in selected_faces:
        for vert in face.verts:
            bbox_min.x = min(bbox_min.x, vert.co.x)
            bbox_min.y = min(bbox_min.y, vert.co.y)
            bbox_min.z = min(bbox_min.z, vert.co.z)
            bbox_max.x = max(bbox_max.x, vert.co.x)
            bbox_max.y = max(bbox_max.y, vert.co.y)
            bbox_max.z = max(bbox_max.z, vert.co.z)
    
    # Calculate the dimensions of the bounding box
    bbox_size = bbox_max - bbox_min
    
    # Find the longest axis - this is likely the cylinder's main axis
    longest_axis_index = 0
    longest_axis_value = bbox_size[0]
    
    for i in range(1, 3):
        if bbox_size[i] > longest_axis_value:
            longest_axis_value = bbox_size[i]
            longest_axis_index = i
    
    # Create axis vector based on the longest bounding box dimension
    cylinder_axis = mathutils.Vector((0, 0, 0))
    cylinder_axis[longest_axis_index] = 1.0
    
    # Transform the axis to object space to ensure it's correctly oriented
    cylinder_axis = obj.matrix_world.inverted() @ cylinder_axis
    cylinder_axis.normalize()
    
    print(f"Using bounding box method: cylinder axis={cylinder_axis}, longest axis index={longest_axis_index}")
    
    # Apply factor offset along the cylinder axis
    # Positive factor moves toward one end, negative toward the other
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
