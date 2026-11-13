/**
 * IELTS Corner - Tiện ích xem Văn Bản & Hình Ảnh tối giản ở góc màn hình
 * Hỗ trợ kéo di chuyển tự do, phóng to thu nhỏ góc, xem riêng biệt hoặc song song cả hai.
 * Loại bỏ hoàn toàn gạch đỏ spellcheck, tối ưu tối đa không gian đọc.
 */

(function () {
  if (document.getElementById("ielts-corner-root")) return;

  // Trạng thái đơn giản
  let activeTab = "text"; // 'text', 'image' hoặc 'split'
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
      savedText: "Chào bạn! Đây là khung xem văn bản.\n\n• Nhấn Ctrl + V để dán đoạn văn tiếng Anh vào đây.\n• Bấm 🔊 để nghe phát âm.\n• Chuyển sang tab [🖼️ Hình ảnh] để xem ảnh chụp màn hình.\n• Chọn tab [🌓 Cả hai] để vừa nhìn đề bài vừa gõ bài.\n• Kéo góc dưới phải để phóng to / thu nhỏ.",
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
        if (textArea && !isActivelyTyping) {
          if (textArea.tagName === "TEXTAREA" && textArea.value !== savedText) {
            textArea.value = savedText;
          } else if (textArea.innerHTML !== savedText) {
            textArea.innerHTML = savedText;
          }
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

    // ĐỒNG BỘ TAB ĐANG CHỌN (VĂN BẢN, HÌNH ẢNH, HOẶC CẢ HAI)
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

        // Nội dung văn bản
        if (data.savedText !== null && data.savedText !== undefined) {
          savedText = data.savedText;
          const textArea = shadow.getElementById("text-area");
          const isActivelyTyping = document.hasFocus() && shadow.activeElement === textArea;
          if (textArea && !isActivelyTyping) {
            if (textArea.tagName === "TEXTAREA" && textArea.value !== savedText) {
              textArea.value = savedText;
            } else if (textArea.innerHTML !== savedText) {
              textArea.innerHTML = savedText;
            }
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
        min-width: 260px;
        min-height: 180px;
      }

      /* Thanh cuộn siêu mảnh tối ưu diện tích hiển thị */
      .text-area::-webkit-scrollbar,
      .view-image::-webkit-scrollbar,
      .card-body::-webkit-scrollbar {
        width: 5px;
        height: 5px;
      }
      .text-area::-webkit-scrollbar-track,
      .view-image::-webkit-scrollbar-track,
      .card-body::-webkit-scrollbar-track {
        background: transparent;
      }
      .text-area::-webkit-scrollbar-thumb,
      .view-image::-webkit-scrollbar-thumb,
      .card-body::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 10px;
      }
      .text-area::-webkit-scrollbar-thumb:hover,
      .view-image::-webkit-scrollbar-thumb:hover,
      .card-body::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
      }

      /* Thanh kéo di chuyển trên cùng */
      .drag-header {
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
        padding: 5px 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        cursor: grab;
        user-select: none;
      }

      .drag-header:active {
        cursor: grabbing;
      }

      /* Tab chuyển đổi Text, Hình, và Cả hai */
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
        padding: 3px 8px;
        font-size: 11.5px;
        font-weight: 600;
        color: #64748b;
        border-radius: 5px;
        cursor: pointer;
        transition: all 0.15s;
        white-space: nowrap;
      }

      .tab-btn.active {
        background: #ffffff;
        color: #4f46e5;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
      }

      .header-right {
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .drag-hint {
        font-size: 11px;
        color: #94a3b8;
        font-weight: 500;
        margin-left: 2px;
      }

      .btn-icon {
        background: none;
        border: none;
        color: #64748b;
        cursor: pointer;
        padding: 3px 6px;
        border-radius: 4px;
        font-size: 12px;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .btn-icon:hover {
        background: #e2e8f0;
        color: #0f172a;
      }

      .btn-close-red:hover {
        background: #fee2e2 !important;
        color: #ef4444 !important;
      }

      /* Nội dung thẻ */
      .card-body {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 6px;
        gap: 6px;
        overflow: hidden;
        background: #ffffff;
        position: relative;
      }

      /* MỤC 1: VĂN BẢN (TEXT) */
      .view-text {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-height: 70px;
        overflow: hidden;
      }

      .text-area {
        flex: 1;
        width: 100%;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 14px;
        line-height: 1.48;
        color: #0f172a;
        outline: none;
        font-family: inherit;
        background: #ffffff;
        overflow-y: auto;
        white-space: pre-wrap;
        word-break: break-word;
        user-select: text;
        -webkit-spellcheck: none;
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
        border: 1px dashed #cbd5e1;
        border-radius: 8px;
        padding: 4px;
        background: #f8fafc;
        overflow: auto;
        position: relative;
        min-height: 70px;
      }

      .image-preview {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        border-radius: 6px;
        display: none;
        cursor: zoom-in;
        transition: transform 0.15s ease;
      }

      .empty-image-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        color: #64748b;
        padding: 10px;
        gap: 4px;
        font-size: 12px;
      }

      .empty-icon {
        font-size: 26px;
      }

      /* Thanh công cụ dưới đáy */
      .card-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 5px 8px;
        background: #f8fafc;
        border-top: 1px solid #e2e8f0;
        font-size: 11.5px;
        transition: all 0.2s ease;
      }

      .card-footer.collapsed {
        display: none !important;
      }

      .footer-btn {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        padding: 3px 7px;
        border-radius: 5px;
        font-size: 11.5px;
        font-weight: 600;
        color: #334155;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 3px;
        white-space: nowrap;
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
        width: 18px;
        height: 18px;
        cursor: nwse-resize;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: bold;
        color: #6366f1;
        background: #e0e7ff;
        border-top-left-radius: 6px;
        user-select: none;
      }

      /* Khung dịch chuẩn ngữ cảnh (Collapsible Drawer) */
      .trans-drawer {
        display: none;
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 160px;
        max-height: 85%;
        background: #f8fafc;
        border-top: 1px solid #cbd5e1;
        box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.12);
        flex-direction: column;
        z-index: 50;
        border-radius: 0 0 12px 12px;
      }

      .trans-drawer-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 5px 10px;
        background: #f1f5f9;
        border-bottom: 1px solid #e2e8f0;
        font-size: 11px;
        font-weight: 600;
        color: #475569;
        cursor: row-resize;
        user-select: none;
      }

      .trans-drawer-actions {
        display: flex;
        gap: 6px;
      }

      .trans-drawer-btn {
        background: none;
        border: none;
        font-size: 11px;
        color: #4f46e5;
        cursor: pointer;
        padding: 2px 4px;
        border-radius: 4px;
      }

      .trans-drawer-btn:hover {
        background: #e2e8f0;
      }

      .trans-drawer-body {
        padding: 8px 10px;
        font-size: 13px;
        line-height: 1.5;
        color: #1e293b;
        overflow-y: auto;
        white-space: pre-wrap;
        user-select: text;
        flex: 1;
        min-height: 40px;
      }

      .resize-grip:hover {
        background: #4f46e5;
        color: #ffffff;
      }

      /* Bong bóng thu nhỏ có thể kéo di chuyển */
      .bubble-box {
        display: none;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%);
        color: white;
        box-shadow: 0 8px 18px rgba(79, 70, 229, 0.45);
        cursor: grab;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 16px;
        border: 2px solid white;
        user-select: none;
        transition: transform 0.15s, box-shadow 0.15s;
      }

      .bubble-box:hover {
        transform: scale(1.08);
        box-shadow: 0 12px 24px rgba(79, 70, 229, 0.55);
      }

      .bubble-box:active {
        cursor: grabbing;
        transform: scale(0.95);
      }
    `;
    shadow.appendChild(style);

    // Cấu trúc HTML
    const wrapper = document.createElement("div");
    wrapper.innerHTML = `
      <div id="ielts-card" class="card-box" style="width: ${cardWidth}px; height: ${cardHeight}px; display: ${isMinimized ? "none" : "flex"}">
        
        <!-- Header có thể kéo di chuyển -->
        <div class="drag-header" id="drag-header" title="Nhấp giữ thanh này để kéo di chuyển thẻ">
          <div class="tabs-group">
            <button class="tab-btn ${activeTab === "text" ? "active" : ""}" id="tab-text" title="Chỉ xem văn bản">📝 Văn bản</button>
            <button class="tab-btn ${activeTab === "image" ? "active" : ""}" id="tab-image" title="Chỉ xem hình ảnh">🖼️ Hình ảnh</button>
            <button class="tab-btn ${activeTab === "split" ? "active" : ""}" id="tab-split" title="Xem cùng lúc cả hình ảnh và văn bản">🌓 Cả hai</button>
          </div>
          <div class="header-right">
            <button class="btn-icon" id="btn-toggle-footer" title="Ẩn/Hiện thanh nút bên dưới để tối đa diện tích chữ & hình">🔽</button>
            <span class="drag-hint">⠿ Kéo</span>
            <button class="btn-icon" id="btn-minimize" title="Thu nhỏ thành bong bóng tròn">_</button>
            <button class="btn-icon btn-close-red" id="btn-close-widget" title="Tắt hoàn toàn widget (Có thể bật lại từ biểu tượng tiện ích)">✕</button>
          </div>
        </div>

        <!-- Body: Chứa Hình ảnh và Văn bản -->
        <div class="card-body" id="card-body">
          
          <!-- MỤC 2: HÌNH ẢNH (đặt lên trên khi chia đôi để tiện xem đề bài / chart bên trên, gõ chữ bên dưới) -->
          <div class="view-image" id="view-image" style="display: ${activeTab === "image" || activeTab === "split" ? "flex" : "none"}; ${activeTab === "split" ? "max-height: 48%;" : ""}">
            <img class="image-preview" id="image-preview" src="${savedImage}" style="display: ${savedImage ? "block" : "none"}" title="Nhấp để phóng to / thu nhỏ ảnh">
            
            <div class="empty-image-box" id="empty-image-box" style="display: ${savedImage ? "none" : "flex"}">
              <span class="empty-icon">📷</span>
              <p>Ấn <strong>Ctrl + V</strong> dán ảnh chụp màn hình</p>
            </div>
          </div>

          <!-- MỤC 1: VĂN BẢN (Hỗ trợ Highlight & tắt spellcheck) -->
          <div class="view-text" id="view-text" style="display: ${activeTab === "text" || activeTab === "split" ? "flex" : "none"}">
            <div class="text-area" id="text-area" contenteditable="true" spellcheck="false" autocomplete="off" autocorrect="off" autocapitalize="off" data-gramm="false" data-gramm_editor="false" data-enable-grammarly="false" placeholder="Nhấn Ctrl + V hoặc gõ văn bản tiếng Anh vào đây..."></div>
          </div>

        </div>

        <!-- Footer thanh công cụ -->
        <div class="card-footer" id="card-footer">
          <!-- Footer nút cho Text -->
          <div id="footer-text" style="display: ${activeTab === "text" ? "flex" : "none"}; width: 100%; justify-content: space-between; align-items: center;">
            <div style="display: flex; gap: 4px;">
              <button class="footer-btn" id="btn-trans" title="Dịch chuẩn ngữ cảnh (Ctrl+T)">🌐 Dịch</button>
              <button class="footer-btn" id="btn-hl" title="Tô màu Highlight (Ctrl+H)">🖍️</button>
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

          <!-- Footer nút cho Split (Cả hai) -->
          <div id="footer-split" style="display: ${activeTab === "split" ? "flex" : "none"}; width: 100%; justify-content: space-between; align-items: center;">
            <div style="display: flex; gap: 4px; align-items: center;">
              <button class="footer-btn" id="btn-trans-split" title="Dịch chuẩn ngữ cảnh (Ctrl+T)">🌐 Dịch</button>
              <button class="footer-btn" id="btn-hl-split" title="Tô màu Highlight (Ctrl+H)">🖍️</button>
              <button class="footer-btn" id="btn-tts-split">🔊 Đọc</button>
              <button class="footer-btn" id="btn-font-minus-split" title="Thu nhỏ chữ">A-</button>
              <button class="footer-btn" id="btn-font-plus-split" title="Phóng to chữ">A+</button>
              <label class="footer-btn" style="cursor: pointer;" title="Tải ảnh">
                📁 Ảnh
                <input type="file" id="file-input-split" accept="image/*" style="display:none;">
              </label>
            </div>
            <div style="display: flex; gap: 4px;">
              <button class="footer-btn btn-danger" id="btn-clear-text-split" title="Xóa chữ">Xóa chữ</button>
              <button class="footer-btn btn-danger" id="btn-clear-image-split" title="Xóa ảnh">Xóa ảnh</button>
            </div>
          </div>
        </div>

        <!-- Khung dịch chuẩn ngữ cảnh (Drawer kéo lên/xuống được) -->
        <div class="trans-drawer" id="trans-drawer">
          <div class="trans-drawer-header" id="trans-drawer-header" title="Nắm giữ và kéo lên / kéo xuống để chỉnh độ cao">
            <span>🌐 Dịch đối ứng song ngữ ═ (Kéo lên/xuống) ═</span>
            <div class="trans-drawer-actions">
              <button class="trans-drawer-btn" id="btn-copy-trans" title="Sao chép bản dịch">📋 Chép</button>
              <button class="trans-drawer-btn" id="btn-close-trans" title="Đóng khung dịch (Esc)">✕</button>
            </div>
          </div>
          <div class="trans-drawer-body" id="trans-body">Đang tải bản dịch...</div>
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
    setupFooterToggle(shadow);
    setupDrag(host, shadow.getElementById("drag-header"), cardEl);
    setupResize(host, cardEl, shadow.getElementById("resize-grip"));
    setupBubbleDragAndClick(host, cardEl, bubbleEl, shadow.getElementById("btn-minimize"));

    const btnCloseWidget = shadow.getElementById("btn-close-widget");
    if (btnCloseWidget) {
      btnCloseWidget.addEventListener("click", (e) => {
        e.stopPropagation();
        isEnabled = false;
        chrome.storage.local.set({ isEnabled: false });
        host.style.display = "none";
      });
    }
  }

  // --- CỐ ĐỊNH VÀ ÁP DỤNG TỌA ĐỘ AN TOÀN TRONG MÀN HÌNH ---
  function applyPosition(host) {
    if (!host) return;
    const card = host.shadowRoot?.getElementById("ielts-card");
    const currentW = (card && card.offsetWidth) || cardWidth || 380;
    const currentH = (card && card.offsetHeight) || cardHeight || 440;

    if (widgetPosition.left !== undefined) {
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

  // --- CHUYỂN TAB (VĂN BẢN, HÌNH ẢNH, HOẶC CẢ HAI) ---
  function switchTab(shadow, tab) {
    activeTab = tab;
    const tabText = shadow.getElementById("tab-text");
    const tabImage = shadow.getElementById("tab-image");
    const tabSplit = shadow.getElementById("tab-split");
    const viewText = shadow.getElementById("view-text");
    const viewImage = shadow.getElementById("view-image");
    const footerText = shadow.getElementById("footer-text");
    const footerImage = shadow.getElementById("footer-image");
    const footerSplit = shadow.getElementById("footer-split");

    if (tabText) tabText.classList.toggle("active", tab === "text");
    if (tabImage) tabImage.classList.toggle("active", tab === "image");
    if (tabSplit) tabSplit.classList.toggle("active", tab === "split");

    if (tab === "text") {
      viewText.style.display = "flex";
      viewText.style.flex = "1";
      viewImage.style.display = "none";
      if (footerText) footerText.style.display = "flex";
      if (footerImage) footerImage.style.display = "none";
      if (footerSplit) footerSplit.style.display = "none";
    } else if (tab === "image") {
      viewImage.style.display = "flex";
      viewImage.style.flex = "1";
      viewImage.style.maxHeight = "none";
      viewText.style.display = "none";
      if (footerText) footerText.style.display = "none";
      if (footerImage) footerImage.style.display = "flex";
      if (footerSplit) footerSplit.style.display = "none";
    } else if (tab === "split") {
      viewImage.style.display = "flex";
      viewImage.style.flex = "1";
      viewImage.style.maxHeight = "48%";
      viewText.style.display = "flex";
      viewText.style.flex = "1";
      if (footerText) footerText.style.display = "none";
      if (footerImage) footerImage.style.display = "none";
      if (footerSplit) footerSplit.style.display = "flex";
    }
    chrome.storage.local.set({ activeTab });
  }

  function setupTabs(shadow) {
    shadow.getElementById("tab-text").addEventListener("click", () => switchTab(shadow, "text"));
    shadow.getElementById("tab-image").addEventListener("click", () => switchTab(shadow, "image"));
    const tabSplit = shadow.getElementById("tab-split");
    if (tabSplit) {
      tabSplit.addEventListener("click", () => switchTab(shadow, "split"));
    }
  }

  // --- NÚT ẨN / HIỆN FOOTER ĐỂ TỐI ĐA KHÔNG GIAN ĐỌC ---
  function setupFooterToggle(shadow) {
    const btnToggle = shadow.getElementById("btn-toggle-footer");
    const footer = shadow.getElementById("card-footer");
    let isHidden = false;

    if (btnToggle && footer) {
      btnToggle.addEventListener("click", (e) => {
        e.stopPropagation();
        isHidden = !isHidden;
        if (isHidden) {
          footer.classList.add("collapsed");
          btnToggle.textContent = "🔼";
          btnToggle.title = "Hiện thanh công cụ bên dưới";
        } else {
          footer.classList.remove("collapsed");
          btnToggle.textContent = "🔽";
          btnToggle.title = "Ẩn thanh công cụ bên dưới để tối đa diện tích chữ & hình";
        }
      });
    }
  }

  // --- MỤC VĂN BẢN (TEXT) ---
  function setupTextControls(shadow) {
    const textArea = shadow.getElementById("text-area");
    const btnTrans = shadow.getElementById("btn-trans");
    const btnTransSplit = shadow.getElementById("btn-trans-split");
    const transDrawer = shadow.getElementById("trans-drawer");
    const transBody = shadow.getElementById("trans-body");
    const btnCloseTrans = shadow.getElementById("btn-close-trans");
    const btnCopyTrans = shadow.getElementById("btn-copy-trans");
    const btnHl = shadow.getElementById("btn-hl");
    const btnHlSplit = shadow.getElementById("btn-hl-split");
    const btnTts = shadow.getElementById("btn-tts");
    const btnTtsSplit = shadow.getElementById("btn-tts-split");
    const btnClearText = shadow.getElementById("btn-clear-text");
    const btnClearTextSplit = shadow.getElementById("btn-clear-text-split");
    const btnFontPlus = shadow.getElementById("btn-font-plus");
    const btnFontPlusSplit = shadow.getElementById("btn-font-plus-split");
    const btnFontMinus = shadow.getElementById("btn-font-minus");
    const btnFontMinusSplit = shadow.getElementById("btn-font-minus-split");

    // XÓA BỎ HOÀN TOÀN DẤU GẠCH ĐỎ CHÍNH TẢ
    textArea.spellcheck = false;
    textArea.setAttribute("spellcheck", "false");
    textArea.setAttribute("autocomplete", "off");
    textArea.setAttribute("autocorrect", "off");
    textArea.setAttribute("autocapitalize", "off");
    textArea.style.fontSize = `${fontSize}px`;

    if (savedText) {
      if (savedText.includes("<") && savedText.includes(">")) {
        textArea.innerHTML = savedText;
      } else {
        textArea.innerHTML = savedText.replace(/\n/g, "<br>");
      }
    }

    // Hàm lưu văn bản tức thời
    function saveTextNow() {
      if (!textArea) return;
      const current = textArea.innerHTML || textArea.innerText || "";
      savedText = current;
      try {
        chrome.storage.local.set({ savedText: current });
      } catch (e) {}
    }

    // Chức năng Highlight màu vàng & Hoàn tác Ctrl + Z
    let hlHistory = [];

    function applyHighlight() {
      hlHistory.push(textArea.innerHTML);
      document.execCommand("hiliteColor", false, "#fef08a");
      isUserDirty = true;
      saveTextNow();
    }

    if (btnHl) btnHl.addEventListener("click", applyHighlight);
    if (btnHlSplit) btnHlSplit.addEventListener("click", applyHighlight);

    // Chức năng Dịch chuẩn ngữ cảnh & Tìm đối ứng song ngữ 2 chiều
    let currentAlignSegments = [];

    function highlightAlignFromEn() {
      if (!currentAlignSegments || currentAlignSegments.length === 0 || !transBody) return;
      let sel = window.getSelection().toString().trim();
      if (!sel) {
        transBody.querySelectorAll(".trans-seg").forEach(el => {
          el.style.background = "transparent";
          el.style.color = "inherit";
        });
        return;
      }
      let firstMatch = null;
      currentAlignSegments.forEach((seg, idx) => {
        let span = transBody.querySelector(`.trans-seg[data-idx="${idx}"]`);
        if (!span) return;
        if (seg.en.toLowerCase().includes(sel.toLowerCase()) || sel.toLowerCase().includes(seg.en.toLowerCase())) {
          span.style.background = "#fed7aa";
          span.style.color = "#7c2d12";
          span.style.borderRadius = "3px";
          if (!firstMatch) firstMatch = span;
        } else {
          span.style.background = "transparent";
          span.style.color = "inherit";
        }
      });
      if (firstMatch) firstMatch.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function highlightAlignFromVi(idx) {
      if (!currentAlignSegments || !currentAlignSegments[idx] || !transBody) return;
      transBody.querySelectorAll(".trans-seg").forEach(el => {
        el.style.background = "transparent";
        el.style.color = "inherit";
      });
      let activeSpan = transBody.querySelector(`.trans-seg[data-idx="${idx}"]`);
      if (activeSpan) {
        activeSpan.style.background = "#fed7aa";
        activeSpan.style.color = "#7c2d12";
        activeSpan.style.borderRadius = "3px";
      }

      let enSentence = currentAlignSegments[idx].en;
      let fullText = textArea.innerText || textArea.textContent || "";
      let pos = fullText.indexOf(enSentence);
      if (pos !== -1) {
        let selection = window.getSelection();
        let range = document.createRange();
        let nodeIterator = document.createNodeIterator(textArea, NodeFilter.SHOW_TEXT);
        let textNode;
        let currentOffset = 0;
        let startNode = null, startOffset = 0, endNode = null, endOffset = 0;
        while ((textNode = nodeIterator.nextNode())) {
          let nextOffset = currentOffset + textNode.nodeValue.length;
          if (!startNode && pos >= currentOffset && pos <= nextOffset) {
            startNode = textNode;
            startOffset = pos - currentOffset;
          }
          if (!endNode && (pos + enSentence.length) >= currentOffset && (pos + enSentence.length) <= nextOffset) {
            endNode = textNode;
            endOffset = (pos + enSentence.length) - currentOffset;
            break;
          }
          currentOffset = nextOffset;
        }
        if (startNode && endNode) {
          range.setStart(startNode, startOffset);
          range.setEnd(endNode, endOffset);
          selection.removeAllRanges();
          selection.addRange(range);
          let rect = range.getBoundingClientRect();
          textArea.scrollBy({ top: rect.top - textArea.getBoundingClientRect().top - 40, behavior: "smooth" });
        }
      }
    }

    textArea.addEventListener("mouseup", highlightAlignFromEn);
    textArea.addEventListener("keyup", highlightAlignFromEn);

    function translateContext() {
      let queryText = window.getSelection().toString().trim();
      if (!queryText) {
        queryText = (textArea.innerText || textArea.textContent || "").trim();
      }
      if (!queryText) return;

      if (transDrawer) transDrawer.style.display = "flex";
      if (transBody) transBody.textContent = "⏳ Đang phân tích ngữ cảnh và dịch đối ứng song ngữ...";

      const url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=vi&dt=t&dt=bd&dt=rm&q=" + encodeURIComponent(queryText);
      fetch(url)
        .then(r => r.json())
        .then(data => {
          currentAlignSegments = [];
          if (transBody) transBody.innerHTML = "";
          let segments = (data[0] || []).filter(item => item && item[0] && item[1]);

          segments.forEach((seg, idx) => {
            let cleanVi = seg[0].trim();
            let span = document.createElement("span");
            span.className = "trans-seg";
            span.dataset.idx = idx;
            span.textContent = cleanVi;
            span.style.cursor = "pointer";
            span.title = "Nhấp để tìm câu tiếng Anh tương ứng";
            span.addEventListener("click", () => highlightAlignFromVi(idx));
            span.addEventListener("mouseup", () => highlightAlignFromVi(idx));
            if (transBody) {
              transBody.appendChild(span);
              transBody.appendChild(document.createTextNode(" "));
            }
            currentAlignSegments.push({ en: seg[1].trim(), vi: cleanVi });
          });

          if (data.length > 1 && data[1]) {
            let lines = [];
            for (let pos of data[1]) {
              let part = pos[0];
              let meanings = (pos[1] || []).slice(0, 5).join(", ");
              lines.push(`• (${part}) ${meanings}`);
            }
            if (lines.length > 0) {
              let div = document.createElement("div");
              div.style.cssText = "margin-top: 8px; font-size: 11px; color: #64748b; white-space: pre-wrap;";
              div.textContent = "\n📚 Các nét nghĩa theo ngữ cảnh:\n" + lines.join("\n");
              if (transBody) transBody.appendChild(div);
            }
          }

          highlightAlignFromEn();
        })
        .catch(() => {
          if (transBody) transBody.textContent = "Không thể kết nối máy chủ dịch (vui lòng kiểm tra kết nối mạng).";
        });
    }

    if (btnTrans) btnTrans.addEventListener("click", translateContext);
    if (btnTransSplit) btnTransSplit.addEventListener("click", translateContext);
    if (btnCloseTrans) {
      btnCloseTrans.addEventListener("click", () => {
        if (transDrawer) transDrawer.style.display = "none";
      });
    }
    if (btnCopyTrans) {
      btnCopyTrans.addEventListener("click", () => {
        if (transBody && transBody.textContent) {
          navigator.clipboard.writeText(transBody.textContent).then(() => {
            btnCopyTrans.textContent = "✓ Đã chép";
            setTimeout(() => { btnCopyTrans.textContent = "📋 Chép"; }, 1500);
          });
        }
      });
    }

    // KÉO THANH TIÊU ĐỀ ĐỂ ĐIỀU CHỈNH ĐỘ CAO KHUNG DỊCH (SPLITTER DRAG)
    const transDrawerHeader = shadow.getElementById("trans-drawer-header");
    let isDraggingDrawer = false;
    let startDrawerY = 0;
    let startDrawerH = 160;

    let transFontSize = 13;
    chrome.storage.local.get({ transDrawerHeight: 160, transFontSize: 13 }, (res) => {
      if (res.transDrawerHeight && transDrawer) {
        transDrawer.style.setProperty("height", `${res.transDrawerHeight}px`, "important");
      }
      if (res.transFontSize) {
        transFontSize = res.transFontSize;
        if (transBody) transBody.style.fontSize = `${transFontSize}px`;
      }
    });

    if (transDrawerHeader && transDrawer) {
      transDrawerHeader.addEventListener("mousedown", (e) => {
        if (e.target.closest("button")) return;
        isDraggingDrawer = true;
        startDrawerY = e.clientY;
        startDrawerH = transDrawer.offsetHeight || 160;
        document.body.style.userSelect = "none";
        e.preventDefault();
        e.stopPropagation();
      });

      window.addEventListener("mousemove", (e) => {
        if (!isDraggingDrawer) return;
        const delta = startDrawerY - e.clientY;
        const card = shadow.getElementById("ielts-card");
        const maxH = card ? Math.max(120, card.offsetHeight - 50) : 350;
        const newH = Math.max(55, Math.min(maxH, startDrawerH + delta));
        transDrawer.style.setProperty("height", `${newH}px`, "important");
        chrome.storage.local.set({ transDrawerHeight: newH });
      }, true);

      window.addEventListener("mouseup", () => {
        if (isDraggingDrawer) {
          isDraggingDrawer = false;
          document.body.style.userSelect = "";
        }
      }, true);
    }

    // CTRL + LĂN CHUỘT ĐỂ PHÓNG TO / THU NHỎ CỠ CHỮ TRỰC TIẾP (CẢ 2 KHUNG)
    textArea.addEventListener("wheel", (e) => {
      if (e.ctrlKey) {
        e.preventDefault();
        adjustFontSize(e.deltaY < 0 ? 1 : -1);
      }
    }, { passive: false });

    function adjustTransFontSize(delta) {
      const target = transFontSize + delta;
      if (target >= 10 && target <= 28) {
        transFontSize = target;
        if (transBody) transBody.style.fontSize = `${transFontSize}px`;
        chrome.storage.local.set({ transFontSize });
      }
    }

    if (transBody) {
      transBody.addEventListener("wheel", (e) => {
        if (e.ctrlKey) {
          e.preventDefault();
          adjustTransFontSize(e.deltaY < 0 ? 1 : -1);
        }
      }, { passive: false });
    }

    // Phím tắt Ctrl + H để Highlight, Ctrl + T để Dịch, Ctrl + Z để hoàn tác highlight
    textArea.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === "h" || e.key === "H")) {
        e.preventDefault();
        applyHighlight();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === "t" || e.key === "T")) {
        e.preventDefault();
        translateContext();
      } else if (e.key === "Escape") {
        if (transDrawer && transDrawer.style.display !== "none") {
          transDrawer.style.display = "none";
        }
      } else if ((e.ctrlKey || e.metaKey) && (e.key === "z" || e.key === "Z") && !e.shiftKey) {
        if (hlHistory.length > 0) {
          e.preventDefault();
          textArea.innerHTML = hlHistory.pop();
          isUserDirty = true;
          saveTextNow();
        }
      }
    });

    function onUserTyping() {
      hlHistory = [];
      isUserDirty = true;
      saveTextNow();
    }

    // Tự động lưu văn bản liên tục trên mọi thao tác gõ
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
    function clearTextAction() {
      textArea.innerHTML = "";
      savedText = "";
      isUserDirty = true;
      chrome.storage.local.set({ savedText: "" });
    }
    if (btnClearText) btnClearText.addEventListener("click", clearTextAction);
    if (btnClearTextSplit) btnClearTextSplit.addEventListener("click", clearTextAction);

    // KHI RỜI TAB HOẶC RỜI CỬA SỔ
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
    function playSpeech() {
      const text = (textArea.innerText || textArea.textContent || "").trim();
      if (!text || !("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();
      setTimeout(() => {
        const u = new SpeechSynthesisUtterance(text);
        u.lang = "en-US";
        u.rate = 0.95;
        window.speechSynthesis.speak(u);
      }, 50);
    }
    if (btnTts) btnTts.addEventListener("click", playSpeech);
    if (btnTtsSplit) btnTtsSplit.addEventListener("click", playSpeech);

    // Tăng giảm cỡ chữ
    function adjustFontSize(delta) {
      const target = fontSize + delta;
      if (target >= 11 && target <= 26) {
        fontSize = target;
        textArea.style.fontSize = `${fontSize}px`;
        chrome.storage.local.set({ fontSize });
      }
    }
    if (btnFontPlus) btnFontPlus.addEventListener("click", () => adjustFontSize(2));
    if (btnFontPlusSplit) btnFontPlusSplit.addEventListener("click", () => adjustFontSize(2));
    if (btnFontMinus) btnFontMinus.addEventListener("click", () => adjustFontSize(-2));
    if (btnFontMinusSplit) btnFontMinusSplit.addEventListener("click", () => adjustFontSize(-2));
  }

  // --- MỤC HÌNH ẢNH (IMAGE) ---
  function setupImageControls(shadow) {
    const imagePreview = shadow.getElementById("image-preview");
    const emptyBox = shadow.getElementById("empty-image-box");
    const fileInput = shadow.getElementById("file-input");
    const fileInputSplit = shadow.getElementById("file-input-split");
    const btnClearImage = shadow.getElementById("btn-clear-image");
    const btnClearImageSplit = shadow.getElementById("btn-clear-image-split");
    const card = shadow.getElementById("ielts-card");

    function renderImage(dataUrl) {
      savedImage = dataUrl;
      imagePreview.src = dataUrl;
      imagePreview.style.display = "block";
      emptyBox.style.display = "none";
      chrome.storage.local.set({ savedImage: dataUrl });
    }

    function onFileChosen(e) {
      const file = e.target.files[0];
      if (file && file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (evt) => renderImage(evt.target.result);
        reader.readAsDataURL(file);
      }
    }

    if (fileInput) fileInput.addEventListener("change", onFileChosen);
    if (fileInputSplit) fileInputSplit.addEventListener("change", onFileChosen);

    // Xóa ảnh
    function clearImageAction() {
      savedImage = "";
      imagePreview.src = "";
      imagePreview.style.display = "none";
      emptyBox.style.display = "flex";
      chrome.storage.local.set({ savedImage: "" });
    }
    if (btnClearImage) btnClearImage.addEventListener("click", clearImageAction);
    if (btnClearImageSplit) btnClearImageSplit.addEventListener("click", clearImageAction);

    // Nhấp vào ảnh để phóng to chi tiết / thu nhỏ vừa vặn
    let isZoomed = false;
    imagePreview.addEventListener("click", () => {
      isZoomed = !isZoomed;
      if (isZoomed) {
        imagePreview.style.objectFit = "cover";
        imagePreview.style.cursor = "zoom-out";
      } else {
        imagePreview.style.objectFit = "contain";
        imagePreview.style.cursor = "zoom-in";
      }
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
            if (activeTab === "text") {
              switchTab(shadow, "split"); // Chuyển sang Cả hai để xem vừa ảnh vừa bài
            }
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

      const newW = Math.max(240, Math.min(maxW, startW + (e.clientX - startX)));
      const newH = Math.max(160, Math.min(maxH, startH + (e.clientY - startY)));

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

    bubble.title = "Nhấp chuột trái để mở lại thẻ (Chuột phải để tắt hoàn toàn)";
    bubble.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      isEnabled = false;
      chrome.storage.local.set({ isEnabled: false });
      host.style.display = "none";
    });

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

      if (Math.hypot(deltaX, deltaY) > 8) {
        const bubbleSize = 46;
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

      if (elapsed < 350 || moveDistance < 10) {
        openCard();
      } else {
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
