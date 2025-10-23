#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Multi-Modal Generator
Chương trình tích hợp Chat, Image Generation, Video Generation và Text-to-Speech
Sử dụng API AI Thực Chiến
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import os
import base64
import time
import threading
import requests
import logging
from datetime import datetime
from openai import OpenAI
from PIL import Image, ImageTk
import io

class AIGenerator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Multi-Modal Generator")
        self.root.geometry("1000x700")
        
        # Session management
        self.session_id = None
        self.session_folder = None
        self.api_key = None
        self.client = None
        
        # Chat history
        self.chat_history = []
        
        # Setup logging
        self.setup_logging()
        
        # Setup GUI
        self.setup_gui()
        
    def setup_logging(self):
        """Thiết lập hệ thống logging"""
        # Tạo folder logs nếu chưa có
        os.makedirs("logs", exist_ok=True)
        
        # Cấu hình logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/ai_generator_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("=== AI Multi-Modal Generator Started ===")
        
    def log_session(self, message):
        """Log với session info"""
        if self.session_folder:
            log_file = os.path.join(self.session_folder, "session.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} - {message}\n")
        
    def setup_gui(self):
        """Thiết lập giao diện chính"""
        # Tạo notebook cho các tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tạo các tabs
        self.create_settings_tab()
        self.create_chat_tab()
        self.create_image_tab()
        self.create_video_tab()
        self.create_tts_tab()
        
        # Disable tất cả tabs trừ Settings
        self.disable_all_tabs_except_settings()
        
    def create_settings_tab(self):
        """Tạo tab Settings"""
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="⚙️ Settings")
        
        # API Key input
        ttk.Label(self.settings_frame, text="API Key:", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.api_key_var = tk.StringVar()
        api_entry = ttk.Entry(self.settings_frame, textvariable=self.api_key_var, 
                            width=60, show="*", font=("Arial", 10))
        api_entry.pack(pady=5)
        
        # Save button
        save_btn = ttk.Button(self.settings_frame, text="💾 Save & Start", 
                             command=self.save_api_key)
        save_btn.pack(pady=10)
        
        # Status label
        self.status_label = ttk.Label(self.settings_frame, text="Chưa có API key", 
                                     foreground="red")
        self.status_label.pack(pady=5)
        
        # Instructions
        instructions = """
Hướng dẫn sử dụng:
1. Nhập API key của bạn vào ô trên
2. Click "Save & Start" để bắt đầu
3. Sử dụng các tab khác để tạo nội dung
4. Tất cả output sẽ được lưu trong folder data/session_YYYYMMDD_HHMMSS/
        """
        ttk.Label(self.settings_frame, text=instructions, justify=tk.LEFT).pack(pady=20)
        
    def create_chat_tab(self):
        """Tạo tab Chat"""
        self.chat_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.chat_frame, text="💬 Chat")
        
        # Chat history display
        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, height=20, 
                                                    state=tk.DISABLED, wrap=tk.WORD)
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Input frame
        input_frame = ttk.Frame(self.chat_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.chat_input = tk.Text(input_frame, height=3, wrap=tk.WORD)
        self.chat_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        send_btn = ttk.Button(input_frame, text="📤 Send", command=self.send_chat_message)
        send_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Bind Enter key
        self.chat_input.bind("<Control-Return>", lambda e: self.send_chat_message())
        
    def create_image_tab(self):
        """Tạo tab Image Generation"""
        self.image_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.image_frame, text="🖼️ Image")
        
        # Mode selection
        mode_frame = ttk.LabelFrame(self.image_frame, text="Chế độ", padding=10)
        mode_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.image_mode = tk.StringVar(value="text_to_image")
        ttk.Radiobutton(mode_frame, text="Text → Image", variable=self.image_mode, 
                       value="text_to_image").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Image → Image", variable=self.image_mode, 
                       value="image_to_image").pack(anchor=tk.W)
        
        # Prompt input
        prompt_frame = ttk.LabelFrame(self.image_frame, text="Mô tả", padding=10)
        prompt_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.image_prompt = tk.Text(prompt_frame, height=3, wrap=tk.WORD)
        self.image_prompt.pack(fill=tk.X)
        
        # Image input (for image-to-image mode)
        self.image_input_frame = ttk.LabelFrame(self.image_frame, text="Ảnh đầu vào", padding=10)
        self.image_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.image_path_var = tk.StringVar()
        path_entry = ttk.Entry(self.image_input_frame, textvariable=self.image_path_var, 
                              state=tk.DISABLED)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_btn = ttk.Button(self.image_input_frame, text="📁 Browse", 
                              command=self.browse_image)
        browse_btn.pack(side=tk.RIGHT)
        
        # Generate button
        generate_btn = ttk.Button(self.image_frame, text="🎨 Generate Image", 
                                command=self.generate_image)
        generate_btn.pack(pady=10)
        
        # Preview frame
        self.preview_frame = ttk.LabelFrame(self.image_frame, text="Preview", padding=10)
        self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.image_preview = ttk.Label(self.preview_frame, text="Chưa có ảnh")
        self.image_preview.pack(expand=True)
        
    def create_video_tab(self):
        """Tạo tab Video Generation"""
        self.video_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.video_frame, text="🎬 Video")
        
        # Prompt input
        prompt_frame = ttk.LabelFrame(self.video_frame, text="Mô tả video", padding=10)
        prompt_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.video_prompt = tk.Text(prompt_frame, height=3, wrap=tk.WORD)
        self.video_prompt.pack(fill=tk.X)
        
        # Image input (optional)
        image_frame = ttk.LabelFrame(self.video_frame, text="Ảnh đầu vào (tùy chọn)", padding=10)
        image_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.video_image_path_var = tk.StringVar()
        path_entry = ttk.Entry(image_frame, textvariable=self.video_image_path_var, 
                              state=tk.DISABLED)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_btn = ttk.Button(image_frame, text="📁 Browse", 
                              command=self.browse_video_image)
        browse_btn.pack(side=tk.RIGHT)
        
        # Settings
        settings_frame = ttk.LabelFrame(self.video_frame, text="Cài đặt", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Aspect ratio
        ttk.Label(settings_frame, text="Tỷ lệ khung hình:").grid(row=0, column=0, sticky=tk.W)
        self.aspect_ratio = tk.StringVar(value="16:9")
        aspect_combo = ttk.Combobox(settings_frame, textvariable=self.aspect_ratio, 
                                   values=["16:9", "9:16", "1:1"])
        aspect_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Resolution
        ttk.Label(settings_frame, text="Độ phân giải:").grid(row=1, column=0, sticky=tk.W)
        self.resolution = tk.StringVar(value="720p")
        res_combo = ttk.Combobox(settings_frame, textvariable=self.resolution, 
                                values=["720p", "1080p"])
        res_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Generate button
        generate_btn = ttk.Button(self.video_frame, text="🎬 Generate Video", 
                               command=self.generate_video)
        generate_btn.pack(pady=10)
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Sẵn sàng")
        self.progress_label = ttk.Label(self.video_frame, textvariable=self.progress_var)
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(self.video_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
    def create_tts_tab(self):
        """Tạo tab Text-to-Speech"""
        self.tts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tts_frame, text="🎤 TTS")
        
        # Text input
        text_frame = ttk.LabelFrame(self.tts_frame, text="Văn bản", padding=10)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tts_text = scrolledtext.ScrolledText(text_frame, height=10, wrap=tk.WORD)
        self.tts_text.pack(fill=tk.BOTH, expand=True)
        
        # Voice selection
        voice_frame = ttk.LabelFrame(self.tts_frame, text="Giọng nói", padding=10)
        voice_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(voice_frame, text="Chọn giọng:").pack(side=tk.LEFT)
        self.voice_var = tk.StringVar(value="Zephyr")
        voice_combo = ttk.Combobox(voice_frame, textvariable=self.voice_var,
                                  values=["Zephyr", "Puck", "Charon", "Kore"])
        voice_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Generate button
        generate_btn = ttk.Button(self.tts_frame, text="🎤 Generate Audio", 
                                command=self.generate_tts)
        generate_btn.pack(pady=10)
        
        # Status
        self.tts_status = ttk.Label(self.tts_frame, text="Sẵn sàng")
        self.tts_status.pack(pady=5)
        
    def disable_all_tabs_except_settings(self):
        """Disable tất cả tabs trừ Settings"""
        for i in range(1, self.notebook.index("end")):
            self.notebook.tab(i, state="disabled")
            
    def enable_all_tabs(self):
        """Enable tất cả tabs"""
        for i in range(self.notebook.index("end")):
            self.notebook.tab(i, state="normal")
            
    def save_api_key(self):
        """Lưu API key và khởi tạo session"""
        self.logger.info("=== Bắt đầu quá trình lưu API key ===")
        
        api_key = self.api_key_var.get().strip()
        if not api_key:
            self.logger.warning("Người dùng chưa nhập API key")
            messagebox.showerror("Lỗi", "Vui lòng nhập API key!")
            return
            
        self.logger.info(f"API key được nhập: {api_key[:10]}...{api_key[-4:]}")
        
        try:
            self.api_key = api_key
            self.client = OpenAI(api_key=api_key, base_url="https://api.thucchien.ai")
            self.logger.info("OpenAI client đã được khởi tạo thành công")
            
            # Test API key trước khi tiếp tục
            self.logger.info("Đang kiểm tra API key...")
            if not self._test_api_key():
                self.logger.error("API key không hợp lệ hoặc đã hết hạn")
                messagebox.showerror("Lỗi", "API key không hợp lệ hoặc đã hết hạn!\nVui lòng kiểm tra lại API key của bạn.")
                return
            
            # Tạo session mới
            self.create_new_session()
            
            # Enable tất cả tabs
            self.enable_all_tabs()
            
            # Update status
            self.status_label.config(text="✅ API key đã được lưu và xác thực", foreground="green")
            
            self.logger.info("API key đã được lưu và xác thực thành công, tất cả tabs đã được kích hoạt")
            messagebox.showinfo("Thành công", "API key đã được lưu và xác thực thành công! Bạn có thể sử dụng các chức năng khác.")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu API key: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi lưu API key: {str(e)}")
    
    def _test_api_key(self):
        """Test API key với một request đơn giản"""
        try:
            # Test với chat API (đơn giản nhất)
            url = "https://api.thucchien.ai/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": "gemini-2.5-flash",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                self.logger.info("API key hợp lệ")
                return True
            else:
                self.logger.error(f"API key test failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Lỗi khi test API key: {str(e)}")
            return False
        
    def create_new_session(self):
        """Tạo session mới với timestamp"""
        self.logger.info("=== Tạo session mới ===")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = f"session_{timestamp}"
        self.session_folder = os.path.join("data", self.session_id)
        
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info(f"Session folder: {self.session_folder}")
        
        # Tạo folder structure
        os.makedirs(self.session_folder, exist_ok=True)
        os.makedirs(os.path.join(self.session_folder, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.session_folder, "videos"), exist_ok=True)
        os.makedirs(os.path.join(self.session_folder, "audio"), exist_ok=True)
        
        self.logger.info("Đã tạo cấu trúc folder cho session")
        
        # Tạo session info
        session_info = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "api_calls": 0
        }
        
        with open(os.path.join(self.session_folder, "session_info.json"), "w", encoding="utf-8") as f:
            json.dump(session_info, f, ensure_ascii=False, indent=2)
            
        self.logger.info("Đã tạo session_info.json")
        
        # Initialize chat history
        self.chat_history = [{"role": "system", "content": "Bạn là một trợ lý ảo thân thiện, chuyên nghiệp, nói tiếng Việt tự nhiên."}]
        
        self.logger.info("Session mới đã được tạo thành công")
        self.log_session("Session mới được tạo")
        
    def send_chat_message(self):
        """Gửi tin nhắn chat"""
        self.logger.info("=== Bắt đầu quá trình chat ===")
        
        if not self.client:
            self.logger.warning("Client chưa được khởi tạo, yêu cầu nhập API key")
            messagebox.showerror("Lỗi", "Vui lòng nhập API key trước!")
            return
            
        message = self.chat_input.get("1.0", tk.END).strip()
        if not message:
            self.logger.warning("Tin nhắn rỗng, bỏ qua")
            return
            
        self.logger.info(f"Tin nhắn người dùng: {message[:50]}...")
        
        # Clear input
        self.chat_input.delete("1.0", tk.END)
        
        # Add to history
        self.chat_history.append({"role": "user", "content": message})
        self.logger.info("Đã thêm tin nhắn người dùng vào lịch sử")
        
        # Display user message
        self.display_chat_message("👤 Bạn", message)
        
        # Get AI response
        try:
            self.logger.info("Đang gọi API chat completions...")
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=self.chat_history
            )
            
            end_time = time.time()
            self.logger.info(f"API chat hoàn thành trong {end_time - start_time:.2f} giây")
            
            ai_message = response.choices[0].message.content
            self.logger.info(f"Phản hồi AI: {ai_message[:50]}...")
            
            self.chat_history.append({"role": "assistant", "content": ai_message})
            self.logger.info("Đã thêm phản hồi AI vào lịch sử")
            
            # Display AI response
            self.display_chat_message("🤖 AI", ai_message)
            
            # Save chat history
            self.save_chat_history()
            
            self.log_session(f"Chat: User: {message[:30]}... | AI: {ai_message[:30]}...")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi gọi API chat: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi gọi API: {str(e)}")
            
    def display_chat_message(self, sender, message):
        """Hiển thị tin nhắn trong chat"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: {message}\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        
    def save_chat_history(self):
        """Lưu lịch sử chat"""
        with open(os.path.join(self.session_folder, "chat_history.json"), "w", encoding="utf-8") as f:
            json.dump(self.chat_history, f, ensure_ascii=False, indent=2)
            
    def browse_image(self):
        """Chọn ảnh cho image-to-image mode"""
        file_path = filedialog.askopenfilename(
            title="Chọn ảnh",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self.image_path_var.set(file_path)
            
    def browse_video_image(self):
        """Chọn ảnh cho video generation"""
        file_path = filedialog.askopenfilename(
            title="Chọn ảnh",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self.video_image_path_var.set(file_path)
            
    def generate_image(self):
        """Tạo ảnh"""
        self.logger.info("=== Bắt đầu quá trình tạo ảnh ===")
        
        if not self.client:
            self.logger.warning("Client chưa được khởi tạo, yêu cầu nhập API key")
            messagebox.showerror("Lỗi", "Vui lòng nhập API key trước!")
            return
            
        prompt = self.image_prompt.get("1.0", tk.END).strip()
        if not prompt:
            self.logger.warning("Người dùng chưa nhập mô tả ảnh")
            messagebox.showerror("Lỗi", "Vui lòng nhập mô tả ảnh!")
            return
            
        mode = self.image_mode.get()
        self.logger.info(f"Chế độ tạo ảnh: {mode}")
        self.logger.info(f"Prompt: {prompt[:50]}...")
        
        try:
            if mode == "text_to_image":
                self.logger.info("Bắt đầu tạo ảnh từ text...")
                start_time = time.time()
                
                # Text to image - Y CHANG NOTEBOOK - dùng client.images.generate()
                response = self.client.images.generate(
                    model="gemini-2.5-flash-image-preview",
                    prompt=prompt,
                    n=1,
                    extra_body={
                        "aspect_ratio": "1:1"
                    }
                )
                
                end_time = time.time()
                self.logger.info(f"API tạo ảnh hoàn thành trong {end_time - start_time:.2f} giây")
                
                # Save image - Y CHANG NOTEBOOK
                b64_data = response.data[0].b64_json
                image_data = base64.b64decode(b64_data)
                self.logger.info(f"Đã decode ảnh, kích thước: {len(image_data)} bytes")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"image_{timestamp}.png"
                filepath = os.path.join(self.session_folder, "images", filename)
                
                with open(filepath, "wb") as f:
                    f.write(image_data)
                    
                self.logger.info(f"Đã lưu ảnh tại: {filepath}")
                
                # Update preview
                self.update_image_preview(filepath)
                self.logger.info("Đã cập nhật preview ảnh")
                
                # Save metadata
                metadata = {
                    "type": "text_to_image",
                    "prompt": prompt,
                    "filename": filename,
                    "created_at": datetime.now().isoformat()
                }
                
                with open(os.path.join(self.session_folder, "images", f"{filename}.json"), "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                    
                self.logger.info("Đã lưu metadata cho ảnh")
                self.log_session(f"Image Generation (Text): {prompt[:30]}... -> {filename}")
                
                messagebox.showinfo("Thành công", f"Ảnh đã được tạo và lưu tại: {filepath}")
                
            else:  # image_to_image
                self.logger.info("Bắt đầu tạo ảnh từ ảnh có sẵn...")
                
                image_path = self.image_path_var.get()
                if not image_path or not os.path.exists(image_path):
                    self.logger.warning("Không tìm thấy ảnh đầu vào")
                    messagebox.showerror("Lỗi", "Vui lòng chọn ảnh đầu vào!")
                    return
                    
                self.logger.info(f"Ảnh đầu vào: {image_path}")
                
                # Read and encode image
                with open(image_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")
                    
                self.logger.info(f"Đã encode ảnh, kích thước base64: {len(image_b64)} characters")
                    
                # Call Gemini API for image-to-image
                self.logger.info("Đang gọi Gemini API cho image-to-image...")
                start_time = time.time()
                
                headers = {
                    "x-goog-api-key": self.api_key,
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "contents": [{
                        "parts": [
                            {
                                "text": (
                                    f"Here is an image. Please generate a new version "
                                    f"based on this image with the following modification: {prompt}. "
                                    f"The new image should reflect this change realistically."
                                )
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": image_b64
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "imageConfig": {
                            "aspectRatio": "1:1"
                        }
                    }
                }
                
                self.logger.info("Đang gửi request đến Gemini API...")
                response = requests.post(
                    "https://api.thucchien.ai/gemini/v1beta/models/gemini-2.5-flash-image-preview:generateContent",
                    headers=headers,
                    json=payload
                )
                
                end_time = time.time()
                self.logger.info(f"Gemini API hoàn thành trong {end_time - start_time:.2f} giây")
                
                if response.status_code != 200:
                    self.logger.error(f"API error: {response.status_code} - {response.text}")
                    messagebox.showerror("Lỗi", f"API error: {response.status_code} - {response.text}")
                    return
                    
                data = response.json()
                self.logger.info("Đã nhận được phản hồi từ Gemini API")
                
                # Extract image data - xử lý như trong notebook
                try:
                    parts = data["candidates"][0]["content"]["parts"]
                    img_b64 = None
                    for p in parts:
                        if "inline_data" in p:
                            img_b64 = p["inline_data"]["data"]
                        elif "inlineData" in p:
                            img_b64 = p["inlineData"]["data"]
                            
                    if not img_b64:
                        self.logger.error("Gemini không trả về dữ liệu ảnh")
                        messagebox.showerror("Lỗi", f"Gemini không trả về dữ liệu ảnh. Phản hồi API:\n{json.dumps(data, indent=2)}")
                        return
                        
                    self.logger.info(f"Đã trích xuất dữ liệu ảnh, kích thước: {len(img_b64)} characters")
                except Exception as e:
                    self.logger.error(f"Lỗi khi xử lý phản hồi API: {str(e)}")
                    messagebox.showerror("Lỗi", f"Lỗi khi xử lý phản hồi API: {str(e)}\n{json.dumps(data, indent=2)}")
                    return
                    
                # Save image
                img_data = base64.b64decode(img_b64)
                self.logger.info(f"Đã decode ảnh, kích thước: {len(img_data)} bytes")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"image_edited_{timestamp}.png"
                filepath = os.path.join(self.session_folder, "images", filename)
                
                with open(filepath, "wb") as f:
                    f.write(img_data)
                    
                self.logger.info(f"Đã lưu ảnh chỉnh sửa tại: {filepath}")
                
                # Update preview
                self.update_image_preview(filepath)
                self.logger.info("Đã cập nhật preview ảnh")
                
                # Save metadata
                metadata = {
                    "type": "image_to_image",
                    "prompt": prompt,
                    "input_image": image_path,
                    "filename": filename,
                    "created_at": datetime.now().isoformat()
                }
                
                with open(os.path.join(self.session_folder, "images", f"{filename}.json"), "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                    
                self.logger.info("Đã lưu metadata cho ảnh chỉnh sửa")
                self.log_session(f"Image Generation (Edit): {prompt[:30]}... -> {filename}")
                
                messagebox.showinfo("Thành công", f"Ảnh đã được chỉnh sửa và lưu tại: {filepath}")
                
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo ảnh: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi tạo ảnh: {str(e)}")
            
    def update_image_preview(self, image_path):
        """Cập nhật preview ảnh"""
        try:
            # Load and resize image for preview
            image = Image.open(image_path)
            image.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # Update label
            self.image_preview.config(image=photo, text="")
            self.image_preview.image = photo  # Keep a reference
            
        except Exception as e:
            self.image_preview.config(text=f"Lỗi hiển thị ảnh: {str(e)}")
            
    def generate_video(self):
        """Tạo video (chạy trong thread riêng)"""
        self.logger.info("=== Bắt đầu quá trình tạo video ===")
        
        if not self.client:
            self.logger.warning("Client chưa được khởi tạo, yêu cầu nhập API key")
            messagebox.showerror("Lỗi", "Vui lòng nhập API key trước!")
            return
            
        prompt = self.video_prompt.get("1.0", tk.END).strip()
        if not prompt:
            self.logger.warning("Người dùng chưa nhập mô tả video")
            messagebox.showerror("Lỗi", "Vui lòng nhập mô tả video!")
            return
            
        self.logger.info(f"Prompt video: {prompt[:50]}...")
        self.logger.info("Bắt đầu tạo video trong thread riêng...")
        
        # Start video generation in separate thread
        thread = threading.Thread(target=self._generate_video_thread, args=(prompt,))
        thread.daemon = True
        thread.start()
        
    def _generate_video_thread(self, prompt):
        """Thread function để tạo video"""
        try:
            self.logger.info("=== Bước 1: Tạo request video ===")
            # Step 1: Create video
            self.progress_var.set("Đang tạo video...")
            self.progress_bar.start()
            
            operation_name = self._create_video_request(prompt)
            if not operation_name:
                self.logger.error("Không thể tạo request video")
                return
                
            self.logger.info(f"Đã tạo request video, operation: {operation_name}")
                
            # Step 2: Check progress
            self.logger.info("=== Bước 2: Kiểm tra tiến độ video ===")
            self.progress_var.set("Đang chờ video hoàn thành... (có thể mất vài phút)")
            video_id = self._check_video_progress(operation_name)
            if not video_id:
                self.logger.error("Không thể lấy video ID")
                self.progress_var.set("Lỗi: Không thể lấy video ID")
                return
                
            self.logger.info(f"Video đã hoàn thành, video ID: {video_id}")
                
            # Step 3: Download video
            self.logger.info("=== Bước 3: Tải video ===")
            self.progress_var.set("Đang tải video...")
            self._download_video(video_id)
            
            self.progress_var.set("Video đã hoàn thành!")
            self.progress_bar.stop()
            self.logger.info("Quá trình tạo video hoàn thành thành công")
            self.log_session(f"Video Generation: {prompt[:30]}... -> completed")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo video: {str(e)}")
            self.progress_var.set(f"Lỗi: {str(e)}")
            self.progress_bar.stop()
            messagebox.showerror("Lỗi", f"Lỗi khi tạo video: {str(e)}")
            
    def _create_video_request(self, prompt):
        """Tạo request video - theo đúng notebook"""
        self.logger.info("Đang tạo request video...")
        url = "https://api.thucchien.ai/gemini/v1beta/models/veo-3.0-generate-001:predictLongRunning"
        
        # Check if image is provided - theo đúng logic notebook
        image_path = self.video_image_path_var.get()
        image_obj = None
        if image_path and os.path.exists(image_path):
            self.logger.info(f"Sử dụng ảnh đầu vào: {image_path}")
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            
            # Sử dụng mimetypes như trong notebook
            import mimetypes
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/png"
                
            image_obj = {
                "bytesBase64Encoded": img_b64,
                "mimeType": mime_type
            }
            self.logger.info(f"Đã encode ảnh, kích thước: {len(img_b64)} characters, mime_type: {mime_type}")
        else:
            self.logger.info("Không có ảnh đầu vào, tạo video từ text")
            
        instance = {"prompt": prompt}
        if image_obj:
            instance["image"] = image_obj
            
        payload = {
            "instances": [instance],
            "parameters": {
                "negativePrompt": "blurry, low quality",
                "aspectRatio": self.aspect_ratio.get(),
                "resolution": self.resolution.get(),
                "personGeneration": "allow_all" if not image_obj else "allow_adult"
            }
        }
        
        self.logger.info(f"Tạo video với prompt: {prompt}")
        print(f"\nTao video voi prompt: {prompt}")
        if image_obj:
            self.logger.info(f"Sử dụng ảnh làm đầu vào: {image_path}")
            print(f"Su dung anh lam dau vao: {image_path}")
        self.logger.info(f"Payload video: aspect_ratio={self.aspect_ratio.get()}, resolution={self.resolution.get()}")
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        self.logger.info("Đang gửi request tạo video...")
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload)
        end_time = time.time()
        
        self.logger.info(f"Request video hoàn thành trong {end_time - start_time:.2f} giây")
        
        if response.status_code != 200:
            self.logger.error(f"Lỗi tạo video: {response.status_code} - {response.text}")
            messagebox.showerror("Lỗi", f"Lỗi tạo video: {response.status_code}")
            return None
            
        data = response.json()
        operation_name = data.get("name")
        if not operation_name:
            self.logger.error("Không tìm thấy operation_name trong phản hồi")
            self.logger.error(f"Phản hồi API: {json.dumps(data, indent=2)}")
            messagebox.showerror("Lỗi", "Không tìm thấy operation_name trong phản hồi")
            return None
            
            self.logger.info("Đã gửi yêu cầu tạo video thành công")
        self.logger.info(f"Mã tiến trình (operation): {operation_name}")
        print(f"Da gui yeu cau tao video thanh cong.")
        print(f"Ma tien trinh (operation): {operation_name}")
        return operation_name
        
    def _check_video_progress(self, operation_name):
        """Kiểm tra tiến độ video - theo đúng notebook"""
        self.logger.info(f"Bắt đầu kiểm tra tiến độ video: {operation_name}")
        
        # Xử lý URL như trong notebook
        if operation_name.startswith("models/"):
            url = f"https://api.thucchien.ai/gemini/v1beta/{operation_name}"
        else:
            url = f"https://api.thucchien.ai/gemini/v1beta/models/veo-3.0-generate-001/operations/{operation_name}"
            
        headers = {"x-goog-api-key": self.api_key}
        
        self.logger.info("Đang kiểm tra tiến độ video...")
        print("\nDang kiem tra tien do video...")
        check_count = 0
        
        while True:
            check_count += 1
            self.logger.info(f"Kiểm tra tiến độ lần {check_count}...")
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                self.logger.error(f"Lỗi khi kiểm tra tiến độ: {response.status_code} - {response.text}")
                messagebox.showerror("Lỗi", f"Lỗi khi kiểm tra tiến độ: {response.status_code}")
                return None
                
            data = response.json()
            done = data.get("done", False)
            
            if done:
                self.logger.info("Video đã hoàn thành!")
                
                # Extract video ID - theo đúng logic notebook
                video_id = None
                try:
                    uri = (
                        data["response"]["generateVideoResponse"]
                        ["generatedSamples"][0]["video"]["uri"]
                    )
                    # Rút ID từ URI
                    if ":download" in uri:
                        video_id = uri.split("/")[-1].split(":")[0]
                except Exception:
                    # fallback cho cấu trúc cũ
                    try:
                        video_id = data["response"]["video"]["name"]
                    except:
                        pass
                        
                if not video_id:
                    self.logger.error("Không tìm thấy video_id trong phản hồi")
                    self.logger.error(f"Phản hồi API: {json.dumps(data, indent=2)}")
                    messagebox.showerror("Lỗi", "Không thể trích xuất video ID")
                    return None
                    
                self.logger.info(f"Video ID: {video_id}")
                print(f"Video da hoan tat!")
                print(f"Video ID: {video_id}")
                return video_id
            else:
                progress = data.get("metadata", {}).get("progressPercent", "Đang xử lý")
                self.logger.info(f"Tiến độ: {progress}% - chờ 60 giây trước khi kiểm tra lại...")
                print(f"Tien do: {progress}% - cho 60 giay truoc khi kiem tra lai...")
                self.progress_var.set(f"Đang xử lý video... {progress}% - chờ 60 giây...")
                time.sleep(60)  # Chờ 60 giây như trong notebook
                
    def _download_video(self, video_id):
        """Tải video - theo đúng notebook"""
        if not video_id:
            self.logger.error("Không có video_id để tải")
            messagebox.showerror("Lỗi", "Không có video_id để tải")
            return
            
        self.logger.info(f"Bắt đầu tải video: {video_id}")
        url = f"https://api.thucchien.ai/gemini/download/v1beta/files/{video_id}:download?alt=media"
        headers = {"x-goog-api-key": self.api_key}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"video_{timestamp}.mp4"
        filepath = os.path.join(self.session_folder, "videos", filename)
        
        self.logger.info(f"Đang tải video về: {filepath}")
        print(f"\nDang tai video ve: {filepath}")
        start_time = time.time()
        
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code != 200:
            self.logger.error(f"Lỗi khi tải video: {response.status_code} - {response.text}")
            messagebox.showerror("Lỗi", f"Lỗi khi tải video: {response.status_code}")
            return
            
        total_size = 0
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)
                    
        end_time = time.time()
        self.logger.info(f"Video đã được tải thành công: {filepath}")
        self.logger.info(f"Đã tải video hoàn thành trong {end_time - start_time:.2f} giây, kích thước: {total_size} bytes")
        print(f"Video da duoc tai thanh cong: {filepath}")
        
        # Save metadata
        metadata = {
            "video_id": video_id,
            "filename": filename,
            "created_at": datetime.now().isoformat(),
            "file_size": total_size
        }
        
        with open(os.path.join(self.session_folder, "videos", f"{filename}.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        self.logger.info("Đã lưu metadata cho video")
        messagebox.showinfo("Thành công", f"Video đã được tải và lưu tại: {filepath}")
        
    def generate_tts(self):
        """Tạo text-to-speech với Gemini API"""
        self.logger.info("=== Bắt đầu quá trình tạo TTS ===")
        
        if not self.api_key:
            self.logger.warning("API key chưa được khởi tạo, yêu cầu nhập API key")
            messagebox.showerror("Lỗi", "Vui lòng nhập API key trước!")
            return
            
        text = self.tts_text.get("1.0", tk.END).strip()
        if not text:
            self.logger.warning("Người dùng chưa nhập văn bản")
            messagebox.showerror("Lỗi", "Vui lòng nhập văn bản!")
            return
            
        voice = self.voice_var.get()
        self.logger.info(f"Tạo TTS với giọng: {voice}")
        self.logger.info(f"Văn bản: {text[:50]}...")
        
        try:
            self.logger.info("Đang gọi Gemini API TTS...")
            start_time = time.time()
            
            # Gọi Gemini API theo đúng tài liệu
            url = "https://api.thucchien.ai/gemini/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
            
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": text}
                    ]
                }],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": voice
                            }
                        }
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            end_time = time.time()
            self.logger.info(f"API TTS hoàn thành trong {end_time - start_time:.2f} giây")
            
            if response.status_code != 200:
                self.logger.error(f"API error: {response.status_code} - {response.text}")
                messagebox.showerror("Lỗi", f"API error: {response.status_code}")
                return
            
            # Lấy audio data từ response theo cấu trúc Gemini
            data = response.json()
            audio_b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            audio_data = base64.b64decode(audio_b64)
            
            self.logger.info(f"Đã decode audio, kích thước: {len(audio_data)} bytes")
            
            # Save audio
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audio_{timestamp}.wav"
            filepath = os.path.join(self.session_folder, "audio", filename)
            
            self.logger.info(f"Đang lưu audio tại: {filepath}")
            
            with open(filepath, "wb") as f:
                f.write(audio_data)
                        
            self.logger.info(f"Đã lưu audio, kích thước: {len(audio_data)} bytes")
                        
            # Save metadata
            metadata = {
                "text": text,
                "voice": voice,
                "filename": filename,
                "created_at": datetime.now().isoformat(),
                "file_size": len(audio_data)
            }
            
            with open(os.path.join(self.session_folder, "audio", f"{filename}.json"), "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            self.logger.info("Đã lưu metadata cho audio")
            self.log_session(f"TTS: {text[:30]}... (voice: {voice}) -> {filename}")
            
            self.tts_status.config(text=f"✅ Audio đã được tạo: {filename}")
            messagebox.showinfo("Thành công", f"Audio đã được tạo và lưu tại: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo audio: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi tạo audio: {str(e)}")
            
    def run(self):
        """Chạy ứng dụng"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AIGenerator()
    app.run()
