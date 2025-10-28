bl_info = {
    "name": "Blend-REST",
    "description": "REST API server for Blender automation",
    "author": "Vadym Vikulin",
    "version": (1, 1, 3),
    "blender": (3, 6, 0),
    "location": "View3D > Tool Shelf > Blend-REST",
    "category": "Development",
}

import bpy
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import queue
import os
import sys
import importlib

# Thread-safe command queue
command_queue = queue.Queue()

# -----------------------------
# Action imports (safe)
# -----------------------------
action_modules = [
    'create_object',
    'modify_object', 
    'boolean_difference',
    'undo', 
    'redo', 
    'select_faces', 
    'add_thread', 
    'bisect_plane',
    'setup_scene',
    'polygon_shape'
]

def safe_import_actions():
    funcs = {}
    actions_dir = os.path.join(os.path.dirname(__file__), 'actions')
    if actions_dir not in sys.path:
        sys.path.append(actions_dir)

    for module_name in action_modules:
        try:
            mod = importlib.import_module(module_name)
            func_name = f"execute_{module_name}"
            funcs[module_name] = getattr(mod, func_name)
            print(f"[Blend-REST] Imported {func_name}")
        except Exception as e:
            print(f"[Blend-REST] Warning: could not import {module_name}: {e}")
            # fallback dummy function
            funcs[module_name] = lambda cmd, name=module_name: print(f"[Blend-REST] Skipped {name}: {cmd}")
    return funcs

action_funcs = safe_import_actions()

# -----------------------------
# Blender REST handler
# -----------------------------
class BlenderRESTHandler:
    def __init__(self, queue):
        self.queue = queue

    def handle_request(self, command):
        self.queue.put(command)
        return {"status": "queued"}

# -----------------------------
# REST server
# -----------------------------
class BlendRESTServer:
    def __init__(self):
        self.server = None
        self.handler = BlenderRESTHandler(command_queue)
        self.is_running = False

    def start_server(self, port=8000):
        if self.is_running:
            return {"status": "already running"}
        try:
            self.server = HTTPServer(('127.0.0.1', port), self._create_http_handler())
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.is_running = True
            print(f"[Blend-REST] Server started on port {port}")
            return {"status": "started", "port": port}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def stop_server(self):
        if self.server:
            self.server.shutdown()
            self.server = None
            self.is_running = False
            print("[Blend-REST] Server stopped")
        return {"status": "stopped"}

    def _create_http_handler(self):
        handler_instance = self.handler  # capture for closure

        class CustomHTTPHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    if self.path == '/v1/models':
                        objects = [{
                            "name": obj.name,
                            "type": obj.type,
                            "location": list(obj.location),
                            "rotation": list(obj.rotation_euler),
                            "dimensions": list(obj.dimensions)
                        } for obj in bpy.data.objects]
                        self._send_json(objects)
                    elif self.path == '/v1/status':
                        self._send_json({"status": "ready", "objects": len(bpy.data.objects)})
                    else:
                        self._send_json({"error": "Endpoint not found"}, 404)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)

            def do_POST(self):
                try:
                    if self.path == '/v1/commands':
                        content_length = int(self.headers.get('Content-Length', 0))
                        post_data = self.rfile.read(content_length)
                        command = json.loads(post_data.decode())
                        print(f"[Blend-REST] Received command: {command}")
                        result = handler_instance.handle_request(command)
                        self._send_json(result)
                    else:
                        self._send_json({"error": "Endpoint not found"}, 404)
                except Exception as e:
                    import traceback
                    print(f"[Blend-REST] POST error: {e}")
                    print(f"[Blend-REST] POST traceback: {traceback.format_exc()}")
                    self._send_json({"error": str(e)}, 500)

            def log_message(self, format, *args):
                # suppress default HTTP server logging
                return

            def _send_json(self, data, code=200):
                self.send_response(code)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

        return CustomHTTPHandler

# -----------------------------
# Blender operators
# -----------------------------
class StartServerOperator(bpy.types.Operator):
    bl_idname = "blend_rest.start_server"
    bl_label = "Start REST Server"

    def execute(self, context):
        global rest_server
        rest_server = BlendRESTServer()
        result = rest_server.start_server()
        self.report({'INFO'}, f"Server: {result['status']}")
        return {'FINISHED'}

class StopServerOperator(bpy.types.Operator):
    bl_idname = "blend_rest.stop_server"
    bl_label = "Stop REST Server"

    def execute(self, context):
        global rest_server
        if rest_server:
            result = rest_server.stop_server()
            self.report({'INFO'}, f"Server: {result['status']}")
        return {'FINISHED'}

# -----------------------------
# Blender panel
# -----------------------------
class BlendRESTPanel(bpy.types.Panel):
    bl_label = "Blend-REST"
    bl_idname = "VIEW3D_PT_blend_rest"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Blend-REST"

    def draw(self, context):
        layout = self.layout
        layout.operator("blend_rest.start_server")
        layout.operator("blend_rest.stop_server")

# -----------------------------
# Timer: process queued commands
# -----------------------------
def process_commands():
    while not command_queue.empty():
        cmd = command_queue.get()
        action = cmd.get("action")
        func = action_funcs.get(action, lambda c: print(f"[Blend-REST] Unknown action: {c}"))
        try:
            func(cmd)
        except Exception as e:
            import traceback
            print(f"[Blend-REST] Error executing action '{action}': {e}")
            print(f"[Blend-REST] Traceback: {traceback.format_exc()}")
    return 0.1

# -----------------------------
# Global server instance
# -----------------------------
rest_server = None

# -----------------------------
# Registration
# -----------------------------
def register():
    bpy.utils.register_class(StartServerOperator)
    bpy.utils.register_class(StopServerOperator)
    bpy.utils.register_class(BlendRESTPanel)
    if not bpy.app.timers.is_registered(process_commands):
        bpy.app.timers.register(process_commands)

def unregister():
    bpy.utils.unregister_class(StartServerOperator)
    bpy.utils.unregister_class(StopServerOperator)
    bpy.utils.unregister_class(BlendRESTPanel)
    if rest_server:
        rest_server.stop_server()
    if bpy.app.timers.is_registered(process_commands):
        bpy.app.timers.unregister(process_commands)

if __name__ == "__main__":
    register()
