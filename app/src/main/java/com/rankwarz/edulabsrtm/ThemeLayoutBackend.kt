package com.rankwarz.edulabsrtm

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

private const val THEME_LAYOUT_BACKEND_URL = "https://medigyaan.xyz/Neurons/theme_layout_backend.php"
private const val PREFS_THEME_CACHE = "theme_layout_cache"
private const val KEY_CACHED_LAYOUTS = "cached_layouts"
private const val KEY_CACHED_VERSION = "cached_version"
private const val TAG = "ThemeLayoutBackend"

data class ThemeLayoutCatalogResponse(
    val ok: Boolean = false,
    val version: Long = 0L,
    val layouts: List<RemoteThemeLayout> = emptyList(),
    val layout: RemoteThemeLayout? = null,
    val error: String? = null
)

data class RemoteThemeLayout(
    val layout_key: String = "",
    val layout_name: String = "",
    val family: String = "",
    val cover: String = "",
    val page: String = "",
    val table: String = "",
    val chart: String = "",
    val page_chrome_layout: String = "",
    val title_page_layout: String = "",
    val chapter_layout: String = "",
    val section_layout: String = "",
    val paragraph_layout: String = "",
    val table_layout: String = "",
    val chart_layout: String = "",
    val figure_layout: String = "",
    val header_footer_layout: String = "",
    val special_page_layout: String = "",
    val accent_color: String = "",
    val soft_color: String = "",
    val header_fill_color: String = "",
    val footer_fill_color: String = "",
    val rule_color: String = "",
    val settings_json: String = "",
    val preview_json: String = "",
    val logo_position: String = "top-right",
    val logo_size: String = "medium",
    val logo_style: String = "rounded",
    val logo_offset_x: Int = 0,
    val logo_offset_y: Int = 0,
    val page_margin: String = "normal",
    val font_scheme: String = "serif",
    val shadow_depth: String = "light",
    val updated_at: Long = 0L,
    val sort_order: Int = 0,
    val is_active: Boolean = true
)

private val themeLayoutGson = Gson()

/**
 * Check if a newer version of theme layouts is available on the server.
 * Returns the server version if newer, null if same or error.
 */
suspend fun checkRemoteThemeVersion(): Long? = withContext(Dispatchers.IO) {
    try {
        val url = URL("$THEME_LAYOUT_BACKEND_URL?action=check_version&ts=${System.currentTimeMillis()}")
        val connection = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 10000
            readTimeout = 10000
            requestMethod = "GET"
            setRequestProperty("Accept", "application/json")
        }
        val code = connection.responseCode
        val raw = bufferedResponse(connection)
        connection.disconnect()
        if (code !in 200..299) return@withContext null
        val resp = themeLayoutGson.fromJson(raw, ThemeLayoutCatalogResponse::class.java)
        if (resp.ok) resp.version else null
    } catch (e: Exception) {
        Log.w(TAG, "Failed to check theme version", e)
        null
    }
}

/**
 * Fetch all active remote theme layouts from the server.
 */
suspend fun fetchRemoteThemeLayouts(): List<RemoteThemeLayout> = withContext(Dispatchers.IO) {
    val response = fetchRemoteThemeCatalog()
    response.layouts
        .filter { it.is_active }
        .sortedWith(compareBy<RemoteThemeLayout> { it.sort_order }.thenBy { it.layout_name.lowercase() })
}

/**
 * Fetch a single remote theme layout by key.
 */
