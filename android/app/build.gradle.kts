import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// La firma de release vive fuera del repo (android/keystore.properties).
val firmaProps = Properties().apply {
    val f = rootProject.file("keystore.properties")
    if (f.exists()) f.inputStream().use { cargar -> load(cargar) }
}

android {
    namespace = "com.dancenot.sunov1"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.dancenot.sunov1"
        minSdk = 26
        targetSdk = 35
        versionCode = 10303
        versionName = "1.3.3"
    }

    signingConfigs {
        create("release") {
            if (firmaProps.getProperty("storeFile") != null) {
                storeFile = rootProject.file(firmaProps.getProperty("storeFile"))
                storePassword = firmaProps.getProperty("storePassword")
                keyAlias = firmaProps.getProperty("keyAlias")
                keyPassword = firmaProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions { jvmTarget = "17" }

    buildFeatures { compose = true }

    packaging {
        resources.excludes += setOf("META-INF/DEPENDENCIES", "META-INF/LICENSE*", "META-INF/NOTICE*")
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.10.01"))
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.ui:ui:1.7.5")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("net.jthink:jaudiotagger:2.2.5")
}
