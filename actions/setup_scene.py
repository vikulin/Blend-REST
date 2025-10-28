import bpy

def execute_setup_scene(cmd):
    """Setup Blender scene for small-scale modeling (0-300 mm)"""
    
    params = cmd.get("params", {})
    unit_scale = params.get("unit_scale", 0.001)    # 1 BU = 1 mm
    clip_start = params.get("clip_start", 0.1)      # 0.1 mm
    clip_end = params.get("clip_end", 10000)        # 10 m, enough for small objects
    grid_scale = params.get("grid_scale", 0.001)    # grid step 1 mm
    
    # --- 1. Set scene units to millimeters ---
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = unit_scale
    scene.unit_settings.length_unit = 'MILLIMETERS'

    print(f"[Setup Scene] Units set: 1 Blender Unit = {1/unit_scale} mm")

    # --- 2. Adjust 3D viewports safely ---
    found_viewport = False
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                found_viewport = True
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # Set viewport clipping and grid
                        space.clip_start = clip_start
                        space.clip_end = clip_end
                        space.overlay.grid_scale = grid_scale
                        print(f"[Setup Scene] Updated VIEW_3D area: clip={clip_start}-{clip_end}, grid={grid_scale}")

    if not found_viewport:
        print("[Setup Scene] ⚠ No VIEW_3D area found — skipped viewport adjustments.")

    # --- 3. Adjust camera if present ---
    if scene.camera:
        cam = scene.camera.data
        cam.clip_start = clip_start
        cam.clip_end = clip_end
        print(f"[Setup Scene] Camera '{scene.camera.name}' clip range set: {clip_start}-{clip_end}")

    print("[Setup Scene] Scene setup complete for small-scale modeling.")
    return True
