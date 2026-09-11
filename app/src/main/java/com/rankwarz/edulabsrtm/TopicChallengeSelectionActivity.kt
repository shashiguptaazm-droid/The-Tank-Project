package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.widget.SearchView
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.FirebaseDatabase
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder
import kotlin.math.abs

class TopicChallengeSelectionActivity : BaseActivity() {

    companion object {
        const val MODE_MATCHMAKING = "MATCHMAKING"
        const val MODE_FRIENDS = "FRIENDS"
        private const val TAG = "TOPIC_CHALLENGE"
        private const val PREF_NAME = "MY_APP"
        private const val KEY_FOLLOW_PREFIX = "follow_status_"
        private const val KEY_USER_ID = "user_id"
    }

    private lateinit var searchView: SearchView
    private lateinit var recyclerView: RecyclerView
    private lateinit var btnStart: Button
    private lateinit var toolbarTitle: TextView
    private lateinit var toolbarSubtitle: TextView
    private val userList = mutableListOf<UserItem>()
    private val selectedUserIds = mutableSetOf<String>()
    private lateinit var adapter: ChallengeUserAdapter

    private var selectedSubject = ""
    private var selectedTopic = ""
    private var testUniqueId = 0

    private var quizType = ""
    private var userId = 0
    private var userName = "You"

    private var mode = MODE_FRIENDS
    private var isMatchmakingMode = false

    private var quizId = 0

    private val ROOT_URL = "https://medigyaan.xyz/Neurons/"
    private val BASE_URL = "https://medigyaan.xyz/Neurons/"

    private val requestQueue by lazy { Volley.newRequestQueue(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_challenge_selection)
        toolbarTitle = findViewById(R.id.toolbarTitle)
        toolbarSubtitle = findViewById(R.id.toolbarSubtitle)

        val prefs = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        userId = prefs.getInt(KEY_USER_ID, 0)
        userName = prefs.getString("name", "You") ?: "You"

        testUniqueId = intent.getIntExtra("UNIQUE_ID", 0)
        selectedSubject = intent.getStringExtra("SUBJECT")
            ?: intent.getStringExtra("SELECTED_SUBJECT")
            ?: prefs.getString("selected_subject_preference", "")
            ?: ""
        selectedTopic = intent.getStringExtra("TOPIC") 
            ?: intent.getStringExtra("SELECTED_TOPIC")
            ?: ""

        quizType = intent.getStringExtra("QUIZ_TYPE") ?: "CUSTOM"
        mode = intent.getStringExtra("MODE") ?: MODE_FRIENDS
        isMatchmakingMode = mode == MODE_MATCHMAKING

        searchView = findViewById(R.id.searchView)
        recyclerView = findViewById(R.id.userRecyclerView)
        btnStart = findViewById(R.id.btnStartChallenge)
        setupAppBottomNavigation(findViewById<BottomNavigationView>(R.id.bottomNavigation), R.id.nav_home)

        quizId = generateQuizId()

        btnStart.isEnabled = true
        btnStart.alpha = 1f

        if (selectedSubject.isBlank()) {
            Toast.makeText(this, "Invalid subject", Toast.LENGTH_SHORT).show()
            finish()
        } else {
            ensureFirebaseAuth {
                setupRecyclerView()
                setupUi()

                if (!isMatchmakingMode) {
                    setupSearch()
                    loadSavedCloseFriends()
                }

                btnStart.setOnClickListener {
                    if (btnStart.isEnabled) {
                        if (isMatchmakingMode) {
                            startMatchmaking()
                        } else {
                            if (selectedUserIds.isEmpty()) {
                                Toast.makeText(this, "Select users", Toast.LENGTH_SHORT).show()
                            } else {
                                sendFriendChallenge()
                            }
                        }
                    }
                }
            }
        }
    }

    private fun ensureFirebaseAuth(onReady: () -> Unit) {
        val current = FirebaseAuth.getInstance().currentUser
        if (current != null) {
            onReady()
        } else {
            FirebaseAuth.getInstance().signInAnonymously()
                .addOnSuccessListener { onReady() }
                .addOnFailureListener { e ->
                    Toast.makeText(this, "Auth failed", Toast.LENGTH_SHORT).show()
                    finish()
                }
        }
    }

