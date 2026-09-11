package com.rankwarz.edulabsrtm

import android.graphics.Typeface
import android.text.Spannable
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.text.style.RelativeSizeSpan
import android.text.style.StyleSpan
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.sp
import androidx.compose.material3.Text
import com.rankwarz.edulabsrtm.utils.MedigyaanMetadata

/**
 * Renders AI reply text the way the app displays chat answers:
 * `**Title**` markdown segments become prominent section titles.
 * Inline `**bold**` segments become bold without asterisks.
 */
@Composable
fun AiRichText(
    text: String,
    modifier: Modifier = Modifier,
    style: TextStyle = MaterialTheme.typography.bodyMedium,
    color: Color = Color.Unspecified,
    lineHeight: TextUnit? = null,
    maxLines: Int = Int.MAX_VALUE,
    overflow: TextOverflow = TextOverflow.Clip
) {
    val effectiveStyle = if (lineHeight != null) style.copy(lineHeight = lineHeight) else style
    val highlight = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f)
    val baseSize = style.fontSize
    val iconified = MedigyaanMetadata.iconify(text)
    val annotated = remember(iconified, highlight, baseSize) {
        buildAiAnnotatedString(iconified, highlight, baseSize)
    }
    Text(
        text = annotated,
        modifier = modifier,
        style = effectiveStyle,
        color = color,
        maxLines = maxLines,
        overflow = overflow
    )
}

/**
 * Renders `**Title**` and `**bold**` markdown segments in classic [TextView]s:
 * - Standalone `**Title**` and `### Title` are formatted as prominent section titles (bold, 1.18x size, primary teal color, no asterisks).
 * - Leading `**Title:**` prefixes are bolded with title accent color.
 * - Inline `**bold**` is rendered in bold typeface without raw asterisks.
 * Safe to call on any AI reply text everywhere in the app.
 */
