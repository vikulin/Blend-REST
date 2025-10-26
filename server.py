import bpy, json, threading, bmesh
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
                    
        elif action == "boolean_difference":
            bpy.ops.ed.undo_push(message="Original")
            # Create a hole using boolean difference operation
            target_name = cmd.get("target")
            cutter_params = cmd.get("cutter", {})
            
            # Get the target object
            target_obj = bpy.data.objects.get(target_name)
            if not target_obj:
                continue
                
            # Create cutter object (cylinder for hole)
            cutter_type = cutter_params.get("type", "cylinder")
            if cutter_type == "cylinder":
                # Get adjustable parameters with defaults
                cutter_location = cutter_params.get("location", [0, 0, 0])
                cutter_radius = cutter_params.get("radius", 0.5)
                cutter_depth = cutter_params.get("depth", 2.0)
                
                # Create cutter cylinder
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=cutter_radius,
                    depth=cutter_depth,
                    location=cutter_location
                )
                cutter_obj = bpy.context.active_object
                cutter_obj.name = "BooleanCutter"
                
                # Apply boolean modifier to target object
                bool_mod = target_obj.modifiers.new(name="BooleanDifference", type='BOOLEAN')
                bool_mod.operation = 'DIFFERENCE'
                bool_mod.object = cutter_obj
                
                # Apply the modifier
                bpy.context.view_layer.objects.active = target_obj
                bpy.ops.object.modifier_apply(modifier=bool_mod.name)
                
                # Delete the cutter object
                bpy.data.objects.remove(cutter_obj, do_unlink=True)

                bpy.ops.ed.undo_push(message="Hole created")
                
        elif action == "undo":
            # Use Blender's built-in undo functionality (equivalent to Ctrl+Z)
            bpy.ops.ed.undo()
            
        elif action == "redo":
            # Use Blender's built-in redo functionality (equivalent to Ctrl+Shift+Z)
            bpy.ops.ed.redo()
            
        elif action == "add_thread":
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
                return 0.1
                
            # Position the 3D cursor
            bpy.context.scene.cursor.location = position
            
            # Select object and enter edit mode
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Select only the side (tube) faces of the cylinder, exclude top and bottom
            # Use a simpler approach: select all faces, then deselect by normal direction
            bpy.ops.mesh.select_mode(type="FACE")
            bpy.ops.mesh.select_all(action='SELECT')  # Select all faces first
            
            # Deselect faces pointing mostly up/down (top/bottom faces)
            # This works in edit mode without bmesh issues
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.mesh.select_face_by_sides(number=4, type='EQUAL')  # Select only quads (side faces)
            
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
            finally:
                # Return to object mode
                bpy.ops.object.mode_set(mode='OBJECT')
            
            bpy.ops.ed.undo_push(message="Added thread")
        # Add more actions as needed

    return 0.1  # run again after 0.1 sec

# Register Blender timer to execute queued commands on main thread
bpy.app.timers.register(process_commands)
