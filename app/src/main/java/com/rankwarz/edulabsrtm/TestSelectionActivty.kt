package com.rankwarz.edulabsrtm
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.*
import androidx.appcompat.app.AlertDialog
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.android.material.bottomnavigation.BottomNavigationView
import org.json.JSONObject

class TestSelectionActivity : BaseActivity() {

    private lateinit var subjectLayout: LinearLayout
    private lateinit var testGrid: GridView
    private lateinit var headerTitle: TextView

    private var quizType: String = "NEET_PG"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_test_selection)

        initViews()
        setupCategoryClicks()
        setupBottomNavigation()
    }

    private fun initViews() {
        subjectLayout = findViewById(R.id.subjectLayout)
        testGrid = findViewById(R.id.testSeriesGrid)
        headerTitle = findViewById(R.id.headerTitle)
    }

    // 🔥 CATEGORY CLICK HANDLING
    private fun setupCategoryClicks() {

        val categories = mapOf(
            R.id.cardNeetPg to Triple("NEET PG", 1, "NEET_PG"),
            R.id.cardNeetUg to Triple("NEET UG", 100, "NEET_UG")
        )

        for ((viewId, data) in categories) {
            findViewById<View>(viewId)?.setOnClickListener {
                quizType = data.third
                loadTestGrid(data.first, data.second)
            }
        }
    }

    // 🔥 LOAD GRID
    private fun loadTestGrid(subject: String, startId: Int) {

        headerTitle.text = subject

        subjectLayout.visibility = View.GONE
        testGrid.visibility = View.VISIBLE

        Toast.makeText(this, "Loading tests...", Toast.LENGTH_SHORT).show()

        val testNames = List(50) { i -> "$subject Mock Test ${i + 1}" }

        testGrid.adapter = TestGridAdapter(this, testNames, startId)

        testGrid.onItemClickListener =
            AdapterView.OnItemClickListener { _, _, position, _ ->
                val finalUniqueId = startId + position
                showModeDialog(subject, finalUniqueId)
            }
    }

    // 🔥 MODE DIALOG
    private fun showModeDialog(subject: String, uniqueId: Int) {

        val options = arrayOf("Practice Solo", "Challenge Friend")

        AlertDialog.Builder(this)
            .setTitle("$subject • Test $uniqueId")
            .setItems(options) { _, which ->
                when (which) {
                    0 -> openSoloMode(subject, uniqueId)
                    1 -> openChallengeMode(subject, uniqueId)
                }
            }
            .show()
    }

    private fun openSoloMode(subject: String, uniqueId: Int) {
        val intent = Intent(this, SinglePlayerTestModeActivity::class.java).apply {
            putExtra("UNIQUE_ID", uniqueId)
            putExtra("SELECTED_SUBJECT", subject)
            putExtra("QUIZ_TYPE", quizType)
        }
        startActivity(intent)
    }
    private fun setupBottomNavigation() {
        val bottomNav: BottomNavigationView = findViewById(R.id.bottomNavigation)
        setupAppBottomNavigation(bottomNav, R.id.nav_home)
    }
    private fun openChallengeMode(subject: String, uniqueId: Int) {
        val intent = Intent(this, TopicChallengeSelectionActivity::class.java).apply {
            putExtra("UNIQUE_ID", uniqueId)
            putExtra("QUIZ_TYPE", "TEST_SERIES")
            putExtra("SELECTED_SUBJECT", subject)
            putExtra("SUBJECT", subject)
        }
        startActivity(intent)
    }

    // 🔙 BACK HANDLING
    private fun handleBack() {
        if (testGrid.visibility == View.VISIBLE) {
            testGrid.visibility = View.GONE
            subjectLayout.visibility = View.VISIBLE
            headerTitle.text = "Select Category"
        } else {
            finish()
        }
    }

    override fun onBackPressed() {
        handleBack()
    }
}
