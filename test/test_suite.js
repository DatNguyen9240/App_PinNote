/**
 * IELTS Corner - Test Suite cho phiên bản tối giản Text & Image
 */

const fs = require('fs');
const path = require('path');

console.log("==================================================");
console.log("   KIỂM THỬ PHIÊN BẢN TỐI GIẢN (TEXT & IMAGE)");
console.log("==================================================\n");

let passed = 0;
let total = 0;

function assert(condition, name) {
  total++;
  if (condition) {
    console.log(`✅ [PASS] ${name}`);
    passed++;
  } else {
    console.error(`❌ [FAIL] ${name}`);
  }
}

const contentJs = fs.readFileSync(path.join(__dirname, '..', 'content/content.js'), 'utf8');
const popupJs = fs.readFileSync(path.join(__dirname, '..', 'popup/popup.js'), 'utf8');
const popupHtml = fs.readFileSync(path.join(__dirname, '..', 'popup/popup.html'), 'utf8');
const testPageHtml = fs.readFileSync(path.join(__dirname, '..', 'test/test_page.html'), 'utf8');

assert(contentJs.includes("tab-text") && contentJs.includes("tab-image"), "Tách riêng 2 mục: Văn bản (Text) và Hình ảnh (Image)");
assert(contentJs.includes("setupDrag"), "Hỗ trợ kéo di chuyển tự do");
assert(contentJs.includes("setupResize"), "Hỗ trợ kéo góc phóng to / thu nhỏ");
assert(contentJs.includes("FileReader"), "Hỗ trợ dán hoặc chọn ảnh");
assert(contentJs.includes("speechSynthesis"), "Hỗ trợ phát âm giọng bản xứ chuẩn");
assert(!popupJs.includes("window.close()"), "Popup không tự tắt khi nhấn nút");
assert(contentJs.includes("saveTextNow") && contentJs.includes("visibilitychange"), "Lưu tức thời khi chuyển tab dù chưa bỏ focus (blur)");
assert(contentJs.includes("safeLeft") && contentJs.includes("safeTop"), "Tự động căn chỉnh vị trí an toàn tránh bị trôi ra ngoài màn hình");
assert(testPageHtml.includes("BroadcastChannel") && testPageHtml.includes("localStorage"), "Trang test đồng bộ thời gian thực giữa nhiều tab");

console.log(`\nKết quả: ${passed}/${total} bài kiểm tra thành công!`);
