package com.rankwarz.edulabsrtm

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.Typography
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import kotlin.concurrent.thread

class CollegeDetailActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val collegeName = intent.getStringExtra("college_name").orEmpty()
        val listUrl = intent.getStringExtra("list_url")
            ?: "https://www.MediGyaan.xyz/colleges.html"

        setContent {
            EduLabsRTMThemeFromPreferences {
                CollegeDetailApp(
                    collegeName = collegeName,
                    listUrl = listUrl
                )
            }
        }
    }
}

@Composable
private fun CollegeDetailApp(
    collegeName: String,
    listUrl: String
) {
    val context = LocalContext.current

    var loading by rememberSaveable { mutableStateOf(true) }
    var allRowsShown by rememberSaveable { mutableStateOf(false) }
    var data by remember { mutableStateOf<CollegeDetailData?>(null) }
    var errorText by rememberSaveable { mutableStateOf<String?>(null) }

    LaunchedEffect(collegeName) {
        loading = true
        errorText = null

        val cached = CollegeDetailCache.load(context, collegeName)
        if (cached != null) {
            data = cached
            loading = false
            return@LaunchedEffect
        }

        thread {
            try {
                val result = CollegeHtmlRepository.loadCollege(context, listUrl, collegeName)
                (context as? ComponentActivity)?.runOnUiThread {
                    data = result
                    loading = false
                }
            } catch (e: Exception) {
                (context as? ComponentActivity)?.runOnUiThread {
                    errorText = e.message ?: "Unable to load college data"
                    loading = false
                }
            }
        }
    }

    MaterialTheme(typography = Typography()) {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .background(MaterialTheme.colorScheme.background)
                .navigationBarsPadding(),
            color = MaterialTheme.colorScheme.background
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp)
            ) {
                Text(
                    text = if (collegeName.isBlank()) "College Details" else collegeName,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.padding(bottom = 12.dp)
                )

                when {
                    loading -> {
                        LoadingCard()
                    }

                    errorText != null -> {
                        ReviewCard(
                            title = "Data about the college is in review",
                            subtitle = errorText ?: "Unable to load college data"
                        )
                    }

                    data?.dataInReview == true || data == null -> {
                        ReviewCard(
                            title = "Data about the college is in review",
                            subtitle = data?.reviewMessage?.ifBlank {
                                "No matching college page was found"
                            } ?: "No matching college page was found"
                        )
                    }

                    else -> {
                        CollegeInfoCard(
                            college = data!!,
                            allRowsShown = allRowsShown,
                            onToggleDetails = { allRowsShown = !allRowsShown }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun LoadingCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.5.dp)
                Spacer(modifier = Modifier.width(14.dp))
                Text(
                    text = "Loading college data...",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }

            Spacer(modifier = Modifier.height(14.dp))
            Text(
                text = "Fetching the linked HTML page and caching the parsed details.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 14.sp
            )
        }
    }
}

@Composable
private fun ReviewCard(
    title: String,
    subtitle: String
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF1F2)),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text(
                text = title,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFB91C1C),
                fontSize = 16.sp
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = subtitle,
                color = Color(0xFF7F1D1D),
                fontSize = 14.sp
            )
        }
    }
}

