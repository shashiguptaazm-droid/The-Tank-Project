package com.rankwarz.edulabsrtm

import AttemptAdapter
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.Volley

class QuestionAttemptsActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: AttemptAdapter
    private val list = ArrayList<AttemptModel>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_attempts)

        val questionId = intent.getIntExtra("question_id", 0)
        val userId = "YOUR_USER_ID"

        recyclerView = findViewById(R.id.recyclerView)
        recyclerView.layoutManager = LinearLayoutManager(this)

        adapter = AttemptAdapter(list)
        recyclerView.adapter = adapter

        loadAttempts(questionId, userId)
    }

    private fun loadAttempts(questionId: Int, userId: String) {
        val url = "https://medigyaan.xyz/Neurons/attempts_api.php?question_id=$questionId&user_id=$userId"

        val request = JsonObjectRequest(
            Request.Method.GET, url, null,
            { response ->
                val arr = response.getJSONArray("attempts")
                list.clear()

                for (i in 0 until arr.length()) {
                    val obj = arr.getJSONObject(i)

                    list.add(
                        AttemptModel(
                            obj.getString("temporary_user_id"),
                            obj.getString("user_answer"),
                            obj.getInt("is_correct"),
                            obj.getString("name"),
                            obj.getString("created_at")
                        )
                    )
                }

                adapter.notifyDataSetChanged()
            },
            {
                Toast.makeText(this, "Error loading attempts", Toast.LENGTH_SHORT).show()
            })

        Volley.newRequestQueue(this).add(request)
    }
}