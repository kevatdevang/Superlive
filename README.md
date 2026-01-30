# Superlive Project

This repository hosts a hybrid project containing a Python-based asynchronous API server and an Android application built with Jetpack Compose.

## 📂 Project Structure

The project has a unique structure where the `app/` directory serves dual purposes:
1.   **Python Package**: Contains the source code for the Quart-based API server.
2.  **Android Module**: Contains the source code and build configuration for the Android application.

```
Superlive/
├── app/
│   ├── core/              # Python Core logic (Config, Client, Device, Logger)
│   ├── modules/           # Python API Modules (User, Gift, Tempmail)
│   ├── src/               # Android Source Code (Kotlin/Java)
│   ├── build.gradle.kts   # Android Build Configuration
│   └── __init__.py        # Python Package Marker
├── run.py                 # Python Server Entry Point
├── requirements.txt       # Python Dependencies
├── gradlew / gradlew.bat  # Gradle Wrapper scripts
└── build.gradle.kts       # Root Gradle Configuration
```

## 🐍 Python Backend

The backend is an asynchronous web server built using **Quart**. It appears to be designed for automating or interacting with the Superlive platform, featuring modules for user management, gifting, and temporary email handling.

### Features
- **Async Framework**: Built on Quart and Hypercorn.
- **Modules**:
    - **User**: User management endpoints.
    - **Gift**: Handling gift interactions.
    - **Tempmail**: Integration for temporary email services.
- **Core Utilities**: Includes device fingerprinting simulation (`device.py`) and a task scheduler (`scheduler.py`).

### Setup & Run

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Server**:
    ```bash
    python run.py
    ```
    The server will start on `http://0.0.0.0:5000` (or the port specified in `PORT` env var).

## 📱 Android Application

The Android application is a modern native app built using **Kotlin** and **Jetpack Compose**.

### Tech Stack
- **Language**: Kotlin
- **UI Framework**: Jetpack Compose (Material3)
- **Minimum SDK**: 24
- **Target SDK**: 36

### Build Instructions

You can build the app using the included Gradle wrapper or open the project in Android Studio.

**Build via Command Line**:
```bash
# Windows
.\gradlew.bat assembleDebug

# Linux/Mac
./gradlew assembleDebug
```

## ⚙️ Configuration

- **Python**: Configuration is likely handled in `app/core/config.py` and environment variables (.env via `python-dotenv`).
- **Android**: Configuration is standard in `app/build.gradle.kts`.
