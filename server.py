import bpy, json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import queue

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
                        "scale": list(obj.scale)
                    })
                
                response = json.dumps({"models": objects})
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(response.encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Endpoint not found"}')
            
    def do_POST(self):
        if self.path == '/' or self.path == '/v1/commands':
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length)
            try:
                command = json.loads(body)
                command_queue.put(command)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "queued"}')
            except Exception as e:
                self.send_response(400)
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
        
        if action == "create_object":
            typ = cmd["type"]
            p = cmd.get("params", {})
            if typ == "cube":
                bpy.ops.mesh.primitive_cube_add(**p)
            elif typ == "cylinder":
                bpy.ops.mesh.primitive_cylinder_add(**p)
            # ... other types
            
        elif action == "modify_object":
            obj_name = cmd.get("name")
            props = cmd.get("properties", {})
            obj = bpy.data.objects.get(obj_name)
            if obj:
                for k,v in props.items():
                    setattr(obj, k, v)
        # Add more actions as needed

    return 0.1  # run again after 0.1 sec

# Register Blender timer to execute queued commands on main thread
bpy.app.timers.register(process_commands)
