import bpy
import bmesh

def execute_select_faces(cmd):
    """Select specific faces on an object"""
    bpy.ops.ed.undo_push(message="Original")
    # Select specific faces on an object
    select_params = cmd.get("params", {})
    target_object = select_params.get("target")  # Object to select faces on
    side_type = select_params.get("side", "all")  # "external", "internal", or "all"
    
    # Get the target object
    obj = bpy.data.objects.get(target_object)
    if not obj:
        print(f"Error: Object '{target_object}' not found")
        return False
        
    # Select object and enter edit mode
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    bpy.ops.mesh.select_mode(type="FACE")
    # Default: select all quad faces (side faces only)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_face_by_sides(number=4, type='EQUAL')  # Select only quads

    if side_type in ["external", "internal"]:
        # Now filter based on external/internal using face normals
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        # Deselect all first, then selectively re-select based on normal direction
        for face in bm.faces:
            if face.select:  # Only process currently selected faces (side faces)
                # Calculate face center
                center = face.calc_center_median()
                
                # Calculate vector from object origin to face center
                vec_to_face = center - obj.location
                
                # Dot product between face normal and vector to face center
                dot_product = face.normal.dot(vec_to_face)
                
                # Determine if this face should be selected based on side_type
                should_select = False
                if side_type == "external" and dot_product > 0:
                    should_select = True
                elif side_type == "internal" and dot_product < 0:
                    should_select = True
                
                face.select = should_select
        
        bmesh.update_edit_mesh(obj.data)
    bpy.ops.ed.undo_push(message=f"Selected {side_type} faces")
    return True
