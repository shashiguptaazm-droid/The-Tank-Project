import java.io.FileInputStream
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.google.services)
    alias(libs.plugins.ksp)
}

kotlin {
    jvmToolchain(17)
}


val keystoreProperties = Properties().apply {
    val propsFile = rootProject.file("app/keystore.properties")
    if (propsFile.exists()) {
        FileInputStream(propsFile).use { load(it) }
    }
}

android {
    namespace = "com.rankwarz.edulabsrtm"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.corp.medigyaan"
        minSdk = 26
        targetSdk = 36
        versionCode = 5
        versionName = "4.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        create("release") {
            storeFile = keystoreProperties.getProperty("storeFile")?.let { file(it) }
            storePassword = keystoreProperties.getProperty("storePassword")
            keyAlias = keystoreProperties.getProperty("keyAlias")
            keyPassword = keystoreProperties.getProperty("keyPassword")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            if (keystoreProperties.getProperty("storeFile") != null) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
            excludes += "META-INF/DEPENDENCIES"
            excludes += "META-INF/NOTICE"
            excludes += "META-INF/LICENSE"
        }
        jniLibs.useLegacyPackaging = true
    }
}

dependencies {
    implementation(libs.play.services.mlkit.text.recognition.common)
    
    implementation("com.tom-roush:pdfbox-android:2.0.27.0")
    implementation("androidx.compose.runtime:runtime-saveable")
    // --- Firebase & Identity ---
    implementation(platform("androidx.compose:compose-bom:2026.01.00"))
    implementation(platform("com.google.firebase:firebase-bom:34.0.0"))
    implementation(libs.firebase.auth)
    implementation(libs.firebase.storage)
    implementation(libs.firebase.messaging)
    implementation("com.google.firebase:firebase-database")
    implementation("com.google.firebase:firebase-firestore")
    implementation(libs.firebase.appcheck.playintegrity)
    implementation(libs.firebase.appcheck.debug)
    implementation(libs.googleid)
    implementation("com.google.android.gms:play-services-auth:21.0.0")
    implementation("com.google.android.play:integrity:1.6.0")

    // --- OCR (ML Kit text recognition) ---
    implementation("com.google.mlkit:text-recognition:16.0.1")

    // --- Networking & Utils ---
    implementation("com.android.volley:volley:1.2.1")
    // Use OkHttp 4.x to avoid the Kotlin 2.2 metadata mismatch from 5.x artifacts
    implementation(platform("com.squareup.okhttp3:okhttp-bom:4.12.0"))
    implementation("com.squareup.okhttp3:okhttp")
    implementation("com.squareup.okhttp3:logging-interceptor")
    implementation("com.squareup.retrofit2:retrofit:3.0.0")
    implementation("com.squareup.retrofit2:converter-gson:3.0.0")
    implementation("com.google.code.gson:gson:2.13.1")
    implementation("org.jsoup:jsoup:1.18.1")
    implementation("com.github.bumptech.glide:glide:4.16.0")
    ksp("com.github.bumptech.glide:compiler:4.16.0")
    implementation("io.coil-kt:coil-compose:2.7.0")

    // --- UI & Jetpack ---
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.recyclerview)
    implementation(libs.androidx.swiperefreshlayout)
    implementation(libs.androidx.gridlayout)
    implementation(libs.androidx.coordinatorlayout)
    
    // --- Compose ---
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation("androidx.compose.material:material:1.7.0")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.runtime:runtime-livedata:1.6.1")
    implementation("androidx.compose.runtime:runtime-saveable")
    implementation("androidx.compose.runtime:runtime")
    implementation("androidx.compose.ui:ui-text:1.7.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.10.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.10.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.10.0")

    // --- Room ---
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    // --- Third Party & Misc ---
    implementation("com.github.PhilJay:MPAndroidChart:3.1.0")
    implementation("com.google.zxing:core:3.5.3")
    implementation("com.github.yalantis:ucrop:2.2.8")
    implementation(libs.impress)
    implementation(libs.androidx.tools.core)
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")

    // --- Apache POI ---
    implementation("org.apache.poi:poi:5.2.5")
    implementation("org.apache.poi:poi-ooxml:5.2.5") {
        exclude(group = "org.apache.poi", module = "poi-ooxml-lite")
    }
    implementation("org.apache.commons:commons-compress:1.26.1")
    implementation("commons-io:commons-io:2.16.1")
    implementation("org.apache.xmlbeans:xmlbeans:5.2.0")
    implementation("com.fasterxml.woodstox:woodstox-core:6.2.7")
    implementation("org.apache.poi:poi-ooxml-full:5.2.5") {
        exclude(group = "org.apache.poi", module = "poi-ooxml-lite")
    }

    // --- Video Player (ExoPlayer) ---
    implementation("com.google.android.exoplayer:exoplayer:2.19.1")

    // --- LiveKit WebRTC Audio/Video Calls ---
    implementation("io.livekit:livekit-android:2.16.0")

    // --- Cashfree Payment Gateway ---
    implementation("com.cashfree.pg:api:2.6.0")

    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
