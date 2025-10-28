import bpy

def execute_modify_object(cmd):
    """Modify object properties"""
    obj_name = cmd.get("name")
    props = cmd.get("properties", {})
    obj = bpy.data.objects.get(obj_name)
    if obj:
        for k,v in props.items():
            setattr(obj, k, v)
