import bpy
import bmesh
import mathutils

def execute_select_faces(cmd):
    """Select specific faces on an object"""
    bpy.ops.ed.undo_push(message="Original")
    # Select specific faces on an object
    select_params = cmd.get("params", {})
    target_object = select_params.get("target")  # Object to select faces on
    side_type = select_params.get("side", "all")  # "external", "internal", or "all"
    faces_set_index = select_params.get("faces_set_index")  # Specific ring index to select

    # Get the target object
    obj = bpy.data.objects.get(target_object)
    if not obj:
        print(f"Error: Object '{target_object}' not found")
        return False

    # Ensure proper mode
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # Clear selection
    for face in bm.faces:
        face.select = False

    if faces_set_index is not None:
        select_faces_by_ring_criterion(bm, faces_set_index)
    else:
        # Default behavior
        for face in bm.faces:
            if len(face.verts) == 4:
                face.select = True
        
        if side_type in ["external", "internal"]:
            filter_faces_by_side(bm, obj, side_type)

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.ed.undo_push(message=f"Selected set {faces_set_index}" if faces_set_index is not None else f"Selected {side_type} faces")
    return True

def select_faces_by_ring_criterion(bm, set_index):
    """Select faces based on which side of bisect plane they're on"""
    # Ensure lookup tables are up to date
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    # Get all quad faces
    quad_faces = [face for face in bm.faces if len(face.verts) == 4]
    print(f"Found {len(quad_faces)} quad faces")
    
    if not quad_faces:
        print("No quad faces found - cannot perform ring selection")
        return
    
    # Find vertices that are part of rings (connected to 4 faces)
    ring_vertices = [vert for vert in bm.verts if len(vert.link_faces) == 4]
    print(f"Found {len(ring_vertices)} ring vertices")
    
    if not ring_vertices:
        print("No ring vertices found")
        return
    
    # Find edges connecting ring vertices (potential bisect edges)
    ring_edges = []
    for edge in bm.edges:
        if all(vert in ring_vertices for vert in edge.verts):
            ring_edges.append(edge)
    
    print(f"Found {len(ring_edges)} ring edges")
    
    if not ring_edges:
        print("No ring edges found")
        return
    
    # Calculate average position of all ring edges to find bisect plane
    edge_positions = []
    for edge in ring_edges:
        vert1, vert2 = edge.verts
        center = (vert1.co + vert2.co) / 2
        edge_positions.append(center)
    
    avg_bisect_pos = sum(edge_positions, mathutils.Vector()) / len(edge_positions)
    
    # Determine the correct bisect plane orientation
    # The bisect plane should be perpendicular to the cylinder's main axis
    # First, find the cylinder's main axis using all quad faces
    bbox_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    bbox_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
    
    for face in quad_faces:
        for vert in face.verts:
            bbox_min.x = min(bbox_min.x, vert.co.x)
            bbox_min.y = min(bbox_min.y, vert.co.y)
            bbox_min.z = min(bbox_min.z, vert.co.z)
            bbox_max.x = max(bbox_max.x, vert.co.x)
            bbox_max.y = max(bbox_max.y, vert.co.y)
            bbox_max.z = max(bbox_max.z, vert.co.z)
    
    bbox_size = bbox_max - bbox_min
    cylinder_axis = max(range(3), key=lambda i: bbox_size[i])
    
    # The bisect plane should be perpendicular to the cylinder's main axis
    # For a cylinder, the bisect plane normal should align with the cylinder axis
    main_axis = cylinder_axis
    
    print(f"Cylinder main axis: {cylinder_axis}, Bisect plane at {avg_bisect_pos} on axis {main_axis}")
    
    # Separate faces into two groups based on which side of plane they're on
    side_a_faces = []
    side_b_faces = []
    
    for face in quad_faces:
        face_center = face.calc_center_median()
        if face_center[main_axis] < avg_bisect_pos[main_axis]:
            side_a_faces.append(face.index)
        else:
            side_b_faces.append(face.index)
    
    # Create final face groups
    face_groups = []
    if side_a_faces:
        face_groups.append(side_a_faces)
    if side_b_faces:
        face_groups.append(side_b_faces)
    
    print(f"Created {len(face_groups)} face groups")
    for i, group in enumerate(face_groups):
        print(f"  Group {i}: {len(group)} faces")
    
    # Select the requested set
    if 0 <= set_index < len(face_groups):
        # Clear all selections first
        for face in bm.faces:
            face.select = False
        
        bm.faces.ensure_lookup_table()
        
        for face_idx in face_groups[set_index]:
            try:
                bm.faces[face_idx].select = True
            except IndexError:
                print(f"Warning: Face index {face_idx} not found in bmesh")
                continue
        
        print(f"Selected set {set_index} with {len(face_groups[set_index])} faces")
    else:
        print(f"Set index {set_index} out of range (0-{len(face_groups)-1})")

def filter_faces_by_side(bm, obj, side_type):
    """Filter faces based on external/internal criteria"""
    selected_faces = [face for face in bm.faces if face.select]
    
    for face in bm.faces:
        face.select = False
        
    for face in selected_faces:
        center = face.calc_center_median()
        vec_to_face = center - obj.location
        dot_product = face.normal.dot(vec_to_face)
        
        should_select = False
        if side_type == "external" and dot_product > 0:
            should_select = True
        elif side_type == "internal" and dot_product < 0:
            should_select = True
            
        face.select = should_select
