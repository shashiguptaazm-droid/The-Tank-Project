package com.rankwarz.edulabsrtm

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.google.android.material.button.MaterialButton
import com.google.firebase.Firebase
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import com.google.firebase.auth.auth
import com.google.firebase.messaging.FirebaseMessaging
import org.json.JSONObject

class LoginActivity : AppCompatActivity() {

    private lateinit var auth: FirebaseAuth
    private lateinit var googleSignInClient: GoogleSignInClient
    private lateinit var emailField: EditText
    private lateinit var passwordField: EditText
    private lateinit var loginBtn: Button
    private lateinit var progressBar: ProgressBar
    private lateinit var googleSignInBtn: MaterialButton
    private lateinit var registerBtn: TextView
    private lateinit var forgotPasswordBtn: TextView
    private lateinit var prefs: SharedPreferences

    private val RC_SIGN_IN = 9001
    private val TAG = "EduLabs_Auth"
    private val FCM_TAG = "FCM_DEBUG"

    private var pendingAfterPermissionAction: (() -> Unit)? = null

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            Log.d(TAG, "POST_NOTIFICATIONS granted = $granted")
            pendingAfterPermissionAction?.invoke()
            pendingAfterPermissionAction = null
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        auth = Firebase.auth
        emailField = findViewById(R.id.email)
        passwordField = findViewById(R.id.password)
        loginBtn = findViewById(R.id.loginBtn)
        progressBar = findViewById(R.id.progressBar)
        googleSignInBtn = findViewById(R.id.googleSignInBtn)
        registerBtn = findViewById(R.id.registerBtn)
        forgotPasswordBtn = findViewById(R.id.forgotPasswordBtn)
        prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)

        val webClientId = "556329611895-27u1fj7bn16leb87k24ul71hg48j20rv.apps.googleusercontent.com"
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(webClientId)
            .requestEmail()
            .build()

        googleSignInClient = GoogleSignIn.getClient(this, gso)

        loginBtn.setOnClickListener { manualLogin() }

        googleSignInBtn.setOnClickListener {
            requestNotificationPermissionThen {
                startGoogleSignIn()
            }
        }

        registerBtn.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
        }

        forgotPasswordBtn.setOnClickListener {
            startActivity(Intent(this, ForgotPasswordActivity::class.java))
        }

        // Auto-login without forcing permission popup
        if (prefs.getInt("user_id", 0) != 0) {
            val savedId = prefs.getInt("user_id", 0)
            if (savedId != 0) {
                syncFcmToken(savedId)
            }
            navigateToDashboard()
        }
    }

    private fun startGoogleSignIn() {
        progressBar.visibility = View.VISIBLE
        googleSignInClient.signOut().addOnCompleteListener {
            startActivityForResult(googleSignInClient.signInIntent, RC_SIGN_IN)
        }
    }

    private fun requestNotificationPermissionThen(next: () -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            next()
            return
        }

        val permission = Manifest.permission.POST_NOTIFICATIONS

        val granted = ContextCompat.checkSelfPermission(
            this,
            permission
        ) == PackageManager.PERMISSION_GRANTED

        if (granted) {
            next()
            return
        }

        // Ask normally. Do not jump to settings on first request.
        pendingAfterPermissionAction = next
        notificationPermissionLauncher.launch(permission)
    }

    private fun syncFcmToken(userId: Int) {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Log.w(FCM_TAG, "Fetching FCM registration token failed", task.exception)
                return@addOnCompleteListener
            }

            val token = task.result
            Log.d(FCM_TAG, "Fetched Token: $token")

            val url = "https://medigyaan.xyz/Neurons/api/update_fcmv2.php"

            val request = object : StringRequest(Method.POST, url,
                { response ->
                    Log.d(FCM_TAG, "FCM Token synced to MySQL successfully: $response")
                },
                { error ->
                    Log.e(FCM_TAG, "FCM Sync Failed: ${error.message}")
                }) {

                override fun getParams(): MutableMap<String, String> {
                    val params = HashMap<String, String>()
                    params["user_id"] = userId.toString()
                    params["fcm_token"] = token ?: ""
                    return params
                }
            }

            request.retryPolicy = DefaultRetryPolicy(10000, 1, 1.0f)
            Volley.newRequestQueue(this).add(request)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == RC_SIGN_IN) {
            val task = GoogleSignIn.getSignedInAccountFromIntent(data)
            try {
                val account = task.getResult(ApiException::class.java)!!
                firebaseAuthWithGoogle(account.idToken!!)
            } catch (e: ApiException) {
                progressBar.visibility = View.GONE
                Log.e(TAG, "Google sign in failed: ${e.statusCode}")
                Toast.makeText(this, "Google sign-in failed", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun firebaseAuthWithGoogle(idToken: String) {
        val credential = GoogleAuthProvider.getCredential(idToken, null)
        auth.signInWithCredential(credential)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    syncUserWithBackend(user?.uid, user?.email, user?.displayName)
                } else {
                    progressBar.visibility = View.GONE
                    Toast.makeText(this, "Google login failed", Toast.LENGTH_SHORT).show()
                }
            }
    }

    private fun syncUserWithBackend(fUid: String?, email: String?, name: String?) {
        val url = "https://medigyaan.xyz/Neurons/google-callback.php"
        val jsonBody = JSONObject().apply {
            put("firebase_uid", fUid)
            put("email", email)
            put("name", name)
        }

        val request = JsonObjectRequest(
            Request.Method.POST,
            url,
            jsonBody,
            { response ->
                progressBar.visibility = View.GONE
                if (response.optBoolean("success")) {
                    val userId = response.optInt("user_id")
                    saveUserSession(userId, name ?: "", email ?: "")
                    syncFcmToken(userId)
                    navigateToDashboard()
                } else {
                    Toast.makeText(this, "Backend sync failed", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                progressBar.visibility = View.GONE
                val errorMsg = if (error.networkResponse != null) {
                    "Status: ${error.networkResponse.statusCode}, Data: ${String(error.networkResponse.data)}"
                } else {
                    error.toString()
                }
                Log.e(TAG, "Google backend sync failed: $errorMsg")
                Toast.makeText(this, "Google login failed: ${error.javaClass.simpleName}", Toast.LENGTH_SHORT).show()
            }
        )

        Volley.newRequestQueue(this).add(request)
    }

    private fun manualLogin() {
        val email = emailField.text.toString().trim()
        val pass = passwordField.text.toString().trim()

        if (email.isEmpty()) {
            emailField.error = "Enter email"
            return
        }

        if (pass.isEmpty()) {
            passwordField.error = "Enter password"
            return
        }

        progressBar.visibility = View.VISIBLE

        val url = "https://medigyaan.xyz/Neurons/api/login.php"
        val jsonBody = JSONObject().apply {
            put("email", email)
            put("password", pass)
        }

        val request = JsonObjectRequest(
            Request.Method.POST,
            url,
            jsonBody,
            { response ->
                progressBar.visibility = View.GONE
                if (response.optBoolean("success")) {
                    val userId = response.optInt("user_id")
                    val name = response.optString("name")

                    saveUserSession(userId, name, email)
                    syncFcmToken(userId)
                    navigateToDashboard()
                } else {
                    Toast.makeText(this, "Invalid credentials", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                progressBar.visibility = View.GONE
                val errorMsg = if (error.networkResponse != null) {
                    "Status: ${error.networkResponse.statusCode}, Data: ${String(error.networkResponse.data)}"
                } else {
                    error.toString()
                }
                Log.e(TAG, "Login error: $errorMsg")
                Toast.makeText(this, "Login failed: ${error.javaClass.simpleName}", Toast.LENGTH_SHORT).show()
            }
        )

        Volley.newRequestQueue(this).add(request)
    }

    private fun saveUserSession(id: Int, name: String, email: String) {
        prefs.edit()
            .putInt("user_id", id)
            .putString("name", name)
            .putString("email", email)
            .apply()
    }

    private fun navigateToDashboard() {
        startActivity(Intent(this, DashboardActivity::class.java))
        finish()
    }
}