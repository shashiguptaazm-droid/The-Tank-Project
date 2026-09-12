package com.rankwarz.edulabsrtm

import android.graphics.Bitmap
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.TextView
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.google.android.material.button.MaterialButton
import com.google.android.material.button.MaterialButtonToggleGroup
import com.google.android.material.card.MaterialCardView
import com.google.android.material.checkbox.MaterialCheckBox

class QuestionShareBottomSheet : BottomSheetDialogFragment() {

    private var shareData: QuestionShareHelper.QuestionShareData? = null
    private var attachedBitmap: Bitmap? = null
    private var shareAsImage: Boolean = true
    var onAddToQuizRequested: (() -> Unit)? = null

    companion object {
        const val TAG = "QuestionShareBottomSheet"

        fun newInstance(
            data: QuestionShareHelper.QuestionShareData,
            bitmap: Bitmap? = null,
            onAddToQuiz: (() -> Unit)? = null
        ): QuestionShareBottomSheet {
            val sheet = QuestionShareBottomSheet()
            sheet.shareData = data
            sheet.attachedBitmap = bitmap
            sheet.onAddToQuizRequested = onAddToQuiz
            return sheet
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.layout_question_share_bottom_sheet, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        val data = shareData ?: run {
            dismiss()
            return
        }

        val txtSubtitle = view.findViewById<TextView>(R.id.txtShareSubtitle)
        val btnClose = view.findViewById<ImageButton>(R.id.btnCloseSheet)
        val toggleGroup = view.findViewById<MaterialButtonToggleGroup>(R.id.formatToggleGroup)
        val chkIncludeAnswer = view.findViewById<MaterialCheckBox>(R.id.chkIncludeAnswer)
        val txtPreviewBadge = view.findViewById<TextView>(R.id.txtPreviewBadge)
        val txtPreviewQuestion = view.findViewById<TextView>(R.id.txtPreviewQuestion)
        val txtPreviewOptions = view.findViewById<TextView>(R.id.txtPreviewOptions)

        val btnMediGyaanCard = view.findViewById<MaterialCardView>(R.id.btnShareMediGyaanCard)
        val btnMediGyaanGrid = view.findViewById<LinearLayout>(R.id.btnShareMediGyaan)

        val btnWhatsApp = view.findViewById<LinearLayout>(R.id.btnShareWhatsApp)
        val btnTelegram = view.findViewById<LinearLayout>(R.id.btnShareTelegram)
        val btnInstagram = view.findViewById<LinearLayout>(R.id.btnShareInstagram)
        val btnTwitter = view.findViewById<LinearLayout>(R.id.btnShareTwitter)
        val btnFacebook = view.findViewById<LinearLayout>(R.id.btnShareFacebook)
        val btnLinkedIn = view.findViewById<LinearLayout>(R.id.btnShareLinkedIn)
        val btnSMS = view.findViewById<LinearLayout>(R.id.btnShareSMS)
        val btnCopy = view.findViewById<LinearLayout>(R.id.btnShareCopy)
        val btnMoreGrid = view.findViewById<LinearLayout>(R.id.btnShareMoreGrid)
        val btnMore = view.findViewById<MaterialButton>(R.id.btnShareMore)

        // Subtitle & preview
        val subjectTopic = if (data.topic.isNotBlank() && data.topic != "General" && data.topic != "Uncategorized") {
            "${data.subject} • ${data.topic}"
        } else {
            data.subject.ifBlank { "NEET PG" }
        }
        txtSubtitle.text = subjectTopic
        txtPreviewBadge.text = "Q#${data.questionId}"

        val cleanQ = data.questionText.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
        txtPreviewQuestion.text = cleanQ

        val cleanA = data.optionA.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
        val cleanB = data.optionB.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
        val cleanC = data.optionC.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
        val cleanD = data.optionD.replace(Regex("^\\d+[.\\s\\-)]+\\s*"), "").trim()
        txtPreviewOptions.text = "A) $cleanA\nB) $cleanB\nC) $cleanC\nD) $cleanD"

        // If the question was already answered, allow user to include answer in share
        if (data.isAnswered && !data.correctAnswer.isNullOrBlank()) {
            chkIncludeAnswer.visibility = View.VISIBLE
            chkIncludeAnswer.isChecked = false
        } else {
            chkIncludeAnswer.visibility = View.GONE
        }

        btnClose.setOnClickListener { dismiss() }

        toggleGroup.addOnButtonCheckedListener { _, checkedId, isChecked ->
            if (isChecked) {
                shareAsImage = (checkedId == R.id.btnFormatImage)
            }
        }

        val onMediGyaanClick = View.OnClickListener {
            val ctx = context ?: return@OnClickListener
            QuestionShareHelper.showMediGyaanShareDialog(ctx, data, chkIncludeAnswer.isChecked, onAddToQuizRequested)
            dismiss()
        }

        btnMediGyaanCard?.setOnClickListener(onMediGyaanClick)
        btnMediGyaanGrid?.setOnClickListener(onMediGyaanClick)

        btnWhatsApp.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.shareToWhatsApp(ctx, data, shareAsImage, chkIncludeAnswer.isChecked, attachedBitmap)
            dismiss()
        }

        btnTelegram.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.shareToTelegram(ctx, data, shareAsImage, chkIncludeAnswer.isChecked, attachedBitmap)
            dismiss()
        }

        btnInstagram.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.shareToInstagram(ctx, data, shareAsImage, chkIncludeAnswer.isChecked, attachedBitmap)
            dismiss()
        }

        btnTwitter.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.shareToTwitter(ctx, data, shareAsImage, chkIncludeAnswer.isChecked, attachedBitmap)
            dismiss()
        }

        btnFacebook.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.shareToFacebook(ctx, data, shareAsImage, chkIncludeAnswer.isChecked, attachedBitmap)
            dismiss()
        }

        btnLinkedIn.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.shareToLinkedIn(ctx, data, shareAsImage, chkIncludeAnswer.isChecked, attachedBitmap)
            dismiss()
        }

        btnSMS.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.shareToSms(ctx, data, chkIncludeAnswer.isChecked)
            dismiss()
        }

        btnCopy.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.copyToClipboard(ctx, data, chkIncludeAnswer.isChecked)
            dismiss()
        }

        btnMoreGrid?.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.shareChooser(ctx, data, shareAsImage, chkIncludeAnswer.isChecked, attachedBitmap)
            dismiss()
        }

        btnMore.setOnClickListener {
            val ctx = context ?: return@setOnClickListener
            QuestionShareHelper.shareChooser(ctx, data, shareAsImage, chkIncludeAnswer.isChecked, attachedBitmap)
            dismiss()
        }
    }
}
