import requests
import os
import json
import openai
import time
import re  
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import whisper
import requests


BITRIX24_WEBHOOK = os.getenv("BITRIX24_WEBHOOK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")


print(f"🔑 OpenAI API Key: {openai.api_key}")

# ✅ Bitrix API Configuration
BITRIX_WEBHOOK_BASE = ""
MEDIA_DIR = "media"

# ✅ Ensure media directory exists
os.makedirs(MEDIA_DIR, exist_ok=True)



@csrf_exempt
def bitrix_webhook(request):
    """Handles incoming webhooks from Bitrix24."""
    if request.method == "POST":
        try:
            print("📩 Received Webhook Request")
            data = request.POST.dict()
            print("📩 Parsed Data:", json.dumps(data, indent=2))

            comment_id = data.get("data[FIELDS][ID]")
            if not comment_id:
                print("❌ Comment ID not found!")
                return JsonResponse({"error": "Comment ID not found"}, status=400)

            print(f"🆔 Extracted Comment ID: {comment_id}")

            comment_data = get_comment_details(comment_id)
            if not comment_data:
                return JsonResponse({"error": "Failed to retrieve comment details"}, status=400)

            print(f"📄 Retrieved Comment Data: {json.dumps(comment_data, indent=2)}")

            lead_id = comment_data.get("ENTITY_ID")
            if not lead_id:
                print("❌ Lead ID not found!")
                return JsonResponse({"error": "Lead ID not found"}, status=400)

            print(f"🔗 Associated Lead ID: {lead_id}")

            file_id = extract_file_id(comment_data)
            if not file_id:
                print("⚠️ No file found in the comment.")
                return JsonResponse({"message": "No file attached. Comment processed."}, status=200)

            print(f"📥 Extracted File ID: {file_id}")

            audio_path = download_audio(file_id)
            if not audio_path or not os.path.exists(audio_path):
                return JsonResponse({"error": "Failed to download audio file"}, status=400)

            print(f"🎵 Audio File Saved At: {audio_path}")

            transcription = transcribe_audio(audio_path)
            if not transcription:
                return JsonResponse({"error": "Failed to transcribe audio"}, status=400)

            print(f"📝 Transcription: {transcription}")

            feedback = analyze_feedback(transcription)
            print(f"✅ Generated Feedback: {feedback}")

            sentiment = analyze_sentiment(transcription)
            print(f"✅ Generated Sentiment : {sentiment}")

            post_feedback_to_bitrix(lead_id, transcription, feedback, sentiment)

            return JsonResponse({"message": "Processed successfully"}, status=200)

        except Exception as e:
            print(f"❌ Exception: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


def get_comment_details(comment_id):
    """Fetches comment details from Bitrix24."""
    url = f"{BITRIX_WEBHOOK_BASE}crm.timeline.comment.get"
    print(f"🔍 Fetching Comment Data from Bitrix24 (ID: {comment_id})")
    
    response = requests.get(url, params={"id": comment_id})
    if response.status_code == 200:
        print("✅ Successfully retrieved comment data")
        return response.json().get("result", {})

    print(f"❌ Failed to fetch comment details: {response.text}")
    return None


def extract_file_id(comment_data):
    """Extracts file ID from comment data."""
    files = comment_data.get("FILES")
    if not files:
        print("⚠️ No files found in comment data.")
        return None

    file_info = list(files.values())[0]  # Get first file
    file_id = file_info.get("id")
    print(f"📁 Extracted File ID: {file_id}")
    return file_id


def get_authenticated_file_url(file_id):
    """Fetches an authenticated download URL from Bitrix24."""
    url = f"{BITRIX_WEBHOOK_BASE}disk.file.get"
    print(f"🔗 Fetching Download URL for File ID: {file_id}")

    response = requests.get(url, params={"id": file_id})
    if response.status_code == 200:
        download_url = response.json().get("result", {}).get("DOWNLOAD_URL")
        print(f"✅ Retrieved Download URL: {download_url}")
        return download_url

    print(f"❌ Failed to get authenticated file URL: {response.text}")
    return None


def download_audio(file_id):
    """Downloads the MP3 file using the authenticated Bitrix24 link."""
    file_url = get_authenticated_file_url(file_id)
    if not file_url:
        print("❌ Could not retrieve authenticated URL. Aborting download.")
        return None

    print(f"📥 Downloading from URL: {file_url}")

    try:
        response = requests.get(file_url, stream=True, allow_redirects=True)

        # ✅ Debugging: Print response headers
        print("📜 Response Headers:", response.headers)

        # Extract filename from headers safely
        content_disposition = response.headers.get("Content-Disposition", "")
        filename = "unknown.mp3"  # Default if filename extraction fails

        if content_disposition:
            match = re.search(r'filename\*=utf-8\'\'([\w\-.%+]+)', content_disposition)
            if match:
                filename = match.group(1)
            else:
                match = re.search(r'filename="([^"]+)"', content_disposition)
                if match:
                    filename = match.group(1)

        # ✅ Sanitize filename to avoid special character issues
        filename = re.sub(r'[\\/*?:"<>|;]', '_', filename)  # Replace special characters with '_'

        # ✅ Ensure file has an .mp3 extension
        if not filename.endswith(".mp3"):
            filename += ".mp3"

        # ✅ Add timestamp to avoid duplicates
        unique_filename = f"{int(time.time())}_{filename}"
        file_path = os.path.join(MEDIA_DIR, unique_filename)

        print(f"📂 Saving File As: {file_path}")

        # ✅ Ensure media directory exists
        if not os.path.exists(MEDIA_DIR):
            os.makedirs(MEDIA_DIR)

        # ✅ Save the file
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)

        print(f"✅ File successfully downloaded: {file_path}")

        # ✅ Validate file size (avoid empty/corrupt downloads)
        if os.path.getsize(file_path) < 1024:  # Minimum valid file size
            print("❌ Downloaded file is too small to be valid.")
            os.remove(file_path)
            return None

        return file_path

    except Exception as e:
        print(f"❌ Exception while downloading: {e}")
        return None

