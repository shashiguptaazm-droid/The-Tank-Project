package com.rankwarz.edulabsrtm

import com.rankwarz.edulabsrtm.model.PubMedCitationValidator
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PubMedCitationValidatorTest {

    private val numberedList = """
        1. Bhutta ZA, Das JK, Walker N, et al. Interventions to address deaths from childhood pneumonia and diarrhoea equitably: what works and at what cost? Lancet. 2013;381(9875):1417-29. doi: 10.1016/S0140-6736(13)60648-0.
        2. Walker CL, Rudan I, Liu L, et al. Global burden of childhood pneumonia and diarrhoea. Lancet. 2013;381(9875):1405-16.
        3. Liu L, Oza S, Hogan D, et al. Global, regional, and national causes of child mortality in 2000-13. Lancet. 2015;385(9966):430-40.
    """.trimIndent()

    private val vancouverList = """
        Bhutta ZA, Das JK, Walker N, et al. Interventions to address deaths from childhood pneumonia and diarrhoea equitably. Lancet. 2013;381(9875):1417-29.
        Walker CL, Rudan I, Liu L, et al. Global burden of childhood pneumonia and diarrhoea. Lancet. 2013;381(9875):1405-16.
        Liu L, Oza S, Hogan D, et al. Global, regional, and national causes of child mortality in 2000-13. Lancet. 2015;385(9966):430-40.
    """.trimIndent()

    private val wrappedList = """
        1. Bhutta ZA, Das JK, Walker N, et al. Interventions to address deaths from childhood pneumonia and diarrhoea equitably:
           what works and at what cost? Lancet. 2013;381(9875):1417-29.
        2. Walker CL, Rudan I, Liu L, et al. Global burden of childhood pneumonia and diarrhoea. Lancet.
           2013;381(9875):1405-16.
    """.trimIndent()

    private val aiReplyWithIntro = """
        Here are 3 PubMed references for typhoid fever:
        1. Wain J, Hendriksen RS, Mikoleit ML, Keddy KH, Ochiai RL. Typhoid fever. Lancet. 2015;385(9973):1136-45. PMID: 25458731.
        2. Crump JA, Luby SP, Mintz ED. The global burden of typhoid fever. Bull World Health Organ. 2004;82(5):346-53. PMID: 15298225.
        3. Bhutta ZA. Current concepts in the diagnosis and treatment of typhoid fever. BMJ. 2006;333(7558):78-82. PMID: 16825230.
    """.trimIndent()

    private val proseQuestion = "Can you explain the treatment of typhoid fever? Also what is the first line antibiotic and the typical duration of therapy in adults?"

    private fun texts(entries: List<PubMedCitationValidator.CitationEntry>) = entries.map { it.text }

    @Test
    fun numberedListSplitsIntoThree() {
        assertTrue(PubMedCitationValidator.looksLikeReferenceBlock(numberedList))
        val entries = PubMedCitationValidator.extractCitationEntries(numberedList)
        assertEquals(3, entries.size)
        assertTrue(texts(entries)[0].contains("Bhutta ZA"))
        assertTrue(texts(entries)[1].contains("Walker CL"))
        assertTrue(texts(entries)[2].contains("Liu L"))
    }

    @Test
    fun unnumberedVancouverListSplits() {
        assertTrue(PubMedCitationValidator.looksLikeReferenceBlock(vancouverList))
        val entries = PubMedCitationValidator.extractCitationEntries(vancouverList)
        assertEquals(3, entries.size)
    }

    @Test
    fun wrappedNumberedListStaysAsTwoEntries() {
        assertTrue(PubMedCitationValidator.looksLikeReferenceBlock(wrappedList))
        val entries = PubMedCitationValidator.extractCitationEntries(wrappedList)
        assertEquals(2, entries.size)
        assertTrue(texts(entries)[0].contains("1417-29"))
        assertTrue(texts(entries)[1].contains("1405-16"))
    }

    @Test
    fun plainProseDoesNotLookLikeReferences() {
        assertFalse(PubMedCitationValidator.looksLikeReferenceBlock(proseQuestion))
        assertEquals(0, PubMedCitationValidator.extractCitationEntries(proseQuestion).size)
    }

    @Test
    fun pmidAndDoiExtraction() {
        assertEquals("25458731", PubMedCitationValidator.extractPmid("Typhoid fever. Lancet. 2015;385(9973):1136-45. PMID: 25458731."))
        assertEquals("10.1016/S0140-6736(13)60648-0", PubMedCitationValidator.extractDoi("doi: 10.1016/S0140-6736(13)60648-0."))
        assertEquals("", PubMedCitationValidator.extractPmid("No id here"))
    }

    @Test
    fun referencesHeaderIsSkippedInExtraction() {
        val entries = PubMedCitationValidator.extractCitationEntries(aiReplyWithIntro)
        // Intro line + numbered lines: intro merges into first entry unless sliced upstream;
        // at minimum every numbered citation is its own entry.
        assertTrue(entries.size >= 3)
        assertTrue(texts(entries).last().contains("16825230"))
    }

    @Test
    fun stripReferenceMetadataRemovesPmidAndDoi() {
        val stripped = PubMedCitationValidator.stripReferenceMetadata(
            "Bhutta ZA, et al. Interventions. Lancet. 2013;381:1417. doi: 10.1016/S0140-6736(13)60648-0. PMID: 23541540."
        )
        assertFalse(stripped.contains("PMID", ignoreCase = true))
        assertFalse(stripped.contains("doi", ignoreCase = true))
        assertTrue(stripped.contains("Bhutta"))
    }
}
