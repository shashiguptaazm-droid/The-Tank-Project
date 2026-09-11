package com.rankwarz.edulabsrtm

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.util.Patterns
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.google.firebase.messaging.FirebaseMessaging
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar

class RegisterActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EduLabsRTMThemeFromPreferences {
                Surface {
                    RegisterScreen(
                        onLoginClick = {
                            startActivity(
                                Intent(this, LoginActivity::class.java)
                            )
                            finish()
                        },
                        onDashboard = {
                            startActivity(
                                Intent(this, DashboardActivity::class.java)
                            )
                            finishAffinity()
                        }
                    )
                }
            }
        }
    }
}

private enum class RegisterStep {
    FORM, OTP
}

private fun normalizeCollegeName(value: String): String {
    return value
        .replace("\n", " ")
        .replace("\r", " ")
        .replace(Regex("\\s+"), " ")
        .trim()
}

private fun loadColleges(context: Context): List<String> {
    return try {
        val colleges = mutableSetOf<String>()

        try {
            val json1 = context.assets.open("predictor_data_new.json")
                .bufferedReader()
                .use { it.readText() }

            val root = JSONArray(json1)

            for (i in 0 until root.length()) {
                val obj = root.optJSONObject(i) ?: continue

                if (obj.optString("type") == "table") {
                    val data = obj.optJSONArray("data") ?: continue

                    for (j in 0 until data.length()) {
                        val collegeObj = data.optJSONObject(j) ?: continue
                        val collegeName = normalizeCollegeName(
                            collegeObj.optString("college_name").trim()
                        )

                        if (collegeName.isNotBlank()) {
                            colleges.add(collegeName)
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("RegisterActivity", "Error loading predictor_data_new.json", e)
        }

        try {
            val json2 = context.assets.open("colleges.json")
                .bufferedReader()
                .use { it.readText() }

            val array = JSONArray(json2)

            for (i in 0 until array.length()) {
                val obj = array.optJSONObject(i) ?: continue
                val name = normalizeCollegeName(obj.optString("name").trim())

                if (name.isNotBlank()) {
                    colleges.add(name)
                }
            }
        } catch (e: Exception) {
            Log.e("RegisterActivity", "Error loading colleges.json", e)
        }

        colleges
            .filter { it.isNotBlank() }
            .sorted()

    } catch (e: Exception) {
        Log.e("RegisterActivity", "Failed to load college data", e)
        emptyList()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SearchableCollegeField(
    value: String,
    onValueChange: (String) -> Unit
) {
    val context = LocalContext.current

    val allColleges = remember(context) {
        loadColleges(context)
    }

    var expanded by remember { mutableStateOf(false) }

    val filteredColleges = remember(value, allColleges) {
        val query = value.trim()
        if (query.length < 3) {
            emptyList<String>()
        } else {
            allColleges
                .filter { it.contains(query, ignoreCase = true) || it.split(" ").any { word -> word.startsWith(query, ignoreCase = true) } }
                .take(20)
        }
    }

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded }
    ) {
        OutlinedTextField(
            value = value,
            onValueChange = {
                onValueChange(it)
                expanded = it.trim().length >= 3
            },
            modifier = Modifier
                .fillMaxWidth()
                .menuAnchor(),
            label = { Text("College Name") },
            singleLine = true,
            shape = RoundedCornerShape(16.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = MaterialTheme.colorScheme.primary,
                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                focusedLabelColor = MaterialTheme.colorScheme.primary,
                unfocusedLabelColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                cursorColor = MaterialTheme.colorScheme.primary,
                focusedTextColor = MaterialTheme.colorScheme.onSurface,
                unfocusedTextColor = MaterialTheme.colorScheme.onSurface
            )
        )

        ExposedDropdownMenu(
            expanded = expanded && filteredColleges.isNotEmpty(),
            onDismissRequest = { expanded = false }
        ) {
            filteredColleges.forEach { college ->
                DropdownMenuItem(
                    text = { Text(college) },
                    onClick = {
                        onValueChange(college)
                        expanded = false
                    }
                )
            }
        }
    }
}

private val INDIAN_STATES = listOf(
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Puducherry"
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun YearSelectionField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String = "Batch Year"
) {
    val currentYear = Calendar.getInstance().get(Calendar.YEAR)
    val years = remember {
        (currentYear downTo 2000).map { it.toString() }
    }

    var expanded by remember { mutableStateOf(false) }

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded }
    ) {
        OutlinedTextField(
            value = value,
            onValueChange = { },
            readOnly = true,
            modifier = Modifier
                .fillMaxWidth()
                .menuAnchor(),
            label = { Text(label) },
            trailingIcon = {
                ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded)
            },
            singleLine = true,
            shape = RoundedCornerShape(16.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = MaterialTheme.colorScheme.primary,
                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                focusedLabelColor = MaterialTheme.colorScheme.primary,
                unfocusedLabelColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                cursorColor = MaterialTheme.colorScheme.primary,
                focusedTextColor = MaterialTheme.colorScheme.onSurface,
                unfocusedTextColor = MaterialTheme.colorScheme.onSurface
            )
        )

        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false }
        ) {
            years.forEach { year ->
                DropdownMenuItem(
                    text = { Text(year) },
                    onClick = {
                        onValueChange(year)
                        expanded = false
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StateDropdownField(
    value: String,
    onValueChange: (String) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded }
    ) {
        OutlinedTextField(
            value = value,
            onValueChange = { },
            readOnly = true,
            modifier = Modifier
                .fillMaxWidth()
                .menuAnchor(),
            label = { Text("State") },
            trailingIcon = {
                ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded)
            },
            singleLine = true,
            shape = RoundedCornerShape(16.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = MaterialTheme.colorScheme.primary,
                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                focusedLabelColor = MaterialTheme.colorScheme.primary,
                unfocusedLabelColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                cursorColor = MaterialTheme.colorScheme.primary,
                focusedTextColor = MaterialTheme.colorScheme.onSurface,
                unfocusedTextColor = MaterialTheme.colorScheme.onSurface
            )
        )

        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false }
        ) {
            INDIAN_STATES.forEach { state ->
                DropdownMenuItem(
                    text = { Text(state) },
                    onClick = {
                        onValueChange(state)
                        expanded = false
                    }
                )
            }
        }
    }
}

