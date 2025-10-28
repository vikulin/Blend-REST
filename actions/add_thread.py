import bpy

def execute_add_thread(cmd):
    """Add thread using MACHIN3tools plugin"""
    bpy.ops.ed.undo_push(message="Original")
    # Add thread using MACHIN3tools plugin
    thread_params = cmd.get("params", {})
    target_object = thread_params.get("target")  # Object to apply thread to
    position = thread_params.get("position", [0, 0, 0])  # Position for cursor
    radius = thread_params.get("radius", 0.2)  # Radius of the thread
    segments = thread_params.get("segments", 32)  # Number of segments
    loops = thread_params.get("loops", 10)  # Number of loops/threads
    depth = thread_params.get("depth", 10)  # Depth as percentage of minor diameter
    fade = thread_params.get("fade", 15)  # Percentage of segments fading
    h1 = thread_params.get("h1", 0.2)  # Bottom Flank
    h2 = thread_params.get("h2", 0.2)  # Top Flank
    h3 = thread_params.get("h3", 0.05)  # Crest
    h4 = thread_params.get("h4", 0.05)  # Root
    flip = thread_params.get("flip", False)  # Flip thread direction
    
    # Get the target object
    obj = bpy.data.objects.get(target_object)
    if not obj:
        print(f"Error: Object '{target_object}' not found")
        return False
        
    # Position the 3D cursor
    bpy.context.scene.cursor.location = position
    
    # Use select_faces action to select side faces first
    bpy.ops.ed.undo_push(message="Selected side faces")
    
    # Create the thread using MACHIN3tools operator
    try:
        bpy.ops.machin3.add_thread(
            radius=radius,
            segments=segments,
            loops=loops,
            depth=depth,
            fade=fade,
            h1=h1,
            h2=h2,
            h3=h3,
            h4=h4,
            flip=flip
        )
        print(f"Thread created on '{target_object}' at position {position}")
    except Exception as e:
        print(f"Error adding thread: {e}")
        return False
    finally:
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.ed.undo_push(message="Added thread")
    return True
