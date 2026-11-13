document.addEventListener("DOMContentLoaded", () => {
  const toggleEnable = document.getElementById("toggle-enable");
  const btnFocusText = document.getElementById("btn-focus-paste");
  const btnFocusImage = document.getElementById("btn-focus-image");
  const btnFocusSplit = document.getElementById("btn-focus-split");
  const btnResetPos = document.getElementById("btn-reset-pos");
  const statusNotice = document.getElementById("status-notice");

  function showNotice(msg) {
    if (!statusNotice) return;
    statusNotice.textContent = msg;
    statusNotice.style.display = "block";
    setTimeout(() => {
      statusNotice.style.display = "none";
    }, 2000);
  }

  // Load saved state
  chrome.storage.local.get({ isEnabled: true }, (data) => {
    toggleEnable.checked = data.isEnabled;
  });

  // Bật / Tắt thẻ
  toggleEnable.addEventListener("change", (e) => {
    chrome.storage.local.set({ isEnabled: e.target.checked, forceShow: Date.now() });
    showNotice(e.target.checked ? "✓ Đã bật hiển thị thẻ" : "✕ Đã tạm ẩn thẻ");
  });

  // Chuyển sang mục Văn Bản
  btnFocusText.addEventListener("click", () => {
    chrome.storage.local.set({
      activeTab: "text",
      isEnabled: true,
      isMinimized: false,
      forceShow: Date.now()
    });
    showNotice("✓ Đang mở mục Văn Bản");
  });

  // Chuyển sang mục Hình Ảnh
  btnFocusImage.addEventListener("click", () => {
    chrome.storage.local.set({
      activeTab: "image",
      isEnabled: true,
      isMinimized: false,
      forceShow: Date.now()
    });
    showNotice("✓ Đang mở mục Hình Ảnh");
  });

  // Chuyển sang mục Cả Hai
  if (btnFocusSplit) {
    btnFocusSplit.addEventListener("click", () => {
      chrome.storage.local.set({
        activeTab: "split",
        isEnabled: true,
        isMinimized: false,
        forceShow: Date.now()
      });
      showNotice("✓ Đang mở mục Cả Văn Bản & Hình Ảnh");
    });
  }

  // Đặt lại vị trí về góc màn hình
  btnResetPos.addEventListener("click", () => {
    chrome.storage.local.set({
      isEnabled: true,
      isMinimized: false,
      position: { right: 24, bottom: 24 },
      cardWidth: 380,
      cardHeight: 440,
      forceShow: Date.now()
    });
    toggleEnable.checked = true;
    showNotice("✓ Đã đưa thẻ về góc dưới - phải!");
  });
});
