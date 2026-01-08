import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivy.core.window import Window
import requests
import threading
from plyer import filechooser

# تغيير لون الخلفية ليكون عصرياً
Window.clearcolor = (0.1, 0.1, 0.1, 1)

class DubbingApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # 1. العنوان
        title = Label(text="🎬 المترجم الذكي", font_size='28sp', color=(1, 0.8, 0, 1), size_hint=(1, 0.1))
        self.layout.add_widget(title)
        
        # 2. خانة إدخال الرابط (هنا تضع رابط Kaggle المتغير)
        self.layout.add_widget(Label(text="رابط السيرفر (من Kaggle):", size_hint=(1, 0.05)))
        self.url_input = TextInput(
            hint_text="https://xxxx.trycloudflare.com", 
            multiline=False, 
            size_hint=(1, 0.1),
            background_color=(0.2, 0.2, 0.2, 1),
            foreground_color=(1, 1, 1, 1)
        )
        self.layout.add_widget(self.url_input)

        # 3. خانة التوكن (الكود السري)
        self.layout.add_widget(Label(text="كود التفعيل:", size_hint=(1, 0.05)))
        self.token_input = TextInput(
            text="ADMIN_123", 
            multiline=False, 
            size_hint=(1, 0.1),
            password=True,
            background_color=(0.2, 0.2, 0.2, 1),
            foreground_color=(1, 1, 1, 1)
        )
        self.layout.add_widget(self.token_input)
        
        # 4. زر اختيار الفيديو
        self.btn_select = Button(
            text="📂 اضغط لاختيار فيديو", 
            font_size='20sp', 
            size_hint=(1, 0.15), 
            background_normal='',
            background_color=(0, 0.6, 0.8, 1)
        )
        self.btn_select.bind(on_press=self.select_file)
        self.layout.add_widget(self.btn_select)
        
        # 5. شاشة الحالة (لعرض ما يحدث)
        self.status_label = Label(text="جاهز للعمل...", font_size='16sp', size_hint=(1, None), height=200)
        scroll = ScrollView(size_hint=(1, 0.4))
        scroll.add_widget(self.status_label)
        self.layout.add_widget(scroll)
        
        return self.layout

    def select_file(self, instance):
        # التحقق من أن المستخدم وضع رابطاً
        if not self.url_input.text.strip():
            self.status_label.text = "⚠️ خطأ: يجب وضع رابط السيرفر أولاً!"
            return

        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            
        filechooser.open_file(on_selection=self.start_thread)

    def start_thread(self, selection):
        # تشغيل العمل في الخلفية حتى لا يتجمد التطبيق
        if selection:
            threading.Thread(target=self.process_video, args=(selection,)).start()

    def process_video(self, selection):
        video_path = selection[0]
        server_url = self.url_input.text.strip().rstrip('/')
        token = self.token_input.text.strip()

        self.update_status(f"جاري العمل على:\n{os.path.basename(video_path)}")
        
        # 1. قص الصوت
        self.update_status("✂️ جاري قص الصوت (محلياً)...")
        audio_path = os.path.join(os.path.dirname(video_path), "temp_audio.mp3")
        
        try:
            import ffmpeg
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, acodec='libmp3lame', q=4, vn=None, loglevel="quiet")
                .run(overwrite_output=True)
            )
        except Exception as e:
            self.update_status(f"❌ خطأ في ffmpeg:\n{e}")
            return

        # 2. الإرسال للسيرفر
        self.update_status("🌐 جاري الإرسال للسيرفر...")
        try:
            with open(audio_path, 'rb') as f:
                files = {'file': f}
                data = {'token': token}
                response = requests.post(f"{server_url}/translate", files=files, data=data, timeout=600)
                
            if response.status_code == 200:
                srt_content = response.text
                self.save_and_merge(video_path, srt_content)
            else:
                self.update_status(f"❌ خطأ من السيرفر: {response.status_code}")
        except Exception as e:
            self.update_status(f"❌ فشل الاتصال بالسيرفر.\nتأكد من الرابط!")

    def save_and_merge(self, video_path, srt_content):
        # 3. معالجة العربي وحفظ الترجمة
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            
            self.update_status("📝 معالجة النصوص العربية...")
            srt_path = os.path.join(os.path.dirname(video_path), "subs.srt")
            
            fixed_lines = []
            for line in srt_content.splitlines():
                if "-->" in line or line.isdigit() or not line.strip():
                    fixed_lines.append(line)
                else:
                    try:
                        reshaped = arabic_reshaper.reshape(line)
                        bidi_text = get_display(reshaped)
                        fixed_lines.append(bidi_text)
                    except:
                        fixed_lines.append(line)
                        
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(fixed_lines))
                
            # 4. الحرق
            self.update_status("🎬 جاري إنتاج الفيديو النهائي...")
            output_video = os.path.join(os.path.dirname(video_path), f"Final_{os.path.basename(video_path)}")
            
            import ffmpeg
            style = "Fontname=Arial,Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=50"
            (
                ffmpeg
                .input(video_path)
                .output(output_video, vf=f"subtitles={srt_path}:force_style='{style}'", loglevel="quiet")
                .run(overwrite_output=True)
            )
            self.update_status(f"✅ تم الحفظ بنجاح!\nالملف: Final_{os.path.basename(video_path)}")
            
            # تنظيف
            if os.path.exists(audio_path): os.remove(audio_path)
            if os.path.exists(srt_path): os.remove(srt_path)

        except Exception as e:
             self.update_status(f"❌ خطأ أثناء الدمج: {e}")

    def update_status(self, text):
        # دالة مساعدة لتحديث النص من الـ Thread
        self.status_label.text = text

if __name__ == '__main__':
    DubbingApp().run()
