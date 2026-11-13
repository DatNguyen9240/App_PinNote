"""
IELTS Corner - Desktop Widget (Hỗ trợ Dịch Song Ngữ Đối Ứng 2 Chiều + Tách Note + Highlight)
- Bôi đen chữ / câu tiếng Anh ➔ Tự động tìm, làm sáng và cuộn đến câu dịch tiếng Việt đối lại!
- Bôi đen chữ / câu tiếng Việt ➔ Tự động tìm, làm sáng và cuộn đến câu tiếng Anh gốc tương ứng!
- Nắm kéo Note ra ngoài màn hình (Tear-off tab): Thả ra ngoài để tách thành cửa sổ riêng biệt nổi độc lập!
- Nút tách nhanh ↗ và menu chuột phải "Tách thành cửa sổ riêng".
- Nút gộp lại ↙ để đưa Note trở về cửa sổ chính bất cứ lúc nào.
- Dịch chuẩn ngữ cảnh IELTS (Ctrl + T): Dịch văn phong học thuật, tra cứu từ loại và các nét nghĩa theo ngữ cảnh.
- Tạo và quản lý nhiều Note: Note 1, Note 2, Note 3... (Ctrl + N, Ctrl + Tab).
- Highlight 4 màu + Hoàn tác Ctrl + Z tức thì: Vừa tô màu xong ấn Ctrl + Z mất màu ngay mà không mất chữ.
- Always-on-top: Luôn nổi trên Word, PDF Cambridge, Chrome, Desktop ở bất cứ đâu.
"""

import sys
import os
import json
import base64
import io
import time
import threading
import subprocess
import urllib.request
import urllib.parse
import socket
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageGrab

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ielts_desktop_data.json")

# Khóa đơn phiên (Single-instance lock) ngăn việc mở nhiều cửa sổ trùng đè lên nhau
_instance_socket = None

def ensure_single_instance():
    global _instance_socket
    try:
        _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _instance_socket.bind(("127.0.0.1", 48829))
        return True
    except socket.error:
        return False


