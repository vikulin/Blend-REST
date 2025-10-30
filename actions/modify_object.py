import bpy

def execute_modify_object(cmd):
    """Modify object properties"""
    params = cmd.get("params", {})
    obj_name = params.get("target")
    props = params.get("properties", {})
    obj = bpy.data.objects.get(obj_name)
    if obj:
        for k,v in props.items():
            setattr(obj, k, v)
