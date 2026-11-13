/**
 * IELTS Corner - Test Suite cho phiên bản tối giản Text & Image
 */

const fs = require('fs');
const path = require('path');

console.log("==================================================");
console.log("   KIỂM THỬ TỐI ƯU GIAO DIỆN & DESKTOP APP");
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
assert(contentJs.includes("tab-split"), "Chế độ xem đồng thời cả chữ và ảnh (Split View: Cả hai)");
assert(contentJs.includes('spellcheck="false"'), "Đã tắt hoàn toàn dấu gạch đỏ chính tả (spellcheck=false)");
assert(contentJs.includes("btn-toggle-footer"), "Có nút ẩn/hiện thanh công cụ dưới đáy để mở rộng không gian đọc");
assert(contentJs.includes("setupDrag"), "Hỗ trợ kéo di chuyển tự do");
assert(contentJs.includes("setupResize"), "Hỗ trợ kéo góc phóng to / thu nhỏ");
assert(contentJs.includes("FileReader"), "Hỗ trợ dán hoặc chọn ảnh");
assert(contentJs.includes("speechSynthesis"), "Hỗ trợ phát âm giọng bản xứ chuẩn");
assert(!popupJs.includes("window.close()"), "Popup không tự tắt khi nhấn nút");
assert(contentJs.includes("saveTextNow") && contentJs.includes("visibilitychange"), "Lưu tức thời khi chuyển tab dù chưa bỏ focus (blur)");
assert(contentJs.includes("safeLeft") && contentJs.includes("safeTop"), "Tự động căn chỉnh vị trí an toàn tránh bị trôi ra ngoài màn hình");
assert(testPageHtml.includes("BroadcastChannel") && testPageHtml.includes("localStorage"), "Trang test đồng bộ thời gian thực giữa nhiều tab");
assert(fs.existsSync(path.join(__dirname, '..', 'desktop_app/app.py')), "Ứng dụng Desktop Python Always-on-top đã sẵn sàng");
assert(fs.existsSync(path.join(__dirname, '..', 'desktop_app/standalone_window.html')), "Cửa sổ Web Standalone đã sẵn sàng");
assert(fs.existsSync(path.join(__dirname, '..', 'Chay_App_IELTS_Corner.bat')), "File chạy 1-click Desktop App .bat đã sẵn sàng");

const appPy = fs.readFileSync(path.join(__dirname, '..', 'desktop_app/app.py'), 'utf8');
const standaloneHtml = fs.readFileSync(path.join(__dirname, '..', 'desktop_app/standalone_window.html'), 'utf8');

assert(appPy.includes("highlight_selection") && appPy.includes("hl_yellow"), "Desktop App hỗ trợ Highlight từ vựng và lưu trữ highlight");
assert(appPy.includes("create_new_note") && appPy.includes("notes"), "Desktop App hỗ trợ tạo và chuyển đổi nhiều Note");
assert(standaloneHtml.includes("applyHighlight") && standaloneHtml.includes("hiliteColor"), "Web Standalone hỗ trợ Highlight nhiều màu và lưu trữ");
assert(standaloneHtml.includes("createNewNote") && standaloneHtml.includes("notes"), "Web Standalone hỗ trợ tạo và chuyển đổi nhiều Note");
assert(contentJs.includes("applyHighlight") && contentJs.includes("btn-hl"), "Chrome Extension hỗ trợ phím tắt và nút Highlight");
assert(appPy.includes("translate_context") && appPy.includes("client=gtx"), "Desktop App hỗ trợ Dịch chuẩn ngữ cảnh IELTS (Ctrl + T)");
assert(standaloneHtml.includes("translateContext") && standaloneHtml.includes("client=gtx"), "Web Standalone hỗ trợ Dịch chuẩn ngữ cảnh IELTS (Ctrl + T)");
assert(contentJs.includes("translateContext") && contentJs.includes("btn-trans"), "Chrome Extension hỗ trợ Dịch chuẩn ngữ cảnh IELTS (Ctrl + T)");
assert(appPy.includes("DetachedNoteWindow") && appPy.includes("detach_note") && appPy.includes("reattach_note"), "Desktop App hỗ trợ tách và gộp Note thành cửa sổ riêng biệt");
assert(appPy.includes("on_tab_motion") && appPy.includes("ghost"), "Desktop App hỗ trợ nắm kéo chuột tab Note ra ngoài để tách cửa sổ (Tear-off tab)");
assert(standaloneHtml.includes("detachNoteWeb"), "Web Standalone hỗ trợ mở Note trong cửa sổ riêng biệt");
assert(appPy.includes("on_en_selection_change") && appPy.includes("on_vi_selection_change"), "Desktop App hỗ trợ bôi đen tìm câu/từ đối ứng song ngữ 2 chiều");
assert(standaloneHtml.includes("highlightAlignFromEn") && standaloneHtml.includes("highlightAlignFromVi"), "Web Standalone hỗ trợ tìm câu/từ đối ứng song ngữ 2 chiều");
assert(contentJs.includes("highlightAlignFromEn") && contentJs.includes("highlightAlignFromVi"), "Chrome Extension hỗ trợ tìm câu/từ đối ứng song ngữ 2 chiều");
assert(appPy.includes("ensure_single_instance") && appPy.includes("os._exit(0)"), "Desktop App có khóa đơn phiên chống mở đè nhiều app và thoát sạch sẽ");
assert(contentJs.includes("btn-close-widget"), "Chrome Extension có nút đóng hoàn toàn (✕) để không tự hiện lại");

console.log(`\nKết quả: ${passed}/${total} bài kiểm tra thành công!`);
