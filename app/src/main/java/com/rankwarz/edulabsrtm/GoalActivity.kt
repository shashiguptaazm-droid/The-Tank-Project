package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.google.android.material.bottomnavigation.BottomNavigationView

class GoalActivity : AppCompatActivity() {

    private lateinit var prefs: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        applySavedTheme()

        // Check if a goal is already selected to avoid hindering the user
        val savedGoal = prefs.getString("selected_subject_preference", null)
        if (savedGoal != null && !intent.getBooleanExtra(EXTRA_CHANGE_GOAL, false)) {
            navigateToDashboard()
            return
        }

        setContentView(R.layout.activity_goal)

        if (intent.getBooleanExtra(EXTRA_CHANGE_GOAL, false)) {
            findViewById<TextView>(R.id.txtGoalTitle)?.text = "Change Your Goal Target"
        }

        setupCategoryCards()

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

    private fun applySavedTheme() {
        applySavedAppTheme(this)
    }

    private fun setupCategoryCards() {
        val lockedExams = setOf("UPSC", "CAT", "Commerce", "Law", "Computer Software", "BCBR")
        val unlockedExams = setOf("NEET PG", "NEET UG")

        val categories = mapOf(
            R.id.cardNeetPg to "NEET PG",
            R.id.cardNeetUg to "NEET UG",
            R.id.cardUpsc to "UPSC",
            R.id.cardCat to "CAT",
            R.id.cardCommerce to "Commerce",
            R.id.cardLaw to "Law",
            R.id.cardSoftware to "Computer Software",
            R.id.cardBcbr to "BCBR"
        )

        for ((id, examName) in categories) {
            val cardView = findViewById<View>(id)
            if (cardView == null) continue

            if (examName in lockedExams) {
                cardView.isClickable = false
                cardView.alpha = 0.5f
                cardView.setOnClickListener(null)
                addComingSoonOverlay(cardView, examName)
            } else if (examName in unlockedExams) {
                cardView.setOnClickListener { animateClick(cardView); saveGoalAndProceed(examName) }
            }
        }
    }

    private fun addComingSoonOverlay(parent: View, examName: String) {
        val overlay = TextView(this)
        overlay.text = "COMING SOON"
        overlay.setTextColor(Color.parseColor("#FF9800"))
        overlay.textSize = 12f
        overlay.typeface = Typeface.DEFAULT_BOLD
        overlay.gravity = Gravity.CENTER
        overlay.background = ContextCompat.getDrawable(this, R.drawable.bg_status_badge)
        val params = FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        ).apply { gravity = Gravity.CENTER }
        (parent as? ViewGroup)?.addView(overlay, params)
    }

    private fun saveGoalAndProceed(examName: String) {
        prefs.edit().putString("selected_subject_preference", examName).apply()
        Toast.makeText(this, "Target Exam Set: $examName", Toast.LENGTH_SHORT).show()
        navigateToDashboard()
    }

    private fun navigateToDashboard() {
        val intent = Intent(this, DashboardActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        startActivity(intent)
        finish()
    }

    companion object {
        const val EXTRA_CHANGE_GOAL = "extra_change_goal"
    }

    private fun animateClick(v: View) {
        v.animate()
            .scaleX(0.96f)
            .scaleY(0.96f)
            .setDuration(70)
            .withEndAction {
                v.animate().scaleX(1f).scaleY(1f).setDuration(70).start()
            }
            .start()
    }
}
