package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.SharedPreferences
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import org.json.JSONObject
import org.jsoup.Jsoup
import org.jsoup.internal.Normalizer.normalize
import java.util.LinkedHashMap
import java.util.Locale

data class CollegeDetailData(
    val collegeName: String,
    val detailUrl: String = "",
    val address: String = "",
    val state: String = "",
    val pinCode: String = "",
    val annualFee: String = "",
    val nriFee: String = "",
    val stipend1: String = "",
    val stipend2: String = "",
    val stipend3: String = "",
    val dean: String = "",
    val nodalOfficer: String = "",
    val website: String = "",
    val allFields: LinkedHashMap<String, String> = linkedMapOf(),
    val rawHtml: String = "",
    val dataInReview: Boolean = false,
    val reviewMessage: String = ""
)

object CollegeDetailCache {
    private const val PREF_NAME = "college_detail_cache_v1"

    private fun prefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
    }

    private fun key(name: String): String = "college_" + normalize(name)

    fun save(context: Context, data: CollegeDetailData) {
        val obj = JSONObject().apply {
            put("collegeName", data.collegeName)
            put("detailUrl", data.detailUrl)
            put("address", data.address)
            put("state", data.state)
            put("pinCode", data.pinCode)
            put("annualFee", data.annualFee)
            put("nriFee", data.nriFee)
            put("stipend1", data.stipend1)
            put("stipend2", data.stipend2)
            put("stipend3", data.stipend3)
            put("dean", data.dean)
            put("nodalOfficer", data.nodalOfficer)
            put("website", data.website)
            put("rawHtml", data.rawHtml)
            put("dataInReview", data.dataInReview)
            put("reviewMessage", data.reviewMessage)
            put("allFields", JSONObject(data.allFields as Map<*, *>))
        }

        prefs(context).edit().putString(key(data.collegeName), obj.toString()).apply()
    }

    fun load(context: Context, collegeName: String): CollegeDetailData? {
        val raw = prefs(context).getString(key(collegeName), null) ?: return null
        return try {
            val obj = JSONObject(raw)
            val fieldsObj = obj.optJSONObject("allFields")
            val fields = LinkedHashMap<String, String>()
            if (fieldsObj != null) {
                val keys = fieldsObj.keys()
                while (keys.hasNext()) {
                    val k = keys.next()
                    fields[k] = fieldsObj.optString(k, "")
                }
            }

            CollegeDetailData(
                collegeName = obj.optString("collegeName", collegeName),
                detailUrl = obj.optString("detailUrl", ""),
                address = obj.optString("address", ""),
                state = obj.optString("state", ""),
                pinCode = obj.optString("pinCode", ""),
                annualFee = obj.optString("annualFee", ""),
                nriFee = obj.optString("nriFee", ""),
                stipend1 = obj.optString("stipend1", ""),
                stipend2 = obj.optString("stipend2", ""),
                stipend3 = obj.optString("stipend3", ""),
                dean = obj.optString("dean", ""),
                nodalOfficer = obj.optString("nodalOfficer", ""),
                website = obj.optString("website", ""),
                allFields = fields,
                rawHtml = obj.optString("rawHtml", ""),
                dataInReview = obj.optBoolean("dataInReview", false),
                reviewMessage = obj.optString("reviewMessage", "")
            )
        } catch (_: Exception) {
            null
        }
    }
}

object CollegeHtmlRepository {

    private val client = OkHttpClient.Builder()
        .followRedirects(true)
        .followSslRedirects(true)
        .build()

    fun loadCollege(
        context: Context,
        listUrl: String,
        collegeName: String
    ): CollegeDetailData {
        CollegeDetailCache.load(context, collegeName)?.let { cached ->
            return cached
        }

        return try {
            val listHtml = downloadHtml(listUrl)
            if (listHtml.isBlank()) {
                return review(collegeName, "Data about the college is in review")
            }

            val detailHref = findCollegeHref(listHtml, collegeName)
            if (detailHref.isBlank()) {
                return review(collegeName, "Data about the college is in review")
            }

            val detailUrl = resolveUrl(listUrl, detailHref)
            if (detailUrl.isBlank()) {
                return review(collegeName, "Data about the college is in review")
            }

            val detailHtml = downloadHtml(detailUrl)
            if (detailHtml.isBlank()) {
                return review(collegeName, "Data about the college is in review", detailUrl)
            }

            val parsed = parseDetailHtml(collegeName, detailUrl, detailHtml)
            CollegeDetailCache.save(context, parsed)
            parsed
        } catch (_: Exception) {
            review(collegeName, "Data about the college is in review")
        }
    }

    private fun review(name: String, msg: String, detailUrl: String = ""): CollegeDetailData {
        return CollegeDetailData(
            collegeName = name,
            detailUrl = detailUrl,
            dataInReview = true,
            reviewMessage = msg
        )
    }

