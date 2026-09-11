package com.rankwarz.edulabsrtm

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Quiz
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.recyclerview.widget.RecyclerView
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun HistoryScreen(
    list: List<HistoryModel>,
    onItemClick: ((HistoryModel) -> Unit)? = null
) {
    if (list.isEmpty()) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "No History Found",
                color = Color.Gray,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        }
        return
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        Color(0xFF0F172A),
                        Color(0xFF111827),
                        Color(0xFF1E293B)
                    )
                )
            ),
        contentPadding = PaddingValues(14.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        itemsIndexed(list) { index, item ->
            HistoryCard(
                item = item,
                index = index,
                onClick = {
                    onItemClick?.invoke(item)
                }
            )
        }
    }
}

@Composable
fun HistoryCard(
    item: HistoryModel,
    index: Int,
    onClick: () -> Unit
) {
    val percentage = if (item.totalQuestions > 0)
        (item.correctAnswers * 100f) / item.totalQuestions
    else
        0f

    val modeColor by animateColorAsState(
        targetValue = when (item.mode.uppercase()) {
            "CHALLENGE" -> Color(0xFFEF4444)
            "FINAL_TEST" -> Color(0xFF8B5CF6)
            "SINGLE_PLAYER" -> Color(0xFF06B6D4)
            else -> Color(0xFF22C55E)
        },
        label = ""
    )

    val sdf = SimpleDateFormat(
        "dd MMM yyyy • hh:mm a",
        Locale.getDefault()
    )

    val icon = when (item.mode.uppercase()) {
        "CHALLENGE" -> Icons.Default.SportsEsports
        "FINAL_TEST" -> Icons.Default.Quiz
        "SINGLE_PLAYER" -> Icons.Default.Star
        else -> Icons.Default.History
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(
            containerColor = Color(0xFF111827)
        ),
        elevation = CardDefaults.cardElevation(
            defaultElevation = 7.dp
        )
    ) {
        Column(
            modifier = Modifier.padding(18.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(52.dp)
                        .clip(RoundedCornerShape(18.dp))
                        .background(modeColor.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = modeColor
                    )
                }

                Spacer(modifier = Modifier.width(14.dp))

                Column(
                    modifier = Modifier.weight(1f)
                ) {
                    Text(
                        text = item.title.ifBlank {
                            item.mode
                        },
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )

                    Spacer(modifier = Modifier.height(3.dp))

                    Text(
                        text = item.topic,
                        color = Color(0xFF94A3B8),
                        fontSize = 13.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                Column(
                    horizontalAlignment = Alignment.End
                ) {
                    Text(
                        text = "${percentage.toInt()}%",
                        color = modeColor,
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 20.sp
                    )

                    Text(
                        text = "#${index + 1}",
                        color = Color(0xFF64748B),
                        fontSize = 11.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            LinearProgressIndicator(
                progress = { (percentage / 100f).coerceIn(0f, 1f) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(9.dp)
                    .clip(RoundedCornerShape(999.dp)),
                color = modeColor,
                trackColor = Color(0xFF334155)
            )

            Spacer(modifier = Modifier.height(18.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                HistoryStatChip(
                    title = "Score",
                    value = item.score.toString(),
                    bg = Color(0xFF082F49),
                    fg = Color(0xFF38BDF8),
                    modifier = Modifier.weight(1f)
                )

                HistoryStatChip(
                    title = "Correct",
                    value = "${item.correctAnswers}/${item.totalQuestions}",
                    bg = Color(0xFF052E16),
                    fg = Color(0xFF4ADE80),
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                HistoryStatChip(
                    title = "Wrong",
                    value = item.wrongAnswers.toString(),
                    bg = Color(0xFF450A0A),
                    fg = Color(0xFFF87171),
                    modifier = Modifier.weight(1f)
                )

                HistoryStatChip(
                    title = "Mode",
                    value = item.mode,
                    bg = Color(0xFF1E1B4B),
                    fg = Color(0xFFA78BFA),
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(18.dp))

            HorizontalDivider(
                color = Color(0xFF1E293B)
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = sdf.format(Date(item.timestamp)),
                color = Color(0xFF94A3B8),
                fontSize = 12.sp
            )
        }
    }
}

@Composable
fun HistoryStatChip(
    title: String,
    value: String,
    bg: Color,
    fg: Color,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(18.dp),
        color = bg
    ) {
        Column(
            modifier = Modifier.padding(
                horizontal = 14.dp,
                vertical = 12.dp
            ),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = title,
                color = fg.copy(alpha = 0.8f),
                fontSize = 11.sp
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = value,
                color = fg,
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp,
                maxLines = 1
            )
        }
    }
}

class HistoryAdapter(private val items: List<HistoryModel>, private val onItemClick: (HistoryModel) -> Unit) : RecyclerView.Adapter<HistoryAdapter.ViewHolder>() {

    class ViewHolder(v: View) : RecyclerView.ViewHolder(v) {
        val title: TextView = v.findViewById(R.id.challengeTitle)
        val status: TextView = v.findViewById(R.id.challengeStatus)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val v = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_challenge_simple, parent, false)
        return ViewHolder(v)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]
        holder.title.text = item.title.ifBlank { item.topic }
        holder.status.text = "Score: ${item.score} | Correct: ${item.correctAnswers}/${item.totalQuestions}"
        holder.itemView.setOnClickListener { onItemClick(item) }
    }

    override fun getItemCount() = items.size
}