# ✅ Load API key from settings


model = whisper.load_model("base")
print("Whisper loaded successfully!")


def transcribe_audio(audio_path):
    """Transcribes the MP3 file using OpenAI Whisper locally (free version)."""
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return None

    try:
        print(f"📢 Transcribing {audio_path} locally using Whisper...")
        model = whisper.load_model("base")  # Choose from 'tiny', 'base', 'small', 'medium', 'large'
        result = model.transcribe(audio_path)
        transcription = result["text"]
        print(f"✅ Transcription Success: {transcription}")

        return transcription

    except Exception as e:
        print(f"❌ Unexpected Transcription Error: {e}")
        return None
    

    



# MODEL = "mistralai/Mistral-7B-Instruct-v0.1"
# HF_API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

# def analyze_feedback(transcription):
#     """Generates sentiment analysis and feedback in English using Hugging Face API with retries."""
#     if not transcription:
#         print("⚠️ Empty transcription provided. Skipping analysis.")
#         return "Error: No transcription available."

#     prompt = f"Analyze the following conversation and provide feedback in English:\n\n{transcription}"
#     headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
#     payload = {"inputs": prompt}

#     # Retry logic
#     max_retries = 5
#     for attempt in range(max_retries):
#         try:
#             print(f"📢 Sending transcription to Hugging Face API... Attempt {attempt + 1}/{max_retries}")
#             response = requests.post(HF_API_URL, headers=headers, json=payload)

#             if response.status_code == 200:
#                 feedback = response.json()[0].get("generated_text", "No feedback generated.")
#                 print(f"✅ Feedback Generated: {feedback}")
#                 return feedback
#             elif response.status_code == 503:  # Service Unavailable
#                 wait_time = 2 ** attempt  # Exponential backoff (2s, 4s, 8s, 16s)
#                 print(f"❌ API is down. Retrying in {wait_time} seconds...")
#                 time.sleep(wait_time)
#             else:
#                 print(f"❌ Hugging Face API Error: {response.status_code} - {response.text}")
#                 break  # Exit loop on non-retryable errors

#         except requests.RequestException as e:
#             print(f"❌ Hugging Face API Request Error: {e}")
#             break

#     return "Error generating feedback."

    
# from transformers import pipeline

# # Load sentiment analysis model
# sentiment_analyzer = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")

# def analyze_sentiment(transcription):
#     """Performs sentiment analysis on the conversation."""
#     if not transcription:
#         return "Error: No transcription available."

