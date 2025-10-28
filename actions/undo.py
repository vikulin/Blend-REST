import bpy

def execute_undo(cmd):
    """Perform undo operation"""
    # Use Blender's built-in undo functionality (equivalent to Ctrl+Z)
    bpy.ops.ed.undo()
    return True
