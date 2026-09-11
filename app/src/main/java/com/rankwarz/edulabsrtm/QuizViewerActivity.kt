package com.rankwarz.edulabsrtm

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import org.json.JSONArray
import org.json.JSONObject

class QuizViewerActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var emptyText: TextView

    private val questionList = ArrayList<JSONObject>()

    private val API = "https://medigyaan.xyz/Neurons/get_quiz_questions.php"
    private var quizId = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_quiz_viewer)

        quizId = intent.getIntExtra("QUIZ_ID", 0)

        recyclerView = findViewById(R.id.recyclerView)
        emptyText = findViewById(R.id.emptyText)

        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = QuestionAdapter()

        fetchQuestions()
    }

    private fun fetchQuestions() {
        val queue = Volley.newRequestQueue(this)

        val request = object : StringRequest(
            Request.Method.POST,
            API,
            { response ->
                try {
                    Log.d("VIEWER", "raw response = $response")

                    val json = JSONObject(response)

                    if (json.optBoolean("success")) {
                        val arr: JSONArray = json.optJSONArray("questions") ?: JSONArray()

                        questionList.clear()
                        for (i in 0 until arr.length()) {
                            questionList.add(arr.getJSONObject(i))
                        }

                        recyclerView.adapter?.notifyDataSetChanged()

                        if (questionList.isEmpty()) {
                            emptyText.visibility = View.VISIBLE
                            recyclerView.visibility = View.GONE
                        } else {
                            emptyText.visibility = View.GONE
                            recyclerView.visibility = View.VISIBLE
                        }
                    } else {
                        questionList.clear()
                        recyclerView.adapter?.notifyDataSetChanged()
                        emptyText.visibility = View.VISIBLE
                        recyclerView.visibility = View.GONE

                        Toast.makeText(
                            this,
                            json.optString("message", "No questions found"),
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (e: Exception) {
                    Log.e("VIEWER", "Parse error: ${e.message}", e)
                    emptyText.visibility = View.VISIBLE
                    recyclerView.visibility = View.GONE
                    Toast.makeText(this, "Invalid response from server", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                Log.e("VIEWER", "Network error: ${error.message}", error)
                emptyText.visibility = View.VISIBLE
                recyclerView.visibility = View.GONE
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
            }
        ) {
            override fun getParams(): Map<String, String> {
                return hashMapOf("quiz_id" to quizId.toString())
            }
        }

        queue.add(request)
    }

    inner class QuestionAdapter : RecyclerView.Adapter<QuestionAdapter.ViewHolder>() {

        inner class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
            val txtQuestion: TextView = itemView.findViewById(R.id.txtQuestion)
            val txtOptions: TextView = itemView.findViewById(R.id.txtOptions)
            val txtAnswer: TextView = itemView.findViewById(R.id.txtAnswer)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_question_view, parent, false)
            return ViewHolder(view)
        }

        override fun getItemCount(): Int = questionList.size

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val q = questionList[position]

            val question = q.optString("question", "")
            val a = q.optString("option_a", "")
            val b = q.optString("option_b", "")
            val c = q.optString("option_c", "")
            val d = q.optString("option_d", "")
            val correct = q.optString("correct_option", "")

            holder.txtQuestion.text = "${position + 1}. $question"
            holder.txtOptions.text = "A. $a\nB. $b\nC. $c\nD. $d"
            holder.txtAnswer.text = "Correct: $correct"
        }
    }
}