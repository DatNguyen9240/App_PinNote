"""
IELTS Corner - Desktop Widget (Phiên bản Tối Giản + Highlight + Hoàn Tác Ctrl + Z)
- Hỗ trợ hoàn tác (Ctrl + Z): Khi vừa highlight xong, ấn Ctrl + Z sẽ mất màu highlight ngay lập tức!
- Hỗ trợ làm lại (Ctrl + Y hoặc Ctrl + Shift + Z).
- Chức năng Highlight: Màu Vàng 🟡, Xanh lá 🟢, Hồng 🌸, Xanh lam 🔵.
- Phím tắt Ctrl + H để tô màu tức thì đoạn chữ đang chọn.
- Menu chuột phải có đầy đủ tùy chọn màu highlight & xóa highlight.
- Lưu lại toàn bộ các đoạn đã highlight khi tắt/mở app.
- Thiết kế Zen Mode tối giản 100% diện tích cho nội dung.
- Always-on-top: Luôn nổi trên Word, PDF, Chrome, Desktop.
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
        self.saved_highlights = []

        # Lịch sử hoàn tác (Undo/Redo) cho cả Highlight và Text
        self.action_history = []
        self.redo_history = []
        self.hl_counter = 0

        # Đọc dữ liệu
        self.load_data()

        # Xây dựng giao diện tối giản
        self.create_minimal_ui()

        # Cấu hình màu highlight cho Text widget
        self.setup_highlight_tags()

        # Áp dụng highlights đã lưu
        self.apply_saved_highlights()

        # Phím tắt toàn cục
        self.root.bind("<Control-v>", self.on_paste_global)
        self.root.bind("<Control-V>", self.on_paste_global)
        self.root.bind("<Control-h>", lambda e: self.highlight_selection("yellow"))
        self.root.bind("<Control-H>", lambda e: self.highlight_selection("yellow"))
        self.root.bind("<Control-z>", self.on_undo)
        self.root.bind("<Control-Z>", self.on_undo)
        self.root.bind("<Control-y>", self.on_redo)
        self.root.bind("<Control-Y>", self.on_redo)
        self.root.bind("<Control-plus>", lambda e: self.change_font_size(2))
        self.root.bind("<Control-equal>", lambda e: self.change_font_size(2))
        self.root.bind("<Control-minus>", lambda e: self.change_font_size(-2))
        self.root.bind("<Control-d>", lambda e: self.play_tts())
        self.root.bind("<Control-D>", lambda e: self.play_tts())

        # Gắn phím tắt trực tiếp lên Text editor để chặn Ctrl+Z mặc định
        self.text_editor.bind("<Control-z>", self.on_undo)
        self.text_editor.bind("<Control-Z>", self.on_undo)
        self.text_editor.bind("<Control-y>", self.on_redo)
        self.text_editor.bind("<Control-Y>", self.on_redo)
        self.text_editor.bind("<Key>", self.on_key_press)

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
            "Chào bạn! Ứng dụng đã hỗ trợ tính năng Highlight và Hoàn tác (Undo):\n\n"
            "• Bôi đen chữ rồi ấn Ctrl + H để tô màu vàng.\n"
            "• Ấn Ctrl + Z ngay sau khi highlight thì màu tô sẽ biến mất ngay lập tức!\n"
            "• Ấn Ctrl + Y để làm lại (Redo) thao tác vừa hoàn tác.\n"
            "• Nhấp chuột phải để chọn các màu khác: Vàng 🟡, Xanh 🟢, Hồng 🌸, Xanh lam 🔵.\n"
            "• Các đoạn highlight sẽ được lưu tự động, mở lại không bị mất.\n"
            "• Bấm 🌓 ở góc trên để xem song song cả đề bài và bài làm."
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
                    self.saved_highlights = data.get("highlights", [])

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

            # Lấy toàn bộ các đoạn highlight
            highlights = []
            for color in ["yellow", "green", "pink", "blue"]:
                tag_name = f"hl_{color}"
                ranges = self.text_editor.tag_ranges(tag_name)
                for i in range(0, len(ranges), 2):
                    highlights.append({
                        "color": color,
                        "start": str(ranges[i]),
                        "end": str(ranges[i+1])
                    })

            data = {
                "geometry": geom,
                "text": text_content,
                "font_size": self.font_size,
                "active_tab": self.active_tab,
                "is_topmost": self.is_topmost,
                "is_zen_mode": self.is_zen_mode,
                "highlights": highlights,
                "image_base64": self.current_image_data or ""
            }
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def setup_highlight_tags(self):
        self.text_editor.tag_configure("hl_yellow", background="#fef08a", foreground="#0f172a")
        self.text_editor.tag_configure("hl_green", background="#bbf7d0", foreground="#0f172a")
        self.text_editor.tag_configure("hl_pink", background="#fbcfe8", foreground="#0f172a")
        self.text_editor.tag_configure("hl_blue", background="#bae6fd", foreground="#0f172a")

    def apply_saved_highlights(self):
        for hl in self.saved_highlights:
            try:
                color = hl.get("color", "yellow")
                start = hl.get("start")
                end = hl.get("end")
                if start and end:
                    self.text_editor.tag_add(f"hl_{color}", start, end)
            except Exception:
                pass

    def on_key_press(self, event):
        # Theo dõi gõ chữ để phối hợp với lịch sử Ctrl + Z
        if event.state & 4: # Nhấn Ctrl
            return
        if (event.char and event.char.isprintable()) or event.keysym in ("BackSpace", "Delete", "Return"):
            if not self.action_history or self.action_history[-1] != "text":
                self.action_history.append("text")
                self.redo_history.clear()

    def highlight_selection(self, color="yellow"):
        try:
            sel_start = self.text_editor.index(tk.SEL_FIRST)
            sel_end = self.text_editor.index(tk.SEL_LAST)
        except tk.TclError:
            return

        self.hl_counter += 1
        ms = f"hl_s_{self.hl_counter}"
        me = f"hl_e_{self.hl_counter}"
        self.text_editor.mark_set(ms, sel_start)
        self.text_editor.mark_set(me, sel_end)
        self.text_editor.mark_gravity(ms, tk.LEFT)
        self.text_editor.mark_gravity(me, tk.RIGHT)

        tag_to_apply = f"hl_{color}"
        current_tags = self.text_editor.tag_names(sel_start)

        if tag_to_apply in current_tags:
            # Gỡ màu (toggle off)
            self.text_editor.tag_remove(tag_to_apply, sel_start, sel_end)
            self.action_history.append({
                "type": "highlight",
                "mark_start": ms,
                "mark_end": me,
                "added_color": None,
                "removed_color": color,
                "old_tags": []
            })
        else:
            old_tags = []
            for c in ["yellow", "green", "pink", "blue"]:
                tname = f"hl_{c}"
                if tname in current_tags:
                    old_tags.append(c)
                    self.text_editor.tag_remove(tname, sel_start, sel_end)
            
            self.text_editor.tag_add(tag_to_apply, sel_start, sel_end)
            self.action_history.append({
                "type": "highlight",
                "mark_start": ms,
                "mark_end": me,
                "added_color": color,
                "removed_color": None,
                "old_tags": old_tags
            })

        self.redo_history.clear()
        self.save_data()

    def remove_highlight_selection(self):
        try:
            sel_start = self.text_editor.index(tk.SEL_FIRST)
            sel_end = self.text_editor.index(tk.SEL_LAST)
        except tk.TclError:
            return

        current_tags = self.text_editor.tag_names(sel_start)
        old_tags = []
        for c in ["yellow", "green", "pink", "blue"]:
            tname = f"hl_{c}"
            if tname in current_tags:
                old_tags.append(c)
                self.text_editor.tag_remove(tname, sel_start, sel_end)

        if old_tags:
            self.hl_counter += 1
            ms = f"hl_s_{self.hl_counter}"
            me = f"hl_e_{self.hl_counter}"
            self.text_editor.mark_set(ms, sel_start)
            self.text_editor.mark_set(me, sel_end)
            self.text_editor.mark_gravity(ms, tk.LEFT)
            self.text_editor.mark_gravity(me, tk.RIGHT)

            self.action_history.append({
                "type": "highlight",
                "mark_start": ms,
                "mark_end": me,
                "added_color": None,
                "removed_color": None,
                "old_tags": old_tags
            })
            self.redo_history.clear()
            self.save_data()

    def on_undo(self, event=None):
        """Khi ấn Ctrl + Z: Hoàn tác highlight nếu vừa highlight xong, hoặc hoàn tác chữ"""
        if self.action_history and isinstance(self.action_history[-1], dict) and self.action_history[-1].get("type") == "highlight":
            action = self.action_history.pop()
            try:
                start = self.text_editor.index(action["mark_start"])
                end = self.text_editor.index(action["mark_end"])

                # Nếu vừa tô màu thì gỡ màu bỏ đi
                if action.get("added_color"):
                    self.text_editor.tag_remove(f"hl_{action['added_color']}", start, end)
                
                # Nếu vừa gỡ màu thì tô lại
                if action.get("removed_color"):
                    self.text_editor.tag_add(f"hl_{action['removed_color']}", start, end)

                # Khôi phục các màu cũ trước đó nếu có
                for c in action.get("old_tags", []):
                    self.text_editor.tag_add(f"hl_{c}", start, end)

                self.redo_history.append(action)
                self.save_data()
            except Exception:
                pass
            return "break"
        else:
            if self.action_history and self.action_history[-1] == "text":
                self.action_history.pop()
            try:
                self.text_editor.edit_undo()
                self.save_data()
            except tk.TclError:
                pass
            return "break"

    def on_redo(self, event=None):
        """Khi ấn Ctrl + Y hoặc Ctrl + Shift + Z: Làm lại thao tác vừa hoàn tác"""
        if self.redo_history and isinstance(self.redo_history[-1], dict) and self.redo_history[-1].get("type") == "highlight":
            action = self.redo_history.pop()
            try:
                start = self.text_editor.index(action["mark_start"])
                end = self.text_editor.index(action["mark_end"])

                for c in ["yellow", "green", "pink", "blue"]:
                    self.text_editor.tag_remove(f"hl_{c}", start, end)

                if action.get("added_color"):
                    self.text_editor.tag_add(f"hl_{action['added_color']}", start, end)

                self.action_history.append(action)
                self.save_data()
            except Exception:
                pass
            return "break"
        else:
            try:
                self.text_editor.edit_redo()
                self.save_data()
            except tk.TclError:
                pass
            return "break"

    def create_minimal_ui(self):
        # 1. THANH CÔNG CỤ SIÊU MỎNG (Chỉ cao 26px)
        self.top_bar = tk.Frame(self.root, bg="#f8fafc", height=26)
        if not self.is_zen_mode:
            self.top_bar.pack(fill=tk.X, side=tk.TOP)

        # Tabs siêu nhỏ
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

        # Thao tác bên phải: 🖍️ Highlight | 🔊 Đọc | 📌 Ghim | ⋯ Menu
        actions_frame = tk.Frame(self.top_bar, bg="#f8fafc")
        actions_frame.pack(side=tk.RIGHT, padx=6)

        # Nút Highlight nhanh màu vàng
        self.btn_hl_icon = tk.Label(
            actions_frame, text="🖍️", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#334155", padx=4, pady=2, cursor="hand2"
        )
        self.btn_hl_icon.pack(side=tk.LEFT, padx=2)
        self.btn_hl_icon.bind("<Button-1>", lambda e: self.highlight_selection("yellow"))

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

        # 2. KHUNG NỘI DUNG CHÍNH (TRÀN VIỀN 100%)
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

        # Khung Chữ (Tràn viền, không viền đen)
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

        # Rê chuột lên đỉnh để hiện thanh công cụ khi ở chế độ Zen Mode
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
        
        # Nhóm Highlight
        hl_menu = tk.Menu(self.menu, tearoff=0, font=("Segoe UI", 9))
        hl_menu.add_command(label="🟡 Màu Vàng (Ctrl+H)", command=lambda: self.highlight_selection("yellow"))
        hl_menu.add_command(label="🟢 Màu Xanh lá", command=lambda: self.highlight_selection("green"))
        hl_menu.add_command(label="🌸 Màu Hồng", command=lambda: self.highlight_selection("pink"))
        hl_menu.add_command(label="🔵 Màu Xanh lam", command=lambda: self.highlight_selection("blue"))
        hl_menu.add_separator()
        hl_menu.add_command(label="⚪ Bỏ Highlight đoạn chọn", command=self.remove_highlight_selection)
        
        self.menu.add_cascade(label="🖍️ Tô màu Highlight", menu=hl_menu)
        self.menu.add_command(label="↩️ Hoàn tác / Undo (Ctrl+Z)", command=self.on_undo)
        self.menu.add_command(label="🔊 Nghe đọc đoạn văn (Ctrl+D)", command=self.play_tts)
        self.menu.add_separator()

        # Chế độ xem
        self.menu.add_command(label="📝 Chỉ xem Văn bản", command=lambda: self.switch_tab("text"))
        self.menu.add_command(label="🖼️ Chỉ xem Hình ảnh", command=lambda: self.switch_tab("image"))
        self.menu.add_command(label="🌓 Xem Cả hai (Song song)", command=lambda: self.switch_tab("split"))
        self.menu.add_separator()

        # Cỡ chữ
        self.menu.add_command(label="➕ Phóng to chữ (Ctrl +)", command=lambda: self.change_font_size(2))
        self.menu.add_command(label="➖ Thu nhỏ chữ (Ctrl -)", command=lambda: self.change_font_size(-2))
        self.menu.add_separator()

        # Tùy chọn khác
        self.menu.add_command(label="📁 Tải file ảnh từ máy...", command=self.choose_image_file)
        self.menu.add_command(label="📌 Bật/Tắt Ghim trên cùng", command=self.toggle_pin)
        self.menu.add_command(
            label="✨ Ẩn/Hiện thanh công cụ (Zen Mode)", command=self.toggle_zen_mode
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
