package com.corp.tankosmobileapp

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Paint
import android.graphics.Typeface
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Bundle
import android.util.Base64
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException

// ═══════════════════════════════════════════════════════════════════════════
//  Anti-Gravity Glassmorphism Theme (Dark Space Aesthetic)
// ═══════════════════════════════════════════════════════════════════════════
object CyberTheme {
    val BG = Color(0xFF0A0A10)
    val BG2 = Color(0xFF0F101A)
    val BG_CARD = Color(0xB2141623) // Semi-transparent glass background
    
    // Core Neon Accents
    val ACCENT_CYAN = Color(0xFF00E5FF)
    val ACCENT_PURPLE = Color(0xFF7C4DFF)
    val NEON_BLUE = Color(0xFF448AFF)
    val NEON_PURPLE = Color(0xFFB388FF)
    val NEON_GREEN = Color(0xFF69F0AE)
    val NEON_PINK = Color(0xFFFF4081)
    
    val TEXT = Color(0xFFE8EAF6)
    val DIM = Color(0xFF5C6BC0)

    val HEADER_GRADIENT = Brush.horizontalGradient(
        colors = listOf(Color(0xFF00E5FF), Color(0xFF7C4DFF))
    )
}

class MainActivity : ComponentActivity() {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .connectionPool(okhttp3.ConnectionPool(2, 5, java.util.concurrent.TimeUnit.MINUTES))
        .build()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            Surface(
                modifier = Modifier.fillMaxSize(),
                color = CyberTheme.BG
            ) {
                MainScreen(client)
            }
        }
    }
}

enum class MsgType { USER, TANK_REPLY, THINKING, TOOL_EXEC }
data class ChatBubble(
    val sender: String,
    val text: String,
    val type: MsgType,
    val modelInfo: String = ""
)

data class TorrentHit(
    val title: String,
    val size: String,
    val seeders: Int,
    val leechers: Int,
    val source: String,
    val accessUri: String
)
data class ActiveDownload(
    val gid: String,
    val progress: Float = 0f,
    val speed: String = "0 KB/s",
    val status: String = "Checking...",
    val ttsText: String = ""
)
data class TrendingItem(
    val title: String,
    val category: String,
    val seeds: Int,
    val leechs: Int
)
data class TrailerItem(
    val title: String,
    val videoTitle: String,
    val youtubeId: String,
    val channel: String,
    val duration: String
)

data class DetectionBox(
    val x1: Float,
    val y1: Float,
    val x2: Float,
    val y2: Float,
    val label: String,
    val conf: Float
)

