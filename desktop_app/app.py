"""
IELTS Corner - Desktop Widget (Phiên bản Tối Giản - Tập Trung 100% Nội Dung)
- Thiết kế Zen Mode: Loại bỏ toàn bộ nút bấm rườm rà, dành 100% diện tích cho chữ và ảnh.
- Thanh công cụ siêu mỏng tinh tế ở đỉnh (có thể ẩn hoàn toàn).
- Menu chuột phải tiện lợi: Đầy đủ tính năng Đọc, Đổi cỡ chữ, Chuyển chế độ xem, Ghim...
- Always-on-top: Luôn nổi trên Word, PDF, Chrome, Desktop.
- Dán thông minh Ctrl + V: Tự nhận diện ảnh chụp màn hình hoặc văn bản.
- Tràn viền, không viền đen bao quanh.
"""

import sys
import os
import json
import base64
import io
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageGrab

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ielts_desktop_data.json")

class IELTSCornerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("IELTS Corner")
        self.root.configure(bg="#ffffff")

        # Always-on-top
        self.is_topmost = True
        self.root.attributes("-topmost", True)

        # Trạng thái
        self.active_tab = "text" # "text", "image", "split"
        self.font_size = 14
        self.current_image = None
        self.current_image_data = None
        self.zoom_mode = "fit"
        self.is_zen_mode = False

        # Đọc dữ liệu
        self.load_data()

        # Xây dựng giao diện tối giản
        self.create_minimal_ui()

        # Phím tắt
        self.root.bind("<Control-v>", self.on_paste_global)
        self.root.bind("<Control-V>", self.on_paste_global)
        self.root.bind("<Control-plus>", lambda e: self.change_font_size(2))
        self.root.bind("<Control-equal>", lambda e: self.change_font_size(2))
        self.root.bind("<Control-minus>", lambda e: self.change_font_size(-2))
        self.root.bind("<Control-d>", lambda e: self.play_tts())
        self.root.bind("<Control-D>", lambda e: self.play_tts())

        # Menu chuột phải
        self.create_context_menu()
        self.root.bind("<Button-3>", self.show_context_menu)

        # Bắt sự kiện co giãn
        self.root.bind("<Configure>", self.on_window_resize)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Áp dụng hiển thị ban đầu
        self.switch_tab(self.active_tab)

    def load_data(self):
        default_geometry = "420x500+880+160"
        self.saved_text = (
            "Chào bạn! Giao diện đã được tối giản tối đa:\n\n"
            "• Toàn bộ màn hình dành trọn vẹn cho việc đọc chữ và xem ảnh.\n"
            "• Nhấn Ctrl + V để dán đoạn văn hoặc ảnh chụp màn hình.\n"
            "• Nhấp chuột phải vào bất cứ đâu để mở Menu (Đọc, Cỡ chữ, Chế độ...).\n"
            "• Bấm nút 🌓 ở góc trên để xem song song cả đề bài và bài làm.\n"
            "• Bấm 📌 để ghim luôn nổi trên Word, PDF, Chrome."
        )

        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_geometry = data.get("geometry", default_geometry)
                    self.saved_text = data.get("text", self.saved_text)
                    self.font_size = data.get("font_size", 14)
                    self.active_tab = data.get("active_tab", "text")
                    self.is_topmost = data.get("is_topmost", True)
                    self.is_zen_mode = data.get("is_zen_mode", False)

                    img_b64 = data.get("image_base64", "")
                    if img_b64:
                        try:
                            img_bytes = base64.b64decode(img_b64)
                            self.current_image = Image.open(io.BytesIO(img_bytes))
                            self.current_image_data = img_b64
                        except Exception:
                            pass
            except Exception:
                pass

        self.root.geometry(default_geometry)
        self.root.attributes("-topmost", self.is_topmost)

    def save_data(self):
        try:
            geom = self.root.geometry()
            text_content = self.text_editor.get("1.0", tk.END).strip()
            data = {
                "geometry": geom,
                "text": text_content,
                "font_size": self.font_size,
                "active_tab": self.active_tab,
                "is_topmost": self.is_topmost,
                "is_zen_mode": self.is_zen_mode,
                "image_base64": self.current_image_data or ""
            }
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def create_minimal_ui(self):
        # 1. THANH CÔNG CỤ SIÊU MỎNG (Chỉ cao 26px, trong suốt và hòa vào nền)
        self.top_bar = tk.Frame(self.root, bg="#f8fafc", height=26)
        if not self.is_zen_mode:
            self.top_bar.pack(fill=tk.X, side=tk.TOP)

        # Nhóm chọn chế độ xem dạng Icon siêu gọn
        mode_frame = tk.Frame(self.top_bar, bg="#f8fafc")
        mode_frame.pack(side=tk.LEFT, padx=6, pady=2)

        self.btn_mode_text = tk.Label(
            mode_frame, text="📝 Chữ", font=("Segoe UI", 8, "bold"),
            bg="#ffffff" if self.active_tab == "text" else "#f8fafc",
            fg="#4f46e5" if self.active_tab == "text" else "#64748b",
            padx=6, pady=2, cursor="hand2"
        )
        self.btn_mode_text.pack(side=tk.LEFT, padx=1)
        self.btn_mode_text.bind("<Button-1>", lambda e: self.switch_tab("text"))

        self.btn_mode_image = tk.Label(
            mode_frame, text="🖼️ Hình", font=("Segoe UI", 8, "bold"),
            bg="#ffffff" if self.active_tab == "image" else "#f8fafc",
            fg="#4f46e5" if self.active_tab == "image" else "#64748b",
            padx=6, pady=2, cursor="hand2"
        )
        self.btn_mode_image.pack(side=tk.LEFT, padx=1)
        self.btn_mode_image.bind("<Button-1>", lambda e: self.switch_tab("image"))

        self.btn_mode_split = tk.Label(
            mode_frame, text="🌓 Cả hai", font=("Segoe UI", 8, "bold"),
            bg="#ffffff" if self.active_tab == "split" else "#f8fafc",
            fg="#4f46e5" if self.active_tab == "split" else "#64748b",
            padx=6, pady=2, cursor="hand2"
        )
        self.btn_mode_split.pack(side=tk.LEFT, padx=1)
        self.btn_mode_split.bind("<Button-1>", lambda e: self.switch_tab("split"))

        # Nhóm thao tác bên phải: 🔊 Đọc | 📌 Ghim | ⋯ Menu
        actions_frame = tk.Frame(self.top_bar, bg="#f8fafc")
        actions_frame.pack(side=tk.RIGHT, padx=6)

        self.btn_tts_icon = tk.Label(
            actions_frame, text="🔊", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#334155", padx=4, pady=2, cursor="hand2"
        )
        self.btn_tts_icon.pack(side=tk.LEFT, padx=2)
        self.btn_tts_icon.bind("<Button-1>", lambda e: self.play_tts())

        self.btn_pin_icon = tk.Label(
            actions_frame, text="📌" if self.is_topmost else "📍", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#4f46e5" if self.is_topmost else "#94a3b8",
            padx=4, pady=2, cursor="hand2"
        )
        self.btn_pin_icon.pack(side=tk.LEFT, padx=2)
        self.btn_pin_icon.bind("<Button-1>", lambda e: self.toggle_pin())

        self.btn_menu_icon = tk.Label(
            actions_frame, text="⋯", font=("Segoe UI", 10, "bold"),
            bg="#f8fafc", fg="#475569", padx=4, pady=2, cursor="hand2"
        )
        self.btn_menu_icon.pack(side=tk.LEFT, padx=2)
        self.btn_menu_icon.bind("<Button-1>", lambda e: self.show_context_menu(e))

        # 2. KHUNG NỘI DUNG CHÍNH (TRÀN VIỀN 100%, KHÔNG CÓ VIỀN ĐEN HAY PADDING DÀY)
        self.content_frame = tk.Frame(self.root, bg="#ffffff")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Khung Ảnh
        self.image_container = tk.Frame(self.content_frame, bg="#ffffff")
        self.image_label = tk.Label(
            self.image_container,
            text="📷 Chưa có ảnh\nẤn Ctrl + V dán ảnh chụp màn hình",
            bg="#ffffff", fg="#94a3b8", font=("Segoe UI", 10)
        )
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.image_label.bind("<Button-1>", self.on_image_click)
        self.image_label.bind("<Button-3>", self.show_context_menu)

        # Khung Chữ (Tràn viền, không viền hộp thô)
        self.text_container = tk.Frame(self.content_frame, bg="#ffffff")
        
        self.text_scrollbar = tk.Scrollbar(self.text_container, width=5)
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_editor = tk.Text(
            self.text_container,
            wrap=tk.WORD,
            font=("Segoe UI", self.font_size),
            fg="#0f172a",
            bg="#ffffff",
            bd=0,
            highlightthickness=0,
            relief="flat",
            padx=12,
            pady=10,
            undo=True,
            yscrollcommand=self.text_scrollbar.set
        )
        self.text_editor.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.text_scrollbar.config(command=self.text_editor.yview)

        # Nạp nội dung
        self.text_editor.insert("1.0", self.saved_text)
        self.text_editor.bind("<Button-3>", self.show_context_menu)

        # Rê chuột vào đỉnh cửa sổ để hiện thanh công cụ khi ở chế độ Zen Mode
        self.root.bind("<Motion>", self.check_hover_top_bar)

    def check_hover_top_bar(self, event):
        if self.is_zen_mode:
            if event.y < 28:
                if not self.top_bar.winfo_ismapped():
                    self.top_bar.pack(fill=tk.X, side=tk.TOP, before=self.content_frame)
            elif event.y > 45:
                if self.top_bar.winfo_ismapped():
                    self.top_bar.pack_forget()

    def create_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 9))
        self.menu.add_command(label="🔊 Nghe đọc đoạn văn (Ctrl+D)", command=self.play_tts)
        self.menu.add_separator()

        # Chế độ xem
        self.menu.add_command(label="📝 Chỉ xem Văn bản", command=lambda: self.switch_tab("text"))
        self.menu.add_command(label="🖼️ Chỉ xem Hình ảnh", command=lambda: self.switch_tab("image"))
        self.menu.add_command(label="🌓 Xem Cả hai (Song song)", command=lambda: self.switch_tab("split"))
        self.menu.add_separator()

        # Cỡ chữ
        self.menu.add_command(label="➕ Phóng to chữ (A+)", command=lambda: self.change_font_size(2))
        self.menu.add_command(label="➖ Thu nhỏ chữ (A-)", command=lambda: self.change_font_size(-2))
        self.menu.add_separator()

        # Tải ảnh
        self.menu.add_command(label="📁 Tải file ảnh từ máy...", command=self.choose_image_file)
        self.menu.add_command(label="📌 Bật/Tắt Ghim trên cùng", command=self.toggle_pin)
        self.menu.add_command(
            label="✨ Ẩn/Hiện thanh công cụ trên (Zen Mode)", command=self.toggle_zen_mode
        )
        self.menu.add_separator()

        # Xóa
        self.menu.add_command(label="🗑️ Xóa hết chữ", command=self.clear_text)
        self.menu.add_command(label="🗑️ Xóa hình ảnh", command=self.clear_image)

    def show_context_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def switch_tab(self, tab):
        self.active_tab = tab

        # Cập nhật style nút trên top_bar
        for btn, t in [(self.btn_mode_text, "text"), (self.btn_mode_image, "image"), (self.btn_mode_split, "split")]:
            if t == tab:
                btn.configure(bg="#ffffff", fg="#4f46e5")
            else:
                btn.configure(bg="#f8fafc", fg="#64748b")

        self.image_container.pack_forget()
        self.text_container.pack_forget()

        if tab == "text":
            self.text_container.pack(fill=tk.BOTH, expand=True)
        elif tab == "image":
            self.image_container.pack(fill=tk.BOTH, expand=True)
            self.render_image()
        elif tab == "split":
            self.image_container.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
            self.text_container.pack(fill=tk.BOTH, expand=True, side=tk.BOTTOM)
            self.render_image()

    def toggle_pin(self):
        self.is_topmost = not self.is_topmost
        self.root.attributes("-topmost", self.is_topmost)
        self.btn_pin_icon.configure(
            text="📌" if self.is_topmost else "📍",
            fg="#4f46e5" if self.is_topmost else "#94a3b8"
        )

    def toggle_zen_mode(self):
        self.is_zen_mode = not self.is_zen_mode
        if self.is_zen_mode:
            self.top_bar.pack_forget()
        else:
            self.top_bar.pack(fill=tk.X, side=tk.TOP, before=self.content_frame)

    def change_font_size(self, delta):
        new_size = self.font_size + delta
        if 11 <= new_size <= 28:
            self.font_size = new_size
            self.text_editor.configure(font=("Segoe UI", self.font_size))

    def clear_text(self):
        self.text_editor.delete("1.0", tk.END)

    def clear_image(self):
        self.current_image = None
        self.current_image_data = None
        self.image_label.configure(
            image="", text="📷 Chưa có ảnh\nẤn Ctrl + V dán ảnh chụp màn hình"
        )

    def choose_image_file(self):
        path = filedialog.askopenfilename(
            title="Chọn hình ảnh",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("All files", "*.*")]
        )
        if path:
            try:
                img = Image.open(path)
                self.set_image(img)
                if self.active_tab == "text":
                    self.switch_tab("split")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể mở ảnh: {e}")

    def set_image(self, pil_image):
        self.current_image = pil_image
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        self.current_image_data = base64.b64encode(buf.getvalue()).decode("utf-8")
        self.render_image()

    def render_image(self):
        if not self.current_image:
            self.image_label.configure(
                image="", text="📷 Chưa có ảnh\nẤn Ctrl + V dán ảnh chụp màn hình"
            )
            return

        self.image_container.update_idletasks()
        w = max(100, self.image_container.winfo_width() - 8)
        h = max(80, self.image_container.winfo_height() - 8)

        img_copy = self.current_image.copy()
        if self.zoom_mode == "fit":
            img_copy.thumbnail((w, h), Image.Resampling.LANCZOS)
        
        self.tk_photo = ImageTk.PhotoImage(img_copy)
        self.image_label.configure(image=self.tk_photo, text="")

    def on_image_click(self, event):
        if not self.current_image:
            self.choose_image_file()
            return
        self.zoom_mode = "original" if self.zoom_mode == "fit" else "fit"
        self.render_image()

    def on_window_resize(self, event):
        if self.active_tab in ("image", "split") and self.current_image:
            self.render_image()

    def on_paste_global(self, event):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                self.set_image(img)
                if self.active_tab == "text":
                    self.switch_tab("split")
                return "break"
            elif isinstance(img, list) and img and os.path.isfile(img[0]):
                try:
                    pil_img = Image.open(img[0])
                    self.set_image(pil_img)
                    if self.active_tab == "text":
                        self.switch_tab("split")
                    return "break"
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def play_tts(self):
        text = self.text_editor.get("1.0", tk.END).strip()
        if not text:
            return

        def run_speech():
            try:
                clean = text.replace('"', ' ').replace("'", " ").replace("`", " ")[:600]
                ps = (
                    "Add-Type -AssemblyName System.Speech; "
                    "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    f"$synth.Speak('{clean}')"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

        threading.Thread(target=run_speech, daemon=True).start()

    def on_close(self):
        self.save_data()
        self.root.destroy()
        sys.exit(0)


def main():
    root = tk.Tk()
    app = IELTSCornerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
