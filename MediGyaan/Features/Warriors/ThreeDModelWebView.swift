import SwiftUI
import WebKit

/// Interactive 3D Model WebGL Viewer for MediGyaan.
/// Renders `.glb` 3D models (Avatar Warriors & Medical Equipment) using Three.js,
/// OrbitControls, and GLTFLoader with GPU-accelerated Metal/WebKit pipeline.
struct ThreeDModelWebView: UIViewRepresentable {

    let modelName: String
    var glowColorHex: String = "#00E5FF"
    var autoRotate: Bool = true
    var cameraDistance: Double = 3.2
    var cameraHeight: Double = 1.2
    var onModelLoaded: (() -> Void)? = nil

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.isScrollEnabled = false
        webView.scrollView.bounces = false
        webView.navigationDelegate = context.coordinator

        let html = generateViewerHTML(
            modelName: modelName,
            glowHex: glowColorHex,
            camDist: cameraDistance,
            camHeight: cameraHeight,
            autoRotate: autoRotate
        )

        webView.loadHTMLString(html, baseURL: Bundle.main.bundleURL)
        RemoteLogger.log(tag: "ThreeDModelWebView_Load", message: "Loading 3D model: \(modelName)")
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {
        if context.coordinator.currentModel != modelName ||
            context.coordinator.currentGlow != glowColorHex {
            context.coordinator.currentModel = modelName
            context.coordinator.currentGlow = glowColorHex

            let safeModel = modelName.replacingOccurrences(of: "'", with: "\\'")
            let safeGlow = glowColorHex.replacingOccurrences(of: "'", with: "\\'")
            let script = "if (window.loadModel) { window.loadModel('\(safeModel)', '\(safeGlow)', \(cameraDistance), \(cameraHeight)); }"
            uiView.evaluateJavaScript(script, completionHandler: nil)
        }

        if context.coordinator.currentAutoRotate != autoRotate {
            context.coordinator.currentAutoRotate = autoRotate
            let script = "if (window.toggleAutoRotate) { window.toggleAutoRotate(\(autoRotate)); }"
            uiView.evaluateJavaScript(script, completionHandler: nil)
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(
            model: modelName,
            glow: glowColorHex,
            autoRotate: autoRotate,
            onLoaded: onModelLoaded
        )
    }

    class Coordinator: NSObject, WKNavigationDelegate {
        var currentModel: String
        var currentGlow: String
        var currentAutoRotate: Bool
        var onLoaded: (() -> Void)?

        init(model: String, glow: String, autoRotate: Bool, onLoaded: (() -> Void)?) {
            self.currentModel = model
            self.currentGlow = glow
            self.currentAutoRotate = autoRotate
            self.onLoaded = onLoaded
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            onLoaded?()
        }
    }

    // MARK: - Embedded Three.js HTML Viewer Template

    private func generateViewerHTML(
        modelName: String,
        glowHex: String,
        camDist: Double,
        camHeight: Double,
        autoRotate: Bool
    ) -> String {
        return """
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
          <style>
            * { margin: 0; padding: 0; box-sizing: border-box; -webkit-user-select: none; }
            html, body { width: 100%; height: 100%; overflow: hidden; background: transparent; }
            #canvas-container { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }
            #loader {
              position: absolute;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
              width: 32px;
              height: 32px;
              border: 3px solid rgba(0, 229, 255, 0.2);
              border-top-color: #00e5ff;
              border-radius: 50%;
              animation: spin 0.8s linear infinite;
              pointer-events: none;
              transition: opacity 0.3s;
            }
            @keyframes spin { 0% { transform: translate(-50%, -50%) rotate(0deg); } 100% { transform: translate(-50%, -50%) rotate(360deg); } }
            .hidden { opacity: 0; pointer-events: none; }
          </style>
          <script src="js/three.min.js"></script>
          <script src="js/GLTFLoader.js"></script>
          <script src="js/OrbitControls.js"></script>
        </head>
        <body>
          <div id="canvas-container"></div>
          <div id="loader"></div>

          <script>
            let scene, camera, renderer, controls, currentModelGroup, rimLight;
            let loaderEl = document.getElementById('loader');
            let initialCamDistance = \(camDist);
            let initialCamHeight = \(camHeight);

            function init() {
              const container = document.getElementById('canvas-container');
              const width = window.innerWidth;
              const height = window.innerHeight;

              scene = new THREE.Scene();

              camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
              camera.position.set(0, initialCamHeight, initialCamDistance);

              renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance' });
              renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
              renderer.setSize(width, height);
              renderer.setClearColor(0x000000, 0);
              renderer.outputEncoding = THREE.sRGBEncoding;
              container.appendChild(renderer.domElement);

              controls = new THREE.OrbitControls(camera, renderer.domElement);
              controls.enableDamping = true;
              controls.dampingFactor = 0.08;
              controls.enableZoom = true;
              controls.zoomSpeed = 1.0;
              controls.enablePan = false;
              controls.autoRotate = \(autoRotate ? "true" : "false");
              controls.autoRotateSpeed = 1.8;
              controls.minDistance = 0.8;
              controls.maxDistance = 7.0;
              controls.target.set(0, 0.2, 0);

              // Lighting Setup
              const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
              scene.add(ambientLight);

              const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
              keyLight.position.set(3, 4, 3);
              scene.add(keyLight);

              const fillLight = new THREE.DirectionalLight(0x7dd3fc, 1.2);
              fillLight.position.set(-3, 2, 2);
              scene.add(fillLight);

              rimLight = new THREE.DirectionalLight(parseInt('\(glowHex)'.replace('#', '0x'), 16) || 0x00e5ff, 2.0);
              rimLight.position.set(0, 3, -3);
              scene.add(rimLight);

              // Ground Pedestal Glow Ring
              const ringGeo = new THREE.RingGeometry(0.8, 0.86, 48);
              const ringMat = new THREE.MeshBasicMaterial({
                color: parseInt('\(glowHex)'.replace('#', '0x'), 16) || 0x00e5ff,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.4
              });
              const ring = new THREE.Mesh(ringGeo, ringMat);
              ring.rotation.x = Math.PI / 2;
              ring.position.y = -0.02;
              scene.add(ring);

              window.addEventListener('resize', onWindowResize, false);
              animate();

              loadModel('\(modelName)', '\(glowHex)', initialCamDistance, initialCamHeight);
            }

            function onWindowResize() {
              if (!camera || !renderer) return;
              camera.aspect = window.innerWidth / window.innerHeight;
              camera.updateProjectionMatrix();
              renderer.setSize(window.innerWidth, window.innerHeight);
            }

            function animate() {
              requestAnimationFrame(animate);
              if (controls) controls.update();
              if (renderer && scene && camera) renderer.render(scene, camera);
            }

            window.loadModel = function(modelFile, glowHex, camDist, camHeight) {
              if (!modelFile) return;
              if (loaderEl) loaderEl.classList.remove('hidden');

              if (rimLight && glowHex) {
                const hexVal = parseInt(glowHex.replace('#', '0x'), 16);
                if (!isNaN(hexVal)) rimLight.color.setHex(hexVal);
              }

              if (currentModelGroup) {
                scene.remove(currentModelGroup);
                currentModelGroup = null;
              }

              const loader = new THREE.GLTFLoader();
              loader.load(
                modelFile,
                function(gltf) {
                  currentModelGroup = gltf.scene;

                  // Compute Bounding Box to center & normalize scale
                  const box = new THREE.Box3().setFromObject(currentModelGroup);
                  const size = new THREE.Vector3();
                  box.getSize(size);
                  const center = new THREE.Vector3();
                  box.getCenter(center);

                  const maxDim = Math.max(size.x, size.y, size.z);
                  const targetSize = 2.0;
                  const scale = targetSize / (maxDim || 1.0);
                  currentModelGroup.scale.set(scale, scale, scale);

                  currentModelGroup.position.x = -center.x * scale;
                  currentModelGroup.position.y = -box.min.y * scale;
                  currentModelGroup.position.z = -center.z * scale;

                  scene.add(currentModelGroup);
                  if (loaderEl) loaderEl.classList.add('hidden');
                },
                undefined,
                function(error) {
                  console.error('Error loading 3D model:', error);
                  if (loaderEl) loaderEl.classList.add('hidden');
                }
              );
            };

            window.toggleAutoRotate = function(enabled) {
              if (controls) controls.autoRotate = !!enabled;
            };

            window.resetCamera = function() {
              if (camera && controls) {
                camera.position.set(0, initialCamHeight, initialCamDistance);
                controls.target.set(0, 0.2, 0);
                controls.update();
              }
            };

            if (document.readyState === 'complete' || document.readyState === 'interactive') {
              setTimeout(init, 10);
            } else {
              window.addEventListener('DOMContentLoaded', init);
            }
          </script>
        </body>
        </html>
        """
    }
}
