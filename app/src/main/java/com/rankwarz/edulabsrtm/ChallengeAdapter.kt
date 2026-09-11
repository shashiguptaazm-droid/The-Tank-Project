package com.rankwarz.edulabsrtm

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class ChallengeAdapter(
    private val items: List<ChallengeModel>,
    private val onItemClick: (ChallengeModel) -> Unit
) : RecyclerView.Adapter<ChallengeAdapter.ViewHolder>() {

    class ViewHolder(v: View) : RecyclerView.ViewHolder(v) {
        val title: TextView = v.findViewById(R.id.challengeTitle)
        val topic: TextView = v.findViewById(R.id.challengeTopic)
        val status: TextView = v.findViewById(R.id.challengeStatus)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val v = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_challenge_simple, parent, false)
        return ViewHolder(v)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]

        // Format the ID for display (e.g., lobby_489 -> Battle #489)
        holder.title.text = "Battle ${item.id.replace("lobby_", "#")}"
        holder.topic.text = if (item.topicName.isNotBlank()) "Topic: ${item.topicName}" else ""
        holder.status.text = "Status: Finished"

        // Color code status
        if (item.status == "Finished") {
            holder.status.setTextColor(Color.parseColor("#FF9800")) // Orange
        } else {
            holder.status.setTextColor(Color.parseColor("#757575")) // Grey
        }

        holder.itemView.setOnClickListener { onItemClick(item) }
    }

    override fun getItemCount() = items.size
}