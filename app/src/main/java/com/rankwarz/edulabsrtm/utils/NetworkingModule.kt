package com.rankwarz.edulabsrtm.utils

import android.content.Context
import com.android.volley.RequestQueue
import com.android.volley.toolbox.Volley
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

object NetworkingModule {
    private var requestQueue: RequestQueue? = null
    private var okHttpClient: OkHttpClient? = null

    fun getRequestQueue(context: Context): RequestQueue {
        if (requestQueue == null) {
            requestQueue = Volley.newRequestQueue(context.applicationContext)
        }
        return requestQueue!!
    }

    fun getOkHttpClient(): OkHttpClient {
        if (okHttpClient == null) {
            okHttpClient = OkHttpClient.Builder()
                .connectTimeout(60, TimeUnit.SECONDS)
                .readTimeout(120, TimeUnit.SECONDS)
                .writeTimeout(120, TimeUnit.SECONDS)
                .build()
        }
        return okHttpClient!!
    }
}
