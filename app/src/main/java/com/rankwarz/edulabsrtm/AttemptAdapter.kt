import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.rankwarz.edulabsrtm.AttemptModel
import com.rankwarz.edulabsrtm.R

 class AttemptAdapter(private val list: List<AttemptModel>) :
    RecyclerView.Adapter<AttemptAdapter.ViewHolder>() {

    inner class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val name: TextView = view.findViewById(R.id.nameText)
        val answer: TextView = view.findViewById(R.id.answerText)
        val status: TextView = view.findViewById(R.id.statusText)
        val time: TextView = view.findViewById(R.id.timeText)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_attempt, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = list[position]

        holder.name.text = item.name
        holder.answer.text = "Answer: ${item.user_answer}"
        holder.status.text = if (item.is_correct == 1) "✅ Correct" else "❌ Wrong"
        holder.time.text = item.created_at
    }

    override fun getItemCount() = list.size
}