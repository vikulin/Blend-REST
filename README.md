# Blend-REST

A REST API server for Blender that allows you to create and manipulate 3D objects programmatically.

## Setup

1. **Install the script in Blender**:
   - Open Blender
   - Go to `Scripting` workspace
   - Open the text editor and load `server.py`
   - Click `Run Script` to start the REST server

2. **Verify the server is running**:
   - The server runs on `localhost:8000`
   - You should see a message indicating the server has started

## REST API Endpoints

### GET /v1/models
Retrieve all objects in the current scene.

**Example:**
```bash
curl http://localhost:8000/v1/models
```

**Response:**
```json
{
  "models": [
    {
      "name": "Cube",
      "type": "MESH",
      "location": [0, 0, 0],
      "rotation": [0, 0, 0],
      "scale": [1, 1, 1]
    }
  ]
}
```

### POST /
Create or modify objects in the scene.

**Supported Actions:**

#### Create Object
```json
{
  "action": "create_object",
  "type": "cylinder",
  "params": {
    "radius": 1,
    "depth": 1,
    "location": [0, 0, 0]
  }
}
```

Supported types: `cube`, `cylinder`, `sphere`, `cone`, `plane`

#### Modify Object
```json
{
  "action": "modify_object",
  "name": "Cylinder",
  "properties": {
    "location": [0, 0, 0],
    "rotation": [0, 0, 0],
    "scale": [1, 1, 1]
  }
}
```

#### Boolean Difference (Create Hole)
```json
{
  "action": "boolean_difference",
  "target": "Cylinder",
  "cutter": {
    "type": "cylinder",
    "radius": 0.5,
    "depth": 2.2,
    "location": [0, 0, 0]
  }
}
```

## Examples

### Create a Cylinder
The `examples/create-cylinder.ps1` script creates a cylinder with radius 1 and depth 1 at the origin.

**Run from PowerShell:**
```powershell
cd examples
.\create-cylinder.ps1
```

**Or run directly:**
```powershell
curl -Method POST -Headers @{'Content-Type'='application/json'} -Body '{"action": "create_object", "type": "cylinder", "params": {"radius": 1, "depth": 1, "location": [0, 0, 0]}}' -Uri "http://localhost:8000/"
```

## Development

The server runs in a separate thread within Blender and processes commands through a thread-safe queue. Commands are executed on Blender's main thread using a timer callback.

### Project Structure
```
Blend-REST/
├── server.py          # Blender REST API server
├── examples/
│   └── create-cylinder.ps1  # Example PowerShell script
└── README.md          # This file
```

### Adding New Object Types
Extend the `process_commands()` function in `server.py` to support additional primitive types or custom operations.

## Notes

- The server must be running within Blender for the API to work
- All object manipulations are queued and processed on Blender's main thread
- Make sure Blender is kept open while using the API
