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
        
    # Ensure we're in object mode first to avoid any mode conflicts
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # Select object and enter edit mode
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Refresh mesh data to ensure we're working with current topology
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action='DESELECT')
    
    # Use bmesh to work with the mesh more reliably
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    # Clear any existing selections
    for face in bm.faces:
        face.select = False
    
    # Select faces based on side count (quads for cylinders)
    for face in bm.faces:
        if len(face.verts) == 4:  # Select quad faces
            face.select = True
    
    bmesh.update_edit_mesh(obj.data)
    
    if side_type in ["external", "internal"]:
        # Now filter based on external/internal using face normals
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        # Create a list of currently selected faces
        selected_faces = [face for face in bm.faces if face.select]
        
        # Deselect all first
        for face in bm.faces:
            face.select = False
        
        # Select only the faces that match the external/internal criteria
        for face in selected_faces:
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
