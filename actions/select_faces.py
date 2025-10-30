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
    """Select faces based on multiple bisect planes"""
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
    
    # Find edges connecting ring vertices (bisect edges)
    ring_edges = []
    for edge in bm.edges:
        if all(vert in ring_vertices for vert in edge.verts):
            ring_edges.append(edge)
    
    print(f"Found {len(ring_edges)} ring edges")
    
    if not ring_edges:
        print("No ring edges found")
        return
    
    # Determine cylinder's main axis
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
    print(f"Cylinder main axis: {cylinder_axis}")
    
    # Group ring edges by their position along the cylinder axis
    # This separates different bisect operations
    edge_groups = {}
    for edge in ring_edges:
        vert1, vert2 = edge.verts
        center = (vert1.co + vert2.co) / 2
        position = center[cylinder_axis]
        
        # Group edges with similar positions (same bisect operation)
        group_key = round(position, 4)  # 4 decimal places precision
        if group_key not in edge_groups:
            edge_groups[group_key] = []
        edge_groups[group_key].append(edge)
    
    print(f"Found {len(edge_groups)} distinct ring groups")
    
    # Calculate average position for each ring group (bisect plane position)
    ring_positions = []
    for group_key, edges in edge_groups.items():
        positions = []
        for edge in edges:
            vert1, vert2 = edge.verts
            center = (vert1.co + vert2.co) / 2
            positions.append(center[cylinder_axis])
        
        avg_pos = sum(positions) / len(positions)
        ring_positions.append(avg_pos)
    
    # Sort ring positions along the cylinder axis
    ring_positions.sort()
    print(f"Ring positions along axis {cylinder_axis}: {ring_positions}")
    
    # Create face groups based on segments between ring positions
    face_groups = []
    
    if ring_positions:
        # Add group before first ring
        group_before = []
        for face in quad_faces:
            face_center = face.calc_center_median()
            if face_center[cylinder_axis] < ring_positions[0]:
                group_before.append(face.index)
        if group_before:
            face_groups.append(group_before)
        
        # Add groups between rings
        for i in range(len(ring_positions) - 1):
            group_between = []
            for face in quad_faces:
                face_center = face.calc_center_median()
                if ring_positions[i] <= face_center[cylinder_axis] < ring_positions[i + 1]:
                    group_between.append(face.index)
            if group_between:
                face_groups.append(group_between)
        
        # Add group after last ring
        group_after = []
        for face in quad_faces:
            face_center = face.calc_center_median()
            if face_center[cylinder_axis] >= ring_positions[-1]:
                group_after.append(face.index)
        if group_after:
            face_groups.append(group_after)
    else:
        # Fallback: single group if no rings found
        face_groups.append([face.index for face in quad_faces])
    
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
