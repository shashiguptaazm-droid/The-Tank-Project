package com.rankwarz.edulabsrtm

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.bumptech.glide.request.RequestOptions

class UserAdapter(
    private val onUserClick: (ChatUserItem) -> Unit,
    private val onBlockUser: (ChatUserItem) -> Unit
) : RecyclerView.Adapter<UserAdapter.UserViewHolder>() {

    private var users = mutableListOf<ChatUserItem>()

    fun setUsers(newList: List<ChatUserItem>) {
        users.clear()
        users.addAll(newList)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): UserViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_user_chat, parent, false)
        return UserViewHolder(view)
    }

    override fun onBindViewHolder(holder: UserViewHolder, position: Int) {
        val user = users[position]
        holder.bind(user)
    }

    override fun getItemCount(): Int = users.size

    inner class UserViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val img: ImageView = view.findViewById(R.id.userImage)
        private val name: TextView = view.findViewById(R.id.userName)
        private val onlineIndicator: View = view.findViewById(R.id.onlineIndicator)
        private val blockBtn: ImageView = view.findViewById(R.id.blockBtn)

        fun bind(user: ChatUserItem) {
            name.text = user.name
            val fullImageUrl = if (user.image.startsWith("http")) user.image 
                               else "https://medigyaan.xyz/Neurons/" + user.image.removePrefix("/")
            
            Glide.with(itemView.context)
                .load(if (user.image.isNotEmpty()) fullImageUrl else R.drawable.ic_user_placeholder)
                .apply(RequestOptions.circleCropTransform())
                .placeholder(R.drawable.ic_user_placeholder)
                .into(img)

            // Online indicator
            onlineIndicator.visibility = if (user.isOnline) View.VISIBLE else View.GONE
            
            // Block button (only for other users, not self)
            // Note: current user check would need current user ID passed in

            itemView.setOnClickListener { onUserClick(user) }
            blockBtn.setOnClickListener { 
                AlertDialog.Builder(itemView.context)
                    .setTitle("Block User")
                    .setMessage("Block ${user.name}? They won't be able to message you.")
                    .setPositiveButton("Block") { _, _ ->
                        onBlockUser(user)
                    }
                    .setNegativeButton("Cancel", null)
                    .show()
            }
        }
    }
}
