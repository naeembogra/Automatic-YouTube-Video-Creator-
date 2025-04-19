import os
import requests
from dotenv import load_dotenv
from openai import OpenAI
from moviepy import ImageClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips

# পরিবেশ ভেরিয়েবল লোড করা
load_dotenv()

# API কীগুলো লোড করা
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ১. NewsAPI থেকে ট্রেন্ডিং টপিক সংগ্রহ
def get_trending_topic():
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    response = requests.get(url).json()
    return response["articles"][0]["title"]

# ২. OpenAI দিয়ে স্ক্রিপ্ট তৈরি (ফলব্যাক সহ)
def generate_script(topic):
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Write a short script for a YouTube video about: {topic}"}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI ব্যর্থ হয়েছে: {e}")
        return f"এটি {topic} নিয়ে একটি সংক্ষিপ্ত ভিডিও। আরো জানতে আমাদের চ্যানেলে থাকুন।"

# ৩. Unsplash থেকে একাধিক ছবি ডাউনলোড
def download_images(query, count=3):
    url = f"https://api.unsplash.com/search/photos?query={query}&per_page={count}&client_id={UNSPLASH_API_KEY}"
    response = requests.get(url).json()
    image_urls = [result["urls"]["full"] for result in response["results"][:count]]
    image_files = []
    for i, image_url in enumerate(image_urls):
        image_data = requests.get(image_url).content
        filename = f"image_{i}.jpg"
        with open(filename, "wb") as f:
            f.write(image_data)
        image_files.append(filename)
    return image_files

# ৪. ElevenLabs দিয়ে প্রাকৃতিক ভয়েসওভার তৈরি
def generate_voiceover(script):
    url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {
        "text": script,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.2
        }
    }
    response = requests.post(url, json=data, headers=headers)
    with open("voiceover.mp3", "wb") as f:
        f.write(response.content)

# ৫. Pixabay থেকে ব্যাকগ্রাউন্ড মিউজিক ডাউনলোড (ফলব্যাক সহ)
def download_background_music():
    try:
        url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q=music&audio_duration=short"
        response = requests.get(url).json()
        music_url = response["hits"][0]["previewURL"]
        music_data = requests.get(music_url).content
        with open("background_music.mp3", "wb") as f:
            f.write(music_data)
        # ফাইলটি অডিও কিনা চেক করা
        bg_music = AudioFileClip("background_music.mp3")
        return True
    except Exception as e:
        print(f"Pixabay থেকে অডিও ডাউনলোড ব্যর্থ: {e}")
        # ফলব্যাক: একটি ডিফল্ট অডিও ফাইল ব্যবহার (আপনার পিসিতে থাকা একটি MP3 ফাইল)
        default_music = "default_music.mp3"  # আপনার পিসিতে একটি MP3 ফাইলের পাথ দিন
        if os.path.exists(default_music):
            return True
        else:
            print("ডিফল্ট মিউজিক ফাইল পাওয়া যায়নি। ব্যাকগ্রাউন্ড মিউজিক ছাড়াই ভিডিও তৈরি হবে।")
            return False

# ৬. ভিডিও তৈরি
def create_video():
    topic = get_trending_topic()
    script = generate_script(topic)
    image_files = download_images(topic, count=3)
    generate_voiceover(script)
    has_music = download_background_music()

    # ভয়েসওভার এবং ব্যাকগ্রাউন্ড মিউজিক মিক্স
    voiceover = AudioFileClip("voiceover.mp3")
    if has_music:
        try:
            bg_music = AudioFileClip("background_music.mp3").volumex(0.3)
            if bg_music.duration < voiceover.duration:
                bg_music = bg_music.fx(vfx.audio_loop, duration=voiceover.duration)
            else:
                bg_music = bg_music.subclip(0, voiceover.duration)
            final_audio = CompositeAudioClip([voiceover, bg_music])
        except Exception as e:
            print(f"ব্যাকগ্রাউন্ড মিউজিক মিক্স করতে ব্যর্থ: {e}")
            final_audio = voiceover
    else:
        final_audio = voiceover

    # একাধিক ছবি দিয়ে ভিডিও ক্লিপ তৈরি
    duration_per_image = voiceover.duration / len(image_files)
    clips = []
    for image_file in image_files:
        clip = ImageClip(image_file, duration=duration_per_image)
        clip = clip.fx(vfx.fadein, 1).fx(vfx.fadeout, 1)
        clips.append(clip)

    # ভিডিও কনক্যাটেনেট করা
    final_video = concatenate_videoclips(clips, method="compose")
    final_video.audio = final_audio

    # ফাইনাল ভিডিও সেভ
    final_video.write_videofile("output_video.mp4", fps=24)

if __name__ == "__main__":
    create_video()
