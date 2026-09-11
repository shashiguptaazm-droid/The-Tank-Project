package com.rankwarz.edulabsrtm

import android.app.Application
import com.google.firebase.FirebaseApp
import com.google.firebase.appcheck.FirebaseAppCheck
import com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory
import com.google.firebase.appcheck.playintegrity.PlayIntegrityAppCheckProviderFactory
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.FirebaseFirestoreSettings
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.rankwarz.edulabsrtm.model.ModelRotator

class EduLabsApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        instance = this
        ModelRotator.init(this)
        applySavedAppTheme(this)
        
        // Initialize PDFBox for Android
        PDFBoxResourceLoader.init(this)
        
        FirebaseApp.initializeApp(this)
        FirebaseFirestore.getInstance().firestoreSettings = FirebaseFirestoreSettings.Builder()
            .setPersistenceEnabled(false)
            .build()
        
        val firebaseAppCheck = FirebaseAppCheck.getInstance()
        
        // If you are running on an emulator or debug device, use the Debug provider.
        // Otherwise, use Play Integrity.
        if (BuildConfig.DEBUG) {
            firebaseAppCheck.installAppCheckProviderFactory(
                DebugAppCheckProviderFactory.getInstance()
            )
        } else {
            firebaseAppCheck.installAppCheckProviderFactory(
                PlayIntegrityAppCheckProviderFactory.getInstance()
            )
        }
    }

    companion object {
        lateinit var instance: EduLabsApplication
            private set
    }
}