suspend fun fetchRemoteThemeLayout(layoutKey: String): RemoteThemeLayout? = withContext(Dispatchers.IO) {
    if (layoutKey.isBlank()) return@withContext null
    try {
        val url = URL("$THEME_LAYOUT_BACKEND_URL?action=get&layout_key=${java.net.URLEncoder.encode(layoutKey, "UTF-8")}&ts=${System.currentTimeMillis()}")
        val connection = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 10000
            readTimeout = 15000
            requestMethod = "GET"
            setRequestProperty("Accept", "application/json")
        }
        val code = connection.responseCode
        val raw = bufferedResponse(connection)
        connection.disconnect()
        if (code !in 200..299) return@withContext null
        val resp = themeLayoutGson.fromJson(raw, ThemeLayoutCatalogResponse::class.java)
        resp.layout?.takeIf { it.is_active }
    } catch (e: Exception) {
        Log.w(TAG, "Failed to fetch remote theme layout: $layoutKey", e)
        null
    }
}

/**
 * Get the cached server version from local prefs.
 */
fun getCachedThemeVersion(context: Context): Long {
    return context.getSharedPreferences(PREFS_THEME_CACHE, Context.MODE_PRIVATE)
        .getLong(KEY_CACHED_VERSION, 0L)
}

/**
 * Get cached remote layouts from local prefs.
 */
fun getCachedRemoteThemeLayouts(context: Context): List<RemoteThemeLayout> {
    val json = context.getSharedPreferences(PREFS_THEME_CACHE, Context.MODE_PRIVATE)
        .getString(KEY_CACHED_LAYOUTS, null) ?: return emptyList()
    return try {
        val type = object : TypeToken<List<RemoteThemeLayout>>() {}.type
        themeLayoutGson.fromJson(json, type)
    } catch (e: Exception) {
        emptyList()
    }
}

/**
 * Cache remote layouts locally so they're available offline.
 */
fun cacheRemoteThemeLayouts(context: Context, layouts: List<RemoteThemeLayout>, version: Long) {
    context.getSharedPreferences(PREFS_THEME_CACHE, Context.MODE_PRIVATE).edit()
        .putString(KEY_CACHED_LAYOUTS, themeLayoutGson.toJson(layouts))
        .putLong(KEY_CACHED_VERSION, version)
        .apply()
}

/**
 * Sync remote layouts: check version, download if newer, cache locally.
 * Returns true if new layouts were downloaded.
 */
suspend fun syncRemoteThemeLayouts(context: Context): Boolean = withContext(Dispatchers.IO) {
    try {
        val serverVersion = checkRemoteThemeVersion() ?: return@withContext false
        val cachedVersion = getCachedThemeVersion(context)
        if (serverVersion <= cachedVersion) return@withContext false

        Log.d(TAG, "Newer theme layouts available (server: $serverVersion, cached: $cachedVersion), downloading...")
        val layouts = fetchRemoteThemeLayouts()
        if (layouts.isEmpty()) return@withContext false

        cacheRemoteThemeLayouts(context, layouts, serverVersion)
        Log.d(TAG, "Downloaded ${layouts.size} remote theme layouts")
        true
    } catch (e: Exception) {
        Log.w(TAG, "Failed to sync remote theme layouts", e)
        false
    }
}

/**
 * Check if a layout_key corresponds to a remote (server-synced) layout.
 */
fun isRemoteLayout(selection: String): Boolean {
    return selection.contains("|SERVER:", ignoreCase = true)
}

/**
 * Resolve a selection string to a RemoteThemeLayout if it's a server layout.
 */
fun resolveRemoteLayout(selection: String, remoteLayouts: List<RemoteThemeLayout>): RemoteThemeLayout? {
    if (!isRemoteLayout(selection)) return null
    val key = selection.substringAfter("SERVER:", "").substringBefore("|").trim()
    return remoteLayouts.firstOrNull { it.layout_key.equals(key, ignoreCase = true) }
}

/**
 * Extract the pure color theme name from any selection string.
 * e.g. "CLASSIC|SERVER:FOO|Bar" -> "CLASSIC"
 */
fun colorThemeFromSelection(selection: String): String {
    return selection.substringBefore("|").trim().ifBlank { "CLASSIC" }
}

/**
 * Extract the layout token (after the color theme) from a selection string.
 */
