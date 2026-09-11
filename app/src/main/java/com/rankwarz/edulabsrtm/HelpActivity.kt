package com.rankwarz.edulabsrtm

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.navigation.NavigationBarView

class HelpActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_contact_us)

        val emailTxt = findViewById<TextView>(R.id.txtEmail)
        val phoneTxt = findViewById<TextView>(R.id.txtPhone)

        emailTxt.setOnClickListener {
            val intent = Intent(Intent.ACTION_SENDTO).apply {
                data = Uri.parse("mailto:runescape007@ymail.com")
                putExtra(Intent.EXTRA_SUBJECT, "Query regarding EduLabs")
            }
            startActivity(Intent.createChooser(intent, "Send Email"))
        }

        phoneTxt.setOnClickListener {
            val intent = Intent(Intent.ACTION_DIAL).apply {
                data = Uri.parse("tel:7860245819")
            }
            startActivity(intent)
        }

        val bottomNav = BottomNavigationView(this)
        bottomNav.id = R.id.bottomNavigation
        bottomNav.fitsSystemWindows = true
        val params = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply { gravity = Gravity.BOTTOM; bottomMargin = 0 }
        val content = findViewById<FrameLayout>(android.R.id.content)
        content.addView(bottomNav, params)
        setupAppBottomNavigation(bottomNav, R.id.nav_messages)
    }
}