def fetch_context_translation(query_text, on_success, on_error):
    """Gửi yêu cầu dịch chuẩn ngữ cảnh qua Google Neural Translation API (không cần API key)."""
    def worker():
        try:
            url = (
                "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=vi&dt=t&dt=bd&dt=rm&q="
                + urllib.parse.quote(query_text)
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_segments = []
                if data and len(data) > 0 and data[0]:
                    for s in data[0]:
                        if s and len(s) > 1 and s[0] and s[1]:
                            raw_segments.append({"en": s[1], "vi": s[0]})

                extra = ""
                if len(data) > 1 and data[1]:
                    extra_lines = []
                    for pos in data[1]:
                        part_name = pos[0]
                        meanings = ", ".join(pos[1][:5]) if len(pos) > 1 else ""
                        extra_lines.append(f"• ({part_name}) {meanings}")
                    if extra_lines:
                        extra = "\n\n📚 Các nét nghĩa theo ngữ cảnh:\n" + "\n".join(extra_lines)

                on_success(raw_segments, extra)
        except Exception:
            on_error("Không thể kết nối máy chủ dịch (vui lòng kiểm tra kết nối mạng).")

    threading.Thread(target=worker, daemon=True).start()


def speak_english_text(text):
    """Phát âm giọng đọc bản xứ qua Windows Speech Synthesis."""
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


# ==============================================================================
# LỚP CỬA SỔ NOTE TÁCH RỜI (DETACHED NOTE WINDOW)
# ==============================================================================
class DetachedNoteWindow:
    def __init__(self, main_app, note, x=None, y=None):
        self.main_app = main_app
        self.note = note
        self.note_id = str(note.get("id"))

        self.top = tk.Toplevel(main_app.root)
        self.top.configure(bg="#ffffff")
        self.update_title()

        # Always-on-top
        self.is_topmost = True
        self.top.attributes("-topmost", True)

        # Cỡ cửa sổ
        w, h = 420, 520
        if x is not None and y is not None:
            sw = self.top.winfo_screenwidth()
            sh = self.top.winfo_screenheight()
            sx = max(10, min(x, sw - w - 10))
            sy = max(10, min(y, sh - h - 40))
            self.top.geometry(f"{w}x{h}+{sx}+{sy}")
        else:
            mx = main_app.root.winfo_x() + 40
            my = main_app.root.winfo_y() + 40
            self.top.geometry(f"{w}x{h}+{mx}+{my}")

        self.font_size = main_app.font_size
        self.zoom_mode = "fit"
        self.active_tab = note.get("active_tab", "text")
        self.current_image = None
        self.current_image_data = note.get("image_base64", "")
        self.action_history = []
        self.redo_history = []
        self.hl_counter = 0

        # Danh sách đối ứng song ngữ 2 chiều
        self.align_segments = []
        self.is_syncing_align = False

        self.create_ui()
        self.setup_highlight_tags()
        self.load_content()
        self.setup_shortcuts()

        self.top.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_title(self):
        title = self.note.get("title", "Note")
        self.top.title(f"IELTS Corner - {title}")

    def create_ui(self):
        self.top_bar = tk.Frame(self.top, bg="#f8fafc", height=28)
        self.top_bar.pack(fill=tk.X, side=tk.TOP)

        mode_frame = tk.Frame(self.top_bar, bg="#f8fafc")
        mode_frame.pack(side=tk.LEFT, padx=3, pady=2)

        self.btn_mode_text = tk.Label(
            mode_frame, text="📝", font=("Segoe UI", 8),
            bg="#ffffff" if self.active_tab == "text" else "#f8fafc",
            fg="#4f46e5" if self.active_tab == "text" else "#64748b",
            padx=4, pady=2, cursor="hand2"
        )
        self.btn_mode_text.pack(side=tk.LEFT, padx=1)
        self.btn_mode_text.bind("<Button-1>", lambda e: self.switch_tab("text"))

        self.btn_mode_image = tk.Label(
            mode_frame, text="🖼️", font=("Segoe UI", 8),
            bg="#ffffff" if self.active_tab == "image" else "#f8fafc",
            fg="#4f46e5" if self.active_tab == "image" else "#64748b",
            padx=4, pady=2, cursor="hand2"
        )
        self.btn_mode_image.pack(side=tk.LEFT, padx=1)
        self.btn_mode_image.bind("<Button-1>", lambda e: self.switch_tab("image"))

        self.btn_mode_split = tk.Label(
            mode_frame, text="🌓", font=("Segoe UI", 8),
            bg="#ffffff" if self.active_tab == "split" else "#f8fafc",
            fg="#4f46e5" if self.active_tab == "split" else "#64748b",
            padx=4, pady=2, cursor="hand2"
        )
        self.btn_mode_split.pack(side=tk.LEFT, padx=1)
        self.btn_mode_split.bind("<Button-1>", lambda e: self.switch_tab("split"))

        title_box = tk.Frame(self.top_bar, bg="#f8fafc")
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        title_text = self.note.get("title", "Note")
        disp_title = title_text if len(title_text) <= 12 else title_text[:11] + "…"
        self.lbl_title = tk.Label(
            title_box, text=f"📑 {disp_title}", font=("Segoe UI", 8, "bold"),
            bg="#eff6ff", fg="#2563eb", padx=6, pady=1, cursor="hand2",
            relief="groove", bd=1
        )
        self.lbl_title.pack(side=tk.LEFT)
        self.lbl_title.bind("<Double-Button-1>", lambda e: self.rename_note())

        actions_frame = tk.Frame(self.top_bar, bg="#f8fafc")
        actions_frame.pack(side=tk.RIGHT, padx=3)

        self.btn_trans_icon = tk.Label(
            actions_frame, text="🌐", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#4f46e5", padx=3, pady=2, cursor="hand2"
        )
        self.btn_trans_icon.pack(side=tk.LEFT, padx=1)
        self.btn_trans_icon.bind("<Button-1>", lambda e: self.translate_context())

        self.btn_hl_icon = tk.Label(
            actions_frame, text="🖍️", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#334155", padx=3, pady=2, cursor="hand2"
        )
        self.btn_hl_icon.pack(side=tk.LEFT, padx=1)
        self.btn_hl_icon.bind("<Button-1>", lambda e: self.highlight_selection("yellow"))

        self.btn_tts_icon = tk.Label(
            actions_frame, text="🔊", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#334155", padx=3, pady=2, cursor="hand2"
        )
        self.btn_tts_icon.pack(side=tk.LEFT, padx=1)
        self.btn_tts_icon.bind("<Button-1>", lambda e: self.play_tts())

        self.btn_pin_icon = tk.Label(
            actions_frame, text="📌" if self.is_topmost else "📍", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#4f46e5" if self.is_topmost else "#94a3b8",
            padx=3, pady=2, cursor="hand2"
        )
        self.btn_pin_icon.pack(side=tk.LEFT, padx=1)
        self.btn_pin_icon.bind("<Button-1>", lambda e: self.toggle_pin())

        self.btn_reattach = tk.Label(
            actions_frame, text="↙", font=("Segoe UI", 9, "bold"),
            bg="#f8fafc", fg="#059669", padx=3, pady=2, cursor="hand2"
        )
        self.btn_reattach.pack(side=tk.LEFT, padx=1)
        self.btn_reattach.bind("<Button-1>", lambda e: self.reattach_to_main())

        self.content_frame = tk.Frame(self.top, bg="#ffffff")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.image_container = tk.Frame(self.content_frame, bg="#f8fafc")
        self.image_label = tk.Label(
            self.image_container,
            text="📷 Chưa có ảnh\nẤn Ctrl + V dán ảnh chụp màn hình",
            bg="#f8fafc", fg="#94a3b8",
            font=("Segoe UI", 11)
        )
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.image_label.bind("<Button-1>", self.on_image_click)

        self.text_container = tk.Frame(self.content_frame, bg="#ffffff")
        self.text_editor = tk.Text(
            self.text_container,
            font=("Segoe UI", self.font_size),
            wrap=tk.WORD,
            undo=True,
            maxundo=-1,
            autoseparators=True,
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#4f46e5",
            selectbackground="#c7d2fe",
            selectforeground="#1e1b4b"
        )
        self.text_editor.pack(fill=tk.BOTH, expand=True)

        # Khung dịch chuẩn ngữ cảnh đối ứng song ngữ
        self.trans_panel = tk.Frame(self.top, bg="#f8fafc", relief="solid", bd=1)

        trans_header = tk.Frame(self.trans_panel, bg="#f1f5f9", height=24)
        trans_header.pack(fill=tk.X, side=tk.TOP)

        lbl_trans_title = tk.Label(
            trans_header, text="🌐 Dịch đối ứng song ngữ (Bôi đen câu/từ để tìm đối ứng 2 chiều)",
            font=("Segoe UI", 8, "bold"), bg="#f1f5f9", fg="#334155", padx=6, pady=2
        )
        lbl_trans_title.pack(side=tk.LEFT)

        btn_close_trans = tk.Label(
            trans_header, text="✕", font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9", fg="#64748b", padx=6, cursor="hand2"
        )
        btn_close_trans.pack(side=tk.RIGHT)
        btn_close_trans.bind("<Button-1>", lambda e: self.close_translation())

        btn_copy_trans = tk.Label(
            trans_header, text="📋 Sao chép", font=("Segoe UI", 8),
            bg="#f1f5f9", fg="#4f46e5", padx=6, cursor="hand2"
        )
        btn_copy_trans.pack(side=tk.RIGHT)
        btn_copy_trans.bind("<Button-1>", lambda e: self.copy_translation())

        self.trans_text = tk.Text(
            self.trans_panel,
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            relief="flat",
            bd=0,
            bg="#f8fafc",
            fg="#0f172a",
            padx=8,
            pady=6,
            height=5
        )
        self.trans_text.pack(fill=tk.BOTH, expand=True)

        self.create_context_menu()

    def setup_shortcuts(self):
        self.top.bind("<Control-v>", self.on_paste_global)
        self.top.bind("<Control-V>", self.on_paste_global)
        self.top.bind("<Control-h>", lambda e: self.highlight_selection("yellow"))
        self.top.bind("<Control-H>", lambda e: self.highlight_selection("yellow"))
        self.top.bind("<Control-t>", lambda e: self.translate_context())
        self.top.bind("<Control-T>", lambda e: self.translate_context())
        self.top.bind("<Control-z>", self.on_undo)
        self.top.bind("<Control-Z>", self.on_undo)
        self.top.bind("<Control-y>", self.on_redo)
        self.top.bind("<Control-Y>", self.on_redo)
        self.top.bind("<Control-d>", lambda e: self.play_tts())
        self.top.bind("<Control-D>", lambda e: self.play_tts())
        self.top.bind("<Control-plus>", lambda e: self.change_font_size(2))
        self.top.bind("<Control-equal>", lambda e: self.change_font_size(2))
        self.top.bind("<Control-minus>", lambda e: self.change_font_size(-2))
        self.top.bind("<Escape>", lambda e: self.close_translation())

        self.text_editor.bind("<Control-z>", self.on_undo)
        self.text_editor.bind("<Control-Z>", self.on_undo)
        self.text_editor.bind("<Control-y>", self.on_redo)
        self.text_editor.bind("<Control-Y>", self.on_redo)
        self.text_editor.bind("<Key>", self.on_key_press)

        # Lắng nghe bôi đen / chọn chữ 2 chiều (tiếng Anh ➔ tiếng Việt và ngược lại)
        self.text_editor.bind("<<Selection>>", self.on_en_selection_change)
        self.text_editor.bind("<ButtonRelease-1>", self.on_en_selection_change)
        self.text_editor.bind("<KeyRelease>", self.on_en_selection_change)

        self.trans_text.bind("<<Selection>>", self.on_vi_selection_change)
        self.trans_text.bind("<ButtonRelease-1>", self.on_vi_selection_change)
        self.trans_text.bind("<KeyRelease>", self.on_vi_selection_change)

        self.top.bind("<Button-3>", self.show_context_menu)
        self.top.bind("<Configure>", self.on_window_resize)

    def setup_highlight_tags(self):
        self.text_editor.tag_configure("hl_yellow", background="#fef08a", foreground="#0f172a")
        self.text_editor.tag_configure("hl_green", background="#bbf7d0", foreground="#0f172a")
        self.text_editor.tag_configure("hl_pink", background="#fbcfe8", foreground="#0f172a")
        self.text_editor.tag_configure("hl_blue", background="#bae6fd", foreground="#0f172a")

        # Tag đối ứng song ngữ 2 chiều (Warm luminous tone)
        self.text_editor.tag_configure("align_match", background="#fed7aa", foreground="#7c2d12")
        self.trans_text.tag_configure("align_match", background="#fed7aa", foreground="#7c2d12")

    def load_content(self):
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", self.note.get("text", ""))

        for hl in self.note.get("highlights", []):
            try:
                c = hl.get("color", "yellow")
                s = hl.get("start")
                e = hl.get("end")
                if s and e:
                    self.text_editor.tag_add(f"hl_{c}", s, e)
            except Exception:
                pass

        img_b64 = self.note.get("image_base64", "")
        if img_b64:
            try:
                img_bytes = base64.b64decode(img_b64)
                self.current_image = Image.open(io.BytesIO(img_bytes))
                self.current_image_data = img_b64
            except Exception:
                self.current_image = None
                self.current_image_data = None
        else:
            self.current_image = None
            self.current_image_data = None

        self.switch_tab(self.note.get("active_tab", "text"))

    def sync_to_note(self):
        self.note["text"] = self.text_editor.get("1.0", tk.END).strip()
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
        self.note["highlights"] = highlights
        self.note["image_base64"] = self.current_image_data or ""
        self.note["active_tab"] = self.active_tab
        self.main_app.save_data()

    def on_key_press(self, event):
        if event.state & 4:
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
        self.sync_to_note()

    def on_undo(self, event=None):
        if self.action_history and isinstance(self.action_history[-1], dict) and self.action_history[-1].get("type") == "highlight":
            action = self.action_history.pop()
            try:
                start = self.text_editor.index(action["mark_start"])
                end = self.text_editor.index(action["mark_end"])

                if action.get("added_color"):
                    self.text_editor.tag_remove(f"hl_{action['added_color']}", start, end)

                if action.get("removed_color"):
                    self.text_editor.tag_add(f"hl_{action['removed_color']}", start, end)

                for c in action.get("old_tags", []):
                    self.text_editor.tag_add(f"hl_{c}", start, end)

                self.redo_history.append(action)
                self.sync_to_note()
            except Exception:
                pass
            return "break"
        else:
            try:
                self.text_editor.edit_undo()
                if self.action_history and self.action_history[-1] == "text":
                    self.action_history.pop()
                    self.redo_history.append("text")
                self.sync_to_note()
            except tk.TclError:
                pass
            return "break"

    def on_redo(self, event=None):
        if self.redo_history:
            action = self.redo_history.pop()
            if isinstance(action, dict) and action.get("type") == "highlight":
                try:
                    start = self.text_editor.index(action["mark_start"])
                    end = self.text_editor.index(action["mark_end"])
                    for c in action.get("old_tags", []):
                        self.text_editor.tag_remove(f"hl_{c}", start, end)
                    if action.get("added_color"):
                        self.text_editor.tag_add(f"hl_{action['added_color']}", start, end)
                    if action.get("removed_color"):
                        self.text_editor.tag_remove(f"hl_{action['removed_color']}", start, end)
                    self.action_history.append(action)
                    self.sync_to_note()
                except Exception:
                    pass
            elif action == "text":
                try:
                    self.text_editor.edit_redo()
                    self.action_history.append("text")
                    self.sync_to_note()
                except tk.TclError:
                    pass
            return "break"

    # --- DỊCH CHUẨN NGỮ CẢNH VÀ TÌM ĐỐI ỨNG SONG NGỮ 2 CHIỀU ---
    def translate_context(self):
        try:
            query_text = self.text_editor.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
        except tk.TclError:
            query_text = ""

        if not query_text:
            query_text = self.text_editor.get("1.0", tk.END).strip()

        if not query_text:
            return

        self.show_translation_loading("⏳ Đang phân tích ngữ cảnh và dịch đối ứng song ngữ...")
        fetch_context_translation(
            query_text,
            on_success=lambda raw_segs, extra: self.top.after(0, lambda: self.display_aligned_translation(raw_segs, extra)),
            on_error=lambda err: self.top.after(0, lambda: self.show_translation_error(err))
        )

    def show_translation_loading(self, text):
        if not self.trans_panel.winfo_ismapped():
            self.trans_panel.pack(fill=tk.X, side=tk.BOTTOM, before=self.content_frame)
        self.trans_text.delete("1.0", tk.END)
        self.trans_text.insert("1.0", text)

    def show_translation_error(self, err):
        self.trans_text.delete("1.0", tk.END)
        self.trans_text.insert("1.0", err)

    def display_aligned_translation(self, raw_segments, extra):
        self.align_segments = []
        self.trans_text.delete("1.0", tk.END)

        curr_en_search = "1.0"
        ts = int(time.time() * 1000)

        for i, seg in enumerate(raw_segments):
            clean_en = seg["en"].strip()
            ms_en = f"det_en_s_{i}_{ts}"
            me_en = f"det_en_e_{i}_{ts}"

            if clean_en:
                pos = self.text_editor.search(clean_en, curr_en_search, tk.END)
                if not pos:
                    prefix = clean_en[:min(25, len(clean_en))]
                    pos = self.text_editor.search(prefix, curr_en_search, tk.END)
                if pos:
                    end_pos = f"{pos}+{len(clean_en)}c"
                    self.text_editor.mark_set(ms_en, pos)
                    self.text_editor.mark_set(me_en, end_pos)
                    self.text_editor.mark_gravity(ms_en, tk.LEFT)
                    self.text_editor.mark_gravity(me_en, tk.RIGHT)
                    curr_en_search = end_pos
                else:
                    ms_en, me_en = None, None
            else:
                ms_en, me_en = None, None

            ms_vi = f"det_vi_s_{i}_{ts}"
            me_vi = f"det_vi_e_{i}_{ts}"
            vi_start = self.trans_text.index(tk.INSERT)
            self.trans_text.insert(tk.END, seg["vi"])
            vi_end = self.trans_text.index(f"{tk.INSERT}-1c")

            self.trans_text.mark_set(ms_vi, vi_start)
            self.trans_text.mark_set(me_vi, vi_end)
            self.trans_text.mark_gravity(ms_vi, tk.LEFT)
            self.trans_text.mark_gravity(me_vi, tk.RIGHT)

            if ms_en and me_en:
                self.align_segments.append({
                    "ms_en": ms_en,
                    "me_en": me_en,
                    "ms_vi": ms_vi,
                    "me_vi": me_vi,
                    "en": clean_en,
                    "vi": seg["vi"].strip()
                })

        if extra:
            self.trans_text.insert(tk.END, extra)

        if not self.trans_panel.winfo_ismapped():
            self.trans_panel.pack(fill=tk.X, side=tk.BOTTOM, before=self.content_frame)

        self.on_en_selection_change()

    def on_en_selection_change(self, event=None):
        if self.is_syncing_align or not getattr(self, "align_segments", None):
            return
        try:
            sel_s = self.text_editor.index(tk.SEL_FIRST)
            sel_e = self.text_editor.index(tk.SEL_LAST)
        except tk.TclError:
            sel_s = self.text_editor.index(tk.INSERT)
            sel_e = f"{sel_s}+1c"

        self.is_syncing_align = True
        try:
            self.trans_text.tag_remove("align_match", "1.0", tk.END)
            first_match = None
            for seg in self.align_segments:
                try:
                    s_en = self.text_editor.index(seg["ms_en"])
                    e_en = self.text_editor.index(seg["me_en"])
                    if self.text_editor.compare(sel_s, "<", e_en) and self.text_editor.compare(sel_e, ">", s_en):
                        vi_s = self.trans_text.index(seg["ms_vi"])
                        vi_e = self.trans_text.index(seg["me_vi"])
                        self.trans_text.tag_add("align_match", vi_s, vi_e)
                        if not first_match:
                            first_match = vi_s
                except Exception:
                    pass
            if first_match:
                self.trans_text.see(first_match)
        finally:
            self.is_syncing_align = False

    def on_vi_selection_change(self, event=None):
        if self.is_syncing_align or not getattr(self, "align_segments", None):
            return
        try:
            sel_s = self.trans_text.index(tk.SEL_FIRST)
            sel_e = self.trans_text.index(tk.SEL_LAST)
        except tk.TclError:
            sel_s = self.trans_text.index(tk.INSERT)
            sel_e = f"{sel_s}+1c"

        self.is_syncing_align = True
        try:
            self.text_editor.tag_remove("align_match", "1.0", tk.END)
            first_match = None
            for seg in self.align_segments:
                try:
                    s_vi = self.trans_text.index(seg["ms_vi"])
                    e_vi = self.trans_text.index(seg["me_vi"])
                    if self.trans_text.compare(sel_s, "<", e_vi) and self.trans_text.compare(sel_e, ">", s_vi):
                        en_s = self.text_editor.index(seg["ms_en"])
                        en_e = self.text_editor.index(seg["me_en"])
                        self.text_editor.tag_add("align_match", en_s, en_e)
                        if not first_match:
                            first_match = en_s
                except Exception:
                    pass
            if first_match:
                self.text_editor.see(first_match)
        finally:
            self.is_syncing_align = False

    def close_translation(self):
        self.text_editor.tag_remove("align_match", "1.0", tk.END)
        self.trans_text.tag_remove("align_match", "1.0", tk.END)
        if self.trans_panel.winfo_ismapped():
            self.trans_panel.pack_forget()

    def copy_translation(self):
        content = self.trans_text.get("1.0", tk.END).strip()
        if content:
            self.top.clipboard_clear()
            self.top.clipboard_append(content)

    def play_tts(self):
        text = self.text_editor.get("1.0", tk.END).strip()
        speak_english_text(text)

    def switch_tab(self, tab):
        self.active_tab = tab
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
        self.top.attributes("-topmost", self.is_topmost)
        self.btn_pin_icon.configure(
            text="📌" if self.is_topmost else "📍",
            fg="#4f46e5" if self.is_topmost else "#94a3b8"
        )

    def change_font_size(self, delta):
        new_size = self.font_size + delta
        if 11 <= new_size <= 28:
            self.font_size = new_size
            self.text_editor.configure(font=("Segoe UI", self.font_size))

    def rename_note(self):
        old_title = self.note.get("title", "Note")
        new_title = simpledialog.askstring("Đổi tên Note", "Nhập tên mới cho Note:", initialvalue=old_title, parent=self.top)
        if new_title and new_title.strip():
            self.note["title"] = new_title.strip()
            self.update_title()
            disp_title = new_title if len(new_title) <= 12 else new_title[:11] + "…"
            self.lbl_title.configure(text=f"📑 {disp_title}")
            self.main_app.render_note_tabs()
            self.main_app.save_data()

    def reattach_to_main(self):
        self.sync_to_note()
        self.main_app.reattach_note(self.note_id)

    def on_close(self):
        self.sync_to_note()
        self.main_app.on_detached_window_closed(self.note_id)
        try:
            self.top.destroy()
        except Exception:
            pass

    def set_image(self, pil_image):
        self.current_image = pil_image
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        self.current_image_data = base64.b64encode(buf.getvalue()).decode("utf-8")
        self.render_image()
        self.sync_to_note()

    def render_image(self):
        if not self.current_image:
            self.image_label.configure(image="", text="📷 Chưa có ảnh\nẤn Ctrl + V dán ảnh chụp màn hình")
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
            path = filedialog.askopenfilename(title="Chọn ảnh", filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")])
            if path:
                try:
                    self.set_image(Image.open(path))
                except Exception:
                    pass
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
                    self.set_image(Image.open(img[0]))
                    if self.active_tab == "text":
                        self.switch_tab("split")
                    return "break"
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def create_context_menu(self):
        self.menu = tk.Menu(self.top, tearoff=0, font=("Segoe UI", 9))
        self.menu.add_command(label="🌐 Dịch song ngữ đối ứng (Ctrl+T)", command=self.translate_context)
        self.menu.add_command(label="🔊 Nghe đọc đoạn văn (Ctrl+D)", command=self.play_tts)
        self.menu.add_command(label="↙ Gộp lại vào cửa sổ chính", command=self.reattach_to_main)
        self.menu.add_separator()
        self.menu.add_command(label="🟡 Highlight Vàng (Ctrl+H)", command=lambda: self.highlight_selection("yellow"))
        self.menu.add_command(label="🟢 Highlight Xanh lá", command=lambda: self.highlight_selection("green"))
        self.menu.add_command(label="🌸 Highlight Hồng", command=lambda: self.highlight_selection("pink"))
        self.menu.add_command(label="🔵 Highlight Xanh lam", command=lambda: self.highlight_selection("blue"))
        self.menu.add_separator()
        self.menu.add_command(label="✏️ Đổi tên Note", command=self.rename_note)
        self.menu.add_command(label="📌 Bật/Tắt Ghim nổi", command=self.toggle_pin)

    def show_context_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()


# ==============================================================================
# LỚP ỨNG DỤNG CHÍNH (IELTS CORNER MAIN APP)
# ==============================================================================
class IELTSCornerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("IELTS Corner")
        self.root.configure(bg="#ffffff")

        # Always-on-top
        self.is_topmost = True
        self.root.attributes("-topmost", True)

        # Trạng thái chung
        self.font_size = 14
        self.zoom_mode = "fit"
        self.is_zen_mode = False
        self.active_tab = "text"
        self.current_image = None
        self.current_image_data = None
        self.saved_highlights = []

        # Quản lý nhiều Note
        self.notes = []
        self.active_note_id = "1"

        # Quản lý cửa sổ tách rời (Detached Windows) & Kéo thả tab
        self.detached_windows = {}
        self.tab_drag = None

        # Danh sách đối ứng song ngữ 2 chiều
        self.align_segments = []
        self.is_syncing_align = False

        # Lịch sử hoàn tác (Undo/Redo) cho Highlight và Text
        self.action_history = []
        self.redo_history = []
        self.hl_counter = 0

        # Đọc dữ liệu
        self.load_data()

        # Xây dựng giao diện tối giản
        self.create_minimal_ui()

        # Cấu hình màu highlight cho Text widget
        self.setup_highlight_tags()

        # Nạp dữ liệu của note hiện tại lên UI
        self.load_note_ui(first_load=True)

        # Phím tắt toàn cục
        self.root.bind("<Control-v>", self.on_paste_global)
        self.root.bind("<Control-V>", self.on_paste_global)
        self.root.bind("<Control-h>", lambda e: self.highlight_selection("yellow"))
        self.root.bind("<Control-H>", lambda e: self.highlight_selection("yellow"))
        self.root.bind("<Control-t>", lambda e: self.translate_context())
        self.root.bind("<Control-T>", lambda e: self.translate_context())
        self.root.bind("<Control-z>", self.on_undo)
        self.root.bind("<Control-Z>", self.on_undo)
        self.root.bind("<Control-y>", self.on_redo)
        self.root.bind("<Control-Y>", self.on_redo)
        self.root.bind("<Control-n>", lambda e: self.create_new_note())
        self.root.bind("<Control-N>", lambda e: self.create_new_note())
        self.root.bind("<Control-w>", lambda e: self.delete_current_note())
        self.root.bind("<Control-W>", lambda e: self.delete_current_note())
        self.root.bind("<Control-Tab>", self.cycle_next_note)
        self.root.bind("<Control-plus>", lambda e: self.change_font_size(2))
        self.root.bind("<Control-equal>", lambda e: self.change_font_size(2))
        self.root.bind("<Control-minus>", lambda e: self.change_font_size(-2))
        self.root.bind("<Control-d>", lambda e: self.play_tts())
        self.root.bind("<Control-D>", lambda e: self.play_tts())
        self.root.bind("<Escape>", lambda e: self.close_translation())

        # Gắn phím tắt trực tiếp lên Text editor
        self.text_editor.bind("<Control-z>", self.on_undo)
        self.text_editor.bind("<Control-Z>", self.on_undo)
        self.text_editor.bind("<Control-y>", self.on_redo)
        self.text_editor.bind("<Control-Y>", self.on_redo)
        self.text_editor.bind("<Key>", self.on_key_press)

        # Lắng nghe bôi đen / chọn chữ 2 chiều (tiếng Anh ➔ tiếng Việt và ngược lại)
        self.text_editor.bind("<<Selection>>", self.on_en_selection_change)
        self.text_editor.bind("<ButtonRelease-1>", self.on_en_selection_change)
        self.text_editor.bind("<KeyRelease>", self.on_en_selection_change)

        self.trans_text.bind("<<Selection>>", self.on_vi_selection_change)
        self.trans_text.bind("<ButtonRelease-1>", self.on_vi_selection_change)
        self.trans_text.bind("<KeyRelease>", self.on_vi_selection_change)

        # Menu chuột phải
        self.create_context_menu()
        self.root.bind("<Button-3>", self.show_context_menu)

        # Bắt sự kiện co giãn
        self.root.bind("<Configure>", self.on_window_resize)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_data(self):
        default_geometry = "440x540+860+140"
        default_text = (
            "Chào bạn! Ứng dụng đã hỗ trợ DỊCH ĐỐI ỨNG SONG NGỮ 2 CHIỀU & TÁCH CỬA SỔ:\n\n"
            "• Nhấn Ctrl + T (hoặc icon 🌐) để dịch toàn bộ bài hoặc đoạn chọn sang tiếng Việt.\n"
            "• BÔI ĐEN câu/từ tiếng Anh ➔ Tự động làm sáng & tìm đến câu dịch tiếng Việt đối lại!\n"
            "• BÔI ĐEN câu/từ tiếng Việt ➔ Tự động làm sáng & tìm đến câu tiếng Anh đối lại!\n"
            "• Nắm giữ chuột vào tab Note và kéo ra ngoài màn hình để tách thành cửa sổ riêng!\n"
            "• Hoặc bấm nút [↗] bên cạnh tab Note để tách tức thì, bấm [↙] để gộp lại."
        )

        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_geometry = data.get("geometry", default_geometry)
                    self.font_size = data.get("font_size", 14)
                    self.is_topmost = data.get("is_topmost", True)
                    self.is_zen_mode = data.get("is_zen_mode", False)
                    self.active_note_id = str(data.get("active_note_id", "1"))

                    if "notes" in data and isinstance(data["notes"], list) and data["notes"]:
                        self.notes = data["notes"]
                    else:
                        old_text = data.get("text", default_text)
                        old_hl = data.get("highlights", [])
                        old_img = data.get("image_base64", "")
                        old_tab = data.get("active_tab", "text")
                        self.notes = [{
                            "id": "1",
                            "title": "Note 1",
                            "text": old_text,
                            "highlights": old_hl,
                            "image_base64": old_img,
                            "active_tab": old_tab
                        }]
            except Exception:
                pass

        if not self.notes:
            self.notes = [{
                "id": "1",
                "title": "Note 1",
                "text": default_text,
                "highlights": [],
                "image_base64": "",
                "active_tab": "text"
            }]

        self.root.geometry(default_geometry)
        self.root.attributes("-topmost", self.is_topmost)

    def get_current_note(self):
        for n in self.notes:
            if str(n.get("id")) == str(self.active_note_id):
                return n
        if self.notes:
            self.active_note_id = str(self.notes[0]["id"])
            return self.notes[0]
        new_note = {
            "id": "1",
            "title": "Note 1",
            "text": "",
            "highlights": [],
            "image_base64": "",
            "active_tab": "text"
        }
        self.notes.append(new_note)
        self.active_note_id = "1"
        return new_note

    def snapshot_current_note(self):
        note = self.get_current_note()
        note["text"] = self.text_editor.get("1.0", tk.END).strip()

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
        note["highlights"] = highlights
        note["image_base64"] = self.current_image_data or ""
        note["active_tab"] = self.active_tab

    def save_data(self):
        try:
            self.snapshot_current_note()
            data = {
                "geometry": self.root.geometry(),
                "font_size": self.font_size,
                "is_topmost": self.is_topmost,
                "is_zen_mode": self.is_zen_mode,
                "active_note_id": self.active_note_id,
                "notes": self.notes
            }
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_note_ui(self, first_load=False):
        note = self.get_current_note()

        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", note.get("text", ""))

        self.saved_highlights = note.get("highlights", [])
        self.apply_saved_highlights()

        img_b64 = note.get("image_base64", "")
        if img_b64:
            try:
                img_bytes = base64.b64decode(img_b64)
                self.current_image = Image.open(io.BytesIO(img_bytes))
                self.current_image_data = img_b64
            except Exception:
                self.current_image = None
                self.current_image_data = None
        else:
            self.current_image = None
            self.current_image_data = None

        self.switch_tab(note.get("active_tab", "text"))
        self.action_history.clear()
        self.redo_history.clear()
        self.close_translation()
        self.render_note_tabs()

    def switch_note(self, note_id):
        if str(note_id) == str(self.active_note_id):
            return
        self.snapshot_current_note()
        self.active_note_id = str(note_id)
        self.load_note_ui()
        self.save_data()

    def create_new_note(self):
        self.snapshot_current_note()
        new_id = str(int(time.time() * 1000))
        num = len(self.notes) + 1
        existing_titles = [n.get("title", "") for n in self.notes]
        while f"Note {num}" in existing_titles:
            num += 1

        new_note = {
            "id": new_id,
            "title": f"Note {num}",
            "text": "",
            "highlights": [],
            "image_base64": "",
            "active_tab": "text"
        }
        self.notes.append(new_note)
        self.active_note_id = new_id
        self.load_note_ui()
        self.save_data()

    def delete_current_note(self):
        self.delete_note_by_id(self.active_note_id)

    def delete_note_by_id(self, nid):
        nid = str(nid)
        if nid in self.detached_windows:
            win = self.detached_windows.pop(nid, None)
            if win:
                try:
                    win.top.destroy()
                except Exception:
                    pass

        if len(self.notes) <= 1:
            self.text_editor.delete("1.0", tk.END)
            self.clear_image()
            self.action_history.clear()
            self.redo_history.clear()
            self.save_data()
            return

        curr_idx = 0
        for i, n in enumerate(self.notes):
            if str(n["id"]) == nid:
                curr_idx = i
                break

        del self.notes[curr_idx]
        next_idx = min(curr_idx, len(self.notes) - 1)
        self.active_note_id = str(self.notes[next_idx]["id"])
        self.load_note_ui()
        self.save_data()

    def rename_current_note(self, note=None):
        if note is None:
            note = self.get_current_note()
        old_title = note.get("title", "Note")
        new_title = simpledialog.askstring(
            "Đổi tên Note", "Nhập tên mới cho Note:",
            initialvalue=old_title, parent=self.root
        )
        if new_title and new_title.strip():
            note["title"] = new_title.strip()
            self.render_note_tabs()
            self.save_data()

    def cycle_next_note(self, event=None):
        attached = [n for n in self.notes if str(n["id"]) not in self.detached_windows]
        if len(attached) <= 1:
            return "break"
        curr_idx = 0
        for i, n in enumerate(attached):
            if str(n["id"]) == str(self.active_note_id):
                curr_idx = i
                break
        next_idx = (curr_idx + 1) % len(attached)
        self.switch_note(attached[next_idx]["id"])
        return "break"

    # ==========================================================================
    # CÁC HÀM QUẢN LÝ KÉO TÁCH & GỘP NOTE (TEAR-OFF & REATTACH)
    # ==========================================================================
    def detach_note(self, note_id, x=None, y=None):
        nid = str(note_id)
        if nid in self.detached_windows:
            self.focus_detached_note(nid)
            return

        target_note = None
        for n in self.notes:
            if str(n.get("id")) == nid:
                target_note = n
                break
        if not target_note:
            return

        if nid == str(self.active_note_id):
            self.snapshot_current_note()

        win = DetachedNoteWindow(self, target_note, x=x, y=y)
        self.detached_windows[nid] = win

        if nid == str(self.active_note_id):
            attached = [n for n in self.notes if str(n["id"]) not in self.detached_windows]
            if attached:
                self.active_note_id = str(attached[0]["id"])
                self.load_note_ui()
            else:
                self.create_new_note()

        self.render_note_tabs()
        self.save_data()

    def reattach_note(self, note_id):
        nid = str(note_id)
        win = self.detached_windows.get(nid)
        if win:
            win.sync_to_note()
            try:
                win.top.destroy()
            except Exception:
                pass
            self.detached_windows.pop(nid, None)

        self.active_note_id = nid
        self.load_note_ui()
        self.render_note_tabs()
        self.save_data()
        self.root.deiconify()
        self.root.lift()

    def focus_detached_note(self, note_id):
        nid = str(note_id)
        win = self.detached_windows.get(nid)
        if win and win.top.winfo_exists():
            win.top.deiconify()
            win.top.lift()
            win.top.focus_force()

    def on_detached_window_closed(self, note_id):
        nid = str(note_id)
        self.detached_windows.pop(nid, None)
        self.render_note_tabs()
        self.save_data()

    def on_tab_press(self, event, nid):
        self.tab_drag = {
            "nid": str(nid),
            "start_x": event.x_root,
            "start_y": event.y_root,
            "dragging": False,
            "ghost": None
        }

    def on_tab_motion(self, event, nid):
        if not self.tab_drag:
            return
        dx = abs(event.x_root - self.tab_drag["start_x"])
        dy = abs(event.y_root - self.tab_drag["start_y"])

        if (dx > 10 or dy > 10) and not self.tab_drag["dragging"]:
            self.tab_drag["dragging"] = True
            ghost = tk.Toplevel(self.root)
            ghost.overrideredirect(True)
            try:
                ghost.attributes("-alpha", 0.85)
            except Exception:
                pass
            ghost.attributes("-topmost", True)

            title = "Note"
            for n in self.notes:
                if str(n.get("id")) == str(nid):
                    title = n.get("title", "Note")
                    break

            lbl = tk.Label(
                ghost,
                text=f"📑 {title}  ↗ Thả ra ngoài để tách cửa sổ",
                font=("Segoe UI", 9, "bold"),
                bg="#4f46e5", fg="#ffffff",
                padx=8, pady=4, relief="solid", bd=1
            )
            lbl.pack()
            self.tab_drag["ghost"] = ghost

        if self.tab_drag["dragging"] and self.tab_drag["ghost"]:
            gx = event.x_root + 12
            gy = event.y_root + 12
            self.tab_drag["ghost"].geometry(f"+{gx}+{gy}")

    def on_tab_release(self, event, nid):
        if not self.tab_drag:
            return
        was_dragging = self.tab_drag["dragging"]
        ghost = self.tab_drag.get("ghost")
        if ghost:
            try:
                ghost.destroy()
            except Exception:
                pass
        self.tab_drag = None

        if was_dragging:
            win_x = self.root.winfo_rootx()
            win_y = self.root.winfo_rooty()
            win_w = self.root.winfo_width()

            is_outside = (
                event.x_root < win_x - 5 or event.x_root > win_x + win_w + 5 or
                event.y_root < win_y - 5 or event.y_root > win_y + 45
            )
            if is_outside:
                self.detach_note(nid, x=event.x_root - 80, y=event.y_root - 20)
                return

        if str(nid) in self.detached_windows:
            self.focus_detached_note(nid)
        else:
            self.switch_note(nid)

    def show_tab_context_menu(self, event, note):
        nid = str(note.get("id"))
        tab_menu = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 9))
        if nid in self.detached_windows:
            tab_menu.add_command(label="↙ Gộp lại vào cửa sổ chính", command=lambda: self.reattach_note(nid))
            tab_menu.add_command(label="🔍 Hiện lên trên (Focus)", command=lambda: self.focus_detached_note(nid))
        else:
            tab_menu.add_command(label="↗ Tách thành cửa sổ riêng", command=lambda: self.detach_note(nid))
            tab_menu.add_command(label="✏️ Đổi tên Note", command=lambda: self.rename_current_note(note))
            if len(self.notes) > 1:
                tab_menu.add_separator()
                tab_menu.add_command(label="🗑️ Xóa Note này", command=lambda: self.delete_note_by_id(nid))
        try:
            tab_menu.tk_popup(event.x_root, event.y_root)
        finally:
            tab_menu.grab_release()

    def render_note_tabs(self):
        for child in self.notes_bar_frame.winfo_children():
            child.destroy()

        pill_container = tk.Frame(self.notes_bar_frame, bg="#f8fafc")
        pill_container.pack(side=tk.LEFT)

        for i, note in enumerate(self.notes):
            nid = str(note.get("id"))
            is_active = (nid == str(self.active_note_id))
            is_detached = (nid in self.detached_windows)

            raw_title = note.get("title", f"Note {i+1}")
            display_title = raw_title if len(raw_title) <= 9 else raw_title[:8] + "…"

            if is_detached:
                display_text = f"↗ {display_title}"
                pill_bg = "#eff6ff"
                pill_fg = "#2563eb"
                pill_relief = "groove"
                pill_bd = 1
            else:
                display_text = display_title
                pill_bg = "#ffffff" if is_active else "#f1f5f9"
                pill_fg = "#4f46e5" if is_active else "#64748b"
                pill_relief = "solid" if is_active else "flat"
                pill_bd = 1 if is_active else 0

            pill = tk.Label(
                pill_container,
                text=display_text,
                font=("Segoe UI", 8, "bold" if (is_active or is_detached) else "normal"),
                bg=pill_bg,
                fg=pill_fg,
                relief=pill_relief,
                bd=pill_bd,
                padx=6, pady=1, cursor="hand2"
            )
            pill.pack(side=tk.LEFT, padx=1)

            pill.bind("<Button-1>", lambda e, note_id=nid: self.on_tab_press(e, note_id))
            pill.bind("<B1-Motion>", lambda e, note_id=nid: self.on_tab_motion(e, note_id))
            pill.bind("<ButtonRelease-1>", lambda e, note_id=nid: self.on_tab_release(e, note_id))
            pill.bind("<Double-Button-1>", lambda e, n=note: self.rename_current_note(n))
            pill.bind("<Button-3>", lambda e, n=note: self.show_tab_context_menu(e, n))

            if is_active and not is_detached:
                btn_detach = tk.Label(
                    pill_container, text="↗", font=("Segoe UI", 7, "bold"),
                    bg="#f1f5f9", fg="#4f46e5", padx=2, pady=0, cursor="hand2",
                    relief="flat"
                )
                btn_detach.pack(side=tk.LEFT, padx=0)
                btn_detach.bind("<Button-1>", lambda e, note_id=nid: self.detach_note(note_id))

        btn_add = tk.Label(
            pill_container, text="+", font=("Segoe UI", 9, "bold"),
            bg="#f8fafc", fg="#4f46e5", padx=5, pady=1, cursor="hand2"
        )
        btn_add.pack(side=tk.LEFT, padx=2)
        btn_add.bind("<Button-1>", lambda e: self.create_new_note())

    # ==========================================================================
    # CÁC TÍNH NĂNG HIGHLIGHT & HOÀN TÁC (UNDO / REDO)
    # ==========================================================================
    def setup_highlight_tags(self):
        self.text_editor.tag_configure("hl_yellow", background="#fef08a", foreground="#0f172a")
        self.text_editor.tag_configure("hl_green", background="#bbf7d0", foreground="#0f172a")
        self.text_editor.tag_configure("hl_pink", background="#fbcfe8", foreground="#0f172a")
        self.text_editor.tag_configure("hl_blue", background="#bae6fd", foreground="#0f172a")

        # Tag đối ứng song ngữ 2 chiều
        self.text_editor.tag_configure("align_match", background="#fed7aa", foreground="#7c2d12")
        self.trans_text.tag_configure("align_match", background="#fed7aa", foreground="#7c2d12")

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
        if event.state & 4:
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
        if self.action_history and isinstance(self.action_history[-1], dict) and self.action_history[-1].get("type") == "highlight":
            action = self.action_history.pop()
            try:
                start = self.text_editor.index(action["mark_start"])
                end = self.text_editor.index(action["mark_end"])

                if action.get("added_color"):
                    self.text_editor.tag_remove(f"hl_{action['added_color']}", start, end)

                if action.get("removed_color"):
                    self.text_editor.tag_add(f"hl_{action['removed_color']}", start, end)

                for c in action.get("old_tags", []):
                    self.text_editor.tag_add(f"hl_{c}", start, end)

                self.redo_history.append(action)
                self.save_data()
            except Exception:
                pass
            return "break"
        else:
            try:
                self.text_editor.edit_undo()
                if self.action_history and self.action_history[-1] == "text":
                    self.action_history.pop()
                    self.redo_history.append("text")
                self.save_data()
            except tk.TclError:
                pass
            return "break"

    def on_redo(self, event=None):
        if self.redo_history:
            action = self.redo_history.pop()
            if isinstance(action, dict) and action.get("type") == "highlight":
                try:
                    start = self.text_editor.index(action["mark_start"])
                    end = self.text_editor.index(action["mark_end"])
                    for c in action.get("old_tags", []):
                        self.text_editor.tag_remove(f"hl_{c}", start, end)
                    if action.get("added_color"):
                        self.text_editor.tag_add(f"hl_{action['added_color']}", start, end)
                    if action.get("removed_color"):
                        self.text_editor.tag_remove(f"hl_{action['removed_color']}", start, end)
                    self.action_history.append(action)
                    self.save_data()
                except Exception:
                    pass
            elif action == "text":
                try:
                    self.text_editor.edit_redo()
                    self.action_history.append("text")
                    self.save_data()
                except tk.TclError:
                    pass
            return "break"

    # ==========================================================================
    # CHỨC NĂNG DỊCH CHUẨN NGỮ CẢNH & TÌM ĐỐI ỨNG SONG NGỮ 2 CHIỀU
    # ==========================================================================
    def translate_context(self):
        try:
            query_text = self.text_editor.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
        except tk.TclError:
            query_text = ""

        if not query_text:
            query_text = self.text_editor.get("1.0", tk.END).strip()

        if not query_text:
            return

        self.show_translation_loading("⏳ Đang phân tích ngữ cảnh và dịch đối ứng song ngữ...")
        fetch_context_translation(
            query_text,
            on_success=lambda raw_segs, extra: self.root.after(0, lambda: self.display_aligned_translation(raw_segs, extra)),
            on_error=lambda err: self.root.after(0, lambda: self.show_translation_error(err))
        )

    def show_translation_loading(self, text):
        if not self.trans_panel.winfo_ismapped():
            self.trans_panel.pack(fill=tk.X, side=tk.BOTTOM, before=self.content_frame)
        self.trans_text.delete("1.0", tk.END)
        self.trans_text.insert("1.0", text)

    def show_translation_error(self, err):
        self.trans_text.delete("1.0", tk.END)
        self.trans_text.insert("1.0", err)

    def display_aligned_translation(self, raw_segments, extra):
        self.align_segments = []
        self.trans_text.delete("1.0", tk.END)

        curr_en_search = "1.0"
        ts = int(time.time() * 1000)

        for i, seg in enumerate(raw_segments):
            clean_en = seg["en"].strip()
            ms_en = f"main_en_s_{i}_{ts}"
            me_en = f"main_en_e_{i}_{ts}"

            if clean_en:
                pos = self.text_editor.search(clean_en, curr_en_search, tk.END)
                if not pos:
                    prefix = clean_en[:min(25, len(clean_en))]
                    pos = self.text_editor.search(prefix, curr_en_search, tk.END)
                if pos:
                    end_pos = f"{pos}+{len(clean_en)}c"
                    self.text_editor.mark_set(ms_en, pos)
                    self.text_editor.mark_set(me_en, end_pos)
                    self.text_editor.mark_gravity(ms_en, tk.LEFT)
                    self.text_editor.mark_gravity(me_en, tk.RIGHT)
                    curr_en_search = end_pos
                else:
                    ms_en, me_en = None, None
            else:
                ms_en, me_en = None, None

            ms_vi = f"main_vi_s_{i}_{ts}"
            me_vi = f"main_vi_e_{i}_{ts}"
            vi_start = self.trans_text.index(tk.INSERT)
            self.trans_text.insert(tk.END, seg["vi"])
            vi_end = self.trans_text.index(f"{tk.INSERT}-1c")

            self.trans_text.mark_set(ms_vi, vi_start)
            self.trans_text.mark_set(me_vi, vi_end)
            self.trans_text.mark_gravity(ms_vi, tk.LEFT)
            self.trans_text.mark_gravity(me_vi, tk.RIGHT)

            if ms_en and me_en:
                self.align_segments.append({
                    "ms_en": ms_en,
                    "me_en": me_en,
                    "ms_vi": ms_vi,
                    "me_vi": me_vi,
                    "en": clean_en,
                    "vi": seg["vi"].strip()
                })

        if extra:
            self.trans_text.insert(tk.END, extra)

        if not self.trans_panel.winfo_ismapped():
            self.trans_panel.pack(fill=tk.X, side=tk.BOTTOM, before=self.content_frame)

        self.on_en_selection_change()

    def on_en_selection_change(self, event=None):
        if self.is_syncing_align or not getattr(self, "align_segments", None):
            return
        try:
            sel_s = self.text_editor.index(tk.SEL_FIRST)
            sel_e = self.text_editor.index(tk.SEL_LAST)
        except tk.TclError:
            sel_s = self.text_editor.index(tk.INSERT)
            sel_e = f"{sel_s}+1c"

        self.is_syncing_align = True
        try:
            self.trans_text.tag_remove("align_match", "1.0", tk.END)
            first_match = None
            for seg in self.align_segments:
                try:
                    s_en = self.text_editor.index(seg["ms_en"])
                    e_en = self.text_editor.index(seg["me_en"])
                    if self.text_editor.compare(sel_s, "<", e_en) and self.text_editor.compare(sel_e, ">", s_en):
                        vi_s = self.trans_text.index(seg["ms_vi"])
                        vi_e = self.trans_text.index(seg["me_vi"])
                        self.trans_text.tag_add("align_match", vi_s, vi_e)
                        if not first_match:
                            first_match = vi_s
                except Exception:
                    pass
            if first_match:
                self.trans_text.see(first_match)
        finally:
            self.is_syncing_align = False

    def on_vi_selection_change(self, event=None):
        if self.is_syncing_align or not getattr(self, "align_segments", None):
            return
        try:
            sel_s = self.trans_text.index(tk.SEL_FIRST)
            sel_e = self.trans_text.index(tk.SEL_LAST)
        except tk.TclError:
            sel_s = self.trans_text.index(tk.INSERT)
            sel_e = f"{sel_s}+1c"

        self.is_syncing_align = True
        try:
            self.text_editor.tag_remove("align_match", "1.0", tk.END)
            first_match = None
            for seg in self.align_segments:
                try:
                    s_vi = self.trans_text.index(seg["ms_vi"])
                    e_vi = self.trans_text.index(seg["me_vi"])
                    if self.trans_text.compare(sel_s, "<", e_vi) and self.trans_text.compare(sel_e, ">", s_vi):
                        en_s = self.text_editor.index(seg["ms_en"])
                        en_e = self.text_editor.index(seg["me_en"])
                        self.text_editor.tag_add("align_match", en_s, en_e)
                        if not first_match:
                            first_match = en_s
                except Exception:
                    pass
            if first_match:
                self.text_editor.see(first_match)
        finally:
            self.is_syncing_align = False

    def close_translation(self):
        self.text_editor.tag_remove("align_match", "1.0", tk.END)
        self.trans_text.tag_remove("align_match", "1.0", tk.END)
        if self.trans_panel.winfo_ismapped():
            self.trans_panel.pack_forget()

    def copy_translation(self):
        content = self.trans_text.get("1.0", tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)

    # ==========================================================================
    # GIAO DIỆN CHÍNH
    # ==========================================================================
    def create_minimal_ui(self):
        # 1. THANH CÔNG CỤ SIÊU MỎNG (28px)
        self.top_bar = tk.Frame(self.root, bg="#f8fafc", height=28)
        if not self.is_zen_mode:
            self.top_bar.pack(fill=tk.X, side=tk.TOP)

        # Bên trái: Chế độ xem [📝] [🖼️] [🌓]
        mode_frame = tk.Frame(self.top_bar, bg="#f8fafc")
        mode_frame.pack(side=tk.LEFT, padx=4, pady=2)

        self.btn_mode_text = tk.Label(
            mode_frame, text="📝", font=("Segoe UI", 8),
            bg="#ffffff" if self.active_tab == "text" else "#f8fafc",
            fg="#4f46e5" if self.active_tab == "text" else "#64748b",
            padx=5, pady=2, cursor="hand2"
        )
        self.btn_mode_text.pack(side=tk.LEFT, padx=1)
        self.btn_mode_text.bind("<Button-1>", lambda e: self.switch_tab("text"))

        self.btn_mode_image = tk.Label(
            mode_frame, text="🖼️", font=("Segoe UI", 8),
            bg="#ffffff" if self.active_tab == "image" else "#f8fafc",
            fg="#4f46e5" if self.active_tab == "image" else "#64748b",
            padx=5, pady=2, cursor="hand2"
        )
        self.btn_mode_image.pack(side=tk.LEFT, padx=1)
        self.btn_mode_image.bind("<Button-1>", lambda e: self.switch_tab("image"))

        self.btn_mode_split = tk.Label(
            mode_frame, text="🌓", font=("Segoe UI", 8),
            bg="#ffffff" if self.active_tab == "split" else "#f8fafc",
            fg="#4f46e5" if self.active_tab == "split" else "#64748b",
            padx=5, pady=2, cursor="hand2"
        )
        self.btn_mode_split.pack(side=tk.LEFT, padx=1)
        self.btn_mode_split.bind("<Button-1>", lambda e: self.switch_tab("split"))

        # Ở giữa: Danh sách các Note [ Note 1 ] [ Note 2 ] [ + ]
        self.notes_bar_frame = tk.Frame(self.top_bar, bg="#f8fafc")
        self.notes_bar_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # Bên phải: 🌐 Dịch | 🖍️ Highlight | 🔊 Đọc | 📌 Ghim | ⋯ Menu
        actions_frame = tk.Frame(self.top_bar, bg="#f8fafc")
        actions_frame.pack(side=tk.RIGHT, padx=3)

        self.btn_trans_icon = tk.Label(
            actions_frame, text="🌐", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#4f46e5", padx=3, pady=2, cursor="hand2"
        )
        self.btn_trans_icon.pack(side=tk.LEFT, padx=1)
        self.btn_trans_icon.bind("<Button-1>", lambda e: self.translate_context())

        self.btn_hl_icon = tk.Label(
            actions_frame, text="🖍️", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#334155", padx=3, pady=2, cursor="hand2"
        )
        self.btn_hl_icon.pack(side=tk.LEFT, padx=1)
        self.btn_hl_icon.bind("<Button-1>", lambda e: self.highlight_selection("yellow"))

        self.btn_tts_icon = tk.Label(
            actions_frame, text="🔊", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#334155", padx=3, pady=2, cursor="hand2"
        )
        self.btn_tts_icon.pack(side=tk.LEFT, padx=1)
        self.btn_tts_icon.bind("<Button-1>", lambda e: self.play_tts())

        self.btn_pin_icon = tk.Label(
            actions_frame, text="📌" if self.is_topmost else "📍", font=("Segoe UI", 9),
            bg="#f8fafc", fg="#4f46e5" if self.is_topmost else "#94a3b8",
            padx=3, pady=2, cursor="hand2"
        )
        self.btn_pin_icon.pack(side=tk.LEFT, padx=1)
        self.btn_pin_icon.bind("<Button-1>", lambda e: self.toggle_pin())

        self.btn_menu_icon = tk.Label(
            actions_frame, text="⋯", font=("Segoe UI", 10, "bold"),
            bg="#f8fafc", fg="#475569", padx=3, pady=2, cursor="hand2"
        )
        self.btn_menu_icon.pack(side=tk.LEFT, padx=1)
        self.btn_menu_icon.bind("<Button-1>", lambda e: self.show_context_menu(e))

        # 2. KHUNG NỘI DUNG CHÍNH
        self.content_frame = tk.Frame(self.root, bg="#ffffff")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # 3. KHUNG HÌNH ẢNH
        self.image_container = tk.Frame(self.content_frame, bg="#f8fafc")
        self.image_label = tk.Label(
            self.image_container,
            text="📷 Chưa có ảnh\nẤn Ctrl + V dán ảnh chụp màn hình",
            bg="#f8fafc", fg="#94a3b8",
            font=("Segoe UI", 11)
        )
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.image_label.bind("<Button-1>", self.on_image_click)

        # 4. KHUNG VĂN BẢN (KHÔNG GẠCH ĐỎ)
        self.text_container = tk.Frame(self.content_frame, bg="#ffffff")
        self.text_editor = tk.Text(
            self.text_container,
            font=("Segoe UI", self.font_size),
            wrap=tk.WORD,
            undo=True,
            maxundo=-1,
            autoseparators=True,
            relief="flat",
            bd=0,
            padx=14,
            pady=14,
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#4f46e5",
            selectbackground="#c7d2fe",
            selectforeground="#1e1b4b"
        )
        self.text_editor.pack(fill=tk.BOTH, expand=True)

        # 5. KHUNG KẾT QUẢ DỊCH ĐỐI ỨNG SONG NGỮ
        self.trans_panel = tk.Frame(self.root, bg="#f8fafc", relief="solid", bd=1)

        trans_header = tk.Frame(self.trans_panel, bg="#f1f5f9", height=24)
        trans_header.pack(fill=tk.X, side=tk.TOP)

        lbl_trans_title = tk.Label(
            trans_header, text="🌐 Dịch đối ứng song ngữ (Bôi đen câu/từ để tìm đối ứng 2 chiều)",
            font=("Segoe UI", 8, "bold"), bg="#f1f5f9", fg="#334155", padx=6, pady=2
        )
        lbl_trans_title.pack(side=tk.LEFT)

        btn_close_trans = tk.Label(
            trans_header, text="✕", font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9", fg="#64748b", padx=6, cursor="hand2"
        )
        btn_close_trans.pack(side=tk.RIGHT)
        btn_close_trans.bind("<Button-1>", lambda e: self.close_translation())

        btn_copy_trans = tk.Label(
            trans_header, text="📋 Sao chép", font=("Segoe UI", 8),
            bg="#f1f5f9", fg="#4f46e5", padx=6, cursor="hand2"
        )
        btn_copy_trans.pack(side=tk.RIGHT)
        btn_copy_trans.bind("<Button-1>", lambda e: self.copy_translation())

        self.trans_text = tk.Text(
            self.trans_panel,
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            relief="flat",
            bd=0,
            bg="#f8fafc",
            fg="#0f172a",
            padx=8,
            pady=6,
            height=5
        )
        self.trans_text.pack(fill=tk.BOTH, expand=True)

        self.root.bind("<Motion>", self.check_hover_top_bar)

    def check_hover_top_bar(self, event):
        if self.is_zen_mode:
            if event.y < 30:
                if not self.top_bar.winfo_ismapped():
                    self.top_bar.pack(fill=tk.X, side=tk.TOP, before=self.content_frame)
            elif event.y > 50:
                if self.top_bar.winfo_ismapped():
                    self.top_bar.pack_forget()

    def create_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 9))

        self.menu.add_command(label="🌐 Dịch song ngữ đối ứng (Ctrl+T)", command=self.translate_context)
        self.menu.add_command(label="🔊 Nghe đọc đoạn văn (Ctrl+D)", command=self.play_tts)
        self.menu.add_command(label="↗ Tách Note này thành cửa sổ riêng", command=lambda: self.detach_note(self.active_note_id))
        self.menu.add_separator()

        note_menu = tk.Menu(self.menu, tearoff=0, font=("Segoe UI", 9))
        note_menu.add_command(label="➕ Tạo Note mới (Ctrl+N)", command=self.create_new_note)
        note_menu.add_command(label="↗ Tách Note thành cửa sổ riêng", command=lambda: self.detach_note(self.active_note_id))
        note_menu.add_command(label="✏️ Đổi tên Note hiện tại", command=self.rename_current_note)
        note_menu.add_command(label="➡️ Chuyển sang Note tiếp (Ctrl+Tab)", command=self.cycle_next_note)
        note_menu.add_separator()
        note_menu.add_command(label="🗑️ Xóa Note hiện tại (Ctrl+W)", command=self.delete_current_note)
        self.menu.add_cascade(label="📑 Quản lý nhiều Note", menu=note_menu)
        self.menu.add_separator()

        hl_menu = tk.Menu(self.menu, tearoff=0, font=("Segoe UI", 9))
        hl_menu.add_command(label="🟡 Màu Vàng (Ctrl+H)", command=lambda: self.highlight_selection("yellow"))
        hl_menu.add_command(label="🟢 Màu Xanh lá", command=lambda: self.highlight_selection("green"))
        hl_menu.add_command(label="🌸 Màu Hồng", command=lambda: self.highlight_selection("pink"))
        hl_menu.add_command(label="🔵 Màu Xanh lam", command=lambda: self.highlight_selection("blue"))
        hl_menu.add_separator()
        hl_menu.add_command(label="⚪ Bỏ Highlight đoạn chọn", command=self.remove_highlight_selection)

        self.menu.add_cascade(label="🖍️ Tô màu Highlight", menu=hl_menu)
        self.menu.add_command(label="↩️ Hoàn tác / Undo (Ctrl+Z)", command=self.on_undo)
        self.menu.add_separator()

        self.menu.add_command(label="📝 Chỉ xem Văn bản", command=lambda: self.switch_tab("text"))
        self.menu.add_command(label="🖼️ Chỉ xem Hình ảnh", command=lambda: self.switch_tab("image"))
        self.menu.add_command(label="🌓 Xem Cả hai (Song song)", command=lambda: self.switch_tab("split"))
        self.menu.add_separator()

        self.menu.add_command(label="➕ Phóng to chữ (Ctrl +)", command=lambda: self.change_font_size(2))
        self.menu.add_command(label="➖ Thu nhỏ chữ (Ctrl -)", command=lambda: self.change_font_size(-2))
        self.menu.add_separator()

        self.menu.add_command(label="📁 Tải file ảnh từ máy...", command=self.choose_image_file)
        self.menu.add_command(label="📌 Bật/Tắt Ghim trên cùng", command=self.toggle_pin)
        self.menu.add_command(label="✨ Ẩn/Hiện thanh công cụ (Zen Mode)", command=self.toggle_zen_mode)
        self.menu.add_separator()

        self.menu.add_command(label="🗑️ Xóa hết chữ của Note này", command=self.clear_text)
        self.menu.add_command(label="🗑️ Xóa hình ảnh của Note này", command=self.clear_image)

    def show_context_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def switch_tab(self, tab):
        self.active_tab = tab

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
        self.save_data()

    def clear_image(self):
        self.current_image = None
        self.current_image_data = None
        self.image_label.configure(
            image="", text="📷 Chưa có ảnh\nẤn Ctrl + V dán ảnh chụp màn hình"
        )
        self.save_data()

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
        self.save_data()

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
        speak_english_text(text)

    def on_close(self):
        for nid, win in list(self.detached_windows.items()):
            try:
                win.sync_to_note()
                win.top.destroy()
            except Exception:
                pass
        self.detached_windows.clear()
        self.save_data()
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)


def main():
    if not ensure_single_instance():
        # Nếu ứng dụng đã đang chạy rồi, không mở thêm cửa sổ thứ hai đè lên
        sys.exit(0)
    root = tk.Tk()
    app = IELTSCornerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
