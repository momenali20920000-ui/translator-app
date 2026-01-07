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
st.title("🎬 استوديو الترجمة (Online)")

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    # نستخدم base لأنه أخف وأسرع للسيرفر المجاني
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
    # إعدادات محسنة لتجاوز حظر يوتيوب للسيرفرات
    ydl_opts = {
        'format': 'mp4/best',
        'outtmpl': 'input_video.mp4',
        'quiet': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        # هذا الجزء مهم جداً لخداع يوتيوب
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.google.com/'
        }
    }
    
    if os.path.exists("input_video.mp4"): os.remove("input_video.mp4")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "input_video.mp4"

def process_text_for_burning(text):
    # دالة إصلاح الحروف العربية المقطعة
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except:
        return text

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
        
        # معالجة خاصة للعربية عند الدمج
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
        # استخدام إعدادات خطوط عامة لضمان العمل على السيرفر
        style = "Fontsize=24,Alignment=2,MarginV=25,BorderStyle=1,Outline=1,Shadow=0"
        stream = ffmpeg.input(video_file)
        stream = ffmpeg.output(stream, output_file, vf=f"subtitles={srt_file_path}:force_style='{style}'")
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
        return output_file
    except Exception as e:
        st.warning(f"لم نتمكن من دمج الفيديو بسبب قيود السيرفر: {e}")
        return None

# --- الواجهة ---
tab1, tab2 = st.tabs(["🔗 رابط يوتيوب", "📂 رفع ملف مباشر"])
video_source = None

# التبويب الأول: الرابط
with tab1:
    url = st.text_input("ضع رابط الفيديو هنا:")
    if st.button("🚀 ابدأ من الرابط") and url:
        with st.spinner("جاري محاولة سحب الفيديو..."):
            try:
                video_source = download_video(url)
            except Exception as e:
                # هنا سنظهر الخطأ الحقيقي لنعرف السبب
                st.error(f"تعذر تحميل الفيديو من الرابط (يوتيوب يحظر السيرفرات أحياناً).")
                st.code(f"Error details: {e}")
                st.info("💡 الحل السريع: حمل الفيديو على هاتفك ثم استخدم التبويب الثاني 'رفع ملف مباشر'.")

# التبويب الثاني: رفع الملف
with tab2:
    uploaded = st.file_uploader("اختر الفيديو من جهازك", type=["mp4", "mov", "avi"])
    if st.button("🚀 ابدأ المعالجة") and uploaded:
        with open("input_video.mp4", "wb") as f:
            f.write(uploaded.getbuffer())
        video_source = "input_video.mp4"

# --- بدء المعالجة ---
if video_source and os.path.exists(video_source):
    st.divider()
    st.info(f"✅ تم استلام الفيديو! جاري العمل... (اللغة: {selected_lang_name})")
    
    with st.spinner("🤖 الذكاء الاصطناعي يكتب النص... (قد يستغرق دقيقة)"):
        try:
            model = whisper.load_model(model_type)
            result = model.transcribe(video_source)
            
            clean_text, burn_text = create_srt_files(result["segments"], target_lang_code)
            
            with open("clean_subs.srt", "w", encoding="utf-8") as f: f.write(clean_text)
            with open("burn_subs.srt", "w", encoding="utf-8") as f: f.write(burn_text)
            
            st.success("تم استخراج النص وترجمته!")
            
            # محاولة الدمج
            final_video = None
            with st.spinner("🎞️ جاري دمج الترجمة مع الفيديو..."):
                final_video = burn_subtitles(video_source, "burn_subs.srt")
            
            st.divider()
            if final_video and os.path.exists(final_video):
                st.subheader("📺 الفيديو النهائي:")
                st.video(final_video)
                with open(final_video, "rb") as v:
                    st.download_button("⬇️ تحميل الفيديو المترجم (MP4)", v, "video_translated.mp4")
            else:
                st.warning("تم تجهيز ملف الترجمة، لكن دمج الفيديو فشل (قد يحتاج السيرفر لمكتبات إضافية). يمكنك تحميل ملف الترجمة والفيديو الأصلي.")
                
            st.download_button("📄 تحميل ملف الترجمة (SRT)", clean_text, "subtitles.srt")
            
        except Exception as e:
            st.error(f"حدث خطأ أثناء المعالجة: {e}")

