package com.rankwarz.edulabsrtm

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.widget.SearchView
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.bumptech.glide.Glide
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.navigation.NavigationView
import com.google.android.material.chip.Chip
import com.google.android.material.chip.ChipGroup
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder

// --- 1. DATA MODELS ---
data class QuestionItem(
    val id: String,
    val text: String,
    val subject: String,
    val image: String
)

data class UserItem(
    val id: String,
    var name: String,
    var photo: String,
    val isCloseFriend: Boolean = false
)

data class CommunityPostItem(
    val id: Int,
    val author: String,
    val authorPhoto: String,
    val caption: String,
    val images: List<String>,
    val likes: Int,
    val uploadDate: String
)

data class UserVideoItem(
    val id: Int,
    val title: String,
    val author: String,
    val authorPhoto: String,
    val videoUrl: String,
    val thumbnailUrl: String,
    val likes: Int,
    val uploadDate: String
)

data class TopicItem(
    val name: String,
    val subject: String
)

// --- 2. CLICK LISTENER ---
interface OnSearchItemClickListener {
    fun onQuestionClick(item: QuestionItem)
    fun onUserClick(item: UserItem)
    fun onPostClick(item: CommunityPostItem)
    fun onTopicClick(item: TopicItem)
    fun onVideoClick(item: UserVideoItem)
}

// --- 3. MAIN ACTIVITY ---
class GlobalSearchActivity : BaseActivity(), OnSearchItemClickListener {

    private val TAG = "SEARCH_LOGS"
    private val APP_SIGNATURE = "EduLabsRTM_Secure_v1_2026"

    private lateinit var searchAdapter: GlobalSearchAdapter
    private lateinit var searchView: SearchView
    private lateinit var recyclerView: RecyclerView
    private lateinit var filterChipGroup: ChipGroup

    private val allResults = mutableListOf<Any>()
    private val displayResults = mutableListOf<Any>()
    private var activeFilter = "ALL" // "ALL", "QUESTIONS", "USERS", "POSTS", "VIDEOS"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_search)

        val drawer = findViewById<DrawerLayout>(R.id.drawerLayout)
        val bottomNav = findViewById<BottomNavigationView>(R.id.bottomNavigation)
        val sideNav = findViewById<NavigationView>(R.id.navigationView)

        if (drawer != null && bottomNav != null && sideNav != null) {
            setupNavigation(drawer, bottomNav, sideNav)
        }

        searchView = findViewById(R.id.searchView)
        recyclerView = findViewById(R.id.searchRecyclerView)
        filterChipGroup = findViewById(R.id.filterChipGroup)

        setupRecyclerView()
        setupBottomNavigation(bottomNav)
        setupFilterChips()

