package com.rankwarz.edulabsrtm

import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.android.volley.Response
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import org.json.JSONArray
import org.json.JSONObject

// Changed inheritance from AppCompatActivity to BaseActivity
class NewsFeedActivity : BaseActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var adapter: NewsFeedAdapter
    private val postList = mutableListOf<PostModel>()

    /** Post passed in by another screen (e.g. AI chat community card) — pinned to the top. */
    private var focusPost: PostModel? = null

    private val FETCH_POSTS_URL = "https://medigyaan.xyz/Neurons/api/fetch_posts.php"
    private val ACTION_URL = "https://medigyaan.xyz/Neurons/api/social_actions.php"

    companion object {
        const val EXTRA_FOCUS_POST_ID = "extra_focus_post_id"
        const val EXTRA_FOCUS_POST_JSON = "extra_focus_post_json"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_news_feed)

        // Initialize Navigation from BaseActivity
        setupNavigation(
            findViewById(R.id.drawerLayout),
            findViewById(R.id.bottomNavigation),
            findViewById(R.id.navigationView)
        )

        recyclerView = findViewById(R.id.rvNewsFeed)
        swipeRefresh = findViewById(R.id.swipeRefresh)

        setupRecyclerView()
        applyFocusPostFromIntent()

        swipeRefresh.setOnRefreshListener { fetchNewsFeed(isRefresh = true) }
        fetchNewsFeed(isRefresh = false)
    }

    /**
     * Reads the focused post (from the AI chat community card) and pins it to the top of
     * the feed so the tapped post's image + caption are shown in-app immediately, with
     * the rest of the community feed loading below it.
     */
    private fun applyFocusPostFromIntent() {
        val focusId = intent.getIntExtra(EXTRA_FOCUS_POST_ID, -1)
        if (focusId <= 0) return
        val focusJson = intent.getStringExtra(EXTRA_FOCUS_POST_JSON) ?: return
        runCatching {
            val obj = JSONObject(focusJson)
            val paths = mutableListOf<String>()
            val arr = obj.optJSONArray("file_paths")
            if (arr != null) {
                for (j in 0 until arr.length()) {
                    val p = arr.optString(j, "").trim()
                    if (p.isNotEmpty()) paths.add(p)
                }
            }
            focusPost = PostModel(
                postId = obj.getInt("post_id"),
                ownerName = obj.optString("name", "MediGyaan user"),
                ownerPhoto = obj.optString("photo", ""),
                caption = obj.optString("caption", ""),
                filePaths = paths,
                likes = obj.optInt("likes", 0),
                isLiked = false
            )
            postList.add(0, focusPost!!)
            adapter.notifyDataSetChanged()
        }
    }

    private fun setupRecyclerView() {
        adapter = NewsFeedAdapter(postList,
            onLikeClick = { post -> sendSocialAction(post.postId, "like") },
            onCommentClick = { post -> /* Implement Comment Dialog */ },
            onShareClick = { post -> sendSocialAction(post.postId, "share") }
        )
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = adapter
    }

    private fun fetchNewsFeed(isRefresh: Boolean) {
        if (isRefresh) postList.clear()

        // Keep the focused post pinned at the top (also after a pull-to-refresh).
        focusPost?.let { focus ->
            postList.removeAll { it.postId == focus.postId }
            postList.add(0, focus)
        }

        val request = object : StringRequest(Method.GET, FETCH_POSTS_URL,
            Response.Listener { response ->
                swipeRefresh.isRefreshing = false
                try {
                    val jsonArray = JSONArray(response)
                    for (i in 0 until jsonArray.length()) {
                        val obj = jsonArray.getJSONObject(i)

                        // Skip the focused post if the feed already contains it.
                        if (obj.getInt("post_id") == focusPost?.postId) continue

                        val filesJson = obj.getJSONArray("file_paths")
                        val filePaths = mutableListOf<String>()
                        for (j in 0 until filesJson.length()) {
                            filePaths.add(filesJson.getString(j))
                        }

                        postList.add(PostModel(
                            postId = obj.getInt("post_id"),
                            ownerName = obj.getString("name"),
                            ownerPhoto = obj.getString("photo"),
                            caption = obj.getString("caption"),
                            filePaths = filePaths,
                            likes = obj.getInt("likes"),
                            isLiked = obj.optInt("user_liked", 0) == 1
                        ))
                    }
                    adapter.notifyDataSetChanged()
                } catch (e: Exception) {
                    Log.e("DATA_ERROR", "Error parsing: ${e.message}")
                }
            },
            Response.ErrorListener { error ->
                swipeRefresh.isRefreshing = false
                Toast.makeText(this, "Network Error", Toast.LENGTH_SHORT).show()
            }
        ) {
            override fun getHeaders(): MutableMap<String, String> {
                return hashMapOf("X-App-Signature" to "EduLabsRTM_Secure_v1_2026")
            }
        }
        Volley.newRequestQueue(this).add(request)
    }

    private fun sendSocialAction(postId: Int, action: String) {
        val userId = getSharedPreferences("UserPrefs", MODE_PRIVATE).getInt("user_id", 0)

        val request = object : StringRequest(Method.POST, ACTION_URL,
            Response.Listener { /* Handle success */ },
            Response.ErrorListener { /* Handle error */ }
        ) {
            override fun getBody(): ByteArray {
                val params = JSONObject()
                params.put("action", action)
                params.put("post_id", postId)
                params.put("user_id", userId)
                return params.toString().toByteArray()
            }

            override fun getHeaders(): MutableMap<String, String> {
                return hashMapOf(
                    "Content-Type" to "application/json",
                    "X-App-Signature" to "EduLabsRTM_Secure_v1_2026"
                )
            }
        }
        Volley.newRequestQueue(this).add(request)
    }

    // Handle back button to close drawer first
    override fun onBackPressed() {
        val drawer = findViewById<androidx.drawerlayout.widget.DrawerLayout>(R.id.drawerLayout)
        if (drawer.isDrawerOpen(androidx.core.view.GravityCompat.START)) {
            drawer.closeDrawer(androidx.core.view.GravityCompat.START)
        } else {
            super.onBackPressed()
        }
    }
}