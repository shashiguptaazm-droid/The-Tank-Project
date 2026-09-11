package com.rankwarz.edulabsrtm

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.ListView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import org.json.JSONObject

data class SearchItem(
    val subject: String,
    val topic: String
) {
    override fun toString(): String {
        return "$subject → $topic"
    }
}

class TopicSelector : AppCompatActivity() {

    private lateinit var searchInput: EditText
    private lateinit var listView: ListView

    private val list = ArrayList<SearchItem>()
    private lateinit var adapter: ArrayAdapter<SearchItem>

    private val handler = Handler(Looper.getMainLooper())
    private var runnable: Runnable? = null

    private val BASE_URL = "https://medigyaan.xyz/Neurons/api/topicsearch.php"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_topicsearch)

        searchInput = findViewById(R.id.searchInput)
        listView = findViewById(R.id.searchList)

        adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, list)
        listView.adapter = adapter

        searchInput.addTextChangedListener(object : TextWatcher {
            override fun afterTextChanged(s: Editable?) {}

            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}

            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                runnable?.let { handler.removeCallbacks(it) }

                runnable = Runnable {
                    val query = s.toString().trim()
                    if (query.length >= 2) {
                        search(query)
                    } else {
                        list.clear()
                        adapter.notifyDataSetChanged()
                    }
                }
                handler.postDelayed(runnable!!, 400)
            }
        })

        listView.setOnItemClickListener { _, _, position, _ ->
            val item = list[position]
            showModeDialog(item)
        }
    }

    private fun showModeDialog(item: SearchItem) {
        val modes = arrayOf("Matchmaking", "Challenge Mode", "Practice Mode")

        AlertDialog.Builder(this)
            .setTitle("${item.subject} → ${item.topic}")
            .setItems(modes) { _, which ->
                when (which) {
                    0 -> openClassicGame(item)
                    1 -> openChallengeSelection(item)
                    2 -> openPracticeMode(item)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun openClassicGame(item: SearchItem) {
        val intent = Intent(this, ClassicGameActivity::class.java).apply {
            putExtra("SUBJECT", item.subject)
            putExtra("TOPIC", item.topic)
            putExtra("MODE", "MATCHMAKING")
        }
        startActivity(intent)
    }

    private fun openChallengeSelection(item: SearchItem) {
        val intent = Intent(this, TopicChallengeSelectionActivity::class.java).apply {
            putExtra("SUBJECT", item.subject)
            putExtra("TOPIC", item.topic)
            putExtra("MODE", "CHALLENGE")
        }
        startActivity(intent)
    }

    private fun openPracticeMode(item: SearchItem) {
        val intent = Intent(this, MCQActivity::class.java).apply {
            putExtra("SUBJECT", item.subject)
            putExtra("TOPIC", item.topic)
            putExtra("MODE", "PRACTICE")
        }
        startActivity(intent)
    }

    private fun search(query: String) {
        val url = "$BASE_URL?q=${query.replace(" ", "%20")}"
        val cacheKey = "GET:$url"

        fun applySearchResponse(response: String, showErrors: Boolean) {
            try {
                val json = JSONObject(response)

                if (json.getBoolean("success")) {
                    val arr = json.getJSONArray("data")

                    list.clear()

                    for (i in 0 until arr.length()) {
                        val obj = arr.getJSONObject(i)
                        list.add(
                            SearchItem(
                                obj.getString("subject"),
                                obj.getString("topic")
                            )
                        )
                    }

                    adapter.notifyDataSetChanged()
                } else {
                    list.clear()
                    adapter.notifyDataSetChanged()
                }
            } catch (e: Exception) {
                e.printStackTrace()
                if (showErrors) Toast.makeText(this, "Invalid server response", Toast.LENGTH_SHORT).show()
            }
        }

        FirebaseOnlineCache.getString(cacheKey, 24 * 60 * 60 * 1000L) { cached ->
            cached?.let { applySearchResponse(it, showErrors = false) }
        }

        val request = StringRequest(Request.Method.GET, url, { response ->
            FirebaseOnlineCache.putString(cacheKey, response)
            applySearchResponse(response, showErrors = true)
        }, {
            Toast.makeText(this, "Error fetching data", Toast.LENGTH_SHORT).show()
        })

        Volley.newRequestQueue(this).add(request)
    }
}