    private fun downloadHtml(url: String): String {
        val req = Request.Builder().url(url).get().build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return ""
            return resp.body?.string().orEmpty()
        }
    }

    private fun findCollegeHref(listHtml: String, collegeName: String): String {
        val doc = Jsoup.parse(listHtml)
        val cards = doc.select("a.college-card")

        val target = normalize(collegeName)
        var fallbackHref = ""

        for (card in cards) {
            val title = card.selectFirst("h3")?.text()?.trim().orEmpty()
            val normTitle = normalize(title)
            val href = card.attr("href").trim()

            if (normTitle.isNotBlank() && href.isNotBlank()) {
                if (normTitle == target) return href
                if (fallbackHref.isBlank() && (normTitle.contains(target) || target.contains(normTitle))) {
                    fallbackHref = href
                }
            }
        }

        return fallbackHref
    }

    private fun resolveUrl(baseUrl: String, href: String): String {
        if (href.startsWith("http", ignoreCase = true)) return href
        val base = baseUrl.toHttpUrlOrNull() ?: return href
        return base.resolve(href)?.toString() ?: href
    }

    private fun parseDetailHtml(
        collegeName: String,
        detailUrl: String,
        html: String
    ): CollegeDetailData {
        val doc = Jsoup.parse(html)

        val headerTitle = doc.selectFirst(".card-header h1")?.text()?.trim()
            ?: doc.selectFirst("h1")?.text()?.trim()
            ?: collegeName

        val headerAddress = doc.selectFirst(".card-header .address")?.text()?.trim().orEmpty()

        val statBoxes = doc.select(".stat-box")
        var annualFee = ""
        var nriFee = ""
        var stipend1 = ""
        var stipend2 = ""
        var stipend3 = ""

        statBoxes.forEach { box ->
            val heading = box.selectFirst("h3")?.text()?.trim().orEmpty()
            val value = box.selectFirst("p")?.text()?.trim().orEmpty()

            when {
                heading.contains("Annual Fee", ignoreCase = true) -> annualFee = value
                heading.contains("NRI Fee", ignoreCase = true) -> nriFee = value
                heading.contains("1st Year", ignoreCase = true) -> stipend1 = value
                heading.contains("2nd Year", ignoreCase = true) -> stipend2 = value
                heading.contains("3rd Year", ignoreCase = true) -> stipend3 = value
            }
        }

        var dean = ""
        var nodalOfficer = ""
        var website = ""

        doc.select(".info-item").forEach { item ->
            val text = item.text().trim()
            val link = item.selectFirst("a[href]")?.attr("href").orEmpty()

            when {
                text.contains("Dean / Principal", ignoreCase = true) ||
                        text.contains("Name of Dean", ignoreCase = true) ||
                        text.contains("Dean", ignoreCase = true) -> dean = text

                text.contains("Nodal Officer", ignoreCase = true) -> nodalOfficer = text

                text.contains("Website", ignoreCase = true) -> {
                    website = if (link.isNotBlank()) link else text
                }
            }
        }

        val allFields = LinkedHashMap<String, String>()
        var state = ""
        var pinCode = ""

        doc.select("table tr").forEach { row ->
            val tds = row.select("td")
            if (tds.size >= 2) {
                val key = compact(tds[0].text())
                val value = compact(tds[1].text())
                if (key.isNotBlank()) {
                    allFields[key] = value
                    when {
                        key.contains("state", ignoreCase = true) && state.isBlank() -> state = value
                        key.contains("pin code", ignoreCase = true) && pinCode.isBlank() -> pinCode = value
                        key.contains("website address", ignoreCase = true) && website.isBlank() -> {
                            website = tds[1].selectFirst("a[href]")?.attr("href") ?: value
                        }
                        key.contains("name of dean", ignoreCase = true) && dean.isBlank() -> dean = value
                        key.contains("name of nodal officer", ignoreCase = true) && nodalOfficer.isBlank() -> nodalOfficer = value
                    }
                }
            }
        }

        if (headerAddress.isNotBlank() && state.isBlank()) {
            val guessState = guessStateFromAddress(headerAddress)
            if (guessState.isNotBlank()) state = guessState
        }

        return CollegeDetailData(
            collegeName = headerTitle,
            detailUrl = detailUrl,
            address = headerAddress.ifBlank { "Not available" },
            state = state.ifBlank { "Not available" },
            pinCode = pinCode.ifBlank { "Not available" },
            annualFee = annualFee.ifBlank { "Contact To College" },
            nriFee = nriFee.ifBlank { "Contact To College" },
            stipend1 = stipend1.ifBlank { "Not available" },
            stipend2 = stipend2.ifBlank { "Not available" },
            stipend3 = stipend3.ifBlank { "Not available" },
            dean = dean.ifBlank { "Not available" },
            nodalOfficer = nodalOfficer.ifBlank { "Not available" },
            website = website.ifBlank { "Not available" },
            allFields = allFields,
            rawHtml = html,
            dataInReview = false,
            reviewMessage = ""
        )
    }

    private fun normalize(text: String): String {
        return text.lowercase(Locale.getDefault())
            .replace(Regex("[^a-z0-9 ]"), " ")
            .replace(Regex("\\s+"), " ")
            .trim()
    }

    private fun compact(text: String): String {
        return text.replace(Regex("\\s+"), " ").trim()
    }

    private fun guessStateFromAddress(address: String): String {
        val states = listOf(
            "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
            "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
            "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
            "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
            "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
            "Delhi", "Jammu and Kashmir", "Ladakh"
        )

        val lower = address.lowercase(Locale.getDefault())
        return states.firstOrNull { lower.contains(it.lowercase(Locale.getDefault())) }.orEmpty()
    }
}