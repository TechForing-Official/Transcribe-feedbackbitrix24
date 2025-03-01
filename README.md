<!-- Transcribe-feedbackbitrix24 -->
<h1 align="center">🎤 Transcribe-feedbackbitrix24</h1>
<p align="center">
  <b>Bitrix24 Audio Transcription and Feedback System</b>
</p>

---

## 📌 Description
This project processes audio comments from Bitrix24 leads, transcribes them, performs sentiment analysis, and generates actionable feedback using OpenAI GPT and Whisper. The results are then posted back to Bitrix24.

## 🚀 Features
✅ **Webhook Integration**: Handles incoming webhooks from Bitrix24.<br>
✅ **Audio Download**: Retrieves audio files attached to comments in Bitrix24.<br>
✅ **Transcription**: Converts audio to text using Whisper.<br>
✅ **Analysis**: Generates feedback and sentiment analysis using OpenAI GPT.<br>
✅ **Update Bitrix24**: Posts transcription, feedback, and sentiment back to Bitrix24 leads.<br>

## 📋 Prerequisites
- 🐍 **Python**: Ensure Python 3.8+ is installed.
- 📦 **Dependencies**: Install required packages using:
  ```bash
  pip install -r requirements.txt
  ```
- 🔑 **Environment Variables**: Set up the following:
  - `OPENAI_API_KEY`: Your OpenAI API key.
  - `BITRIX_WEBHOOK_BASE`: Base URL for your Bitrix24 webhook.
- 🌍 **Ngrok**: Install and configure Ngrok for tunneling to localhost.

## 🛠️ Installation
```bash
git clone <repository_url>
cd <repository_folder>
pip install -r requirements.txt
mkdir -p media
```

## 🚀 Running the Project
### Step 1: Start the Django Server
```bash
python manage.py runserver
```
### Step 2: Start Ngrok
```bash
ngrok http 8000
```
Copy the forwarding URL (e.g., `https://<ngrok_subdomain>.ngrok.io`) and set it as the webhook URL in Bitrix24.

### Step 3: Configure Bitrix24 Webhook
- Navigate to your Bitrix24 account and set up a webhook.
- Use the Ngrok URL as the endpoint for the webhook.

## ⚡ Workflow
1️⃣ **Trigger**: A comment is added to a Bitrix24 lead, triggering the webhook.<br>
2️⃣ **Audio Processing**:
   - The project fetches the comment and downloads the attached audio.
   - Transcription is performed using Whisper.<br>
3️⃣ **Analysis**:
   - The transcription is analyzed using OpenAI GPT to provide feedback and sentiment.<br>
4️⃣ **Update Bitrix24**:
   - Transcription, feedback, and sentiment are posted back to the lead in Bitrix24.

## 📂 File Structure
```
app_name/views.py    # Webhook logic and helper functions
media/               # Directory for storing downloaded audio files
requirements.txt     # Python dependencies
```

## 🛠️ Troubleshooting
❌ **Ngrok Tunnel Not Working?** Ensure Ngrok is running and the correct forwarding URL is used in Bitrix24.<br>
❌ **Audio File Not Downloading?** Check if the file ID is correctly extracted from Bitrix24 comments.<br>
❌ **API Rate Limit?** The OpenAI API has a rate limit. Retries are implemented with exponential backoff.<br>

## 🔒 Notes
- Ensure sensitive keys like `OPENAI_API_KEY` are not hardcoded. Use environment variables.
- Test the webhook with sample data from Bitrix24 to ensure proper functionality.
