package com.rankwarz.edulabsrtm

import android.app.Activity
import android.app.Dialog
import android.content.Context
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.Window
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide

object AvatarManager {

    const val PREFS_KEY_AVATAR_INDEX = "selected_avatar_id"
    const val PREFS_KEY_AVATAR_NAME = "selected_avatar_name"
    const val PREFS_KEY_AVATAR_TITLE = "selected_avatar_title"

    data class AnimalAvatar(
        val index: Int,
        val animalName: String,
        val characterName: String,
        val resId: Int
    ) {
        val title: String get() = "The $animalName • $characterName"
        val shortName: String get() = animalName
        val fileTag: String get() = "avatar_%02d".format(index + 1)
    }

    val AVATARS = listOf(
        AnimalAvatar(0, "Mantis", "Zerek", R.drawable.avatar_01),
        AnimalAvatar(1, "Octopus", "Octavius", R.drawable.avatar_02),
        AnimalAvatar(2, "Ram", "Balthazar", R.drawable.avatar_03),
        AnimalAvatar(3, "Bat", "Vesper", R.drawable.avatar_04),
        AnimalAvatar(4, "Pangolin", "Kaido", R.drawable.avatar_05),
        AnimalAvatar(5, "Vulture", "Malakor", R.drawable.avatar_06),
        AnimalAvatar(6, "Cheetah", "Swift", R.drawable.avatar_07),
        AnimalAvatar(7, "Beaver", "Thistle", R.drawable.avatar_08),
        AnimalAvatar(8, "Phoenix", "Pyra", R.drawable.avatar_09),
        AnimalAvatar(9, "Wolf", "Fenrir", R.drawable.avatar_10),
        AnimalAvatar(10, "Stag", "Cernun", R.drawable.avatar_11),
        AnimalAvatar(11, "Gorilla", "Titan", R.drawable.avatar_12),
        AnimalAvatar(12, "Crocodile", "Sobek", R.drawable.avatar_13),
        AnimalAvatar(13, "Leopard", "Orion", R.drawable.avatar_14),
        AnimalAvatar(14, "Rhino", "Goliath", R.drawable.avatar_15),
        AnimalAvatar(15, "Chameleon", "Spectra", R.drawable.avatar_16),
        AnimalAvatar(16, "Dolphin", "Echo", R.drawable.avatar_17),
        AnimalAvatar(17, "Scorpion", "Venom", R.drawable.avatar_18),
        AnimalAvatar(18, "Lion", "Aurelius", R.drawable.avatar_19),
        AnimalAvatar(19, "Raven", "Corvus", R.drawable.avatar_20),
        AnimalAvatar(20, "Elephant", "Ganesha", R.drawable.avatar_21),
        AnimalAvatar(21, "Bear", "Ursa", R.drawable.avatar_22),
        AnimalAvatar(22, "Fox", "Reynard", R.drawable.avatar_23),
        AnimalAvatar(23, "Tiger", "Tigris", R.drawable.avatar_24),
        AnimalAvatar(24, "Eagle", "Aquila", R.drawable.avatar_25),
        AnimalAvatar(25, "Cobra", "Naja", R.drawable.avatar_26),
        AnimalAvatar(26, "Stallion", "Pegasus", R.drawable.avatar_27)
    )

    val AVATAR_DRAWABLES: IntArray = AVATARS.map { it.resId }.toIntArray()

    fun getAvatar(index: Int): AnimalAvatar {
        val safeIndex = index.coerceIn(0, AVATARS.size - 1)
        return AVATARS[safeIndex]
    }

    fun getSelectedAvatar(context: Context): AnimalAvatar {
        val index = getSelectedAvatarIndex(context)
        return getAvatar(index)
    }

    fun getSelectedAvatarIndex(context: Context): Int {
        val prefs = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        return prefs.getInt(PREFS_KEY_AVATAR_INDEX, 0).coerceIn(0, AVATARS.size - 1)
    }

    fun getSelectedAvatarResId(context: Context): Int {
        return getSelectedAvatar(context).resId
    }

    fun getSelectedAvatarName(context: Context): String {
        return getSelectedAvatar(context).shortName
    }

    fun saveSelectedAvatar(context: Context, index: Int) {
        val avatar = getAvatar(index)
        val prefs = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        prefs.edit()
            .putInt(PREFS_KEY_AVATAR_INDEX, avatar.index)
            .putString(PREFS_KEY_AVATAR_NAME, avatar.animalName.lowercase())
            .putString(PREFS_KEY_AVATAR_TITLE, avatar.title)
            .apply()
    }

    fun getAvatarResId(index: Int): Int {
        return getAvatar(index).resId
    }

    fun getAvatarByName(name: String?): AnimalAvatar? {
        if (name.isNullOrBlank()) return null
        val query = name.trim().lowercase()

        // Match animal name, character name, or file tag
        return AVATARS.firstOrNull {
            it.animalName.equals(query, ignoreCase = true) ||
            it.characterName.equals(query, ignoreCase = true) ||
            it.fileTag.equals(query, ignoreCase = true) ||
            query == "avatar_${it.index + 1}" ||
            query == "avatar${it.index + 1}"
        }
    }

    fun getAvatarResIdByName(name: String?): Int? {
        return getAvatarByName(name)?.resId
    }

    fun getAvatarForIdentifier(identifier: String?): Int {
        if (identifier.isNullOrBlank()) return AVATARS[0].resId
        val hash = Math.abs(identifier.hashCode())
        val index = hash % AVATARS.size
        return AVATARS[index].resId
    }

