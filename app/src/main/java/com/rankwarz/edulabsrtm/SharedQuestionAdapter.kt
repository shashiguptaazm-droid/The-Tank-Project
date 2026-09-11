package com.rankwarz.edulabsrtm

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class SharedQuestionAdapter(
    private val list: List<SharedQuestionModel>,
    private val onClick: (SharedQuestionModel) -> Unit
) : RecyclerView.Adapter<SharedQuestionAdapter.ViewHolder>() {

    inner class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val question: TextView = itemView.findViewById(R.id.questionText)
        val attempts: TextView = itemView.findViewById(R.id.attemptsText)
        val accuracy: TextView = itemView.findViewById(R.id.accuracyText)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_shared_question, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = list[position]

        holder.question.text = item.question
        holder.attempts.text = "Attempts: ${item.total_attempts}"
        holder.accuracy.text = "Accuracy: ${item.accuracy}%"

        holder.itemView.setOnClickListener {
            onClick(item)
        }
    }

    override fun getItemCount(): Int = list.size
}