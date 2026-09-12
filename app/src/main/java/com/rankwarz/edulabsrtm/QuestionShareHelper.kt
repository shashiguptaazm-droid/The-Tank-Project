package com.rankwarz.edulabsrtm

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.net.Uri
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File
import java.io.FileOutputStream

object QuestionShareHelper {

    private const val TAG = "QuestionShareHelper"
    private const val FILE_PROVIDER_AUTHORITY = "com.corp.medigyaan.fileprovider"

    data class QuestionShareData(
        val questionId: Int,
        val questionText: String,
        val optionA: String,
        val optionB: String,
        val optionC: String,
        val optionD: String,
        val subject: String,
        val topic: String,
        val imageUrl: String? = null,
        val userId: Int = 0,
        val correctAnswer: String? = null,
        val explanation: String? = null,
        val isAnswered: Boolean = false
    )

    fun buildShareUrl(questionId: Int, userId: Int): String {
        return "https://medigyaan.xyz/Neurons/share.php?question_id=$questionId&ref=$userId"
    }

    /**
     * Builds clean, formatted question text with emojis, options, and challenge link.
     */
    fun buildShareText(data: QuestionShareData, includeAnswer: Boolean = false): String {
        val sb = StringBuilder()
        sb.append("🧠 *MediGyaan Medical MCQ Challenge*\n")

        val subjectPart = data.subject.trim().takeIf { it.isNotBlank() && it != "null" } ?: "NEET PG"
        val topicPart = data.topic.trim().takeIf { it.isNotBlank() && it != "null" && it != "General" && it != "Uncategorized" }
        sb.append("📚 *Subject:* $subjectPart")
        if (topicPart != null) {
            sb.append(" • *Topic:* $topicPart")
        }
        sb.append("\n\n")

        val cleanQuestion = data.questionText.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
        sb.append("*Q:* $cleanQuestion\n\n")

        val cleanA = data.optionA.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
        val cleanB = data.optionB.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
        val cleanC = data.optionC.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
        val cleanD = data.optionD.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()

        sb.append("A) $cleanA\n")
        sb.append("B) $cleanB\n")
        sb.append("C) $cleanC\n")
        sb.append("D) $cleanD\n\n")

        if (includeAnswer && !data.correctAnswer.isNullOrBlank()) {
            sb.append("✅ *Correct Answer:* Option ${data.correctAnswer.trim()}\n")
            if (!data.explanation.isNullOrBlank()) {
                val cleanExp = data.explanation.trim()
                sb.append("💡 *Explanation:* $cleanExp\n\n")
            } else {
                sb.append("\n")
            }
        }

        val shareUrl = buildShareUrl(data.questionId, data.userId)
        sb.append("🎯 *Think you know the answer? Solve & compete on MediGyaan:*\n")
        sb.append("👉 $shareUrl\n\n")
        sb.append("#MediGyaan #NEETPG #MedicalMCQ #NextExam")
        return sb.toString()
    }

