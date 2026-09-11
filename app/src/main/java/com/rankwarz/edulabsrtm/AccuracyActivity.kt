package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.SharedPreferences
import android.graphics.Color
import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.widget.Button
import android.widget.FrameLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.components.Description
import com.github.mikephil.charting.components.Legend
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.components.MarkerView
import com.github.mikephil.charting.highlight.Highlight
import com.github.mikephil.charting.utils.MPPointF
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import com.github.mikephil.charting.formatter.ValueFormatter
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.tabs.TabLayout
import org.json.JSONObject

class AccuracyActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "ACCURACY_DEBUG"
        private const val PREF_NAME = "MY_APP"
        private const val KEY_USER_ID = "user_id"
        private const val BASE_URL = "https://medigyaan.xyz/Neurons/"
    }

    private lateinit var prefs: SharedPreferences

    private var txtBigAccuracy: TextView? = null
    private var txtOverallStats: TextView? = null
    private var txtPeriodStats: TextView? = null
    private var txtTodayStats: TextView? = null
    private var txtStatus: TextView? = null
    private var btnRefresh: Button? = null
    private var tabLayout: TabLayout? = null
    private var lineChart: LineChart? = null

    private var loggedInUserId = 0
    private var overallAccuracyFromServer = 0
    private var selectedTab = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_accuracy)

        prefs = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        loggedInUserId = prefs.getInt(KEY_USER_ID, 0)

        initViews()
        setupTabs()

        btnRefresh?.setOnClickListener {
            loadAccuracy()
        }

        loadAccuracy()

        val bottomNav = BottomNavigationView(this)
        bottomNav.id = R.id.bottomNavigation
        val params = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply { gravity = Gravity.BOTTOM }
        val content = findViewById<FrameLayout>(android.R.id.content)
        content.addView(bottomNav, params)
        setupAppBottomNavigation(bottomNav, R.id.nav_feed)
    }

    private fun initViews() {
        txtBigAccuracy = findViewById(R.id.txtBigAccuracy)
        txtOverallStats = findViewById(R.id.txtOverallStats)
        txtPeriodStats = findViewById(R.id.txtPeriodStats)
        txtTodayStats = findViewById(R.id.txtTodayStats)
        txtStatus = findViewById(R.id.txtStatus)
        btnRefresh = findViewById(R.id.btnRefresh)
        tabLayout = findViewById(R.id.tabLayoutAccuracy)
        lineChart = findViewById(R.id.lineChartAccuracy)
    }

    private fun setupTabs() {
        val tab = tabLayout ?: return

        tab.removeAllTabs()
        tab.addTab(tab.newTab().setText("7 Days"))
        tab.addTab(tab.newTab().setText("30 Days"))
        tab.addTab(tab.newTab().setText("Topics"))

        tab.addOnTabSelectedListener(object : TabLayout.OnTabSelectedListener {
            override fun onTabSelected(t: TabLayout.Tab?) {
                selectedTab = t?.position ?: 0
                renderSelectedTab()
            }

            override fun onTabUnselected(t: TabLayout.Tab?) {}
            override fun onTabReselected(t: TabLayout.Tab?) {
                selectedTab = t?.position ?: 0
                renderSelectedTab()
            }
        })
    }

    private fun renderSelectedTab() {
        when (selectedTab) {
            0 -> renderTrend(7, "7 Days")
            1 -> renderTrend(30, "30 Days")
            2 -> renderTopicWise()
        }
    }

    private fun loadAccuracy() {
        if (loggedInUserId == 0) {
            txtStatus?.text = "Invalid user"
            return
        }

        val url = "${BASE_URL}get_profilev1.php?user_id=$loggedInUserId&viewer_id=$loggedInUserId"

        txtStatus?.text = "Loading accuracy..."
        Log.d(TAG, "API CALL: $url")

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                try {
                    val root = JSONObject(response)
                    val json = root.optJSONObject("data") ?: root
                    updateAccuracyUI(json)
                } catch (e: Exception) {
                    Log.e(TAG, "Parse error: ${e.message}")
                    txtStatus?.text = "Parse error"
                    Toast.makeText(this, "Parse error", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                Log.e(TAG, "Network error: ${error.message}")
                txtStatus?.text = "Network error"
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
            }
        )

        Volley.newRequestQueue(this).add(request)
    }

    private fun updateAccuracyUI(json: JSONObject) {
        val name = json.optString("name", "User")

        var overallAttempted = 0
        var overallCorrect = 0

        val attemptsArr = json.optJSONArray("attempts")
        if (attemptsArr != null && attemptsArr.length() > 0) {
            val obj = attemptsArr.optJSONObject(0)
            if (obj != null) {
                overallAttempted = obj.optInt("total_attempted", 0)
                overallCorrect = obj.optInt("correct_attempted", 0)
            }
        }

        overallAccuracyFromServer = if (overallAttempted > 0) {
            (overallCorrect * 100) / overallAttempted
        } else {
            0
        }

        val todayStats = DailyStatsManager.getToday(this)
        val todayAttempted = todayStats.first
        val todayCorrect = todayStats.second
        val todayAccuracy = DailyStatsManager.calculateAccuracy(todayAttempted, todayCorrect)

        val estimatedAttempted = estimateEndOfDay(todayAttempted)
        val estimatedCorrect = estimateEndOfDay(todayCorrect)
        val estimatedAccuracy = if (estimatedAttempted > 0) {
            (estimatedCorrect * 100) / estimatedAttempted
        } else {
            0
        }

        txtBigAccuracy?.text = "$overallAccuracyFromServer%"
        txtOverallStats?.text = "Overall: $overallCorrect correct / $overallAttempted attempted"
        txtTodayStats?.text = "Today: $todayCorrect correct / $todayAttempted attempted • Accuracy $todayAccuracy%"
        txtStatus?.text = "$name • Accuracy loaded"
        txtPeriodStats?.text = "Estimated end of day: $estimatedCorrect correct / $estimatedAttempted attempted • Accuracy $estimatedAccuracy%"

    }


    private fun renderTrend(days: Int, title: String) {
        val statsList = DailyStatsManager.getGraphData(this, days)

        if (statsList.isEmpty()) {
            txtPeriodStats?.text = "$title • No history yet"
            clearChart()
            return
        }

        txtPeriodStats?.text = "$title • Showing trend"

        setupChart(
            labels = statsList.map { it.first },
            values = statsList.map { it.second.toFloat() },
            chartTitle = "$title accuracy trend"
        )
    }

    private fun renderTopicWise() {
        val topicMap = DailyStatsManager.getTodayTopicWise(this)

        if (topicMap.isEmpty()) {
            txtPeriodStats?.text = "Topics • No topic data yet"
            clearChart()
            return
        }

        val items = topicMap.map { entry ->
            val topic = entry.key
            val attempted = entry.value.first
            val correct = entry.value.second
            val accuracy = DailyStatsManager.calculateAccuracy(attempted, correct)
            Triple(topic, attempted, accuracy)
        }.sortedByDescending { it.third }

        val totalAttempted = items.sumOf { it.second }
        val totalCorrect = items.sumOf { DailyStatsManager.calculateAccuracy(it.second, it.third) * it.second / 100 }
        val overallTopicAccuracy = if (totalAttempted > 0) {
            (items.sumOf { it.third * it.second } / totalAttempted)
        } else {
            0
        }

        val summary = StringBuilder()
        for ((topic, attempted, accuracy) in items) {
            val correct = if (attempted > 0) (attempted * accuracy) / 100 else 0
            summary.append("$topic: $correct/$attempted • $accuracy%\n")
        }

        txtPeriodStats?.text = "Topics • Overall today $overallTopicAccuracy%"
        txtTodayStats?.text = summary.toString().trim()

        setupChart(
            labels = items.map { it.first },
            values = items.map { it.third.toFloat() },
            chartTitle = "Topic-wise accuracy"
        )
    }

    private fun setupChart(labels: List<String>, values: List<Float>, chartTitle: String) {
        val chart = lineChart ?: return

        val entries = ArrayList<Entry>()
        for (i in values.indices) {
            entries.add(Entry(i.toFloat(), values[i]))
        }

        val accentColor = Color.parseColor("#00E5FF")
        val dataSet = LineDataSet(entries, chartTitle).apply {
            color = accentColor
            setCircleColor(Color.WHITE)
            circleRadius = 5f
            circleHoleRadius = 3f
            setDrawCircleHole(true)
            lineWidth = 3f
            
            // Neon Glow
            setDrawFilled(true)
            fillDrawable = ContextCompat.getDrawable(this@AccuracyActivity, R.drawable.bg_chart_gradient)
            
            setDrawValues(false) // Use Marker instead
            mode = LineDataSet.Mode.CUBIC_BEZIER
            
            // Highlighting
            highlightLineWidth = 2f
            highLightColor = Color.WHITE
            setDrawHorizontalHighlightIndicator(false)
        }

        chart.data = LineData(dataSet)

        chart.description = Description().apply { text = "" }

        chart.axisRight.isEnabled = false
        chart.legend.apply {
            isEnabled = true
            textColor = Color.WHITE
            textSize = 12f
            form = Legend.LegendForm.CIRCLE
        }
        
        chart.setDrawGridBackground(false)
        chart.setTouchEnabled(true)
        chart.isDragEnabled = true
        chart.isScaleXEnabled = true
        chart.isScaleYEnabled = true
        chart.setScaleEnabled(true)
        chart.setPinchZoom(true)
        
        // Pinning logic via Marker
        val marker = CustomMarkerView(this, R.layout.layout_chart_marker)
        marker.chartView = chart
        chart.marker = marker
        
        chart.animateXY(800, 800)

        chart.xAxis.apply {
            position = XAxis.XAxisPosition.BOTTOM
            granularity = 1f
            setDrawGridLines(false)
            textColor = Color.LTGRAY
            labelRotationAngle = -45f
            valueFormatter = object : ValueFormatter() {
                override fun getFormattedValue(value: Float): String {
                    val index = value.toInt()
                    return if (index in labels.indices) labels[index] else ""
                }
            }
        }

        chart.axisLeft.apply {
            axisMinimum = 0f
            axisMaximum = 100f
            setDrawGridLines(true)
            gridColor = Color.parseColor("#1A1F38")
            gridLineWidth = 1f
            textColor = Color.LTGRAY
            valueFormatter = object : ValueFormatter() {
                override fun getFormattedValue(value: Float): String {
                    return "${value.toInt()}%"
                }
            }
        }

        chart.invalidate()
    }

    private fun clearChart() {
        lineChart?.clear()
        lineChart?.invalidate()
    }

    private fun estimateEndOfDay(currentCount: Int): Int {
        if (currentCount <= 0) return 0

        val now = java.util.Calendar.getInstance()
        val minutesPassed = now.get(java.util.Calendar.HOUR_OF_DAY) * 60 + now.get(java.util.Calendar.MINUTE)

        val safeMinutes = minutesPassed.coerceAtLeast(60)
        val fractionOfDay = safeMinutes / (24f * 60f)

        return (currentCount / fractionOfDay).toInt()
    }

    class CustomMarkerView(context: Context, layoutResource: Int) : MarkerView(context, layoutResource) {
        private val tvContent: TextView = findViewById(R.id.tvContent)

        override fun refreshContent(e: Entry, highlight: Highlight) {
            tvContent.text = "${e.y.toInt()}%"
            super.refreshContent(e, highlight)
        }

        override fun getOffset(): MPPointF {
            return MPPointF(-(width / 2).toFloat(), -height.toFloat())
        }
    }
}