package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.textfield.TextInputEditText
import com.yalantis.ucrop.UCrop
import java.io.File
import java.io.FileOutputStream

class WidgetSettingsActivity : AppCompatActivity() {

    private val prefs by lazy { getSharedPreferences("neet_widget", MODE_PRIVATE) }
    private lateinit var etName: TextInputEditText
    private lateinit var etDate: TextInputEditText
    private lateinit var rvGallery: RecyclerView

    private val galleryImages = listOf(
        R.drawable.bg_neet_pg, R.drawable.bg_neet_ug, R.drawable.bg_cat, 
        R.drawable.bg_law, R.drawable.bg_upsc, R.drawable.bg_bcbr
    )

    private val pickImageLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == RESULT_OK) {
            val sourceUri = result.data?.data ?: return@registerForActivityResult
            val destUri = Uri.fromFile(File(cacheDir, "cropped_widget.jpg"))
            startCrop(sourceUri, destUri)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_widget_settings_v2)

        etName = findViewById(R.id.etWidgetExamName)
        etDate = findViewById(R.id.etWidgetExamDate)
        rvGallery = findViewById(R.id.rvGallery)

        setupToolbar()
        loadSavedValues()
        setupGallery()

        findViewById<View>(R.id.btnSetCustomBg).setOnClickListener { pickImage() }
        findViewById<View>(R.id.btnSave).setOnClickListener { saveChanges() }
        findViewById<View>(R.id.btnReset).setOnClickListener { resetSettings() }
    }

    private fun setupToolbar() {
        val toolbar = findViewById<Toolbar>(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        toolbar.setNavigationOnClickListener { finish() }
    }

    private fun setupGallery() {
        rvGallery.layoutManager = GridLayoutManager(this, 3)
        rvGallery.adapter = GalleryAdapter(galleryImages) { resId ->
            saveResourceImage(resId)
        }
    }

    private fun loadSavedValues() {
        etName.setText(prefs.getString("selected_exam_name", "NEET PG"))
        etDate.setText(prefs.getString("selected_exam_date", "2026-06-15"))
    }

    private fun pickImage() {
        pickImageLauncher.launch(Intent(Intent.ACTION_PICK).apply { type = "image/*" })
    }

    private fun startCrop(source: Uri, destination: Uri) {
        UCrop.of(source, destination).withAspectRatio(4f, 2f).withMaxResultSize(1200, 600).start(this)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode == RESULT_OK && requestCode == UCrop.REQUEST_CROP) {
            UCrop.getOutput(data!!)?.let { saveFinalImage(it) }
        }
    }

    private fun saveFinalImage(uri: Uri) {
        try {
            val bitmap = BitmapFactory.decodeStream(contentResolver.openInputStream(uri))
            val file = File(filesDir, "widget_bg.jpg")
            FileOutputStream(file).use { bitmap.compress(Bitmap.CompressFormat.JPEG, 90, it) }
            prefs.edit().putString("local_background_path", file.absolutePath).apply()
            NeetAppWidget.forceUpdate(this)
            Toast.makeText(this, "Background updated!", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) { Toast.makeText(this, "Failed to save", Toast.LENGTH_SHORT).show() }
    }

    private fun saveResourceImage(resId: Int) {
        val bitmap = BitmapFactory.decodeResource(resources, resId)
        val file = File(filesDir, "widget_bg.jpg")
        FileOutputStream(file).use { bitmap.compress(Bitmap.CompressFormat.JPEG, 90, it) }
        prefs.edit().putString("local_background_path", file.absolutePath).apply()
        NeetAppWidget.forceUpdate(this)
        Toast.makeText(this, "Theme selected!", Toast.LENGTH_SHORT).show()
    }

    private fun saveChanges() {
        val name = etName.text.toString().trim()
        val date = etDate.text.toString().trim()
        if (name.isEmpty()) { Toast.makeText(this, "Enter name", Toast.LENGTH_SHORT).show(); return }
        prefs.edit().putString("selected_exam_name", name).putString("selected_exam_date", date).apply()
        NeetAppWidget.forceUpdate(this)
        Toast.makeText(this, "Settings saved!", Toast.LENGTH_SHORT).show()
    }

    private fun resetSettings() {
        prefs.edit().clear().apply()
        NeetAppWidget.forceUpdate(this)
        loadSavedValues()
        Toast.makeText(this, "Settings reset", Toast.LENGTH_SHORT).show()
    }

    inner class GalleryAdapter(private val images: List<Int>, private val onSelect: (Int) -> Unit) : RecyclerView.Adapter<GalleryAdapter.VH>() {
        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) = VH(LayoutInflater.from(parent.context).inflate(R.layout.item_gallery_thumb, parent, false))
        override fun onBindViewHolder(holder: VH, position: Int) {
            holder.img.setImageResource(images[position])
            holder.itemView.setOnClickListener { onSelect(images[position]) }
        }
        override fun getItemCount() = images.size
        inner class VH(v: View) : RecyclerView.ViewHolder(v) { val img: ImageView = v.findViewById(R.id.ivThumb) }
    }
}