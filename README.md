# ☀️ Brahma Sol — Embodied 3D AI Operating Companion

<div align="center">

<img src="assets/brahma_sol_logo.png" alt="Brahma Sol Logo" width="380" />

### *The Sovereign, Multimodal 3D Desktop AI Operating Companion*
#### Created by Buildonaut — Suryaansh

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6%20%2B%20WebEngine-41CD52?logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Local AI](https://img.shields.io/badge/Local%20Brain-Ollama%20%2F%20Qwen2.5-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![Voice](https://img.shields.io/badge/Neural%20TTS-Kokoro--82M%20(54%20Voices)-FF6F00)](https://github.com/thewh1teagle/kokoro-onnx)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![License](https://img.shields.io/badge/License-Source--Available%20Personal%20Use-blue.svg)](LICENSE)

[**Download Windows Installer (v2.4.1)**](https://drive.google.com/file/d/1V18O0bY4H_e907DiXuheAbOjwZy3ckmQ/view?usp=sharing) • [**Official Website**](https://brahma-sol.netlify.app) • [**YouTube: @Buildonaut-AI**](https://www.youtube.com/@Buildonaut-AI) • [**Discord Community**](https://discord.gg/c9xhxSqURx)

</div>

---

## 🌌 Overview

**Brahma Sol** is a next-generation desktop intelligence built to function as an authentic JARVIS-level operating companion. Combining an **embodied 3D WebGL avatar**, **100% sovereign air-gapped local AI reasoning**, **sub-50ms neural speech synthesis**, and **sub-15ms direct hardware automations**, Brahma Sol transforms your Windows PC into a living, responsive command center.

Unlike traditional cloud-tethered chatbots that send your data to external APIs, Brahma Sol can operate **100% offline**, running local models directly on your hardware with zero telemetry.

---

## ⚡ Core Capabilities

### 1. 🤖 Embodied 3D Celestial Companion
* **Real-Time 3D Physical Body**: Interactive WebGL Three.js character rendered in a transparent, click-through desktop overlay.
* **Natural Eye Tracking & Expressions**: Tracks your mouse cursor and gaze across multiple monitors in real-time.
* **60 FPS Hardware Composition**: Fluid dragging, floating launcher docks, and customizable positions.

### 2. 🧠 Sovereign Offline AI Brain (Ollama ReAct)
* **100% Air-Gapped Intelligence**: Runs locally via Ollama (`qwen2.5:7b` / `qwen2.5:3b`) with zero cloud dependencies and zero data leaving your machine.
* **Autonomous Tool Use**: Reads files, inspects processes, launches software, and automates desktop tasks.
* **Optional Cloud Augmentation**: Seamlessly toggle between local models and Google Gemini for deep coding or multimodal tasks.

### 3. 🎙️ Kokoro-82M Neural Voice Engine
* **Ultra-Fast Local TTS**: High-fidelity neural voice synthesis running directly on CPU via ONNX Runtime.
* **54 Expressive Voices**: Includes clear British, American, and Indian English accents (`bm_lewis`, `hm_omega`, etc.).
* **Instant Barge-In**: Sub-30ms voice cutoff when you speak or interrupt.

### 4. ⚡ Tier 1 Instant Action Reflexes (<15ms)
* **Zero-Latency Execution**: High-frequency desktop commands bypass heavy LLM loops completely:
  - `"open whatsapp"` &rarr; Launches WhatsApp via native Windows protocol.
  - `"play <song> on youtube"` &rarr; Instantly opens and plays media without asking follow-up questions.
  - `"open notepad and type <text>"` &rarr; Launches Notepad and types text automatically.
  - Volume, display brightness, calculator, and system controls executed in <10ms.

### 5. 🛡️ Project Ultron & Auto-Heal Engine
* **Autonomous Error Recovery**: Ultron Crash Sentry detects runtime anomalies, inspects Python abstract syntax trees (AST), applies dynamic hotfixes, and prevents crashes without terminating your workflow.
* **Dynamic Skill Forge**: Can synthesize, verify in the Crucible sandbox, and hot-load new Python skills on the fly.

### 6. 🌐 3D HoloGlobe & Geospatial Radar
* **Global Geospatial Intelligence**: Embedded 3D Earth globe with live great-circle flight routes, aircraft radar tracking, turn-by-turn highway navigation, and nearby POI scans.

### 7. 🌌 NASA APOD 4K Wallpaper Engine
* **Celestial Workspace**: Automatically fetches, analyzes, and sets your desktop background to NASA's Astronomy Picture of the Day in 4K resolution with automated daily astronomical briefings.

---

## 🚀 Quick Start

### Option A: Standalone Windows Installer (Recommended)
1. Download **`brahma-sol_setup.exe`** from [Google Drive](https://drive.google.com/file/d/1V18O0bY4H_e907DiXuheAbOjwZy3ckmQ/view?usp=sharing).
2. Run the setup wizard (featuring the Celestial 3D Companion installer).
3. Launch **Brahma Sol** from your Desktop shortcut or Start Menu.

---

### Option B: Run from Source

#### Prerequisites
* Windows 10 / 11 (64-bit)
* Python 3.11 or 3.12
* [Ollama](https://ollama.com/) (recommended model: `ollama pull qwen2.5:7b` or `ollama pull qwen2.5:3b`)

#### Installation
```bash
# 1. Clone the repository
git clone https://github.com/titechprabhasolutions/Brahma-sol.git
cd Brahma-sol

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch Brahma Sol
python main.py
```

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│               BRAHMA SOL DESKTOP HUD                   │
│   • PyQt6 Glassmorphism UI   • Three.js 3D Companion   │
│   • FFT Waveform Visualizer  • Transparent Desktop Dock │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│     TIER 1 REFLEXES       │ │   SOVEREIGN LOCAL BRAIN   │
│ • Sub-15ms Regex Parser   │ │ • Ollama ReAct Runtime    │
│ • Direct Win32 Controls   │ │ • Qwen 2.5 7B / 3B        │
│ • App Launchers & Media   │ │ • Memory Cortex & RAG     │
└───────────────────────────┘ └─────────────┬─────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────┐
│                 AUTONOMOUS ACTION ENGINE                │
│ • Kokoro-82M Neural Voice (54 Voices, CPU ONNX)        │
│ • Ultron Auto-Heal Sentry (AST Patching & Crucible)     │
│ • NASA APOD Engine       • 3D HoloGlobe Radar          │
└─────────────────────────────────────────────────────────┘
```

---

## 🤝 Community & Support

* 🎬 **YouTube**: [Buildonaut - AI](https://www.youtube.com/@Buildonaut-AI) *(Tutorials, feature breakdowns & builds)*
* 💬 **Discord**: [Join our Community](https://discord.gg/c9xhxSqURx)
* 📸 **Instagram**: [@buildonaut.dev](https://www.instagram.com/buildonaut.dev/)
* 🌐 **Ecosystem**:
  - [Brahma Sol Official Web](https://brahma-sol.netlify.app)
  - [Brahma Evo](https://brahma-evo.netlify.app)
  - [Brahma Echo](https://brahma-echo.netlify.app)

---

## 📜 License

Brahma Sol is released under the **Brahma Sol Source-Available Personal Use License**.  
Free for personal, educational, and academic use. Redistribution, SaaS commercialization, or selling packaged copies without prior written consent is strictly prohibited. See [`LICENSE`](LICENSE) for full details.

---

<div align="center">
<sub>Crafted with passion by <b>Suryaansh Tiwari</b> (<a href="https://www.youtube.com/@Buildonaut-AI">Buildonaut</a>) & TiTech Prabha Solutions.</sub>
</div>