    fun loadAvatar(
        context: Context,
        imageView: ImageView,
        customUrlOrName: String? = null,
        isMe: Boolean = false,
        fallbackIdentifier: String? = null
    ) {
        if (isMe) {
            val resId = getSelectedAvatarResId(context)
            Glide.with(context).load(resId).circleCrop().into(imageView)
            return
        }

        val matchedAvatar = getAvatarByName(customUrlOrName)
        if (matchedAvatar != null) {
            Glide.with(context).load(matchedAvatar.resId).circleCrop().into(imageView)
            return
        }

        if (!customUrlOrName.isNullOrBlank() && customUrlOrName != "null" && customUrlOrName.startsWith("http")) {
            val fallbackRes = getAvatarForIdentifier(fallbackIdentifier ?: customUrlOrName)
            Glide.with(context)
                .load(customUrlOrName)
                .circleCrop()
                .placeholder(fallbackRes)
                .error(fallbackRes)
                .into(imageView)
            return
        }

        val resId = getAvatarForIdentifier(fallbackIdentifier ?: customUrlOrName)
        Glide.with(context).load(resId).circleCrop().into(imageView)
    }

    fun showAvatarPicker(
        activity: Activity,
        onEquipped: ((avatarIndex: Int, resId: Int) -> Unit)? = null
    ) {
        val dialog = Dialog(activity)
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE)
        dialog.setContentView(R.layout.dialog_avatar_picker)
        dialog.window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
        dialog.window?.setLayout(
            (activity.resources.displayMetrics.widthPixels * 0.94).toInt(),
            ViewGroup.LayoutParams.WRAP_CONTENT
        )

        var selectedIndex = getSelectedAvatarIndex(activity)
        val initialEquippedIndex = selectedIndex

        val ivPreview = dialog.findViewById<ImageView>(R.id.ivSelectedAvatarPreview)
        val txtNamePreview = dialog.findViewById<TextView>(R.id.txtAvatarNamePreview)
        val txtStatusPreview = dialog.findViewById<TextView>(R.id.txtAvatarStatusPreview)
        val btnEquip = dialog.findViewById<Button>(R.id.btnEquipAvatar)
        val btnClose = dialog.findViewById<ImageView>(R.id.btnCloseDialog)
        val recyclerView = dialog.findViewById<RecyclerView>(R.id.recyclerAvatars)

        fun updatePreview(index: Int) {
            val avatar = getAvatar(index)
            ivPreview.setImageResource(avatar.resId)
            txtNamePreview.text = avatar.title
            if (index == initialEquippedIndex) {
                txtStatusPreview.text = "EQUIPPED"
                txtStatusPreview.setTextColor(Color.parseColor("#00FF41"))
                btnEquip.text = "EQUIPPED"
                btnEquip.isEnabled = false
                btnEquip.alpha = 0.6f
            } else {
                txtStatusPreview.text = "READY TO EQUIP"
                txtStatusPreview.setTextColor(Color.parseColor("#40C4FF"))
                btnEquip.text = "EQUIP"
                btnEquip.isEnabled = true
                btnEquip.alpha = 1.0f
            }
        }

        updatePreview(selectedIndex)

        var adapter: AvatarGridAdapter? = null
        adapter = AvatarGridAdapter(
            avatars = AVATARS,
            selectedIndex = selectedIndex,
            onItemClicked = { newIndex ->
                val prev = selectedIndex
                selectedIndex = newIndex
                adapter?.selectedIndex = newIndex
                adapter?.notifyItemChanged(prev)
                adapter?.notifyItemChanged(newIndex)
                updatePreview(newIndex)
            }
        )

        recyclerView.layoutManager = GridLayoutManager(activity, 3)
        recyclerView.adapter = adapter
        recyclerView.scrollToPosition(selectedIndex)

        btnEquip.setOnClickListener {
            saveSelectedAvatar(activity, selectedIndex)
            onEquipped?.invoke(selectedIndex, AVATARS[selectedIndex].resId)
            dialog.dismiss()
        }

        btnClose.setOnClickListener {
            dialog.dismiss()
        }

        dialog.show()
    }

    private class AvatarGridAdapter(
        private val avatars: List<AnimalAvatar>,
        var selectedIndex: Int,
        private val onItemClicked: (Int) -> Unit
    ) : RecyclerView.Adapter<AvatarGridAdapter.AvatarViewHolder>() {

        class AvatarViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val ivAvatar: ImageView = view.findViewById(R.id.ivAvatarItem)
            val ivCheck: ImageView = view.findViewById(R.id.ivAvatarCheck)
            val txtNum: TextView = view.findViewById(R.id.txtAvatarNum)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): AvatarViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_avatar_grid, parent, false)
            return AvatarViewHolder(view)
        }

        override fun onBindViewHolder(holder: AvatarViewHolder, position: Int) {
            val avatar = avatars[position]
            holder.ivAvatar.setImageResource(avatar.resId)
            holder.txtNum.text = avatar.animalName

            val isSelected = position == selectedIndex
            if (isSelected) {
                holder.ivAvatar.setBackgroundResource(R.drawable.bg_avatar_selected)
                holder.ivCheck.visibility = View.VISIBLE
                holder.txtNum.setTextColor(Color.parseColor("#00FF41"))
            } else {
                holder.ivAvatar.setBackgroundResource(R.drawable.bg_avatar_unselected)
                holder.ivCheck.visibility = View.GONE
                holder.txtNum.setTextColor(Color.parseColor("#B3FFFFFF"))
            }

            holder.itemView.setOnClickListener {
                onItemClicked(position)
            }
        }

        override fun getItemCount(): Int = avatars.size
    }
}
