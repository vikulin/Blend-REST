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
from http.server import HTTPServer, BaseHTTPRequestHandler
import queue
import os
import sys
import importlib

# Global bpy reference for action modules
global_bpy = bpy

def inject_bpy_to_actions():
    """Inject bpy module into action modules"""
    action_modules = [
        'create_object', 'modify_object', 'boolean_difference',
        'undo', 'redo', 'select_faces', 'add_thread', 'bisect_plane'
    ]
    
    for module_name in action_modules:
        try:
            module = importlib.import_module(f".actions.{module_name}", package=__name__)
            module.bpy = global_bpy
        except Exception as e:
            print(f"[Blend-REST] Failed to inject bpy into {module_name}: {e}")

# Import action functions
try:
    from .actions.create_object import execute_create_object
    from .actions.modify_object import execute_modify_object
    from .actions.boolean_difference import execute_boolean_difference
    from .actions.undo import execute_undo
    from .actions.redo import execute_redo
    from .actions.select_faces import execute_select_faces
    from .actions.add_thread import execute_add_thread
    from .actions.bisect_plane import execute_bisect_plane
    print("[Blend-REST] All action functions imported successfully")
    
    # Inject bpy into action modules
    inject_bpy_to_actions()
    
except ImportError as e:
    print(f"[Blend-REST] Import failed: {e}")

# Thread-safe command queue
command_queue = queue.Queue()

class BlenderRESTHandler:
    def __init__(self, queue):
        self.queue = queue
    
    def handle_request(self, command):
        """Handle REST API requests by adding to command queue"""
        self.queue.put(command)
        return {"status": "queued"}

# Server class for Blender integration
class BlendRESTServer:
    def __init__(self):
        self.server = None
        self.handler = BlenderRESTHandler(command_queue)
        self.is_running = False
    
    def start_server(self, port=8000):
        """Start the REST server"""
        if self.is_running:
            return {"status": "already running"}
        
        try:
            self.server = HTTPServer(('localhost', port), self._create_http_handler())
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.is_running = True
            return {"status": "started", "port": port}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def stop_server(self):
        """Stop the REST server"""
        if self.server:
            self.server.shutdown()
            self.server = None
            self.is_running = False
        return {"status": "stopped"}
    
    def _create_http_handler(self):
        """Create HTTP handler class"""
        handler = self.handler
        
        class CustomHTTPHandler(BaseHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.handler = handler
            
            def do_GET(self):
                """Handle GET requests"""
                try:
                    if self.path == '/v1/models':
                        # Get all objects in the scene
                        objects = []
                        for obj in bpy.data.objects:
                            objects.append({
                                "name": obj.name,
                                "type": obj.type,
                                "location": list(obj.location),
                                "rotation": list(obj.rotation_euler),
                                "dimensions": list(obj.dimensions)
                            })
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(objects).encode())
                    elif self.path == '/v1/status':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "ready", "objects": len(bpy.data.objects)}).encode())
                    else:
                        self.send_response(404)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"error": "Endpoint not found"}')
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
            
            def do_POST(self):
                """Handle POST requests"""
                try:
                    if self.path == '/v1/commands':
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        command = json.loads(post_data.decode())
                        
                        # Add command to queue
                        result = self.handler.handle_request(command)
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(result).encode())
                    else:
                        self.send_response(404)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"error": "Endpoint not found"}')
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
        
        return CustomHTTPHandler

# Blender operator to start server
class StartServerOperator(bpy.types.Operator):
    bl_idname = "blend_rest.start_server"
    bl_label = "Start REST Server"
    
    def execute(self, context):
        global rest_server
        rest_server = BlendRESTServer()
        result = rest_server.start_server()
        self.report({'INFO'}, f"Server: {result['status']}")
        return {'FINISHED'}

# Blender operator to stop server
class StopServerOperator(bpy.types.Operator):
    bl_idname = "blend_rest.stop_server"
    bl_label = "Stop REST Server"
    
    def execute(self, context):
        global rest_server
        if rest_server:
            result = rest_server.stop_server()
            self.report({'INFO'}, f"Server: {result['status']}")
        return {'FINISHED'}

# Blender panel for UI
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

# Timer function to process commands
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

    return 0.1  # run again after 0.1 sec

# Global server instance
rest_server = None

# Registration
def register():
    bpy.utils.register_class(StartServerOperator)
    bpy.utils.register_class(StopServerOperator)
    bpy.utils.register_class(BlendRESTPanel)
    
    # Start command processor timer
    if not bpy.app.timers.is_registered(process_commands):
        bpy.app.timers.register(process_commands)

def unregister():
    bpy.utils.unregister_class(StartServerOperator)
    bpy.utils.unregister_class(StopServerOperator)
    bpy.utils.unregister_class(BlendRESTPanel)
    
    # Stop server if running
    if rest_server:
        rest_server.stop_server()
    
    # Stop command processor timer
    if bpy.app.timers.is_registered(process_commands):
        bpy.app.timers.unregister(process_commands)

if __name__ == "__main__":
    register()