fun aiMarkdownSpannable(text: String, highlightColor: Int = 0x40B3E5FC.toInt()): Spannable {
    val iconified = MedigyaanMetadata.iconify(text)
    val builder = SpannableStringBuilder()
    val lines = iconified.split("\n")
    val titleColor = 0xFF00796B.toInt()

    lines.forEachIndexed { i, line ->
        val isLast = i == lines.size - 1

        // 1. Standalone Title: **Title** or ### Title or **Title:**
        val standaloneTitleMatch = Regex("""^\s*(?:\*\*|#{1,4}\s*)([^*#\n]+?)(?:\*\*)?\s*$""").find(line)
        // 2. Leading Title with colon: **Title:** or 1. **Title:**
        val leadingTitleMatch = Regex("""^(\s*(?:\d+\.\s*)?)\*\*([^*:]+):?\*\*:?\s*(.*)$""").find(line)

        when {
            standaloneTitleMatch != null && standaloneTitleMatch.groupValues[1].isNotBlank() -> {
                val titleText = standaloneTitleMatch.groupValues[1].trim()
                val start = builder.length
                builder.append(titleText)
                val end = builder.length
                builder.setSpan(StyleSpan(Typeface.BOLD), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                builder.setSpan(RelativeSizeSpan(1.18f), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                builder.setSpan(ForegroundColorSpan(titleColor), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            leadingTitleMatch != null -> {
                val prefix = leadingTitleMatch.groupValues[1]
                val titleText = leadingTitleMatch.groupValues[2].trim()
                val rest = leadingTitleMatch.groupValues[3]

                if (prefix.isNotEmpty()) builder.append(prefix)
                val start = builder.length
                builder.append(titleText).append(": ")
                val end = builder.length
                builder.setSpan(StyleSpan(Typeface.BOLD), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                builder.setSpan(ForegroundColorSpan(titleColor), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)

                appendWithInlineBold(builder, rest)
            }
            else -> {
                appendWithInlineBold(builder, line)
            }
        }

        if (!isLast) {
            builder.append("\n")
        }
    }

    return builder
}

private fun appendWithInlineBold(builder: SpannableStringBuilder, text: String) {
    var index = 0
    while (index < text.length) {
        val start = text.indexOf("**", startIndex = index)
        if (start < 0) {
            builder.append(text.substring(index))
            break
        }
        builder.append(text.substring(index, start))
        val end = text.indexOf("**", startIndex = start + 2)
        if (end < 0) {
            builder.append(text.substring(start))
            break
        }
        val boldContent = text.substring(start + 2, end)
        val spanStart = builder.length
        builder.append(boldContent)
        val spanEnd = builder.length
        builder.setSpan(StyleSpan(Typeface.BOLD), spanStart, spanEnd, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        index = end + 2
    }
}

private fun buildAiAnnotatedString(
    text: String,
    highlight: Color,
    baseSize: TextUnit
): AnnotatedString {
    val titleColor = Color(0xFF00796B)
    return buildAnnotatedString {
        val lines = text.split("\n")
        var inDiff = false

        lines.forEachIndexed { i, line ->
            val isLast = i == lines.size - 1

            when {
                line.startsWith("```diff") -> {
                    inDiff = true
                    append(line + "\n")
                }
                line.startsWith("```") && inDiff -> {
                    inDiff = false
                    append(line + "\n")
                }
                inDiff && line.startsWith("-") -> {
                    pushStyle(SpanStyle(color = Color(0xFFD32F2F), background = Color(0xFFFFEBEE)))
                    append(line + "\n")
                    pop()
                }
                inDiff && line.startsWith("+") -> {
                    pushStyle(SpanStyle(color = Color(0xFF388E3C), background = Color(0xFFE8F5E9)))
                    append(line + "\n")
                    pop()
                }
                else -> {
                    val standaloneTitleMatch = Regex("""^\s*(?:\*\*|#{1,4}\s*)([^*#\n]+?)(?:\*\*)?\s*$""").find(line)
                    val leadingTitleMatch = Regex("""^(\s*(?:\d+\.\s*)?)\*\*([^*:]+):?\*\*:?\s*(.*)$""").find(line)

                    when {
                        standaloneTitleMatch != null && standaloneTitleMatch.groupValues[1].isNotBlank() -> {
                            val titleText = standaloneTitleMatch.groupValues[1].trim()
                            pushStyle(
                                SpanStyle(
                                    fontWeight = FontWeight.Bold,
                                    fontSize = (baseSize.value * 1.18f).sp,
                                    color = titleColor
                                )
                            )
                            append(titleText)
                            pop()
                        }
                        leadingTitleMatch != null -> {
                            val prefix = leadingTitleMatch.groupValues[1]
                            val titleText = leadingTitleMatch.groupValues[2].trim()
                            val rest = leadingTitleMatch.groupValues[3]

                            if (prefix.isNotEmpty()) append(prefix)
                            pushStyle(
                                SpanStyle(
                                    fontWeight = FontWeight.Bold,
                                    color = titleColor
                                )
                            )
                            append(titleText)
                            append(": ")
                            pop()
                            appendAnnotatedWithInlineBold(rest)
                        }
                        else -> {
                            appendAnnotatedWithInlineBold(line)
                        }
                    }

                    if (!isLast) {
                        append("\n")
                    }
                }
            }
        }
    }
}

private fun AnnotatedString.Builder.appendAnnotatedWithInlineBold(text: String) {
    var index = 0
    while (index < text.length) {
        val start = text.indexOf("**", startIndex = index)
        if (start < 0) {
            append(text.substring(index))
            break
        }
        append(text.substring(index, start))
        val end = text.indexOf("**", startIndex = start + 2)
        if (end < 0) {
            append(text.substring(start))
            break
        }
        val boldContent = text.substring(start + 2, end)
        pushStyle(SpanStyle(fontWeight = FontWeight.Bold))
        append(boldContent)
        pop()
        index = end + 2
    }
}