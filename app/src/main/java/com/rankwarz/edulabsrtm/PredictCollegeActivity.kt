package com.rankwarz.edulabsrtm

import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.InputType
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.cardview.widget.CardView
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.navigation.NavigationBarView
import androidx.core.content.ContextCompat
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.roundToInt

class PredictCollegeActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var prefs: SharedPreferences
    private lateinit var progressBar: ProgressBar
    private lateinit var filterContainer: LinearLayout
    private lateinit var layoutEmptyState: LinearLayout
    private lateinit var btnAiChat: Button

    private lateinit var txtPredictedRank: TextView
    private lateinit var txtTier: TextView
    private lateinit var txtTotalResults: TextView
    private lateinit var txtAiSummary: TextView
    private lateinit var txtSafeCount: TextView
    private lateinit var txtTargetCount: TextView
    private lateinit var txtDreamCount: TextView

    private val feedList = mutableListOf<FeedItem>()
    private val masterColleges = mutableListOf<CollegeModel>()

    private val API_URL = "https://medigyaan.xyz/Neurons/predictor_app.php"
    private val PREDICT_RANK_URL = "https://medigyaan.xyz/Neurons/predict_rank.php"
    private var userId: Int = 0

    private var selectedRank = "50000"
    private var originalRank = "50000"
    private var selectedTier = "📘 Average"
    private var selectedCategory = "GEN"
    private var selectedQuota = "All India"
    private var selectedYear = "all"
    private var selectedSubject = ""

    private var selectedState = ""
    private var selectedCollegeType = ""
    private var selectedMaxFee = ""
    private var selectedMaxBond = ""
    private var selectedMinStipend = ""
    private var selectedAiPreference = ""

    private var distinctSubjects: List<String> = emptyList()
    private var distinctStates: List<String> = emptyList()
    private var distinctCategories: List<String> = emptyList()
    private var distinctQuotas: List<String> = emptyList()
    private var distinctCollegeTypes: List<String> = listOf("Government", "Private")

    private lateinit var btnCustomRank: TextView
    private lateinit var btnSubjectFilter: TextView
    private lateinit var btnStateFilter: TextView
    private lateinit var btnCategoryFilter: TextView
    private lateinit var btnQuotaFilter: TextView
    private lateinit var btnCollegeTypeFilter: TextView
    private lateinit var btnFeeFilter: TextView
    private lateinit var btnBondFilter: TextView
    private lateinit var btnStipendFilter: TextView
    private lateinit var btnAiFilter: TextView
    private lateinit var btnResetFilter: TextView

    private lateinit var rankRow: LinearLayout
    private lateinit var row1: LinearLayout
    private lateinit var row2: LinearLayout
    private lateinit var row3: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_predict_college)

        recyclerView = findViewById(R.id.recyclerColleges)
        progressBar = findViewById(R.id.progressBar)
        filterContainer = findViewById(R.id.filterContainer)
        layoutEmptyState = findViewById(R.id.layoutEmptyState)
        btnAiChat = findViewById(R.id.btnAiChat)

        txtPredictedRank = findViewById(R.id.txtPredictedRank)
        txtTier = findViewById(R.id.txtTier)
        txtTotalResults = findViewById(R.id.txtTotalResults)
        txtAiSummary = findViewById(R.id.txtAiSummary)
        txtSafeCount = findViewById(R.id.txtSafeCount)
        txtTargetCount = findViewById(R.id.txtTargetCount)
        txtDreamCount = findViewById(R.id.txtDreamCount)

        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.setHasFixedSize(false)

        prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        userId = prefs.getInt("user_id", 0)
        val accuracy = prefs.getInt("accuracy", 0)
        val streak = prefs.getInt("streak", 0)
        val attempted = prefs.getInt("attempted", 0)
        val correct = prefs.getInt("correct", 0)

        val rankFromIntent = getRankFromIntentOrNull()
        val rankFromPrefs = prefs.getString("predicted_rank", null)
            ?: prefs.getInt("predicted_rank", -1).let { if (it == -1) null else it.toString() }
            ?: prefs.getString("rank", null)
            ?: prefs.getInt("rank", -1).let { if (it == -1) null else it.toString() }

        val finalRawRank = rankFromIntent ?: rankFromPrefs ?: "50000"
        selectedRank = cleanRankString(finalRawRank)
        originalRank = selectedRank

        selectedTier = intent.getStringExtra("TIER") ?: "📘 Average"
        selectedCategory = intent.getStringExtra("CATEGORY")?.trim().orEmpty().ifBlank { "GEN" }
        selectedQuota = intent.getStringExtra("QUOTA")?.trim().orEmpty().ifBlank { "All India" }
        selectedYear = intent.getStringExtra("YEAR")?.trim().orEmpty().ifBlank { "all" }
        selectedSubject = intent.getStringExtra("SUBJECT")?.trim().orEmpty()

        txtPredictedRank.text = "🎯 Expected Rank : $selectedRank"
        txtTier.text = "Tier : $selectedTier"
        txtAiSummary.text = "Loading AI counseling..."
        txtTotalResults.text = "Available Colleges : 0"
        txtSafeCount.text = "SAFE : 0"
        txtTargetCount.text = "TARGET : 0"
        txtDreamCount.text = "DREAM : 0"

        btnAiChat.setOnClickListener {
            val intent = Intent(this, AiChatActivity::class.java)
            startActivity(intent)
        }

        val btnToggle = findViewById<Button>(R.id.btnToggleSummary)
        val cardSummary = findViewById<CardView>(R.id.cardSummary)
        val cardFilters = findViewById<CardView>(R.id.cardFilters)
        var summaryVisible = true

        btnToggle.setOnClickListener {
            summaryVisible = !summaryVisible
            if (summaryVisible) {
                cardSummary.visibility = View.VISIBLE
                cardFilters.visibility = View.VISIBLE
                btnToggle.text = "🔽 Hide Summary"
            } else {
                cardSummary.visibility = View.GONE
                cardFilters.visibility = View.GONE
                btnToggle.text = "🔼 Show Summary"
            }
        }

        btnCustomRank = createChip("Rank: $selectedRank") {
            showCustomRankDialog()
        }
        btnSubjectFilter = createChip("Subject: ${selectedSubject.ifBlank { "Any" }}") {
            val items = if (distinctSubjects.isNotEmpty()) {
                listOf("All") + distinctSubjects
            } else {
                listOf(
                    "All",
                    "Anatomy",
                    "Physiology",
                    "Biochemistry",
                    "Pharmacology",
                    "Pathology",
                    "Microbiology",
                    "Forensic Medicine",
                    "Community Medicine",
                    "General Medicine",
                    "Paediatrics",
                    "Dermatology",
                    "Psychiatry",
                    "Respiratory Medicine",
                    "Radiology",
                    "Anaesthesiology",
                    "General Surgery",
                    "Orthopaedics",
                    "ENT",
                    "Ophthalmology",
                    "Obstetrics & Gynaecology"
                )
            }

            showChoiceDialog(
                "Select Subject",
                items,
                selectedSubject.ifBlank { "All" }
            ) {
                selectedSubject = if (it == "All") "" else it
                updateFilterButtonText()
                applyLocalFiltersAndRender()
            }
        }

        btnStateFilter = createChip("State: Any") {
            showChoiceDialog(
                "Select State",
                listOf("All") + distinctStates,
                selectedState.ifBlank { "All" }
            ) {
                selectedState = if (it == "All") "" else it
                updateFilterButtonText()
                applyLocalFiltersAndRender()
            }
        }

        btnCategoryFilter = createChip("Category: $selectedCategory") {
            val items = if (distinctCategories.isNotEmpty()) {
                listOf("All") + distinctCategories
            } else {
                listOf("All", "GEN", "OBC", "SC", "ST", "EWS")
            }

            showChoiceDialog(
                "Select Category",
                items,
                selectedCategory.ifBlank { "All" }
            ) {
                selectedCategory = if (it == "All") "" else it
                updateFilterButtonText()
                applyLocalFiltersAndRender()
            }
        }

        btnQuotaFilter = createChip("Quota: $selectedQuota") {
            val items = if (distinctQuotas.isNotEmpty()) {
                listOf("All") + distinctQuotas
            } else {
                listOf("All", "All India", "State", "AIQ", "NRI", "Management")
            }

            showChoiceDialog(
                "Select Quota",
                items,
                selectedQuota.ifBlank { "All" }
            ) {
                selectedQuota = if (it == "All") "" else it
                updateFilterButtonText()
                applyLocalFiltersAndRender()
            }
        }

        btnCollegeTypeFilter = createChip("Type: Any") {
            val items = listOf("All") + distinctCollegeTypes
            showChoiceDialog(
                "Select College Type",
                items,
                selectedCollegeTypeDisplay()
            ) {
                selectedCollegeType = when (it) {
                    "Government" -> "government"
                    "Private" -> "private"
                    else -> ""
                }
                updateFilterButtonText()
                applyLocalFiltersAndRender()
            }
        }

        btnFeeFilter = createChip("Fee: Any") {
            val items =
                listOf("All", "<= 100000", "<= 200000", "<= 300000", "<= 500000", "<= 1000000")
            showChoiceDialog("Select Max Fee / Year", items, selectedMaxFeeLabel()) {
                selectedMaxFee = when (it) {
                    "<= 100000" -> "100000"
                    "<= 200000" -> "200000"
                    "<= 300000" -> "300000"
                    "<= 500000" -> "500000"
                    "<= 1000000" -> "1000000"
                    else -> ""
                }
                updateFilterButtonText()
                applyLocalFiltersAndRender()
            }
        }

        btnBondFilter = createChip("Bond: Any") {
            val items = listOf("All", "<= 1", "<= 2", "<= 3", "<= 5")
            showChoiceDialog("Select Max Bond", items, selectedMaxBondLabel()) {
                selectedMaxBond = when (it) {
                    "<= 1" -> "1"
                    "<= 2" -> "2"
                    "<= 3" -> "3"
                    "<= 5" -> "5"
                    else -> ""
                }
                updateFilterButtonText()
                applyLocalFiltersAndRender()
            }
        }

        btnStipendFilter = createChip("Stipend: Any") {
            val items = listOf("All", ">= 0", ">= 25000", ">= 50000", ">= 75000", ">= 100000")
            showChoiceDialog("Select Minimum Stipend", items, selectedMinStipendLabel()) {
                selectedMinStipend = when (it) {
                    ">= 25000" -> "25000"
                    ">= 50000" -> "50000"
                    ">= 75000" -> "75000"
                    ">= 100000" -> "100000"
                    else -> ""
                }
                updateFilterButtonText()
                applyLocalFiltersAndRender()
            }
        }

        btnAiFilter = createChip("Chance: Any") {
            val items = listOf("All", "SAFE", "TARGET", "DREAM")
            showChoiceDialog("Select Result Label", items, selectedAiPreference.ifBlank { "All" }) {
                selectedAiPreference = if (it == "All") "" else it
                updateFilterButtonText()
                applyLocalFiltersAndRender()
            }
        }

        btnResetFilter = createChip("Reset Filters") {
            selectedSubject = ""
            selectedState = ""
            selectedCategory = "GEN"
            selectedQuota = "All India"
            selectedCollegeType = ""
            selectedMaxFee = ""
            selectedMaxBond = ""
            selectedMinStipend = ""
            selectedAiPreference = ""
            updateFilterButtonText()
            applyLocalFiltersAndRender()
        }

        rankRow = createRow()
        row1 = createRow()
        row2 = createRow()
        row3 = createRow()

        buildFilterButtons()

        filterContainer.addView(rankRow)
        filterContainer.addView(row1)
        filterContainer.addView(row2)
        filterContainer.addView(row3)
        updateFilterButtonText()

        fetchPredictionFromServer(accuracy, streak, attempted, correct)

        val bottomNav = findViewById<BottomNavigationView>(R.id.bottomNavigation)
        setupAppBottomNavigation(bottomNav, R.id.nav_feed)
    }

    private fun updateFilterButtonText() {
        btnCustomRank.text = "Rank: $selectedRank"
        btnSubjectFilter.text = "Subject: ${selectedSubject.ifBlank { "Any" }}"
        btnStateFilter.text = "State: ${selectedState.ifBlank { "Any" }}"
        btnCategoryFilter.text = "Category: ${selectedCategory.ifBlank { "Any" }}"
        btnQuotaFilter.text = "Quota: ${selectedQuota.ifBlank { "Any" }}"
        btnCollegeTypeFilter.text = "Type: ${selectedCollegeTypeDisplay()}"
        btnFeeFilter.text = "Fee: ${selectedMaxFeeLabel()}"
        btnBondFilter.text = "Bond: ${selectedMaxBondLabel()}"
        btnStipendFilter.text = "Stipend: ${selectedMinStipendLabel()}"
        btnAiFilter.text = "Chance: ${selectedAiPreference.ifBlank { "Any" }}"
        txtPredictedRank.text = "🎯 Expected Rank : $selectedRank"
    }

    private fun selectedCollegeTypeDisplay(): String {
        return when (selectedCollegeType.lowercase()) {
            "government" -> "Government"
            "private" -> "Private"
            else -> "Any"
        }
    }

    private fun selectedMaxFeeLabel(): String {
        return when (selectedMaxFee) {
            "100000" -> "<= 100000"
            "200000" -> "<= 200000"
            "300000" -> "<= 300000"
            "500000" -> "<= 500000"
            "1000000" -> "<= 1000000"
            else -> "Any"
        }
    }

    private fun selectedMaxBondLabel(): String {
        return when (selectedMaxBond) {
            "1" -> "<= 1"
            "2" -> "<= 2"
            "3" -> "<= 3"
            "5" -> "<= 5"
            else -> "Any"
        }
    }

    private fun selectedMinStipendLabel(): String {
        return when (selectedMinStipend) {
            "25000" -> ">= 25000"
            "50000" -> ">= 50000"
            "75000" -> ">= 75000"
            "100000" -> ">= 100000"
            else -> "Any"
        }
    }

    private fun createFilterRow(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }
    }

    private fun createChip(text: String, onClick: () -> Unit): TextView {
        return TextView(this).apply {
            this.text = text
            setTextColor(Color.WHITE)
            setTypeface(typeface, Typeface.BOLD)
            textSize = 13f
            setPadding(28, 18, 28, 18)
            setBackgroundColor(Color.parseColor("#2563EB"))
            layoutParams = LinearLayout.LayoutParams(
                0,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                1f
            ).apply {
                setMargins(10, 10, 10, 10)
            }
            isClickable = true
            isFocusable = true
            setOnClickListener { onClick() }
        }
    }

    private fun showCustomRankDialog() {
        val input = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER
            setText(selectedRank)
            setSelection(text.length)
        }

        AlertDialog.Builder(this)
            .setTitle("Enter Custom Rank")
            .setMessage("Change the rank and refresh results.")
            .setView(input)
            .setPositiveButton("Apply") { _, _ ->
                val value = input.text.toString().trim().toIntOrNull()
                if (value == null || value <= 0) {
                    Toast.makeText(this, "Please enter a valid rank", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                selectedRank = value.toString()
                updateFilterButtonText()
                fetchColleges()
            }
            .setNeutralButton("Original") { _, _ ->
                selectedRank = originalRank
                updateFilterButtonText()
                fetchColleges()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun fetchPredictionFromServer(
        accuracy: Int,
        streak: Int,
        attempted: Int,
        correct: Int
    ) {
        txtPredictedRank.text = "Predicting..."
        txtAiSummary.text = "Analyzing performance..."

        Log.d("RANK_API", "Fetching prediction for User: $userId")
        val queue = Volley.newRequestQueue(this)

        val request = object : StringRequest(
            Request.Method.POST,
            PREDICT_RANK_URL,
            { response ->
                Log.d("RANK_API", "Response: $response")
                try {
                    val json = JSONObject(response)
                    if (json.optBoolean("success", false)) {
                        val minRankStr = json.optString("predicted_min_rank", "0")
                        val tier = json.optString("tier", "Average")

                        selectedRank = cleanRankString(minRankStr)
                        originalRank = selectedRank
                        selectedTier = tier

                        prefs.edit().putString("predicted_rank", selectedRank).putString("predicted_tier", tier).apply()

                        updateFilterButtonText()
                        fetchColleges()
                    } else {
                        Log.e("RANK_API", json.optString("message", "Prediction unavailable"))
                        fetchColleges()
                    }
                } catch (e: Exception) {
                    Log.e("RANK_API", "JSON Error", e)
                    fetchColleges()
                }
            },
            { error ->
                Log.e("RANK_API", "Volley Error: ${error.message}")
                fetchColleges()
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                return hashMapOf(
                    "accuracy" to accuracy.toString(),
                    "streak" to streak.toString(),
                    "attempted" to attempted.toString(),
                    "correct" to correct.toString(),
                    "user_id" to userId.toString()
                )
            }
        }

        request.retryPolicy = DefaultRetryPolicy(10000, 2, 1.5f)
        request.setShouldCache(false)
        queue.add(request)
    }

    private fun showChoiceDialog(
        title: String,
        items: List<String>,
        current: String,
        onSelected: (String) -> Unit
    ) {
        val safeItems = items.distinct()
        val checkedIndex = safeItems.indexOfFirst {
            it.equals(current, ignoreCase = true)
        }.let { if (it >= 0) it else 0 }

        AlertDialog.Builder(this)
            .setTitle(title)
            .setSingleChoiceItems(safeItems.toTypedArray(), checkedIndex) { dialog, which ->
                onSelected(safeItems[which])
                dialog.dismiss()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun fetchColleges() {
        progressBar.visibility = View.VISIBLE
        txtAiSummary.text = "Loading AI counseling..."
        layoutEmptyState.visibility = View.GONE

        val queue = Volley.newRequestQueue(this)

        val request = object : StringRequest(
            Request.Method.POST,
            API_URL,
            { response ->
                progressBar.visibility = View.GONE
                try {
                    Log.d("COLLEGE_API", response)

                    val json = JSONObject(response)
                    val success = json.optBoolean("success", false)

                    if (success) {
                        val aiSummary = json.optString("ai_summary", "")
                        txtAiSummary.text = aiMarkdownSpannable(
                            formatAiSummary(aiSummary.ifBlank { "AI summary unavailable" })
                        )

                        // Save the college-predictor AI summary (input params + reply) for model training.
                        if (aiSummary.isNotBlank()) {
                            try {
                                val promptParams = org.json.JSONObject()
                                    .put("rank", selectedRank)
                                    .put("category", selectedCategory)
                                    .put("quota", selectedQuota)
                                    .put("subject", selectedSubject)
                                    .put("state", selectedState)
                                    .put("college_type", selectedCollegeType)
                                    .put("max_fee", selectedMaxFee)
                                    .put("max_bond", selectedMaxBond)
                                    .put("min_stipend", selectedMinStipend)
                                    .put("ai_preference", selectedAiPreference)
                                    .toString()
                                AiTrainingLogger.log(
                                    source = "predict_college",
                                    provider = "",
                                    model = "",
                                    prompt = "College predictor request: " + promptParams,
                                    response = aiSummary
                                )
                            } catch (e: Exception) {
                                // Logging must never break college rendering.
                            }
                        }

                        val totalResults = json.optInt("total_results", 0)
                        val safeCount = json.optInt("safe_count", 0)
                        val targetCount = json.optInt("target_count", 0)
                        val dreamCount = json.optInt("dream_count", 0)

                        txtTotalResults.text = "Available Colleges : $totalResults"
                        txtSafeCount.text = "SAFE : $safeCount"
                        txtTargetCount.text = "TARGET : $targetCount"
                        txtDreamCount.text = "DREAM : $dreamCount"

                        val incomingSubjects = jsonArrayToList(
                            json.optJSONArray("distinct_subjects")
                                ?: json.optJSONArray("distinct_courses")
                        )
                        val incomingStates = jsonArrayToList(json.optJSONArray("distinct_states"))
                        val incomingCategories =
                            jsonArrayToList(json.optJSONArray("distinct_categories"))
                        val incomingQuotas = jsonArrayToList(json.optJSONArray("distinct_quotas"))

                        Log.d("COLLEGE_API", "Subjects: $incomingSubjects")
                        Log.d("COLLEGE_API", "States: $incomingStates")
                        Log.d("COLLEGE_API", "Categories: $incomingCategories")
                        Log.d("COLLEGE_API", "Quotas: $incomingQuotas")

                        if (incomingSubjects.isNotEmpty()) {
                            distinctSubjects = (distinctSubjects + incomingSubjects)
                                .distinct()
                                .sortedBy { it.lowercase() }
                        }
                        if (incomingStates.isNotEmpty()) {
                            distinctStates = (distinctStates + incomingStates)
                                .distinct()
                                .sortedBy { it.lowercase() }
                        }
                        if (incomingCategories.isNotEmpty()) {
                            distinctCategories = (distinctCategories + incomingCategories)
                                .distinct()
                                .sortedBy { it.lowercase() }
                        }
                        if (incomingQuotas.isNotEmpty()) {
                            distinctQuotas = (distinctQuotas + incomingQuotas)
                                .distinct()
                                .sortedBy { it.lowercase() }
                        }

                        distinctCollegeTypes =
                            jsonArrayToList(json.optJSONArray("distinct_college_types")).ifEmpty {
                                listOf("Government", "Private")
                            }

                        masterColleges.clear()
                        addToMasterList(json.optJSONArray("safe_colleges"), "SAFE")
                        addToMasterList(json.optJSONArray("target_colleges"), "TARGET")
                        addToMasterList(json.optJSONArray("dream_colleges"), "DREAM")

                        buildFilterButtons()
                        applyLocalFiltersAndRender()

                        if (distinctSubjects.size < 5 || distinctStates.size < 5) {
                            fetchGlobalFiltersFallback()
                        }
                    } else {
                        val msg = json.optString("message", "No colleges found")
                        txtAiSummary.text = msg
                        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
                        masterColleges.clear()
                        feedList.clear()
                        recyclerView.adapter = CollegeFeedAdapter(feedList)
                        layoutEmptyState.visibility = View.VISIBLE
                    }
                } catch (e: Exception) {
                    Log.e("COLLEGE_API", "Parsing error", e)
                    Toast.makeText(this, "Parsing error", Toast.LENGTH_SHORT).show()
                    txtAiSummary.text = "Parsing error"
                    layoutEmptyState.visibility = View.VISIBLE
                }
            },
            { error ->
                progressBar.visibility = View.GONE
                Log.e("COLLEGE_API", error.message ?: "Volley Error")
                Toast.makeText(this, "Network Error", Toast.LENGTH_SHORT).show()
                txtAiSummary.text = "Network Error"
                layoutEmptyState.visibility = View.VISIBLE
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                val params = hashMapOf(
                    "rank" to selectedRank,
                    "category" to selectedCategory.ifBlank { "GEN" },
                    "quota" to selectedQuota.ifBlank { "All India" },
                    "subject" to selectedSubject,
                    "state" to selectedState,
                    "college_type" to selectedCollegeType,
                    "max_fee" to selectedMaxFee,
                    "max_bond" to selectedMaxBond,
                    "min_stipend" to selectedMinStipend,
                    "ai_preference" to selectedAiPreference
                )

                if (selectedYear != "all") {
                    params["year"] = selectedYear
                }

                return params
            }
        }

        request.retryPolicy = DefaultRetryPolicy(10000, 2, 1.5f)
        request.setShouldCache(false)
        queue.add(request)
    }

    private fun fetchGlobalFiltersFallback() {
        val queue = Volley.newRequestQueue(this)
        val request = object : StringRequest(
            Request.Method.POST,
            API_URL,
            { response ->
                try {
                    val json = JSONObject(response)
                    if (json.optBoolean("success", false)) {
                        val fallbackSubjects = jsonArrayToList(
                            json.optJSONArray("distinct_subjects")
                                ?: json.optJSONArray("distinct_courses")
                        )
                        val fallbackStates = jsonArrayToList(json.optJSONArray("distinct_states"))
                        val fallbackCategories =
                            jsonArrayToList(json.optJSONArray("distinct_categories"))
                        val fallbackQuotas = jsonArrayToList(json.optJSONArray("distinct_quotas"))

                        Log.d("FALLBACK_FILTERS", "FB Subjects: $fallbackSubjects")
                        Log.d("FALLBACK_FILTERS", "FB States: $fallbackStates")
                        Log.d("FALLBACK_FILTERS", "FB Categories: $fallbackCategories")
                        Log.d("FALLBACK_FILTERS", "FB Quotas: $fallbackQuotas")

                        distinctSubjects = (distinctSubjects + fallbackSubjects).distinct()
                            .sortedBy { it.lowercase() }
                        distinctStates =
                            (distinctStates + fallbackStates).distinct().sortedBy { it.lowercase() }
                        distinctCategories = (distinctCategories + fallbackCategories).distinct()
                            .sortedBy { it.lowercase() }
                        distinctQuotas =
                            (distinctQuotas + fallbackQuotas).distinct().sortedBy { it.lowercase() }

                        buildFilterButtons()
                    }
                } catch (e: Exception) {
                    Log.e("FALLBACK_FILTERS", "Error processing structural fallback lists", e)
                }
            },
            { error -> Log.e("FALLBACK_FILTERS", "Sync failed: ${error.message}") }
        ) {
            override fun getParams(): MutableMap<String, String> {
                val params = hashMapOf(
                    "rank" to "50000",
                    "category" to "GEN",
                    "quota" to "All India"
                )
                if (selectedYear != "all") {
                    params["year"] = selectedYear
                }
                return params
            }
        }
        request.setShouldCache(false)
        queue.add(request)
    }

    private fun addToMasterList(arr: JSONArray?, label: String) {
        if (arr == null || arr.length() == 0) return

        for (i in 0 until arr.length()) {
            val obj = arr.optJSONObject(i) ?: continue

            val rawStipend = obj.optDouble("average_stipend", 0.0)
            val finalStipend = if (rawStipend <= 0.0) 100000.0 else rawStipend

            masterColleges.add(
                CollegeModel(
                    id = obj.optInt("id", i),
                    institute = obj.optString("institute", ""),
                    course = obj.optString("course", ""),
                    subject = obj.optString("subject", obj.optString("course", "")),
                    closingRank = obj.optInt("closing_rank", 0),
                    category = obj.optString("category", ""),
                    quota = obj.optString("quota", ""),
                    year = obj.optString("year", ""),
                    round = obj.optString("round", ""),
                    state = obj.optString("state", ""),
                    medicalCouncil = obj.optString("medical_council", ""),
                    feePerYear = obj.optDouble("fee_per_year", 0.0),
                    totalFee = obj.optDouble("total_fee", 0.0),
                    averageStipend = finalStipend,
                    bondYears = obj.optInt("bond_years", 0),
                    chance = obj.optString("chance", label),
                    aiLabel = obj.optString("ai_label", label)
                )
            )
        }
    }

    private fun applyLocalFiltersAndRender() {
        feedList.clear()

        val safeList = mutableListOf<CollegeModel>()
        val targetList = mutableListOf<CollegeModel>()
        val dreamList = mutableListOf<CollegeModel>()

        val groupedColleges = masterColleges
            .filter { matchesFilters(it) }
            .groupBy {
                "${it.institute}|${it.subject}|${it.category}|${it.quota}|${it.state}|${it.year}|${it.round}|${it.closingRank}"
            }
            .map { (_, occurrences) ->
                val first = occurrences.first()
                first.copy(seatCount = occurrences.size)
            }

        for (college in groupedColleges) {
            when (normalize(college.aiLabel)) {
                "safe" -> safeList.add(college)
                "target" -> targetList.add(college)
                else -> dreamList.add(college)
            }
        }

        val totalSafeSeats = safeList.sumOf { it.seatCount }
        val totalTargetSeats = targetList.sumOf { it.seatCount }
        val totalDreamSeats = dreamList.sumOf { it.seatCount }

        if (safeList.isNotEmpty()) {
            feedList.add(FeedItem.SectionHeader("SAFE Colleges"))
            safeList.sortedBy { it.closingRank }
                .forEach { feedList.add(FeedItem.CollegeRow(it)) }
        }

        if (targetList.isNotEmpty()) {
            feedList.add(FeedItem.SectionHeader("TARGET Colleges"))
            targetList.sortedBy { it.closingRank }
                .forEach { feedList.add(FeedItem.CollegeRow(it)) }
        }

        if (dreamList.isNotEmpty()) {
            feedList.add(FeedItem.SectionHeader("DREAM Colleges"))
            dreamList.sortedBy { it.closingRank }
                .forEach { feedList.add(FeedItem.CollegeRow(it)) }
        }

        recyclerView.adapter = CollegeFeedAdapter(feedList)
        layoutEmptyState.visibility = if (feedList.isEmpty()) View.VISIBLE else View.GONE

        txtSafeCount.text = "SAFE : $totalSafeSeats"
        txtTargetCount.text = "TARGET : $totalTargetSeats"
        txtDreamCount.text = "DREAM : $totalDreamSeats"
        txtTotalResults.text =
            "Available Colleges : ${feedList.count { it is FeedItem.CollegeRow }}"
    }

    private fun matchesFilters(college: CollegeModel): Boolean {
        if (selectedSubject.isNotBlank()) {
            val subjectText = normalize(college.subject.ifBlank { college.course })
            if (!subjectText.contains(normalize(selectedSubject))) return false
        }

        if (selectedState.isNotBlank() &&
            !normalize(college.state).contains(normalize(selectedState))
        ) {
            return false
        }

        if (selectedCategory.isNotBlank() &&
            !normalize(college.category).contains(normalize(selectedCategory))
        ) {
            return false
        }

        if (selectedQuota.isNotBlank() &&
            !normalize(college.quota).contains(normalize(selectedQuota))
        ) {
            return false
        }

        if (selectedCollegeType == "government") {
            val inst = normalize(college.institute)
            if (!inst.contains("government") && !inst.contains("govt") && !inst.contains("aiims")) {
                return false
            }
        }

        if (selectedCollegeType == "private") {
            val inst = normalize(college.institute)
            if (inst.contains("government") || inst.contains("govt") || inst.contains("aiims")) {
                return false
            }
        }

        if (selectedMaxFee.isNotBlank() &&
            college.feePerYear > selectedMaxFee.toDoubleOrNull().orZero()
        ) {
            return false
        }

        if (selectedMaxBond.isNotBlank() &&
            college.bondYears > selectedMaxBond.toIntOrNull().orZero()
        ) {
            return false
        }

        if (selectedMinStipend.isNotBlank() &&
            college.averageStipend < selectedMinStipend.toDoubleOrNull().orZero()
        ) {
            return false
        }

        if (selectedAiPreference.isNotBlank() &&
            !normalize(college.aiLabel).contains(normalize(selectedAiPreference))
        ) {
            return false
        }

        return true
    }

    private fun formatAiSummary(raw: String): String {
        return try {
            val json = JSONObject(raw)
            val summary = json.optString("summary", raw)
            val highlights = json.optJSONArray("highlights")
            val builder = StringBuilder(summary)

            if (highlights != null && highlights.length() > 0) {
                builder.append("\n\nHighlights:\n")
                for (i in 0 until highlights.length()) {
                    builder.append("• ").append(highlights.optString(i)).append("\n")
                }
            }

            builder.toString().trim()
        } catch (_: Exception) {
            raw
        }
    }

    private fun jsonArrayToList(arr: JSONArray?): List<String> {
        if (arr == null) return emptyList()
        val out = mutableListOf<String>()
        for (i in 0 until arr.length()) {
            val v = arr.optString(i).trim()
            if (v.isNotEmpty()) out.add(v)
        }
        return out.distinct().sortedBy { it.lowercase() }
    }

    private fun normalize(text: String): String {
        return text.trim().lowercase().replace(Regex("\\s+"), " ")
    }

    private fun Double?.orZero(): Double = this ?: 0.0
    private fun Int?.orZero(): Int = this ?: 0

    private fun createRow(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = 6
            }
        }
    }

    private fun getRankFromIntentOrNull(): String? {
        return intent.getStringExtra("rank") ?: intent.getStringExtra("predicted_rank")
    }

    private fun cleanRankString(raw: String): String {
        return raw.filter { it.isDigit() }.ifBlank { "50000" }
    }

    private fun buildFilterButtons() {
        rankRow.removeAllViews()
        row1.removeAllViews()
        row2.removeAllViews()
        row3.removeAllViews()

        rankRow.addView(btnCustomRank)

        row1.addView(btnSubjectFilter)
        row1.addView(btnStateFilter)
        row1.addView(btnCategoryFilter)

        row2.addView(btnQuotaFilter)
        row2.addView(btnCollegeTypeFilter)
        row2.addView(btnFeeFilter)

        row3.addView(btnBondFilter)
        row3.addView(btnStipendFilter)
        row3.addView(btnAiFilter)
        row3.addView(btnResetFilter)
    }
}

/* --------------------------------------------------- */
/* UTILS */
/* --------------------------------------------------- */

fun formatAmount(amount: Double): String {
    return if (amount >= 100000) {
        "${(amount / 100000).roundToInt()}L"
    } else {
        amount.roundToInt().toString()
    }
}

/* --------------------------------------------------- */
/* MODELS */
/* --------------------------------------------------- */

data class CollegeModel(
    val id: Int = 0,
    val institute: String,
    val course: String,
    val subject: String,
    val closingRank: Int,
    val category: String,
    val quota: String,
    val year: String,
    val round: String,
    val state: String,
    val medicalCouncil: String,
    val feePerYear: Double,
    val totalFee: Double,
    val averageStipend: Double,
    val bondYears: Int,
    val chance: String,
    val aiLabel: String = "",
    val seatCount: Int = 1
)

sealed class FeedItem {
    data class SectionHeader(val title: String) : FeedItem()
    data class CollegeRow(val college: CollegeModel) : FeedItem()
}

/* --------------------------------------------------- */
/* ADAPTER */
/* --------------------------------------------------- */

class CollegeFeedAdapter(
    private val list: List<FeedItem>
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    companion object {
        private const val TYPE_HEADER = 1
        private const val TYPE_COLLEGE = 2
    }

    override fun getItemViewType(position: Int): Int {
        return when (list[position]) {
            is FeedItem.SectionHeader -> TYPE_HEADER
            is FeedItem.CollegeRow -> TYPE_COLLEGE
        }
    }

    override fun getItemCount(): Int = list.size

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val context = parent.context

        fun createBoxText(
            size: Float,
            textColor: String,
            bgColor: String,
            bold: Boolean = false,
            paddingH: Int = 12,
            paddingV: Int = 10,
            corner: Float = 12f,
            strokeColor: String = "#334155"
        ): TextView {
            return TextView(context).apply {
                textSize = size
                setTextColor(Color.parseColor(textColor))
                if (bold) setTypeface(typeface, Typeface.BOLD)
                setPadding(paddingH, paddingV, paddingH, paddingV)
                background = GradientDrawable().apply {
                    shape = GradientDrawable.RECTANGLE
                    cornerRadius = corner
                    setColor(Color.parseColor(bgColor))
                    setStroke(2, Color.parseColor(strokeColor))
                }
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
            }
        }

        fun createRow(): LinearLayout {
            return LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                ).apply {
                    topMargin = 6
                }
            }
        }

        fun createMiniBox(
            textColor: String,
            bgColor: String,
            bold: Boolean = false
        ): TextView {
            return TextView(context).apply {
                textSize = 10f
                setTextColor(Color.parseColor(textColor))
                if (bold) setTypeface(typeface, Typeface.BOLD)
                gravity = Gravity.CENTER
                setPadding(8, 8, 8, 8)
                isSingleLine = false
                maxLines = 3
                background = GradientDrawable().apply {
                    shape = GradientDrawable.RECTANGLE
                    cornerRadius = 10f
                    setColor(Color.parseColor(bgColor))
                    setStroke(2, Color.parseColor("#334155"))
                }
                layoutParams = LinearLayout.LayoutParams(
                    0,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    1f
                ).apply {
                    marginEnd = 8
                }
            }
        }

        return when (viewType) {
            TYPE_HEADER -> {
                val tv = TextView(context).apply {
                    textSize = 19f
                    setTextColor(Color.parseColor("#FFFFFF"))
                    setTypeface(typeface, Typeface.BOLD)
                    setPadding(28, 24, 28, 14)
                    background = GradientDrawable().apply {
                        shape = GradientDrawable.RECTANGLE
                        cornerRadius = 0f
                        setColor(Color.parseColor("#0F172A"))
                    }
                    layoutParams = ViewGroup.MarginLayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                    ).apply {
                        setMargins(0, 10, 0, 10)
                    }
                }
                HeaderVH(tv)
            }

            else -> {
                val container = LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    layoutParams = RecyclerView.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                    )
                }

                val card = CardView(context).apply {
                    radius = 16f
                    cardElevation = 4f
                    useCompatPadding = true
                    preventCornerOverlap = true
                    setCardBackgroundColor(Color.parseColor("#0B1220"))
                    layoutParams = RecyclerView.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                    ).apply {
                        setMargins(14, 10, 14, 10)
                    }
                }

                val root = LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(12, 12, 12, 12)
                    background = GradientDrawable().apply {
                        shape = GradientDrawable.RECTANGLE
                        cornerRadius = 16f
                        setColor(Color.parseColor("#0B1220"))
                    }
                }

                val txtInstitute = createBoxText(
                    14f,
                    "#FFFFFF",
                    "#1E293B",
                    true,
                    paddingH = 12,
                    paddingV = 10,
                    corner = 12f,
                    strokeColor = "#475569"
                )

                val txtAddress = createBoxText(
                    11f,
                    "#E2E8F0",
                    "#111827",
                    true,
                    paddingH = 12,
                    paddingV = 10,
                    corner = 12f,
                    strokeColor = "#334155"
                )

                val txtState = createBoxText(
                    11f,
                    "#E2E8F0",
                    "#111827",
                    true,
                    paddingH = 12,
                    paddingV = 10,
                    corner = 12f,
                    strokeColor = "#334155"
                )

                val row1 = createRow()
                val txtCourse = createBoxText(
                    11.5f,
                    "#CBD5E1",
                    "#162033"
                )
                val txtRank = createBoxText(
                    11.5f,
                    "#38BDF8",
                    "#0B2940",
                    true
                )
                row1.addView(
                    txtCourse,
                    LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.3f)
                        .apply { marginEnd = 6 }
                )
                row1.addView(
                    txtRank,
                    LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                )

                val row2 = createRow()
                val txtChance = createBoxText(
                    11.5f,
                    "#22C55E",
                    "#10281A",
                    true
                )
                val txtFees = createBoxText(
                    11.5f,
                    "#FACC15",
                    "#3B2A05",
                    true
                )
                row2.addView(
                    txtChance,
                    LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                        .apply { marginEnd = 6 }
                )
                row2.addView(
                    txtFees,
                    LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                )

                val row3 = createRow()
                val txtStipend = createBoxText(
                    11.5f,
                    "#4ADE80",
                    "#0F2418"
                )
                val txtExtra = createBoxText(
                    11.5f,
                    "#94A3B8",
                    "#151E2D"
                )
                row3.addView(
                    txtStipend,
                    LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                        .apply { marginEnd = 6 }
                )
                row3.addView(
                    txtExtra,
                    LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                )

                val divider = View(context).apply {
                    setBackgroundColor(Color.parseColor("#243041"))
                    layoutParams = LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        2
                    ).apply {
                        topMargin = 10
                        bottomMargin = 8
                    }
                }

                val txtCompleteInfo = createBoxText(
                    11.5f,
                    "#E2E8F0",
                    "#1E293B",
                    false
                ).apply {
                    gravity = Gravity.START
                }

                val detailsTitle = TextView(context).apply {
                    text = "Additional Details"
                    textSize = 10f
                    setTextColor(Color.parseColor("#94A3B8"))
                    setTypeface(typeface, Typeface.BOLD)
                    setPadding(4, 0, 4, 4)
                }

                val detailsRow1 = createRow()
                val txtQuota = createMiniBox("#E2E8F0", "#111827", true)
                val txtCategory = createMiniBox("#E2E8F0", "#111827", true)
                detailsRow1.addView(txtQuota)
                detailsRow1.addView(txtCategory)

                val detailsRow2 = createRow()
                val txtRound = createMiniBox("#E2E8F0", "#111827", true)
                val txtBond = createMiniBox("#E2E8F0", "#111827", true)
                detailsRow2.addView(txtRound)
                detailsRow2.addView(txtBond)

                val detailsRow3 = createRow()
                val txtYear = createMiniBox("#E2E8F0", "#111827", true)
                val spacer = View(context).apply {
                    layoutParams = LinearLayout.LayoutParams(
                        0,
                        1,
                        1f
                    )
                }
                detailsRow3.addView(txtYear)
                detailsRow3.addView(spacer)

                root.addView(txtInstitute)
                root.addView(txtAddress)
                root.addView(txtState)
                root.addView(row1)
                root.addView(row2)
                root.addView(row3)
                root.addView(
                    txtCompleteInfo,
                    LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                    ).apply { topMargin = 8 }
                )
                root.addView(divider)
                root.addView(detailsTitle)
                root.addView(detailsRow1)
                root.addView(detailsRow2)
                root.addView(detailsRow3)

                card.addView(root)
                container.addView(card)

                CollegeVH(
                    container,
                    txtInstitute,
                    txtCourse,
                    txtRank,
                    txtChance,
                    txtFees,
                    txtStipend,
                    txtExtra,
                    txtQuota,
                    txtCategory,
                    txtRound,
                    txtBond,
                    txtYear,
                    txtCompleteInfo,
                    txtAddress,
                    txtState
                )
            }
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        when (val item = list[position]) {
            is FeedItem.SectionHeader -> {
                (holder as HeaderVH).textView.text = item.title
            }

            is FeedItem.CollegeRow -> {
                val college = item.college
                val vh = holder as CollegeVH

                val displaySubject = college.subject.ifBlank { college.course }

                val rawInstitute = college.institute.ifBlank { "Unknown Institute" }
                val commaIndex = rawInstitute.indexOf(",")

                val instituteName: String
                val instituteAddress: String

                if (commaIndex != -1) {
                    instituteName = rawInstitute.substring(0, commaIndex).trim()
                    instituteAddress = rawInstitute.substring(commaIndex + 1).trim()
                } else {
                    instituteName = rawInstitute
                    instituteAddress = ""
                }

                vh.txtInstitute.text = instituteName
                vh.txtAddress.text = "📍 Address: ${if (instituteAddress.isNotBlank()) instituteAddress else "Not Available"}"
                vh.txtState.text = "🏙 State: ${if (college.state.isNotBlank()) college.state else "Not Available"}"

                vh.txtCourse.text = "📘 ${displaySubject}"

                vh.txtRank.text = "🎯 Rank: ${college.closingRank} • 🪑 Seats: ${college.seatCount}"
                vh.txtChance.text = "Chance: ${college.chance} • ${college.aiLabel}"
                vh.txtFees.text = "💰 Fee / Year: ₹${formatAmount(college.feePerYear)}"
                vh.txtStipend.text = "🏥 Stipend: ₹${formatAmount(college.averageStipend)}"
                vh.txtExtra.text = "Quota: ${college.quota}"

                vh.txtCompleteInfo.text =
                    "📋 Full Course Info: $displaySubject (${college.category}) in ${college.state} via ${college.quota} quota. Medical Council: ${college.medicalCouncil.ifBlank { "All India Council" }}"

                vh.txtQuota.text = "Quota: ${college.quota}"
                vh.txtCategory.text = "Category: ${college.category}"
                vh.txtRound.text = "Round: ${college.round}"
                vh.txtBond.text = "Bond: ${college.bondYears} Years"
                vh.txtYear.text = "Year: ${college.year}"

                vh.itemView.setOnClickListener {
                    val context = vh.itemView.context
                    val intent = android.content.Intent(context, CollegeDetailActivity::class.java)
                    intent.putExtra("college_name", college.institute)
                    intent.putExtra("list_url", "https://www.MediGyaan.xyz/colleges.html")
                    context.startActivity(intent)
                }
            }
        }
    }
}

/* --------------------------------------------------- */
/* VIEW HOLDERS */
/* --------------------------------------------------- */

class HeaderVH(val textView: TextView) : RecyclerView.ViewHolder(textView)

class CollegeVH(
    val cardView: View,
    val txtInstitute: TextView,
    val txtCourse: TextView,
    val txtRank: TextView,
    val txtChance: TextView,
    val txtFees: TextView,
    val txtStipend: TextView,
    val txtExtra: TextView,
    val txtQuota: TextView,
    val txtCategory: TextView,
    val txtRound: TextView,
    val txtBond: TextView,
    val txtYear: TextView,
    val txtCompleteInfo: TextView,
    val txtAddress: TextView,
    val txtState: TextView
) : RecyclerView.ViewHolder(cardView)