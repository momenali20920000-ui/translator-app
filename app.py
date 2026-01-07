import streamlit as st
import whisper
import os
import yt_dlp
import ffmpeg
from datetime import timedelta
from deep_translator import GoogleTranslator
import arabic_reshaper
from bidi.algorithm import get_display

st.set_page_config(page_title="المترجم العربي", layout="centered")
st.title("🎬 استوديو الترجمة (يدعم العربية)")

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    # ملاحظة: اخترنا base للتخفيف على السيرفر المجاني
    model_type = st.selectbox("دقة الذكاء الاصطناعي:", ["base", "small"])
    
    lang_options = {
        "العربية": "ar",
        "الإنجليزية": "en", 
        "الفرنسية": "fr",
        "الأسبانية": "es"
    }
    selected_lang_name = st.selectbox("ترجم الفيديو إلى:", list(lang_options.keys()))
    target_lang_code = lang_options[selected_lang_name]

# --- دوال المعالجة ---

def download_video(url):
    ydl_opts = {'format': 'mp4/best', 'outtmpl': 'input_video.mp4', 'quiet': True, 'geo_bypass': True, 'nocheckcertificate': True}
    if os.path.exists("input_video.mp4"): os.remove("input_video.mp4")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "input_video.mp4"

def process_text_for_burning(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def create_srt_files(segments, target_lang):
    clean_srt = ""
    burn_srt = ""
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
        
        if target_lang == "ar":
            ready_text = process_text_for_burning(translated_text)
        else:
            ready_text = translated_text
            
        burn_srt += f"{i}\n{start} --> {end}\n{ready_text}\n\n"
        
        my_bar.progress(i / len(segments))
        
    my_bar.empty()
    return clean_srt, burn_srt

def burn_subtitles(video_file, srt_file_path):
    output_file = "final_video.mp4"
    if os.path.exists(output_file): os.remove(output_file)
    
    try:
        # استخدام خط افتراضي في النظام
        style = "Fontsize=24,Alignment=2,MarginV=25"
        stream = ffmpeg.input(video_file)
        stream = ffmpeg.output(stream, output_file, vf=f"subtitles={srt_file_path}:force_style='{style}'")
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
        return output_file
    except Exception as e:
        return None

# --- الواجهة ---
tab1, tab2 = st.tabs(["🔗 رابط", "📂 ملف"])
video_source = None

with tab1:
    url = st.text_input("الرابط:")
    if st.button("🚀 ابدأ") and url:
        with st.spinner("تحميل..."):
            try:
                video_source = download_video(url)
            except:
                st.error("خطأ في التحميل")

with tab2:
    uploaded = st.file_uploader("ملف", type=["mp4"])
    if st.button("🚀 معالجة") and uploaded:
        with open("input_video.mp4", "wb") as f: f.write(uploaded.getbuffer())
        video_source = "input_video.mp4"

if video_source and os.path.exists(video_source):
    st.info(f"جاري العمل... اللغة: {selected_lang_name}")
    
    with st.spinner("جاري استخراج الكلام... (قد يستغرق وقتاً)"):
        # فرضنا base هنا لتسريع العمل
        model = whisper.load_model("base") 
        result = model.transcribe(video_source)
    
    clean_text, burn_text = create_srt_files(result["segments"], target_lang_code)
    
    with open("clean_subs.srt", "w", encoding="utf-8") as f: f.write(clean_text)
    with open("burn_subs.srt", "w", encoding="utf-8") as f: f.write(burn_text)
    
    st.success("✅ تمت الترجمة!")
    
    with st.spinner("🎞️ جاري الدمج..."):
        final_video = burn_subtitles(video_source, "burn_subs.srt")
    
    st.divider()
    if final_video:
        st.subheader("النتيجة:")
        st.video(final_video)
        with open(final_video, "rb") as v:
            st.download_button("⬇️ تحميل الفيديو", v, "video_translated.mp4")
            
    st.download_button("📄 تحميل ملف الترجمة", clean_text, "subs.srt")
