package com.rankwarz.edulabsrtm

import android.content.Context
import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.ImageView
import android.widget.TextView
import com.bumptech.glide.Glide
import com.bumptech.glide.request.RequestOptions

data class LobbyPlayer(
    val id: String = "",
    val name: String = "",
    val photo: String = "",
    val status: String = "waiting",
    val role: String = "guest"
)

class LobbyPlayerAdapter(
    private val context: Context,
    private val players: List<LobbyPlayer>
) : BaseAdapter() {

    override fun getCount() = players.size
    override fun getItem(position: Int) = players[position]
    override fun getItemId(position: Int) = position.toLong()

    override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
        val view = convertView ?: LayoutInflater.from(context).inflate(R.layout.item_lobby_player, parent, false)
        val player = players[position]

        val ivAvatar = view.findViewById<ImageView>(R.id.ivPlayerAvatar)
        val txtName = view.findViewById<TextView>(R.id.txtPlayerName)
        val txtRole = view.findViewById<TextView>(R.id.txtPlayerRole)
        val txtStatus = view.findViewById<TextView>(R.id.txtPlayerStatus)

        txtName.text = player.name
        txtRole.text = player.role.uppercase()
        txtStatus.text = player.status.uppercase()

        if (player.photo.isNotBlank()) {
            val fullUrl = if (player.photo.startsWith("http")) player.photo else "https://medigyaan.xyz/Neurons/" + player.photo.removePrefix("/")
            Glide.with(context)
                .load(fullUrl)
                .apply(RequestOptions.circleCropTransform())
                .placeholder(R.drawable.ic_person)
                .into(ivAvatar)
        } else {
            ivAvatar.setImageResource(R.drawable.ic_person)
        }

        when (player.status.lowercase()) {
            "ready" -> {
                txtStatus.setBackgroundResource(R.drawable.bg_status_badge_green)
                txtStatus.setTextColor(Color.WHITE)
            }
            "waiting" -> {
                txtStatus.setBackgroundResource(R.drawable.bg_status_badge)
                txtStatus.setTextColor(Color.WHITE)
            }
            else -> {
                txtStatus.setBackgroundResource(R.drawable.bg_status_badge_gray)
                txtStatus.setTextColor(Color.WHITE)
            }
        }

        return view
    }
}