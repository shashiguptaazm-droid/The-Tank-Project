package com.rankwarz.edulabsrtm.util

import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.util.Log
import android.widget.Toast

object DownloadHelper {
    private const val TAG = "DownloadHelper"

    fun downloadFile(context: Context, fileUrl: String, suggestedName: String? = null) {
        if (fileUrl.isBlank()) {
            Toast.makeText(context, "Cannot download: empty URL", Toast.LENGTH_SHORT).show()
            return
        }

        try {
            val resolvedUrl = if (fileUrl.startsWith("http")) fileUrl else "https://medigyaan.xyz/Neurons/" + fileUrl.removePrefix("/")
            val uri = Uri.parse(resolvedUrl)
            
            val fileName = when {
                !suggestedName.isNullOrBlank() -> suggestedName
                uri.lastPathSegment != null -> uri.lastPathSegment!!
                else -> "download_${System.currentTimeMillis()}"
            }

            // Clean filename
            val safeFileName = fileName.replace(Regex("[^a-zA-Z0-9._-]"), "_")

            val request = DownloadManager.Request(uri).apply {
                setTitle(safeFileName)
                setDescription("Downloading file from MediGyaan")
                setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, safeFileName)
                setAllowedOverMetered(true)
                setAllowedOverRoaming(true)
            }

            val manager = context.getSystemService(Context.DOWNLOAD_SERVICE) as? DownloadManager
            if (manager != null) {
                manager.enqueue(request)
                Toast.makeText(context, "Downloading $safeFileName...", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(context, "Download manager not available", Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error initiating download: ${e.message}", e)
            Toast.makeText(context, "Download failed: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }
}
