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
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.FirebaseDatabase
import org.json.JSONObject

class ChallengeSelectionActivity : BaseActivity() {

    companion object {
        const val MODE_MATCHMAKING = "MATCHMAKING"
        const val MODE_FRIENDS = "FRIENDS"
        const val TAG = "CHALLENGE_SELECT"
        private const val PREF_NAME = "MY_APP"
        private const val KEY_FOLLOW_PREFIX = "follow_status_"
        private const val KEY_USER_ID = "user_id"
    }

    private lateinit var searchView: SearchView
    private lateinit var recyclerView: RecyclerView
    private lateinit var toolbarTitle: TextView
    private lateinit var toolbarSubtitle: TextView
    private lateinit var btnStart: Button
    private lateinit var prefs: android.content.SharedPreferences

    private val userList = mutableListOf<UserItem>()
    private val selectedUserIds = mutableSetOf<String>()
    private lateinit var adapter: ChallengeUserAdapter

    private var testUniqueId: Int = 0
    private var quizType: String = ""
    private var userId: Int = 0
    private var userName: String = "You"

    private var mode: String = MODE_FRIENDS
    private var isMatchmakingMode = false

    private val APP_SIGNATURE = "EduLabsRTM_Secure_v1_2026"
    private val ROOT_URL = "https://medigyaan.xyz/Neurons/"
    private val BASE_URL = "https://medigyaan.xyz/Neurons/"


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_challenge_selection)

        prefs = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

        testUniqueId = intent.getIntExtra("UNIQUE_ID", 0)
        quizType = intent.getStringExtra("QUIZ_TYPE") ?: "TEST_SERIES"
        mode = intent.getStringExtra("MODE") ?: MODE_FRIENDS
        isMatchmakingMode = mode == MODE_MATCHMAKING

        userId = prefs.getInt(KEY_USER_ID, 0)
        userName = prefs.getString("name", "You") ?: "You"

        Log.d(TAG, "onCreate -> uniqueId=$testUniqueId, quizType=$quizType, mode=$mode, userId=$userId")

        if (testUniqueId < 1 || testUniqueId > 50) {
            Log.e(TAG, "Invalid UNIQUE_ID=$testUniqueId. Backend expects 1..50.")
            Toast.makeText(this, "Invalid quiz selected", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        searchView = findViewById(R.id.searchView)
        recyclerView = findViewById(R.id.userRecyclerView)
        btnStart = findViewById(R.id.btnStartChallenge)
        setupAppBottomNavigation(findViewById<BottomNavigationView>(R.id.bottomNavigation), R.id.nav_home)

        ensureFirebaseAuth {
            setupRecyclerView()
            setupUi()
            toolbarTitle = findViewById(R.id.toolbarTitle)
            toolbarSubtitle = findViewById(R.id.toolbarSubtitle)
            if (!isMatchmakingMode) {
                setupSearch()
                loadSavedCloseFriends()
            }

            btnStart.setOnClickListener {
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

    private fun ensureFirebaseAuth(onReady: () -> Unit) {
        val current = FirebaseAuth.getInstance().currentUser
        if (current != null) {
            Log.d(TAG, "Firebase auth already ready -> uid=${current.uid}")
            onReady()
            return
        }

        Log.d(TAG, "Signing in anonymously...")
        FirebaseAuth.getInstance().signInAnonymously()
            .addOnSuccessListener {
                Log.d(TAG, "Anonymous auth success -> uid=${FirebaseAuth.getInstance().currentUser?.uid}")
                onReady()
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Auth failed: ${e.message}", e)
                Toast.makeText(this, "Auth failed", Toast.LENGTH_SHORT).show()
                finish()
            }
    }

    private fun setupUi() {
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
                    fetchUsers(q)
                } else {
                    loadSavedCloseFriends()
                }
                return true
            }

            override fun onQueryTextChange(newText: String?): Boolean {
                if (newText.isNullOrBlank()) {
                    loadSavedCloseFriends()
                }
                return false
            }
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

        val url = "$BASE_URL/get_close_friends.php?user_id=$userId"
        val cacheKey = "GET:$url"
        FirebaseOnlineCache.getString(cacheKey, 10 * 60 * 1000L) { cached ->
            cached?.let { applyCloseFriendsResponse(it, showEmptyToast = false) }
        }

        val request = object : StringRequest(
            Method.GET, url,
            { response ->
                FirebaseOnlineCache.putString(cacheKey, response)
                userList.clear()
                selectedUserIds.clear()
                adapter.notifyDataSetChanged()
                try {
                    val json = JSONObject(response)

                    if (json.getString("status") == "success") {
                        val friends = json.getJSONArray("friends")

                        for (i in 0 until friends.length()) {
                            val obj = friends.getJSONObject(i)

                            val id = obj.getString("id")
                            if (id == userId.toString()) continue

                            // 🔥 Placeholder item
                            val item = UserItem(
                                id = id,
                                name = "Loading...",
                                photo = "",
                                isCloseFriend = true
                            )

                            userList.add(item)

                            // 🔥 Fetch full profile
                            fetchFriendProfile(id, item)
                        }

                        adapter.notifyDataSetChanged()
                        btnStart.text = "Send (${selectedUserIds.size})"

                        toolbarTitle.text = "Select Friends"
                        toolbarSubtitle.text = "${userList.size} followers"

                        if (userList.isEmpty()) {
                            toolbarTitle.text = "No Friends"
                            toolbarSubtitle.text = "No followers found"
                            Toast.makeText(this, "No followers found", Toast.LENGTH_SHORT).show()
                        }

                    } else {
                        toolbarTitle.text = "Error"
                        toolbarSubtitle.text = "Server error"
                    }

                } catch (e: Exception) {
                    toolbarTitle.text = "Error"
                    toolbarSubtitle.text = "Parsing failed"
                    Log.e(TAG, "Parsing error", e)
                }
            },
            { error ->
                toolbarTitle.text = "Network Error"
                toolbarSubtitle.text = "Check connection"
                Log.e(TAG, "API error", error)
            }
        ) {}

        Volley.newRequestQueue(this).add(request)
    }

    private fun applyCloseFriendsResponse(response: String, showEmptyToast: Boolean) {
        try {
            val json = JSONObject(response)
            if (json.getString("status") != "success") return
            val friends = json.getJSONArray("friends")

            userList.clear()
            selectedUserIds.clear()
            for (i in 0 until friends.length()) {
                val obj = friends.getJSONObject(i)
                val id = obj.getString("id")
                if (id == userId.toString()) continue
                val item = UserItem(id = id, name = "Loading...", photo = "", isCloseFriend = true)
                userList.add(item)
                fetchFriendProfile(id, item)
            }

            adapter.notifyDataSetChanged()
            btnStart.text = "Send (${selectedUserIds.size})"
            toolbarTitle.text = if (userList.isEmpty()) "No Friends" else "Select Friends"
            toolbarSubtitle.text = if (userList.isEmpty()) "No followers found" else "${userList.size} followers"
            if (userList.isEmpty() && showEmptyToast) {
                Toast.makeText(this, "No followers found", Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Cached close friends parse error", e)
        }
    }
    private fun fetchFriendProfile(friendId: String, userItem: UserItem) {

        val url = "$BASE_URL/get_profilev1.php?user_id=$friendId&viewer_id=$userId"
        val cacheKey = "GET:$url"
        FirebaseOnlineCache.getString(cacheKey, 60 * 60 * 1000L) { cached ->
            cached?.let { applyFriendProfileResponse(friendId, userItem, it) }
        }

        val request = StringRequest(
            Request.Method.GET,
            url,
            { response ->
                FirebaseOnlineCache.putString(cacheKey, response)
                applyFriendProfileResponse(friendId, userItem, response)
            },
            { error ->
                Log.e(TAG, "Network error: ${error.message}")
            }
        )

        Volley.newRequestQueue(this).add(request)
    }

    private fun applyFriendProfileResponse(friendId: String, userItem: UserItem, response: String) {
                try {
                    val root = JSONObject(response)
                    val json = root.optJSONObject("data") ?: root

                    val name = json.optString("name", "User $friendId")
                    val photoRaw = json.optString("photo", "")

                    // 🔥 FIX IMAGE URL
                    val fixedPhoto = photoRaw
                        .takeIf { it.isNotBlank() && it != "null" }
                        ?.let {
                            if (it.startsWith("http")) it
                            else BASE_URL + it.replace("./", "").trimStart('/')
                        } ?: ""

                    userItem.name = name
                    userItem.photo = fixedPhoto

                    // 🔥 Update only changed item (better performance)
                    val index = userList.indexOfFirst { it.id == friendId }
                    if (index != -1) {
                        adapter.notifyItemChanged(index)
                    }

                    Log.d("PROFILE_LOAD", "Updated $friendId -> $name")

                } catch (e: Exception) {
                    Log.e(TAG, "Parse error: ${e.message}")
                }
    }



    private fun fetchUsers(keyword: String) {
        val url = "${ROOT_URL}api/searchv2.php?keyword=$keyword&type=json"
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

                                // ✅ IMAGE FIX
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
                return hashMapOf("X-App-Signature" to APP_SIGNATURE)
            }
        }

        Volley.newRequestQueue(this).add(req)
    }

    private fun startMatchmaking() {
        btnStart.isEnabled = false
        val ref = FirebaseDatabase.getInstance().reference.child("lobbies")

        Log.d(TAG, "startMatchmaking()")

        ref.orderByChild("status").equalTo("waiting").get()
            .addOnSuccessListener { snap ->
                var lobby: DataSnapshot? = null

                for (l in snap.children) {
                    val max = l.child("maxPlayers").getValue(Int::class.java) ?: 2
                    val count = l.child("players").childrenCount.toInt()
                    val status = l.child("status").getValue(String::class.java) ?: "waiting"

                    Log.d(TAG, "Lobby found -> ${l.key}, status=$status, players=$count/$max")

                    if (count < max) {
                        lobby = l
                        break
                    }
                }

                if (lobby != null) {
                    Log.d(TAG, "Joining existing lobby -> ${lobby!!.key}")
                    joinLobby(lobby!!)
                } else {
                    val newLobbyId = "lobby_${System.currentTimeMillis()}"
                    Log.d(TAG, "No lobby found. Creating -> $newLobbyId")
                    createLobby(newLobbyId, true)
                }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Matchmaking error: ${e.message}", e)
                btnStart.isEnabled = true
                Toast.makeText(this, "Matchmaking error", Toast.LENGTH_SHORT).show()
            }
    }

    private fun joinLobby(lobby: DataSnapshot) {
        val lobbyId = lobby.key ?: run {
            btnStart.isEnabled = true
            return
        }

        val hostId = lobby.child("host_id").value?.toString() ?: ""
        val isHost = hostId == userId.toString()

        val challengeId = when (val raw = lobby.child("challenge_id").value) {
            is Long -> raw.toInt()
            is Int -> raw
            is String -> raw.toIntOrNull() ?: 0
            else -> 0
        }

        val quizId = when (val raw = lobby.child("quiz_id").value) {
            is Long -> raw.toInt()
            is Int -> raw
            is String -> raw.toIntOrNull() ?: testUniqueId
            else -> testUniqueId
        }

        Log.d(TAG, "joinLobby -> lobbyId=$lobbyId hostId=$hostId isHost=$isHost challengeId=$challengeId quizId=$quizId")

        val ref = FirebaseDatabase.getInstance().reference.child("lobbies").child(lobbyId)

        ref.child("players").child(userId.toString())
            .setValue(
                mapOf(
                    "name" to userName,
                    "status" to "ready",
                    "role" to if (isHost) "host" else "guest",
                    "joined_at" to System.currentTimeMillis(),
                    "isBot" to false
                )
            )
            .addOnSuccessListener {
                openLobby(lobbyId, challengeId, quizId, isHost)
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "joinLobby failed: ${e.message}", e)
                btnStart.isEnabled = true
                Toast.makeText(this, "Join failed", Toast.LENGTH_SHORT).show()
            }
    }

    private fun sendFriendChallenge() {
        btnStart.isEnabled = false
        val url = "${ROOT_URL}initiate_challenge.php"
        Log.d(TAG, "sendFriendChallenge() -> $url")

        val req = object : StringRequest(
            Request.Method.POST,
            url,
            { res ->
                try {
                    Log.d(TAG, "initiate_challenge response -> $res")
                    val json = JSONObject(res)
                    val success = json.optBoolean("success") || json.optString("status") == "success"

                    if (!success) {
                        btnStart.isEnabled = true
                        Toast.makeText(this, "Failed to initiate", Toast.LENGTH_SHORT).show()
                    } else {
                        val challengeId = json.optInt("challenge_id", 0)
                        if (challengeId == 0) {
                            btnStart.isEnabled = true
                            Toast.makeText(this, "Invalid challenge id", Toast.LENGTH_SHORT).show()
                        } else {
                            val lobbyId = "lobby_$challengeId"
                            Log.d(TAG, "Friend challenge created -> challengeId=$challengeId lobbyId=$lobbyId")
                            createLobby(lobbyId, true, challengeId)
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "sendFriendChallenge parse error: ${e.message}", e)
                    btnStart.isEnabled = true
                }
            },
            { err ->
                Log.e(TAG, "sendFriendChallenge network error: ${err.message}", err)
                btnStart.isEnabled = true
                Toast.makeText(this, "Network error", Toast.LENGTH_SHORT).show()
            }
        ) {
            override fun getParams(): MutableMap<String, String> {
                return hashMapOf(
                    "creator_id" to userId.toString(),
                    "quiz_id" to testUniqueId.toString(),
                    "quiz_type" to quizType,
                    "opponent_ids" to selectedUserIds.joinToString(",")
                )
            }

            override fun getHeaders(): MutableMap<String, String> {
                return hashMapOf("X-App-Signature" to APP_SIGNATURE)
            }
        }

        Volley.newRequestQueue(this).add(req)
    }

    private fun createLobby(lobbyId: String, isHost: Boolean, challengeId: Int = generateChallengeId()) {
        val ref = FirebaseDatabase.getInstance().reference.child("lobbies").child(lobbyId)

        val data = mapOf(
            "status" to "waiting",
            "host_id" to userId.toString(),
            "challenge_id" to challengeId,
            "quiz_id" to testUniqueId,
            "quiz_type" to quizType,
            "maxPlayers" to 2,
            "created_at" to System.currentTimeMillis()
        )

        Log.d(TAG, "createLobby -> lobbyId=$lobbyId challengeId=$challengeId quizId=$testUniqueId")

        ref.setValue(data)
            .addOnSuccessListener {
                ref.child("players").child(userId.toString())
                    .setValue(
                        mapOf(
                            "name" to userName,
                            "status" to "ready",
                            "role" to "host",
                            "joined_at" to System.currentTimeMillis(),
                            "isBot" to false
                        )
                    )
                    .addOnSuccessListener {
                        openLobby(lobbyId, challengeId, testUniqueId, isHost)
                    }
                    .addOnFailureListener { e ->
                        Log.e(TAG, "Host player write failed: ${e.message}", e)
                        Toast.makeText(this, "Lobby player write failed", Toast.LENGTH_SHORT).show()
                    }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "createLobby failed: ${e.message}", e)
                Toast.makeText(this, "Create lobby failed", Toast.LENGTH_SHORT).show()
                btnStart.isEnabled = true
            }
    }

    private fun openLobby(lobbyId: String, challengeId: Int, quizId: Int, isHost: Boolean) {
        Log.d(TAG, "openLobby -> lobbyId=$lobbyId challengeId=$challengeId quizId=$quizId isHost=$isHost")

        startActivity(
            Intent(this, LobbyActivity::class.java).apply {
                putExtra("lobby_id", lobbyId)
                putExtra("challenge_id", challengeId)
                putExtra("CHALLENGE_ID", challengeId)
                putExtra("quiz_id", quizId)
                putExtra("UNIQUE_ID", quizId)
                putExtra("QUIZ_TYPE", quizType)
                putExtra("user_id", userId.toString())
                putExtra("user_name", userName)
                putExtra("is_host", isHost)
                putExtra("IS_CHALLENGE", true)
                putExtra("mode", mode)
            }
        )
        finish()
    }

    private fun generateChallengeId(): Int {
        val id = ((System.currentTimeMillis() % 900000L) + 100000L).toInt()
        Log.d(TAG, "generateChallengeId -> $id")
        return id
    }
}
