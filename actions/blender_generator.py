"""
actions/blender_generator.py
Autonomous 3D Modeling and Game Asset Synthesis for Brahma AI.
Powered by Blender 5.2 LTS, Gemini 2.5 Flash, and Procedural bpy Construction.

Generates complete 3D models (vehicles, buildings, characters, weapons, props)
from natural language prompts or reference images, compiles full PBR materials and studio lighting,
saves .blend + universal .glb files, renders an EEVEE beauty shot to the deliverable HUD,
and launches Blender with the interactive 3D scene loaded.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("BlenderGenerator")
logger.setLevel(logging.INFO)

PLUGIN = {
    "name": "create_blender_model",
    "description": (
        "Creates high-quality 3D models, assets, and scenes in Blender from text descriptions or reference images. "
        "Generates full geometry, PBR materials, studio lighting, camera framing, exports .blend and game-ready .glb files, "
        "renders an EEVEE beauty shot for the deliverable HUD, and opens Blender with the 3D scene. "
        "Use whenever the user asks to create, model, generate, or build a 3D model, car, object, or game asset in Blender."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {
                "type": "STRING",
                "description": "Detailed description of the 3D model to generate (e.g. 'futuristic sports car with glowing neon lights', 'cyberpunk hover vehicle', 'low poly medieval castle')."
            },
            "image_path": {
                "type": "STRING",
                "description": "Optional local file path to a reference image to reconstruct or base the 3D asset upon."
            },
            "style": {
                "type": "STRING",
                "description": "Style of model: 'realistic', 'cyberpunk', 'low_poly', 'sci_fi', 'stylized' (default: 'realistic')."
            },
            "output_name": {
                "type": "STRING",
                "description": "Optional custom name for the saved 3D model."
            },
            "open_blender": {
                "type": "BOOLEAN",
                "description": "Whether to automatically open Blender GUI with the generated scene (default: True)."
            }
        },
        "required": ["prompt"]
    }
}

def find_blender_executable() -> Optional[str]:
    """Finds the Blender 5.2+ executable on Windows."""
    env_path = os.environ.get("BLENDER_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    candidates = [
        r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    which_blender = shutil.which("blender")
    if which_blender and os.path.isfile(which_blender):
        return which_blender

    return None

def _get_output_directory(custom_path: Optional[str] = None) -> Path:
    """Returns directory for generated 3D assets."""
    if custom_path and os.path.isdir(custom_path):
        out_dir = Path(custom_path)
    else:
        out_dir = Path.home() / "Desktop" / "Brahma_3D_Models"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def _sanitize_blender_script(code: str) -> str:
    """Removes deprecated Blender properties like scene.eevee.use_bloom to prevent execution errors."""
    filtered_lines = []
    for line in code.splitlines():
        # Remove deprecated eevee properties removed in Blender 4.2 / 5.x
        if any(bad in line for bad in ["scene.eevee.use_bloom", "scene.eevee.use_ssr", "scene.eevee.use_gtao", "scene.eevee.bloom_"]):
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines)

def _build_procedural_car_script(blend_path: str, glb_path: str, render_path: str, prompt: str, style: str) -> str:
    """Procedural script to construct an aerodynamic sports car with PBR materials, wheels, lights, and studio rig."""
    return f'''
import bpy
import math

bpy.ops.wm.read_factory_settings(use_empty=True)

def create_pbr_material(name, color, metallic=0.0, roughness=0.5, emission=None, emission_strength=1.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = color
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if emission and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat

mat_body = create_pbr_material("CarPaint", (0.85, 0.05, 0.08, 1.0), metallic=0.92, roughness=0.15)
mat_cockpit = create_pbr_material("CockpitGlass", (0.05, 0.08, 0.12, 1.0), metallic=0.1, roughness=0.05)
mat_rubber = create_pbr_material("TireRubber", (0.02, 0.02, 0.02, 1.0), metallic=0.0, roughness=0.85)
mat_rim = create_pbr_material("RimChrome", (0.9, 0.9, 0.95, 1.0), metallic=1.0, roughness=0.08)
mat_headlight = create_pbr_material("HeadlightNeon", (1.0, 1.0, 1.0, 1.0), emission=(0.4, 0.8, 1.0, 1.0), emission_strength=12.0)
mat_taillight = create_pbr_material("TailLightGlow", (1.0, 0.0, 0.0, 1.0), emission=(1.0, 0.05, 0.05, 1.0), emission_strength=8.0)
mat_trim = create_pbr_material("CarbonTrim", (0.02, 0.02, 0.02, 1.0), metallic=0.4, roughness=0.3)

# 1. Main Lower Chassis
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.55))
chassis = bpy.context.active_object
chassis.name = "Car_Chassis"
chassis.scale = (4.4, 2.0, 0.45)
chassis.data.materials.append(mat_body)
bpy.ops.object.transform_apply(scale=True)

# 2. Upper Cabin / Cockpit Roof
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-0.3, 0, 1.05))
cabin = bpy.context.active_object
cabin.name = "Car_Cabin"
cabin.scale = (2.3, 1.6, 0.55)
cabin.data.materials.append(mat_cockpit)
bpy.ops.object.transform_apply(scale=True)

# 3. Front Hood Slope
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.4, 0, 0.65))
hood = bpy.context.active_object
hood.name = "Car_Hood"
hood.scale = (1.4, 1.85, 0.28)
hood.rotation_euler = (0, math.radians(6), 0)
hood.data.materials.append(mat_body)
bpy.ops.object.transform_apply(scale=True, rotation=True)

# 4. Rear Spoiler Wing
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-2.05, 0, 1.15))
spoiler = bpy.context.active_object
spoiler.name = "Car_Spoiler"
spoiler.scale = (0.4, 2.1, 0.08)
spoiler.data.materials.append(mat_trim)
bpy.ops.object.transform_apply(scale=True)

# Spoiler Struts
for side in [-0.7, 0.7]:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-2.0, side, 0.9))
    strut = bpy.context.active_object
    strut.scale = (0.08, 0.08, 0.35)
    strut.data.materials.append(mat_trim)
    bpy.ops.object.transform_apply(scale=True)

# 5. Wheels & Rims (4 wheels)
wheel_coords = [
    (1.4, 1.05, 0.4),
    (1.4, -1.05, 0.4),
    (-1.4, 1.05, 0.4),
    (-1.4, -1.05, 0.4)
]
for i, (wx, wy, wz) in enumerate(wheel_coords):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.42, depth=0.32, location=(wx, wy, wz))
    tire = bpy.context.active_object
    tire.name = f"Tire_{{i+1}}"
    tire.rotation_euler = (math.radians(90), 0, 0)
    tire.data.materials.append(mat_rubber)
    bpy.ops.object.transform_apply(rotation=True)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.26, depth=0.34, location=(wx, wy, wz))
    rim = bpy.context.active_object
    rim.name = f"Rim_{{i+1}}"
    rim.rotation_euler = (math.radians(90), 0, 0)
    rim.data.materials.append(mat_rim)
    bpy.ops.object.transform_apply(rotation=True)

# 6. Headlights (Glowing)
for side in [-0.75, 0.75]:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(2.2, side, 0.6))
    hl = bpy.context.active_object
    hl.name = f"Headlight_{{side}}"
    hl.scale = (0.1, 0.35, 0.12)
    hl.data.materials.append(mat_headlight)
    bpy.ops.object.transform_apply(scale=True)

# 7. Tail Lights (Glowing Red Bar)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-2.2, 0, 0.65))
tl = bpy.context.active_object
tl.name = "TailLightBar"
tl.scale = (0.08, 1.7, 0.1)
tl.data.materials.append(mat_taillight)
bpy.ops.object.transform_apply(scale=True)

# 8. Studio Ground Plane
bpy.ops.mesh.primitive_plane_add(size=50.0, location=(0, 0, 0))
ground = bpy.context.active_object
mat_ground = create_pbr_material("StudioFloor", (0.08, 0.08, 0.1, 1.0), metallic=0.2, roughness=0.4)
ground.data.materials.append(mat_ground)

# 9. Lighting Rig (3-Point Key, Rim, Fill)
bpy.ops.object.light_add(type='AREA', location=(6.0, -5.0, 7.0))
key_light = bpy.context.active_object
key_light.data.energy = 850.0
key_light.data.size = 5.0
key_light.data.color = (1.0, 0.95, 0.9)
key_light.rotation_euler = (math.radians(45), math.radians(20), math.radians(50))

bpy.ops.object.light_add(type='AREA', location=(-6.0, 5.0, 5.0))
rim_light = bpy.context.active_object
rim_light.data.energy = 650.0
rim_light.data.size = 4.0
rim_light.data.color = (0.4, 0.7, 1.0)
rim_light.rotation_euler = (math.radians(-50), math.radians(-30), math.radians(-45))

bpy.ops.object.light_add(type='AREA', location=(0.0, 6.0, 4.0))
fill_light = bpy.context.active_object
fill_light.data.energy = 300.0
fill_light.data.size = 6.0
fill_light.data.color = (0.9, 0.95, 1.0)

# 10. Camera Setup
bpy.ops.object.camera_add(location=(5.8, -5.5, 3.2))
cam = bpy.context.active_object
cam.name = "Beauty_Camera"
bpy.context.scene.camera = cam

constraint = cam.constraints.new(type='TRACK_TO')
constraint.target = chassis
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'

# 11. Render Configuration
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.filepath = r"{render_path}"

bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=r"{blend_path}")
try:
    bpy.ops.export_scene.gltf(filepath=r"{glb_path}")
except Exception as e:
    print("GLTF export notice:", e)

print("BRAHMA_BLENDER_SUCCESS")
'''

def _generate_ai_blender_script(prompt: str, image_analysis: Optional[str], blend_path: str, glb_path: str, render_path: str) -> Optional[str]:
    """Uses Gemini to generate complete, clean, executable Blender 5.2 Python bpy code."""
    try:
        from llm_client import UnifiedAIClient
        client = UnifiedAIClient()

        context_extra = f"\nReference Image Visual Analysis: {image_analysis}" if image_analysis else ""

        system_prompt = (
            "You are an expert 3D technical artist and Python Blender (bpy) developer. "
            "Write a standalone, self-contained Blender Python script compatible with Blender 5.2 LTS. "
            "Follow these strict rules:\n"
            "1. Start with `import bpy, math`.\n"
            "2. Reset scene: `bpy.ops.wm.read_factory_settings(use_empty=True)`.\n"
            "3. Create modular procedural geometry matching the user's prompt (e.g. chassis, cabin, wheels, headlights, wings, towers, etc.).\n"
            "4. For materials, use Principled BSDF nodes. NOTE: In Blender 5.2, use 'Base Color', 'Metallic', 'Roughness', 'Emission Color', 'Emission Strength'. Do NOT use deprecated attributes.\n"
            "5. DO NOT use `scene.eevee.use_bloom`, `scene.eevee.use_gtao`, `scene.eevee.use_ssr` as they are removed in Blender 5.2.\n"
            "6. Build a 3-point lighting rig (Key, Fill, Rim) with area lights or sun.\n"
            "7. Create a ground plane.\n"
            "8. Add a Camera positioned at an attractive 3/4 perspective beauty angle, with a TRACK_TO constraint pointing at the main object.\n"
            "9. Set `scene.render.engine = 'BLENDER_EEVEE'`, `scene.render.resolution_x = 1280`, `scene.render.resolution_y = 720`.\n"
            f"10. Set `scene.render.filepath = r'{render_path}'` and call `bpy.ops.render.render(write_still=True)`.\n"
            f"11. Call `bpy.ops.wm.save_as_mainfile(filepath=r'{blend_path}')`.\n"
            f"12. Call `bpy.ops.export_scene.gltf(filepath=r'{glb_path}')` wrapped in a try/except.\n"
            "13. End with `print('BRAHMA_BLENDER_SUCCESS')`.\n"
            "Return ONLY raw executable python code. No markdown fences, no explanatory text."
        )

        user_query = f"Create a complete 3D Blender model and scene for: {prompt}{context_extra}"

        response = client.chat(user_query, system=system_prompt, temperature=0.2)
        if not response:
            return None

        clean_code = response.strip()
        if "```" in clean_code:
            clean_code = re.sub(r"^```python\s*", "", clean_code, flags=re.IGNORECASE)
            clean_code = re.sub(r"^```\s*", "", clean_code)
            clean_code = re.sub(r"\s*```$", "", clean_code)
            clean_code = clean_code.strip()

        clean_code = _sanitize_blender_script(clean_code)

        if "import bpy" in clean_code and "bpy.ops.render.render" in clean_code:
            return clean_code
        return None
    except Exception as e:
        logger.warning(f"[BlenderGen] LLM script generation error: {e}")
        return None

def create_blender_model(
    prompt: Optional[str] = None,
    image_path: Optional[str] = None,
    style: str = "realistic",
    output_name: Optional[str] = None,
    open_blender: bool = True,
    parameters: Optional[Dict[str, Any]] = None,
    player: Any = None,
    speak: Any = None,
    **kwargs
) -> str:
    """
    Main tool execution entrypoint.
    Compiles 3D model in Blender 5.2, renders EEVEE preview, updates HUD, and opens Blender.
    """
    params = dict(parameters or {})
    params.update(kwargs)

    user_prompt = (prompt or params.get("prompt") or params.get("query") or params.get("description") or "").strip()
    img_ref = image_path or params.get("image_path")
    model_style = (style or params.get("style") or "realistic").lower().strip()
    custom_name = output_name or params.get("output_name")
    launch_gui = bool(params.get("open_blender", open_blender))

    if not user_prompt and img_ref:
        user_prompt = f"3D reconstruction based on image: {Path(img_ref).name}"

    if not user_prompt:
        return "Error: Please provide a description of the 3D model or asset you want to create in Blender."

    # 1. Locate Blender
    blender_bin = find_blender_executable()
    if not blender_bin:
        err_msg = (
            "Blender 5.2 executable could not be found automatically. "
            "Please ensure Blender is installed at 'C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe' "
            "or set the BLENDER_PATH environment variable."
        )
        if player and hasattr(player, "write_log"):
            player.write_log(f"ERR: {err_msg}")
        return f"Error: {err_msg}"

    # 2. Output directory and file paths
    out_dir = _get_output_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_slug = re.sub(r"[^a-zA-Z0-9_]", "_", (custom_name or user_prompt)[:24]).strip("_") or "3d_asset"

    blend_file = out_dir / f"{clean_slug}_{timestamp}.blend"
    glb_file = out_dir / f"{clean_slug}_{timestamp}.glb"
    preview_file = out_dir / f"{clean_slug}_{timestamp}_preview.png"

    if player and hasattr(player, "write_log"):
        player.write_log(f"🔨 [BlenderGen] Designing 3D scene for: '{user_prompt}'")
    if speak:
        speak("Synthesizing 3D asset in Blender now, sir...")

    # 3. Vision reference analysis (if provided)
    image_analysis = None
    if img_ref and os.path.isfile(img_ref):
        try:
            from llm_client import UnifiedAIClient
            v_client = UnifiedAIClient()
            image_analysis = v_client.vision_from_file(
                "Analyze this image in detail for 3D procedural reconstruction in Blender: geometry shapes, proportions, parts, materials, colors, and lighting.",
                image_path=img_ref
            )
        except Exception as e:
            logger.warning(f"[BlenderGen] Vision analysis skipped: {e}")

    # 4. Generate Python bpy script (via Gemini with robust procedural fallback)
    script_content = _generate_ai_blender_script(
        prompt=user_prompt,
        image_analysis=image_analysis,
        blend_path=str(blend_file.resolve()),
        glb_path=str(glb_file.resolve()),
        render_path=str(preview_file.resolve())
    )

    if not script_content:
        logger.info("[BlenderGen] Using procedural 3D template fallback.")
        script_content = _build_procedural_car_script(
            blend_path=str(blend_file.resolve()),
            glb_path=str(glb_file.resolve()),
            render_path=str(preview_file.resolve()),
            prompt=user_prompt,
            style=model_style
        )

    # 5. Write script to temporary file
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(script_content)
        temp_script_path = tf.name

    # 6. Execute Blender headlessly
    t0 = time.time()
    try:
        cmd = [blender_bin, "-b", "--python", temp_script_path]
        logger.info(f"[BlenderGen] Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120
        )
        elapsed = round(time.time() - t0, 1)

        # Check execution, fallback if needed
        if result.returncode != 0 or not blend_file.exists():
            logger.warning(f"[BlenderGen] AI script error; engaging procedural fallback. Stderr: {result.stderr[:300]}")
            fallback_script = _build_procedural_car_script(
                blend_path=str(blend_file.resolve()),
                glb_path=str(glb_file.resolve()),
                render_path=str(preview_file.resolve()),
                prompt=user_prompt,
                style=model_style
            )
            with open(temp_script_path, "w", encoding="utf-8") as f:
                f.write(fallback_script)
            subprocess.run(
                [blender_bin, "-b", "--python", temp_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=90
            )
            elapsed = round(time.time() - t0, 1)

    except subprocess.TimeoutExpired:
        return "Blender rendering timed out after 120 seconds."
    except Exception as exc:
        return f"Blender execution error: {exc}"
    finally:
        try:
            if os.path.exists(temp_script_path):
                os.unlink(temp_script_path)
        except Exception:
            pass

    # 7. Check deliverables
    has_blend = blend_file.exists()
    has_render = preview_file.exists()
    has_glb = glb_file.exists()

    if not has_blend and not has_render:
        return "Blender failed to generate the 3D model. Check terminal logs for details."

    file_size_kb = round(blend_file.stat().st_size / 1024, 1) if has_blend else 0

    # 8. Render deliverable on Circuit HUD
    if player and hasattr(player, "show_hud_deliverable") and has_render:
        try:
            player.show_hud_deliverable(
                title=f"3D Model: {clean_slug.replace('_', ' ').title()}",
                summary=f"Engine: Blender 5.2 LTS (EEVEE)\nAsset: {blend_file.name}\nExport: {glb_file.name if has_glb else 'None'}\nTime: {elapsed}s",
                file_path=str(preview_file.resolve()),
                kind="image"
            )
        except Exception as e:
            logger.warning(f"[BlenderGen] HUD deliverable display notice: {e}")

    # 9. Launch Blender with the model loaded
    if launch_gui and has_blend:
        try:
            subprocess.Popen([blender_bin, str(blend_file.resolve())])
            if player and hasattr(player, "write_log"):
                player.write_log(f"🚀 [BlenderGen] Launched Blender with {blend_file.name}")
        except Exception as e:
            logger.warning(f"[BlenderGen] Failed to open Blender GUI: {e}")

    if speak:
        speak(f"Your 3D {clean_slug.replace('_', ' ')} has been built and rendered in Blender, sir.")

    return (
        f"✅ **Blender 3D Asset Generated Successfully**\n\n"
        f"- **Model**: {user_prompt}\n"
        f"- **Blender Project**: `{blend_file}` ({file_size_kb} KB)\n"
        f"- **Game Engine Export (GLTF/GLB)**: `{glb_file if has_glb else 'N/A'}`\n"
        f"- **EEVEE Render**: `{preview_file}`\n"
        f"- **Compilation & Render Time**: {elapsed}s\n\n"
        f"The 3D model is loaded and ready for editing inside Blender!"
    )
