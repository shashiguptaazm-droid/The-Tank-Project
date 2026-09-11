package com.rankwarz.edulabsrtm

import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.cardview.widget.CardView
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.rankwarz.edulabsrtm.util.AiDocumentOcrHelper
import com.rankwarz.edulabsrtm.util.DownloadHelper
import com.rankwarz.edulabsrtm.util.LinkPreviewData
import com.rankwarz.edulabsrtm.util.LinkPreviewHelper
import com.rankwarz.edulabsrtm.util.MediaCacheManager
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale

class MessageAdapter(
    private val currentUserId: Int,
    private val onImageClick: (String) -> Unit,
    private val onFileClick: (String) -> Unit,
    private val onCallInviteClick: (String) -> Unit,
    private val onDeleteMessage: (ChatMessage, Int) -> Unit,
    private val onAskAiAboutDocument: (String, String) -> Unit
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private val messages = mutableListOf<ChatMessage>()

    companion object {
        private const val TYPE_SENT = 1
        private const val TYPE_RECEIVED = 2
    }

    fun addMessage(msg: ChatMessage) {
        messages.add(msg)
        notifyItemInserted(messages.size - 1)
    }

    fun setMessages(newList: List<ChatMessage>) {
        messages.clear()
        messages.addAll(newList)
        notifyDataSetChanged()
    }

    fun removeMessageAt(position: Int) {
        if (position >= 0 && position < messages.size) {
            messages.removeAt(position)
            notifyItemRemoved(position)
        }
    }

    fun updateMessageAt(position: Int, newMsg: ChatMessage) {
        if (position in messages.indices) {
            messages[position] = newMsg
            notifyItemChanged(position)
        } else {
            addMessage(newMsg)
        }
    }

    fun getMessageAt(position: Int): ChatMessage? {
        return if (position in messages.indices) messages[position] else null
    }

    override fun getItemViewType(position: Int): Int {
        return if (messages[position].senderId == currentUserId) TYPE_SENT else TYPE_RECEIVED
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        return if (viewType == TYPE_SENT) {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_message_sent, parent, false)
            SentViewHolder(view)
        } else {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_message_received, parent, false)
            ReceivedViewHolder(view)
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = messages[position]
        if (holder is SentViewHolder) holder.bind(message, position)
        else if (holder is ReceivedViewHolder) holder.bind(message, position)
    }

    override fun getItemCount(): Int = messages.size

    inner class SentViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val text: TextView = view.findViewById(R.id.messageText)
        private val time: TextView = view.findViewById(R.id.messageTime)
        private val status: TextView = view.findViewById(R.id.messageStatus)
        private val askAiBtn: TextView = view.findViewById(R.id.askAiBtn)
        private val bubbleLayout: View = view.findViewById(R.id.bubbleLayout)
        private val aiHeaderLayout: View? = view.findViewById(R.id.aiHeaderLayout)

        // Media Card views
        private val mediaCard: CardView = view.findViewById(R.id.mediaCard)
        private val messageImage: ImageView = view.findViewById(R.id.messageImage)
        private val videoPlayOverlay: View = view.findViewById(R.id.videoPlayOverlay)
        private val videoDuration: TextView = view.findViewById(R.id.videoDuration)
        private val videoDownloadOverlay: View = view.findViewById(R.id.videoDownloadOverlay)
        private val icVideoDownloadArrow: ImageView = view.findViewById(R.id.icVideoDownloadArrow)
        private val videoDownloadProgress: ProgressBar = view.findViewById(R.id.videoDownloadProgress)
        private val videoDownloadText: TextView = view.findViewById(R.id.videoDownloadText)
        private val btnMediaDownload: ImageButton = view.findViewById(R.id.btnMediaDownload)

        // Document Card views
        private val documentCard: CardView = view.findViewById(R.id.documentCard)
        private val docThumbnail: ImageView = view.findViewById(R.id.docThumbnail)
        private val docTypeBadge: TextView = view.findViewById(R.id.docTypeBadge)
        private val docPageCount: TextView = view.findViewById(R.id.docPageCount)
        private val docTitle: TextView = view.findViewById(R.id.docTitle)
        private val docSubtitle: TextView = view.findViewById(R.id.docSubtitle)
        private val btnDocDownload: ImageButton = view.findViewById(R.id.btnDocDownload)

        // Link Preview views
        private val linkPreviewCard: CardView = view.findViewById(R.id.linkPreviewCard)
        private val linkThumb: ImageView = view.findViewById(R.id.linkThumb)
        private val linkDomain: TextView = view.findViewById(R.id.linkDomain)
        private val linkTitle: TextView = view.findViewById(R.id.linkTitle)
        private val linkDesc: TextView = view.findViewById(R.id.linkDesc)

        fun bind(msg: ChatMessage, position: Int) {
            bindShared(
                msg = msg,
                position = position,
                textTv = text,
                timeTv = time,
                askAiBtn = askAiBtn,
                aiHeaderLayout = aiHeaderLayout,
                mediaCard = mediaCard,
                imageIv = messageImage,
                videoPlayOverlay = videoPlayOverlay,
                videoDuration = videoDuration,
                videoDownloadOverlay = videoDownloadOverlay,
                icVideoDownloadArrow = icVideoDownloadArrow,
                videoDownloadProgress = videoDownloadProgress,
                videoDownloadText = videoDownloadText,
                btnMediaDownload = btnMediaDownload,
                documentCard = documentCard,
                docThumbnail = docThumbnail,
                docTypeBadge = docTypeBadge,
                docPageCount = docPageCount,
                docTitle = docTitle,
                docSubtitle = docSubtitle,
                btnDocDownload = btnDocDownload,
                linkPreviewCard = linkPreviewCard,
                linkThumb = linkThumb,
                linkDomain = linkDomain,
                linkTitle = linkTitle,
                linkDesc = linkDesc
            )

            status.text = if (msg.isRead == 1) " \u2713\u2713" else " \u2713"
            status.setTextColor(if (msg.isRead == 1) 0xFF34B7F1.toInt() else 0xFF808080.toInt())

            itemView.setOnLongClickListener {
                showMessageOptions(itemView, msg, position)
                true
            }
        }
    }

    inner class ReceivedViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val text: TextView = view.findViewById(R.id.messageText)
        private val time: TextView = view.findViewById(R.id.messageTime)
        private val askAiBtn: TextView = view.findViewById(R.id.askAiBtn)
        private val bubbleLayout: View = view.findViewById(R.id.bubbleLayout)
        private val aiHeaderLayout: View? = view.findViewById(R.id.aiHeaderLayout)

        // Media Card views
        private val mediaCard: CardView = view.findViewById(R.id.mediaCard)
        private val messageImage: ImageView = view.findViewById(R.id.messageImage)
        private val videoPlayOverlay: View = view.findViewById(R.id.videoPlayOverlay)
        private val videoDuration: TextView = view.findViewById(R.id.videoDuration)
        private val videoDownloadOverlay: View = view.findViewById(R.id.videoDownloadOverlay)
        private val icVideoDownloadArrow: ImageView = view.findViewById(R.id.icVideoDownloadArrow)
        private val videoDownloadProgress: ProgressBar = view.findViewById(R.id.videoDownloadProgress)
        private val videoDownloadText: TextView = view.findViewById(R.id.videoDownloadText)
        private val btnMediaDownload: ImageButton = view.findViewById(R.id.btnMediaDownload)

        // Document Card views
        private val documentCard: CardView = view.findViewById(R.id.documentCard)
        private val docThumbnail: ImageView = view.findViewById(R.id.docThumbnail)
        private val docTypeBadge: TextView = view.findViewById(R.id.docTypeBadge)
        private val docPageCount: TextView = view.findViewById(R.id.docPageCount)
        private val docTitle: TextView = view.findViewById(R.id.docTitle)
        private val docSubtitle: TextView = view.findViewById(R.id.docSubtitle)
        private val btnDocDownload: ImageButton = view.findViewById(R.id.btnDocDownload)

        // Link Preview views
        private val linkPreviewCard: CardView = view.findViewById(R.id.linkPreviewCard)
        private val linkThumb: ImageView = view.findViewById(R.id.linkThumb)
        private val linkDomain: TextView = view.findViewById(R.id.linkDomain)
        private val linkTitle: TextView = view.findViewById(R.id.linkTitle)
        private val linkDesc: TextView = view.findViewById(R.id.linkDesc)

        fun bind(msg: ChatMessage, position: Int) {
            bindShared(
                msg = msg,
                position = position,
                textTv = text,
                timeTv = time,
                askAiBtn = askAiBtn,
                aiHeaderLayout = aiHeaderLayout,
                mediaCard = mediaCard,
                imageIv = messageImage,
                videoPlayOverlay = videoPlayOverlay,
                videoDuration = videoDuration,
                videoDownloadOverlay = videoDownloadOverlay,
                icVideoDownloadArrow = icVideoDownloadArrow,
                videoDownloadProgress = videoDownloadProgress,
                videoDownloadText = videoDownloadText,
                btnMediaDownload = btnMediaDownload,
                documentCard = documentCard,
                docThumbnail = docThumbnail,
                docTypeBadge = docTypeBadge,
                docPageCount = docPageCount,
                docTitle = docTitle,
                docSubtitle = docSubtitle,
                btnDocDownload = btnDocDownload,
                linkPreviewCard = linkPreviewCard,
                linkThumb = linkThumb,
                linkDomain = linkDomain,
                linkTitle = linkTitle,
                linkDesc = linkDesc
            )

            itemView.setOnLongClickListener {
                showMessageOptions(itemView, msg, position)
                true
            }
        }
    }

    private fun bindShared(
        msg: ChatMessage,
        position: Int,
        textTv: TextView,
        timeTv: TextView,
        askAiBtn: TextView,
        aiHeaderLayout: View?,
        mediaCard: CardView,
        imageIv: ImageView,
        videoPlayOverlay: View,
        videoDuration: TextView,
        videoDownloadOverlay: View,
        icVideoDownloadArrow: ImageView,
        videoDownloadProgress: ProgressBar,
        videoDownloadText: TextView,
        btnMediaDownload: ImageButton,
        documentCard: CardView,
        docThumbnail: ImageView,
        docTypeBadge: TextView,
        docPageCount: TextView,
        docTitle: TextView,
        docSubtitle: TextView,
        btnDocDownload: ImageButton,
        linkPreviewCard: CardView,
        linkThumb: ImageView,
        linkDomain: TextView,
        linkTitle: TextView,
        linkDesc: TextView
    ) {
        val context = textTv.context

        // 1. Video and audio call invites check
        if (msg.text.startsWith("VIDEO_CALL_INVITE:") || msg.text.startsWith("AUDIO_CALL_INVITE:")) {
            val isVideo = msg.text.startsWith("VIDEO_CALL_INVITE:")
            val room = if (isVideo) msg.text.substringAfter("VIDEO_CALL_INVITE:") else msg.text.substringAfter("AUDIO_CALL_INVITE:")
            textTv.text = if (isVideo) "📹 Video Call Invite (Tap to join)" else "📞 Audio Call Invite (Tap to join)"
            textTv.setOnClickListener { onCallInviteClick(room) }
            mediaCard.visibility = View.GONE
            documentCard.visibility = View.GONE
            linkPreviewCard.visibility = View.GONE
            askAiBtn.visibility = View.GONE
            aiHeaderLayout?.visibility = View.GONE
            timeTv.text = formatTime(msg.sentAt)
            return
        }

        // 2. Regular message text & WhatsApp-style Meta AI Header
        val isAiMessage = msg.senderId == 0 || msg.text.startsWith("🤖 MediGyaan AI", ignoreCase = true)
        if (isAiMessage) {
            aiHeaderLayout?.visibility = View.VISIBLE
            val cleanContent = msg.text
                .removePrefix("🤖 MediGyaan AI:\n\n")
                .removePrefix("🤖 MediGyaan AI:\n")
                .removePrefix("🤖 MediGyaan AI:")
                .trim()
            textTv.text = aiMarkdownSpannable(cleanContent)
        } else if (msg.text.startsWith("🤖 @medigyaanAI", ignoreCase = true)) {
            aiHeaderLayout?.visibility = View.VISIBLE
            textTv.text = aiMarkdownSpannable(msg.text)
        } else {
            aiHeaderLayout?.visibility = View.GONE
            textTv.text = msg.text
        }
        textTv.visibility = if (textTv.text.isNotEmpty()) View.VISIBLE else View.GONE
        textTv.setOnClickListener(null)
        timeTv.text = formatTime(msg.sentAt)

        // 3. Link Preview (WhatsApp style)
        val extractedUrl = LinkPreviewHelper.extractFirstUrl(msg.text)
        if (extractedUrl != null) {
            linkPreviewCard.visibility = View.VISIBLE
            linkPreviewCard.tag = extractedUrl

            val cached = LinkPreviewHelper.getCachedPreview(extractedUrl)
            if (cached != null) {
                bindLinkPreviewData(cached, linkPreviewCard, linkThumb, linkDomain, linkTitle, linkDesc)
            } else {
                linkDomain.text = Uri.parse(extractedUrl).host?.removePrefix("www.") ?: "Link"
                linkTitle.text = extractedUrl
                linkDesc.text = "Loading preview..."
                linkThumb.visibility = View.GONE

                LinkPreviewHelper.fetchPreview(extractedUrl) { data ->
                    if (linkPreviewCard.tag == extractedUrl && data != null) {
                        bindLinkPreviewData(data, linkPreviewCard, linkThumb, linkDomain, linkTitle, linkDesc)
                    }
                }
            }

            linkPreviewCard.setOnClickListener {
                try {
                    val browserIntent = Intent(Intent.ACTION_VIEW, Uri.parse(extractedUrl))
                    context.startActivity(browserIntent)
                } catch (e: Exception) {
                    Toast.makeText(context, "Cannot open link: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        } else {
            linkPreviewCard.visibility = View.GONE
            linkPreviewCard.tag = null
        }

        // 4. Attachments Handling
        if (msg.attachment.isNotBlank() && msg.attachment != "null") {
            val fullUrl = MediaCacheManager.resolveFullUrl(msg.attachment)
            val fileName = msg.attachment.substringAfterLast("/")
            val ext = fileName.substringAfterLast(".", "").lowercase()

            when {
                // =========================================================
                // 1. VIDEO (Playback ONLY allowed once downloaded/cached)
                // =========================================================
                isVideo(ext) -> {
                    mediaCard.visibility = View.VISIBLE
                    documentCard.visibility = View.GONE
                    askAiBtn.visibility = View.GONE

                    val isCached = MediaCacheManager.isVideoDownloaded(context, fullUrl)
                    val isDownloading = MediaCacheManager.isVideoDownloading(fullUrl)

                    // Load frame thumbnail with Glide
                    val videoSource = if (isCached) {
                        MediaCacheManager.getCachedVideoFile(context, fullUrl)
                    } else {
                        fullUrl
                    }

                    Glide.with(context)
                        .asBitmap()
                        .load(videoSource)
                        .frame(1_000_000)
                        .centerCrop()
                        .into(imageIv)

                    if (isCached) {
                        // DOWNLOADED: Show Play button in center
                        videoDownloadOverlay.visibility = View.GONE
                        videoPlayOverlay.visibility = View.VISIBLE
                        videoDuration.visibility = View.GONE

                        // Play strictly from cached local file!
                        val localFile = MediaCacheManager.getCachedVideoFile(context, fullUrl)
                        val playAction = View.OnClickListener {
                            val intent = Intent(context, VideoPlayerActivity::class.java).apply {
                                putExtra("VIDEO_URL", localFile.absolutePath)
                                putExtra("VIDEO_TITLE", fileName)
                            }
                            context.startActivity(intent)
                        }

                        mediaCard.setOnClickListener(playAction)
                        imageIv.setOnClickListener(playAction)
                        videoPlayOverlay.setOnClickListener(playAction)

                        // Save to Downloads folder button
                        btnMediaDownload.visibility = View.VISIBLE
                        btnMediaDownload.setOnClickListener {
                            DownloadHelper.downloadFile(context, fullUrl, fileName)
                        }
                    } else {
                        // NOT DOWNLOADED YET: Playback blocked until downloaded!
                        videoPlayOverlay.visibility = View.GONE
                        videoDownloadOverlay.visibility = View.VISIBLE

                        if (isDownloading) {
                            icVideoDownloadArrow.visibility = View.GONE
                            videoDownloadProgress.visibility = View.VISIBLE
                            videoDownloadText.text = "Downloading..."
                        } else {
                            icVideoDownloadArrow.visibility = View.VISIBLE
                            videoDownloadProgress.visibility = View.GONE
                            videoDownloadText.text = "Tap to Download"
                        }

                        val startDownloadAction = View.OnClickListener {
                            if (MediaCacheManager.isVideoDownloading(fullUrl)) return@OnClickListener
                            
                            icVideoDownloadArrow.visibility = View.GONE
                            videoDownloadProgress.visibility = View.VISIBLE
                            videoDownloadText.text = "Downloading..."
                            Toast.makeText(context, "Downloading video...", Toast.LENGTH_SHORT).show()

                            MediaCacheManager.downloadVideo(
                                context = context,
                                url = fullUrl,
                                onProgress = { percent ->
                                    videoDownloadText.text = "$percent%"
                                },
                                onComplete = { file ->
                                    if (file != null && file.exists()) {
                                        Toast.makeText(context, "Video ready to play!", Toast.LENGTH_SHORT).show()
                                        notifyItemChanged(position)
                                    } else {
                                        icVideoDownloadArrow.visibility = View.VISIBLE
                                        videoDownloadProgress.visibility = View.GONE
                                        videoDownloadText.text = "Tap to Retry"
                                        Toast.makeText(context, "Download failed", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            )
                        }

                        mediaCard.setOnClickListener(startDownloadAction)
                        imageIv.setOnClickListener(startDownloadAction)
                        videoDownloadOverlay.setOnClickListener(startDownloadAction)
                        btnMediaDownload.setOnClickListener(startDownloadAction)
                    }
                }

                // =========================================================
                // 2. IMAGE
                // =========================================================
                isImage(ext) -> {
                    mediaCard.visibility = View.VISIBLE
                    documentCard.visibility = View.GONE
                    askAiBtn.visibility = View.VISIBLE
                    askAiBtn.setOnClickListener {
                        onAskAiAboutDocument(fullUrl, msg.text)
                    }
                    videoPlayOverlay.visibility = View.GONE
                    videoDownloadOverlay.visibility = View.GONE

                    Glide.with(context)
                        .load(fullUrl)
                        .centerCrop()
                        .into(imageIv)

                    imageIv.setOnClickListener { onImageClick(fullUrl) }
                    mediaCard.setOnClickListener { onImageClick(fullUrl) }

                    btnMediaDownload.visibility = View.VISIBLE
                    btnMediaDownload.setOnClickListener {
                        DownloadHelper.downloadFile(context, fullUrl, fileName)
                    }
                }

                // =========================================================
                // 3. DOCUMENT (1st Page Converted to Image & Preloaded)
                // =========================================================
                else -> {
                    mediaCard.visibility = View.GONE
                    documentCard.visibility = View.VISIBLE

                    val eligibleForAi = AiDocumentOcrHelper.isEligibleForAi(ext)
                    askAiBtn.visibility = if (eligibleForAi) View.VISIBLE else View.GONE
                    if (eligibleForAi) {
                        askAiBtn.setOnClickListener {
                            onAskAiAboutDocument(fullUrl, msg.text)
                        }
                    } else {
                        askAiBtn.setOnClickListener(null)
                    }

                    docTitle.text = fileName
                    val docType = getDocumentType(ext)
                    val docBadgeColor = getDocumentBadgeColor(docType)
                    val docBadgeText = docType.uppercase().take(4)

                    docTypeBadge.text = docBadgeText
                    setDocBadgeBackground(docTypeBadge, docBadgeColor)

                    docSubtitle.text = "${docType.uppercase()} Document"

                    // Check if 1st page image thumbnail is already cached
                    val cachedThumb = MediaCacheManager.getCachedThumbnail(fullUrl)
                    val cachedPages = MediaCacheManager.getCachedPageCount(fullUrl)

                    if (cachedThumb != null) {
                        docThumbnail.setImageBitmap(cachedThumb)
                        docThumbnail.scaleType = ImageView.ScaleType.CENTER_CROP
                        if (cachedPages != null && cachedPages > 1) {
                            docPageCount.visibility = View.VISIBLE
                            docPageCount.text = "$cachedPages pages"
                        } else {
                            docPageCount.visibility = View.GONE
                        }
                    } else {
                        // Preload document and convert 1st page to image
                        docThumbnail.tag = fullUrl
                        docPageCount.visibility = View.GONE

                        MediaCacheManager.preloadDocumentAndGetFirstPage(context, fullUrl) { bitmap, pageCount ->
                            if (docThumbnail.tag == fullUrl && bitmap != null) {
                                docThumbnail.setImageBitmap(bitmap)
                                docThumbnail.scaleType = ImageView.ScaleType.CENTER_CROP
                                if (pageCount > 1) {
                                    docPageCount.visibility = View.VISIBLE
                                    docPageCount.text = "$pageCount pages"
                                }
                            }
                        }
                    }

                    val openDocAction = View.OnClickListener {
                        openDocumentInVps(it, fullUrl, msg.attachment)
                    }
                    documentCard.setOnClickListener(openDocAction)
                    docThumbnail.setOnClickListener(openDocAction)

                    // Download to phone button
                    btnDocDownload.setOnClickListener {
                        DownloadHelper.downloadFile(context, fullUrl, fileName)
                    }
                }
            }
        } else {
            mediaCard.visibility = View.GONE
            documentCard.visibility = View.GONE
            askAiBtn.visibility = View.GONE
            askAiBtn.setOnClickListener(null)
        }
    }

    private fun bindLinkPreviewData(
        data: LinkPreviewData,
        card: CardView,
        thumb: ImageView,
        domain: TextView,
        title: TextView,
        desc: TextView
    ) {
        domain.text = data.domain
        title.text = data.title
        if (data.description.isNotBlank()) {
            desc.visibility = View.VISIBLE
            desc.text = data.description
        } else {
            desc.visibility = View.GONE
        }

        if (!data.imageUrl.isNullOrBlank()) {
            thumb.visibility = View.VISIBLE
            Glide.with(card.context)
                .load(data.imageUrl)
                .centerCrop()
                .into(thumb)
        } else {
            thumb.visibility = View.GONE
        }
    }

    private fun setDocBadgeBackground(textView: TextView, color: Int) {
        val drawable = GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = 10f
            setColor(color)
        }
        textView.background = drawable
    }

    private fun getDocumentType(ext: String): String {
        return when (ext.lowercase()) {
            "pdf" -> "pdf"
            "doc", "docx" -> "word"
            "ppt", "pptx" -> "ppt"
            "xls", "xlsx", "csv" -> "excel"
            "txt", "md", "json", "xml" -> "txt"
            "zip", "rar", "7z", "tar", "gz" -> "zip"
            else -> if (ext.isNotBlank()) ext else "file"
        }
    }

    private fun getDocumentBadgeColor(docType: String): Int {
        return when (docType) {
            "pdf" -> Color.parseColor("#E53935")   // Red
            "word" -> Color.parseColor("#1E88E5")  // Blue
            "ppt" -> Color.parseColor("#FB8C00")   // Orange
            "excel" -> Color.parseColor("#43A047") // Green
            "txt" -> Color.parseColor("#546E7A")   // Slate
            "zip" -> Color.parseColor("#8E24AA")   // Purple
            else -> Color.parseColor("#78909C")
        }
    }

    private fun openDocumentInVps(view: View, url: String, originalPath: String) {
        val viewerUrl = "https://docs.google.com/viewer?embedded=true&url=$url"
        val intent = Intent(view.context, WebViewActivity::class.java).putExtra("url", viewerUrl)
        intent.putExtra("title", originalPath.substringAfterLast("/"))
        view.context.startActivity(intent)
    }

    private fun showMessageOptions(view: View, msg: ChatMessage, position: Int) {
        val popup = PopupMenu(view.context, view)
        popup.menuInflater.inflate(R.menu.message_long_press_menu, popup.menu)

        // Only show delete for own messages
        if (msg.senderId != currentUserId) {
            popup.menu.findItem(R.id.action_delete)?.isVisible = false
        }

        // Only show download if message has attachment
        val hasAttachment = msg.attachment.isNotBlank() && msg.attachment != "null"
        popup.menu.findItem(R.id.action_download)?.isVisible = hasAttachment

        popup.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                R.id.action_download -> {
                    if (hasAttachment) {
                        val fullUrl = MediaCacheManager.resolveFullUrl(msg.attachment)
                        val fileName = msg.attachment.substringAfterLast("/")
                        DownloadHelper.downloadFile(view.context, fullUrl, fileName)
                    }
                    true
                }
                R.id.action_copy -> {
                    val clipboard = view.context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    val clip = android.content.ClipData.newPlainText("Message", msg.text)
                    clipboard.setPrimaryClip(clip)
                    Toast.makeText(view.context, "Copied to clipboard", Toast.LENGTH_SHORT).show()
                    true
                }
                R.id.action_delete -> {
                    onDeleteMessage(msg, position)
                    true
                }
                else -> false
            }
        }
        popup.show()
    }

    private fun isImage(ext: String): Boolean {
        return listOf("jpg", "jpeg", "png", "gif", "webp", "bmp", "heic").contains(ext.lowercase())
    }

    private fun isVideo(ext: String): Boolean {
        return listOf("mp4", "mkv", "webm", "3gp", "mov", "avi", "ts", "flv", "m4v").contains(ext.lowercase())
    }

    private fun formatTime(sentAt: String): String {
        return try {
            val sdfSource = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
            val date = sdfSource.parse(sentAt) ?: return sentAt
            SimpleDateFormat("hh:mm a", Locale.getDefault()).format(date)
        } catch (e: Exception) { sentAt }
    }
}