@Composable
fun RegisterScreen(
    onLoginClick: () -> Unit,
    onDashboard: () -> Unit
) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    var step by remember { mutableStateOf(RegisterStep.FORM) }
    var name by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var mobile by remember { mutableStateOf("") }
    var collegeName by remember { mutableStateOf("") }
    var batchYear by remember { mutableStateOf("") }
    var passingYear by remember { mutableStateOf("") }
    var selectedState by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var referralCode by remember {
        mutableStateOf(
            context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
                .getString("pending_referral_code", "")
                .orEmpty()
        )
    }
    var otp by remember { mutableStateOf("") }

    var loading by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }

    val heroColor = MaterialTheme.colorScheme.primary
    val bgColor = MaterialTheme.colorScheme.background
    val formBorder = MaterialTheme.colorScheme.outline
    val hintColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)

    fun showToast(msg: String) {
        Toast.makeText(context, msg, Toast.LENGTH_SHORT).show()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(bgColor)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(20.dp)
        ) {
            Spacer(modifier = Modifier.height(36.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(28.dp),
                colors = CardDefaults.cardColors(containerColor = heroColor),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(
                            start = 24.dp,
                            top = 28.dp,
                            end = 24.dp,
                            bottom = 28.dp
                        ),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Image(
                        painter = painterResource(id = R.drawable.medigyaan_logo),
                        contentDescription = "Logo",
                        modifier = Modifier.size(96.dp)
                    )

                    Spacer(modifier = Modifier.height(18.dp))

                    Text(
                        text = "RankWarz",
                        color = Color.White,
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Black,
                        letterSpacing = 0.5.sp
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        text = "Empowering Competitive Learning",
                        color = Color(0xFFCFCFCF),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp),
                shape = RoundedCornerShape(28.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                border = BorderStroke(1.dp, formBorder),
                elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp)
                ) {
                    Text(
                        text = if (step == RegisterStep.FORM) "Create Account" else "Verify OTP",
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Black
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = if (step == RegisterStep.FORM)
                            "Register to continue to your dashboard"
                        else
                            "Enter the 6-digit OTP sent to your mobile number",
                        color = hintColor,
                        fontSize = 14.sp
                    )

                    if (message.isNotBlank()) {
                        Spacer(modifier = Modifier.height(14.dp))
                        Text(
                            text = message,
                            color = MaterialTheme.colorScheme.error,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    Spacer(modifier = Modifier.height(28.dp))

                    if (step == RegisterStep.FORM) {
                        RegisterTextField(
                            value = name,
                            onValueChange = { name = it },
                            label = "Full Name",
                            keyboardType = KeyboardType.Text
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        RegisterTextField(
                            value = email,
                            onValueChange = { email = it },
                            label = "Email Address",
                            keyboardType = KeyboardType.Email
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        RegisterTextField(
                            value = mobile,
                            onValueChange = {
                                val digits = it.filter { c -> c.isDigit() }
                                mobile = if (digits.length <= 10) digits else digits.take(10)
                            },
                            label = "Mobile / WhatsApp Number",
                            keyboardType = KeyboardType.Number
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        SearchableCollegeField(
                            value = collegeName,
                            onValueChange = { collegeName = it }
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        YearSelectionField(
                            value = batchYear,
                            onValueChange = { batchYear = it }
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        YearSelectionField(
                            value = passingYear,
                            onValueChange = { passingYear = it },
                            label = "Passing Year"
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        StateDropdownField(
                            value = selectedState,
                            onValueChange = { selectedState = it }
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        RegisterTextField(
                            value = password,
                            onValueChange = { password = it },
                            label = "Password",
                            keyboardType = KeyboardType.Password,
                            password = true
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        RegisterTextField(
                            value = confirmPassword,
                            onValueChange = { confirmPassword = it },
                            label = "Repeat Password",
                            keyboardType = KeyboardType.Password,
                            password = true
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        RegisterTextField(
                            value = referralCode,
                            onValueChange = {
                                referralCode = it.uppercase()
                                    .replace(Regex("[^A-Z0-9]"), "")
                                    .take(32)
                                context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
                                    .edit()
                                    .putString("pending_referral_code", referralCode)
                                    .apply()
                            },
                            label = "Referral Code (Optional)",
                            keyboardType = KeyboardType.Text
                        )

                        Spacer(modifier = Modifier.height(24.dp))

                        Button(
                            onClick = {
                                message = ""

                                when {
                                    name.isBlank() -> {
                                        showToast("Enter name")
                                        return@Button
                                    }

                                    !Patterns.EMAIL_ADDRESS.matcher(email).matches() -> {
                                        showToast("Invalid email")
                                        return@Button
                                    }

                                    mobile.length != 10 || !mobile.matches(Regex("^[6-9]\\d{9}$")) -> {
                                        showToast("Invalid 10-digit Indian mobile number")
                                        return@Button
                                    }

                                    collegeName.isBlank() -> {
                                        showToast("Enter college name")
                                        return@Button
                                    }

                                    batchYear.length != 4 -> {
                                        showToast("Select valid batch year")
                                        return@Button
                                    }

                                    passingYear.length != 4 -> {
                                        showToast("Select passing year")
                                        return@Button
                                    }

                                    selectedState.isBlank() -> {
                                        showToast("Select your state")
                                        return@Button
                                    }

                                    password.length < 6 -> {
                                        showToast("Password must be at least 6 characters")
                                        return@Button
                                    }

                                    password != confirmPassword -> {
                                        showToast("Passwords do not match")
                                        return@Button
                                    }
                                }

                                loading = true
                                sendOtp(
                                    context = context,
                                    name = name.trim(),
                                    email = email.trim(),
                                    mobile = mobile.trim(),
                                    collegeName = collegeName.trim(),
                                    batchYear = batchYear.trim(),
                                    passingYear = passingYear.trim(),
                                    state = selectedState.trim(),
                                    password = password,
                                    onSuccess = { serverMsg ->
                                        loading = false
                                        message = serverMsg.ifBlank { "OTP sent successfully" }
                                        step = RegisterStep.OTP
                                        showToast("OTP sent")
                                    },
                                    onError = { err ->
                                        loading = false
                                        message = err
                                        showToast(err)
                                    }
                                )
                            },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(56.dp),
                            shape = RoundedCornerShape(16.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = heroColor,
                                contentColor = Color.White
                            ),
                            enabled = !loading
                        ) {
                            Text(
                                text = if (loading) "Please Wait..." else "Send OTP",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    } else {
                        Text(
                            text = "$name • $mobile",
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                            fontSize = 13.sp
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        RegisterTextField(
                            value = otp,
                            onValueChange = {
                                val digits = it.filter { c -> c.isDigit() }
                                otp = if (digits.length <= 6) digits else digits.take(6)
                            },
                            label = "Enter OTP",
                            keyboardType = KeyboardType.Number
                        )

                        Spacer(modifier = Modifier.height(24.dp))

                        Button(
                            onClick = {
                                message = ""

                                if (otp.length != 6) {
                                    showToast("Enter a valid 6-digit OTP")
                                    return@Button
                                }

                                loading = true
                                verifyOtp(
                                    context = context,
                                    name = name.trim(),
                                    email = email.trim(),
                                    mobile = mobile.trim(),
                                    collegeName = collegeName.trim(),
                                    batchYear = batchYear.trim(),
                                    passingYear = passingYear.trim(),
                                    state = selectedState.trim(),
                                    password = password,
                                    otp = otp.trim(),
                                    referralCode = referralCode.trim(),
                                    onSuccess = { userId, userName, userEmail ->
                                        loading = false
                                        saveUserSession(context, userId, userName, userEmail)
                                        applyReferralCode(context, userId, referralCode.trim(), userEmail)
                                        syncFcmToken(context, userId)
                                        onDashboard()
                                    },
                                    onError = { err ->
                                        loading = false
                                        message = err
                                        showToast(err)
                                    }
                                )
                            },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(56.dp),
                            shape = RoundedCornerShape(16.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = heroColor,
                                contentColor = Color.White
                            ),
                            enabled = !loading
                        ) {
                            Text(
                                text = if (loading) "Please Wait..." else "Verify OTP",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        TextButton(
                            onClick = {
                                loading = false
                                otp = ""
                                step = RegisterStep.FORM
                                message = ""
                            },
                            modifier = Modifier.align(Alignment.CenterHorizontally)
                        ) {
                            Text(
                                text = "Edit registration details",
                                color = MaterialTheme.colorScheme.primary,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(22.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        HorizontalDivider(
                            modifier = Modifier.weight(1f),
                            color = MaterialTheme.colorScheme.outline
                        )

                        Text(
                            text = "  OR  ",
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium
                        )

                        HorizontalDivider(
                            modifier = Modifier.weight(1f),
                            color = MaterialTheme.colorScheme.outline
                        )
                    }

                    Spacer(modifier = Modifier.height(18.dp))

                    OutlinedButton(
                        onClick = {
                            showToast("Google registration can be added with your Google backend flow")
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp),
                        shape = RoundedCornerShape(16.dp),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = MaterialTheme.colorScheme.onSurface
                        )
                    ) {
                        Text(
                            text = "Continue with Google",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Already have an account?",
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                            fontSize = 14.sp
                        )

                        TextButton(onClick = onLoginClick) {
                            Text(
                                text = "Login",
                                color = MaterialTheme.colorScheme.primary,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }
        }

        if (loading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Surface(
                    shape = RoundedCornerShape(18.dp),
                    tonalElevation = 6.dp,
                    shadowElevation = 6.dp,
                    color = MaterialTheme.colorScheme.surface
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 20.dp, vertical = 16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(22.dp),
                            strokeWidth = 2.5.dp
                        )
                        Spacer(modifier = Modifier.width(14.dp))
                        Text(
                            text = "Please wait...",
                            color = MaterialTheme.colorScheme.onSurface,
                            fontSize = 14.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun RegisterTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    keyboardType: KeyboardType,
    password: Boolean = false
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth(),
        label = { Text(label) },
        singleLine = true,
        shape = RoundedCornerShape(16.dp),
        visualTransformation = if (password) PasswordVisualTransformation() else VisualTransformation.None,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = MaterialTheme.colorScheme.primary,
            unfocusedBorderColor = MaterialTheme.colorScheme.outline,
            focusedLabelColor = MaterialTheme.colorScheme.primary,
            unfocusedLabelColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            cursorColor = MaterialTheme.colorScheme.primary,
            focusedTextColor = MaterialTheme.colorScheme.onSurface,
            unfocusedTextColor = MaterialTheme.colorScheme.onSurface
        )
    )
}

private fun sendOtp(
    context: Context,
    name: String,
    email: String,
    mobile: String,
    collegeName: String,
    batchYear: String,
    passingYear: String,
    state: String,
    password: String,
    onSuccess: (String) -> Unit,
    onError: (String) -> Unit
) {
    val url = "https://medigyaan.xyz/Neurons/send_otp3.php?ts=${System.currentTimeMillis()}"
    val jsonBody = JSONObject().apply {
        put("name", name)
        put("email", email)
        put("mobile_no", mobile)
        put("college_name", collegeName)
        put("batch_year", batchYear)
        put("passing_year", passingYear)
        put("state", state)
        put("password", password)
        put("repeat_password", password)
    }
    
    Log.d("REGISTER_JSON", jsonBody.toString())
    
    val request = object : JsonObjectRequest(
        Request.Method.POST, url, jsonBody,
        { response ->
            Log.d("RegisterActivity", "sendOtp Response: $response")
            if (response.optBoolean("success")) {
                onSuccess(response.optString("message", "OTP sent successfully"))
            } else {
                onError(response.optString("message", "OTP could not be sent"))
            }
        },
        { error ->
            Log.e("RegisterActivity", "sendOtp Error: ${error.message}", error)
            onError(error.message ?: "Network error")
        }
    ) {
        override fun getHeaders(): MutableMap<String, String> {
            return hashMapOf(
                "Cache-Control" to "no-cache, no-store, must-revalidate",
                "Pragma" to "no-cache",
                "Expires" to "0"
            )
        }
    }
    request.setShouldCache(false)
    Volley.newRequestQueue(context.applicationContext).add(request)
}

private fun verifyOtp(
    context: Context,
    name: String,
    email: String,
    mobile: String,
    collegeName: String,
    batchYear: String,
    passingYear: String,
    state: String,
    password: String,
    otp: String,
    referralCode: String,
    onSuccess: (Int, String, String) -> Unit,
    onError: (String) -> Unit
) {
    val url = "https://medigyaan.xyz/Neurons/verify_otp12.php?ts=${System.currentTimeMillis()}"
    val jsonBody = JSONObject().apply {
        put("name", name)
        put("email", email)
        put("mobile_no", mobile)
        put("college_name", collegeName)
        put("batch_year", batchYear)
        put("passing_year", passingYear)
        put("state", state)
        put("password", password)
        put("otp", otp)
        if (referralCode.isNotBlank()) put("referral_code", referralCode)
    }
    
    Log.d("VERIFY_JSON", jsonBody.toString())
    
    val request = object : JsonObjectRequest(
        Request.Method.POST, url, jsonBody,
        { response ->
            Log.d("RegisterActivity", "verifyOtp Response: $response")
            if (response.optBoolean("success")) {
                val userId = response.optInt("user_id", 0)
                val userName = response.optString("name", name)
                val userEmail = response.optString("email", email)
                if (userId > 0) {
                    onSuccess(userId, userName, userEmail)
                } else {
                    onError("User id missing from server response")
                }
            } else {
                onError(response.optString("message", "OTP verification failed"))
            }
        },
        { error ->
            Log.e("RegisterActivity", "verifyOtp Error: ${error.message}", error)
            onError(error.message ?: "Network error")
        }
    ) {
        override fun getHeaders(): MutableMap<String, String> {
            return hashMapOf(
                "Cache-Control" to "no-cache, no-store, must-revalidate",
                "Pragma" to "no-cache",
                "Expires" to "0"
            )
        }
    }
    request.setShouldCache(false)
    Volley.newRequestQueue(context.applicationContext).add(request)
}

private fun applyReferralCode(context: Context, userId: Int, referralCode: String, email: String) {
    if (referralCode.isBlank()) return

    val url = "https://medigyaan.xyz/Neurons/api/referral_api.php"
    val request = object : StringRequest(
        Request.Method.POST,
        url,
        { response ->
            try {
                val root = JSONObject(response)
                if (root.optString("status") == "success") {
                    context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
                        .edit()
                        .remove("pending_referral_code")
                        .apply()
                }
            } catch (_: Exception) {
            }
        },
        { error -> Log.e("RegisterActivity", "Referral apply error: ${error.message}") }
    ) {
        override fun getParams(): MutableMap<String, String> {
            return hashMapOf(
                "action" to "apply",
                "new_user_id" to userId.toString(),
                "referral_code" to referralCode,
                "email" to email
            )
        }
    }
    request.setShouldCache(false)
    Volley.newRequestQueue(context.applicationContext).add(request)
}

private fun saveUserSession(context: Context, userId: Int, name: String, email: String) {
    context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE).edit()
        .putInt("user_id", userId)
        .putString("name", name)
        .putString("email", email)
        .apply()
}

private fun syncFcmToken(context: Context, userId: Int) {
    FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
        if (task.isSuccessful) {
            val token = task.result
            val url = "https://medigyaan.xyz/Neurons/api/update_fcmv2.php"
            val request = object : StringRequest(Request.Method.POST, url,
                { response -> Log.i("RegisterActivity", "FCM Sync success: $response") },
                { error -> Log.e("RegisterActivity", "FCM Sync error: ${error.message}") }
            ) {
                override fun getParams(): MutableMap<String, String> {
                    val params = HashMap<String, String>()
                    params["user_id"] = userId.toString()
                    params["fcm_token"] = token ?: ""
                    return params
                }
            }
            Volley.newRequestQueue(context.applicationContext).add(request)
        }
    }
}
