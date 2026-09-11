package com.rankwarz.edulabsrtm

import android.content.Context
import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.TextView

class TestGridAdapter(
    private val context: Context,
    private val testList: List<String>,
    private val startId: Int
) : BaseAdapter() {

    private val prefs = context.getSharedPreferences("COMPLETED_TESTS", Context.MODE_PRIVATE)

    override fun getCount(): Int = testList.size
    override fun getItem(position: Int): Any = testList[position]
    override fun getItemId(position: Int): Long = position.toLong()

    override fun getView(position: Int, convertView: View?, parent: ViewGroup?): View {
        // Use your custom card layout here
        val view: View = convertView ?: LayoutInflater.from(context)
            .inflate(R.layout.item_test_card, parent, false)

        val title = view.findViewById<TextView>(R.id.testTitle)
        val statusBadge = view.findViewById<TextView>(R.id.attemptStatus)
        val subtitle = view.findViewById<TextView>(R.id.testSubtitle)

        val currentTestId = startId + position
        title.text = testList[position]
        subtitle.text = "Standard Pattern"

        // Logic to show "Attempted" vs "Not Attempted"
        val isCompleted = prefs.getBoolean("id_$currentTestId", false)

        if (isCompleted) {
            statusBadge.text = "Attempted"
            statusBadge.setTextColor(Color.WHITE)
            statusBadge.setBackgroundColor(Color.parseColor("#4CAF50")) // Green
        } else {
            statusBadge.text = "Not Attempted"
            statusBadge.setTextColor(Color.parseColor("#757575"))
            statusBadge.setBackgroundColor(Color.parseColor("#E0E0E0")) // Gray
        }

        return view
    }
}