    /**
     * Renders a branded high-resolution question card Bitmap (width 1080px) and writes
     * it to cacheDir/shared_images, returning a FileProvider content:// URI.
     */
    fun createQuestionCardImageUri(
        context: Context,
        data: QuestionShareData,
        includeAnswer: Boolean = false,
        attachedBitmap: Bitmap? = null
    ): Uri? {
        return runCatching {
            val inflater = LayoutInflater.from(context)
            val cardView = inflater.inflate(R.layout.layout_question_share_card, null)

            val topicBadge = cardView.findViewById<TextView>(R.id.shareCardTopicBadge)
            val questionText = cardView.findViewById<TextView>(R.id.shareCardQuestionText)
            val optionAText = cardView.findViewById<TextView>(R.id.shareCardOptionAText)
            val optionBText = cardView.findViewById<TextView>(R.id.shareCardOptionBText)
            val optionCText = cardView.findViewById<TextView>(R.id.shareCardOptionCText)
            val optionDText = cardView.findViewById<TextView>(R.id.shareCardOptionDText)
            val questionImage = cardView.findViewById<ImageView>(R.id.shareCardQuestionImage)
            val answerLayout = cardView.findViewById<LinearLayout>(R.id.shareCardAnswerLayout)
            val answerText = cardView.findViewById<TextView>(R.id.shareCardAnswerText)
            val explanationText = cardView.findViewById<TextView>(R.id.shareCardExplanationText)

            val subjectTopic = if (data.topic.isNotBlank() && data.topic != "General" && data.topic != "Uncategorized") {
                "${data.subject} • ${data.topic}"
            } else {
                data.subject.ifBlank { "NEET PG" }
            }
            topicBadge.text = subjectTopic

            val cleanQuestion = data.questionText.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
            questionText.text = cleanQuestion

            optionAText.text = data.optionA.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
            optionBText.text = data.optionB.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
            optionCText.text = data.optionC.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
            optionDText.text = data.optionD.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()

            if (attachedBitmap != null) {
                questionImage.visibility = View.VISIBLE
                questionImage.setImageBitmap(attachedBitmap)
            } else {
                questionImage.visibility = View.GONE
            }

            if (includeAnswer && !data.correctAnswer.isNullOrBlank()) {
                answerLayout.visibility = View.VISIBLE
                answerText.text = "✅ Correct Answer: Option ${data.correctAnswer.trim()}"
                if (!data.explanation.isNullOrBlank()) {
                    explanationText.visibility = View.VISIBLE
                    explanationText.text = data.explanation.trim()
                } else {
                    explanationText.visibility = View.GONE
                }
            } else {
                answerLayout.visibility = View.GONE
            }

            // Measure & Layout at standard 1080px width
            val targetWidth = 1080
            val widthSpec = View.MeasureSpec.makeMeasureSpec(targetWidth, View.MeasureSpec.EXACTLY)
            val heightSpec = View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED)
            cardView.measure(widthSpec, heightSpec)

            val targetHeight = cardView.measuredHeight.coerceAtLeast(1080)
            cardView.layout(0, 0, targetWidth, targetHeight)

            val bitmap = Bitmap.createBitmap(targetWidth, targetHeight, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bitmap)
            cardView.draw(canvas)

            // Save to cache directory
            val cacheDir = File(context.cacheDir, "shared_images").apply { mkdirs() }
            val file = File(cacheDir, "question_${data.questionId}_${System.currentTimeMillis()}.png")
            FileOutputStream(file).use { out ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }
            bitmap.recycle()

            FileProvider.getUriForFile(context, FILE_PROVIDER_AUTHORITY, file)
        }.getOrElse { e ->
            Log.e(TAG, "Failed to create question card image: ${e.message}", e)
            null
        }
    }

    /**
     * Share directly to WhatsApp (personal or business) with fallback to web or system chooser.
     */
    fun shareToWhatsApp(
        context: Context,
        data: QuestionShareData,
        asImage: Boolean,
        includeAnswer: Boolean,
        attachedBitmap: Bitmap? = null
    ) {
        val textMessage = buildShareText(data, includeAnswer)
        val imageUri = if (asImage) createQuestionCardImageUri(context, data, includeAnswer, attachedBitmap) else null

        val packages = listOf("com.whatsapp", "com.whatsapp.w4b")
        var targetPkg: String? = null
        for (pkg in packages) {
            if (isPackageInstalled(context, pkg)) {
                targetPkg = pkg
                break
            }
        }

        if (targetPkg != null) {
            val intent = Intent(Intent.ACTION_SEND).apply {
                `package` = targetPkg
                if (imageUri != null) {
                    type = "image/png"
                    putExtra(Intent.EXTRA_STREAM, imageUri)
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                } else {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                }
            }
            runCatching {
                context.startActivity(intent)
                return
            }
        }

        // WhatsApp web fallback if text only
        if (!asImage) {
            val webUri = Uri.parse("https://api.whatsapp.com/send?text=${Uri.encode(textMessage)}")
            runCatching {
                context.startActivity(Intent(Intent.ACTION_VIEW, webUri))
                return
            }
        }

        // Fallback to chooser
        shareChooser(context, data, asImage, includeAnswer, attachedBitmap)
    }

    /**
     * Share directly to Telegram with fallback to t.me or system chooser.
     */
    fun shareToTelegram(
        context: Context,
        data: QuestionShareData,
        asImage: Boolean,
        includeAnswer: Boolean,
        attachedBitmap: Bitmap? = null
    ) {
        val textMessage = buildShareText(data, includeAnswer)
        val imageUri = if (asImage) createQuestionCardImageUri(context, data, includeAnswer, attachedBitmap) else null
        val telegramPkg = "org.telegram.messenger"

        if (isPackageInstalled(context, telegramPkg)) {
            val intent = Intent(Intent.ACTION_SEND).apply {
                `package` = telegramPkg
                if (imageUri != null) {
                    type = "image/png"
                    putExtra(Intent.EXTRA_STREAM, imageUri)
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                } else {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                }
            }
            runCatching {
                context.startActivity(intent)
                return
            }
        }

        // Fallback to Telegram web share
        val shareUrl = buildShareUrl(data.questionId, data.userId)
        val webUri = Uri.parse("https://t.me/share/url?url=${Uri.encode(shareUrl)}&text=${Uri.encode(textMessage)}")
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, webUri))
            return
        }

        shareChooser(context, data, asImage, includeAnswer, attachedBitmap)
    }

    /**
     * Share directly to Instagram (Stories or Feed).
     */
    fun shareToInstagram(
        context: Context,
        data: QuestionShareData,
        asImage: Boolean,
        includeAnswer: Boolean,
        attachedBitmap: Bitmap? = null
    ) {
        val textMessage = buildShareText(data, includeAnswer)
        val imageUri = createQuestionCardImageUri(context, data, includeAnswer, attachedBitmap)
        val instaPkg = "com.instagram.android"

        if (isPackageInstalled(context, instaPkg) && imageUri != null) {
            // Try Instagram Stories first
            val storyIntent = Intent("com.instagram.share.ADD_TO_STORY").apply {
                setDataAndType(imageUri, "image/png")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            if (storyIntent.resolveActivity(context.packageManager) != null) {
                runCatching {
                    context.startActivity(storyIntent)
                    return
                }
            }

            // Fallback to Instagram Feed share
            val feedIntent = Intent(Intent.ACTION_SEND).apply {
                `package` = instaPkg
                type = "image/png"
                putExtra(Intent.EXTRA_STREAM, imageUri)
                putExtra(Intent.EXTRA_TEXT, textMessage)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            runCatching {
                context.startActivity(feedIntent)
                return
            }
        }

        Toast.makeText(context, "Instagram app not installed", Toast.LENGTH_SHORT).show()
        shareChooser(context, data, asImage, includeAnswer, attachedBitmap)
    }

    /**
     * Share to X (Twitter) with fallback to twitter.com web intent.
     */
    fun shareToTwitter(
        context: Context,
        data: QuestionShareData,
        asImage: Boolean,
        includeAnswer: Boolean,
        attachedBitmap: Bitmap? = null
    ) {
        val textMessage = buildShareText(data, includeAnswer)
        val imageUri = if (asImage) createQuestionCardImageUri(context, data, includeAnswer, attachedBitmap) else null
        val twitterPkg = "com.twitter.android"

        if (isPackageInstalled(context, twitterPkg)) {
            val intent = Intent(Intent.ACTION_SEND).apply {
                `package` = twitterPkg
                if (imageUri != null) {
                    type = "image/png"
                    putExtra(Intent.EXTRA_STREAM, imageUri)
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                } else {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                }
            }
            runCatching {
                context.startActivity(intent)
                return
            }
        }

        // Web intent fallback
        val webUri = Uri.parse("https://twitter.com/intent/tweet?text=${Uri.encode(textMessage)}")
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, webUri))
            return
        }

        shareChooser(context, data, asImage, includeAnswer, attachedBitmap)
    }

    /**
     * Share to Facebook.
     */
    fun shareToFacebook(
        context: Context,
        data: QuestionShareData,
        asImage: Boolean,
        includeAnswer: Boolean,
        attachedBitmap: Bitmap? = null
    ) {
        val textMessage = buildShareText(data, includeAnswer)
        val imageUri = if (asImage) createQuestionCardImageUri(context, data, includeAnswer, attachedBitmap) else null
        val fbPkg = "com.facebook.katana"

        if (isPackageInstalled(context, fbPkg)) {
            val intent = Intent(Intent.ACTION_SEND).apply {
                `package` = fbPkg
                if (imageUri != null) {
                    type = "image/png"
                    putExtra(Intent.EXTRA_STREAM, imageUri)
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                } else {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                }
            }
            runCatching {
                context.startActivity(intent)
                return
            }
        }

        shareChooser(context, data, asImage, includeAnswer, attachedBitmap)
    }

    /**
     * Share to LinkedIn.
     */
    fun shareToLinkedIn(
        context: Context,
        data: QuestionShareData,
        asImage: Boolean,
        includeAnswer: Boolean,
        attachedBitmap: Bitmap? = null
    ) {
        val textMessage = buildShareText(data, includeAnswer)
        val imageUri = if (asImage) createQuestionCardImageUri(context, data, includeAnswer, attachedBitmap) else null
        val linkedinPkg = "com.linkedin.android"

        if (isPackageInstalled(context, linkedinPkg)) {
            val intent = Intent(Intent.ACTION_SEND).apply {
                `package` = linkedinPkg
                if (imageUri != null) {
                    type = "image/png"
                    putExtra(Intent.EXTRA_STREAM, imageUri)
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                } else {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, textMessage)
                }
            }
            runCatching {
                context.startActivity(intent)
                return
            }
        }

        shareChooser(context, data, asImage, includeAnswer, attachedBitmap)
    }

    /**
     * Share via SMS / Messaging app.
     */
    fun shareToSms(context: Context, data: QuestionShareData, includeAnswer: Boolean) {
        val textMessage = buildShareText(data, includeAnswer)
        runCatching {
            val intent = Intent(Intent.ACTION_SENDTO).apply {
                this.data = Uri.parse("smsto:")
                putExtra("sms_body", textMessage)
                putExtra(Intent.EXTRA_TEXT, textMessage)
            }
            context.startActivity(intent)
        }.onFailure {
            // Fallback to text copy
            copyToClipboard(context, data, includeAnswer)
        }
    }

    /**
     * Copy formatted question text & link to system clipboard.
     */
    fun copyToClipboard(context: Context, data: QuestionShareData, includeAnswer: Boolean) {
        val textMessage = buildShareText(data, includeAnswer)
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
        if (clipboard != null) {
            val clip = ClipData.newPlainText("MediGyaan Question", textMessage)
            clipboard.setPrimaryClip(clip)
            Toast.makeText(context, "Question copied to clipboard! 📋", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Universal system share sheet.
     */
    fun shareChooser(
        context: Context,
        data: QuestionShareData,
        asImage: Boolean,
        includeAnswer: Boolean,
        attachedBitmap: Bitmap? = null
    ) {
        val textMessage = buildShareText(data, includeAnswer)
        val imageUri = if (asImage) createQuestionCardImageUri(context, data, includeAnswer, attachedBitmap) else null

        val intent = Intent(Intent.ACTION_SEND).apply {
            if (imageUri != null) {
                type = "image/png"
                putExtra(Intent.EXTRA_STREAM, imageUri)
                putExtra(Intent.EXTRA_TEXT, textMessage)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            } else {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, textMessage)
            }
        }
        val chooser = Intent.createChooser(intent, "Share Question via")
        chooser.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        context.startActivity(chooser)
    }

    /**
     * Share inside MediGyaan:
     * Offers Post to Feed, 1v1 Topic Challenge, Add to Custom Quiz, and View Shared Questions.
     */
    fun showMediGyaanShareDialog(
        context: Context,
        data: QuestionShareData,
        includeAnswer: Boolean = false,
        onAddToQuiz: (() -> Unit)? = null
    ) {
        val options = arrayOf(
            "📢 Post to MediGyaan Feed (Discuss with Doctors)",
            "⚔️ Challenge a Peer (1v1 Topic Battle)",
            "📑 Add to My Custom Quiz",
            "📊 View My Shared Questions"
        )

        androidx.appcompat.app.AlertDialog.Builder(context)
            .setTitle("Share inside MediGyaan")
            .setIcon(R.mipmap.ic_launcher)
            .setItems(options) { dialog, which ->
                dialog.dismiss()
                when (which) {
                    0 -> postToCommunityFeed(context, data, includeAnswer)
                    1 -> challengePeer(context, data)
                    2 -> {
                        if (onAddToQuiz != null) {
                            onAddToQuiz.invoke()
                        } else {
                            Toast.makeText(context, "Opening quiz selector...", Toast.LENGTH_SHORT).show()
                        }
                    }
                    3 -> viewSharedQuestions(context, data)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    fun postToCommunityFeed(context: Context, data: QuestionShareData, includeAnswer: Boolean) {
        runCatching {
            val text = buildShareText(data, includeAnswer)
            val focusJson = org.json.JSONObject().apply {
                put("post_id", data.questionId)
                put("name", "MediGyaan Doctor")
                put("photo", "")
                put("caption", text)
                put("file_paths", org.json.JSONArray())
                put("likes", 0)
            }
            val intent = Intent(context, NewsFeedActivity::class.java).apply {
                putExtra(NewsFeedActivity.EXTRA_FOCUS_POST_ID, data.questionId)
                putExtra(NewsFeedActivity.EXTRA_FOCUS_POST_JSON, focusJson.toString())
            }
            context.startActivity(intent)
            Toast.makeText(context, "Shared to MediGyaan Community Feed! 📢", Toast.LENGTH_SHORT).show()
        }.onFailure { e ->
            Log.e(TAG, "Failed to open NewsFeedActivity: ${e.message}", e)
        }
    }

    fun challengePeer(context: Context, data: QuestionShareData) {
        runCatching {
            val intent = Intent(context, TopicChallengeSelectionActivity::class.java).apply {
                putExtra("SELECTED_SUBJECT", data.subject)
                putExtra("SELECTED_TOPIC", data.topic)
                putExtra("MODE", "FRIENDS")
            }
            context.startActivity(intent)
        }.onFailure { e ->
            Log.e(TAG, "Failed to open TopicChallengeSelectionActivity: ${e.message}", e)
        }
    }

    fun viewSharedQuestions(context: Context, data: QuestionShareData) {
        runCatching {
            val intent = Intent(context, SharedQuestionsActivity::class.java).apply {
                putExtra("USER_ID", data.userId)
            }
            context.startActivity(intent)
        }.onFailure { e ->
            Log.e(TAG, "Failed to open SharedQuestionsActivity: ${e.message}", e)
        }
    }

    private fun isPackageInstalled(context: Context, packageName: String): Boolean {
        return runCatching {
            context.packageManager.getPackageInfo(packageName, 0)
            true
        }.getOrDefault(false)
    }
}
