package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.yalantis.ucrop.UCrop
import java.io.File
import java.io.FileOutputStream
import java.util.Locale

class WidgetSettingsActivity : AppCompatActivity() {

    private val prefs by lazy {
        getSharedPreferences("neet_widget", Context.MODE_PRIVATE)
    }

    private lateinit var etExamName: EditText
    private lateinit var etExamDate: EditText

    private lateinit var tempSourceUri: Uri
    private lateinit var tempDestUri: Uri

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_widget_settings)

        etExamName = findViewById(R.id.etWidgetExamName)
        etExamDate = findViewById(R.id.etWidgetExamDate)

        loadSavedValues()

        findViewById<Button>(R.id.btnSetWidgetBackground).setOnClickListener {
            pickImage()
        }

        findViewById<Button>(R.id.btnSaveWidgetExam).setOnClickListener {
            saveExamDetails()
        }

        findViewById<Button>(R.id.btnResetWidget).setOnClickListener {
            resetWidgetSettings()
        }

        findViewById<Button>(R.id.btnBack).setOnClickListener {
            finish()
        }
    }

    private fun loadSavedValues() {
        etExamName.setText(prefs.getString("selected_exam_name", "NEET PG"))
        etExamDate.setText(prefs.getString("selected_exam_date", "2026-06-15"))
    }

    // 🔥 STEP 1: PICK IMAGE
    private fun pickImage() {
        val intent = android.content.Intent(Intent.ACTION_PICK)
        intent.type = "image/*"
        startActivityForResult(intent, 101)
    }

    // 🔥 STEP 2: HANDLE PICK + START CROP
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (resultCode != RESULT_OK) return

        if (requestCode == 101) {
            val sourceUri = data?.data ?: return

            val destFile = File(cacheDir, "cropped_widget.jpg")
            val destUri = Uri.fromFile(destFile)

            tempSourceUri = sourceUri
            tempDestUri = destUri

            startCrop(sourceUri, destUri)
        } else if (requestCode == UCrop.REQUEST_CROP) {
            val resultUri = UCrop.getOutput(data!!) ?: return
            saveFinalImage(resultUri)
        } else if (requestCode == UCrop.RESULT_ERROR) {
            Toast.makeText(this, "Crop failed", Toast.LENGTH_SHORT).show()
        }
    }

    // 🔥 STEP 3: UCROP CONFIG
    private fun startCrop(source: Uri, destination: Uri) {
        UCrop.of(source, destination)
            .withAspectRatio(4f, 2f) // 🔥 widget shape (adjust if needed)
            .withMaxResultSize(1200, 600)
            .start(this)
    }

    // 🔥 STEP 4: SAVE FINAL IMAGE
    private fun saveFinalImage(uri: Uri) {
        try {
            val input = contentResolver.openInputStream(uri)
            val bitmap = BitmapFactory.decodeStream(input)

            val file = File(filesDir, "widget_bg.jpg")

            FileOutputStream(file).use {
                bitmap.compress(Bitmap.CompressFormat.JPEG, 90, it)
            }

            prefs.edit()
                .putString("local_background_path", file.absolutePath)
                .apply()

            NeetAppWidget.forceUpdate(this)

            Toast.makeText(this, "Background updated", Toast.LENGTH_SHORT).show()

        } catch (e: Exception) {
            Toast.makeText(this, "Failed to save image", Toast.LENGTH_SHORT).show()
        }
    }

    private fun saveExamDetails() {
        val examName = etExamName.text.toString().trim()
        val examDate = etExamDate.text.toString().trim()

        if (examName.isEmpty()) {
            Toast.makeText(this, "Enter exam name", Toast.LENGTH_SHORT).show()
            return
        }

        prefs.edit()
            .putString("selected_exam_name", examName)
            .putString("selected_exam_date", examDate)
            .apply()

        NeetAppWidget.forceUpdate(this)
        Toast.makeText(this, "Widget updated", Toast.LENGTH_SHORT).show()
    }

    private fun resetWidgetSettings() {
        prefs.edit()
            .remove("local_background_path")
            .remove("selected_exam_name")
            .remove("selected_exam_date")
            .apply()

        NeetAppWidget.forceUpdate(this)
        Toast.makeText(this, "Widget reset", Toast.LENGTH_SHORT).show()
    }
}