#     try:
#         print("📢 Performing sentiment analysis...")
#         sentiment_result = sentiment_analyzer(transcription)
#         sentiment = sentiment_result[0]["label"]  # Example: "POSITIVE"
#         print(f"✅ Sentiment Detected: {sentiment}")
#         return sentiment
#     except Exception as e:
#         print(f"❌ Sentiment Analysis Error: {e}")
#         return "Error analyzing sentiment."

# def process_transcription(transcription):
#     """Processes a call transcription to generate feedback and sentiment."""
#     feedback = analyze_feedback(transcription)
#     sentiment = analyze_sentiment(transcription)

#     return {"feedback": feedback, "sentiment": sentiment}



# openai code


def analyze_feedback(transcription):
    """Generates sentiment analysis and feedback in English using OpenAI GPT with retries."""
    if not transcription:
        print("⚠️ Empty transcription provided. Skipping analysis.")
        return "Error: No transcription available."

    prompt = f"Analyze and provide brutal in details suggestions line by line for the sales executive including service knowledge and overall sales approach:\n\n{transcription}"

    # Retry logic
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"📢 Sending transcription to OpenAI GPT... Attempt {attempt + 1}/{max_retries}")
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "You are an assistant providing conversation feedback."},
                          {"role": "user", "content": prompt}],
                temperature=0.7
            )

            feedback = response.choices[0].message["content"]
            print(f"✅ Feedback Generated: {feedback}")
            return feedback
        except openai.error.RateLimitError:
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"❌ OpenAI API rate limit reached. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except openai.error.OpenAIError as e:
            print(f"❌ OpenAI API Error: {e}")
            break  # Exit loop on non-retryable errors

    return "Error generating feedback."

def analyze_sentiment(transcription):
    """Performs sentiment analysis using OpenAI GPT."""
    if not transcription:
        return "Error: No transcription available."

    prompt = f"Analyze the sentiment of the following conversation (Positive, Neutral, or Negative):\n\n{transcription}"

    try:
        print("📢 Performing sentiment analysis with OpenAI GPT...")
        response = openai.ChatCompletion.create(
           model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are an assistant performing sentiment analysis."},
                      {"role": "user", "content": prompt}],
            temperature=0.0
        )

        sentiment = response.choices[0].message["content"].strip()  # Example: "Positive"
        print(f"✅ Sentiment Detected: {sentiment}")
        return sentiment
    except openai.error.OpenAIError as e:
        print(f"❌ Sentiment Analysis Error: {e}")
        return "Error analyzing sentiment."

def process_transcription(transcription):
    """Processes a call transcription to generate feedback and sentiment."""
    feedback = analyze_feedback(transcription)
    sentiment = analyze_sentiment(transcription)

    return {"feedback": feedback, "sentiment": sentiment}

def post_feedback_to_bitrix(lead_id, transcription, feedback, sentiment):
    """Posts transcription as a comment and feedback+sentiment as another comment in Bitrix24."""
    if not lead_id:
        print("❌ Lead ID is missing. Cannot post feedback.")
        return

    if not transcription:
        print("⚠️ No valid transcription provided. Skipping Bitrix24 update.")
        return

    # First Comment: Transcription
    transcription_comment = f"📝 **Call Transcription:**\n{transcription}"
    post_comment_to_bitrix(lead_id, transcription_comment)

    # Second Comment: Feedback + Sentiment
    if feedback and not feedback.startswith("Error"):
        feedback_sentiment_comment = f"📢 **AI Feedback:** {feedback}\n\n😊 **Sentiment:** {sentiment}"
        post_comment_to_bitrix(lead_id, feedback_sentiment_comment)
    else:
        print("⚠️ No valid feedback generated. Skipping feedback & sentiment update.")

def post_comment_to_bitrix(lead_id, comment_text):
    """Helper function to post a comment to a lead in Bitrix24."""
    payload = {
        "fields": {"ENTITY_ID": lead_id, "ENTITY_TYPE": "lead", "COMMENT": comment_text}
    }
    url = f"{BITRIX_WEBHOOK_BASE}crm.timeline.comment.add.json"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"📢 Posting comment to Bitrix24 for Lead ID {lead_id}... Attempt {attempt + 1}/{max_retries}")
            response = requests.post(url, json=payload)

            if response.status_code == 200:
                print("✅ Successfully posted comment to Bitrix24")
                return
            else:
                print(f"❌ Failed to post: {response.status_code} - {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        except requests.RequestException as e:
            print(f"❌ Bitrix24 API Request Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    print("❌ Giving up on posting to Bitrix24 after multiple failures.")
