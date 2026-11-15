/**
 * installer/html/installer.js
 * ===========================
 * Brahma Sol Celestial Installer Engine:
 * 1. 60 FPS Three.js 3D Character Viewport with real-time dances & reactions
 * 2. 4-Step Interactive Flow: Welcome -> Location -> Install -> Launch
 * 3. Celestial Ocean Silk Background Shader Canvas
 * 4. QWebChannel bridge for native Windows directory picker, disk telemetry & extraction
 */

(function () {
  'use strict';

  // State Management
  let currentStep = 1;
  const TOTAL_STEPS = 4;
  let pyBridge = null;
  let targetInstallPath = "C:\\Program Files\\Brahma Sol";

  // Three.js Scene Variables
  let scene, camera, renderer, mixer, clock;
  let avatarModel = null;
  let currentAction = null;
  let activeClipName = "Dance Simple";
  let actionsMap = new Map();
  let allClips = [];

  // Available Fun Dances & Expressive Clips
  const DANCE_PLAYLIST = [
    { name: "Dance Simple", label: "Joyful Groove" },
    { name: "Dance Funky", label: "Funky Electro" },
    { name: "Victory Fist Pump", label: "Fist Pump Hype" },
    { name: "Victory", label: "Triumphant Cheer" },
    { name: "Cheer One arm", label: "One-Arm Hype" },
    { name: "Greeting", label: "Friendly Welcome" },
    { name: "Jump_Start", label: "Acrobatic Leap" }
  ];
  let currentDanceIndex = 0;

  // ------------------------------------------------------------
  // 1. CELESTIAL BACKGROUND CANVAS (ORGANIC LIQUID SILK WAVES)
  // ------------------------------------------------------------
  function initCelestialBackground() {
    const canvas = document.getElementById("celestial-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let width = (canvas.width = canvas.parentElement.clientWidth);
    let height = (canvas.height = canvas.parentElement.clientHeight);

    window.addEventListener("resize", () => {
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    });

    let time = 0;

    function renderWaves() {
      requestAnimationFrame(renderWaves);
      time += 0.008;

      ctx.clearRect(0, 0, width, height);

      // Wave Layer 1: Pearl Silk Wave (Deep soft ivory)
      ctx.beginPath();
      ctx.moveTo(0, height);
      ctx.lineTo(0, height * 0.55);
      for (let x = 0; x <= width; x += 18) {
        const y = height * 0.58 + Math.sin(x * 0.0018 + time * 0.8) * 38 + Math.cos(x * 0.0035 - time * 0.5) * 20;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(width, height);
      ctx.closePath();

      const pearlGrad = ctx.createLinearGradient(0, height * 0.45, width, height);
      pearlGrad.addColorStop(0, "rgba(245, 240, 230, 0.45)");
      pearlGrad.addColorStop(0.5, "rgba(235, 225, 205, 0.28)");
      pearlGrad.addColorStop(1, "rgba(255, 255, 255, 0.12)");
      ctx.fillStyle = pearlGrad;
      ctx.fill();

      // Wave Layer 2: Metallic Champagne-Gold Current
      ctx.beginPath();
      ctx.moveTo(0, height);
      ctx.lineTo(0, height * 0.72);
      for (let x = 0; x <= width; x += 16) {
        const y = height * 0.70 + Math.sin(x * 0.0024 - time * 1.1) * 32 + Math.cos(x * 0.0048 + time * 0.7) * 16;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(width, height);
      ctx.closePath();

      const goldGrad = ctx.createLinearGradient(0, height * 0.65, width, height);
      goldGrad.addColorStop(0, "rgba(198, 163, 92, 0.28)");
      goldGrad.addColorStop(0.4, "rgba(232, 216, 184, 0.18)");
      goldGrad.addColorStop(1, "rgba(198, 163, 92, 0.05)");
      ctx.fillStyle = goldGrad;
      ctx.fill();

      // Crest line
      ctx.beginPath();
      for (let x = 0; x <= width; x += 16) {
        const y = height * 0.70 + Math.sin(x * 0.0024 - time * 1.1) * 32 + Math.cos(x * 0.0048 + time * 0.7) * 16;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "rgba(198, 163, 92, 0.45)";
      ctx.lineWidth = 1.8;
      ctx.stroke();

      // Wave Layer 3: Ice-Blue Energy Highlights
      ctx.beginPath();
      ctx.moveTo(0, height);
      ctx.lineTo(0, height * 0.86);
      for (let x = 0; x <= width; x += 14) {
        const y = height * 0.84 + Math.sin(x * 0.0032 + time * 1.4) * 22 + Math.cos(x * 0.006 - time * 0.9) * 12;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(width, height);
      ctx.closePath();

      const cyanGrad = ctx.createLinearGradient(0, height * 0.80, 0, height);
      cyanGrad.addColorStop(0, "rgba(56, 189, 248, 0.24)");
      cyanGrad.addColorStop(1, "rgba(2, 132, 199, 0.06)");
      ctx.fillStyle = cyanGrad;
      ctx.fill();
    }

    renderWaves();
  }

  // ------------------------------------------------------------
  // 2. THREE.JS 3D BRAHMA SOL AVATAR & DANCE CONTROLLER
  // ------------------------------------------------------------
  function init3DStage() {
    const container = document.getElementById("companion-3d-stage");
    if (!container) return;

    clock = new THREE.Clock();
    scene = new THREE.Scene();

    const w = container.clientWidth || 440;
    const h = container.clientHeight || 600;

    camera = new THREE.PerspectiveCamera(34, w / h, 0.1, 100);
    camera.position.set(0, 0.05, 2.75);
    camera.lookAt(0, -0.05, 0);

    renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
      precision: "mediump"
    });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1.0, 1.5));
    renderer.setClearColor(0x000000, 0);
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);

    // Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.25);
    scene.add(ambientLight);

    // Golden Key Spotlight
    const goldKey = new THREE.DirectionalLight(0xE8D8B8, 1.8);
    goldKey.position.set(2, 3, 2.5);
    scene.add(goldKey);

    // Ice-Blue Rim Light
    const iceRim = new THREE.DirectionalLight(0x38BDF8, 2.2);
    iceRim.position.set(-2, 1.5, -2);
    scene.add(iceRim);

    // Soft Floor Fill
    const floorBounce = new THREE.DirectionalLight(0xC5A059, 0.6);
    floorBounce.position.set(0, -2, 1.5);
    scene.add(floorBounce);

    // Load Model
    const loader = new THREE.GLTFLoader();
    // Resolve relative model path
    const modelCandidates = [
      "../../assets/avatar/robot.glb",
      "../assets/avatar/robot.glb",
      "assets/avatar/robot.glb",
      "https://storage.googleapis.com/brahma-assets/robot.glb"
    ];

    function tryLoad(index) {
      if (index >= modelCandidates.length) {
        console.warn("[Installer 3D] Could not load model from candidates.");
        return;
      }
      const path = modelCandidates[index];
      loader.load(
        path,
        (gltf) => {
          avatarModel = gltf.scene;
          allClips = gltf.animations || [];
          console.log(`[Installer 3D] Model loaded with ${allClips.length} animations.`);

          avatarModel.scale.set(1.02, 1.02, 1.02);
          avatarModel.position.set(0, -0.32, 0);
          scene.add(avatarModel);

          mixer = new THREE.AnimationMixer(avatarModel);
          allClips.forEach(clip => {
            actionsMap.set(clip.name, mixer.clipAction(clip));
          });

          // Play initial welcome dance!
          playClipWithCallback("Greeting", 0.2, false, () => {
            playClip("Dance Simple", 0.35, true);
          });
        },
        undefined,
        () => tryLoad(index + 1)
      );
    }

    tryLoad(0);

    // Mouse drag rotation
    let isMouseDown = false;
    let prevMouseX = 0;
    container.addEventListener("mousedown", (e) => {
      isMouseDown = true;
      prevMouseX = e.clientX;
    });
    window.addEventListener("mouseup", () => { isMouseDown = false; });
    window.addEventListener("mousemove", (e) => {
      if (isMouseDown && avatarModel) {
        const deltaX = e.clientX - prevMouseX;
        avatarModel.rotation.y += deltaX * 0.015;
        prevMouseX = e.clientX;
      }
    });

    window.addEventListener("resize", () => {
      const newW = container.clientWidth;
      const newH = container.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    });

    // Animate Loop
    function animate() {
      requestAnimationFrame(animate);
      const delta = clock ? clock.getDelta() : 0.016;
      if (mixer) mixer.update(delta);
      renderer.render(scene, camera);
    }

    animate();
  }

  function playClip(clipName, blendTime = 0.3, loop = true) {
    if (!mixer || !actionsMap.has(clipName)) return;
    const newAction = actionsMap.get(clipName);
    if (currentAction === newAction && newAction.isRunning()) return;

    newAction.reset();
    newAction.setEffectiveTimeScale(1.0);
    newAction.setEffectiveWeight(1.0);
    newAction.loop = loop ? THREE.LoopRepeat : THREE.LoopOnce;
    newAction.clampWhenFinished = !loop;

    if (currentAction) {
      currentAction.crossFadeTo(newAction, blendTime, true);
    }
    newAction.play();
    currentAction = newAction;
    activeClipName = clipName;

    // Update Dance Badge
    const badge = document.getElementById("active-dance-name");
    if (badge) badge.innerText = clipName;
  }

  function playClipWithCallback(clipName, blendTime, loop, onFinished) {
    playClip(clipName, blendTime, loop);
    if (onFinished && mixer) {
      const listener = (e) => {
        if (e.action.getClip().name === clipName) {
          mixer.removeEventListener("finished", listener);
          onFinished();
        }
      };
      mixer.addEventListener("finished", listener);
    }
  }

  // ------------------------------------------------------------
  // 3. STEP WIZARD FLOW & STEP CHOREOGRAPHY
  // ------------------------------------------------------------
  function goToStep(stepNumber) {
    if (stepNumber < 1 || stepNumber > TOTAL_STEPS) return;
    currentStep = stepNumber;

    // Update Ribbon Items
    document.querySelectorAll(".ribbon-item").forEach(item => {
      const stepIdx = parseInt(item.getAttribute("data-step"), 10);
      item.classList.remove("active", "completed");
      if (stepIdx === currentStep) {
        item.classList.add("active");
      } else if (stepIdx < currentStep) {
        item.classList.add("completed");
      }
    });

    // Update Step Containers
    document.querySelectorAll(".step-container").forEach(c => {
      c.classList.remove("active");
    });
    const target = document.getElementById(`step-${currentStep}`);
    if (target) target.classList.add("active");

    // Dynamic 3D Model Reaction per Step!
    if (currentStep === 1) {
      playClip("Dance Simple", 0.35, true);
    } else if (currentStep === 2) {
      playClip("Idle_FoldArms", 0.35, true);
    } else if (currentStep === 3) {
      // Energetic dance while installing!
      playClip("Dance Funky", 0.35, true);
      startInstallationProcess();
    } else if (currentStep === 4) {
      // Triumphant celebration on complete!
      playClip("Victory Fist Pump", 0.35, false);
      setTimeout(() => {
        playClip("Victory", 0.35, true);
      }, 2300);
    }
  }

  function cycleNextDance() {
    currentDanceIndex = (currentDanceIndex + 1) % DANCE_PLAYLIST.length;
    const item = DANCE_PLAYLIST[currentDanceIndex];
    playClip(item.name, 0.35, true);
  }

  // ------------------------------------------------------------
  // 4. INSTALLATION PROCESS (SIMULATION & PYWEBCHANNEL BRIDGING)
  // ------------------------------------------------------------
  function startInstallationProcess() {
    const fill = document.getElementById("install-progress-fill");
    const pct = document.getElementById("install-pct-label");
    const component = document.getElementById("install-component-label");
    const speed = document.getElementById("metric-speed");
    const deployed = document.getElementById("metric-deployed");
    const eta = document.getElementById("metric-eta");
    const logBox = document.getElementById("log-drawer");

    const installSteps = [
      { name: "Verifying target destination and permissions...", pct: 5, log: "[SYSTEM] Verified directory write access." },
      { name: "Extracting Brahma Sol Core Binaries...", pct: 15, log: "[EXTRACT] Unpacking BrahmaEvo runtime engine..." },
      { name: "Deploying 3D Avatar Assets & Skeletal Mesh...", pct: 32, log: "[3D-ASSETS] Deploying robot.glb (62 motion tracks)..." },
      { name: "Unpacking Kokoro-82M Neural Voice Model...", pct: 50, log: "[TTS] Initializing Kokoro offline speech weights..." },
      { name: "Compiling Autonomous Locomotion Sentinels...", pct: 68, log: "[LOCOMOTION] Linking Proprioception & Navigation..." },
      { name: "Configuring Passive Sensorium & Memory Cortex...", pct: 82, log: "[SENSORIUM] Initializing workspace activity watchers..." },
      { name: "Creating Windows Desktop & Start Menu Shortcuts...", pct: 94, log: "[SHORTCUTS] Registered Brahma Sol desktop icon." },
      { name: "Finalizing system registration...", pct: 100, log: "[COMPLETE] Brahma Sol installation successful!" }
    ];

    // Check if running under PyQt6 QWebChannel bridge
    if (pyBridge && pyBridge.startNativeInstall) {
      pyBridge.startNativeInstall(
        targetInstallPath,
        document.getElementById("chk-desktop").checked,
        document.getElementById("chk-startmenu").checked,
        document.getElementById("chk-startup").checked
      );
      return;
    }

    // High-fidelity web/preview simulation
    let idx = 0;
    const interval = setInterval(() => {
      if (idx >= installSteps.length) {
        clearInterval(interval);
        setTimeout(() => { goToStep(4); }, 800);
        return;
      }

      const item = installSteps[idx];
      if (fill) fill.style.width = `${item.pct}%`;
      if (pct) pct.innerText = `${item.pct}%`;
      if (component) component.innerText = item.name;

      // Update metrics
      const mbWritten = ((item.pct / 100) * 2840).toFixed(0);
      if (deployed) deployed.innerText = `${(mbWritten / 1024).toFixed(1)} GB / 2.8 GB`;
      if (speed) speed.innerText = `${(48 + Math.random() * 12).toFixed(1)} MB/s`;
      const secondsLeft = Math.max(1, Math.round((100 - item.pct) * 0.14));
      if (eta) eta.innerText = `~${secondsLeft}s remaining`;

      // Log append
      if (logBox) {
        const line = document.createElement("div");
        line.className = item.pct === 100 ? "log-line success" : "log-line active";
        line.innerText = item.log;
        logBox.appendChild(line);
        logBox.scrollTop = logBox.scrollHeight;
      }

      idx++;
    }, 700);
  }

  // ------------------------------------------------------------
  // 5. NATIVE PYQT6 QWEBCHANNEL INTEGRATION
  // ------------------------------------------------------------
  function setupQWebChannel() {
    if (typeof QWebChannel !== "undefined" && window.qt && window.qt.webChannelTransport) {
      new QWebChannel(window.qt.webChannelTransport, function (channel) {
        pyBridge = channel.objects.pyBridge;
        console.log("[Installer Bridge] Connected to Python backend.");

        // Wire native signals
        if (pyBridge.installProgressChanged) {
          pyBridge.installProgressChanged.connect((pctVal, statusTxt, logMsg) => {
            const fill = document.getElementById("install-progress-fill");
            const pct = document.getElementById("install-pct-label");
            const component = document.getElementById("install-component-label");
            const logBox = document.getElementById("log-drawer");
            const speed = document.getElementById("metric-speed");
            const deployed = document.getElementById("metric-deployed");
            const eta = document.getElementById("metric-eta");

            if (fill) fill.style.width = `${pctVal}%`;
            if (pct) pct.innerText = `${pctVal}%`;
            if (component) component.innerText = statusTxt;

            // Dynamically update deployment counters
            if (deployed) {
              const gb = ((pctVal / 100) * 2.8).toFixed(1);
              deployed.innerText = `${gb} GB / 2.8 GB`;
            }
            if (speed) {
              const spd = (54.2 + ((pctVal * 3) % 8.5)).toFixed(1);
              speed.innerText = `~${spd} MB/s`;
            }
            if (eta) {
              const sec = Math.max(0, Math.round((100 - pctVal) * 0.14));
              eta.innerText = sec > 0 ? `~${sec}s remaining` : "Finalizing...";
            }

            if (logBox && logMsg) {
              const line = document.createElement("div");
              line.className = pctVal >= 100 ? "log-line success" : "log-line active";
              line.innerText = logMsg;
              logBox.appendChild(line);
              logBox.scrollTop = logBox.scrollHeight;
            }

            if (pctVal >= 100) {
              setTimeout(() => { goToStep(4); }, 800);
            }
          });
        }

        if (pyBridge.installErrorOccurred) {
          pyBridge.installErrorOccurred.connect((errMsg) => {
            const logBox = document.getElementById("log-drawer");
            if (logBox) {
              const line = document.createElement("div");
              line.className = "log-line error";
              line.style.color = "#EF4444";
              line.innerText = `[NOTICE] ${errMsg}`;
              logBox.appendChild(line);
              logBox.scrollTop = logBox.scrollHeight;
            }
          });
        }

        // Initialize default path from Python
        if (pyBridge.getDefaultInstallPath) {
          pyBridge.getDefaultInstallPath((defaultPath) => {
            if (defaultPath) {
              targetInstallPath = defaultPath;
              const input = document.getElementById("install-path-input");
              if (input) input.value = defaultPath;
              updateDiskMetrics(defaultPath);
            }
          });
        }
      });
    }
  }

  function updateDiskMetrics(path) {
    if (pyBridge && pyBridge.getDiskMetrics) {
      pyBridge.getDiskMetrics(path, (freeGB, totalGB) => {
        const freeLabel = document.getElementById("disk-free-label");
        const fillBar = document.getElementById("disk-fill-bar");
        if (freeLabel) freeLabel.innerText = `${freeGB} GB Free`;
        if (fillBar) fillBar.style.width = `${Math.min(100, Math.round((2.8 / freeGB) * 100))}%`;
      });
    } else {
      // Mock metrics for browser preview
      const freeLabel = document.getElementById("disk-free-label");
      if (freeLabel) freeLabel.innerText = "142.8 GB Free";
    }
  }

  // ------------------------------------------------------------
  // 6. UI EVENT BINDINGS & BUTTON WIRING
  // ------------------------------------------------------------
  window.addEventListener("DOMContentLoaded", () => {
    initCelestialBackground();
    init3DStage();
    setupQWebChannel();

    // Step 1: Welcome
    document.getElementById("btn-step1-next")?.addEventListener("click", () => {
      goToStep(2);
    });

    // Step 2: Storage
    document.getElementById("btn-step2-back")?.addEventListener("click", () => {
      goToStep(1);
    });
    document.getElementById("btn-step2-next")?.addEventListener("click", () => {
      goToStep(3);
    });

    document.getElementById("btn-browse-path")?.addEventListener("click", () => {
      if (pyBridge && pyBridge.browseDirectory) {
        pyBridge.browseDirectory(targetInstallPath, (chosenPath) => {
          if (chosenPath) {
            targetInstallPath = chosenPath;
            const input = document.getElementById("install-path-input");
            if (input) input.value = chosenPath;
            updateDiskMetrics(chosenPath);
          }
        });
      } else {
        alert("Directory browser is active when launched through the installer executable.");
      }
    });

    // Step 4: Launch
    document.getElementById("btn-launch-app")?.addEventListener("click", () => {
      if (pyBridge && pyBridge.launchApplication) {
        pyBridge.launchApplication(targetInstallPath);
      } else {
        alert("Brahma Sol launch triggered! Ready to inhabit your desktop.");
      }
    });

    document.getElementById("btn-finish-close")?.addEventListener("click", () => {
      if (pyBridge && pyBridge.closeWindow) {
        pyBridge.closeWindow();
      } else {
        window.close();
      }
    });

    // Window Minimize & Close Buttons
    document.getElementById("win-min")?.addEventListener("click", () => {
      if (pyBridge && pyBridge.minimizeWindow) pyBridge.minimizeWindow();
    });
    document.getElementById("win-close")?.addEventListener("click", () => {
      if (pyBridge && pyBridge.closeWindow) pyBridge.closeWindow();
      else window.close();
    });

    // Dance Switcher
    document.getElementById("btn-cycle-dance")?.addEventListener("click", cycleNextDance);

    // Initial Path setup
    const pathInput = document.getElementById("install-path-input");
    if (pathInput) pathInput.value = targetInstallPath;
  });

})();
