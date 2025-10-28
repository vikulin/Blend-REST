import bpy

def execute_polygon_shape(cmd):
    """Create a custom polygon shape from vertices and faces safely"""
    
    params = cmd.get("params", {})
    vertices_raw = params.get("vertices", [])
    faces_raw = params.get("faces", [])
    location = params.get("location", [0, 0, 0])
    name = params.get("name", "PolygonShape")
    
    if not vertices_raw or not faces_raw:
        print("[Polygon Shape] Error: vertices and faces arrays are required")
        return False
    
    # --- Convert string arrays to proper lists ---
    try:
        vertices = [list(map(float, v.strip().split())) for v in vertices_raw]
        faces = [list(map(int, f.strip().split())) for f in faces_raw]
    except Exception as e:
        print(f"[Polygon Shape] Error converting vertices/faces: {e}")
        return False
    
    # Validate faces
    max_index = len(vertices) - 1
    for f in faces:
        if any(v > max_index or v < 0 for v in f):
            print(f"[Polygon Shape] Error: face {f} references invalid vertex index")
            return False
    
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
