package com.rankwarz.edulabsrtm

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import androidx.viewpager2.widget.ViewPager2 // Ensure this is imported
import com.bumptech.glide.Glide

class NewsFeedAdapter(
    private val postList: MutableList<PostModel>,
    private val onLikeClick: (PostModel) -> Unit,
    private val onCommentClick: (PostModel) -> Unit,
    private val onShareClick: (PostModel) -> Unit
) : RecyclerView.Adapter<NewsFeedAdapter.PostViewHolder>() {

    class PostViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val ivUserPhoto: ImageView = itemView.findViewById(R.id.ivUserPhoto)
        val tvUserName: TextView = itemView.findViewById(R.id.tvUserName)
        val tvCaption: TextView = itemView.findViewById(R.id.tvCaption)

        // Changed from ImageView to ViewPager2
        val viewPagerPost: ViewPager2 = itemView.findViewById(R.id.viewPagerPost)
        val tvImageCount: TextView = itemView.findViewById(R.id.tvImageCount)

        val btnLike: ImageButton = itemView.findViewById(R.id.btnLike)
        val btnComment: ImageButton = itemView.findViewById(R.id.btnComment)
        val btnShare: ImageButton = itemView.findViewById(R.id.btnShare)
        val tvLikeCount: TextView = itemView.findViewById(R.id.tvLikeCount)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PostViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_post, parent, false)
        return PostViewHolder(view)
    }

    override fun onBindViewHolder(holder: PostViewHolder, position: Int) {
        val post = postList[position]

        holder.tvUserName.text = post.ownerName
        holder.tvCaption.text = post.caption
        holder.tvLikeCount.text = "${post.likes} likes"

        // Load User Profile Photo
        Glide.with(holder.itemView.context)
            .load(post.ownerPhoto)
            .placeholder(R.drawable.ic_user_placeholder)
            .circleCrop()
            .into(holder.ivUserPhoto)

        // --- MULTI-IMAGE SLIDER LOGIC ---
        val sliderAdapter = ImageSliderAdapter(post.filePaths)
        holder.viewPagerPost.adapter = sliderAdapter

        if (post.filePaths.size > 1) {
            holder.tvImageCount.visibility = View.VISIBLE
            holder.tvImageCount.text = "1/${post.filePaths.size}"

            // Update the "1/13" text when user swipes
            holder.viewPagerPost.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
                override fun onPageSelected(pagePosition: Int) {
                    super.onPageSelected(pagePosition)
                    holder.tvImageCount.text = "${pagePosition + 1}/${post.filePaths.size}"
                }
            })
        } else {
            holder.tvImageCount.visibility = View.GONE
        }

        // Like Button Logic
        val likeIcon = if (post.isLiked) R.drawable.ic_heart_filled else R.drawable.ic_heart_outline
        holder.btnLike.setImageResource(likeIcon)

        holder.btnLike.setOnClickListener {
            post.isLiked = !post.isLiked
            if (post.isLiked) post.likes++ else post.likes--

            // Manual update instead of notifyItemChanged(position)
            // This prevents the ViewPager from resetting to image #1 on every click
            holder.tvLikeCount.text = "${post.likes} likes"
            holder.btnLike.setImageResource(if (post.isLiked) R.drawable.ic_heart_filled else R.drawable.ic_heart_outline)

            onLikeClick(post)
        }

        holder.btnComment.setOnClickListener { onCommentClick(post) }
        holder.btnShare.setOnClickListener { onShareClick(post) }
    }

    override fun getItemCount(): Int = postList.size
}