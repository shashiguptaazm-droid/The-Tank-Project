package com.rankwarz.edulabsrtm

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.net.Uri
import android.os.Bundle
import android.provider.ContactsContract
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.android.volley.Request
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.android.material.button.MaterialButton
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream

class ReferralActivity : AppCompatActivity() {

    private val apiUrl = "https://medigyaan.xyz/Neurons/api/referral_api.php"

    /** Play Store link for the app. */
    private val installUrl = "https://play.google.com/store/apps/details?id=com.corp.medigyaan"
    private val prefs by lazy { getSharedPreferences("MY_APP", Context.MODE_PRIVATE) }

    // ── Contacts invite ──
    private val contactPickLauncher = registerForActivityResult(
        ActivityResultContracts.PickContact()
    ) { contactUri ->
        if (contactUri != null) {
            val number = readContactPhoneNumber(contactUri)
            if (number.isNullOrBlank()) {
                Toast.makeText(this, "No phone number on that contact", Toast.LENGTH_SHORT).show()
            } else {
                inviteViaWhatsAppOrSms(number)
            }
        }
    }

    private val contactsPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) launchContactPicker() else showContactsRationale()
    }

    private var userId = 0
    private var referralCode = ""
    private var inviteUrl = ""

    private lateinit var txtReferralCode: TextView
    private lateinit var txtReferralSubtitle: TextView
    private lateinit var txtShareCount: TextView
    private lateinit var txtJoinCount: TextView
    private lateinit var txtRewardCount: TextView
    private lateinit var txtReferralProgress: TextView
    private lateinit var loggedOutCard: View
    private lateinit var txtPendingCode: TextView
    private lateinit var btnShareInvite: MaterialButton
    private lateinit var btnCopyCode: MaterialButton
    private lateinit var btnCopyLink: MaterialButton

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_referral)

        captureIncomingReferralCode(intent?.data)
        userId = prefs.getInt("user_id", 0)

        bindViews()
        setupClicks()

        if (userId <= 0) {
            showLoggedOutState()
        } else {
            loadReferral()
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        captureIncomingReferralCode(intent.data)
    }

    private fun bindViews() {
        txtReferralCode = findViewById(R.id.txtReferralCode)
        txtReferralSubtitle = findViewById(R.id.txtReferralSubtitle)
        txtShareCount = findViewById(R.id.txtShareCount)
        txtJoinCount = findViewById(R.id.txtJoinCount)
        txtRewardCount = findViewById(R.id.txtRewardCount)
        txtReferralProgress = findViewById(R.id.txtReferralProgress)
        loggedOutCard = findViewById(R.id.loggedOutCard)
        txtPendingCode = findViewById(R.id.txtPendingCode)
        btnShareInvite = findViewById(R.id.btnShareInvite)
        btnCopyCode = findViewById(R.id.btnCopyCode)
        btnCopyLink = findViewById(R.id.btnCopyLink)
    }

    private fun setupClicks() {
        findViewById<View>(R.id.btnBack).setOnClickListener { finish() }
        btnShareInvite.setOnClickListener {
            if (userId <= 0) {
                openRegister()
            } else {
                trackShareThenOpenChooser()
            }
        }
        btnCopyCode.setOnClickListener { copyText("Referral code", referralCode.ifBlank { pendingReferralCode() }) }
        btnCopyLink.setOnClickListener { copyText("Invite link", inviteUrl.ifBlank { pendingInviteUrl() }) }
        findViewById<View>(R.id.btnRegisterWithCode).setOnClickListener { openRegister() }
        findViewById<View>(R.id.btnInstallLink).setOnClickListener {
            copyText("Install link", installUrl)
        }
        findViewById<MaterialButton>(R.id.btnInviteContacts).setOnClickListener {
            onInviteContactsClicked()
        }
    }

    // ─────────── Invite contacts (WhatsApp / SMS) ───────────

    private fun onInviteContactsClicked() {
        if (userId <= 0) {
            openRegister()
            return
        }
        when {
            ContextCompat.checkSelfPermission(this, Manifest.permission.READ_CONTACTS) == PackageManager.PERMISSION_GRANTED ->
                launchContactPicker()
            shouldShowRequestPermissionRationale(Manifest.permission.READ_CONTACTS) -> showContactsRationale()
            else -> contactsPermissionLauncher.launch(Manifest.permission.READ_CONTACTS)
        }
    }

    private fun launchContactPicker() {
        runCatching { contactPickLauncher.launch(null) }
            .onFailure {
                // Some devices lack the contacts picker app — fall back to plain share.
                Toast.makeText(this, "Contacts picker unavailable — use Share Invite", Toast.LENGTH_LONG).show()
                trackShareThenOpenChooser()
            }
    }

    private fun showContactsRationale() {
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Contacts permission")
            .setMessage("Allow contacts access so you can pick a friend and send them your invite link directly in WhatsApp or SMS. Your contacts never leave your phone.")
            .setPositiveButton("Allow") { _, _ -> contactsPermissionLauncher.launch(Manifest.permission.READ_CONTACTS) }
            .setNegativeButton("Not now", null)
            .show()
    }

    /** Resolves the picked contact's primary mobile number, then sends the invite. */
    private fun readContactPhoneNumber(contactUri: Uri): String? {
        return runCatching {
            var phoneNumber: String? = null
            contentResolver.query(contactUri, null, null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val idIndex = cursor.getColumnIndex(ContactsContract.Contacts._ID)
                    if (idIndex == -1) return@runCatching null
                    val contactId = cursor.getString(idIndex)
                    
                    val hasPhoneIndex = cursor.getColumnIndex(ContactsContract.Contacts.HAS_PHONE_NUMBER)
                    val hasPhone = if (hasPhoneIndex != -1) cursor.getInt(hasPhoneIndex) > 0 else false
                    
                    if (hasPhone) {
                        contentResolver.query(
                            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                            null,
                            ContactsContract.CommonDataKinds.Phone.CONTACT_ID + " = ?",
                            arrayOf(contactId),
                            null
                        )?.use { phoneCursor ->
                            if (phoneCursor.moveToFirst()) {
                                val numberIndex = phoneCursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                                if (numberIndex != -1) {
                                    phoneNumber = phoneCursor.getString(numberIndex)
                                }
                            }
                        }
                    }
                }
            }
            phoneNumber
        }.getOrNull()
    }

    /** Sends the invite (text + branded logo card) to one number via WhatsApp, falling back to SMS. */
    private fun inviteViaWhatsAppOrSms(phoneNumber: String) {
        val message = buildShareMessage()

        // WhatsApp direct-to-chat (works without QUERY_ALL_PACKAGES because we pass the phone).
        val waIntent = Intent(Intent.ACTION_SENDTO).apply {
            data = Uri.parse("https://wa.me/$phoneNumber")
            putExtra(Intent.EXTRA_TEXT, message)
        }
        val resolved = runCatching { packageManager.queryIntentActivities(waIntent, 0) }.getOrNull().orEmpty()
        if (resolved.isNotEmpty()) {
            // wa.me opens the chat; EXTRA_TEXT is honored by WhatsApp for http(s) wa.me links.
            runCatching { startActivity(waIntent) }
                .onFailure { openSmsFallback(phoneNumber, message) }
            return
        }
        openSmsFallback(phoneNumber, message)
    }

    private fun openSmsFallback(phoneNumber: String, message: String) {
        runCatching {
            startActivity(Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:$phoneNumber")).apply {
                putExtra("sms_body", message)
            })
        }.onFailure {
            Toast.makeText(this, "No SMS app found — link copied instead", Toast.LENGTH_LONG).show()
            copyText("Invite", message)
 }
    }

    /**
     * Renders a branded invite card (app logo + text + code + links) to cache and returns
     * a shareable content:// URI via FileProvider, or null when generation fails.
     */
    private fun createInviteCardImage(): Uri? {
        return runCatching {
            val logo = BitmapFactory.decodeResource(resources, R.mipmap.ic_launcher)
                ?: return null
            val width = 1080
            val height = 1350
            val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bitmap)

            canvas.drawColor(android.graphics.Color.parseColor("#0D1A2B"))

            // Logo centered near the top.
            val logoSize = 320
            val logoLeft = (width - logoSize) / 2f
            canvas.drawBitmap(logo, null, android.graphics.RectF(logoLeft, 150f, logoLeft + logoSize, 150f + logoSize), null)

            val paint = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG)
            paint.textAlign = android.graphics.Paint.Align.CENTER

            // Title.
            paint.color = android.graphics.Color.WHITE
            paint.textSize = 72f
            paint.isFakeBoldText = true
            canvas.drawText("Join me on MediGyaan", width / 2f, 640f, paint)

            // Subtitle.
            paint.color = android.graphics.Color.parseColor("#9FB3CC")
            paint.textSize = 40f
            paint.isFakeBoldText = false
            canvas.drawText("NEET PG MCQ battles · AI counseling · Leaderboards", width / 2f, 720f, paint)

            // Referral code.
            val code = referralCode.ifBlank { pendingReferralCode() }
            paint.color = android.graphics.Color.parseColor("#F4C95D")
            paint.textSize = 64f
            paint.isFakeBoldText = true
            canvas.drawText("Code: $code", width / 2f, 900f, paint)

            // Links.
            paint.color = android.graphics.Color.parseColor("#48D6C8")
            paint.textSize = 38f
            paint.isFakeBoldText = false
            val link = inviteUrl.ifBlank { pendingInviteUrl() }
            canvas.drawText(link, width / 2f, 1040f, paint)
            canvas.drawText(installUrl, width / 2f, 1120f, paint)

            val dir = File(cacheDir, "shared_images").apply { mkdirs() }
            val file = File(dir, "invite_card_${System.currentTimeMillis()}.png")
            FileOutputStream(file).use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
            bitmap.recycle()

            FileProvider.getUriForFile(this, "com.corp.medigyaan.fileprovider", file)
        }.getOrNull()
    }

    // ─────────── Referral data ───────────

    private fun captureIncomingReferralCode(uri: Uri?) {
        val code = uri?.getQueryParameter("code")
            ?.uppercase()
            ?.replace(Regex("[^A-Z0-9]"), "")
            .orEmpty()
        if (code.isNotBlank()) {
            prefs.edit().putString("pending_referral_code", code).apply()
        }
    }

    private fun pendingReferralCode(): String = prefs.getString("pending_referral_code", "") ?: ""

    private fun pendingInviteUrl(): String {
        val code = pendingReferralCode()
        return if (code.isBlank()) "" else "https://medigyaan.xyz/Neurons/referral.php?code=$code"
    }

    private fun showLoggedOutState() {
        val pendingCode = pendingReferralCode()
        referralCode = pendingCode
        inviteUrl = pendingInviteUrl()
        txtReferralCode.text = pendingCode.ifBlank { "SIGN UP" }
        txtReferralSubtitle.text = "Create an account to claim this invite and start tracking your own referrals."
        txtPendingCode.text = if (pendingCode.isBlank()) {
            "Register to start inviting friends."
        } else {
            "Code saved: $pendingCode"
        }
        loggedOutCard.visibility = View.VISIBLE
        btnShareInvite.text = "Create Account"
        btnCopyCode.isEnabled = pendingCode.isNotBlank()
        btnCopyLink.isEnabled = pendingCode.isNotBlank()
    }

    private fun loadReferral() {
        setLoading(true)
        val request = object : StringRequest(
            Request.Method.POST,
            apiUrl,
            { response ->
                setLoading(false)
                try {
                    val root = JSONObject(response)
                    if (root.optString("status") != "success") {
                        Toast.makeText(this, root.optString("message", "Referral failed"), Toast.LENGTH_SHORT).show()
                    } else {
                        val data = root.optJSONObject("data") ?: JSONObject()
                        referralCode = data.optString("referral_code")
                        inviteUrl = data.optString("invite_url")
                        txtReferralCode.text = referralCode
                        txtShareCount.text = data.optInt("share_count", 0).toString()
                        txtJoinCount.text = data.optInt("registered_count", 0).toString()
                        txtRewardCount.text = data.optInt("rewarded_count", 0).toString()
                        txtReferralProgress.text = "Next reward in ${data.optInt("next_reward_at", 3)} invited friend(s)."
                        btnShareInvite.text = "Share Invite"
                        btnCopyCode.isEnabled = referralCode.isNotBlank()
                        btnCopyLink.isEnabled = inviteUrl.isNotBlank()
                    }
                } catch (_: Exception) {
                    Toast.makeText(this, "Referral response error", Toast.LENGTH_SHORT).show()
                }
            },
            {
                setLoading(false)
                Toast.makeText(this, "Could not load referrals", Toast.LENGTH_SHORT).show()
            }
        ) {
            override fun getParams() = hashMapOf(
                "action" to "get",
                "user_id" to userId.toString()
            )
        }
        Volley.newRequestQueue(applicationContext).add(request)
    }

    private fun setLoading(loading: Boolean) {
        btnShareInvite.isEnabled = !loading
        txtReferralCode.text = if (loading) "Loading" else txtReferralCode.text
    }

    private fun trackShareThenOpenChooser() {
        val request = object : StringRequest(
            Request.Method.POST,
            apiUrl,
            { openShareChooser() },
            { openShareChooser() }
        ) {
            override fun getParams() = hashMapOf(
                "action" to "track_share",
                "user_id" to userId.toString(),
                "channel" to "android_share"
            )
        }
        Volley.newRequestQueue(applicationContext).add(request)
    }

    private fun openShareChooser() {
        val message = buildShareMessage()
        val imageUri = createInviteCardImage()
        val intent = Intent(Intent.ACTION_SEND).apply {
            // Branded card with the app logo when it generated successfully.
            type = if (imageUri != null) "image/png" else "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, "Join me on MediGyaan")
            putExtra(Intent.EXTRA_TEXT, message)
            if (imageUri != null) {
                putExtra(Intent.EXTRA_STREAM, imageUri)
                clipData = ClipData.newRawUri("invite_card", imageUri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
        }
        startActivity(Intent.createChooser(intent, "Invite friends"))
    }

    private fun buildShareMessage(): String {
        val code = referralCode.ifBlank { pendingReferralCode() }
        val link = inviteUrl.ifBlank { pendingInviteUrl() }
        return "Join me on MediGyaan for NEET PG MCQ battles, AI counseling and leaderboard practice.\n" +
            "My referral code: $code\n" +
            "Invite link: $link\n" +
            "Install the app: $installUrl"
    }

    private fun copyText(label: String, text: String) {
        if (text.isBlank()) return
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        Toast.makeText(this, "$label copied", Toast.LENGTH_SHORT).show()
    }

    private fun openRegister() {
        startActivity(Intent(this, RegisterActivity::class.java))
    }
}
