package com.rankwarz.edulabsrtm

import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import android.view.View
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.appcompat.widget.SwitchCompat
import androidx.appcompat.widget.Toolbar
import com.bumptech.glide.Glide
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.card.MaterialCardView
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.FirebaseDatabase

class SettingsActivity : AppCompatActivity() {

    private lateinit var prefs: SharedPreferences
    private lateinit var editor: SharedPreferences.Editor
    private var userId: Int = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings_v2)

        prefs = getSharedPreferences("MY_APP", MODE_PRIVATE)
        editor = prefs.edit()
        userId = prefs.getInt("user_id", 0)

        setupToolbar()
        setupProfileHeader()
        setupEarnSection()
        setupPreferencesSection()
        setupAccountSection()
        setupSupportSection()
        setupBottomNavigation()
    }

    private fun setupToolbar() {
        val toolbar = findViewById<Toolbar>(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        toolbar.setNavigationOnClickListener { finish() }
    }

    private fun setupProfileHeader() {
        val name = prefs.getString("name", "User")
        val photo = prefs.getString("photo_url", "")

        findViewById<TextView>(R.id.txtName).text = name
        val ivProfile = findViewById<ImageView>(R.id.ivProfileImage)

        if (!photo.isNullOrEmpty()) {
            val fullUrl = if (photo.startsWith("http")) photo else "https://medigyaan.xyz/Neurons/" + photo.trimStart('/')
            Glide.with(this).load(fullUrl).circleCrop().placeholder(R.drawable.ic_person).into(ivProfile)
        }

        findViewById<View>(R.id.layoutProfile).setOnClickListener {
            startActivity(Intent(this, ProfileActivity::class.java).apply { putExtra("USER_ID", userId) })
        }
    }

    private fun setupEarnSection() {
        findViewById<MaterialCardView>(R.id.itemReferral).setOnClickListener {
            startActivity(Intent(this, ReferralActivity::class.java))
        }
        findViewById<MaterialCardView>(R.id.itemDailyReward).setOnClickListener {
            claimDailyReward()
        }
        findViewById<MaterialCardView>(R.id.itemWatchAds).setOnClickListener {
            Toast.makeText(this, "Coming soon!", Toast.LENGTH_SHORT).show()
        }
    }

    private fun setupPreferencesSection() {
        val darkModeEnabled = prefs.getBoolean("dark_mode", false)
        setupSwitchRow(R.id.itemDarkMode, R.drawable.ic_dark_mode, "Dark Mode", "Adjust appearance", darkModeEnabled) { isChecked ->
            applyDarkMode(isChecked)
            editor.putBoolean("dark_mode", isChecked).apply()
        }

        val notificationsEnabled = prefs.getBoolean("notifications_enabled", true)
        setupSwitchRow(R.id.itemNotifications, R.drawable.ic_notifications, "Notifications", "Message, group & call tones", notificationsEnabled) { isChecked ->
            editor.putBoolean("notifications_enabled", isChecked).apply()
            updateNotificationSettings(isChecked)
        }

        val dataSaver = prefs.getBoolean("data_saver", false)
        setupSwitchRow(R.id.itemDataSaver, R.drawable.ic_data_saver, "Data Saver", "Reduce data usage", dataSaver) { isChecked ->
            editor.putBoolean("data_saver", isChecked).apply()
        }
    }

    private fun setupAccountSection() {
        findViewById<MaterialCardView>(R.id.itemEditProfile).setOnClickListener {
            startActivity(Intent(this, EditProfileActivity::class.java))
        }
        findViewById<MaterialCardView>(R.id.itemWidgetSettings).setOnClickListener {
            startActivity(Intent(this, WidgetSettingsActivity::class.java))
        }
        findViewById<MaterialCardView>(R.id.itemPrivacy).setOnClickListener {
            val intent = Intent(this, WebViewActivity::class.java).apply {
                putExtra("url", "https://medigyaan.xyz/privacy-policy")
                putExtra("title", "Privacy Policy")
            }
            startActivity(intent)
        }
    }

    private fun setupSupportSection() {
        findViewById<MaterialCardView>(R.id.itemHelp).setOnClickListener {
            startActivity(Intent(this, HelpActivity::class.java))
        }
        findViewById<MaterialCardView>(R.id.itemAbout).setOnClickListener {
            showAboutDialog()
        }
    }

    private fun setupSwitchRow(rowId: Int, iconRes: Int, title: String, desc: String, initialSwitchState: Boolean, onClick: (Boolean) -> Unit) {
        val row = findViewById<View>(rowId)
        row.findViewById<TextView>(R.id.txtTitle).text = title
        row.findViewById<TextView>(R.id.txtDescription).text = desc
        row.findViewById<ImageView>(R.id.ivIcon).setImageResource(iconRes)

        val sw = row.findViewById<SwitchCompat>(R.id.switchAction)
        sw.visibility = View.VISIBLE
        sw.isChecked = initialSwitchState
        sw.setOnCheckedChangeListener { _, isChecked -> onClick(isChecked) }
        row.setOnClickListener { sw.toggle() }
    }

    private fun applyDarkMode(enabled: Boolean) {
        AppCompatDelegate.setDefaultNightMode(if (enabled) AppCompatDelegate.MODE_NIGHT_YES else AppCompatDelegate.MODE_NIGHT_NO)
        recreate()
    }

    private fun updateNotificationSettings(enabled: Boolean) {
        FirebaseDatabase.getInstance().reference.child("users").child(userId.toString()).child("notifications").setValue(enabled)
    }

    private fun claimDailyReward() {
        val lastClaim = prefs.getLong("last_daily_claim", 0)
        val now = System.currentTimeMillis()
        if (now - lastClaim < 24 * 60 * 60 * 1000L) {
            Toast.makeText(this, "Daily reward already claimed!", Toast.LENGTH_SHORT).show()
            return
        }
        val reward = (50..150).random()
        val currentCoins = prefs.getInt("user_coins", 0)
        editor.putInt("user_coins", currentCoins + reward).putLong("last_daily_claim", now).apply()
        Toast.makeText(this, "🎉 Claimed $reward coins!", Toast.LENGTH_LONG).show()
    }

    private fun showAboutDialog() {
        AlertDialog.Builder(this).setTitle("About MediGyaan").setMessage("MediGyaan - Medical Education Platform\nVersion 1.0.0\n\n© 2024 MediGyaan. All rights reserved.").setPositiveButton("OK", null).show()
    }

    private fun confirmLogout() {
        AlertDialog.Builder(this).setTitle("Logout").setMessage("Are you sure?").setPositiveButton("Logout") { _, _ ->
            FirebaseAuth.getInstance().signOut()
            editor.clear().apply()
            startActivity(Intent(this, LoginActivity::class.java).apply { flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK })
            finish()
        }.setNegativeButton("Cancel", null).show()
    }

    private fun setupBottomNavigation() {
        setupAppBottomNavigation(findViewById(R.id.bottomNavigation), R.id.nav_home)
    }
}