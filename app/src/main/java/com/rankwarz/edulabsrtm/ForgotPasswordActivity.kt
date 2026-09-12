package com.rankwarz.edulabsrtm

import android.content.Context
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.Volley
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import org.json.JSONObject

class ForgotPasswordActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EduLabsRTMThemeFromPreferences {
                Surface {
                    ForgotPasswordScreen(
                        activity = this
                    )
                }
            }
        }
    }
}

private enum class ForgotStep {
    MOBILE, OTP, PASSWORD
}

@Composable
fun ForgotPasswordScreen(
    activity: ComponentActivity
) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    var step by remember { mutableStateOf(ForgotStep.MOBILE) }
    var mobile by remember { mutableStateOf("") }
    var otp by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }

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
                    Text(
                        text = "MediGyaan",
                        color = Color.White,
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Black,
                        letterSpacing = 0.5.sp
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        text = "Reset your password safely",
                        color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f),
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
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = BorderStroke(1.dp, formBorder),
                elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp)
                ) {
                    Text(
                        text = when (step) {
                            ForgotStep.MOBILE -> "Forgot Password"
                            ForgotStep.OTP -> "Verify OTP"
                            ForgotStep.PASSWORD -> "Set New Password"
                        },
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Black
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = when (step) {
                            ForgotStep.MOBILE -> "Enter your registered mobile number"
                            ForgotStep.OTP -> "Enter the OTP sent to your mobile number"
                            ForgotStep.PASSWORD -> "Create a new password for your account"
                        },
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

                    when (step) {
                        ForgotStep.MOBILE -> {
                            RegisterTextField(
                                value = mobile,
                                onValueChange = {
                                    val digits = it.filter { c -> c.isDigit() }
                                    mobile = if (digits.length <= 10) digits else digits.take(10)
                                },
                                label = "Registered Mobile Number",
                                keyboardType = KeyboardType.Number
                            )

                            Spacer(modifier = Modifier.height(24.dp))

                            Button(
                                onClick = {
                                    message = ""

                                    if (mobile.length != 10 || !mobile.matches(Regex("^[6-9]\\d{9}$"))) {
                                        showToast("Enter valid 10-digit Indian mobile number")
                                        return@Button
                                    }

                                    loading = true
                                    sendForgotOtp(
                                        context = context,
                                        mobile = mobile.trim(),
                                        onSuccess = { serverMsg ->
                                            loading = false
                                            message = serverMsg.ifBlank { "OTP sent successfully" }
                                            step = ForgotStep.OTP
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
                        }

                        ForgotStep.OTP -> {
                            Text(
                                text = mobile,
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
                                    verifyForgotOtp(
                                        context = context,
                                        mobile = mobile.trim(),
                                        otp = otp.trim(),
                                        onSuccess = { serverMsg ->
                                            loading = false
                                            message = serverMsg.ifBlank { "OTP verified successfully" }
                                            step = ForgotStep.PASSWORD
                                            showToast("OTP verified")
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
                                    step = ForgotStep.MOBILE
                                    message = ""
                                },
                                modifier = Modifier.align(Alignment.CenterHorizontally)
                            ) {
                                Text(
                                    text = "Change mobile number",
                                    color = MaterialTheme.colorScheme.primary,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }

                        ForgotStep.PASSWORD -> {
                            Text(
                                text = mobile,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                                fontSize = 13.sp
                            )

                            Spacer(modifier = Modifier.height(16.dp))

                            RegisterTextField(
                                value = password,
                                onValueChange = { password = it },
                                label = "New Password",
                                keyboardType = KeyboardType.Password,
                                password = true
                            )

                            Spacer(modifier = Modifier.height(16.dp))

                            RegisterTextField(
                                value = confirmPassword,
                                onValueChange = { confirmPassword = it },
                                label = "Confirm Password",
                                keyboardType = KeyboardType.Password,
                                password = true
                            )

                            Spacer(modifier = Modifier.height(24.dp))

                            Button(
                                onClick = {
                                    message = ""

                                    if (password.length < 6) {
                                        showToast("Password must be at least 6 characters")
                                        return@Button
                                    }

                                    if (password != confirmPassword) {
                                        showToast("Passwords do not match")
                                        return@Button
                                    }

                                    loading = true
                                    resetPassword(
                                        context = context,
                                        mobile = mobile.trim(),
                                        password = password,
                                        onSuccess = { serverMsg ->
                                            loading = false
                                            message = serverMsg.ifBlank { "Password updated successfully" }
                                            Toast.makeText(
                                                context,
                                                "Password updated successfully",
                                                Toast.LENGTH_LONG
                                            ).show()
                                            activity.finish()
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
                                    text = if (loading) "Please Wait..." else "Update Password",
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            TextButton(
                                onClick = {
                                    loading = false
                                    password = ""
                                    confirmPassword = ""
                                    step = ForgotStep.OTP
                                    message = ""
                                },
                                modifier = Modifier.align(Alignment.CenterHorizontally)
                            ) {
                                Text(
                                    text = "Back to OTP",
                                    color = MaterialTheme.colorScheme.primary,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
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
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium
                        )

                        HorizontalDivider(
                            modifier = Modifier.weight(1f),
                            color = MaterialTheme.colorScheme.outline
                        )
                    }

                    Spacer(modifier = Modifier.height(18.dp))

                    TextButton(
                        onClick = {
                            activity.finish()
                        },
                        modifier = Modifier.align(Alignment.CenterHorizontally)
                    ) {
                        Text(
                            text = "Back to Login",
                            color = MaterialTheme.colorScheme.primary,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
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

private fun sendForgotOtp(
    context: Context,
    mobile: String,
    onSuccess: (String) -> Unit,
    onError: (String) -> Unit
) {
    val url = "https://medigyaan.xyz/Neurons/forgot_password_send_otp.php?ts=${System.currentTimeMillis()}"
    val jsonBody = JSONObject().apply {
        put("mobile_no", mobile)
    }

    val request = object : JsonObjectRequest(
        Request.Method.POST, url, jsonBody,
        { response ->
            Log.d("ForgotPassword", "sendForgotOtp response: $response")
            if (response.optBoolean("success")) {
                onSuccess(response.optString("message", "OTP sent successfully"))
            } else {
                onError(response.optString("message", "OTP could not be sent"))
            }
        },
        { error ->
            Log.e("ForgotPassword", "sendForgotOtp error: ${error.message}", error)
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

private fun verifyForgotOtp(
    context: Context,
    mobile: String,
    otp: String,
    onSuccess: (String) -> Unit,
    onError: (String) -> Unit
) {
    val url = "https://medigyaan.xyz/Neurons/forgot_password_verify_otp.php?ts=${System.currentTimeMillis()}"
    val jsonBody = JSONObject().apply {
        put("mobile_no", mobile)
        put("otp", otp)
    }

    val request = object : JsonObjectRequest(
        Request.Method.POST, url, jsonBody,
        { response ->
            Log.d("ForgotPassword", "verifyForgotOtp response: $response")
            if (response.optBoolean("success")) {
                onSuccess(response.optString("message", "OTP verified successfully"))
            } else {
                onError(response.optString("message", "OTP verification failed"))
            }
        },
        { error ->
            Log.e("ForgotPassword", "verifyForgotOtp error: ${error.message}", error)
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

private fun resetPassword(
    context: Context,
    mobile: String,
    password: String,
    onSuccess: (String) -> Unit,
    onError: (String) -> Unit
) {
    val url = "https://medigyaan.xyz/Neurons/reset_password_app.php?ts=${System.currentTimeMillis()}"
    val jsonBody = JSONObject().apply {
        put("mobile_no", mobile)
        put("password", password)
    }

    val request = object : JsonObjectRequest(
        Request.Method.POST, url, jsonBody,
        { response ->
            Log.d("ForgotPassword", "resetPassword response: $response")
            if (response.optBoolean("success")) {
                onSuccess(response.optString("message", "Password updated successfully"))
            } else {
                onError(response.optString("message", "Password update failed"))
            }
        },
        { error ->
            Log.e("ForgotPassword", "resetPassword error: ${error.message}", error)
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