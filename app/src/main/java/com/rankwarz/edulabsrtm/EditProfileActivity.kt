package com.rankwarz.edulabsrtm

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.util.Base64
import android.util.Log
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.bumptech.glide.Glide
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import org.json.JSONObject
import java.io.ByteArrayOutputStream

class EditProfileActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "EDIT_PROFILE"
        private const val PREF_NAME = "MY_APP"
        private const val KEY_USER_ID = "user_id"
        private const val BASE_URL = "https://medigyaan.xyz/Neurons/"
        private const val PROFILE_API = "${BASE_URL}update_profile_api.php"
    }

    private lateinit var imgProfile: ImageView
    private lateinit var btnChangePhoto: MaterialButton
    private lateinit var btnSave: MaterialButton
    private lateinit var progress: ProgressBar
    private lateinit var etName: TextInputEditText
    private lateinit var etBio: TextInputEditText
    private lateinit var etCollege: TextInputEditText
    private lateinit var etState: TextInputEditText
    private lateinit var etCity: TextInputEditText
    private lateinit var etBatchYear: TextInputEditText
    private lateinit var etPassingYear: TextInputEditText
    private lateinit var etMobile: TextInputEditText
    private lateinit var etAddress: TextInputEditText

    private var userId = 0
    private var selectedPhotoBase64: String? = null

    private val imagePicker = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            handleSelectedPhoto(uri)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_edit_profile)

        userId = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE).getInt(KEY_USER_ID, 0)
        if (userId <= 0) {
            Toast.makeText(this, "Please login again", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        initViews()
        loadProfile()
    }

    private fun initViews() {
        findViewById<Toolbar>(R.id.toolbar).setNavigationOnClickListener { finish() }

        imgProfile = findViewById(R.id.imgEditProfile)
        btnChangePhoto = findViewById(R.id.btnChangePhoto)
        btnSave = findViewById(R.id.btnSaveProfile)
        progress = findViewById(R.id.profileSaveProgress)
        etName = findViewById(R.id.etName)
        etBio = findViewById(R.id.etBio)
        etCollege = findViewById(R.id.autoCollege)
        etState = findViewById(R.id.etState)
        etCity = findViewById(R.id.etCity)
        etBatchYear = findViewById(R.id.etBatchYear)
        etPassingYear = findViewById(R.id.etPassingYear)
        etMobile = findViewById(R.id.etMobile)
        etAddress = findViewById(R.id.etAddress)

        btnChangePhoto.setOnClickListener {
            imagePicker.launch("image/*")
        }

        btnSave.setOnClickListener {
            saveProfile()
        }

        val bottomNav = BottomNavigationView(this)
        bottomNav.id = R.id.bottomNavigation
        bottomNav.fitsSystemWindows = true
        bottomNav.clipToPadding = false
        val params = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply { gravity = Gravity.BOTTOM }
        val content = findViewById<FrameLayout>(android.R.id.content)
        content.addView(bottomNav, params)
        setupAppBottomNavigation(bottomNav, R.id.nav_home)
    }

    private fun loadProfile() {
        setLoading(true)
        val url = "$PROFILE_API?user_id=$userId&viewer_id=$userId"
        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                setLoading(false)
                try {
                    val root = JSONObject(response)
                    if (root.optString("status") != "success") {
                        Toast.makeText(this, root.optString("message", "Profile load failed"), Toast.LENGTH_SHORT).show()
                        return@StringRequest
                    }
                    bindProfile(root.optJSONObject("data") ?: JSONObject())
                } catch (e: Exception) {
                    Log.e(TAG, "Profile parse error", e)
                    Toast.makeText(this, "Could not read profile", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                setLoading(false)
                Log.e(TAG, "Profile load failed", error)
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
            }
        )
        Volley.newRequestQueue(this).add(request)
    }

    private fun bindProfile(json: JSONObject) {
        etName.setText(json.optString("name"))
        etBio.setText(json.optString("bio"))
        etCollege.setText(json.optString("college_name"))
        etState.setText(json.optString("state"))
        etCity.setText(json.optString("city"))
        etBatchYear.setText(json.optInt("batch_year", 0).takeIf { it > 0 }?.toString().orEmpty())
        etPassingYear.setText(json.optInt("passing_year", 0).takeIf { it > 0 }?.toString().orEmpty())
        etMobile.setText(json.optString("mobile_no"))
        etAddress.setText(json.optString("address"))

        val photo = json.optString("photo")
        if (photo.isNotBlank() && photo != "null") {
            val imageUrl = if (photo.startsWith("http")) photo else BASE_URL + photo.removePrefix("./").trimStart('/')
            Glide.with(this)
                .load(imageUrl)
                .circleCrop()
                .placeholder(R.drawable.ic_user_placeholder)
                .into(imgProfile)
        }
    }

    private fun handleSelectedPhoto(uri: Uri) {
        try {
            val bitmap = contentResolver.openInputStream(uri).use { stream ->
                BitmapFactory.decodeStream(stream)
            }
            if (bitmap == null) {
                Toast.makeText(this, "Could not read image", Toast.LENGTH_SHORT).show()
                return
            }

            val scaled = scaleBitmap(bitmap, 900)
            val output = ByteArrayOutputStream()
            scaled.compress(Bitmap.CompressFormat.JPEG, 84, output)
            selectedPhotoBase64 = Base64.encodeToString(output.toByteArray(), Base64.NO_WRAP)

            imgProfile.setImageBitmap(scaled)
            Toast.makeText(this, "Photo selected", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Log.e(TAG, "Image selection failed", e)
            Toast.makeText(this, "Could not prepare image", Toast.LENGTH_SHORT).show()
        }
    }

    private fun scaleBitmap(source: Bitmap, maxSide: Int): Bitmap {
        val width = source.width
        val height = source.height
        val largest = maxOf(width, height)
        if (largest <= maxSide) return source

        val scale = maxSide.toFloat() / largest.toFloat()
        val targetWidth = (width * scale).toInt().coerceAtLeast(1)
        val targetHeight = (height * scale).toInt().coerceAtLeast(1)
        return Bitmap.createScaledBitmap(source, targetWidth, targetHeight, true)
    }

    private fun saveProfile() {
        val name = etName.text?.toString()?.trim().orEmpty()
        if (name.length < 2) {
            etName.error = "Required"
            etName.requestFocus()
            return
        }

        setLoading(true)
        val request = object : StringRequest(
            Request.Method.POST,
            PROFILE_API,
            { response ->
                setLoading(false)
                try {
                    val root = JSONObject(response)
                    if (root.optString("status") == "success") {
                        Toast.makeText(this, "Profile updated", Toast.LENGTH_SHORT).show()
                        setResult(RESULT_OK)
                        finish()
                    } else {
                        Toast.makeText(this, root.optString("message", "Update failed"), Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Save parse error", e)
                    Toast.makeText(this, "Could not read save response", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                setLoading(false)
                Log.e(TAG, "Profile save failed", error)
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                val params = hashMapOf(
                    "user_id" to userId.toString(),
                    "name" to name,
                    "bio" to etBio.textValue(),
                    "college_name" to etCollege.textValue(),
                    "state" to etState.textValue(),
                    "city" to etCity.textValue(),
                    "batch_year" to etBatchYear.textValue(),
                    "passing_year" to etPassingYear.textValue(),
                    "mobile_no" to etMobile.textValue(),
                    "address" to etAddress.textValue()
                )
                selectedPhotoBase64?.let { params["photo_base64"] = it }
                return params
            }
        }

        Volley.newRequestQueue(this).add(request)
    }

    private fun setLoading(isLoading: Boolean) {
        progress.visibility = if (isLoading) View.VISIBLE else View.GONE
        btnSave.isEnabled = !isLoading
        btnChangePhoto.isEnabled = !isLoading
    }

    private fun TextInputEditText.textValue(): String {
        return text?.toString()?.trim().orEmpty()
    }
}
