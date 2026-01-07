import streamlit as st
import whisper
import os
import yt_dlp
import ffmpeg
from datetime import timedelta
from deep_translator import GoogleTranslator
import arabic_reshaper
from bidi.algorithm import get_display

st.set_page_config(page_title="المترجم الذكي", layout="centered")
st.title("🎬 استوديو الترجمة (Final)")

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    model_type = st.selectbox("دقة الذكاء الاصطناعي:", ["base", "small"])
    
    lang_options = {"العربية": "ar", "الإنجليزية": "en", "الفرنسية": "fr", "الأسبانية": "es"}
    selected_lang_name = st.selectbox("اللغة المستهدفة:", list(lang_options.keys()))
    target_lang_code = lang_options[selected_lang_name]

# --- دوال المعالجة ---

def download_video_android_mode(url):
    # إعدادات خاصة لمحاكاة تطبيق أندرويد لتجاوز الحظر
    ydl_opts = {
        'format': 'mp4/best',
        'outtmpl': 'input_video.mp4',
        'quiet': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        # الخدعة الكبرى: استخدام واجهة أندرويد بدلاً من الويب
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
        }
    }
    
    if os.path.exists("input_video.mp4"): os.remove("input_video.mp4")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "input_video.mp4"

def process_text_for_burning(text):
    try:
        return get_display(arabic_reshaper.reshape(text))
    except:
        return text

def create_srt_files(segments, target_lang):
    clean_srt, burn_srt = "", ""
    translator = GoogleTranslator(source='auto', target=target_lang)
    my_bar = st.progress(0, text="جاري الترجمة...")
    
    for i, segment in enumerate(segments, 1):
        start = str(timedelta(seconds=int(segment['start']))) + ',000'
        end = str(timedelta(seconds=int(segment['end']))) + ',000'
        original_text = segment['text'].strip()
        
        try:
            translated_text = translator.translate(original_text)
        except:
            translated_text = original_text
            
        clean_srt += f"{i}\n{start} --> {end}\n{translated_text}\n\n"
        ready_text = process_text_for_burning(translated_text) if target_lang == "ar" else translated_text
        burn_srt += f"{i}\n{start} --> {end}\n{ready_text}\n\n"
        my_bar.progress(i / len(segments))
        
    my_bar.empty()
    return clean_srt, burn_srt

def burn_subtitles(video_file, srt_file_path):
    output_file = "final_video.mp4"
    if os.path.exists(output_file): os.remove(output_file)
    try:
        style = "Fontsize=24,Alignment=2,MarginV=25,BorderStyle=1,Outline=1"
        stream = ffmpeg.input(video_file)
        stream = ffmpeg.output(stream, output_file, vf=f"subtitles={srt_file_path}:force_style='{style}'")
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
        return output_file
    except:
        return None

# --- الواجهة ---
tab1, tab2 = st.tabs(["🔴 رابط يوتيوب", "📂 رفع ملف"])
video_source = None

with tab1:
    url = st.text_input("ضع الرابط:")
    if st.button("🚀 سحب ومعالجة") and url:
        with st.spinner("جاري محاولة التحميل بوضع (Android Mode)..."):
            try:
                video_source = download_video_android_mode(url)
            except Exception as e:
                st.error("⚠️ يوتيوب يرفض الاتصال من هذا السيرفر حالياً.")
                st.info("💡 الحل المؤكد: حمل الفيديو على هاتفك بأي برنامج (مثل SnapTube) ثم استخدم التبويب الثاني 'رفع ملف' هنا.")

with tab2:
    uploaded = st.file_uploader("ملف فيديو", type=["mp4", "mov"])
    if st.button("🚀 معالجة الملف") and uploaded:
        with open("input_video.mp4", "wb") as f: f.write(uploaded.getbuffer())
        video_source = "input_video.mp4"

if video_source and os.path.exists(video_source):
    st.divider()
    with st.spinner("جاري المعالجة والدمج..."):
        model = whisper.load_model(model_type)
        result = model.transcribe(video_source)
        clean, burn = create_srt_files(result["segments"], target_lang_code)
        
        with open("burn.srt", "w", encoding="utf-8") as f: f.write(burn)
        
        final_video = burn_subtitles(video_source, "burn.srt")
        
        if final_video:
            st.video(final_video)
            with open(final_video, "rb") as v:
                st.download_button("⬇️ تحميل الفيديو", v, "video_final.mp4")
                
        st.download_button("📄 ملف الترجمة فقط", clean, "subs.srt")

