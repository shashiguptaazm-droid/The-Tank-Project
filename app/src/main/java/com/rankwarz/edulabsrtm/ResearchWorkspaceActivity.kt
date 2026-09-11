package com.rankwarz.edulabsrtm

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import com.rankwarz.edulabsrtm.utils.ResearchSkill
import com.rankwarz.edulabsrtm.utils.ResearchSkillRegistry
import kotlinx.coroutines.launch

class ResearchWorkspaceActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EduLabsRTMThemeFromPreferences {
                ResearchWorkspaceScreen()
            }
        }
    }
}

sealed class WorkspaceSection(val title: String, val icon: ImageVector, val skillRange: IntRange?) {
    object Dashboard : WorkspaceSection("Dashboard", Icons.Default.Dashboard, null)
    object Research : WorkspaceSection("Research", Icons.Default.Science, 1..10)
    object Literature : WorkspaceSection("Literature", Icons.AutoMirrored.Filled.MenuBook, 11..20)
    object Evidence : WorkspaceSection("Evidence", Icons.Default.Verified, 21..30)
    object Dataset : WorkspaceSection("Dataset", Icons.Default.Dataset, 31..40)
    object Analysis : WorkspaceSection("Analysis", Icons.Default.Analytics, 41..45)
    object Writing : WorkspaceSection("Writing", Icons.Default.EditNote, 46..49)
    object Audit : WorkspaceSection("Audit", Icons.Default.Shield, 50..50)
    object Skills : WorkspaceSection("Skills", Icons.Default.Settings, 1..50)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResearchWorkspaceScreen() {
    var activeSection by remember { mutableStateOf<WorkspaceSection>(WorkspaceSection.Dashboard) }
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(modifier = Modifier.width(280.dp)) {
                Spacer(Modifier.height(12.dp))
                Text(
                    "RESEARCH OS",
                    modifier = Modifier.padding(16.dp),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                HorizontalDivider()
                val sections = listOf(
                    WorkspaceSection.Dashboard,
                    WorkspaceSection.Research,
                    WorkspaceSection.Literature,
                    WorkspaceSection.Evidence,
                    WorkspaceSection.Dataset,
                    WorkspaceSection.Analysis,
                    WorkspaceSection.Writing,
                    WorkspaceSection.Audit,
                    WorkspaceSection.Skills
                )
                sections.forEach { section ->
                    NavigationDrawerItem(
                        label = { Text(section.title) },
                        selected = activeSection == section,
                        onClick = { 
                            activeSection = section
                            scope.launch { drawerState.close() }
                        },
                        icon = { Icon(section.icon, contentDescription = null) },
                        modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding)
                    )
                }
            }
        }
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text("Medical Research AI — ${activeSection.title}") },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Default.Menu, contentDescription = "Menu")
                        }
                    }
                )
            }
        ) { padding ->
            Row(modifier = Modifier.padding(padding).fillMaxSize()) {
                // Main Workspace
                Box(modifier = Modifier.weight(1f).fillMaxHeight()) {
                    when (activeSection) {
                        WorkspaceSection.Dashboard -> DashboardScreen()
                        WorkspaceSection.Literature -> LiteratureScreen()
                        WorkspaceSection.Evidence -> EvidenceScreen()
                        WorkspaceSection.Dataset -> DatasetScreen()
                        WorkspaceSection.Analysis -> AnalysisScreen()
                        WorkspaceSection.Writing -> WritingScreen()
                        WorkspaceSection.Audit -> AuditScreen()
                        WorkspaceSection.Skills -> SkillsCenterScreen()
                        else -> SkillSectionScreen(activeSection)
                    }
                }
                
                // Right Activity Panel
                Surface(
                    modifier = Modifier.width(300.dp).fillMaxHeight(),
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
                    tonalElevation = 1.dp
                ) {
                    ActivityPanel()
                }
            }
        }
    }
}

