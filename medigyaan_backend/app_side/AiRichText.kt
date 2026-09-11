package com.rankwarz.edulabsrtm

import android.graphics.Typeface
import android.text.Spannable
import android.text.SpannableString
import android.text.Spanned
import android.text.style.BackgroundColorSpan
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

/**
 * Renders AI reply text the way the app displays chat answers:
 * `**bold**` markdown segments become bold + highlighted. A segment that
 * sits on its own line (a heading like `**Introduction**`) is additionally
 * scaled up slightly so it reads as a heading.
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
    val annotated = remember(text, highlight, baseSize) {
        buildAiAnnotatedString(text, highlight, baseSize)
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
 * Renders `**bold**` markdown segments in a classic [TextView] as bold + highlighted,
 * matching [AiRichText] for Compose screens. Safe to call on any AI reply text.
 */
fun aiMarkdownSpannable(text: String, highlightColor: Int = 0x40B3E5FC.toInt()): Spannable {
    val spannable = SpannableString(text)
    val regex = Regex("""\*\*([^*]+)\*\*""")
    for (match in regex.findAll(text)) {
        val start = match.range.first
        val end = match.range.last + 1
        spannable.setSpan(StyleSpan(Typeface.BOLD), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        spannable.setSpan(BackgroundColorSpan(highlightColor), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
    }
    return spannable
}

private fun buildAiAnnotatedString(
    text: String,
    highlight: Color,
    baseSize: TextUnit
): AnnotatedString {
    return buildAnnotatedString {
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
            val boldText = text.substring(start + 2, end)
            // A heading: the whole segment sits on its own line
            val isHeadingLike = boldText.isNotBlank() &&
                (start == 0 || text[start - 1] == '\n') &&
                (end + 2 >= text.length || text[end + 2] == '\n')
            pushStyle(
                SpanStyle(
                    fontWeight = FontWeight.Bold,
                    background = highlight,
                    fontSize = if (isHeadingLike && baseSize != TextUnit.Unspecified) baseSize * 1.15f else baseSize
                )
            )
            append(boldText)
            pop()
            index = end + 2
        }
    }
}