fun layoutTokenFromSelection(selection: String): String {
    val afterColor = selection.substringAfter("|", missingDelimiterValue = "").trim()
    if (afterColor.startsWith("SERVER:", ignoreCase = true)) {
        return afterColor.substringBefore("|").trim() // returns "SERVER:XXXX"
    }
    return afterColor.substringBefore("|").trim()
}

/**
 * Safe enum parser — returns null instead of throwing.
 */
inline fun <reified T : Enum<T>> enumValueOfOrNull(name: String): T? {
    return try {
        enumValueOf<T>(name.uppercase().replace(Regex("[^A-Z0-9_]"), ""))
    } catch (_: IllegalArgumentException) { null }
}

/**
 * Parse a hex color string like "#1B3A57" or "1B3A57" to Android Int color.
 */
fun parseHexColor(hex: String): Int? {
    return try {
        val h = if (hex.startsWith("#")) hex else "#$hex"
        android.graphics.Color.parseColor(h)
    } catch (_: Exception) { null }
}

private fun fetchRemoteThemeCatalog(): ThemeLayoutCatalogResponse {
    val url = URL("$THEME_LAYOUT_BACKEND_URL?action=list&ts=${System.currentTimeMillis()}")
    val connection = (url.openConnection() as HttpURLConnection).apply {
        connectTimeout = 15000
        readTimeout = 20000
        requestMethod = "GET"
        setRequestProperty("Accept", "application/json")
    }

    return try {
        val code = connection.responseCode
        val raw = bufferedResponse(connection)
        if (code !in 200..299) {
            throw IllegalStateException("Theme layout backend HTTP $code: ${raw.take(500)}")
        }
        themeLayoutGson.fromJson(raw, ThemeLayoutCatalogResponse::class.java)
    } finally {
        connection.disconnect()
    }
}

private fun bufferedResponse(connection: HttpURLConnection): String {
    val stream = runCatching { connection.inputStream }.getOrNull() ?: connection.errorStream
    if (stream == null) return ""
    return BufferedReader(InputStreamReader(stream)).use { reader ->
        buildString {
            var line: String?
            while (reader.readLine().also { line = it } != null) {
                append(line)
            }
        }
    }
}

fun RemoteThemeLayout.selectionValue(colorTheme: String): String {
    return "${colorTheme.uppercase()}|SERVER:${layout_key.trim()}|${layout_name.trim()}"
}

fun selectionLayoutToken(selection: String): String {
    val token = selection.substringAfter("|", missingDelimiterValue = "").trim()
    if (token.isBlank()) return ""
    return if (token.startsWith("SERVER:", ignoreCase = true)) {
        "SERVER:${token.removePrefix("SERVER:").substringBefore("|").trim()}"
    } else {
        token.substringBefore("|").trim()
    }
}

fun selectionLayoutLabel(selection: String): String {
    val token = selection.substringAfter("|", missingDelimiterValue = "").trim()
    if (token.isBlank()) return ""
    return token.substringAfter("|", missingDelimiterValue = "").trim()
}

fun selectionValueForLayout(
    colorTheme: String,
    layoutToken: String,
    remoteLayouts: List<RemoteThemeLayout> = emptyList()
): String {
    val normalizedLayout = layoutToken.trim()
    if (normalizedLayout.isBlank()) return colorTheme.uppercase()

    if (normalizedLayout.startsWith("SERVER:", ignoreCase = true)) {
        val key = normalizedLayout.removePrefix("SERVER:").substringBefore("|").trim()
        val remote = remoteLayouts.firstOrNull {
            it.layout_key.equals(key, ignoreCase = true)
        }
        val label = remote?.layout_name?.trim().orEmpty().ifBlank { key }
        return "${colorTheme.uppercase()}|SERVER:$key|$label"
    }

    return "${colorTheme.uppercase()}|${normalizedLayout.substringBefore("|").trim()}"
}