@Composable
fun DashboardScreen() {
    val state = ResearchSharedState.workspaceState
    
    Column(modifier = Modifier.padding(24.dp).verticalScroll(rememberScrollState())) {
        Text("Research Planner", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(16.dp))
        
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text("Research Question", fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = state.researchQuestion,
                    onValueChange = {},
                    readOnly = true, // AI managed
                    modifier = Modifier.fillMaxWidth(),
                    placeholder = { Text("Enter your research question...") }
                )
                Spacer(Modifier.height(16.dp))
                Button(onClick = {}, modifier = Modifier.align(Alignment.CenterHorizontally)) {
                    Text("Re-Analyze Research")
                }
            }
        }
        
        Spacer(Modifier.height(24.dp))
        Text("Research Structure", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        HorizontalDivider(Modifier.padding(vertical = 12.dp))
        
        StructureItem("Population", state.pico.population.ifEmpty { "█████████████████" })
        StructureItem("Intervention", state.pico.intervention.ifEmpty { "█████████████████" })
        StructureItem("Comparison", state.pico.comparison.ifEmpty { "█████████████████" })
        StructureItem("Outcome", state.pico.outcome.ifEmpty { "█████████████████" })
        
        Spacer(Modifier.height(16.dp))
        StructureField("Study Type", state.studyType.ifEmpty { "Observational Study" })
        StructureField("Primary Objective", state.objectives.getOrNull(0) ?: "")
        StructureField("Secondary Objectives", state.objectives.drop(1).joinToString("\n"))
        StructureField("Hypothesis", state.hypothesis)
        StructureField("Variables", "")
        StructureField("Eligibility Criteria", "")
        
        Spacer(Modifier.height(24.dp))
        Button(onClick = {}, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp)) {
            Text("Approve Research Plan")
        }
    }
}

@Composable
fun LiteratureScreen() {
    Column(modifier = Modifier.padding(24.dp).verticalScroll(rememberScrollState())) {
        Text("🔎 Literature Search", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(16.dp))
        
        Text("Research topic:", style = MaterialTheme.typography.labelMedium)
        Text("Cataract + Phacoemulsification + Higher Order Aberrations", fontWeight = FontWeight.Bold)
        
        Spacer(Modifier.height(16.dp))
        Text("Generated Search", style = MaterialTheme.typography.labelSmall, color = Color.Gray)
        Surface(
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
            shape = RoundedCornerShape(8.dp),
            color = MaterialTheme.colorScheme.surfaceVariant,
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
        ) {
            Text(
                "(\"Cataract\"[MeSH]) AND (\"Phacoemulsification\"[MeSH]) AND (\"Aberrations, Optically Induced\"[MeSH])",
                modifier = Modifier.padding(12.dp),
                style = MaterialTheme.typography.bodySmall
            )
        }
        
        Button(onClick = {}, modifier = Modifier.align(Alignment.End)) {
            Text("Search PubMed")
        }
        
        Spacer(Modifier.height(24.dp))
        Text("Results: 248", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            ResultStat("☑ Relevant", "82", Color(0xFF4CAF50))
            ResultStat("☑ Highly relevant", "31", Color(0xFF2196F3))
            ResultStat("⚠ Duplicate", "14", Color(0xFFFBC02D))
            ResultStat("✕ Excluded", "121", Color(0xFFF44336))
        }
        
        Spacer(Modifier.height(24.dp))
        // Example Research Card
        ResearchCard("Impact of Phacoemulsification on HOA", "Doe J, et al. • Ophthalmology • 2024", "PMID: 34567890", "94%", "Level II")
    }
}

