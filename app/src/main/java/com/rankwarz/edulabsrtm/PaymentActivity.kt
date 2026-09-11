package com.rankwarz.edulabsrtm

import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.cashfree.pg.api.CFPaymentGatewayService
import com.cashfree.pg.core.api.CFSession
import com.cashfree.pg.core.api.callback.CFCheckoutResponseCallback
import com.cashfree.pg.core.api.exception.CFException
import com.cashfree.pg.core.api.utils.CFErrorResponse
import com.cashfree.pg.core.api.webcheckout.CFWebCheckoutPayment
import com.cashfree.pg.core.api.webcheckout.CFWebCheckoutTheme

class PaymentActivity : AppCompatActivity(), CFCheckoutResponseCallback {

    private val TAG = "CASHFREE_PAYMENT"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_payment)

        // Initialize Cashfree SDK
        CFPaymentGatewayService.initialize(this)

        try {
            CFPaymentGatewayService.getInstance().setCheckoutCallback(this)
        } catch (e: CFException) {
            e.printStackTrace()
        }

        val orderId = intent.getStringExtra("order_id") ?: ""
        val paymentSessionId = intent.getStringExtra("payment_session_id") ?: ""
        val environment = intent.getStringExtra("environment") ?: "SANDBOX"

        if (orderId.isEmpty() || paymentSessionId.isEmpty()) {
            Toast.makeText(this, "Invalid payment session", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        startPayment(orderId, paymentSessionId, environment)
    }

    private fun startPayment(orderId: String, paymentSessionId: String, environment: String) {
        val cfEnvironment = if (environment == "PRODUCTION") {
            CFSession.Environment.PRODUCTION
        } else {
            CFSession.Environment.SANDBOX
        }

        try {
            val session = CFSession.CFSessionBuilder()
                .setEnvironment(cfEnvironment)
                .setOrderId(orderId)
                .setPaymentSessionID(paymentSessionId)
                .build()

            val theme = CFWebCheckoutTheme.CFWebCheckoutThemeBuilder()
                .setNavigationBarBackgroundColor("#007AFF")
                .setNavigationBarTextColor("#FFFFFF")
                .build()

            val payment = CFWebCheckoutPayment.CFWebCheckoutPaymentBuilder()
                .setSession(session)
                .setCFWebCheckoutUITheme(theme)
                .build()

            CFPaymentGatewayService.getInstance().doPayment(this, payment)
        } catch (e: CFException) {
            e.printStackTrace()
        }
    }

    override fun onPaymentVerify(orderId: String?) {
        Log.d(TAG, "Payment Verify: $orderId")
        Toast.makeText(this, "Payment Successful!", Toast.LENGTH_SHORT).show()
        setResult(RESULT_OK)
        finish()
    }

    override fun onPaymentFailure(cfErrorResponse: CFErrorResponse?, orderId: String?) {
        Log.e(TAG, "Payment Failure: ${cfErrorResponse?.message} for order $orderId")
        Toast.makeText(this, "Payment Failed: ${cfErrorResponse?.message}", Toast.LENGTH_LONG).show()
        setResult(RESULT_CANCELED)
        finish()
    }
}
