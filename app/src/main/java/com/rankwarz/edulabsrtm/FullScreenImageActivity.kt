package com.rankwarz.edulabsrtm

import android.content.ContentValues
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.drawable.Drawable
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import com.bumptech.glide.Glide
import com.bumptech.glide.request.target.CustomTarget
import com.bumptech.glide.request.transition.Transition
import java.io.File
import java.io.FileOutputStream
import java.io.OutputStream

class FullScreenImageActivity : AppCompatActivity() {

    private lateinit var imageView: ImageView
    private var imageUrl: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_full_screen_image)

        // Initialize Views
        imageView = findViewById(R.id.fullImageView)
        val btnDownload: ImageButton = findViewById(R.id.btnDownload)
        val btnShare: ImageButton = findViewById(R.id.btnShare)

        // Get URL from Intent
        imageUrl = intent.getStringExtra("image_url")

        // Load the image with Glide
        Glide.with(this)
            .load(imageUrl)
            .placeholder(R.drawable.ic_image_placeholder)
            .into(imageView)

        // Close on image click (WhatsApp style)
        imageView.setOnClickListener { finish() }

        btnDownload.setOnClickListener { downloadImage() }
        btnShare.setOnClickListener { shareImage() }
    }

    private fun downloadImage() {
        if (imageUrl.isNullOrEmpty()) return

        Toast.makeText(this, "Downloading...", Toast.LENGTH_SHORT).show()

        Glide.with(this)
            .asBitmap()
            .load(imageUrl)
            .into(object : CustomTarget<Bitmap>() {
                override fun onResourceReady(resource: Bitmap, transition: Transition<in Bitmap>?) {
                    saveBitmapToDisk(resource)
                }
                override fun onLoadCleared(placeholder: Drawable?) {}
                override fun onLoadFailed(errorDrawable: Drawable?) {
                    Toast.makeText(this@FullScreenImageActivity, "Download failed", Toast.LENGTH_SHORT).show()
                }
            })
    }

    private fun saveBitmapToDisk(bitmap: Bitmap) {
        val filename = "EduLabs_${System.currentTimeMillis()}.jpg"
        var fos: OutputStream? = null

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val resolver = contentResolver
                val contentValues = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                    put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
                    put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/EduLabs")
                }
                // FIXED: Corrected reference for MediaStore URI
                val imageUri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
                fos = imageUri?.let { resolver.openOutputStream(it) }
            } else {
                @Suppress("DEPRECATION")
                val imagesDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES)
                val appDir = File(imagesDir, "EduLabs")
                if (!appDir.exists()) appDir.mkdirs()
                val image = File(appDir, filename)
                fos = FileOutputStream(image)
            }

            fos?.use {
                bitmap.compress(Bitmap.CompressFormat.JPEG, 100, it)
                Toast.makeText(this, "Image saved to Pictures/EduLabs", Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(this, "Save error: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun shareImage() {
        if (imageUrl.isNullOrEmpty()) return

        Glide.with(this)
            .asBitmap()
            .load(imageUrl)
            .into(object : CustomTarget<Bitmap>() {
                override fun onResourceReady(resource: Bitmap, transition: Transition<in Bitmap>?) {
                    shareBitmap(resource)
                }
                override fun onLoadCleared(placeholder: Drawable?) {}
            })
    }

    private fun shareBitmap(bitmap: Bitmap) {
        try {
            // Save to internal cache for sharing
            val cachePath = File(cacheDir, "shared_images")
            cachePath.mkdirs()
            val file = File(cachePath, "temp_share_image.png")
            val stream = FileOutputStream(file)
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
            stream.close()

            // Get URI using the FileProvider defined in Manifest
            val contentUri = FileProvider.getUriForFile(
                this,
                "com.corp.edulabsrtm.fileprovider",
                file
            )

            if (contentUri != null) {
                val shareIntent = Intent().apply {
                    action = Intent.ACTION_SEND
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    setDataAndType(contentUri, contentResolver.getType(contentUri))
                    putExtra(Intent.EXTRA_STREAM, contentUri)
                }
                startActivity(Intent.createChooser(shareIntent, "Share Image"))
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(this, "Share failed", Toast.LENGTH_SHORT).show()
        }
    }
}