@Composable
private fun CollegeInfoCard(
    college: CollegeDetailData,
    allRowsShown: Boolean,
    onToggleDetails: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {

            HeaderBlock(college)

            Spacer(modifier = Modifier.height(14.dp))
            InfoBlock(
                title = "📍 Address",
                content = buildString {
                    append(college.address.ifBlank { "Not available" })
                    append("\nState: ")
                    append(college.state.ifBlank { "Not available" })
                    append("\nPin Code: ")
                    append(college.pinCode.ifBlank { "Not available" })
                },
                accent = Color(0xFF2563EB),
                bg = Color(0xFFEFF6FF)
            )

            Spacer(modifier = Modifier.height(12.dp))
            InfoBlock(
                title = "💰 Fee Structure",
                content = buildString {
                    append("Annual Fee: ")
                    append(college.annualFee.ifBlank { "Not available" })
                    append("\nNRI Fee: ")
                    append(college.nriFee.ifBlank { "Not available" })
                },
                accent = Color(0xFF1D4ED8),
                bg = Color(0xFFF8FAFF)
            )

            Spacer(modifier = Modifier.height(12.dp))
            InfoBlock(
                title = "🏥 Stipend",
                content = buildString {
                    append("1st Year: ")
                    append(college.stipend1.ifBlank { "Not available" })
                    append("\n2nd Year: ")
                    append(college.stipend2.ifBlank { "Not available" })
                    append("\n3rd Year: ")
                    append(college.stipend3.ifBlank { "Not available" })
                },
                accent = Color(0xFF15803D),
                bg = Color(0xFFF0FDF4)
            )

            Spacer(modifier = Modifier.height(12.dp))
            InfoBlock(
                title = "👨‍⚕️ Officials",
                content = buildString {
                    append("Dean / Principal: ")
                    append(college.dean.ifBlank { "Not available" })
                    append("\nNodal Officer: ")
                    append(college.nodalOfficer.ifBlank { "Not available" })
                },
                accent = Color(0xFFB45309),
                bg = Color(0xFFFFFBEB)
            )

            Spacer(modifier = Modifier.height(12.dp))
            InfoBlock(
                title = "🌐 Website",
                content = college.website.ifBlank { "Not available" },
                accent = Color(0xFF7C3AED),
                bg = Color(0xFFF5F3FF),
                clickableLink = college.website.startsWith("http", ignoreCase = true)
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = onToggleDetails,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (allRowsShown) "Hide Full Details" else "View Full Details")
            }

            AnimatedVisibility(visible = allRowsShown) {
                Column(modifier = Modifier.padding(top = 16.dp)) {
                    Divider(color = Color(0xFFE2E8F0))
                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = "Additional Fields",
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 16.sp
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    if (college.allFields.isEmpty()) {
                        ExtraRowBox("No extra rows found in HTML")
                    } else {
                        college.allFields.forEach { (key, value) ->
                            ExtraFieldCard(key, value)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun HeaderBlock(college: CollegeDetailData) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(14.dp)
    ) {
        Text(
            text = college.collegeName,
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )

        Spacer(modifier = Modifier.height(8.dp))

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Tag(text = college.state.ifBlank { "Unknown State" }, bg = Color(0xFFE0F2FE), fg = Color(0xFF075985))
            Tag(text = college.pinCode.ifBlank { "No Pin" }, bg = Color(0xFFFEF3C7), fg = Color(0xFF92400E))
        }
    }
}

@Composable
private fun Tag(text: String, bg: Color, fg: Color) {
    Text(
        text = text,
        color = fg,
        fontSize = 12.sp,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier
            .clip(MaterialTheme.shapes.small)
            .background(bg)
            .padding(horizontal = 10.dp, vertical = 6.dp)
    )
}

@Composable
private fun InfoBlock(
    title: String,
    content: String,
    accent: Color,
    bg: Color,
    clickableLink: Boolean = false
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = bg),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = title,
                color = accent,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = content,
                color = MaterialTheme.colorScheme.onSurface,
                fontSize = 14.sp,
                lineHeight = 20.sp,
                textDecoration = if (clickableLink) TextDecoration.Underline else TextDecoration.None,
                modifier = if (clickableLink) {
                    Modifier.clickable {
                        // If you want to open the link with an Intent, wire it here.
                    }
                } else {
                    Modifier
                }
            )
        }
    }
}

@Composable
private fun ExtraFieldCard(key: String, value: String) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 10.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = key,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = value,
                fontSize = 13.sp,
                color = Color(0xFF475569),
                lineHeight = 18.sp
            )
        }
    }
}

@Composable
private fun ExtraRowBox(text: String) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 10.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF1F5F9))
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(14.dp),
            color = MaterialTheme.colorScheme.onSurface,
            fontSize = 14.sp
        )
    }
}