        searchView.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                val keyword = query?.trim().orEmpty()
                if (keyword.length >= 3) {
                    fetchSearchResults(keyword)
                } else {
                    Toast.makeText(
                        this@GlobalSearchActivity,
                        "Minimum 3 characters required",
                        Toast.LENGTH_SHORT
                    ).show()
                }
                return true
            }

            override fun onQueryTextChange(newText: String?): Boolean = false
        })
    }

    private fun setupBottomNavigation(bottomNav: BottomNavigationView) {
        setupAppBottomNavigation(bottomNav, R.id.nav_search)
    }

    private fun setupRecyclerView() {
        searchAdapter = GlobalSearchAdapter(displayResults, this)
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = searchAdapter
    }

    private fun setupFilterChips() {
        findViewById<Chip>(R.id.chipAll)?.setOnClickListener { updateActiveFilter("ALL") }
        findViewById<Chip>(R.id.chipQuestions)?.setOnClickListener { updateActiveFilter("QUESTIONS") }
        findViewById<Chip>(R.id.chipUsers)?.setOnClickListener { updateActiveFilter("USERS") }
        findViewById<Chip>(R.id.chipPosts)?.setOnClickListener { updateActiveFilter("POSTS") }
        findViewById<Chip>(R.id.chipTopics)?.setOnClickListener { updateActiveFilter("TOPICS") }
        findViewById<Chip>(R.id.chipVideos)?.setOnClickListener { updateActiveFilter("VIDEOS") }
    }

    private fun updateActiveFilter(filter: String) {
        if (activeFilter != filter) {
            activeFilter = filter
            filterResults()
        }
    }

    private fun filterResults() {
        displayResults.clear()
        when (activeFilter) {
            "ALL" -> displayResults.addAll(allResults)
            "QUESTIONS" -> displayResults.addAll(allResults.filterIsInstance<QuestionItem>())
            "USERS" -> displayResults.addAll(allResults.filterIsInstance<UserItem>())
            "POSTS" -> displayResults.addAll(allResults.filterIsInstance<CommunityPostItem>())
            "TOPICS" -> displayResults.addAll(allResults.filterIsInstance<TopicItem>())
            "VIDEOS" -> displayResults.addAll(allResults.filterIsInstance<UserVideoItem>())
        }
        searchAdapter.notifyDataSetChanged()
    }

    private fun fetchSearchResults(keyword: String) {
        val url = "https://medigyaan.xyz/Neurons/api/searchv2.php?keyword=$keyword&type=json"

        val request = object : StringRequest(
            Request.Method.GET,
            url,
            { response ->
                try {
                    val jsonObject = JSONObject(response.trim())
                    if (jsonObject.optString("status") == "success") {
                        allResults.clear()

                        jsonObject.optJSONObject("results")?.let { results ->

                            results.optJSONArray("questions")?.let { qArray ->
                                for (i in 0 until qArray.length()) {
                                    val q = qArray.getJSONObject(i)
                                    allResults.add(
                                        QuestionItem(
                                            id = q.optString("question_id"),
                                            text = q.optString("question"),
                                            subject = q.optString("subject"),
                                            image = q.optString("question_image")
                                        )
                                    )
                                }
                            }

                            results.optJSONArray("users")?.let { uArray ->
                                for (i in 0 until uArray.length()) {
                                    val u = uArray.getJSONObject(i)
                                    allResults.add(
                                        UserItem(
                                            id = u.optString("user_id"),
                                            name = u.optString("name"),
                                            photo = u.optString("photo")
                                        )
                                    )
                                }
                            }
                        }

                        filterResults()

                        if (allResults.isEmpty()) {
                            Toast.makeText(this, "No data found", Toast.LENGTH_SHORT).show()
                        }
                    } else {
                        Toast.makeText(this, "No result found", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "ParsingError: ${e.message}")
                    Toast.makeText(this, "Parsing error", Toast.LENGTH_SHORT).show()
                }
            },
            { error ->
                Log.e(TAG, "VolleyError: ${error.message}")
                Toast.makeText(this, "Server not responding", Toast.LENGTH_SHORT).show()
            }
        ) {
            override fun getHeaders(): MutableMap<String, String> {
                return hashMapOf(
                    "X-App-Signature" to APP_SIGNATURE,
                    "Accept" to "application/json"
                )
            }
        }

        Volley.newRequestQueue(this).add(request)

        fetchCommunityPosts(keyword)
        fetchTopics(keyword)
        fetchUserVideos(keyword)
    }

    private fun fetchTopics(keyword: String) {
        val currentGoal = getSharedPreferences("MY_APP", MODE_PRIVATE).getString("selected_subject_preference", "NEET PG") ?: "NEET PG"
        val subjectFilter = when (currentGoal) {
            "NEET UG" -> "NEET UG"
            "NEET PG" -> "NEET PG"
            "UPSC" -> "UPSC"
            "CAT" -> "CAT"
            else -> currentGoal
        }
        // Updated to use the consistent getTopics.php endpoint - Para 119-121
        val url = "https://medigyaan.xyz/Neurons/api/getTopics.php?subject=${Uri.encode(subjectFilter)}"
        val request = object : StringRequest(
            Method.GET,
            url,
            { response ->
                runCatching {
                    val root = JSONObject(response.trim())
                    if (root.optBoolean("success")) {
                        val data = root.optJSONArray("data") ?: JSONArray()
                        for (i in 0 until data.length()) {
                            val item = data.get(i)
                            val topicName = if (item is JSONObject) {
                                item.optString("name")
                            } else if (item is String) {
                                item
                            } else ""

                            if (topicName.isNotBlank() && topicName.contains(keyword, ignoreCase = true)) {
                                allResults.add(
                                    TopicItem(
                                        name = topicName,
                                        subject = subjectFilter
                                    )
                                )
                            }
                        }
                        // Fix duplicates in the distinct topic list - Para 118
                        val distinctTopics = allResults.filterIsInstance<TopicItem>().distinctBy { it.name }
                        allResults.removeAll { it is TopicItem }
                        allResults.addAll(distinctTopics)
                        
                        filterResults()
                    }
                }.onFailure { Log.e(TAG, "Topic parsing error", it) }
            },
            { error -> Log.e(TAG, "Topic search error: ${error.message}") }
        ) {
            override fun getHeaders(): MutableMap<String, String> = hashMapOf(
                "X-App-Signature" to APP_SIGNATURE,
                "Accept" to "application/json"
            )
        }
        Volley.newRequestQueue(this).add(request)
    }

    private fun fetchCommunityPosts(keyword: String) {
        val userId = getSharedPreferences("MY_APP", MODE_PRIVATE).getInt("user_id", 0)
        val url = "https://medigyaan.xyz/Neurons/api/posts_search.php?q=${URLEncoder.encode(keyword, "UTF-8")}&user_id=$userId"
        val request = object : StringRequest(
            Request.Method.GET,
            url,
            { response ->
                runCatching {
                    val root = JSONObject(response.trim())
                    if (root.optString("status") != "success") return@runCatching
                    val posts = root.optJSONArray("posts") ?: JSONArray()
                    for (i in 0 until posts.length()) {
                        val post = posts.optJSONObject(i) ?: continue
                        val id = post.optInt("post_id", 0)
                        if (id <= 0) continue
                        val images = buildList {
                            val imageArray = post.optJSONArray("images") ?: JSONArray()
                            for (j in 0 until imageArray.length()) {
                                imageArray.optString(j).takeIf { it.startsWith("http") }?.let(::add)
                            }
                        }
                        allResults.add(
                            CommunityPostItem(
                                id = id,
                                author = post.optString("author", "MediGyaan user"),
                                authorPhoto = post.optString("author_photo"),
                                caption = post.optString("caption"),
                                images = images,
                                likes = post.optInt("likes", 0),
                                uploadDate = post.optString("upload_date")
                            )
                        )
                    }
                    filterResults()
                }.onFailure { Log.e(TAG, "Post parsing error", it) }
            },
            { error -> Log.e(TAG, "Post search error: ${error.message}") }
        ) {
            override fun getHeaders(): MutableMap<String, String> = hashMapOf(
                "X-App-Signature" to APP_SIGNATURE,
                "Accept" to "application/json"
            )
        }
        Volley.newRequestQueue(this).add(request)
    }

    private fun fetchUserVideos(keyword: String) {
        val userId = getSharedPreferences("MY_APP", MODE_PRIVATE).getInt("user_id", 0)
        val url = "https://medigyaan.xyz/Neurons/api/videos_search.php?q=${URLEncoder.encode(keyword, "UTF-8")}&user_id=$userId"
        val request = object : StringRequest(
            Request.Method.GET,
            url,
            { response ->
                runCatching {
                    val root = JSONObject(response.trim())
                    if (root.optString("status") != "success") return@runCatching
                    val videos = root.optJSONArray("videos") ?: JSONArray()
                    for (i in 0 until videos.length()) {
                        val v = videos.optJSONObject(i) ?: continue
                        val id = v.optInt("video_id", 0)
                        if (id <= 0) continue
                        allResults.add(
                            UserVideoItem(
                                id = id,
                                title = v.optString("title", "Untitled"),
                                author = v.optString("author", "Unknown"),
                                authorPhoto = v.optString("author_photo", ""),
                                videoUrl = v.optString("video_url", ""),
                                thumbnailUrl = v.optString("thumbnail_url", ""),
                                likes = v.optInt("likes", 0),
                                uploadDate = v.optString("upload_date", "")
                            )
                        )
                    }
                    filterResults()
                }.onFailure { Log.e(TAG, "Video search error", it) }
            },
            { error -> Log.e(TAG, "Video search error: ${error.message}") }
        ) {
            override fun getHeaders(): MutableMap<String, String> = hashMapOf(
                "X-App-Signature" to APP_SIGNATURE,
                "Accept" to "application/json"
            )
        }
        Volley.newRequestQueue(this).add(request)
    }

    override fun onQuestionClick(item: QuestionItem) {
        try {
            val questionId = item.id.toIntOrNull()
            if (questionId == null || questionId <= 0) {
                Log.e(TAG, "Invalid question id from search result: ${item.id}")
                Toast.makeText(this, "Could not load question", Toast.LENGTH_SHORT).show()
                return
            }

            val intent = Intent(this, MCQActivity::class.java)
            intent.putExtra("question_id", questionId)
            intent.putExtra("SELECTED_SUBJECT", item.subject)
            intent.putExtra("from_search", true)
            startActivity(intent)
        } catch (e: Exception) {
            Log.e(TAG, "Error opening McqActivity: ${e.message}")
            Toast.makeText(this, "Could not load question", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onUserClick(item: UserItem) {
        Toast.makeText(this, "Opening profile: ${item.name}", Toast.LENGTH_SHORT).show()
        try {
            val intent = Intent(this, ProfileActivity::class.java)
            intent.putExtra("TARGET_USER_ID", item.id.toIntOrNull() ?: 0)
            startActivity(intent)
        } catch (e: Exception) {
            Log.e("NAV_ERROR", e.toString())
            Toast.makeText(this, "Failed to open profile", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onPostClick(item: CommunityPostItem) {
        val postJson = JSONObject()
            .put("post_id", item.id)
            .put("name", item.author)
            .put("photo", item.authorPhoto)
            .put("caption", item.caption)
            .put("file_paths", JSONArray(item.images))
            .put("likes", item.likes)
        startActivity(
            Intent(this, NewsFeedActivity::class.java)
                .putExtra(NewsFeedActivity.EXTRA_FOCUS_POST_ID, item.id)
                .putExtra(NewsFeedActivity.EXTRA_FOCUS_POST_JSON, postJson.toString())
        )
    }

    override fun onTopicClick(item: TopicItem) {
        val currentSubject = getSharedPreferences("MY_APP", MODE_PRIVATE)
            .getString("selected_subject_preference", "NEET PG") ?: "NEET PG"
        val intent = Intent(this, MCQActivity::class.java)
        intent.putExtra("SELECTED_SUBJECT", currentSubject)
        intent.putExtra("SELECTED_TOPIC", item.name)
        intent.putExtra("from_search", true)
        startActivity(intent)
    }

    override fun onVideoClick(item: UserVideoItem) {
        val intent = Intent(this, VideoPlayerActivity::class.java)
        intent.putExtra("VIDEO_URL", item.videoUrl)
        intent.putExtra("VIDEO_TITLE", item.title)
        startActivity(intent)
    }

    override fun onBackPressed() {
        val drawer = findViewById<DrawerLayout>(R.id.drawerLayout)
        if (drawer != null && drawer.isDrawerOpen(GravityCompat.START)) {
            drawer.closeDrawer(GravityCompat.START)
        } else {
            super.onBackPressed()
        }
    }
}

// --- 4. MULTI-TYPE ADAPTER ---
class GlobalSearchAdapter(
    private val items: List<Any>,
    private val listener: OnSearchItemClickListener
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private val TYPE_QUESTION = 1
    private val TYPE_USER = 2
    private val TYPE_POST = 3
    private val TYPE_TOPIC = 4
    private val TYPE_VIDEO = 5

    override fun getItemViewType(position: Int): Int {
        return when (items[position]) {
            is QuestionItem -> TYPE_QUESTION
            is UserItem -> TYPE_USER
            is CommunityPostItem -> TYPE_POST
            is TopicItem -> TYPE_TOPIC
            is UserVideoItem -> TYPE_VIDEO
            else -> TYPE_USER
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return when (viewType) {
            TYPE_QUESTION -> {
                val view = inflater.inflate(R.layout.item_search_question, parent, false)
                QuestionViewHolder(view)
            }
            TYPE_POST -> PostViewHolder(inflater.inflate(R.layout.item_search_post, parent, false))
            TYPE_TOPIC -> TopicViewHolder(inflater.inflate(R.layout.item_search_topic, parent, false))
            TYPE_VIDEO -> VideoViewHolder(inflater.inflate(R.layout.item_search_video, parent, false))
            else -> {
                val view = inflater.inflate(R.layout.item_search_user, parent, false)
                UserViewHolder(view)
            }
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val item = items[position]

        if (holder is QuestionViewHolder && item is QuestionItem) {
            holder.title.text = item.text
            holder.sub.text = item.subject

            val imageUrl = if (!item.image.isNullOrEmpty() && item.image != "null") {
                if (item.image.startsWith("http")) item.image
                else "https://medigyaan.xyz/Neurons/${item.image}"
            } else {
                null
            }

            if (imageUrl != null) {
                holder.imgCard.visibility = View.VISIBLE
                Glide.with(holder.itemView.context)
                    .load(imageUrl)
                    .placeholder(android.R.drawable.ic_menu_report_image)
                    .error(android.R.drawable.ic_delete)
                    .into(holder.img)
            } else {
                holder.imgCard.visibility = View.GONE
            }

            holder.itemView.setOnClickListener {
                listener.onQuestionClick(item)
            }

        } else if (holder is UserViewHolder && item is UserItem) {
            holder.name.text = item.name

            val imageUrl = if (!item.photo.isNullOrEmpty() && item.photo != "null") {
                if (item.photo.startsWith("http")) item.photo
                else "https://medigyaan.xyz/Neurons/${item.photo}"
            } else {
                null
            }

            Glide.with(holder.itemView.context)
                .load(imageUrl)
                .circleCrop()
                .placeholder(android.R.drawable.ic_menu_gallery)
                .error(android.R.drawable.ic_delete)
                .into(holder.avatar)

            holder.itemView.setOnClickListener {
                listener.onUserClick(item)
            }
        } else if (holder is PostViewHolder && item is CommunityPostItem) {
            holder.author.text = item.author
            holder.caption.text = item.caption
            holder.meta.text = "♥ ${item.likes}"
            val imageUrl = item.images.firstOrNull()
            Glide.with(holder.itemView.context)
                .load(imageUrl)
                .centerCrop()
                .placeholder(android.R.drawable.ic_menu_gallery)
                .into(holder.image)
            holder.itemView.setOnClickListener { listener.onPostClick(item) }
        } else if (holder is TopicViewHolder && item is TopicItem) {
            holder.name.text = item.name
            holder.subject.text = item.subject
            holder.itemView.setOnClickListener { listener.onTopicClick(item) }
            holder.btnPractice.setOnClickListener { listener.onTopicClick(item) }
        } else if (holder is VideoViewHolder && item is UserVideoItem) {
            holder.title.text = item.title
            holder.author.text = item.author
            holder.meta.text = "♥ ${item.likes}"
            holder.itemView.setOnClickListener { listener.onVideoClick(item) }
        }
    }

    override fun getItemCount(): Int = items.size

    class QuestionViewHolder(v: View) : RecyclerView.ViewHolder(v) {
        val title: TextView = v.findViewById(R.id.txtQuestionTitle)
        val sub: TextView = v.findViewById(R.id.txtQuestionSubject)
        val img: ImageView = v.findViewById(R.id.imgQuestion)
        val imgCard: View = v.findViewById(R.id.imgCard)
    }

    class UserViewHolder(v: View) : RecyclerView.ViewHolder(v) {
        val name: TextView = v.findViewById(R.id.txtUserName)
        val avatar: ImageView = v.findViewById(R.id.imgUserAvatar)
    }

    class PostViewHolder(v: View) : RecyclerView.ViewHolder(v) {
        val image: ImageView = v.findViewById(R.id.imgPost)
        val author: TextView = v.findViewById(R.id.txtPostAuthor)
        val caption: TextView = v.findViewById(R.id.txtPostCaption)
        val meta: TextView = v.findViewById(R.id.txtPostMeta)
    }

    class TopicViewHolder(v: View) : RecyclerView.ViewHolder(v) {
        val name: TextView = v.findViewById(R.id.txtTopicName)
        val subject: TextView = v.findViewById(R.id.txtTopicSubject)
        val btnPractice: View = v.findViewById(R.id.btnPracticeSolo)
    }

    class VideoViewHolder(v: View) : RecyclerView.ViewHolder(v) {
        val title: TextView = v.findViewById(R.id.txtVideoTitle)
        val author: TextView = v.findViewById(R.id.txtVideoAuthor)
        val meta: TextView = v.findViewById(R.id.txtVideoMeta)
    }
}
