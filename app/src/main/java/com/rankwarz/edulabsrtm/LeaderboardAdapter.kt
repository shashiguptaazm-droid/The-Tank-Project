package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.rankwarz.edulabsrtm.LeaderboardUser
import com.rankwarz.edulabsrtm.ProfileActivity
import com.rankwarz.edulabsrtm.R

class LeaderboardAdapter(
    private val context: Context,
    private val list: List<LeaderboardUser>
) : RecyclerView.Adapter<LeaderboardAdapter.ViewHolder>() {

    inner class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val txtRank: TextView = view.findViewById(R.id.txtRank)
        val txtName: TextView = view.findViewById(R.id.txtName)
        val txtLevel: TextView = view.findViewById(R.id.txtLevel)
        val txtXP: TextView = view.findViewById(R.id.txtXp)
        val imgUser: ImageView = view.findViewById(R.id.imgUser)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(context)
            .inflate(R.layout.item_leaderboard, parent, false)
        return ViewHolder(view)
    }

    override fun getItemCount() = list.size

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val user = list[position]

        holder.txtRank.text = "#${position + 1}"
        holder.txtName.text = user.name
        holder.txtLevel.text = "Level ${user.level}"
        holder.txtXP.text = "${user.exp} XP"

        val imageUrl = if (user.photo.startsWith("http")) {
            user.photo
        } else {
            "https://medigyaan.xyz/Neurons/${user.photo.replace("./", "")}"
        }

        Glide.with(context)
            .load(imageUrl)
            .circleCrop()
            .placeholder(R.drawable.ic_user_placeholder)
            .into(holder.imgUser)

        holder.itemView.setOnClickListener {
            val userId = user.id.toIntOrNull() ?: 0

            val intent = Intent(context, ProfileActivity::class.java)
            intent.putExtra("TARGET_USER_ID", userId)
            context.startActivity(intent)
        }
    }
}
