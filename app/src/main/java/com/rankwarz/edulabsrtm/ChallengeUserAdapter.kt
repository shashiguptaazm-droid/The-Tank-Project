package com.rankwarz.edulabsrtm

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.CheckBox
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide

class ChallengeUserAdapter(
    private val users: List<UserItem>,
    private val onSelectionChanged: (String, Boolean) -> Unit
) : RecyclerView.Adapter<ChallengeUserAdapter.ViewHolder>() {

    // Keep track of IDs selected
    private val selectedStates = mutableSetOf<String>()

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val v = LayoutInflater.from(parent.context).inflate(R.layout.item_challenge_user, parent, false)
        return ViewHolder(v)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val user = users[position]
        holder.name.text = user.name

        // Load photo safely
        Glide.with(holder.itemView.context)
            .load(user.photo)
            .circleCrop()
            .placeholder(android.R.drawable.ic_menu_gallery)
            .into(holder.avatar)

        // 1. Reset CheckBox to prevent incorrect state when recycling
        holder.checkBox.setOnCheckedChangeListener(null)
        val isCurrentlySelected = selectedStates.contains(user.id)
        holder.checkBox.isChecked = isCurrentlySelected

        // 2. Handle the click on the ENTIRE ROW
        holder.itemView.setOnClickListener {
            val newState = !holder.checkBox.isChecked
            holder.checkBox.isChecked = newState

            if (newState) {
                selectedStates.add(user.id)
            } else {
                selectedStates.remove(user.id)
            }

            // Notify the Activity to update the button text
            onSelectionChanged(user.id, newState)
        }
    }

    override fun getItemCount() = users.size

    class ViewHolder(v: View) : RecyclerView.ViewHolder(v) {
        val name: TextView = v.findViewById(R.id.txtUserName)
        val avatar: ImageView = v.findViewById(R.id.imgUserAvatar)
        val checkBox: CheckBox = v.findViewById(R.id.userCheckBox)
    }
}