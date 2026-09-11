package com.rankwarz.edulabsrtm

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.Volley
import org.json.JSONArray
import org.json.JSONObject

class QuizManagerActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private val quizList = ArrayList<JSONObject>()

    private val FETCH_API = "https://medigyaan.xyz/Neurons/quiz_apiv2.php"
    private val DELETE_API = "https://medigyaan.xyz/Neurons/delete_quiz_api.php"

    // This matches the PHP script you shared
    private val RESULT_API = "https://medigyaan.xyz/Neurons/participants_api.php"

    private var userId = 0

    companion object {
        private const val TAG = "QUIZ_MANAGER"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_quiz_manager)

        userId = intent.getIntExtra("USER_ID", 0)

        recyclerView = findViewById(R.id.recyclerView)
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = QuizAdapter()

        fetchQuizzes()
    }

    // ---------------- FETCH QUIZZES (Using POST Form Data) ----------------
    private fun fetchQuizzes() {
        val queue = Volley.newRequestQueue(this)

        val request = object : JsonObjectRequest(
            Method.POST, FETCH_API, null,
            { response ->
                if (response.optBoolean("success")) {
                    val arr = response.optJSONArray("quizzes") ?: JSONArray()
                    quizList.clear()
                    for (i in 0 until arr.length()) {
                        quizList.add(arr.getJSONObject(i))
                    }
                    recyclerView.adapter?.notifyDataSetChanged()
                } else {
                    Toast.makeText(this, "No quizzes found", Toast.LENGTH_SHORT).show()
                }
            },
            { error -> Log.e(TAG, "Fetch error: ${error.message}") }
        ) {
            override fun getParams(): Map<String, String> = hashMapOf("user_id" to userId.toString())
        }
        queue.add(request)
    }

    // ---------------- DELETE QUIZ ----------------
    private fun deleteQuiz(quizId: Int) {
        val queue = Volley.newRequestQueue(this)

        val request = object : JsonObjectRequest(
            Method.POST, DELETE_API, null,
            { response ->
                if (response.optBoolean("success")) {
                    Toast.makeText(this, "Deleted", Toast.LENGTH_SHORT).show()
                    fetchQuizzes()
                }
            },
            { Toast.makeText(this, "Delete failed", Toast.LENGTH_SHORT).show() }
        ) {
            override fun getParams(): Map<String, String> = hashMapOf("quiz_id" to quizId.toString())
        }
        queue.add(request)
    }

    // ---------------- SHOW RESULTS (Updated for your PHP) ----------------
    private fun showResults(quizId: Int) {
        val queue = Volley.newRequestQueue(this)

        // We append the quiz_id to the URL since your PHP uses $_GET
        val url = "$RESULT_API?quiz_id=$quizId"

        val request = JsonObjectRequest(
            Request.Method.GET, url, null,
            { response ->
                try {
                    // 1. Check if status is success
                    if (response.optString("status") == "success") {

                        // 2. IMPORTANT: 'data' is a JSONArray according to your error log
                        val dataArray = response.optJSONArray("data")

                        if (dataArray != null && dataArray.length() > 0) {
                            val builder = StringBuilder()

                            // 3. Loop through all participants in the data array
                            for (i in 0 until dataArray.length()) {
                                val participant = dataArray.getJSONObject(i)
                                val name = participant.optString("name")
                                val score = participant.optString("correct_count")
                                val total = participant.optString("total_questions")
                                val percent = participant.optString("percentage")

                                builder.append("👤 Name: $name\n")
                                builder.append("✅ Score: $score/$total ($percent%)\n")
                                builder.append("--------------------------\n")
                            }

                            // 4. Show the results in a Dialog
                            AlertDialog.Builder(this)
                                .setTitle("Quiz Participants")
                                .setMessage(builder.toString())
                                .setPositiveButton("OK", null)
                                .show()
                        } else {
                            Toast.makeText(this, "No participants found", Toast.LENGTH_SHORT).show()
                        }
                    } else {
                        val msg = response.optString("message", "Error loading results")
                        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Parse error: ${e.message}")
                    Toast.makeText(this, "Data parsing error", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                Log.e(TAG, "Volley error: ${error.message}")
                Toast.makeText(this, "Network Error", Toast.LENGTH_SHORT).show()
            }
        )
        queue.add(request)
    }

    private fun shareQuiz(quizId: Int) {
        val link = "https://medigyaan.xyz/Neurons/quiz_share.php?quiz_id=$quizId"
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, "Try my quiz 🔥\n$link")
        }
        startActivity(Intent.createChooser(intent, "Share Quiz"))
    }

    // ---------------- ADAPTER ----------------
    inner class QuizAdapter : RecyclerView.Adapter<QuizAdapter.ViewHolder>() {

        inner class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val txtName: TextView = view.findViewById(R.id.txtQuizName)
            val btnView: Button = view.findViewById(R.id.btnView)
            val btnDelete: Button = view.findViewById(R.id.btnDelete)
            val btnShare: Button = view.findViewById(R.id.btnShare)
            val btnResult: Button = view.findViewById(R.id.btnResult)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_quiz, parent, false)
            return ViewHolder(view)
        }

        override fun getItemCount(): Int = quizList.size

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val quiz = quizList[position]
            val quizId = quiz.optInt("quiz_id")
            val quizName = quiz.optString("quiz_name")

            holder.txtName.text = quizName

            holder.btnView.setOnClickListener {
                startActivity(Intent(this@QuizManagerActivity, QuizViewerActivity::class.java)
                    .putExtra("QUIZ_ID", quizId))
            }

            holder.btnDelete.setOnClickListener {
                AlertDialog.Builder(this@QuizManagerActivity)
                    .setTitle("Delete Quiz")
                    .setMessage("Are you sure?")
                    .setPositiveButton("Yes") { _, _ -> deleteQuiz(quizId) }
                    .setNegativeButton("No", null)
                    .show()
            }

            holder.btnShare.setOnClickListener { shareQuiz(quizId) }
            holder.btnResult.setOnClickListener { showResults(quizId) }
        }
    }
}