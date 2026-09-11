package com.rankwarz.edulabsrtm

import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.Spinner
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.Volley
import org.json.JSONObject

/**
 * Support ticket form. Submits a ticket to support_ticket.php which stores it in the
 * `support_tickets` table (separate from question reports) for review in phpMyAdmin.
 */
class SupportActivity : AppCompatActivity() {

    private lateinit var etName: EditText
    private lateinit var etEmail: EditText
    private lateinit var etSubject: EditText
    private lateinit var etMessage: EditText
    private lateinit var spCategory: Spinner
    private lateinit var btnSubmit: Button
    private lateinit var loader: ProgressBar

    private val userId: Int by lazy {
        getSharedPreferences("MY_APP", MODE_PRIVATE).getInt("user_id", 0)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_support)

        etName = findViewById(R.id.etSupportName)
        etEmail = findViewById(R.id.etSupportEmail)
        etSubject = findViewById(R.id.etSupportSubject)
        etMessage = findViewById(R.id.etSupportMessage)
        spCategory = findViewById(R.id.spSupportCategory)
        btnSubmit = findViewById(R.id.btnSubmitTicket)
        loader = findViewById(R.id.supportLoader)

        val prefs = getSharedPreferences("MY_APP", MODE_PRIVATE)
        etName.setText(prefs.getString("name", ""))

        spCategory.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            listOf("General", "App bug", "Wrong question content", "Payment / Rank", "Feature request", "Other")
        )

        btnSubmit.setOnClickListener { submitTicket() }
    }

    private fun submitTicket() {
        val name = etName.text.toString().trim()
        val email = etEmail.text.toString().trim()
        val subject = etSubject.text.toString().trim()
        val message = etMessage.text.toString().trim()
        val category = spCategory.selectedItem?.toString() ?: "General"

        if (name.isEmpty() || message.isEmpty()) {
            Toast.makeText(this, "Name and message are required", Toast.LENGTH_SHORT).show()
            return
        }

        btnSubmit.isEnabled = false
        loader.visibility = View.VISIBLE

        val body = JSONObject().apply {
            put("user_id", userId)
            put("name", name)
            put("email", email)
            put("category", category)
            put("subject", subject.ifEmpty { "(no subject)" })
            put("message", message)
        }

        val request = object : JsonObjectRequest(
            Request.Method.POST, "https://medigyaan.xyz/Neurons/api/support_ticket.php", body,
            { response ->
                btnSubmit.isEnabled = true
                loader.visibility = View.GONE
                if (response.optBoolean("success")) {
                    Toast.makeText(this, "Ticket #${response.optInt("ticket_id")} submitted. We'll get back to you!", Toast.LENGTH_LONG).show()
                    etSubject.setText("")
                    etMessage.setText("")
                    finish()
                } else {
                    Toast.makeText(this, response.optString("error", "Could not submit ticket"), Toast.LENGTH_LONG).show()
                }
            },
            { error ->
                btnSubmit.isEnabled = true
                loader.visibility = View.GONE
                Toast.makeText(this, "Network error — please try again", Toast.LENGTH_LONG).show()
            }
        ) {
            override fun getHeaders(): MutableMap<String, String> {
                return hashMapOf(
                    "Content-Type" to "application/json",
                    "X-App-Signature" to "EduLabsRTM_Secure_v1_2026"
                )
            }
        }
        request.retryPolicy = DefaultRetryPolicy(15000, 1, 1f)
        Volley.newRequestQueue(this).add(request)
    }
}
