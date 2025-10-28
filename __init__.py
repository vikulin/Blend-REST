bl_info = {
    "name": "Blend-REST",
    "description": "REST API server for Blender automation",
    "author": "Vadym Vikulin",
    "version": (1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Tool Shelf > Blend-REST",
    "category": "Development",
}

import bpy
import json
import threading
import queue
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import action functions with proper Blender addon path handling
try:
    # First try relative imports (works when installed as addon)
    from .actions.create_object import execute_create_object
    from .actions.modify_object import execute_modify_object
    from .actions.boolean_difference import execute_boolean_difference
    from .actions.undo import execute_undo
    from .actions.redo import execute_redo
    from .actions.select_faces import execute_select_faces
    from .actions.add_thread import execute_add_thread
    from .actions.bisect_plane import execute_bisect_plane
    print("[Blend-REST] All action functions imported successfully via relative imports")
except ImportError as e:
    print(f"[Blend-REST] Relative imports failed: {e}")
    # Fallback: try absolute import (for development/testing)
    try:
        actions_dir = os.path.join(os.path.dirname(__file__), 'actions')
        if os.path.isdir(actions_dir) and actions_dir not in sys.path:
            sys.path.append(actions_dir)
        
        from actions.create_object import execute_create_object
        from actions.modify_object import execute_modify_object
        from actions.boolean_difference import execute_boolean_difference
        from actions.undo import execute_undo
        from actions.redo import execute_redo
        from actions.select_faces import execute_select_faces
        from actions.add_thread import execute_add_thread
        from actions.bisect_plane import execute_bisect_plane
        print("[Blend-REST] Using fallback import method")
    except ImportError as e:
        print(f"[Blend-REST] Critical: All import methods failed: {e}")

# Thread-safe command queue
command_queue = queue.Queue()


class BlenderRESTHandler:
    def __init__(self, queue):
        self.queue = queue

    def handle_request(self, command):
        """Handle REST API requests by adding to command queue"""
        self.queue.put(command)
        return {"status": "queued"}


class BlendRESTServer:
    def __init__(self):
        self.server = None
        self.handler = BlenderRESTHandler(command_queue)
        self.is_running = False

    def start_server(self, port=8000):
        if self.is_running:
            return {"status": "already running"}

        try:
            handler_ref = self.handler

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
                            result = handler_ref.handle_request(command)
                            self._send_json(result)
                        else:
                            self._send_json({"error": "Endpoint not found"}, 404)
                    except Exception as e:
                        self._send_json({"error": str(e)}, 500)

                def log_message(self, format, *args):
                    # prevent server from spamming Blender console
                    return

                def _send_json(self, data, code=200):
                    self.send_response(code)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode())

            self.server = HTTPServer(('127.0.0.1', port), CustomHTTPHandler)
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


class BLENDREST_OT_start_server(bpy.types.Operator):
    bl_idname = "blendrest.start_server"
    bl_label = "Start REST Server"

    def execute(self, context):
        global rest_server
        rest_server = BlendRESTServer()
        result = rest_server.start_server()
        self.report({'INFO'}, f"Server: {result['status']}")
        return {'FINISHED'}


class BLENDREST_OT_stop_server(bpy.types.Operator):
    bl_idname = "blendrest.stop_server"
    bl_label = "Stop REST Server"

    def execute(self, context):
        global rest_server
        if rest_server:
            result = rest_server.stop_server()
            self.report({'INFO'}, f"Server: {result['status']}")
        return {'FINISHED'}


class VIEW3D_PT_blend_rest(bpy.types.Panel):
    bl_label = "Blend-REST"
    bl_idname = "VIEW3D_PT_blend_rest"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Blend-REST"

    def draw(self, context):
        layout = self.layout
        layout.operator("blendrest.start_server")
        layout.operator("blendrest.stop_server")


def process_commands():
    while not command_queue.empty():
        cmd = command_queue.get()
        action = cmd.get("action")
        try:
            if action == "create_object":
                execute_create_object(cmd)
            elif action == "modify_object":
                execute_modify_object(cmd)
            elif action == "boolean_difference":
                execute_boolean_difference(cmd)
            elif action == "undo":
                execute_undo(cmd)
            elif action == "redo":
                execute_redo(cmd)
            elif action == "select_faces":
                execute_select_faces(cmd)
            elif action == "add_thread":
                execute_add_thread(cmd)
            elif action == "bisect_plane":
                execute_bisect_plane(cmd)
        except Exception as e:
            import traceback
            print(f"[Blend-REST] Error executing action '{action}': {e}")
            print(f"[Blend-REST] Traceback: {traceback.format_exc()}")

    return 0.1


rest_server = None


def register():
    bpy.utils.register_class(BLENDREST_OT_start_server)
    bpy.utils.register_class(BLENDREST_OT_stop_server)
    bpy.utils.register_class(VIEW3D_PT_blend_rest)

    if not bpy.app.timers.is_registered(process_commands):
        bpy.app.timers.register(process_commands)


def unregister():
    bpy.utils.unregister_class(BLENDREST_OT_start_server)
    bpy.utils.unregister_class(BLENDREST_OT_stop_server)
    bpy.utils.unregister_class(VIEW3D_PT_blend_rest)

    if rest_server:
        rest_server.stop_server()

    if bpy.app.timers.is_registered(process_commands):
        bpy.app.timers.unregister(process_commands)


if __name__ == "__main__":
    register()
