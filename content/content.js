/**
 * IELTS Corner - Tiện ích xem Văn Bản & Hình Ảnh tối giản ở góc màn hình
 * Hỗ trợ kéo di chuyển tự do, phóng to thu nhỏ góc, dán văn bản và dán ảnh riêng biệt.
 */

(function () {
  if (document.getElementById("ielts-corner-root")) return;

  // Trạng thái đơn giản
  let activeTab = "text"; // 'text' hoặc 'image'
  let savedText = "";
  let savedImage = "";
  let fontSize = 14;
  let isMinimized = false;
  let isEnabled = true;
  let isUserDirty = false;

  let cardWidth = 380;
  let cardHeight = 440;
  let widgetPosition = { right: 24, bottom: 24 };

  // Tải dữ liệu đã lưu
  chrome.storage.local.get(
    {
      isEnabled: true,
      activeTab: "text",
      savedText: "Chào bạn! Đây là khung xem văn bản.\n\n• Nhấn Ctrl + V để dán đoạn văn tiếng Anh vào đây.\n• Bấm 🔊 để nghe phát âm.\n• Chuyển sang tab [🖼️ Hình ảnh] để xem ảnh chụp màn hình.\n• Kéo góc dưới phải để phóng to / thu nhỏ.",
      savedImage: "",
      fontSize: 14,
      cardWidth: 380,
      cardHeight: 440,
      position: null,
      isMinimized: false
    },
    (data) => {
      isEnabled = data.isEnabled;
      activeTab = data.activeTab || "text";
      savedText = data.savedText || "";
      savedImage = data.savedImage || "";
      fontSize = data.fontSize || 14;
      cardWidth = data.cardWidth || 380;
      cardHeight = data.cardHeight || 440;
      isMinimized = data.isMinimized || false;
      if (data.position) widgetPosition = data.position;

      if (isEnabled) {
        createWidget();
      }
    }
  );

  // Lắng nghe cài đặt từ popup hoặc các tab khác (Đồng bộ thời gian thực giữa mọi trang)
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local") return;
    const root = document.getElementById("ielts-corner-root");
    const shadow = root?.shadowRoot;

    if (changes.forceShow || changes.isEnabled) {
      if (changes.isEnabled !== undefined) isEnabled = changes.isEnabled.newValue;
      if (isEnabled) {
        if (!root) createWidget();
        else {
          root.style.display = "block";
          const card = shadow?.getElementById("ielts-card");
          const bubble = shadow?.getElementById("ielts-bubble");
          if (card) card.style.display = "flex";
          if (bubble) bubble.style.display = "none";
        }
      } else if (root) {
        root.style.display = "none";
      }
    }

    if (changes.isMinimized !== undefined && shadow) {
      isMinimized = changes.isMinimized.newValue;
      const card = shadow.getElementById("ielts-card");
      const bubble = shadow.getElementById("ielts-bubble");
      if (card && bubble) {
        card.style.display = isMinimized ? "none" : "flex";
        bubble.style.display = isMinimized ? "flex" : "none";
      }
    }

    // ĐỒNG BỘ NỘI DUNG VĂN BẢN THỜI GIAN THỰC GIỮA CÁC TAB
    if (changes.savedText !== undefined) {
      savedText = changes.savedText.newValue !== undefined ? changes.savedText.newValue : "";
      if (shadow) {
        const textArea = shadow.getElementById("text-area");
        const isActivelyTyping = document.hasFocus() && shadow.activeElement === textArea;
        if (textArea && !isActivelyTyping && textArea.value !== savedText) {
          textArea.value = savedText;
        }
      }
    }

    // ĐỒNG BỘ HÌNH ẢNH THỜI GIAN THỰC GIỮA CÁC TAB
    if (changes.savedImage !== undefined) {
      savedImage = changes.savedImage.newValue || "";
      if (shadow) {
        const img = shadow.getElementById("image-preview");
        const empty = shadow.getElementById("empty-image-box");
        if (img && empty) {
          img.src = savedImage;
          if (savedImage) {
            img.style.display = "block";
            empty.style.display = "none";
          } else {
            img.style.display = "none";
            empty.style.display = "flex";
          }
        }
      }
    }

    // ĐỒNG BỘ CỠ CHỮ
    if (changes.fontSize !== undefined && shadow) {
      fontSize = changes.fontSize.newValue;
      const textArea = shadow.getElementById("text-area");
      if (textArea) textArea.style.fontSize = `${fontSize}px`;
    }

    // ĐỒNG BỘ TAB ĐANG CHỌN (VĂN BẢN HOẶC HÌNH ẢNH)
    if (changes.activeTab && shadow) {
      switchTab(shadow, changes.activeTab.newValue);
    }

    // ĐỒNG BỘ VỊ TRÍ
    if (changes.position && root) {
      widgetPosition = changes.position.newValue;
      applyPosition(root);
    }

    // ĐỒNG BỘ KÍCH THƯỚC PHÓNG TO / THU NHỎ
    if ((changes.cardWidth || changes.cardHeight) && shadow) {
      if (changes.cardWidth) cardWidth = changes.cardWidth.newValue;
      if (changes.cardHeight) cardHeight = changes.cardHeight.newValue;
      const card = shadow.getElementById("ielts-card");
      if (card) {
        card.style.setProperty("width", `${cardWidth}px`, "important");
        card.style.setProperty("height", `${cardHeight}px`, "important");
      }
    }
  });

  // Tự động kiểm tra và làm mới dữ liệu khi người dùng chuyển sang tab này
  function reloadFromStorage() {
    chrome.storage.local.get(
      {
        savedText: null,
        savedImage: null,
        activeTab: "text",
        fontSize: 14,
        cardWidth: 380,
        cardHeight: 440,
        isMinimized: false,
        isEnabled: true,
        position: null
      },
      (data) => {
        const root = document.getElementById("ielts-corner-root");
        const shadow = root?.shadowRoot;
        if (!shadow) return;

        // Trạng thái bật / tắt
        if (data.isEnabled !== null && data.isEnabled !== undefined) {
          isEnabled = data.isEnabled;
          root.style.display = isEnabled ? "block" : "none";
          if (!isEnabled) return;
        }

        // Trạng thái thu nhỏ hay mở rộng thẻ
        if (data.isMinimized !== null && data.isMinimized !== undefined) {
          isMinimized = data.isMinimized;
          const card = shadow.getElementById("ielts-card");
          const bubble = shadow.getElementById("ielts-bubble");
          if (card && bubble) {
            card.style.display = isMinimized ? "none" : "flex";
            bubble.style.display = isMinimized ? "flex" : "none";
          }
        }

        // Nội dung văn bản - Luôn cập nhật tức thì kể cả khi chưa bỏ focus
        if (data.savedText !== null && data.savedText !== undefined) {
          savedText = data.savedText;
          const textArea = shadow.getElementById("text-area");
          const isActivelyTyping = document.hasFocus() && shadow.activeElement === textArea;
          if (textArea && !isActivelyTyping && textArea.value !== savedText) {
            textArea.value = savedText;
          }
        }

        // Nội dung hình ảnh
        if (data.savedImage !== null && data.savedImage !== undefined) {
          savedImage = data.savedImage;
          const img = shadow.getElementById("image-preview");
          const empty = shadow.getElementById("empty-image-box");
          if (img && empty) {
            img.src = savedImage;
            img.style.display = savedImage ? "block" : "none";
            empty.style.display = savedImage ? "none" : "flex";
          }
        }

        // Tab đang xem
        if (data.activeTab && data.activeTab !== activeTab) {
          switchTab(shadow, data.activeTab);
        }

        // Cỡ chữ
        if (data.fontSize !== null && data.fontSize !== undefined && data.fontSize !== fontSize) {
          fontSize = data.fontSize;
          const textArea = shadow.getElementById("text-area");
          if (textArea) textArea.style.fontSize = `${fontSize}px`;
        }

        // Kích thước khung
        if (data.cardWidth || data.cardHeight) {
          if (data.cardWidth) cardWidth = data.cardWidth;
          if (data.cardHeight) cardHeight = data.cardHeight;
          const card = shadow.getElementById("ielts-card");
          if (card) {
            card.style.setProperty("width", `${cardWidth}px`, "important");
            card.style.setProperty("height", `${cardHeight}px`, "important");
          }
        }

        // Vị trí (Tự điều chỉnh nằm gọn trong màn hình tab này)
        if (data.position) {
          widgetPosition = data.position;
          applyPosition(root);
        }
      }
    );
  }

  window.addEventListener("focus", reloadFromStorage);
  window.addEventListener("pageshow", reloadFromStorage);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      reloadFromStorage();
    }
  });

  // Tự động kiểm tra đồng bộ liên tục khi tab đang mở (chu kỳ 250ms)
  setInterval(() => {
    if (!document.hidden) {
      reloadFromStorage();
    }
  }, 250);

  function createWidget() {
    const host = document.createElement("div");
    host.id = "ielts-corner-root";
    host.style.cssText = "position: fixed !important; z-index: 2147483647 !important; pointer-events: auto !important; margin: 0 !important; padding: 0 !important; border: none !important;";
    document.body.appendChild(host);

    const shadow = host.attachShadow({ mode: "open" });

    // CSS hoàn toàn độc lập trong Shadow DOM
    const style = document.createElement("style");
    style.textContent = `
      * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }

      :host {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 13px;
        color: #1e293b;
      }

      /* Khung thẻ chính */
      .card-box {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        position: relative;
        min-width: 280px;
        min-height: 200px;
      }

      /* Thanh kéo di chuyển trên cùng */
      .drag-header {
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
        padding: 6px 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        cursor: grab;
        user-select: none;
      }

      .drag-header:active {
        cursor: grabbing;
      }

      /* 2 Tab chuyển đổi Text và Hình */
      .tabs-group {
        display: flex;
        background: #e2e8f0;
        padding: 2px;
        border-radius: 6px;
        gap: 2px;
      }

      .tab-btn {
        background: none;
        border: none;
        padding: 4px 10px;
        font-size: 12px;
        font-weight: 600;
        color: #64748b;
        border-radius: 5px;
        cursor: pointer;
        transition: all 0.15s;
      }

      .tab-btn.active {
        background: #ffffff;
        color: #4f46e5;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
      }

      .header-right {
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .drag-hint {
        font-size: 11px;
        color: #94a3b8;
        font-weight: 500;
      }

      .btn-icon {
        background: none;
        border: none;
        color: #64748b;
        cursor: pointer;
        padding: 3px 6px;
        border-radius: 4px;
        font-size: 13px;
        line-height: 1;
      }

      .btn-icon:hover {
        background: #e2e8f0;
        color: #0f172a;
      }

      /* Nội dung thẻ */
      .card-body {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 8px;
        overflow: hidden;
        background: #ffffff;
        position: relative;
      }

      /* MỤC 1: VĂN BẢN (TEXT) */
      .view-text {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .text-area {
        flex: 1;
        width: 100%;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px;
        font-size: 14px;
        line-height: 1.6;
        color: #0f172a;
        resize: none;
        outline: none;
        font-family: inherit;
        background: #ffffff;
      }

      .text-area:focus {
        border-color: #6366f1;
      }

      /* MỤC 2: HÌNH ẢNH (IMAGE) */
      .view-image {
        flex: 1;
        display: none;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border: 2px dashed #cbd5e1;
        border-radius: 8px;
        padding: 6px;
        background: #f8fafc;
        overflow: hidden;
        position: relative;
      }

      .image-preview {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        border-radius: 6px;
        display: none;
      }

      .empty-image-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        color: #64748b;
        padding: 20px;
        gap: 8px;
      }

      .empty-icon {
        font-size: 32px;
      }

      /* Thanh công cụ dưới đáy */
      .card-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 6px 10px;
        background: #f8fafc;
        border-top: 1px solid #e2e8f0;
        font-size: 11.5px;
      }

      .footer-btn {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 11.5px;
        font-weight: 600;
        color: #334155;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .footer-btn:hover {
        background: #f1f5f9;
        border-color: #94a3b8;
      }

      .btn-danger {
        color: #ef4444;
      }

      /* Góc kéo phóng to thu nhỏ */
      .resize-grip {
        position: absolute;
        bottom: 0px;
        right: 0px;
        width: 20px;
        height: 20px;
        cursor: nwse-resize;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: bold;
        color: #6366f1;
        background: #e0e7ff;
        border-top-left-radius: 6px;
        user-select: none;
      }

      .resize-grip:hover {
        background: #4f46e5;
        color: #ffffff;
      }

      /* Bong bóng thu nhỏ có thể kéo di chuyển */
      .bubble-box {
        display: none;
        width: 46px;
        height: 46px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%);
        color: white;
        box-shadow: 0 8px 18px rgba(79, 70, 229, 0.45);
        cursor: grab;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 17px;
        border: 2px solid white;
        user-select: none;
        transition: transform 0.15s, box-shadow 0.15s;
      }

      .bubble-box:hover {
        transform: scale(1.1);
        box-shadow: 0 12px 24px rgba(79, 70, 229, 0.55);
      }

      .bubble-box:active {
        cursor: grabbing;
        transform: scale(0.95);
      }
    `;
    shadow.appendChild(style);

    // Cấu trúc HTML tối giản
    const wrapper = document.createElement("div");
    wrapper.innerHTML = `
      <div id="ielts-card" class="card-box" style="width: ${cardWidth}px; height: ${cardHeight}px; display: ${isMinimized ? "none" : "flex"}">
        
        <!-- Header có thể kéo di chuyển -->
        <div class="drag-header" id="drag-header" title="Nhấp giữ thanh này để kéo di chuyển thẻ">
          <div class="tabs-group">
            <button class="tab-btn ${activeTab === "text" ? "active" : ""}" id="tab-text">📝 Văn bản</button>
            <button class="tab-btn ${activeTab === "image" ? "active" : ""}" id="tab-image">🖼️ Hình ảnh</button>
          </div>
          <div class="header-right">
            <span class="drag-hint">⠿ Kéo</span>
            <button class="btn-icon" id="btn-minimize" title="Thu nhỏ">_</button>
          </div>
        </div>

        <!-- Body -->
        <div class="card-body">
          
          <!-- MỤC 1: VĂN BẢN -->
          <div class="view-text" id="view-text" style="display: ${activeTab === "text" ? "flex" : "none"}">
            <textarea class="text-area" id="text-area" placeholder="Nhấn Ctrl + V hoặc gõ văn bản tiếng Anh vào đây...">${savedText}</textarea>
          </div>

          <!-- MỤC 2: HÌNH ẢNH -->
          <div class="view-image" id="view-image" style="display: ${activeTab === "image" ? "flex" : "none"}">
            <img class="image-preview" id="image-preview" src="${savedImage}" style="display: ${savedImage ? "block" : "none"}">
            
            <div class="empty-image-box" id="empty-image-box" style="display: ${savedImage ? "none" : "flex"}">
              <span class="empty-icon">📷</span>
              <p>Chụp màn hình rồi ấn <strong>Ctrl + V</strong> để dán ảnh vào đây</p>
            </div>
          </div>

        </div>

        <!-- Footer -->
        <div class="card-footer">
          <!-- Footer nút cho Text -->
          <div id="footer-text" style="display: ${activeTab === "text" ? "flex" : "none"}; width: 100%; justify-content: space-between; align-items: center;">
            <div style="display: flex; gap: 4px;">
              <button class="footer-btn" id="btn-tts">🔊 Đọc</button>
              <button class="footer-btn" id="btn-font-minus" title="Thu nhỏ chữ">A-</button>
              <button class="footer-btn" id="btn-font-plus" title="Phóng to chữ">A+</button>
            </div>
            <button class="footer-btn btn-danger" id="btn-clear-text">Xóa chữ</button>
          </div>

          <!-- Footer nút cho Image -->
          <div id="footer-image" style="display: ${activeTab === "image" ? "flex" : "none"}; width: 100%; justify-content: space-between; align-items: center;">
            <label class="footer-btn" style="cursor: pointer;">
              📁 Tải ảnh từ máy
              <input type="file" id="file-input" accept="image/*" style="display:none;">
            </label>
            <button class="footer-btn btn-danger" id="btn-clear-image">Xóa ảnh</button>
          </div>
        </div>

        <!-- Góc co giãn phóng to/thu nhỏ -->
        <div class="resize-grip" id="resize-grip" title="Kéo góc này để phóng to / thu nhỏ">⤡</div>

      </div>

      <!-- Bong bóng thu nhỏ -->
      <div id="ielts-bubble" class="bubble-box" style="display: ${isMinimized ? "flex" : "none"}" title="Nhấp để mở lại">
        <span>E</span>
      </div>
    `;

    shadow.appendChild(wrapper);

    // Áp dụng vị trí
    applyPosition(host);

    // Cài đặt tất cả chức năng
    const cardEl = shadow.getElementById("ielts-card");
    const bubbleEl = shadow.getElementById("ielts-bubble");
    setupTabs(shadow);
    setupTextControls(shadow);
    setupImageControls(shadow);
    setupDrag(host, shadow.getElementById("drag-header"), cardEl);
    setupResize(host, cardEl, shadow.getElementById("resize-grip"));
    setupBubbleDragAndClick(host, cardEl, bubbleEl, shadow.getElementById("btn-minimize"));
  }

  // --- CỐ ĐỊNH VÀ ÁP DỤNG TỌA ĐỘ AN TOÀN TRONG MÀN HÌNH ---
  function applyPosition(host) {
    if (!host) return;
    const card = host.shadowRoot?.getElementById("ielts-card");
    const currentW = (card && card.offsetWidth) || cardWidth || 380;
    const currentH = (card && card.offsetHeight) || cardHeight || 440;

    if (widgetPosition.left !== undefined) {
      // Đảm bảo không bị bay ra ngoài màn hình bên phải hoặc bên trái
      const maxLeft = Math.max(10, window.innerWidth - Math.min(currentW, 100));
      const safeLeft = Math.min(Math.max(10, widgetPosition.left), maxLeft);
      host.style.setProperty("left", `${safeLeft}px`, "important");
      host.style.setProperty("right", "auto", "important");
    } else {
      const r = widgetPosition.right !== undefined ? widgetPosition.right : 24;
      host.style.setProperty("right", `${r}px`, "important");
      host.style.setProperty("left", "auto", "important");
    }

    if (widgetPosition.top !== undefined) {
      // Đảm bảo không bị bay ra ngoài mép dưới hoặc mép trên
      const maxTop = Math.max(10, window.innerHeight - Math.min(currentH, 100));
      const safeTop = Math.min(Math.max(10, widgetPosition.top), maxTop);
      host.style.setProperty("top", `${safeTop}px`, "important");
      host.style.setProperty("bottom", "auto", "important");
    } else {
      const b = widgetPosition.bottom !== undefined ? widgetPosition.bottom : 24;
      host.style.setProperty("bottom", `${b}px`, "important");
      host.style.setProperty("top", "auto", "important");
    }
  }

  // Tự động căn chỉnh khi người dùng phóng to/thu nhỏ cửa sổ trình duyệt
  window.addEventListener("resize", () => {
    const root = document.getElementById("ielts-corner-root");
    if (root) applyPosition(root);
  });

  // --- CHUYỂN TAB (VĂN BẢN VÀ HÌNH ẢNH) ---
  function switchTab(shadow, tab) {
    activeTab = tab;
    const tabText = shadow.getElementById("tab-text");
    const tabImage = shadow.getElementById("tab-image");
    const viewText = shadow.getElementById("view-text");
    const viewImage = shadow.getElementById("view-image");
    const footerText = shadow.getElementById("footer-text");
    const footerImage = shadow.getElementById("footer-image");

    if (tab === "text") {
      tabText.classList.add("active");
      tabImage.classList.remove("active");
      viewText.style.display = "flex";
      viewImage.style.display = "none";
      footerText.style.display = "flex";
      footerImage.style.display = "none";
    } else {
      tabImage.classList.add("active");
      tabText.classList.remove("active");
      viewImage.style.display = "flex";
      viewText.style.display = "none";
      footerImage.style.display = "flex";
      footerText.style.display = "none";
    }
    chrome.storage.local.set({ activeTab });
  }

  function setupTabs(shadow) {
    shadow.getElementById("tab-text").addEventListener("click", () => switchTab(shadow, "text"));
    shadow.getElementById("tab-image").addEventListener("click", () => switchTab(shadow, "image"));
  }

  // --- MỤC VĂN BẢN (TEXT) ---
  function setupTextControls(shadow) {
    const textArea = shadow.getElementById("text-area");
    const btnTts = shadow.getElementById("btn-tts");
    const btnClearText = shadow.getElementById("btn-clear-text");
    const btnFontPlus = shadow.getElementById("btn-font-plus");
    const btnFontMinus = shadow.getElementById("btn-font-minus");

    textArea.style.fontSize = `${fontSize}px`;
    if (savedText) {
      textArea.value = savedText;
    }

    // Hàm lưu văn bản tức thời
    function saveTextNow() {
      if (!textArea) return;
      const current = textArea.value;
      savedText = current;
      try {
        chrome.storage.local.set({ savedText: current });
      } catch (e) {}
    }

    function onUserTyping() {
      isUserDirty = true;
      saveTextNow();
    }

    // Tự động lưu văn bản liên tục trên mọi thao tác gõ (kể cả từng chữ cái, chưa bấm Space)
    textArea.addEventListener("input", onUserTyping);
    textArea.addEventListener("compositionupdate", onUserTyping);
    textArea.addEventListener("compositionend", onUserTyping);
    textArea.addEventListener("change", onUserTyping);
    textArea.addEventListener("keyup", onUserTyping);
    textArea.addEventListener("paste", () => {
      isUserDirty = true;
      setTimeout(saveTextNow, 10);
    });

    // Khi người dùng bấm xóa chữ
    btnClearText.addEventListener("click", () => {
      textArea.value = "";
      savedText = "";
      isUserDirty = true;
      chrome.storage.local.set({ savedText: "" });
    });

    // KHI RỜI TAB HOẶC RỜI CỬA SỔ: Chắc chắn lưu nếu tab này đang có con trỏ gõ chữ
    function handleLeaveTab() {
      const wasTyping = shadow && shadow.activeElement === textArea;
      if (wasTyping || isUserDirty) {
        saveTextNow();
        isUserDirty = false;
      }
    }

    window.addEventListener("blur", handleLeaveTab);
    window.addEventListener("pagehide", handleLeaveTab);
    window.addEventListener("beforeunload", handleLeaveTab);
    document.addEventListener("mouseleave", () => {
      const wasTyping = shadow && shadow.activeElement === textArea;
      if (wasTyping || isUserDirty) saveTextNow();
    });
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        handleLeaveTab();
      } else {
        isUserDirty = false;
        reloadFromStorage();
      }
    });

    // Phát âm đoạn văn
    btnTts.addEventListener("click", () => {
      const text = textArea.value.trim();
      if (!text || !("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();
      setTimeout(() => {
        const u = new SpeechSynthesisUtterance(text);
        u.lang = "en-US";
        u.rate = 0.95;
        window.speechSynthesis.speak(u);
      }, 50);
    });

    // Tăng giảm cỡ chữ
    btnFontPlus.addEventListener("click", () => {
      if (fontSize < 24) {
        fontSize += 2;
        textArea.style.fontSize = `${fontSize}px`;
        chrome.storage.local.set({ fontSize });
      }
    });

    btnFontMinus.addEventListener("click", () => {
      if (fontSize > 11) {
        fontSize -= 2;
        textArea.style.fontSize = `${fontSize}px`;
        chrome.storage.local.set({ fontSize });
      }
    });

    // Xóa chữ
    btnClearText.addEventListener("click", () => {
      textArea.value = "";
      savedText = "";
      chrome.storage.local.set({ savedText: "" });
    });
  }

  // --- MỤC HÌNH ẢNH (IMAGE) ---
  function setupImageControls(shadow) {
    const imagePreview = shadow.getElementById("image-preview");
    const emptyBox = shadow.getElementById("empty-image-box");
    const fileInput = shadow.getElementById("file-input");
    const btnClearImage = shadow.getElementById("btn-clear-image");
    const card = shadow.getElementById("ielts-card");

    function renderImage(dataUrl) {
      savedImage = dataUrl;
      imagePreview.src = dataUrl;
      imagePreview.style.display = "block";
      emptyBox.style.display = "none";
      chrome.storage.local.set({ savedImage: dataUrl });
    }

    // Tải ảnh qua nút bấm file
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file && file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (evt) => renderImage(evt.target.result);
        reader.readAsDataURL(file);
      }
    });

    // Xóa ảnh
    btnClearImage.addEventListener("click", () => {
      savedImage = "";
      imagePreview.src = "";
      imagePreview.style.display = "none";
      emptyBox.style.display = "flex";
      chrome.storage.local.set({ savedImage: "" });
    });

    // Dán (Paste) thông minh: Nhấn Ctrl+V dán ảnh hoặc chữ
    card.addEventListener("paste", (e) => {
      const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items;
      if (!items) return;

      for (let item of items) {
        if (item.type.indexOf("image") !== -1) {
          const blob = item.getAsFile();
          const reader = new FileReader();
          reader.onload = (evt) => {
            renderImage(evt.target.result);
            switchTab(shadow, "image"); // Tự động chuyển qua tab hình ảnh
          };
          reader.readAsDataURL(blob);
          e.preventDefault();
          return;
        }
      }
    });
  }

  // --- DI CHUYỂN THẺ (DRAGGING) ---
  function setupDrag(host, dragHeader, card) {
    let isDragging = false;
    let startX = 0, startY = 0;
    let initLeft = 0, initTop = 0;

    const onMouseMove = (e) => {
      if (!isDragging) return;

      const newLeft = Math.max(0, Math.min(window.innerWidth - card.offsetWidth, initLeft + (e.clientX - startX)));
      const newTop = Math.max(0, Math.min(window.innerHeight - card.offsetHeight, initTop + (e.clientY - startY)));

      host.style.setProperty("left", `${newLeft}px`, "important");
      host.style.setProperty("top", `${newTop}px`, "important");
      host.style.setProperty("right", "auto", "important");
      host.style.setProperty("bottom", "auto", "important");
    };

    const onMouseUp = () => {
      if (!isDragging) return;
      isDragging = false;

      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMouseMove, true);
      window.removeEventListener("mouseup", onMouseUp, true);

      const rect = card.getBoundingClientRect();
      const pos = { left: Math.round(rect.left), top: Math.round(rect.top) };
      widgetPosition = pos;
      chrome.storage.local.set({ position: pos });
    };

    dragHeader.addEventListener("mousedown", (e) => {
      // Không kéo nếu nhấp vào nút
      if (e.target.closest("button") || e.target.closest("input")) return;

      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;

      const rect = card.getBoundingClientRect();
      initLeft = rect.left;
      initTop = rect.top;

      host.style.setProperty("right", "auto", "important");
      host.style.setProperty("bottom", "auto", "important");
      host.style.setProperty("left", `${initLeft}px`, "important");
      host.style.setProperty("top", `${initTop}px`, "important");

      document.body.style.userSelect = "none";
      window.addEventListener("mousemove", onMouseMove, true);
      window.addEventListener("mouseup", onMouseUp, true);

      e.preventDefault();
      e.stopPropagation();
    });
  }

  // --- PHÓNG TO / THU NHỎ (RESIZING) ---
  function setupResize(host, card, handle) {
    let isResizing = false;
    let startX = 0, startY = 0;
    let startW = 0, startH = 0;

    const onMouseMove = (e) => {
      if (!isResizing) return;

      const maxW = window.innerWidth - card.getBoundingClientRect().left - 10;
      const maxH = window.innerHeight - card.getBoundingClientRect().top - 10;

      const newW = Math.max(260, Math.min(maxW, startW + (e.clientX - startX)));
      const newH = Math.max(180, Math.min(maxH, startH + (e.clientY - startY)));

      card.style.setProperty("width", `${newW}px`, "important");
      card.style.setProperty("height", `${newH}px`, "important");
      cardWidth = newW;
      cardHeight = newH;
    };

    const onMouseUp = () => {
      if (!isResizing) return;
      isResizing = false;

      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMouseMove, true);
      window.removeEventListener("mouseup", onMouseUp, true);

      const rect = card.getBoundingClientRect();
      chrome.storage.local.set({
        cardWidth,
        cardHeight,
        position: { left: Math.round(rect.left), top: Math.round(rect.top) }
      });
    };

    handle.addEventListener("mousedown", (e) => {
      isResizing = true;
      startX = e.clientX;
      startY = e.clientY;

      const rect = card.getBoundingClientRect();
      startW = rect.width;
      startH = rect.height;

      // Neo thẻ ở góc trên-trái
      host.style.setProperty("right", "auto", "important");
      host.style.setProperty("bottom", "auto", "important");
      host.style.setProperty("left", `${rect.left}px`, "important");
      host.style.setProperty("top", `${rect.top}px`, "important");

      document.body.style.userSelect = "none";
      window.addEventListener("mousemove", onMouseMove, true);
      window.addEventListener("mouseup", onMouseUp, true);

      e.preventDefault();
      e.stopPropagation();
    });
  }

  // --- KÉO THẢ VÀ NHẤP MỞ CHO BONG BÓNG TRÒN (E) ---
  function setupBubbleDragAndClick(host, card, bubble, btnMin) {
    let isDraggingBubble = false;
    let startX = 0, startY = 0;
    let startTime = 0;
    let initLeft = 0, initTop = 0;

    // Nút thu nhỏ trên thẻ
    btnMin.addEventListener("click", (e) => {
      e.stopPropagation();
      card.style.display = "none";
      bubble.style.display = "flex";
      isMinimized = true;
      chrome.storage.local.set({ isMinimized: true });
    });

    const onMouseMove = (e) => {
      if (!isDraggingBubble) return;

      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;

      // Phải kéo di chuyển hơn 8px mới bắt đầu dời vị trí
      if (Math.hypot(deltaX, deltaY) > 8) {
        const bubbleSize = 48;
        const newLeft = Math.max(0, Math.min(window.innerWidth - bubbleSize, initLeft + deltaX));
        const newTop = Math.max(0, Math.min(window.innerHeight - bubbleSize, initTop + deltaY));

        host.style.setProperty("left", `${newLeft}px`, "important");
        host.style.setProperty("top", `${newTop}px`, "important");
        host.style.setProperty("right", "auto", "important");
        host.style.setProperty("bottom", "auto", "important");
      }
    };

    const onMouseUp = (e) => {
      if (!isDraggingBubble) return;
      isDraggingBubble = false;

      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMouseMove, true);
      window.removeEventListener("mouseup", onMouseUp, true);

      const elapsed = Date.now() - startTime;
      const moveDistance = Math.hypot(e.clientX - startX, e.clientY - startY);

      // Nếu nhấp chuột nhanh (< 350ms) hoặc di chuyển ít (< 10px) => ĐÂY LÀ CLICK MỞ THẺ NGAY LẬP TỨC!
      if (elapsed < 350 || moveDistance < 10) {
        openCard();
      } else {
        // Người dùng cố ý kéo bong bóng đi xa
        const rect = bubble.getBoundingClientRect();
        const pos = { left: Math.round(rect.left), top: Math.round(rect.top) };
        widgetPosition = pos;
        chrome.storage.local.set({ position: pos });
      }
    };

    function openCard() {
      bubble.style.display = "none";
      card.style.display = "flex";
      isMinimized = false;

      // Định vị an toàn không bị tràn màn hình
      const hostRect = host.getBoundingClientRect();
      const cardW = card.offsetWidth || cardWidth || 380;
      const cardH = card.offsetHeight || cardHeight || 440;

      let safeLeft = hostRect.left;
      let safeTop = hostRect.top;

      if (safeLeft + cardW > window.innerWidth - 10) {
        safeLeft = Math.max(10, window.innerWidth - cardW - 10);
      }
      if (safeTop + cardH > window.innerHeight - 10) {
        safeTop = Math.max(10, window.innerHeight - cardH - 10);
      }

      host.style.setProperty("left", `${safeLeft}px`, "important");
      host.style.setProperty("top", `${safeTop}px`, "important");
      host.style.setProperty("right", "auto", "important");
      host.style.setProperty("bottom", "auto", "important");

      widgetPosition = { left: Math.round(safeLeft), top: Math.round(safeTop) };
      chrome.storage.local.set({ isMinimized: false, position: widgetPosition });
    }

    bubble.addEventListener("mousedown", (e) => {
      isDraggingBubble = true;
      startX = e.clientX;
      startY = e.clientY;
      startTime = Date.now();

      const rect = bubble.getBoundingClientRect();
      initLeft = rect.left;
      initTop = rect.top;

      host.style.setProperty("right", "auto", "important");
      host.style.setProperty("bottom", "auto", "important");
      host.style.setProperty("left", `${initLeft}px`, "important");
      host.style.setProperty("top", `${initTop}px`, "important");

      document.body.style.userSelect = "none";
      window.addEventListener("mousemove", onMouseMove, true);
      window.addEventListener("mouseup", onMouseUp, true);

      e.preventDefault();
      e.stopPropagation();
    });
  }
})();
