import bpy

def execute_polygon_shape(cmd):
    """Create a custom polygon shape from vertices and faces safely"""
    
    params = cmd.get("params", {})
    vertices = params.get("vertices", [])
    faces = params.get("faces", [])
    location = params.get("location", [0, 0, 0])
    name = params.get("name", "PolygonShape")
    
    if not vertices or not faces:
        print("[Polygon Shape] Error: vertices and faces arrays are required")
        return False

    
    # Validate and normalize faces format
    processed_faces = []
    max_index = len(vertices) - 1
    
    # Check if faces is a single flat list of vertex indices
    if all(isinstance(f, int) for f in faces):
        # Convert flat list to a single face containing all vertices
        processed_faces = [faces]
    else:
        # Faces is already in correct format: list of face lists
        processed_faces = faces
    
    # Validate each face
    for i, face in enumerate(processed_faces):
        if not isinstance(face, (list, tuple)):
            print(f"[Polygon Shape] Error: face {i} must be a list/tuple of vertex indices")
            return False
        if any(v > max_index or v < 0 for v in face):
            print(f"[Polygon Shape] Error: face {i} references invalid vertex index")
            return False
    
    faces = processed_faces
    
    # Create mesh and object
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    
    # Link object safely
    collection = bpy.context.collection if bpy.context.collection else bpy.data.collections.new("Collection")
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    
    # Ensure object mode
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # Clear selection and set location
    bpy.ops.object.select_all(action='DESELECT')
    obj.location = location
    
    # Create mesh safely
    try:
        mesh.from_pydata(vertices, [], faces)
        mesh.update(calc_edges=True)
    except Exception as e:
        print(f"[Polygon Shape] Failed to create mesh: {e}")
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(mesh)
        return False
    
    # Select and activate
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    print(f"[Polygon Shape] Created '{name}' with {len(vertices)} vertices and {len(faces)} faces")
    return True