    private fun setupUi() {
        toolbarTitle.text = if (isMatchmakingMode) "Find Match" else "Challenge Friends"
        toolbarSubtitle.text = when {
            testUniqueId > 0 -> "Test ID: $testUniqueId"
            selectedTopic.isNotBlank() -> "Topic: $selectedTopic"
            else -> "Subject: $selectedSubject"
        }

        if (isMatchmakingMode) {
            searchView.visibility = View.GONE
            recyclerView.visibility = View.GONE
            btnStart.text = "Find Match"
        } else {
            searchView.visibility = View.VISIBLE
            recyclerView.visibility = View.VISIBLE
            btnStart.text = "Send Challenge"
        }
    }

    private fun setupSearch() {
        searchView.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                val q = query?.trim().orEmpty()
                if (q.isNotEmpty()) {
                    searchView.clearFocus()
                    fetchUsers(q)
                }
                return true
            }

            override fun onQueryTextChange(newText: String?): Boolean = false
        })
    }

    private fun setupRecyclerView() {
        adapter = ChallengeUserAdapter(userList) { id, selected ->
            if (selected) selectedUserIds.add(id) else selectedUserIds.remove(id)
            btnStart.text = if (isMatchmakingMode) "Find Match" else "Send (${selectedUserIds.size})"
        }
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = adapter
    }

    private fun loadSavedCloseFriends() {
        if (isMatchmakingMode) return

        Log.d(TAG, "loadSavedCloseFriends() -> API + profile mode")

        userList.clear()
        selectedUserIds.clear()
        adapter.notifyDataSetChanged()

        toolbarTitle.text = "Loading..."
        toolbarSubtitle.text = "Fetching followers"

        val url = "$BASE_URL/messenger_api.php?get_connections&user_id=$userId"
        val cacheKey = "GET:$url"
        FirebaseOnlineCache.getString(cacheKey, 10 * 60 * 1000L) { cached ->
            cached?.let { applyConnectionsResponse(it, showEmptyToast = false) }
        }

        val request = object : StringRequest(
            Method.GET, url,
            { response ->
                FirebaseOnlineCache.putString(cacheKey, response)
                applyConnectionsResponse(response, showEmptyToast = true)
            },
            { error ->
                toolbarTitle.text = "Network Error"
                toolbarSubtitle.text = "Check connection"
                Log.e(TAG, "API error", error)
            }
        ) {
            override fun getHeaders(): MutableMap<String, String> {
                return hashMapOf("X-App-Signature" to "EduLabsRTM_Secure_v1_2026", "Accept" to "application/json")
            }
        }

        requestQueue.add(request)
    }

    /**
     * Applies the server connections response (messenger get_connections — the same
     * server-driven followed-user list the Messenger uses). Names and photos come ready,
     * so no placeholder rows or per-user profile fetches are needed.
     */
    private fun applyConnectionsResponse(response: String, showEmptyToast: Boolean) {
        try {
            val array = JSONArray(response)
            userList.clear()
            selectedUserIds.clear()
            for (i in 0 until array.length()) {
                val obj = array.getJSONObject(i)
                val id = obj.optString("user_id", "")
                if (id.isBlank() || id == userId.toString()) continue

                var photo = obj.optString("photo", "")
                if (photo.isBlank() || photo.equals("null", true)) photo = ""
                if (photo.isNotEmpty() && !photo.startsWith("http")) {
                    photo = BASE_URL + photo.removePrefix("./").trimStart('/')
                }

                userList.add(
                    UserItem(
                        id = id,
                        name = obj.optString("name", "User $id").ifBlank { "User $id" },
                        photo = photo,
                        isCloseFriend = true
                    )
                )
            }

            adapter.notifyDataSetChanged()
            btnStart.text = "Send (${selectedUserIds.size})"
            toolbarTitle.text = if (userList.isEmpty()) "No Friends" else "Select Friends"
            toolbarSubtitle.text =
                if (userList.isEmpty()) "No connections yet — follow players to chat" else "${userList.size} connections"

            if (userList.isEmpty() && showEmptyToast) {
                Toast.makeText(this, "No connections yet — follow players to chat", Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Connections parse error", e)
            toolbarTitle.text = "Error"
            toolbarSubtitle.text = "Parsing failed"
        }
    }



    private fun fetchUsers(keyword: String) {
        val encodedKeyword = try {
            URLEncoder.encode(keyword, "UTF-8")
        } catch (_: Exception) {
            keyword
        }

        val url = "${ROOT_URL}api/searchv2.php?keyword=$encodedKeyword&type=json"
        Log.d(TAG, "fetchUsers -> $url")

        val req = object : StringRequest(
            Request.Method.GET,
            url,
            { res ->
                try {
                    Log.d(TAG, "fetchUsers raw response -> $res")

                    val json = JSONObject(res)

                    userList.clear()
                    selectedUserIds.clear()

                    if (json.optString("status") == "success") {

                        val results = json.optJSONObject("results")
                        val arr = results?.optJSONArray("users")

                        if (arr != null && arr.length() > 0) {

                            for (i in 0 until arr.length()) {
                                val u = arr.getJSONObject(i)

                                val id = u.optString("user_id", "")
                                if (id.isBlank() || id == userId.toString()) continue

                                val name = u.optString("name", "User")

                                var photo = u.optString("photo", "")
                                if (photo.isBlank() || photo.equals("null", true)) {
                                    photo = ""
                                }
                                if (photo.isNotEmpty() && !photo.startsWith("http")) {
                                    photo = ROOT_URL + photo
                                }

                                Log.d(TAG, "USER -> id=$id name=$name photo=$photo")

                                userList.add(
                                    UserItem(
                                        id = id,
                                        name = name,
                                        photo = photo,
                                        isCloseFriend = false
                                    )
                                )
                            }

                        } else {
                            Log.e(TAG, "No users array")
                            Toast.makeText(this, "No users found", Toast.LENGTH_SHORT).show()
                        }

                    } else {
                        Toast.makeText(this, "No users", Toast.LENGTH_SHORT).show()
                    }

                    adapter.notifyDataSetChanged()
                    btnStart.text = "Send (${selectedUserIds.size})"

                    Log.d(TAG, "fetchUsers -> loaded ${userList.size} users")

                } catch (e: Exception) {
                    Log.e(TAG, "SEARCH_ERROR: ${e.message}", e)
                    Toast.makeText(this, "Search parse error", Toast.LENGTH_SHORT).show()
                }
            },
            { err ->
                Log.e(TAG, "Search failed: ${err.message}", err)
                Toast.makeText(this, "Search failed", Toast.LENGTH_SHORT).show()
            }
        ) {
            override fun getHeaders(): MutableMap<String, String> {
                val headers = HashMap<String, String>()
                headers["User-Agent"] = "EduLabs_Android_App"
                headers["X-App-Signature"] = "EduLabsRTM_Secure_v1_2026"
                return headers
            }
        }

        req.retryPolicy = DefaultRetryPolicy(10000, 2, 1.0f)
        requestQueue.add(req)
    }

    private fun startMatchmaking() {
        btnStart.isEnabled = false
        btnStart.alpha = 0.6f
        val ref = FirebaseDatabase.getInstance().reference.child("lobbies")
        ref.orderByChild("status").equalTo("waiting").get().addOnSuccessListener { snap ->
            var lobby: DataSnapshot? = null
            for (l in snap.children) {
                val sub = l.child("subject").value?.toString() ?: ""
                val top = l.child("topic").value?.toString() ?: ""
                if (l.child("players").childrenCount < 2 && sub == selectedSubject && top == selectedTopic) {
                    lobby = l
                    break
                }
            }
            if (lobby != null) joinLobby(lobby) else createLobby("lobby_${System.currentTimeMillis()}", true)
        }.addOnFailureListener {
            btnStart.isEnabled = true
            btnStart.alpha = 1f
        }
    }

    private fun joinLobby(lobby: DataSnapshot) {
        val lobbyId = lobby.key ?: return
        val ref = FirebaseDatabase.getInstance().reference.child("lobbies").child(lobbyId)
        ref.child("players").child(userId.toString())
            .setValue(mapOf("name" to userName, "status" to "ready"))
            .addOnSuccessListener { openLobby(lobbyId) }
    }

    private fun sendFriendChallenge() {

        btnStart.isEnabled = false
        btnStart.alpha = 0.6f

        val url = "${ROOT_URL}initiate_challenge.php"

        val req = object : StringRequest(Request.Method.POST, url,
            { res ->
                try {
                    val json = JSONObject(res)

                    val challengeId = json.optInt("challenge_id", 0)

                    if (json.optBoolean("success") && challengeId > 0) {

                        val lobbyId = "lobby_$challengeId"

                        // ✅ 1. CREATE LOBBY
                        createLobby(lobbyId, true, challengeId)

                        // ✅ 2. GENERATE INVITE LINK (VERY IMPORTANT)
                        val inviteLink =
                            "https://medigyaan.xyz/Neurons/livebattle.php?challenge_id=$challengeId"

                        // ✅ 3. SHARE INTENT
                        val shareText = """
🔥 Challenge Invite!

$userName has invited you to a live quiz battle ⚔️

👉 Join here:
$inviteLink

📲 Open in app for best experience
                    """.trimIndent()

                        val intent = Intent(Intent.ACTION_SEND)
                        intent.type = "text/plain"
                        intent.putExtra(Intent.EXTRA_TEXT, shareText)

                        startActivity(Intent.createChooser(intent, "Invite via"))

                    } else {
                        Toast.makeText(this, "Failed to create challenge", Toast.LENGTH_SHORT).show()
                        btnStart.isEnabled = true
                        btnStart.alpha = 1f
                    }

                } catch (e: Exception) {
                    e.printStackTrace()
                    btnStart.isEnabled = true
                    btnStart.alpha = 1f
                }
            },
            { error ->
                error.printStackTrace()
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
                btnStart.isEnabled = true
                btnStart.alpha = 1f
            }
        ) {

            override fun getParams(): MutableMap<String, String> = hashMapOf(
                "creator_id" to userId.toString(),
                "quiz_id" to quizId.toString(),
                "quiz_type" to quizType,
                "opponent_ids" to selectedUserIds.joinToString(",")
            )

            override fun getHeaders(): MutableMap<String, String> =
                hashMapOf("X-App-Signature" to "EduLabsRTM_Secure_v1_2026")
        }

        req.retryPolicy = DefaultRetryPolicy(10000, 2, 1.0f)
        requestQueue.add(req)
    }

    private fun createLobby(lobbyId: String, isHost: Boolean, challengeId: Int = generateChallengeId()) {
        val ref = FirebaseDatabase.getInstance().reference.child("lobbies").child(lobbyId)
        val data = mapOf(
            "status" to "waiting",
            "host_id" to userId.toString(),
            "challenge_id" to challengeId,
            "subject" to selectedSubject,
            "topic" to selectedTopic,
            "quiz_type" to quizType,
            "quiz_id" to quizId
        )
        ref.setValue(data).addOnSuccessListener {
            ref.child("players").child(userId.toString())
                .setValue(mapOf("name" to userName, "status" to "ready"))
                .addOnSuccessListener { openLobby(lobbyId) }
        }
    }

    private fun openLobby(lobbyId: String) {
        startActivity(Intent(this, TopicLobbyActivity::class.java).apply {
            putExtra("lobby_id", lobbyId)
            putExtra("SUBJECT", selectedSubject)
            putExtra("SELECTED_SUBJECT", selectedSubject)
            putExtra("TOPIC", selectedTopic)
            putExtra("SELECTED_TOPIC", selectedTopic)
            putExtra("user_id", userId.toString())
            putExtra("user_name", userName)
            putExtra("QUIZ_TYPE", quizType)
            putExtra("mode", mode)
        })
        finish()
    }

    private fun generateQuizId(): Int {
        if (testUniqueId > 0) return testUniqueId
        return abs((selectedSubject.trim() + "_" + selectedTopic.trim()).hashCode()).let { if (it == 0) 1 else it }
    }

    private fun generateChallengeId(): Int =
        ((System.currentTimeMillis() % 900000L) + 100000L).toInt()

}
