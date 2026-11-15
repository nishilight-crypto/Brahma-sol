# Brahma SOL — TTS Engine License Inventory & Attribution

This document details the licensing, copyrights, and commercial distribution compliance for the local speech synthesis engine integrated into Brahma SOL.

---

## 1. Primary Engine: Kokoro-82M

- **Model:** Kokoro-82M (v1.0)
- **Author/Creator:** Hexgrad (`hexgrad/Kokoro-82M`)
- **Repository:** https://huggingface.co/hexgrad/Kokoro-82M
- **ONNX Implementation:** `thewh1teagle/kokoro-onnx`
- **License:** Apache License 2.0
- **Summary:** Permissive open-source license allowing commercial use, modification, distribution, and private use, provided copyright and license notices are preserved.

### Configured Voice Packs:
- **English Voice:** `bm_lewis` (British English Male — Lewis)
  - **License:** Apache 2.0
- **Hindi Voice:** `hm_omega` (Hindi Male — Omega)
  - **License:** Apache 2.0
- **Voice Embeddings:** Distributed under Apache License 2.0.

---

## 2. ONNX Runtime & Acceleration Providers

- **Component:** `onnxruntime` / `onnxruntime-directml`
- **Maintainer:** Microsoft Corporation
- **License:** MIT License
- **Hardware Acceleration:** Microsoft DirectML / CPUExecutionProvider
- **Summary:** Permissive license granting royalty-free commercial distribution and sublicensing.

---

## 3. Phonemization & G2P Runtime

- **Component:** `espeakng-loader` / `espeak-ng`
- **Maintainer:** espeak-ng team / thewh1teagle
- **License:** GNU General Public License v3.0 (GPLv3) / LGPLv3
- **Summary:** Provides phoneme mapping and G2P tables for English, Hindi (Devanagari), and other supported language families.

---

## 4. Audio I/O Runtime

- **Component:** `sounddevice` (PortAudio wrapper)
- **License:** MIT License
- **Component:** `soundfile` (libsndfile wrapper)
- **License:** BSD 3-Clause License
