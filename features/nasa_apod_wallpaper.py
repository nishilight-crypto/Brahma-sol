"""
features/nasa_apod_wallpaper.py
===============================
Autonomous NASA Astronomy & Space 4K Wallpaper Engine for Brahma Sol.
Fetches high-resolution NASA imagery and updates the Windows desktop wallpaper.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

# Tool metadata manifest for DynamicToolRegistry
TOOL_MANIFEST = {
    "name": "nasa_apod_wallpaper",
    "description": "Fetches high-resolution 4K NASA Astronomy Picture of the Day or Deep Space imagery and sets it as the Windows desktop wallpaper.",
    "triggers": [
        "nasa wallpaper",
        "nasa apod",
        "astronomy picture of the day",
        "space wallpaper",
        "set wallpaper to nasa",
        "set nasa wallpaper",
        "download nasa apod",
        "nasa image of the day"
    ],
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Optional search topic e.g. 'nebula', 'galaxy', 'james webb', 'mars' (default: 'nebula')"
            }
        }
    }
}


def _set_windows_wallpaper(image_path: str) -> bool:
    """Sets the wallpaper using Windows SystemParametersInfo API."""
    import sys
    if sys.platform != "win32":
        from core.mac_compat import set_wallpaper
        return set_wallpaper(image_path)
    import ctypes
    try:
        # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE = 1, SPIF_SENDCHANGE = 2
        ctypes.windll.user32.SystemParametersInfoW(20, 0, str(image_path), 3)
        return True
    except Exception as e:
        print(f"[NASA Wallpaper] Failed to set Win32 wallpaper: {e}")
        return False


def execute(query: str = "nebula", **kwargs) -> dict:
    """Fetches high-res NASA imagery and applies it to the Windows desktop."""
    try:
        topic = (query or "nebula").strip()
        encoded = urllib.parse.quote(topic)
        api_url = f"https://images-api.nasa.gov/search?q={encoded}&media_type=image"
        
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0 BrahmaAI/2.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        items = data.get("collection", {}).get("items", [])
        if not items:
            return {"success": False, "error": f"No NASA space images found for topic '{topic}'."}

        # Pick the top result with a valid image link
        chosen = None
        for item in items[:5]:
            links = item.get("links", [])
            data_list = item.get("data", [])
            if links and data_list and links[0].get("href"):
                chosen = item
                break

        if not chosen:
            return {"success": False, "error": "No valid NASA image links available."}

        meta = chosen["data"][0]
        title = meta.get("title", "NASA Deep Space")
        description = meta.get("description", "Cosmic imagery captured by NASA observatories.")[:180]
        nasa_id = meta.get("nasa_id")

        # Resolve asset manifest to get true full-resolution URL
        high_res_url = None
        if nasa_id:
            try:
                asset_url = f"https://images-api.nasa.gov/asset/{nasa_id}"
                a_req = urllib.request.Request(asset_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(a_req, timeout=8) as a_resp:
                    a_data = json.loads(a_resp.read().decode("utf-8"))
                    a_items = a_data.get("collection", {}).get("items", [])
                    # Prefer ~orig.jpg, then ~large.jpg, then ~medium.jpg
                    for suffix in ("~orig.jpg", "~large.jpg", "~medium.jpg"):
                        match = next((i["href"] for i in a_items if i.get("href", "").endswith(suffix)), None)
                        if match:
                            high_res_url = match
                            break
            except Exception:
                pass

        if not high_res_url:
            thumb_url = chosen["links"][0]["href"]
            high_res_url = thumb_url.replace("~thumb.jpg", "~orig.jpg")

        if high_res_url.startswith("http://"):
            high_res_url = high_res_url.replace("http://", "https://")

        # Save to local Brahma directory
        save_dir = Path(os.environ.get("LOCALAPPDATA", ".")) / "BrahmaAI" / "wallpapers"
        save_dir.mkdir(parents=True, exist_ok=True)
        img_dest = save_dir / "nasa_latest_wallpaper.jpg"

        print(f"[NASA Wallpaper] Downloading high-res image from: {high_res_url}")
        img_req = urllib.request.Request(high_res_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(img_req, timeout=20) as img_resp:
            img_dest.write_bytes(img_resp.read())

        # Apply as Windows desktop background
        ok = _set_windows_wallpaper(str(img_dest))
        if ok:
            return {
                "success": True,
                "title": title,
                "summary": f"Desktop wallpaper successfully updated to NASA's '{title}'.",
                "description": description,
                "path": str(img_dest),
                "url": high_res_url
            }
        else:
            return {
                "success": False,
                "error": "Image downloaded but Windows refused to update desktop background."
            }

    except Exception as exc:
        return {"success": False, "error": f"NASA Wallpaper engine encountered an issue: {exc}"}


# Convenience alias for DynamicToolRegistry
def run(parameters: dict = None, **kwargs) -> dict:
    params = parameters or {}
    q = params.get("query") or params.get("goal") or "nebula"
    return execute(query=q)


if __name__ == "__main__":
    res = execute()
    print(json.dumps(res, indent=2))