@Composable
fun EvidenceScreen() {
    Column(modifier = Modifier.padding(24.dp).verticalScroll(rememberScrollState())) {
        Text("REFERENCE VALIDATION", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        HorizontalDivider(Modifier.padding(vertical = 12.dp))
        
        Text("Reference #23", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.height(12.dp))
        
        ValidationRow("PMID", true)
        ValidationRow("DOI", true)
        ValidationRow("Author", true)
        ValidationRow("Journal", true)
        ValidationRow("Year", true)
        ValidationRow("Title", true)
        ValidationRow("Vancouver", true)
        
        Spacer(Modifier.height(32.dp))
        Text("Evidence", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        HorizontalDivider(Modifier.padding(vertical = 12.dp))
        
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("CLAIM", style = MaterialTheme.typography.labelSmall, color = Color.Gray)
                Text("\"Phacoemulsification may reduce...\"", fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(12.dp))
                Text("SOURCE", style = MaterialTheme.typography.labelSmall, color = Color.Gray)
                Text("├── PMID: 12345678\n├── Section: Results\n└── Evidence paragraph", style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(12.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Claim Support:", style = MaterialTheme.typography.bodySmall, modifier = Modifier.width(100.dp))
                    LinearProgressIndicator(progress = { 0.96f }, modifier = Modifier.weight(1f).height(8.dp), strokeCap = StrokeCap.Round)
                    Text(" 96%", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
                }
            }
        }
        
        Button(onClick = {}, modifier = Modifier.padding(top = 16.dp).align(Alignment.End)) {
            Text("View Source")
        }
    }
}

@Composable
fun DatasetScreen() {
    Column(modifier = Modifier.padding(24.dp).verticalScroll(rememberScrollState())) {
        Text("RESEARCH DATASET", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        HorizontalDivider(Modifier.padding(vertical = 12.dp))
        
        // Simple Table View
        TableColumn("Study", "n", "Outcome", "p-value")
        HorizontalDivider(thickness = 0.5.dp)
        TableDataRow("Study A", "120", "0.42", "0.03")
        TableDataRow("Study B", "185", "0.38", "0.01")
        TableDataRow("Study C", "92", "0.51", "0.08")
        
        Spacer(Modifier.height(32.dp))
        Row(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.weight(1f)) {
                Text("Entities", fontWeight = FontWeight.Bold)
                EntityItem("Cataract")
                EntityItem("Phacoemulsification")
                EntityItem("HOA")
                EntityItem("Visual acuity")
            }
            Column(modifier = Modifier.weight(1f)) {
                Text("Outcomes", fontWeight = FontWeight.Bold)
                EntityItem("BCVA")
                EntityItem("Spherical aberration")
                EntityItem("Coma")
                EntityItem("Contrast sensitivity")
            }
        }
    }
}

@Composable
fun AnalysisScreen() {
    Column(modifier = Modifier.padding(24.dp).verticalScroll(rememberScrollState())) {
        Text("📊 EVIDENCE ANALYSIS", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(16.dp))
        
        Text("Studies included: 31", style = MaterialTheme.typography.bodyMedium)
        Spacer(Modifier.height(12.dp))
        
        Text("Evidence Consensus", style = MaterialTheme.typography.labelSmall)
        LinearProgressIndicator(progress = { 0.72f }, modifier = Modifier.fillMaxWidth().height(12.dp), strokeCap = StrokeCap.Round)
        
        Row(modifier = Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Agreement 72%", style = MaterialTheme.typography.bodySmall, color = Color(0xFF4CAF50))
            Text("Conflicting 18%", style = MaterialTheme.typography.bodySmall, color = Color(0xFFF44336))
            Text("Insufficient 10%", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
        }
        
        Spacer(Modifier.height(32.dp))
        Text("Statistical Findings", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text("Outcome: BCVA", style = MaterialTheme.typography.labelMedium, color = Color.Gray)
        HorizontalDivider(Modifier.padding(vertical = 12.dp))
        
        StatsRow("Study A", "OR 1.42", "95% CI 1.2-1.7")
        StatsRow("Study B", "OR 1.31", "95% CI 1.1-1.5")
        StatsRow("Study C", "OR 1.51", "95% CI 1.3-1.9")
        
        Spacer(Modifier.height(24.dp))
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = {}, modifier = Modifier.weight(1f)) { Text("Compare") }
            Button(onClick = {}, modifier = Modifier.weight(1f)) { Text("Statistics") }
            Button(onClick = {}, modifier = Modifier.weight(1f)) { Text("Bias") }
        }
    }
}

@Composable
fun WritingScreen() {
    Column(modifier = Modifier.padding(24.dp).verticalScroll(rememberScrollState())) {
        Text("THESIS BUILDER", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        HorizontalDivider(Modifier.padding(vertical = 12.dp))
        
        Row(modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
            ChapterChip("Title", true)
            ChapterChip("Introduction", true)
            ChapterChip("Literature Review", true)
            ChapterChip("Aim & Objectives", false)
            ChapterChip("Methodology", false)
        }
        
        Spacer(Modifier.height(24.dp))
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("INTRODUCTION", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                Spacer(Modifier.height(8.dp))
                Text(
                    "Cataract is the leading cause of reversible blindness worldwide. With advancements in surgical techniques, phacoemulsification has become the standard of care...",
                    style = MaterialTheme.typography.bodyMedium
                )
                Spacer(Modifier.height(16.dp))
                HorizontalDivider()
                Row(modifier = Modifier.padding(top = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("Evidence: 12 sources", style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
                    Icon(Icons.Default.Verified, contentDescription = null, tint = Color(0xFF4CAF50), modifier = Modifier.size(14.dp))
                    Text(" 18/18 Claims Verified", style = MaterialTheme.typography.bodySmall, color = Color(0xFF4CAF50))
                }
            }
        }
        
        Row(modifier = Modifier.padding(top = 16.dp).align(Alignment.End), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TextButton(onClick = {}) { Text("Regenerate") }
            Button(onClick = {}) { Text("Verify Section") }
        }
    }
}

@Composable
fun AuditScreen() {
    Column(modifier = Modifier.padding(24.dp).verticalScroll(rememberScrollState())) {
        Text("🛡️ RESEARCH AUDIT", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        HorizontalDivider(Modifier.padding(vertical = 12.dp))
        
        AuditInfoRow("Claims", "184", "179 Supported", "5 Unsupported", true)
        AuditInfoRow("References", "126", "126 Validated", "0 Invalid", true)
        AuditInfoRow("PMIDs", "126", "126 Verified", "0 Invalid", true)
        AuditInfoRow("Numerical values", "43", "43 Checked", "0 Errors", true)
        
        Spacer(Modifier.height(24.dp))
        Text("Citation consistency: 100%", fontWeight = FontWeight.Bold, color = Color(0xFF4CAF50))
        
        Card(modifier = Modifier.fillMaxWidth().padding(top = 16.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFFFFEBEE))) {
            Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Warning, contentDescription = null, tint = Color.Red)
                Spacer(Modifier.width(12.dp))
                Text("5 Unsupported claims found in Results section.", color = Color.Red, fontWeight = FontWeight.Bold)
            }
        }
        
        Spacer(Modifier.height(32.dp))
        Column(modifier = Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("RESEARCH SCORE", style = MaterialTheme.typography.labelLarge)
            Text("97%", style = MaterialTheme.typography.displayMedium, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
            LinearProgressIndicator(progress = { 0.97f }, modifier = Modifier.width(200.dp).height(12.dp), strokeCap = StrokeCap.Round)
            Spacer(Modifier.height(16.dp))
            Text("✅ READY FOR FINAL OUTPUT", fontWeight = FontWeight.Bold, color = Color(0xFF4CAF50))
        }
    }
}

@Composable
fun SkillSectionScreen(section: WorkspaceSection) {
    val skills = ResearchSkillRegistry.SKILLS.filter { it.id in (section.skillRange ?: 0..0) }
    
    LazyColumn(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        item {
            Text(section.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text("Automated pipeline for this stage", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
            Spacer(Modifier.height(16.dp))
        }
        items(skills) { skill ->
            SkillCard(skill)
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
fun SkillCard(skill: ResearchSkill) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(skill.name, fontWeight = FontWeight.Bold)
                Text(skill.description, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
            }
            if (skill.isDeterministic) {
                Icon(Icons.Default.Code, contentDescription = "Deterministic", tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(16.dp))
            }
        }
    }
}

@Composable
fun SkillsCenterScreen() {
    LazyColumn(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        item {
            Text("⚙️ RESEARCH AI SKILLS", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(16.dp))
        }
        
        val categories = listOf("Research", "Search", "Validation", "Data", "Generation")
        categories.forEach { category ->
            item {
                Text(category.uppercase(), style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                HorizontalDivider(Modifier.padding(vertical = 8.dp))
            }
            val catSkills = ResearchSkillRegistry.SKILLS.filter { it.category == category }
            items(catSkills) { skill ->
                Row(modifier = Modifier.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(modifier = Modifier.size(8.dp).background(Color(0xFF4CAF50), CircleShape))
                    Spacer(Modifier.width(12.dp))
                    Text(skill.name, style = MaterialTheme.typography.bodyMedium)
                }
            }
            item { Spacer(Modifier.height(24.dp)) }
        }
    }
}

// Helper Components

@Composable
fun StructureItem(label: String, value: String) {
    Row(modifier = Modifier.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, modifier = Modifier.width(120.dp), fontWeight = FontWeight.SemiBold, color = Color.Gray, style = MaterialTheme.typography.bodySmall)
        Text(value, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun StructureField(label: String, value: String) {
    Column(modifier = Modifier.padding(vertical = 6.dp)) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        Text(value.ifEmpty { "Pending analysis..." }, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
fun ResultStat(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, fontWeight = FontWeight.Bold, color = color, fontSize = 18.sp)
        Text(label, style = MaterialTheme.typography.labelSmall, color = Color.Gray)
    }
}

@Composable
fun ResearchCard(title: String, meta: String, pmid: String, relevance: String, evidence: String) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(meta, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
            Text(pmid, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Column {
                    Text("Relevance", style = MaterialTheme.typography.labelSmall, color = Color.Gray)
                    Text(relevance, fontWeight = FontWeight.Bold, color = Color(0xFF4CAF50))
                }
                Column {
                    Text("Evidence", style = MaterialTheme.typography.labelSmall, color = Color.Gray)
                    Text(evidence, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.secondary)
                }
            }
            Row(modifier = Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = {}, modifier = Modifier.weight(1f)) { Text("Abstract", fontSize = 10.sp) }
                TextButton(onClick = {}, modifier = Modifier.weight(1f)) { Text("Full Text", fontSize = 10.sp) }
                Button(onClick = {}, modifier = Modifier.weight(1f), shape = RoundedCornerShape(4.dp)) { Text("Add", fontSize = 10.sp) }
            }
        }
    }
}

@Composable
fun ValidationRow(label: String, isValid: Boolean) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, fontWeight = FontWeight.SemiBold, color = Color.Gray)
        Text(if (isValid) "✅ VALID" else "❌ INVALID", fontWeight = FontWeight.Bold, color = if (isValid) Color(0xFF4CAF50) else Color.Red)
    }
}

@Composable
fun TableColumn(vararg labels: String) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        labels.forEach { label ->
            Text(label, modifier = Modifier.weight(1f), fontWeight = FontWeight.Black, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun TableDataRow(vararg values: String) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        values.forEach { value ->
            Text(value, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun EntityItem(name: String) {
    Text("• $name", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(vertical = 2.dp))
}

@Composable
fun StatsRow(label: String, val1: String, val2: String) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Text(label, modifier = Modifier.width(100.dp), fontWeight = FontWeight.Bold)
        Text(val1, modifier = Modifier.weight(1f), color = MaterialTheme.colorScheme.primary)
        Text(val2, color = Color.Gray, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun ChapterChip(label: String, done: Boolean) {
    Surface(
        modifier = Modifier.padding(end = 8.dp),
        shape = RoundedCornerShape(16.dp),
        color = if (done) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, if (done) Color.Transparent else MaterialTheme.colorScheme.outlineVariant)
    ) {
        Row(modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            if (done) Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(14.dp), tint = MaterialTheme.colorScheme.onPrimaryContainer)
            Text(label, style = MaterialTheme.typography.labelMedium, modifier = Modifier.padding(start = 4.dp))
        }
    }
}

@Composable
fun AuditInfoRow(label: String, total: String, info1: String, info2: String, ok: Boolean) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(modifier = Modifier.weight(1f)) {
            Text(label, fontWeight = FontWeight.Bold)
            Row {
                Text(info1, style = MaterialTheme.typography.bodySmall, color = if (ok) Color(0xFF4CAF50) else Color.Gray)
                Text(" • ", style = MaterialTheme.typography.bodySmall)
                Text(info2, style = MaterialTheme.typography.bodySmall, color = if (info2.contains("Unsupported") || info2.contains("Invalid") || info2.contains("Errors")) Color.Red else Color.Gray)
            }
        }
        Text(total, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = if (ok) MaterialTheme.colorScheme.primary else Color.Red)
    }
}

@Composable
fun ActivityPanel() {
    Column(modifier = Modifier.padding(16.dp)) {
        Text("AI ACTIVITY", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
        HorizontalDivider(Modifier.padding(vertical = 12.dp))
        
        ActivityInfoItem("Skill Running", "None")
        ActivityInfoItem("Evidence", "0 points extracted")
        ActivityInfoItem("Sources", "0 validated")
        ActivityInfoItem("Confidence", "0%")
        
        Spacer(Modifier.height(24.dp))
        Text("LOGS", style = MaterialTheme.typography.labelSmall, color = Color.Gray)
        Spacer(Modifier.height(8.dp))
        Text("Waiting for user input...", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
    }
}

@Composable
fun ActivityInfoItem(label: String, value: String) {
    Column(modifier = Modifier.padding(vertical = 8.dp)) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = Color.Gray)
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
    }
}
