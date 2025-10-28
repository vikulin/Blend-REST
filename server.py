import bpy, json, threading, bmesh, mathutils
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
            
        elif action == "select_faces":
            bpy.ops.ed.undo_push(message="Original")
            # Select specific faces on an object
            select_params = cmd.get("params", {})
            target_object = select_params.get("target")  # Object to select faces on
            side_type = select_params.get("side", "all")  # "external", "internal", or "all"
            
            # Get the target object
            obj = bpy.data.objects.get(target_object)
            if not obj:
                print(f"Error: Object '{target_object}' not found")
                return 0.1
                
            # Select object and enter edit mode
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            bpy.ops.mesh.select_mode(type="FACE")
            # Default: select all quad faces (side faces only)
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.mesh.select_face_by_sides(number=4, type='EQUAL')  # Select only quads
        
            if side_type in ["external", "internal"]:
                # Now filter based on external/internal using face normals
                bm = bmesh.from_edit_mesh(obj.data)
                bm.faces.ensure_lookup_table()
                
                # Deselect all first, then selectively re-select based on normal direction
                for face in bm.faces:
                    if face.select:  # Only process currently selected faces (side faces)
                        # Calculate face center
                        center = face.calc_center_median()
                        
                        # Calculate vector from object origin to face center
                        vec_to_face = center - obj.location
                        
                        # Dot product between face normal and vector to face center
                        dot_product = face.normal.dot(vec_to_face)
                        
                        # Determine if this face should be selected based on side_type
                        should_select = False
                        if side_type == "external" and dot_product > 0:
                            should_select = True
                        elif side_type == "internal" and dot_product < 0:
                            should_select = True
                        
                        face.select = should_select
                
                bmesh.update_edit_mesh(obj.data)
            bpy.ops.ed.undo_push(message=f"Selected {side_type} faces")
            
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
            
            # Use select_faces action to select side faces first
            bpy.ops.ed.undo_push(message="Selected side faces")
            
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
            
        elif action == "bisect_plane":
            # Perform bisect plane operation assuming faces are already selected
            bisect_params = cmd.get("params", {})
            target_object = bisect_params.get("target")  # Object to bisect
            factor = bisect_params.get("factor", 0.0)   # Offset along cylinder axis
            
            # Get the target object
            obj = bpy.data.objects.get(target_object)
            if not obj:
                print(f"Error: Object '{target_object}' not found")
                return 0.1
            
            # Create BMesh from edit mesh
            bm = bmesh.from_edit_mesh(obj.data)
            
            # Get selected faces (assumes selection was already made via select_faces)
            selected_faces = [f for f in bm.faces if f.select]
            
            if not selected_faces:
                print("Error: No faces selected for bisect operation")
                bpy.ops.object.mode_set(mode='OBJECT')
                return 0.1
            
            # Debug output: show selected faces
            print(f"Number of selected faces: {len(selected_faces)}")
            for i, face in enumerate(selected_faces):
                print(f"Face {i} center: {face.calc_center_median()}, area: {face.calc_area()}")
            
            # Calculate weighted center of selected faces
            total_area = 0.0
            weighted_center = mathutils.Vector((0, 0, 0))
            
            for face in selected_faces:
                face_center = face.calc_center_median()
                face_area = face.calc_area()
                weighted_center += face_center * face_area
                total_area += face_area
            
            if total_area > 0:
                plane_co = weighted_center / total_area
            else:
                plane_co = selected_faces[0].calc_center_median()
            
            # Debug output: show weighted center calculation
            print(f"Weighted center calculation: total_area={total_area}, weighted_center={weighted_center}, plane_co={plane_co}")
            
            # Calculate the proper perpendicular direction for cylindrical geometry
            # Collect all face normals
            normals = [face.normal for face in selected_faces]
            print(f"Collected {len(normals)} face normals")
            
            # Find two face normals with approximately 90 degree angle
            best_pair = None
            best_angle = float('inf')  # Looking for dot product closest to 0
            
            for i in range(len(normals)):
                for j in range(i + 1, len(normals)):
                    dot_product = abs(normals[i].dot(normals[j]))
                    if dot_product < best_angle:
                        best_angle = dot_product
                        best_pair = (normals[i], normals[j])
            
            if best_pair and best_angle < 0.3:  # ~90 degree angle (dot < 0.3)
                # Calculate cross product to get cylinder axis (perpendicular to both normals)
                cylinder_axis = best_pair[0].cross(best_pair[1]).normalized()
                print(f"Using cross product method: best_angle={best_angle}, cylinder_axis={cylinder_axis}")
            else:
                # Fallback: find vector most orthogonal to all normals
                best_axis = None
                min_max_dot = float('inf')
                
                candidates = [
                    mathutils.Vector((1, 0, 0)),
                    mathutils.Vector((0, 1, 0)), 
                    mathutils.Vector((0, 0, 1)),
                    mathutils.Vector((-1, 0, 0)),
                    mathutils.Vector((0, -1, 0)),
                    mathutils.Vector((0, 0, -1))
                ]
                
                for candidate in candidates:
                    max_dot = max(abs(candidate.dot(normal)) for normal in normals)
                    if max_dot < min_max_dot:
                        min_max_dot = max_dot
                        best_axis = candidate
                
                cylinder_axis = best_axis
                print(f"Using fallback method: min_max_dot={min_max_dot}, cylinder_axis={cylinder_axis}")
            
            # Apply factor offset along the cylinder axis
            plane_co = plane_co + cylinder_axis * factor
            print(f"Final plane position with offset: plane_co={plane_co}")
            
            # Perform bisect operation
            try:
                bpy.ops.mesh.bisect(
                    plane_co=plane_co,
                    plane_no=cylinder_axis,
                    use_fill=False,
                    clear_inner=False,
                    clear_outer=False,
                    threshold=0.0001
                )
                print(f"Bisect plane applied to '{target_object}' at position {plane_co} with offset {factor}")
            except Exception as e:
                print(f"Error applying bisect: {e}")
            finally:
                # Return to object mode
                print("done")
                bpy.ops.object.mode_set(mode='OBJECT')
            
            bpy.ops.ed.undo_push(message="Bisect plane applied")
            
        # Add more actions as needed

    return 0.1  # run again after 0.1 sec

# Register Blender timer to execute queued commands on main thread
bpy.app.timers.register(process_commands)