// Connectivity Detector Utility — checks active network AND all networks as fallback
fun isWifiConnected(context: Context): Boolean {
    val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    // Primary: check active network
    val activeNetwork = cm.activeNetwork
    if (activeNetwork != null) {
        val capabilities = cm.getNetworkCapabilities(activeNetwork)
        if (capabilities != null && capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
            return true
        }
    }
    // Fallback: check all registered networks for any WiFi connection
    @Suppress("DEPRECATION")
    val allNetworks = cm.allNetworks
    for (network in allNetworks) {
        val capabilities = cm.getNetworkCapabilities(network)
        if (capabilities != null && capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
            return true
        }
    }
    return false
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(client: OkHttpClient) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    // Host configurations (WiFi vs Tailscale VPN Fallbacks)
    var jetsonWifiHost by remember { mutableStateOf("192.168.31.74") }
    var jetsonTailscaleHost by remember { mutableStateOf("100.122.31.46") }
    var jetsonPort by remember { mutableStateOf("8082") }

    var unoqWifiHost by remember { mutableStateOf("192.168.31.72") }
    var unoqTailscaleHost by remember { mutableStateOf("100.84.235.7") }
    var unoqPort by remember { mutableStateOf("80") }

    var vpsTailscaleHost by remember { mutableStateOf("100.71.127.19") }
    var vpsPort by remember { mutableStateOf("9100") } // REST API endpoint per port-scanner findings
    var vpsToken by remember { mutableStateOf("CHANGE_ME_VPS_TOKEN") }

    var authHeader by remember { mutableStateOf("Bearer bench-key") }

    // Detected Wifi state helper (polls every second)
    var isWifiRouteActive by remember { mutableStateOf(isWifiConnected(context)) }
    LaunchedEffect(Unit) {
        val wifiUp = isWifiConnected(context)
        Log.i("DEV", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        Log.i("DEV", "🚀 TANK OS MOBILE — CONNECTION MAP")
        Log.i("DEV", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        Log.i("DEV", "  WiFi: ${if (wifiUp) "UP" else "DOWN"}  Route: ${if (wifiUp) "WIFI" else "TAILSCALE"}")
        Log.i("DEV", "  JETSON WiFi:    $jetsonWifiHost:$jetsonPort")
        Log.i("DEV", "  JETSON Tailscale: $jetsonTailscaleHost:$jetsonPort")
        Log.i("DEV", "  ARDUINO WiFi:    $unoqWifiHost:$unoqPort")
        Log.i("DEV", "  ARDUINO Tailscale: $unoqTailscaleHost:$unoqPort")
        Log.i("DEV", "  VPS Tailscale:   $vpsTailscaleHost:$vpsPort")
        Log.i("DEV", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        isWifiRouteActive = wifiUp
        while (true) {
            isWifiRouteActive = isWifiConnected(context)
            delay(1500)
        }
    }

    // Dynamic hosts resolvers
    val currentJetsonHost = if (isWifiRouteActive) jetsonWifiHost else jetsonTailscaleHost
    val currentUnoqHost = if (isWifiRouteActive) unoqWifiHost else unoqTailscaleHost

    // Dynamic Online/Offline states
    var isJetsonOnline by remember { mutableStateOf(false) }
    var isArduinoOnline by remember { mutableStateOf(false) }
    var isVpsOnline by remember { mutableStateOf(false) }

    // Navigation Tab state
    var selectedTab by remember { mutableStateOf(0) }
    val tabIcons = listOf("🎮", "📷", "📥", "📊", "⚙️", "🗺️")
    val tabLabels = listOf("Control", "Vision", "Torrents", "Stats", "Settings", "Map")
    val haptic = LocalHapticFeedback.current

    // Telemetry state
    var batteryText by remember { mutableStateOf("-- v (--%)") }
    var cpuTempText by remember { mutableStateOf("-- °C") }
    var estopStatus by remember { mutableStateOf(false) }
    var currentEmotion by remember { mutableStateOf("neutral") }
    var connectionStatus by remember { mutableStateOf("Disconnected") }
    var isTailscaleConnected by remember { mutableStateOf(false) }

    // Real-time System Statistics values
    var ramUsageText by remember { mutableStateOf("RAM: -- GB / -- GB") }
    var cpuLoadText by remember { mutableStateOf("CPU Load: -- %") }
    var diskUsageText by remember { mutableStateOf("Local Disk: -- free") }
    var processCountText by remember { mutableStateOf("Active tasks: --") }

    // Move speed / duration variables
    var driveSpeedLinear by remember { mutableFloatStateOf(0.3f) }
    var driveSpeedAngular by remember { mutableFloatStateOf(0.8f) }
    var driveDuration by remember { mutableFloatStateOf(1.0f) }

    // Autonomy states (Patrol & Dock)
    var currentPatrolMode by remember { mutableStateOf("stop") }
    var isDockArmed by remember { mutableStateOf(false) }

    // Camera image state & Camera source toggle (JETSON vs ARDUINO)
    var cameraBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var cameraStatusText by remember { mutableStateOf("No capture yet") }
    var frameW by remember { mutableFloatStateOf(0f) }
    var frameH by remember { mutableFloatStateOf(0f) }
    var activeCameraSource by remember { mutableStateOf("JETSON") } 

    // OpenCV/YOLO Bounding Box states
    var activeDetectionMode by remember { mutableStateOf("NONE") } // NONE, PERSONS, FACES
    val detectedBoxes = remember { mutableStateListOf<DetectionBox>() }
    var isLiveVisionPolling by remember { mutableStateOf(true) }

    // Motion detection states
    var isMotionDetectionActive by remember { mutableStateOf(true) }
    val motionBoxes = remember { mutableStateListOf<DetectionBox>() }
    var motionSensitivity by remember { mutableFloatStateOf(30f) } // pixel diff threshold
    var lastFrameHash by remember { mutableStateOf(0L) }
    var motionPixelCount by remember { mutableStateOf(0) }

    // LIDAR scan states
    data class LidarPoint(val angle: Float, val distance: Int)
    val lidarPoints = remember { mutableStateListOf<LidarPoint>() }
    var lidarMinDist by remember { mutableStateOf(0) }
    var lidarMaxDist by remember { mutableStateOf(0) }
    var lidarPointCount by remember { mutableStateOf(0) }
    var isLidarActive by remember { mutableStateOf(true) }
    var showLidarOverlay by remember { mutableStateOf(true) }
    var showVisualMap by remember { mutableStateOf(true) }

    // Rich Chat bubbles state
    val chatBubbles = remember { mutableStateListOf<ChatBubble>() }
    var chatInputText by remember { mutableStateOf("") }
    var isChatting by remember { mutableStateOf(false) }

    // Torrent Center States
    var torrentQuery by remember { mutableStateOf("") }
    var isSearchingTorrents by remember { mutableStateOf(false) }
    val torrentHits = remember { mutableStateListOf<TorrentHit>() }
    val activeDownloads = remember { mutableStateListOf<ActiveDownload>() }

    // VPS Services States (Trending catalog and active player controllers)
    val trendingList = remember { mutableStateListOf<TrendingItem>() }
    val trailersList = remember { mutableStateListOf<TrailerItem>() }
    var isFetchingVpsData by remember { mutableStateOf(false) }
    var vpsStatusLog by remember { mutableStateOf("VPS log idle...") }

    // Sys Diagnostics States
    var hardwareScanResult by remember { mutableStateOf("Click Scan to inspect board hardware...") }
    var isScanningHardware by remember { mutableStateOf(false) }
    
    // Providers & Testing
    val diagnosticProviders = listOf("groq_a", "groq_b", "groq_c", "gemini", "mistral", "nvidia_nemotron_light", "nvidia_vision", "nvidia_ultra", "phi3-local")
    var selectedDiagProvider by remember { mutableStateOf("gemini") }
    var diagTestPrompt by remember { mutableStateOf("Hello robot! Return connection latency.") }
    var diagTestResult by remember { mutableStateOf("Connection test log...") }
    var isTestingProvider by remember { mutableStateOf(false) }

    // Infinite breathing glowing transitions for device matrix
    val infiniteTransition = rememberInfiniteTransition(label = "glow_trans")
    val glowSpreadFloat by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 5f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "glow_dp"
    )
    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.25f,
        targetValue = 0.9f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "glow_alpha"
    )

    // Command dispatch helper
    fun dispatchCommand(cmdName: String, params: JSONObject, onResult: (JSONObject?) -> Unit) {
        scope.launch {
            try {
                Log.d("DEV", "▶ CMD[$cmdName] → $currentJetsonHost:$jetsonPort …")
                val url = "http://$currentJetsonHost:$jetsonPort/api/cmd/$cmdName"
                val bodyJson = JSONObject().apply {
                    put("params", params)
                }
                val requestBody = bodyJson.toString().toRequestBody("application/json".toMediaType())
                val requestBuilder = Request.Builder().url(url).post(requestBody)
                if (authHeader.isNotEmpty()) {
                    requestBuilder.addHeader("Authorization", authHeader)
                }
                val request = requestBuilder.build()

                val resultJson = withContext(Dispatchers.IO) {
                    client.newCall(request).execute().use { response ->
                        Log.i("DEV", "◀ CMD[$cmdName] ← HTTP ${response.code}")
                        if (response.isSuccessful) {
                            val resStr = response.body?.string() ?: ""
                            JSONObject(resStr)
                        } else {
                            null
                        }
                    }
                }
                onResult(resultJson)
            } catch (e: Exception) {
                Log.e("DEV", "✗ CMD[$cmdName] FAILED: ${e.javaClass.simpleName}: ${e.message}")
                onResult(null)
            }
        }
    }

    // Auto-telemetry & System stats polling — tries WiFi first, falls back to Tailscale
    LaunchedEffect(jetsonWifiHost, jetsonTailscaleHost, jetsonPort) {
        Log.i("DEV", "━━━ JETSON TELEM START ─── WiFi=$jetsonWifiHost:$jetsonPort  TS=$jetsonTailscaleHost:$jetsonPort")
        while (true) {
            val hostsToTry = listOf(
                jetsonWifiHost to "WiFi",
                jetsonTailscaleHost to "Tailscale"
            )
            var connected = false
            for ((host, routeName) in hostsToTry) {
                try {
                    Log.d("DEV", "▶ JETSON[$routeName] → $host:$jetsonPort …")
                    val url = "http://$host:$jetsonPort/api/cmd/telemetry"
                    val bodyJson = JSONObject().apply { put("params", JSONObject()) }
                    val requestBody = bodyJson.toString().toRequestBody("application/json".toMediaType())
                    val requestBuilder = Request.Builder().url(url).post(requestBody)
                    if (authHeader.isNotEmpty()) {
                        requestBuilder.addHeader("Authorization", authHeader)
                    }
                    val request = requestBuilder.build()

                    withContext(Dispatchers.IO) {
                        client.newCall(request).execute().use { response ->
                            val code = response.code
                            Log.i("DEV", "◀ JETSON[$routeName] ← HTTP $code")
                            if (code == 200) {
                                val resStr = response.body?.string() ?: ""
                                val resJson = JSONObject(resStr)
                                val result = resJson.optJSONObject("result")
                                if (result != null) {
                                    val batteryV = result.optDouble("battery_v", 0.0)
                                    val batteryPct = result.optDouble("battery_pct", 0.0) * 100
                                    val cpuC = result.optDouble("cpu_c", 0.0)
                                    val estop = result.optBoolean("estop", false)
                                    val emotion = result.optString("emotion", "neutral")

                                    batteryText = String.format("%.2fv (%.0f%%)", batteryV, batteryPct)
                                    cpuTempText = String.format("%.1f °C", cpuC)
                                    estopStatus = estop
                                    currentEmotion = emotion
                                    connectionStatus = "Online ($routeName)"
                                    isJetsonOnline = true

                                    val ramUsed = result.optDouble("ram_used_gb", 4.2)
                                    val ramTotal = result.optDouble("ram_total_gb", 8.0)
                                    val cpuLoad = result.optDouble("cpu_pct", 22.0)
                                    val diskFree = result.optDouble("disk_free_gb", 34.5)
                                    val activeTasks = result.optInt("active_tasks", 12)

                                    ramUsageText = String.format("RAM: %.1f GB / %.1f GB", ramUsed, ramTotal)
                                    cpuLoadText = String.format("CPU Load: %.0f %%", cpuLoad)
                                    diskUsageText = String.format("Local Disk: %.1f GB free", diskFree)
                                    processCountText = String.format("Active tasks: %d", activeTasks)
                                    Log.i("DEV", "  ✓ JETSON telemetry OK  bat=$batteryText  cpu=$cpuTempText  emotion=$emotion")
                                }
                                connected = true
                            } else if (code == 401) {
                                isJetsonOnline = true
                                connectionStatus = "Needs Auth ($routeName)"
                                connected = true
                                Log.i("DEV", "  ⚠ JETSON needs auth ($routeName)")
                            } else {
                                Log.w("DEV", "  ✗ JETSON HTTP $code ($routeName)")
                            }
                        }
                    }
                    if (connected) break
                } catch (e: Exception) {
                    Log.w("DEV", "  ✗ JETSON[$routeName] $host UNREACHABLE: ${e.javaClass.simpleName}: ${e.message}")
                }
            }
            if (!connected) {
                connectionStatus = "Offline"
                isJetsonOnline = false
                Log.w("DEV", "✗ JETSON ALL ROUTES FAILED")
            }
            delay(3000)
        }
    }

    // Live OpenCV/YOLO Camera & Object overlays polling loop (incorporates Dual USB Cameras selection)
    LaunchedEffect(isLiveVisionPolling, activeDetectionMode, activeCameraSource, currentJetsonHost, currentUnoqHost) {
        Log.i("DEV", "━━━ CAMERA POLLER START ─── source=$activeCameraSource  polling=$isLiveVisionPolling")
        while (isLiveVisionPolling) {
            try {
                if (activeCameraSource == "ARDUINO") {
                    Log.d("DEV", "▶ CAM[ARDUINO] → $currentUnoqHost:$unoqPort/snapshot.jpg …")
                    val snapUrl = "http://$currentUnoqHost:$unoqPort/snapshot.jpg"
                    val snapReq = Request.Builder().url(snapUrl).build()
                    val bytes = withContext(Dispatchers.IO) {
                        client.newCall(snapReq).execute().use { r ->
                            Log.i("DEV", "◀ CAM[ARDUINO] ← HTTP ${r.code}  ${if (r.isSuccessful) "${r.body?.contentLength() ?: 0} bytes" else "FAILED"}")
                            if (r.isSuccessful) r.body?.bytes() else null
                        }
                    }
                    if (bytes != null) {
                        cameraBitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                        detectedBoxes.clear()
                        isArduinoOnline = true
                    } else {
                        isArduinoOnline = false
                    }
                } else {
                    // Try direct serial camera endpoint first, fallback to bridge capture
                    var gotFrame = false
                    try {
                        val camUrl = "http://$currentJetsonHost:$jetsonPort/api/camera/snapshot?max_px=480"
                        Log.d("DEV", "▶ CAM[JETSON] → $camUrl …")
                        val camReq = Request.Builder().url(camUrl)
                        if (authHeader.isNotEmpty()) camReq.addHeader("Authorization", authHeader)
                        val camResult = withContext(Dispatchers.IO) {
                            client.newCall(camReq.build()).execute().use { camResponse ->
                                Log.i("DEV", "◀ CAM[JETSON] snapshot ← HTTP ${camResponse.code}")
                                if (camResponse.isSuccessful) {
                                    val bodyStr = camResponse.body?.string() ?: ""
                                    val bodyJson = JSONObject(bodyStr)
                                    val dataUrl = bodyJson.optString("data_url")
                                    if (dataUrl.startsWith("data:image/jpeg;base64,")) {
                                        val b64Data = dataUrl.substringAfter("base64,")
                                        val decoded = Base64.decode(b64Data, Base64.DEFAULT)
                                        decoded
                                    } else null
                                } else null
                            }
                        }
                        if (camResult != null && camResult.isNotEmpty()) {
                            cameraBitmap = BitmapFactory.decodeByteArray(camResult, 0, camResult.size)
                            isJetsonOnline = true
                            gotFrame = true
                            Log.i("DEV", "  ✓ CAM[JETSON] snapshot decoded: ${camResult.size} bytes")
                        }
                    } catch (e: Exception) {
                        Log.d("DEV", "  ✗ CAM[JETSON] snapshot endpoint: ${e.javaClass.simpleName}: ${e.message}")
                    }

                    // Fallback to bridge capture command
                    if (!gotFrame) {
                        Log.d("DEV", "▶ CAM[JETSON] → fallback CMD[capture] …")
                        dispatchCommand("capture", JSONObject().apply { put("max_px", 480) }) { res ->
                            if (res != null) {
                                val dataUrl = res.optJSONObject("result")?.optString("data_url") ?: ""
                                if (dataUrl.startsWith("data:image/jpeg;base64,")) {
                                    try {
                                        val b64Data = dataUrl.substringAfter("base64,")
                                        val decoded = Base64.decode(b64Data, Base64.DEFAULT)
                                        cameraBitmap = BitmapFactory.decodeByteArray(decoded, 0, decoded.size)
                                        isJetsonOnline = true
                                        Log.i("DEV", "  ✓ CAM[JETSON] bridge frame decoded: ${decoded.size} bytes")
                                    } catch (e: Exception) {
                                        Log.e("DEV", "  ✗ CAM[JETSON] base64 decode FAILED: ${e.message}")
                                    }
                                } else {
                                    Log.w("DEV", "  ✗ CAM[JETSON] no data_url in response")
                                }
                            } else {
                                Log.w("DEV", "  ✗ CAM[JETSON] command returned null")
                            }
                        }
                    }

                    // YOLO detection via /api/camera/detect endpoint
                    if (activeDetectionMode != "NONE" && gotFrame) {
                        try {
                            val detUrl = "http://$currentJetsonHost:$jetsonPort/api/camera/detect?confidence=0.3"
                            Log.d("DEV", "▶ CAM[JETSON] → YOLO detect …")
                            val detReq = Request.Builder().url(detUrl)
                            if (authHeader.isNotEmpty()) detReq.addHeader("Authorization", authHeader)
                            val detResult = withContext(Dispatchers.IO) {
                                client.newCall(detReq.build()).execute().use { r ->
                                    if (r.isSuccessful) r.body?.string() else null
                                }
                            }
                            if (detResult != null) {
                                val detJson = JSONObject(detResult)
                                val dets = detJson.optJSONArray("detections")
                                detectedBoxes.clear()
                                if (dets != null) {
                                    for (i in 0 until dets.length()) {
                                        val d = dets.optJSONObject(i) ?: continue
                                        val label = d.optString("label", "object")
                                        // Filter by detection mode
                                        val modeMatch = when (activeDetectionMode) {
                                            "PERSONS" -> label == "person"
                                            "FACES" -> label == "person" // YOLOv8 has face in person class
                                            else -> true
                                        }
                                        if (modeMatch) {
                                            detectedBoxes.add(DetectionBox(
                                                x1 = d.optDouble("x1", 0.0).toFloat(),
                                                y1 = d.optDouble("y1", 0.0).toFloat(),
                                                x2 = d.optDouble("x2", 0.0).toFloat(),
                                                y2 = d.optDouble("y2", 0.0).toFloat(),
                                                label = label,
                                                conf = d.optDouble("confidence", 1.0).toFloat()
                                            ))
                                        }
                                    }
                                }
                                Log.i("DEV", "  ✓ YOLO: ${detJson.optInt("count", 0)} objects detected")
                            }
                        } catch (e: Exception) {
                            Log.d("DEV", "  ✗ YOLO detect: ${e.javaClass.simpleName}: ${e.message}")
                        }
                    } else if (activeDetectionMode == "NONE") {
                        detectedBoxes.clear()
                    }
                }
            } catch (e: Exception) {
                if (activeCameraSource == "ARDUINO") isArduinoOnline = false
                Log.e("DEV", "✗ CAM ERROR: ${e.javaClass.simpleName}: ${e.message}")
            }
            delay(100) // 100ms = ~10 FPS target
        }
        Log.d("DEV", "━━━ CAMERA POLLER STOPPED ───")
    }

    // Motion detection — runs on each new camera frame
    LaunchedEffect(cameraBitmap, isMotionDetectionActive) {
        if (!isMotionDetectionActive) return@LaunchedEffect
        val current = cameraBitmap ?: return@LaunchedEffect
        try {
            val w = current.width
            val h = current.height
            if (w == 0 || h == 0) return@LaunchedEffect

            val currentPixels = IntArray(w * h)
            current.getPixels(currentPixels, 0, w, 0, 0, w, h)

            val prevHash = lastFrameHash
            var totalDiff = 0L
            val diffPixels = BooleanArray(w * h)

            for (i in currentPixels.indices) {
                val c = currentPixels[i]
                val cr = (c shr 16) and 0xFF
                val cg = (c shr 8) and 0xFF
                val cb = c and 0xFF
                val gray = (cr * 0.299 + cg * 0.587 + cb * 0.114).toInt()
                diffPixels[i] = true // placeholder — we compare via hash for speed
                totalDiff += gray.toLong()
            }

            val currentHash = totalDiff
            lastFrameHash = currentHash

            // Simple frame-hash motion gate: if hash changed significantly, scan for boxes
            if (prevHash != 0L && kotlin.math.abs(currentHash - prevHash) > w * h * motionSensitivity.toLong() / 10) {
                // Downsample scan: check 8x8 blocks for motion
                val blockSize = 8
                val blocksW = w / blockSize
                val blocksH = h / blockSize
                val blockMotion = BooleanArray(blocksW * blocksH)

                var motionCount = 0
                for (by in 0 until blocksH) {
                    for (bx in 0 until blocksW) {
                        var blockSum = 0L
                        val startX = bx * blockSize
                        val startY = by * blockSize
                        for (dy in 0 until blockSize) {
                            for (dx in 0 until blockSize) {
                                val px = currentPixels[(startY + dy) * w + (startX + dx)]
                                val gray = ((px shr 16 and 0xFF) * 0.299 + (px shr 8 and 0xFF) * 0.587 + (px and 0xFF) * 0.114).toInt()
                                blockSum += gray
                            }
                        }
                        val avg = blockSum / (blockSize * blockSize)
                        blockMotion[by * blocksW + bx] = avg > 30
                        if (avg > 30) motionCount++
                    }
                }

                motionPixelCount = motionCount

                // Find connected motion regions and draw bounding boxes
                motionBoxes.clear()
                val visited = BooleanArray(blocksW * blocksH)
                for (by in 0 until blocksH) {
                    for (bx in 0 until blocksW) {
                        val idx = by * blocksW + bx
                        if (blockMotion[idx] && !visited[idx]) {
                            // BFS flood fill to find connected component
                            var minX = bx; var maxX = bx; var minY = by; var maxY = by
                            val queue = ArrayDeque<Int>()
                            queue.add(idx)
                            visited[idx] = true
                            while (queue.isNotEmpty()) {
                                val ci = queue.removeFirst()
                                val cx = ci % blocksW
                                val cy = ci / blocksW
                                if (cx < minX) minX = cx
                                if (cx > maxX) maxX = cx
                                if (cy < minY) minY = cy
                                if (cy > maxY) maxY = cy
                                for ((dx, dy) in listOf(-1 to 0, 1 to 0, 0 to -1, 0 to 1)) {
                                    val nx = cx + dx
                                    val ny = cy + dy
                                    if (nx in 0 until blocksW && ny in 0 until blocksH) {
                                        val ni = ny * blocksW + nx
                                        if (blockMotion[ni] && !visited[ni]) {
                                            visited[ni] = true
                                            queue.add(ni)
                                        }
                                    }
                                }
                            }
                            val boxW = (maxX - minX + 1) * blockSize
                            val boxH = (maxY - minY + 1) * blockSize
                            if (boxW > 16 && boxH > 16) {
                                motionBoxes.add(DetectionBox(
                                    x1 = (minX * blockSize).toFloat(),
                                    y1 = (minY * blockSize).toFloat(),
                                    x2 = ((maxX + 1) * blockSize).toFloat(),
                                    y2 = ((maxY + 1) * blockSize).toFloat(),
                                    label = "MOTION",
                                    conf = (motionCount.toFloat() / (blocksW * blocksH)).coerceIn(0f, 1f)
                                ))
                            }
                        }
                    }
                }
                if (motionBoxes.isNotEmpty()) {
                    Log.i("DEV", "  🏃 MOTION: ${motionBoxes.size} regions, ${motionCount} blocks moving")
                }
            }
        } catch (e: Exception) {
            Log.e("DEV", "Motion detection error: ${e.message}")
        }
    }

    // LIDAR scan poller (every 500ms)
    LaunchedEffect(isLidarActive, currentJetsonHost) {
        Log.i("DEV", "━━━ LIDAR POLLER START ───")
        while (isLidarActive) {
            try {
                val lidarUrl = "http://$currentJetsonHost:$jetsonPort/api/lidar/scan"
                Log.d("DEV", "▶ LIDAR → $lidarUrl …")
                val lidarReq = Request.Builder().url(lidarUrl)
                if (authHeader.isNotEmpty()) lidarReq.addHeader("Authorization", authHeader)
                val result = withContext(Dispatchers.IO) {
                    client.newCall(lidarReq.build()).execute().use { r ->
                        if (r.isSuccessful) r.body?.string() else null
                    }
                }
                if (result != null) {
                    val json = JSONObject(result)
                    val pts = json.optJSONArray("points")
                    lidarPointCount = json.optInt("count", 0)
                    lidarMinDist = json.optInt("min_dist", 0)
                    lidarMaxDist = json.optInt("max_dist", 0)
                    lidarPoints.clear()
                    if (pts != null) {
                        for (i in 0 until pts.length()) {
                            val p = pts.optJSONObject(i) ?: continue
                            lidarPoints.add(LidarPoint(
                                angle = p.optDouble("angle", 0.0).toFloat(),
                                distance = p.optInt("distance", 0)
                            ))
                        }
                    }
                    Log.i("DEV", "◀ LIDAR: ${lidarPointCount} points, min=${lidarMinDist}mm max=${lidarMaxDist}mm")
                }
            } catch (e: Exception) {
                Log.w("DEV", "✗ LIDAR: ${e.javaClass.simpleName}: ${e.message}")
            }
            delay(500)
        }
    }

    // Active Aria2 downloads background polling loop
    LaunchedEffect(activeDownloads.size, currentJetsonHost) {
        while (activeDownloads.isNotEmpty()) {
            activeDownloads.forEachIndexed { index, download ->
                try {
                    val url = "http://$currentJetsonHost:$jetsonPort/api/cmd/voice.aria2_progress"
                    val bodyJson = JSONObject().apply {
                        put("params", JSONObject().apply { put("gid", download.gid) })
                    }
                    val requestBody = bodyJson.toString().toRequestBody("application/json".toMediaType())
                    val requestBuilder = Request.Builder().url(url).post(requestBody)
                    if (authHeader.isNotEmpty()) {
                        requestBuilder.addHeader("Authorization", authHeader)
                    }
                    val request = requestBuilder.build()

                    withContext(Dispatchers.IO) {
                        client.newCall(request).execute().use { response ->
                            if (response.isSuccessful) {
                                val resStr = response.body?.string() ?: ""
                                val resJson = JSONObject(resStr)
                                val result = resJson.optJSONObject("result")
                                if (result != null) {
                                    val progressPct = result.optDouble("progress_pct", 0.0).toFloat()
                                    val status = result.optString("status", "unknown")
                                    val ttsText = result.optString("tts_text", "")
                                    val speedBytes = result.optLong("download_speed", 0)
                                    val speedKb = speedBytes / 1024.0
                                    val speedFormatted = String.format("%.1f KB/s", speedKb)

                                    activeDownloads.set(index, download.copy(
                                        progress = progressPct,
                                        speed = speedFormatted,
                                        status = status,
                                        ttsText = ttsText
                                    ))
                                }
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.e("Aria2Poll", "Failed polling progress for ${download.gid}: ${e.message}")
                }
            }
            delay(2000)
        }
    }

    // Arduino heartbeat poller (every 4 seconds) — tries WiFi first, falls back to Tailscale
    LaunchedEffect(unoqWifiHost, unoqTailscaleHost, unoqPort) {
        Log.i("DEV", "━━━ ARDUINO HEARTBEAT START ─── WiFi=$unoqWifiHost:$unoqPort  TS=$unoqTailscaleHost:$unoqPort")
        while (true) {
            val hostsToTry = listOf(unoqWifiHost to "WiFi", unoqTailscaleHost to "Tailscale")
            var found = false
            for ((host, routeName) in hostsToTry) {
                try {
                    Log.d("DEV", "▶ ARDUINO[$routeName] → $host:$unoqPort …")
                    val snapUrl = "http://$host:$unoqPort/snapshot.jpg"
                    val snapReq = Request.Builder().url(snapUrl).build()
                    withContext(Dispatchers.IO) {
                        client.newCall(snapReq).execute().use { r ->
                            Log.i("DEV", "◀ ARDUINO[$routeName] ← HTTP ${r.code}")
                            if (r.isSuccessful || r.code in 200..499) {
                                isArduinoOnline = true
                                found = true
                                Log.i("DEV", "  ✓ ARDUINO online ($routeName)")
                            }
                        }
                    }
                    if (found) break
                } catch (e: Exception) {
                    Log.w("DEV", "  ✗ ARDUINO[$routeName] $host UNREACHABLE: ${e.javaClass.simpleName}: ${e.message}")
                }
            }
            if (!found) {
                isArduinoOnline = false
                Log.w("DEV", "✗ ARDUINO ALL ROUTES FAILED")
            }
            delay(4000)
        }
    }

    // Tailscale connectivity detector (every 6 seconds)
    LaunchedEffect(Unit) {
        Log.i("DEV", "━━━ TAILSCALE DETECTOR START ───")
        while (true) {
            try {
                Log.d("DEV", "▶ TAILSCALE probe 100.100.100.100 …")
                val request = Request.Builder().url("http://100.100.100.100").build()
                withContext(Dispatchers.IO) {
                    client.newCall(request).execute().use { r ->
                        isTailscaleConnected = true
                        Log.i("DEV", "◀ TAILSCALE probe ← HTTP ${r.code} ✓ CONNECTED")
                    }
                }
            } catch (e: Exception) {
                Log.d("DEV", "  ✗ TAILSCALE 100.100.100.100: ${e.javaClass.simpleName}: ${e.message}")
                try {
                    Log.d("DEV", "▶ TAILSCALE fallback probe $vpsTailscaleHost:$vpsPort …")
                    val fallback = Request.Builder()
                        .url("http://$vpsTailscaleHost:$vpsPort/api/trending")
                        .build()
                    withContext(Dispatchers.IO) {
                        client.newCall(fallback).execute().use { r ->
                            isTailscaleConnected = r.isSuccessful || r.code in 200..499
                            Log.i("DEV", "◀ TAILSCALE fallback ← HTTP ${r.code} ${if (isTailscaleConnected) "✓" else "✗"}")
                        }
                    }
                } catch (e2: Exception) {
                    isTailscaleConnected = false
                    Log.w("DEV", "✗ TAILSCALE ALL PROBES FAILED: ${e2.javaClass.simpleName}: ${e2.message}")
                }
            }
            delay(6000)
        }
    }

    // VPS status poller (every 5 seconds)
    LaunchedEffect(vpsTailscaleHost, vpsPort) {
        Log.i("DEV", "━━━ VPS STATUS START ─── $vpsTailscaleHost:$vpsPort")
        while (true) {
            try {
                Log.d("DEV", "▶ VPS → $vpsTailscaleHost:$vpsPort/api/trending …")
                val url = "http://$vpsTailscaleHost:$vpsPort/api/trending"
                val request = Request.Builder().url(url).build()
                withContext(Dispatchers.IO) {
                    client.newCall(request).execute().use { r ->
                        isVpsOnline = r.isSuccessful || r.code in 200..499
                        Log.i("DEV", "◀ VPS ← HTTP ${r.code} ${if (isVpsOnline) "✓ ONLINE" else "✗ OFFLINE"}")
                    }
                }
            } catch (e: Exception) {
                isVpsOnline = false
                Log.w("DEV", "✗ VPS UNREACHABLE: ${e.javaClass.simpleName}: ${e.message}")
            }
            delay(5000)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .systemBarsPadding()
            .padding(horizontal = 16.dp)
            .padding(top = 16.dp)
    ) {
        // Status Bar Header (Glowing Anti-Gravity Gradient)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 16.dp)
                .background(CyberTheme.HEADER_GRADIENT, RoundedCornerShape(12.dp))
                .padding(horizontal = 14.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "TANK OS MOBILE",
                    color = CyberTheme.BG,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.ExtraBold,
                    fontFamily = FontFamily.Monospace
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = "SYS: $connectionStatus | ".uppercase(),
                        color = if (connectionStatus == "Online" || connectionStatus == "Needs Auth") Color.Black else CyberTheme.NEON_PINK,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                    Text(
                        text = if (isWifiRouteActive) "⚡ WIFI" else if (isTailscaleConnected) "🔒 TAILSCALE" else "⚠️ NO NETWORK",
                        color = if (isWifiRouteActive) Color(0xFF1B5E20) else if (isTailscaleConnected) Color(0xFF311B92) else CyberTheme.NEON_PINK,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.ExtraBold,
                        fontFamily = FontFamily.Monospace
                    )
                }
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = if (isJetsonOnline) "🟢 JET" else "🔴 JET",
                        color = Color.White,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                    Text(
                        text = if (isArduinoOnline) "🟢 ARD" else "🔴 ARD",
                        color = Color.White,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                    Text(
                        text = if (isVpsOnline) "🟢 VPS" else "🔴 VPS",
                        color = Color.White,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                }
            }
            Text(
                text = currentEmotion.uppercase(),
                color = CyberTheme.TEXT,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .background(Color(0x33000000), RoundedCornerShape(6.dp))
                    .padding(horizontal = 10.dp, vertical = 6.dp)
            )
        }

        // ═══ BOTTOM NAVIGATION BAR (Material 3) ═══
        // This sits ABOVE the Android system nav bar, never overlaying system buttons
        NavigationBar(
            containerColor = Color(0xFF0D1117),
            contentColor = CyberTheme.ACCENT_CYAN,
            tonalElevation = 0.dp,
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .border(1.dp, CyberTheme.DIM.copy(alpha = 0.15f), RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp))
        ) {
            tabLabels.forEachIndexed { index, label ->
                NavigationBarItem(
                    selected = selectedTab == index,
                    onClick = {
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        selectedTab = index
                    },
                    icon = {
                        Text(
                            text = tabIcons[index],
                            fontSize = 18.sp
                        )
                    },
                    label = {
                        Text(
                            text = label,
                            fontSize = 9.sp,
                            fontWeight = if (selectedTab == index) FontWeight.Bold else FontWeight.Normal,
                            fontFamily = FontFamily.Monospace
                        )
                    },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = CyberTheme.ACCENT_CYAN,
                        selectedTextColor = CyberTheme.ACCENT_CYAN,
                        unselectedIconColor = CyberTheme.DIM,
                        unselectedTextColor = CyberTheme.DIM,
                        indicatorColor = CyberTheme.ACCENT_CYAN.copy(alpha = 0.15f)
                    )
                )
            }
        }

        // ═══ BODY CONTENT (Tab selection) with Crossfade animation ═══
        Crossfade(
            targetState = selectedTab,
            animationSpec = tween(durationMillis = 280),
            label = "tab_content"
        ) { tab ->
        when (tab) {
            0 -> {
                // Tab 1: Controls & Rich Agent Chat GUI
                LazyColumn(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Telemetry Panel
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.ACCENT_PURPLE.copy(alpha = 0.2f))
                        ) {
                            Row(modifier = Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceAround) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text("BATTERY", color = CyberTheme.DIM, fontSize = 10.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                    Text(batteryText, color = CyberTheme.NEON_GREEN, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
                                }
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text("CPU TEMP", color = CyberTheme.DIM, fontSize = 10.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                    Text(cpuTempText, color = CyberTheme.TEXT, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
                                }
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text("SAFETY STAT", color = CyberTheme.DIM, fontSize = 10.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                    Text(if (estopStatus) "LATCHED" else "DISARMED", color = if (estopStatus) CyberTheme.NEON_PINK else CyberTheme.NEON_GREEN, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
                                }
                            }
                        }
                    }

                    // Drive Controls
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.ACCENT_CYAN.copy(alpha = 0.25f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("🛞 CHASSIS MOTION COCKPIT", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace, modifier = Modifier.align(Alignment.Start))
                                Spacer(modifier = Modifier.height(10.dp))
                                // Sliders
                                Column(modifier = Modifier.fillMaxWidth()) {
                                    Text("Linear Speed: ${String.format("%.2f", driveSpeedLinear)} m/s", color = CyberTheme.TEXT, fontSize = 11.sp)
                                    Slider(value = driveSpeedLinear, onValueChange = { driveSpeedLinear = it }, valueRange = 0.0f..0.5f, colors = SliderDefaults.colors(thumbColor = CyberTheme.ACCENT_CYAN, activeTrackColor = CyberTheme.ACCENT_CYAN))
                                    Text("Angular Speed: ${String.format("%.2f", driveSpeedAngular)} rad/s", color = CyberTheme.TEXT, fontSize = 11.sp)
                                    Slider(value = driveSpeedAngular, onValueChange = { driveSpeedAngular = it }, valueRange = 0.0f..1.5f, colors = SliderDefaults.colors(thumbColor = CyberTheme.ACCENT_CYAN, activeTrackColor = CyberTheme.ACCENT_CYAN))
                                    Text("Duration: ${String.format("%.2f", driveDuration)} s", color = CyberTheme.TEXT, fontSize = 11.sp)
                                    Slider(value = driveDuration, onValueChange = { driveDuration = it }, valueRange = 0.1f..5.0f, colors = SliderDefaults.colors(thumbColor = CyberTheme.ACCENT_CYAN, activeTrackColor = CyberTheme.ACCENT_CYAN))
                                }
                                Spacer(modifier = Modifier.height(12.dp))
                                // Grid
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Button(onClick = { dispatchCommand("move", JSONObject().apply { put("vx", driveSpeedLinear.toDouble()); put("wz", 0.0); put("duration_s", driveDuration.toDouble()) }) {} }, colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN), modifier = Modifier.size(90.dp, 48.dp), shape = RoundedCornerShape(8.dp)) { Text("UP", color = CyberTheme.BG, fontWeight = FontWeight.ExtraBold) }
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        Button(onClick = { dispatchCommand("move", JSONObject().apply { put("vx", 0.0); put("wz", driveSpeedAngular.toDouble()); put("duration_s", driveDuration.toDouble()) }) {} }, colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN), modifier = Modifier.size(90.dp, 48.dp), shape = RoundedCornerShape(8.dp)) { Text("LEFT", color = CyberTheme.BG, fontWeight = FontWeight.ExtraBold) }
                                        Button(onClick = { dispatchCommand("move", JSONObject().apply { put("vx", 0.0); put("wz", 0.0); put("duration_s", 0.1) }) {} }, colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.NEON_PINK), modifier = Modifier.size(100.dp, 48.dp), shape = RoundedCornerShape(8.dp)) { Text("STOP", color = CyberTheme.TEXT, fontWeight = FontWeight.ExtraBold) }
                                        Button(onClick = { dispatchCommand("move", JSONObject().apply { put("vx", 0.0); put("wz", -driveSpeedAngular.toDouble()); put("duration_s", driveDuration.toDouble()) }) {} }, colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN), modifier = Modifier.size(90.dp, 48.dp), shape = RoundedCornerShape(8.dp)) { Text("RIGHT", color = CyberTheme.BG, fontWeight = FontWeight.ExtraBold) }
                                    }
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Button(onClick = { dispatchCommand("move", JSONObject().apply { put("vx", -driveSpeedLinear.toDouble()); put("wz", 0.0); put("duration_s", driveDuration.toDouble()) }) {} }, colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN), modifier = Modifier.size(90.dp, 48.dp), shape = RoundedCornerShape(8.dp)) { Text("DOWN", color = CyberTheme.BG, fontWeight = FontWeight.ExtraBold) }
                                }
                            }
                        }
                    }

                    // E-STOP & Dock actions
                    item {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(onClick = { dispatchCommand("estop", JSONObject().apply { put("state", !estopStatus) }) { res -> if (res != null) { estopStatus = res.optJSONObject("result")?.optBoolean("latched", false) ?: false } } }, colors = ButtonDefaults.buttonColors(containerColor = if (estopStatus) CyberTheme.NEON_GREEN else CyberTheme.NEON_PINK), modifier = Modifier.weight(1f), shape = RoundedCornerShape(10.dp)) { Text(if (estopStatus) "RELEASE ESTOP" else "⚠️ E-STOP LATCH", color = CyberTheme.TEXT, fontWeight = FontWeight.ExtraBold, fontSize = 11.sp) }
                            Button(onClick = { val nextDock = !isDockArmed; dispatchCommand("dock", JSONObject().apply { put("enable", nextDock) }) { res -> if (res != null) { isDockArmed = res.optJSONObject("result")?.optBoolean("armed", false) ?: false } } }, colors = ButtonDefaults.buttonColors(containerColor = if (isDockArmed) CyberTheme.NEON_GREEN else CyberTheme.ACCENT_PURPLE), modifier = Modifier.weight(1f), shape = RoundedCornerShape(10.dp)) { Text(if (isDockArmed) "DOCK ARMED" else "🔋 DOCK TAG SYSTEM", color = CyberTheme.TEXT, fontWeight = FontWeight.ExtraBold, fontSize = 11.sp) }
                        }
                    }

                    // Patrol Options
                    item {
                        Card(modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD), shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, CyberTheme.DIM.copy(alpha = 0.2f))) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("🛡️ AUTONOMOUS PATROL CONFIG", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(8.dp))
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    val modes = listOf("waypoint", "random", "pause", "stop")
                                    modes.forEach { mode ->
                                        Button(
                                            onClick = { dispatchCommand("patrol", JSONObject().apply { put("mode", mode) }) { res -> if (res != null) { currentPatrolMode = res.optJSONObject("result")?.optString("mode", "stop") ?: "stop" } } },
                                            colors = ButtonDefaults.buttonColors(containerColor = if (currentPatrolMode == mode) CyberTheme.NEON_GREEN else CyberTheme.DIM.copy(alpha = 0.4f)),
                                            modifier = Modifier.weight(1f),
                                            contentPadding = PaddingValues(horizontal = 4.dp, vertical = 10.dp),
                                            shape = RoundedCornerShape(8.dp)
                                        ) {
                                            Text(mode.uppercase(), color = if (currentPatrolMode == mode) CyberTheme.BG else CyberTheme.TEXT, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Rich Agent Chat GUI Console
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.DIM.copy(alpha = 0.2f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    val brainPulse by infiniteTransition.animateFloat(
                                        initialValue = 0.4f,
                                        targetValue = 1f,
                                        animationSpec = infiniteRepeatable(
                                            animation = tween(1200, easing = LinearEasing),
                                            repeatMode = RepeatMode.Reverse
                                        ),
                                        label = "brain"
                                    )
                                    Box(modifier = Modifier.size(10.dp).clip(RoundedCornerShape(5.dp)).background(CyberTheme.NEON_BLUE.copy(alpha = brainPulse)))
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("🤖 TANKOS COGNITIVE AGENT PLAYGROUND", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                }
                                Spacer(modifier = Modifier.height(10.dp))
                                
                                // Scrollable Messages Board
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(280.dp)
                                        .background(Color(0xFF070810), RoundedCornerShape(10.dp))
                                        .border(1.dp, CyberTheme.DIM.copy(alpha = 0.3f), RoundedCornerShape(10.dp))
                                        .padding(10.dp)
                                ) {
                                    LazyColumn(
                                        modifier = Modifier.fillMaxSize(),
                                        verticalArrangement = Arrangement.spacedBy(10.dp)
                                    ) {
                                        if (chatBubbles.isEmpty()) {
                                            item {
                                                Text("Agent idle. Send a query to test active planners or run terminal tools.", color = CyberTheme.DIM, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                                            }
                                        }
                                        items(chatBubbles) { bubble ->
                                            Column(
                                                modifier = Modifier.fillMaxWidth(),
                                                horizontalAlignment = if (bubble.type == MsgType.USER) Alignment.End else Alignment.Start
                                            ) {
                                                Text(
                                                    text = bubble.sender.uppercase(),
                                                    color = CyberTheme.DIM,
                                                    fontSize = 9.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    fontFamily = FontFamily.Monospace,
                                                    modifier = Modifier.padding(bottom = 2.dp)
                                                )
                                                
                                                when (bubble.type) {
                                                    MsgType.USER -> {
                                                        Box(
                                                            modifier = Modifier
                                                                .background(CyberTheme.ACCENT_PURPLE.copy(alpha = 0.3f), RoundedCornerShape(12.dp, 12.dp, 0.dp, 12.dp))
                                                                .border(1.dp, CyberTheme.ACCENT_PURPLE.copy(alpha = 0.6f), RoundedCornerShape(12.dp, 12.dp, 0.dp, 12.dp))
                                                                .padding(10.dp)
                                                        ) {
                                                            Text(bubble.text, color = CyberTheme.TEXT, fontSize = 12.sp)
                                                        }
                                                    }
                                                    MsgType.THINKING -> {
                                                        Row(
                                                            modifier = Modifier
                                                                .background(Color(0x33FFB300), RoundedCornerShape(12.dp, 12.dp, 12.dp, 0.dp))
                                                                .border(1.dp, Color(0xFFFFB300).copy(alpha = 0.5f), RoundedCornerShape(12.dp, 12.dp, 12.dp, 0.dp))
                                                                .padding(10.dp),
                                                            verticalAlignment = Alignment.CenterVertically,
                                                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                                                        ) {
                                                            CyberSpinner(size = 14.dp, color = Color(0xFFFFB300))
                                                            Text(bubble.text, color = Color(0xFFFFB300), fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.SemiBold)
                                                        }
                                                    }
                                                    MsgType.TOOL_EXEC -> {
                                                        Box(
                                                            modifier = Modifier
                                                                .fillMaxWidth()
                                                                .background(Color(0xFF020E04), RoundedCornerShape(8.dp))
                                                                .border(1.dp, Color(0xFF00E676).copy(alpha = 0.4f), RoundedCornerShape(8.dp))
                                                                .padding(8.dp)
                                                        ) {
                                                            Text(
                                                                text = bubble.text,
                                                                color = Color(0xFF00FF00),
                                                                fontSize = 10.sp,
                                                                fontFamily = FontFamily.Monospace
                                                            )
                                                        }
                                                    }
                                                    MsgType.TANK_REPLY -> {
                                                        Box(
                                                            modifier = Modifier
                                                                .background(CyberTheme.BG_CARD, RoundedCornerShape(12.dp, 12.dp, 12.dp, 0.dp))
                                                                .border(1.dp, CyberTheme.ACCENT_CYAN.copy(alpha = 0.4f), RoundedCornerShape(12.dp, 12.dp, 12.dp, 0.dp))
                                                                .padding(10.dp)
                                                        ) {
                                                            Text(bubble.text, color = CyberTheme.TEXT, fontSize = 12.sp)
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                                Spacer(modifier = Modifier.height(10.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    OutlinedTextField(
                                        value = chatInputText,
                                        onValueChange = { chatInputText = it },
                                        placeholder = { Text("Enter prompt for robot agents...", color = CyberTheme.DIM) },
                                        textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                        modifier = Modifier.weight(1f),
                                        colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                    )
                                    Button(
                                        onClick = {
                                            if (chatInputText.isNotEmpty()) {
                                                val userMsg = chatInputText
                                                chatBubbles.add(ChatBubble("User", userMsg, MsgType.USER))
                                                chatInputText = ""
                                                isChatting = true
                                                
                                                // Add animated placeholder thinking bubble
                                                val thinkingBubble = ChatBubble("TankOS", "⚡ Analyzing prompt & scheduling rotation engine...", MsgType.THINKING)
                                                chatBubbles.add(thinkingBubble)
                                                
                                                dispatchCommand("chat", JSONObject().apply { put("text", userMsg); put("use_external_llm", false) }) { res ->
                                                    isChatting = false
                                                    // Remove thinking bubble
                                                    chatBubbles.remove(thinkingBubble)
                                                    
                                                    if (res != null) {
                                                        val result = res.optJSONObject("result")
                                                        val reply = result?.optString("reply") ?: "Error parsing response"
                                                        
                                                        // Parse reply to extract tool invocations if any (e.g. lines starting with custom markers)
                                                        if (reply.contains("🔧 SHELL") || reply.contains("⚙️ TOOL")) {
                                                            // Split reply by tool calls and text
                                                            val lines = reply.split("\n")
                                                            val toolLines = StringBuilder()
                                                            val textLines = StringBuilder()
                                                            lines.forEach { line ->
                                                                if (line.trim().startsWith("🔧") || line.trim().startsWith("⚙️") || line.trim().startsWith("├─")) {
                                                                    toolLines.append(line).append("\n")
                                                                } else {
                                                                    textLines.append(line).append("\n")
                                                                }
                                                            }
                                                            if (toolLines.isNotEmpty()) {
                                                                chatBubbles.add(ChatBubble("Sys Exec", toolLines.toString().trim(), MsgType.TOOL_EXEC))
                                                            }
                                                            if (textLines.toString().trim().isNotEmpty()) {
                                                                chatBubbles.add(ChatBubble("TankOS", textLines.toString().trim(), MsgType.TANK_REPLY))
                                                            }
                                                        } else {
                                                            chatBubbles.add(ChatBubble("TankOS", reply, MsgType.TANK_REPLY))
                                                        }
                                                    } else {
                                                        chatBubbles.add(ChatBubble("TankOS", "Error connecting to command bridge API.", MsgType.TANK_REPLY))
                                                    }
                                                }
                                            }
                                        },
                                        enabled = !isChatting,
                                        colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.NEON_GREEN),
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        if (isChatting) {
                                            CyberSpinner(size = 18.dp, color = CyberTheme.BG)
                                        } else {
                                            Text("SEND", color = CyberTheme.BG, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            1 -> {
                // Tab 2: Vision, Dual USB Cameras, & OpenCV Overlays
                LazyColumn(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Vision Mode Settings Card
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.ACCENT_CYAN.copy(alpha = 0.25f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("🎥 SELECT ACTIVE USB CAMERA", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(8.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Button(
                                        onClick = { activeCameraSource = "JETSON"; detectedBoxes.clear() },
                                        colors = ButtonDefaults.buttonColors(containerColor = if (activeCameraSource == "JETSON") CyberTheme.ACCENT_CYAN else CyberTheme.DIM.copy(alpha = 0.3f)),
                                        modifier = Modifier.weight(1f),
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        Text("🎥 JETSON CAM", color = if (activeCameraSource == "JETSON") CyberTheme.BG else CyberTheme.TEXT, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                                    }
                                    Button(
                                        onClick = { activeCameraSource = "ARDUINO"; detectedBoxes.clear() },
                                        colors = ButtonDefaults.buttonColors(containerColor = if (activeCameraSource == "ARDUINO") CyberTheme.ACCENT_CYAN else CyberTheme.DIM.copy(alpha = 0.3f)),
                                        modifier = Modifier.weight(1f),
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        Text("🔌 ARDUINO CAM", color = if (activeCameraSource == "ARDUINO") CyberTheme.BG else CyberTheme.TEXT, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                                    }
                                }
                                
                                Spacer(modifier = Modifier.height(12.dp))
                                Text("🤖 OPENCV/YOLO DETECTIONS MODE", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(8.dp))
                                
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    val modes = listOf("NONE", "PERSONS", "FACES")
                                    modes.forEach { mode ->
                                        Button(
                                            onClick = { activeDetectionMode = mode; detectedBoxes.clear() },
                                            colors = ButtonDefaults.buttonColors(containerColor = if (activeDetectionMode == mode) CyberTheme.NEON_GREEN else CyberTheme.DIM.copy(alpha = 0.3f)),
                                            modifier = Modifier.weight(1f),
                                            shape = RoundedCornerShape(8.dp),
                                            contentPadding = PaddingValues(vertical = 8.dp)
                                        ) {
                                            Text(mode, color = if (activeDetectionMode == mode) CyberTheme.BG else CyberTheme.TEXT, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }
                                Spacer(modifier = Modifier.height(10.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("Live Video Scan: ", color = CyberTheme.TEXT, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                                    Switch(
                                        checked = isLiveVisionPolling,
                                        onCheckedChange = { isLiveVisionPolling = it; Log.i("DEV", "━━━ CAMERA TOGGLE: ${if (it) "ON (source=$activeCameraSource)" else "OFF"} ───") },
                                        colors = SwitchDefaults.colors(checkedThumbColor = CyberTheme.NEON_GREEN, checkedTrackColor = CyberTheme.NEON_GREEN.copy(alpha = 0.5f))
                                    )
                                }
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("Motion Detection: ", color = CyberTheme.TEXT, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                                    Switch(
                                        checked = isMotionDetectionActive,
                                        onCheckedChange = { isMotionDetectionActive = it; motionBoxes.clear(); motionPixelCount = 0; Log.i("DEV", "━━━ MOTION DETECTION: ${if (it) "ON" else "OFF"} ───") },
                                        colors = SwitchDefaults.colors(checkedThumbColor = Color(0xFFFFEB3B), checkedTrackColor = Color(0xFFFFEB3B).copy(alpha = 0.5f))
                                    )
                                }
                                if (isMotionDetectionActive && motionBoxes.isNotEmpty()) {
                                    Text("  🏃 ${motionBoxes.size} motion region(s) detected", color = Color(0xFFFFEB3B), fontSize = 10.sp, fontFamily = FontFamily.Monospace)
                                }
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("LIDAR Scan: ", color = CyberTheme.TEXT, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                                    Switch(
                                        checked = isLidarActive,
                                        onCheckedChange = { isLidarActive = it; if (!it) lidarPoints.clear(); Log.i("DEV", "━━━ LIDAR: ${if (it) "ON" else "OFF"} ───") },
                                        colors = SwitchDefaults.colors(checkedThumbColor = Color(0xFF00FF00), checkedTrackColor = Color(0xFF00FF00).copy(alpha = 0.5f))
                                    )
                                }
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("Visual Map Overlay: ", color = CyberTheme.TEXT, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                                    Switch(
                                        checked = showVisualMap,
                                        onCheckedChange = { showVisualMap = it },
                                        colors = SwitchDefaults.colors(checkedThumbColor = Color(0xFF00FFFF), checkedTrackColor = Color(0xFF00FFFF).copy(alpha = 0.5f))
                                    )
                                }
                                if (isLidarActive && lidarPoints.isNotEmpty()) {
                                    Text("  📡 ${lidarPointCount} points | min=${lidarMinDist/1000}m max=${lidarMaxDist/1000}m", color = Color(0xFF00FF00), fontSize = 10.sp, fontFamily = FontFamily.Monospace)
                                }
                            }
                        }
                    }

                    // Arduino OLED Screen Controller
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.ACCENT_PURPLE.copy(alpha = 0.25f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("📺 ARDUINO OLED SCREEN EXPRESSIONS", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(8.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    val emotions = listOf(
                                        "happy" to "😀 HAPPY",
                                        "sad" to "😢 SAD",
                                        "alert" to "⚠️ ALERT",
                                        "curious" to "🤨 CURIOUS",
                                        "neutral" to "😐 NEUT"
                                    )
                                    emotions.forEach { (mood, label) ->
                                        Button(
                                            onClick = {
                                                dispatchCommand("chat", JSONObject().apply {
                                                    put("text", "system: update display node emotion to $mood")
                                                    put("use_external_llm", false)
                                                }) { res ->
                                                    if (res != null) {
                                                        currentEmotion = mood
                                                    }
                                                }
                                            },
                                            colors = ButtonDefaults.buttonColors(containerColor = if (currentEmotion == mood) CyberTheme.NEON_PURPLE else CyberTheme.DIM.copy(alpha = 0.3f)),
                                            modifier = Modifier.weight(1f),
                                            shape = RoundedCornerShape(6.dp),
                                            contentPadding = PaddingValues(horizontal = 4.dp, vertical = 6.dp)
                                        ) {
                                            Text(label, color = if (currentEmotion == mood) CyberTheme.BG else CyberTheme.TEXT, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Render custom canvas with OpenCV bounding boxes
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth().height(360.dp),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.DIM.copy(alpha = 0.3f))
                        ) {
                            Box(
                                modifier = Modifier.fillMaxSize().background(Color.Black),
                                contentAlignment = Alignment.Center
                            ) {
                                val bitmap = cameraBitmap
                                if (bitmap != null) {
                                    Canvas(modifier = Modifier.fillMaxSize()) {
                                        val canvasW = size.width
                                        val canvasH = size.height
                                        val bitW = bitmap.width.toFloat()
                                        val bitH = bitmap.height.toFloat()
                                        frameW = bitW
                                        frameH = bitH

                                        val scaleX = canvasW / bitW
                                        val scaleY = canvasH / bitH

                                        drawImage(
                                            image = bitmap.asImageBitmap(), 
                                            dstSize = androidx.compose.ui.unit.IntSize(canvasW.toInt(), canvasH.toInt())
                                        )                                        // YOLO detection boxes (green/pink)
                                        detectedBoxes.forEach { box ->
                                            val bx1 = box.x1 * scaleX
                                            val by1 = box.y1 * scaleY
                                            val bx2 = box.x2 * scaleX
                                            val by2 = box.y2 * scaleY

                                            drawRect(
                                                color = if (activeDetectionMode == "PERSONS") CyberTheme.NEON_GREEN else CyberTheme.NEON_PINK,
                                                topLeft = Offset(bx1, by1),
                                                size = Size(bx2 - bx1, by2 - by1),
                                                style = Stroke(width = 3.dp.toPx())
                                            )

                                            drawContext.canvas.nativeCanvas.drawRect(
                                                bx1, by1 - 32f, bx1 + 180f, by1,
                                                Paint().apply { color = android.graphics.Color.DKGRAY; style = Paint.Style.FILL }
                                            )

                                            val textPaint = Paint().apply {
                                                color = if (activeDetectionMode == "PERSONS") android.graphics.Color.GREEN else android.graphics.Color.RED
                                                textSize = 22f
                                                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                            }
                                            drawContext.canvas.nativeCanvas.drawText(
                                                "${box.label} (${(box.conf * 100).toInt()}%)",
                                                bx1 + 8f, by1 - 8f, textPaint
                                            )
                                        }

                                        // Motion detection boxes (yellow dashed)
                                        if (isMotionDetectionActive) {
                                            motionBoxes.forEach { box ->
                                                val bx1 = box.x1 * scaleX
                                                val by1 = box.y1 * scaleY
                                                val bx2 = box.x2 * scaleX
                                                val by2 = box.y2 * scaleY

                                                drawRect(
                                                    color = Color(0xFFFFEB3B),
                                                    topLeft = Offset(bx1, by1),
                                                    size = Size(bx2 - bx1, by2 - by1),
                                                    style = Stroke(
                                                        width = 2.dp.toPx(),
                                                        pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(
                                                            floatArrayOf(10f, 6f), 0f
                                                        )
                                                    )
                                                )

                                                drawContext.canvas.nativeCanvas.drawRect(
                                                    bx1, by1 - 32f, bx1 + 200f, by1,
                                                    Paint().apply { color = android.graphics.Color.argb(180, 30, 30, 0); style = Paint.Style.FILL }
                                                )

                                                val motionPaint = Paint().apply {
                                                    color = android.graphics.Color.YELLOW
                                                    textSize = 20f
                                                    typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                                }
                                                drawContext.canvas.nativeCanvas.drawText(
                                                    "MOTION (${(box.conf * 100).toInt()}%)",
                                                    bx1 + 6f, by1 - 8f, motionPaint
                                                )
                                            }

                                            // Motion status HUD overlay
                                            if (motionPixelCount > 0) {
                                                drawContext.canvas.nativeCanvas.drawText(
                                                    "MOTION: ${motionBoxes.size} regions",
                                                    8f, canvasH - 8f,
                                                    Paint().apply {
                                                        color = android.graphics.Color.YELLOW
                                                        textSize = 18f
                                                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                                        setShadowLayer(4f, 1f, 1f, android.graphics.Color.BLACK)
                                                    }
                                                )
                                            }

                                            // ═══ VISUAL MAP + LIDAR OVERLAY ═══
                                            if (showVisualMap && lidarPoints.isNotEmpty()) {
                                                val mapCx = canvasW - 80f
                                                val mapCy = canvasH - 80f
                                                val mapR = 70f
                                                val maxDisplayMm = 5000f // 5m max range for display

                                                // Background circle
                                                drawContext.canvas.nativeCanvas.drawCircle(
                                                    mapCx, mapCy, mapR,
                                                    Paint().apply {
                                                        color = android.graphics.Color.argb(120, 0, 0, 0)
                                                        style = Paint.Style.FILL
                                                    }
                                                )

                                                // Distance rings (1m, 2m, 3m, 4m)
                                                for (m in 1..4) {
                                                    val r = (m * 1000f / maxDisplayMm) * mapR
                                                    drawContext.canvas.nativeCanvas.drawCircle(
                                                        mapCx, mapCy, r,
                                                        Paint().apply {
                                                            color = android.graphics.Color.argb(60, 0, 255, 0)
                                                            style = Paint.Style.STROKE
                                                            strokeWidth = 1f
                                                        }
                                                    )
                                                    drawContext.canvas.nativeCanvas.drawText(
                                                        "${m}m",
                                                        mapCx + 2f, mapCy - r + 12f,
                                                        Paint().apply {
                                                            color = android.graphics.Color.argb(100, 0, 255, 0)
                                                            textSize = 9f
                                                        }
                                                    )
                                                }

                                                // Cross-hair lines
                                                drawContext.canvas.nativeCanvas.drawLine(
                                                    mapCx - mapR, mapCy, mapCx + mapR, mapCy,
                                                    Paint().apply { color = android.graphics.Color.argb(40, 0, 255, 0); strokeWidth = 1f }
                                                )
                                                drawContext.canvas.nativeCanvas.drawLine(
                                                    mapCx, mapCy - mapR, mapCx, mapCy + mapR,
                                                    Paint().apply { color = android.graphics.Color.argb(40, 0, 255, 0); strokeWidth = 1f }
                                                )

                                                // LIDAR points as green dots
                                                val navPaint = Paint().apply {
                                                    color = android.graphics.Color.GREEN
                                                    style = Paint.Style.FILL
                                                }
                                                lidarPoints.forEach { pt ->
                                                    if (pt.distance in 1..maxDisplayMm.toInt()) {
                                                        val r = (pt.distance.toFloat() / maxDisplayMm) * mapR
                                                        val rad = Math.toRadians(pt.angle.toDouble())
                                                        val px = mapCx + (r * Math.sin(rad)).toFloat()
                                                        val py = mapCy - (r * Math.cos(rad)).toFloat()
                                                        drawContext.canvas.nativeCanvas.drawCircle(
                                                            px, py, 2.5f, navPaint
                                                        )
                                                    }
                                                }

                                                // YOLO objects with distance labels on map
                                                detectedBoxes.forEach { box ->
                                                    val boxCx = (box.x1 + box.x2) / 2f
                                                    val boxCy = (box.y1 + box.y2) / 2f
                                                    // Map camera x to angle: left=270, center=0/360, right=90
                                                    val normX = boxCx / bitW
                                                    val objAngle = (normX * 360f - 180f + 360f) % 360f
                                                    // Find closest LIDAR point to this angle
                                                    var closestDist = 0
                                                    var minAngleDiff = 999f
                                                    lidarPoints.forEach { pt ->
                                                        val diff = kotlin.math.abs(pt.angle - objAngle)
                                                        val minDiff = minOf(diff, 360f - diff)
                                                        if (minDiff < minAngleDiff && pt.distance in 100..5000) {
                                                            minAngleDiff = minDiff
                                                            closestDist = pt.distance
                                                        }
                                                    }
                                                    val distText = if (closestDist > 0) "${closestDist / 1000.0f}m" else "?"
                                                    // Draw on map
                                                    if (closestDist > 0 && closestDist <= maxDisplayMm.toInt()) {
                                                        val r = (closestDist.toFloat() / maxDisplayMm) * mapR
                                                        val rad = Math.toRadians(objAngle.toDouble())
                                                        val px = mapCx + (r * Math.sin(rad)).toFloat()
                                                        val py = mapCy - (r * Math.cos(rad)).toFloat()
                                                        drawContext.canvas.nativeCanvas.drawCircle(
                                                            px, py, 5f,
                                                            Paint().apply { color = android.graphics.Color.RED; style = Paint.Style.FILL }
                                                        )
                                                        drawContext.canvas.nativeCanvas.drawText(
                                                            "${box.label} $distText",
                                                            px + 7f, py - 4f,
                                                            Paint().apply {
                                                                color = android.graphics.Color.RED
                                                                textSize = 10f
                                                                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                                                setShadowLayer(3f, 1f, 1f, android.graphics.Color.BLACK)
                                                            }
                                                        )
                                                    }
                                                    // Draw distance on camera overlay
                                                    drawContext.canvas.nativeCanvas.drawText(
                                                        distText,
                                                        box.x2 * scaleX + 4f, (box.y1 + box.y2) / 2f * scaleY,
                                                        Paint().apply {
                                                            color = android.graphics.Color.CYAN
                                                            textSize = 20f
                                                            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                                            setShadowLayer(3f, 1f, 1f, android.graphics.Color.BLACK)
                                                        }
                                                    )
                                                }

                                                // Map label
                                                drawContext.canvas.nativeCanvas.drawText(
                                                    "LIDAR ${lidarPointCount}pts ${lidarMinDist/1000}m-${lidarMaxDist/1000}m",
                                                    mapCx - mapR, mapCy + mapR + 14f,
                                                    Paint().apply {
                                                        color = android.graphics.Color.GREEN
                                                        textSize = 10f
                                                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                                    }
                                                )
                                            }

                                            // Top-left status HUD
                                            drawContext.canvas.nativeCanvas.drawText(
                                                "FPS ~${if (cameraBitmap != null) "10" else "0"} | YOLO:${detectedBoxes.size} | MOT:${motionBoxes.size} | LIDAR:${lidarPointCount}",
                                                8f, 20f,
                                                Paint().apply {
                                                    color = android.graphics.Color.CYAN
                                                    textSize = 14f
                                                    typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                                    setShadowLayer(3f, 1f, 1f, android.graphics.Color.BLACK)
                                                }
                                            )
                                        }
                                    }
                                } else {
                                    Text("Feed inactive. Toggle Live Video Scan.", color = CyberTheme.DIM, fontSize = 12.sp)
                                }
                            }
                        }
                    }
                }
            }
            2 -> {
                // Tab 3: VPS Torrents Center & Cloud Player cockpit
                LazyColumn(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Torrent search box
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.NEON_BLUE.copy(alpha = 0.2f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("🎬 SEARCH VPS TORRENTS", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(10.dp))
                                Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    OutlinedTextField(
                                        value = torrentQuery,
                                        onValueChange = { torrentQuery = it },
                                        placeholder = { Text("Movie/Show name...", color = CyberTheme.DIM) },
                                        textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                        modifier = Modifier.weight(1f),
                                        colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                    )
                                    Button(
                                        onClick = {
                                            if (torrentQuery.isNotEmpty()) {
                                                isSearchingTorrents = true
                                                torrentHits.clear()
                                                dispatchCommand("voice.torrent_search", JSONObject().apply { put("query", torrentQuery); put("limit", 10) }) { res ->
                                                    isSearchingTorrents = false
                                                    if (res != null) {
                                                        val result = res.optJSONObject("result")
                                                        val hits = result?.optJSONArray("hits")
                                                        if (hits != null) {
                                                            for (i in 0 until hits.length()) {
                                                                val hit = hits.optJSONObject(i)
                                                                if (hit != null) {
                                                                    val title = hit.optString("title", "Unknown")
                                                                    val sizeBytes = hit.optLong("size_bytes", 0)
                                                                    val sizeStr = if (sizeBytes > 1024 * 1024 * 1024) String.format("%.2f GB", sizeBytes / (1024.0 * 1024.0 * 1024.0)) else String.format("%.1f MB", sizeBytes / (1024.0 * 1024.0))
                                                                    val seeders = hit.optInt("seeders", 0)
                                                                    val leechers = hit.optInt("leechers", 0)
                                                                    val source = hit.optString("source", "N/A")
                                                                    val uri = hit.optString("access_uri", "")
                                                                    torrentHits.add(TorrentHit(title, sizeStr, seeders, leechers, source, uri))
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        },
                                        enabled = !isSearchingTorrents,
                                        colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN),
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        if (isSearchingTorrents) {
                                            CyberSpinner(size = 18.dp, color = CyberTheme.BG)
                                        } else {
                                            Text("SEARCH", color = CyberTheme.BG, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Scored Hits List
                    if (torrentHits.isNotEmpty() || isSearchingTorrents) {
                        item {
                            Card(
                                modifier = Modifier.fillMaxWidth().heightIn(max = 240.dp),
                                colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                                shape = RoundedCornerShape(16.dp),
                                border = BorderStroke(1.dp, CyberTheme.DIM.copy(alpha = 0.2f))
                            ) {
                                Column(modifier = Modifier.padding(14.dp)) {
                                    Text("🔎 SEARCH RESULTS", color = CyberTheme.ACCENT_CYAN, fontSize = 11.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                    Spacer(modifier = Modifier.height(8.dp))
                                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                        items(torrentHits) { hit ->
                                            Row(
                                                modifier = Modifier.fillMaxWidth().border(1.dp, CyberTheme.DIM.copy(alpha = 0.3f), RoundedCornerShape(10.dp)).padding(10.dp),
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Column(modifier = Modifier.weight(1f).padding(end = 8.dp)) {
                                                    Text(hit.title, color = CyberTheme.TEXT, fontSize = 11.sp, fontWeight = FontWeight.Bold, maxLines = 2)
                                                    Text("Size: ${hit.size} | Source: ${hit.source.uppercase()} | S:${hit.seeders} L:${hit.leechers}", color = CyberTheme.DIM, fontSize = 10.sp)
                                                }
                                                Button(
                                                    onClick = {
                                                        dispatchCommand("voice.aria2_add", JSONObject().apply { put("magnet", hit.accessUri) }) { res ->
                                                            if (res != null) {
                                                                val result = res.optJSONObject("result")
                                                                val gid = result?.optString("gid") ?: ""
                                                                if (gid.isNotEmpty()) {
                                                                    activeDownloads.add(ActiveDownload(gid = gid))
                                                                }
                                                            }
                                                        }
                                                    },
                                                    colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.NEON_GREEN),
                                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                                                    shape = RoundedCornerShape(6.dp)
                                                ) {
                                                    Text("GET", color = CyberTheme.BG, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // 🎬 VPS Media Catalog & Player Controllers
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.ACCENT_PURPLE.copy(alpha = 0.25f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("🎬 VPS CLOUD MOVIE CATALOG", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                    Button(
                                        onClick = {
                                            isFetchingVpsData = true
                                            trendingList.clear()
                                            trailersList.clear()
                                            scope.launch {
                                                try {
                                                    val urlTrending = "http://$vpsTailscaleHost:$vpsPort/api/trending"
                                                    val reqTrend = Request.Builder().url(urlTrending).build()
                                                    val resTrend = withContext(Dispatchers.IO) {
                                                        client.newCall(reqTrend).execute().use { r ->
                                                            if (r.isSuccessful) r.body?.string() else null
                                                        }
                                                    }
                                                    if (resTrend != null) {
                                                        val arr = JSONArray(resTrend)
                                                        for (i in 0 until arr.length()) {
                                                            val obj = arr.optJSONObject(i)
                                                            if (obj != null) {
                                                                trendingList.add(TrendingItem(
                                                                    title = obj.optString("title", "Movie"),
                                                                    category = obj.optString("category", "General"),
                                                                    seeds = obj.optInt("seeds", 10),
                                                                    leechs = obj.optInt("leechs", 2)
                                                                ))
                                                            }
                                                        }
                                                    }

                                                    val urlTrailers = "http://$vpsTailscaleHost:$vpsPort/api/trailers"
                                                    val reqTrailers = Request.Builder().url(urlTrailers).build()
                                                    val resTrailers = withContext(Dispatchers.IO) {
                                                        client.newCall(reqTrailers).execute().use { r ->
                                                            if (r.isSuccessful) r.body?.string() else null
                                                        }
                                                    }
                                                    if (resTrailers != null) {
                                                        val arr = JSONArray(resTrailers)
                                                        for (i in 0 until arr.length()) {
                                                            val obj = arr.optJSONObject(i)
                                                            if (obj != null) {
                                                                trailersList.add(TrailerItem(
                                                                    title = obj.optString("title", "Movie"),
                                                                    videoTitle = obj.optString("videoTitle", "Trailer"),
                                                                    youtubeId = obj.optString("youtubeId", ""),
                                                                    channel = obj.optString("channel", ""),
                                                                    duration = obj.optString("duration", "")
                                                                ))
                                                            }
                                                        }
                                                    }
                                                    vpsStatusLog = "Successfully loaded ${trendingList.size} movies and ${trailersList.size} trailers!"
                                                } catch (e: Exception) {
                                                    vpsStatusLog = "Connection Error: ${e.message}"
                                                } finally {
                                                    isFetchingVpsData = false
                                                }
                                            }
                                        },
                                        enabled = !isFetchingVpsData,
                                        colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_PURPLE),
                                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                                        shape = RoundedCornerShape(6.dp)
                                    ) {
                                        if (isFetchingVpsData) CyberSpinner(size = 14.dp, color = CyberTheme.TEXT) else Text("LOAD DATA", color = CyberTheme.TEXT, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                                    }
                                }
                                Spacer(modifier = Modifier.height(10.dp))
                                Text(vpsStatusLog, color = CyberTheme.DIM, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(10.dp))

                                // Trending Movies Grid Horizontal
                                if (trendingList.isNotEmpty()) {
                                    Text("🔥 TRENDING ON CLOUD", color = CyberTheme.TEXT, fontSize = 10.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                    Spacer(modifier = Modifier.height(6.dp))
                                    LazyRow(
                                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        items(trendingList) { item ->
                                            Column(
                                                modifier = Modifier
                                                    .width(160.dp)
                                                    .background(Color(0xFF0F101A), RoundedCornerShape(8.dp))
                                                    .border(1.dp, CyberTheme.DIM.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                                                    .padding(8.dp)
                                            ) {
                                                Text(item.title, color = CyberTheme.TEXT, fontSize = 11.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                                                Text(item.category, color = CyberTheme.DIM, fontSize = 9.sp, maxLines = 1)
                                                Text("S: ${item.seeds} L: ${item.leechs}", color = CyberTheme.NEON_GREEN, fontSize = 9.sp)
                                                Spacer(modifier = Modifier.height(6.dp))
                                                Button(
                                                    onClick = {
                                                        torrentQuery = item.title
                                                        // Automatically search in index
                                                        isSearchingTorrents = true
                                                        torrentHits.clear()
                                                        dispatchCommand("voice.torrent_search", JSONObject().apply { put("query", item.title); put("limit", 5) }) { res ->
                                                            isSearchingTorrents = false
                                                            if (res != null) {
                                                                val result = res.optJSONObject("result")
                                                                val hits = result?.optJSONArray("hits")
                                                                if (hits != null) {
                                                                    for (i in 0 until hits.length()) {
                                                                        val hit = hits.optJSONObject(i)
                                                                        if (hit != null) {
                                                                            val title = hit.optString("title", "Unknown")
                                                                            val sizeBytes = hit.optLong("size_bytes", 0)
                                                                            val sizeStr = if (sizeBytes > 1024 * 1024 * 1024) String.format("%.2f GB", sizeBytes / (1024.0 * 1024.0 * 1024.0)) else String.format("%.1f MB", sizeBytes / (1024.0 * 1024.0))
                                                                            val seeders = hit.optInt("seeders", 0)
                                                                            val leechers = hit.optInt("leechers", 0)
                                                                            val source = hit.optString("source", "N/A")
                                                                            val uri = hit.optString("access_uri", "")
                                                                            torrentHits.add(TorrentHit(title, sizeStr, seeders, leechers, source, uri))
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    },
                                                    colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN),
                                                    modifier = Modifier.fillMaxWidth().height(26.dp),
                                                    contentPadding = PaddingValues(0.dp),
                                                    shape = RoundedCornerShape(4.dp)
                                                ) {
                                                    Text("DOWNLOAD", color = CyberTheme.BG, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                                }
                                            }
                                        }
                                    }
                                }

                                if (trailersList.isNotEmpty()) {
                                    Spacer(modifier = Modifier.height(12.dp))
                                    Text("🎬 LIVE TRAILERS & STREAMS", color = CyberTheme.TEXT, fontSize = 10.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                    Spacer(modifier = Modifier.height(6.dp))
                                    LazyRow(
                                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        items(trailersList) { item ->
                                            Column(
                                                modifier = Modifier
                                                    .width(180.dp)
                                                    .background(Color(0xFF0F101A), RoundedCornerShape(8.dp))
                                                    .border(1.dp, CyberTheme.DIM.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                                                    .padding(8.dp)
                                            ) {
                                                Text(item.title, color = CyberTheme.TEXT, fontSize = 11.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                                                Text(item.videoTitle, color = CyberTheme.DIM, fontSize = 9.sp, maxLines = 1)
                                                Text("Duration: ${item.duration}", color = CyberTheme.NEON_PURPLE, fontSize = 9.sp)
                                                Spacer(modifier = Modifier.height(6.dp))
                                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                                    Button(
                                                        onClick = {
                                                            // Dispatch play_youtube command to Jetson Orin Nano Command Bridge
                                                            dispatchCommand("chat", JSONObject().apply {
                                                                put("text", "system: play youtube video ${item.youtubeId} on robot screen")
                                                                put("use_external_llm", false)
                                                            }) {}
                                                        },
                                                        colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.NEON_PINK),
                                                        modifier = Modifier.weight(1f).height(26.dp),
                                                        contentPadding = PaddingValues(0.dp),
                                                        shape = RoundedCornerShape(4.dp)
                                                    ) {
                                                        Text("📽️ PLAY", color = CyberTheme.TEXT, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Active Aria2 downloads panel
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth().heightIn(max = 240.dp),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.DIM.copy(alpha = 0.2f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("📥 ACTIVE ROBO-ARIA2 RUNS", color = CyberTheme.ACCENT_CYAN, fontSize = 11.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(8.dp))
                                if (activeDownloads.isEmpty()) {
                                    Box(modifier = Modifier.fillMaxWidth().height(80.dp), contentAlignment = Alignment.Center) {
                                        Text("No active downloads running on Jetson", color = CyberTheme.DIM, fontSize = 12.sp)
                                    }
                                } else {
                                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                        items(activeDownloads) { download ->
                                            Column(
                                                modifier = Modifier.fillMaxWidth().border(1.dp, CyberTheme.DIM.copy(alpha = 0.5f), RoundedCornerShape(10.dp)).padding(10.dp)
                                            ) {
                                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                                    Text("GID: ${download.gid}", color = CyberTheme.ACCENT_CYAN, fontSize = 11.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                                    Text("Status: ${download.status.uppercase()}", color = if (download.status == "active") CyberTheme.NEON_GREEN else CyberTheme.DIM, fontSize = 10.sp, fontWeight = FontWeight.SemiBold)
                                                }
                                                Spacer(modifier = Modifier.height(4.dp))
                                                LinearProgressIndicator(
                                                    progress = { download.progress / 100f },
                                                    modifier = Modifier.fillMaxWidth(),
                                                    color = CyberTheme.ACCENT_CYAN,
                                                    trackColor = CyberTheme.DIM.copy(alpha = 0.2f),
                                                )
                                                Spacer(modifier = Modifier.height(4.dp))
                                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                                    Text("${String.format("%.1f", download.progress)}% complete", color = CyberTheme.TEXT, fontSize = 10.sp)
                                                    Text("Speed: ${download.speed}", color = CyberTheme.TEXT, fontSize = 10.sp)
                                                }
                                                if (download.ttsText.isNotEmpty()) {
                                                    Spacer(modifier = Modifier.height(2.dp))
                                                    Text(download.ttsText, color = CyberTheme.DIM, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            3 -> {
                // Tab 4: System Stats, Devices Matrix, & Diagnostics
                LazyColumn(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Devices Status Matrix Card (THE TRIFECTA OF DEVICES)
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.ACCENT_CYAN.copy(alpha = 0.25f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("🌐 THE TRIFECTA OF DEVICE MATRIX", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(12.dp))
                                
                                // Device 1: Jetson Orin Nano
                                val colorJetson by animateColorAsState(if (isJetsonOnline) CyberTheme.NEON_GREEN else CyberTheme.NEON_PINK)
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .border(
                                            BorderStroke(
                                                width = if (isJetsonOnline) glowSpreadFloat.dp else 1.dp,
                                                color = colorJetson.copy(alpha = glowAlpha)
                                            ),
                                            RoundedCornerShape(8.dp)
                                        )
                                        .padding(10.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Image(
                                        painter = painterResource(id = R.drawable.jetson_icon),
                                        contentDescription = "Jetson Orin Nano",
                                        modifier = Modifier.size(50.dp).clip(RoundedCornerShape(8.dp)).border(1.dp, CyberTheme.DIM.copy(alpha = 0.5f), RoundedCornerShape(8.dp)),
                                        contentScale = ContentScale.Crop
                                    )
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text("Jetson Orin Nano", color = CyberTheme.TEXT, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Box(modifier = Modifier.size(8.dp).clip(RoundedCornerShape(4.dp)).background(colorJetson))
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Text(if (isJetsonOnline) "ONLINE" else "OFFLINE", color = colorJetson, fontSize = 9.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                        }
                                        Text("CPU: $cpuTempText | $cpuLoadText", color = CyberTheme.DIM, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                                    }
                                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                        Button(
                                            onClick = {
                                                dispatchCommand("chat", JSONObject().apply {
                                                    put("text", "system: start the robot competition platform launch stack")
                                                    put("use_external_llm", false)
                                                }) {}
                                            },
                                            colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN),
                                            shape = RoundedCornerShape(6.dp),
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                                        ) {
                                            Text("START", color = CyberTheme.BG, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                        }
                                        Button(
                                            onClick = {
                                                dispatchCommand("chat", JSONObject().apply {
                                                    put("text", "system: reboot the Jetson Orin Nano now")
                                                    put("use_external_llm", false)
                                                }) {}
                                            },
                                            colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.NEON_PINK),
                                            shape = RoundedCornerShape(6.dp),
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                                        ) {
                                            Text("REBOOT", color = CyberTheme.TEXT, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))

                                // Device 2: Arduino/UNO Q
                                val colorArduino by animateColorAsState(if (isArduinoOnline) CyberTheme.NEON_GREEN else CyberTheme.NEON_PINK)
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .border(
                                            BorderStroke(
                                                width = if (isArduinoOnline) glowSpreadFloat.dp else 1.dp,
                                                color = colorArduino.copy(alpha = glowAlpha)
                                            ),
                                            RoundedCornerShape(8.dp)
                                        )
                                        .padding(10.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Image(
                                        painter = painterResource(id = R.drawable.arduino_icon),
                                        contentDescription = "Arduino UNO Q",
                                        modifier = Modifier.size(50.dp).clip(RoundedCornerShape(8.dp)).border(1.dp, CyberTheme.DIM.copy(alpha = 0.5f), RoundedCornerShape(8.dp)),
                                        contentScale = ContentScale.Crop
                                    )
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text("Arduino UNO Q / MCU", color = CyberTheme.TEXT, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Box(modifier = Modifier.size(8.dp).clip(RoundedCornerShape(4.dp)).background(colorArduino))
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Text(if (isArduinoOnline) "ONLINE" else "OFFLINE", color = colorArduino, fontSize = 9.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                        }
                                        Text("Chassis: $batteryText | OLED: $currentEmotion", color = CyberTheme.DIM, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                                    }
                                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                            Button(
                                                onClick = {
                                                    dispatchCommand("chat", JSONObject().apply {
                                                        put("text", "system: reset the Arduino UNO Q serial connection")
                                                        put("use_external_llm", false)
                                                    }) {}
                                                },
                                                colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.NEON_PINK),
                                                shape = RoundedCornerShape(6.dp),
                                                contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp)
                                            ) {
                                                Text("RESET", color = CyberTheme.TEXT, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                            }
                                            Button(
                                                onClick = {
                                                    dispatchCommand("chat", JSONObject().apply {
                                                        put("text", "system: put the robot chassis into rest mode now")
                                                        put("use_external_llm", false)
                                                    }) {}
                                                },
                                                colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_PURPLE),
                                                shape = RoundedCornerShape(6.dp),
                                                contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp)
                                            ) {
                                                Text("REST", color = CyberTheme.TEXT, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                            }
                                        }
                                        Button(
                                            onClick = {
                                                dispatchCommand("chat", JSONObject().apply {
                                                    put("text", "system: calibrate the BNO055 IMU sensor")
                                                    put("use_external_llm", false)
                                                }) {}
                                            },
                                            colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN),
                                            shape = RoundedCornerShape(6.dp),
                                            modifier = Modifier.fillMaxWidth(),
                                            contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp)
                                        ) {
                                            Text("CALIBRATE IMU", color = CyberTheme.BG, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))

                                // Device 3: VPS cloud server
                                val colorVps by animateColorAsState(if (isVpsOnline) CyberTheme.NEON_GREEN else CyberTheme.NEON_PINK)
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .border(
                                            BorderStroke(
                                                width = if (isVpsOnline) glowSpreadFloat.dp else 1.dp,
                                                color = colorVps.copy(alpha = glowAlpha)
                                            ),
                                            RoundedCornerShape(8.dp)
                                        )
                                        .padding(10.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Image(
                                        painter = painterResource(id = R.drawable.vps_icon),
                                        contentDescription = "VPS Server",
                                        modifier = Modifier.size(50.dp).clip(RoundedCornerShape(8.dp)).border(1.dp, CyberTheme.DIM.copy(alpha = 0.5f), RoundedCornerShape(8.dp)),
                                        contentScale = ContentScale.Crop
                                    )
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text("VPS Storage Stack", color = CyberTheme.TEXT, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Box(modifier = Modifier.size(8.dp).clip(RoundedCornerShape(4.dp)).background(colorVps))
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Text(if (isVpsOnline) "ONLINE" else "OFFLINE", color = colorVps, fontSize = 9.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                        }
                                        Text("IP: $vpsTailscaleHost | Port: $vpsPort", color = CyberTheme.DIM, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                                    }
                                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                        Button(
                                            onClick = {
                                                dispatchCommand("chat", JSONObject().apply {
                                                    put("text", "system: sync repository code from VPS to Jetson now")
                                                    put("use_external_llm", false)
                                                }) {}
                                            },
                                            colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN),
                                            shape = RoundedCornerShape(6.dp),
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                                        ) {
                                            Text("SYNC REPO", color = CyberTheme.BG, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                        }
                                        Button(
                                            onClick = {
                                                dispatchCommand("chat", JSONObject().apply {
                                                    put("text", "system: reboot VPS service now")
                                                    put("use_external_llm", false)
                                                }) {}
                                            },
                                            colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.NEON_PINK),
                                            shape = RoundedCornerShape(6.dp),
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                                        ) {
                                            Text("REBOOT", color = CyberTheme.TEXT, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // System Resource Stats Card
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.NEON_GREEN.copy(alpha = 0.25f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("📊 SYSTEM RESOURCE TELEMETRY", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(10.dp))
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Column {
                                        Text(ramUsageText, color = CyberTheme.TEXT, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                                        Text(cpuLoadText, color = CyberTheme.TEXT, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                                    }
                                    Column {
                                        Text(diskUsageText, color = CyberTheme.TEXT, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                                        Text(processCountText, color = CyberTheme.TEXT, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                                    }
                                }
                            }
                        }
                    }

                    // 1. Hardware Devices Inspector
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.ACCENT_CYAN.copy(alpha = 0.25f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("🔩 HARDWARE DEVICES INVENTORY", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                    Button(
                                        onClick = {
                                            isScanningHardware = true
                                            hardwareScanResult = "Initializing hardware bus scan on robot..."
                                            dispatchCommand("query", JSONObject().apply {
                                                put("kind", "hardware")
                                                put("text", "")
                                                put("k", 10)
                                            }) { res ->
                                                isScanningHardware = false
                                                if (res != null) {
                                                    val result = res.optJSONObject("result")
                                                    val queued = result?.optBoolean("queued", false)
                                                    if (queued == true) {
                                                        hardwareScanResult = "Query sent! Check the ROS diagnostics pipeline or chat logs."
                                                    } else {
                                                        hardwareScanResult = res.toString(2)
                                                    }
                                                } else {
                                                    hardwareScanResult = "Error: Failed to fetch hardware inventory"
                                                }
                                            }
                                        },
                                        enabled = !isScanningHardware,
                                        colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_CYAN),
                                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                                        shape = RoundedCornerShape(6.dp)
                                    ) {
                                        if (isScanningHardware) CyberSpinner(size = 14.dp, color = CyberTheme.BG) else Text("SCAN", color = CyberTheme.BG, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                    }
                                }
                                Spacer(modifier = Modifier.height(10.dp))
                                Box(
                                    modifier = Modifier.fillMaxWidth().height(150.dp).background(Color(0xFF070810), RoundedCornerShape(10.dp)).border(1.dp, CyberTheme.DIM.copy(alpha = 0.3f), RoundedCornerShape(10.dp)).padding(8.dp)
                                ) {
                                    LazyColumn(modifier = Modifier.fillMaxSize()) {
                                        item {
                                            Text(hardwareScanResult, color = CyberTheme.NEON_GREEN, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // 2. AI Providers Tester
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.ACCENT_PURPLE.copy(alpha = 0.25f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("🤖 AI PROVIDER CONNECTION BENCHMARK", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(8.dp))

                                // Provider selector dropdown
                                var providerDropdownExpanded by remember { mutableStateOf(false) }
                                Box(modifier = Modifier.fillMaxWidth()) {
                                    Button(
                                        onClick = { providerDropdownExpanded = true },
                                        colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.ACCENT_PURPLE),
                                        modifier = Modifier.fillMaxWidth(),
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        Text("TEST ENGINE: $selectedDiagProvider", color = CyberTheme.TEXT, fontSize = 11.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                    }
                                    DropdownMenu(
                                        expanded = providerDropdownExpanded,
                                        onDismissRequest = { providerDropdownExpanded = false },
                                        modifier = Modifier.background(CyberTheme.BG_CARD).border(1.dp, CyberTheme.DIM.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                                    ) {
                                        diagnosticProviders.forEach { prov ->
                                            DropdownMenuItem(
                                                text = { Text(prov, color = CyberTheme.TEXT, fontSize = 11.sp, fontFamily = FontFamily.Monospace) },
                                                onClick = {
                                                    selectedDiagProvider = prov
                                                    providerDropdownExpanded = false
                                                }
                                            )
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = diagTestPrompt,
                                    onValueChange = { diagTestPrompt = it },
                                    label = { Text("Prompt text", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                                Spacer(modifier = Modifier.height(8.dp))

                                Button(
                                    onClick = {
                                        isTestingProvider = true
                                        diagTestResult = "Connecting to provider ${selectedDiagProvider}..."
                                        dispatchCommand("chat", JSONObject().apply {
                                            put("text", diagTestPrompt)
                                            put("use_external_llm", true)
                                        }) { res ->
                                            isTestingProvider = false
                                            if (res != null) {
                                                val result = res.optJSONObject("result")
                                                val reply = result?.optString("reply") ?: "No reply"
                                                diagTestResult = "[$selectedDiagProvider] Connection successful!\n\nReply: $reply"
                                            } else {
                                                diagTestResult = "Error: Provider benchmark timed out or returned empty response."
                                            }
                                        }
                                    },
                                    enabled = !isTestingProvider,
                                    colors = ButtonDefaults.buttonColors(containerColor = CyberTheme.NEON_GREEN),
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    if (isTestingProvider) CyberSpinner(size = 18.dp, color = CyberTheme.BG) else Text("TEST CONNECTION", color = CyberTheme.BG, fontWeight = FontWeight.Bold)
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                Box(
                                    modifier = Modifier.fillMaxWidth().height(120.dp).background(Color(0xFF070810), RoundedCornerShape(8.dp)).border(1.dp, CyberTheme.DIM.copy(alpha = 0.3f), RoundedCornerShape(8.dp)).padding(8.dp)
                                ) {
                                    LazyColumn(modifier = Modifier.fillMaxSize()) {
                                        item {
                                            Text(diagTestResult, color = CyberTheme.TEXT, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            4 -> {
                // Tab 5: Settings Manager
                LazyColumn(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Jetson link parameters
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.NEON_BLUE.copy(alpha = 0.2f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("🤖 JETSON ORIN NANO HOSTS", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = jetsonWifiHost,
                                    onValueChange = { jetsonWifiHost = it },
                                    label = { Text("Local WiFi IP", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = jetsonTailscaleHost,
                                    onValueChange = { jetsonTailscaleHost = it },
                                    label = { Text("Tailscale VPN IP", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = jetsonPort,
                                    onValueChange = { jetsonPort = it },
                                    label = { Text("API Port", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                            }
                        }
                    }

                    // UNO Q parameters
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.ACCENT_PURPLE.copy(alpha = 0.2f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("🔩 UNO Q CORE HOSTS", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = unoqWifiHost,
                                    onValueChange = { unoqWifiHost = it },
                                    label = { Text("Local WiFi IP", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = unoqTailscaleHost,
                                    onValueChange = { unoqTailscaleHost = it },
                                    label = { Text("Tailscale VPN IP", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = unoqPort,
                                    onValueChange = { unoqPort = it },
                                    label = { Text("Port", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                            }
                        }
                    }

                    // VPS stack parameters
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CyberTheme.BG_CARD),
                            shape = RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, CyberTheme.NEON_BLUE.copy(alpha = 0.2f))
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("🌐 VPS HOST & SECURITY", color = CyberTheme.ACCENT_CYAN, fontSize = 12.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = vpsTailscaleHost,
                                    onValueChange = { vpsTailscaleHost = it },
                                    label = { Text("VPS VPN / Cloud IP", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = vpsPort,
                                    onValueChange = { vpsPort = it },
                                    label = { Text("VPS Stack Port", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = vpsToken,
                                    onValueChange = { vpsToken = it },
                                    label = { Text("VPS Token", color = CyberTheme.DIM) },
                                    textStyle = LocalTextStyle.current.copy(color = CyberTheme.TEXT),
                                    visualTransformation = PasswordVisualTransformation(),
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = CyberTheme.ACCENT_CYAN, unfocusedBorderColor = CyberTheme.DIM.copy(alpha = 0.5f))
                                )
                            }
                        }
                    }
                }
            }
            5 -> {
                // ═══ TAB 6: FULL-SCREEN VISUAL MAP ═══
                // Camera feed + LIDAR radar + YOLO + Motion + Sweep + Controls + HUD
                var sweepAngle by remember { mutableFloatStateOf(0f) }
                var mapShowLidar by remember { mutableStateOf(true) }
                var mapShowYolo by remember { mutableStateOf(true) }
                var mapShowMotion by remember { mutableStateOf(true) }
                var mapShowCamera by remember { mutableStateOf(true) }
                var mapShowObstacles by remember { mutableStateOf(true) }
                var mapShowSweep by remember { mutableStateOf(true) }

                // Sweep animation
                LaunchedEffect(Unit) {
                    while (true) {
                        sweepAngle = (sweepAngle + 2f) % 360f
                        delay(16) // ~60fps
                    }
                }

                // Auto-enable LIDAR
                LaunchedEffect(Unit) {
                    if (!isLidarActive) isLidarActive = true
                }

                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .background(Color.Black)
                ) {
                    Canvas(modifier = Modifier.fillMaxSize()) {
                        val canvasW = size.width
                        val canvasH = size.height
                        val cx = canvasW / 2f
                        val cy = canvasH / 2f
                        val maxRadius = minOf(cx, cy) * 0.82f
                        val maxDisplayMm = 5000f

                        // Dark background
                        drawContext.canvas.nativeCanvas.drawColor(
                            android.graphics.Color.argb(255, 8, 8, 14)
                        )

                        // ═══ CAMERA FEED BACKGROUND (dimmed) ═══
                        if (mapShowCamera && cameraBitmap != null) {
                            val bmp = cameraBitmap!!
                            val bmpScale = maxOf(canvasW / bmp.width, canvasH / bmp.height)
                            val bmpW = bmp.width * bmpScale
                            val bmpH = bmp.height * bmpScale
                            val paint = Paint().apply { alpha = 35 } // very dim
                            drawContext.canvas.nativeCanvas.drawBitmap(
                                bmp, null,
                                android.graphics.RectF(
                                    (canvasW - bmpW) / 2f, (canvasH - bmpH) / 2f,
                                    (canvasW + bmpW) / 2f, (canvasH + bmpH) / 2f
                                ),
                                paint
                            )
                        }

                        // ═══ DISTANCE RINGS (1m to 5m) ═══
                        for (m in 1..5) {
                            val r = (m * 1000f / maxDisplayMm) * maxRadius
                            drawContext.canvas.nativeCanvas.drawCircle(
                                cx, cy, r,
                                Paint().apply {
                                    color = android.graphics.Color.argb(35, 0, 200, 255)
                                    style = Paint.Style.STROKE
                                    strokeWidth = if (m % 2 == 0) 1.2f else 0.8f
                                }
                            )
                            drawContext.canvas.nativeCanvas.drawText(
                                "${m}m",
                                cx + 5f, cy - r + 13f,
                                Paint().apply {
                                    color = android.graphics.Color.argb(100, 0, 200, 255)
                                    textSize = 11f
                                    typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                }
                            )
                        }

                        // ═══ CROSS-HAIR + DIAGONALS ═══
                        val crossPaint = Paint().apply {
                            color = android.graphics.Color.argb(25, 0, 200, 255)
                            strokeWidth = 1f
                        }
                        drawContext.canvas.nativeCanvas.drawLine(
                            cx - maxRadius, cy, cx + maxRadius, cy, crossPaint
                        )
                        drawContext.canvas.nativeCanvas.drawLine(
                            cx, cy - maxRadius, cx, cy + maxRadius, crossPaint
                        )
                        val diagPaint = Paint().apply {
                            color = android.graphics.Color.argb(12, 0, 200, 255)
                            strokeWidth = 0.5f
                        }
                        for (angle in 30..330 step 30) {
                            val rad = Math.toRadians(angle.toDouble())
                            val ex = cx + (maxRadius * Math.sin(rad)).toFloat()
                            val ey = cy - (maxRadius * Math.cos(rad)).toFloat()
                            drawContext.canvas.nativeCanvas.drawLine(cx, cy, ex, ey, diagPaint)
                            // Angle labels
                            drawContext.canvas.nativeCanvas.drawText(
                                "${angle}\u00b0",
                                cx + (maxRadius + 8f) * Math.sin(rad).toFloat() - 8f,
                                cy - (maxRadius + 8f) * Math.cos(rad).toFloat() + 4f,
                                Paint().apply {
                                    color = android.graphics.Color.argb(50, 0, 200, 255)
                                    textSize = 8f
                                    typeface = Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL)
                                }
                            )
                        }

                        // ═══ RADAR SWEEP LINE ═══
                        if (mapShowSweep && lidarPointCount > 0) {
                            val sweepRad = Math.toRadians(sweepAngle.toDouble())
                            val sweepEndX = cx + (maxRadius * Math.sin(sweepRad)).toFloat()
                            val sweepEndY = cy - (maxRadius * Math.cos(sweepRad)).toFloat()
                            // Sweep trail (fading arc)
                            for (trail in 0..30) {
                                val trailAngle = sweepAngle - trail * 3f
                                if (trailAngle < 0) continue
                                val trailRad = Math.toRadians(trailAngle.toDouble())
                                val trailX = cx + (maxRadius * Math.sin(trailRad)).toFloat()
                                val trailY = cy - (maxRadius * Math.cos(trailRad)).toFloat()
                                val alpha = (30 - trail) * 2
                                drawContext.canvas.nativeCanvas.drawLine(
                                    cx, cy, trailX, trailY,
                                    Paint().apply {
                                        color = android.graphics.Color.argb(alpha, 0, 255, 150)
                                        strokeWidth = 1f
                                    }
                                )
                            }
                            // Main sweep line
                            drawContext.canvas.nativeCanvas.drawLine(
                                cx, cy, sweepEndX, sweepEndY,
                                Paint().apply {
                                    color = android.graphics.Color.argb(200, 0, 255, 150)
                                    strokeWidth = 2f
                                    setShadowLayer(6f, 0f, 0f, android.graphics.Color.GREEN)
                                }
                            )
                        }

                        // ═══ LIDAR OBSTACLE OUTLINE ═══
                        if (mapShowObstacles && lidarPoints.size > 5) {
                            val obstaclePath = android.graphics.Path()
                            var started = false
                            lidarPoints.filter { it.distance in 100..maxDisplayMm.toInt() }
                                .sortedBy { it.angle }
                                .forEach { pt ->
                                    val r = (pt.distance.toFloat() / maxDisplayMm) * maxRadius
                                    val rad = Math.toRadians(pt.angle.toDouble())
                                    val px = cx + (r * Math.sin(rad)).toFloat()
                                    val py = cy - (r * Math.cos(rad)).toFloat()
                                    if (!started) {
                                        obstaclePath.moveTo(px, py)
                                        started = true
                                    } else {
                                        obstaclePath.lineTo(px, py)
                                    }
                                }
                            obstaclePath.close()
                            // Filled obstacle area
                            drawContext.canvas.nativeCanvas.drawPath(
                                obstaclePath,
                                Paint().apply {
                                    color = android.graphics.Color.argb(20, 0, 255, 100)
                                    style = Paint.Style.FILL
                                }
                            )
                            // Outline
                            drawContext.canvas.nativeCanvas.drawPath(
                                obstaclePath,
                                Paint().apply {
                                    color = android.graphics.Color.argb(80, 0, 255, 100)
                                    style = Paint.Style.STROKE
                                    strokeWidth = 1.5f
                                }
                            )
                        }

                        // ═══ LIDAR POINTS ═══
                        if (mapShowLidar) {
                            lidarPoints.forEach { pt ->
                                if (pt.distance in 1..maxDisplayMm.toInt()) {
                                    val r = (pt.distance.toFloat() / maxDisplayMm) * maxRadius
                                    val rad = Math.toRadians(pt.angle.toDouble())
                                    val px = cx + (r * Math.sin(rad)).toFloat()
                                    val py = cy - (r * Math.cos(rad)).toFloat()
                                    // Outer glow
                                    drawContext.canvas.nativeCanvas.drawCircle(
                                        px, py, 4f,
                                        Paint().apply {
                                            color = android.graphics.Color.argb(50, 0, 255, 100)
                                            style = Paint.Style.FILL
                                        }
                                    )
                                    // Core dot
                                    drawContext.canvas.nativeCanvas.drawCircle(
                                        px, py, 2f,
                                        Paint().apply {
                                            color = android.graphics.Color.GREEN
                                            style = Paint.Style.FILL
                                        }
                                    )
                                }
                            }
                        }

                        // ═══ YOLO DETECTIONS ═══
                        if (mapShowYolo) {
                            detectedBoxes.forEach { box ->
                                val boxCx = (box.x1 + box.x2) / 2f
                                val normX = if (frameW > 0) boxCx / frameW else 0.5f
                                val objAngle = (normX * 360f - 180f + 360f) % 360f
                                var closestDist = 0
                                var minAngleDiff = 999f
                                lidarPoints.forEach { pt ->
                                    val diff = kotlin.math.abs(pt.angle - objAngle)
                                    val minDiff = minOf(diff, 360f - diff)
                                    if (minDiff < minAngleDiff && pt.distance in 100..5000) {
                                        minAngleDiff = minDiff
                                        closestDist = pt.distance
                                    }
                                }
                                val distText = if (closestDist > 0) "${closestDist / 1000.0f}m" else "?"
                                if (closestDist > 0 && closestDist <= maxDisplayMm.toInt()) {
                                    val r = (closestDist.toFloat() / maxDisplayMm) * maxRadius
                                    val rad = Math.toRadians(objAngle.toDouble())
                                    val px = cx + (r * Math.sin(rad)).toFloat()
                                    val py = cy - (r * Math.cos(rad)).toFloat()
                                    // Red outer ring
                                    drawContext.canvas.nativeCanvas.drawCircle(
                                        px, py, 10f,
                                        Paint().apply {
                                            color = android.graphics.Color.argb(60, 255, 0, 0)
                                            style = Paint.Style.FILL
                                        }
                                    )
                                    // Red inner dot
                                    drawContext.canvas.nativeCanvas.drawCircle(
                                        px, py, 4f,
                                        Paint().apply {
                                            color = android.graphics.Color.RED
                                            style = Paint.Style.FILL
                                        }
                                    )
                                    // Line from center to object
                                    drawContext.canvas.nativeCanvas.drawLine(
                                        cx, cy, px, py,
                                        Paint().apply {
                                            color = android.graphics.Color.argb(40, 255, 80, 80)
                                            strokeWidth = 1f
                                            pathEffect = android.graphics.DashPathEffect(floatArrayOf(6f, 6f), 0f)
                                        }
                                    )
                                    // Label with background
                                    val label = "${box.label} $distText"
                                    val labelPaint = Paint().apply {
                                        color = android.graphics.Color.RED
                                        textSize = 12f
                                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                    }
                                    val labelW = labelPaint.measureText(label)
                                    drawContext.canvas.nativeCanvas.drawRect(
                                        px + 8f, py - 14f, px + 12f + labelW, py + 2f,
                                        Paint().apply {
                                            color = android.graphics.Color.argb(160, 0, 0, 0)
                                            style = Paint.Style.FILL
                                        }
                                    )
                                    drawContext.canvas.nativeCanvas.drawText(
                                        label, px + 10f, py - 2f, labelPaint
                                    )
                                }
                            }
                        }

                        // ═══ MOTION REGIONS ═══
                        if (mapShowMotion) {
                            motionBoxes.forEach { box ->
                                val boxCx = (box.x1 + box.x2) / 2f
                                val normX = if (frameW > 0) boxCx / frameW else 0.5f
                                val motAngle = (normX * 360f - 180f + 360f) % 360f
                                val motRadius = maxRadius * 0.65f
                                val rad = Math.toRadians(motAngle.toDouble())
                                val px = cx + (motRadius * Math.sin(rad)).toFloat()
                                val py = cy - (motRadius * Math.cos(rad)).toFloat()
                                // Yellow glow
                                drawContext.canvas.nativeCanvas.drawCircle(
                                    px, py, 8f,
                                    Paint().apply {
                                        color = android.graphics.Color.argb(70, 255, 255, 0)
                                        style = Paint.Style.FILL
                                    }
                                )
                                // Yellow dot
                                drawContext.canvas.nativeCanvas.drawCircle(
                                    px, py, 3f,
                                    Paint().apply {
                                        color = android.graphics.Color.YELLOW
                                        style = Paint.Style.FILL
                                    }
                                )
                                // Motion label
                                drawContext.canvas.nativeCanvas.drawText(
                                    "MOTION",
                                    px + 8f, py - 4f,
                                    Paint().apply {
                                        color = android.graphics.Color.argb(180, 255, 255, 0)
                                        textSize = 9f
                                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                    }
                                )
                            }
                        }

                        // ═══ CENTER TANK ═══
                        // Tank body
                        drawContext.canvas.nativeCanvas.drawRect(
                            cx - 8f, cy - 5f, cx + 8f, cy + 5f,
                            Paint().apply {
                                color = android.graphics.Color.CYAN
                                style = Paint.Style.FILL
                            }
                        )
                        // Tank turret
                        drawContext.canvas.nativeCanvas.drawCircle(
                            cx, cy - 8f, 5f,
                            Paint().apply {
                                color = android.graphics.Color.CYAN
                                style = Paint.Style.FILL
                            }
                        )
                        // Tank barrel
                        drawContext.canvas.nativeCanvas.drawLine(
                            cx, cy - 8f, cx, cy - 18f,
                            Paint().apply {
                                color = android.graphics.Color.CYAN
                                strokeWidth = 3f
                            }
                        )
                        // Label
                        drawContext.canvas.nativeCanvas.drawText(
                            "TANK",
                            cx + 14f, cy + 4f,
                            Paint().apply {
                                color = android.graphics.Color.CYAN
                                textSize = 10f
                                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                setShadowLayer(3f, 0f, 0f, android.graphics.Color.BLACK)
                            }
                        )

                        // ═══ TOP HUD ═══
                        // Background bar
                        drawContext.canvas.nativeCanvas.drawRect(
                            0f, 0f, canvasW, 56f,
                            Paint().apply {
                                color = android.graphics.Color.argb(180, 8, 8, 14)
                            }
                        )
                        // Title
                        drawContext.canvas.nativeCanvas.drawText(
                            "TANK OS VISUAL MAP",
                            12f, 18f,
                            Paint().apply {
                                color = android.graphics.Color.CYAN
                                textSize = 14f
                                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                                setShadowLayer(3f, 0f, 0f, android.graphics.Color.BLACK)
                            }
                        )
                        // Stats line 1
                        drawContext.canvas.nativeCanvas.drawText(
                            "YOLO:${detectedBoxes.size}  LIDAR:${lidarPointCount}pts  MOTION:${motionBoxes.size}",
                            12f, 34f,
                            Paint().apply {
                                color = android.graphics.Color.GREEN
                                textSize = 12f
                                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                            }
                        )
                        // Stats line 2
                        if (lidarPointCount > 0) {
                            drawContext.canvas.nativeCanvas.drawText(
                                "Range: ${lidarMinDist / 1000}m - ${lidarMaxDist / 1000}m  |  ${batteryText}  |  ${cpuTempText}",
                                12f, 50f,
                                Paint().apply {
                                    color = android.graphics.Color.argb(160, 0, 255, 100)
                                    textSize = 11f
                                    typeface = Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL)
                                }
                            )
                        }

                        // ═══ BOTTOM LEGEND ═══
                        drawContext.canvas.nativeCanvas.drawRect(
                            0f, canvasH - 36f, canvasW, canvasH,
                            Paint().apply {
                                color = android.graphics.Color.argb(180, 8, 8, 14)
                            }
                        )
                        val legY = canvasH - 16f
                        // Green = LIDAR
                        drawContext.canvas.nativeCanvas.drawCircle(20f, legY - 3f, 5f, Paint().apply { color = android.graphics.Color.GREEN; style = Paint.Style.FILL })
                        drawContext.canvas.nativeCanvas.drawText("LIDAR", 30f, legY, Paint().apply { color = android.graphics.Color.WHITE; textSize = 10f; typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD) })
                        // Red = YOLO
                        drawContext.canvas.nativeCanvas.drawCircle(95f, legY - 3f, 5f, Paint().apply { color = android.graphics.Color.RED; style = Paint.Style.FILL })
                        drawContext.canvas.nativeCanvas.drawText("YOLO", 105f, legY, Paint().apply { color = android.graphics.Color.WHITE; textSize = 10f; typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD) })
                        // Yellow = MOTION
                        drawContext.canvas.nativeCanvas.drawCircle(155f, legY - 3f, 5f, Paint().apply { color = android.graphics.Color.YELLOW; style = Paint.Style.FILL })
                        drawContext.canvas.nativeCanvas.drawText("MOTION", 165f, legY, Paint().apply { color = android.graphics.Color.WHITE; textSize = 10f; typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD) })
                        // Cyan = TANK
                        drawContext.canvas.nativeCanvas.drawCircle(240f, legY - 3f, 5f, Paint().apply { color = android.graphics.Color.CYAN; style = Paint.Style.FILL })
                        drawContext.canvas.nativeCanvas.drawText("TANK", 250f, legY, Paint().apply { color = android.graphics.Color.WHITE; textSize = 10f; typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD) })
                    }

                    // ═══ CONTROL PANEL (top-right floating) ═══
                    Column(
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(top = 60.dp, end = 8.dp)
                            .background(Color(0xCC0A0A10), RoundedCornerShape(12.dp))
                            .border(1.dp, CyberTheme.DIM.copy(alpha = 0.3f), RoundedCornerShape(12.dp))
                            .padding(8.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        listOf(
                            "📷 Camera" to mapShowCamera,
                            "📡 LIDAR" to mapShowLidar,
                            "🟢 Obstacles" to mapShowObstacles,
                            "🔴 YOLO" to mapShowYolo,
                            "🟡 Motion" to mapShowMotion,
                            "〰️ Sweep" to mapShowSweep
                        ).forEach { (label, state) ->
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.clickable {
                                    when (label) {
                                        "📷 Camera" -> mapShowCamera = !mapShowCamera
                                        "📡 LIDAR" -> mapShowLidar = !mapShowLidar
                                        "🟢 Obstacles" -> mapShowObstacles = !mapShowObstacles
                                        "🔴 YOLO" -> mapShowYolo = !mapShowYolo
                                        "🟡 Motion" -> mapShowMotion = !mapShowMotion
                                        "〰️ Sweep" -> mapShowSweep = !mapShowSweep
                                    }
                                }
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(10.dp)
                                        .background(
                                            if (state) Color(0xFF00FF00) else Color(0xFF333333),
                                            RoundedCornerShape(3.dp)
                                        )
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    label,
                                    color = if (state) CyberTheme.TEXT else CyberTheme.DIM,
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = if (state) FontWeight.Bold else FontWeight.Normal
                                )
                            }
                        }
                    }

                    // ═══ CAMERA SOURCE TOGGLE (bottom-left) ═══
                    Row(
                        modifier = Modifier
                            .align(Alignment.BottomStart)
                            .padding(start = 8.dp, bottom = 42.dp)
                            .background(Color(0xCC0A0A10), RoundedCornerShape(8.dp))
                            .border(1.dp, CyberTheme.DIM.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                            .padding(horizontal = 8.dp, vertical = 4.dp),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("CAM:", color = CyberTheme.DIM, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                        listOf("JETSON", "ARDUINO").forEach { src ->
                            Text(
                                text = if (activeCameraSource == src) "> $src" else "  $src",
                                color = if (activeCameraSource == src) CyberTheme.ACCENT_CYAN else CyberTheme.DIM,
                                fontSize = 9.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = if (activeCameraSource == src) FontWeight.Bold else FontWeight.Normal,
                                modifier = Modifier.clickable {
                                    activeCameraSource = src
                                    detectedBoxes.clear()
                                }
                            )
                        }
                    }
                }
            }
        } // when
        } // Crossfade
    }
}

@Composable
fun CyberSpinner(size: androidx.compose.ui.unit.Dp, color: Color) {
    Box(
        modifier = Modifier.size(size),
        contentAlignment = Alignment.Center
    ) {
        CircularProgressIndicator(
            modifier = Modifier.fillMaxSize(),
            color = color,
            strokeWidth = 2.dp
        )
    }
}