import bpy, json, threading, bmesh, mathutils
from http.server import BaseHTTPRequestHandler, HTTPServer
import queue
import os
import sys

# Add actions directory to Python path
actions_dir = os.path.join(os.path.dirname(__file__), 'actions')
if actions_dir not in sys.path:
    sys.path.append(actions_dir)

# Import action functions
from create_object import execute_create_object
from modify_object import execute_modify_object
from boolean_difference import execute_boolean_difference
from undo import execute_undo
from redo import execute_redo
from select_faces import execute_select_faces
from add_thread import execute_add_thread
from bisect_plane import execute_bisect_plane

# Thread-safe command queue
command_queue = queue.Queue()

# Server handler
class BlenderRESTHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/v1/models':
            try:
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
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        
        elif self.path == '/v1/status':
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ready", "objects": len(bpy.data.objects)}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Endpoint not found"}')

    def do_POST(self):
        if self.path == '/v1/commands':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                command = json.loads(post_data.decode())
                
                # Add command to queue for processing in Blender's main thread
                command_queue.put(command)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "queued"}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Endpoint not found"}')

# Start server thread
def start_server():
    server = HTTPServer(('localhost', 8000), BlenderRESTHandler)
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# Main Blender loop executor
def process_commands():
    while not command_queue.empty():
        cmd = command_queue.get()
        action = cmd.get("action")
        
        # Call the appropriate action function
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
            
    return 0.1  # run again after 0.1 sec

# Register Blender timer to execute queued commands on main thread
bpy.app.timers.register(process_commands)
