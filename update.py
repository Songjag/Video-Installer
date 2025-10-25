import os
import requests
import zipfile
import shutil

# --- Cấu hình ---
GITHUB_API = "https://api.github.com/repos/Songjag/Video-Installer/releases/latest"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(CURRENT_DIR, "version")
MAIN_EXE = os.path.join(CURRENT_DIR, "main.exe")

def get_local_version():
    """Đọc phiên bản hiện tại từ file version."""
    if not os.path.exists(VERSION_FILE):
        return "none"
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def save_local_version(version: str):
    """Lưu phiên bản mới nhất vào file version."""
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(version.strip())

def download_and_update():
    print("🔍 Kiểm tra bản cập nhật...")

    # --- B1: Lấy thông tin bản phát hành mới nhất ---
    r = requests.get(GITHUB_API, timeout=10)
    if r.status_code != 200:
        print("❌ Không thể truy cập GitHub API.")
        return
    
    data = r.json()
    remote_version = data.get("tag_name", "unknown")
    title = data.get("name", "")
    assets = data.get("assets", [])

    local_version = get_local_version()
    print(f"📦 Phiên bản hiện tại: {local_version}")
    print(f"📢 Phiên bản GitHub: {remote_version} ({title})")

    # --- B2: So sánh phiên bản ---
    if local_version == remote_version:
        print("✅ Bạn đang ở phiên bản mới nhất, không cần cập nhật.")
        return

    # --- B3: Tải file zip mới ---
    if not assets:
        print("❌ Không có file .zip nào trong release.")
        return

    asset = next((a for a in assets if a["name"].endswith(".zip")), None)
    if not asset:
        print("❌ Không tìm thấy file .zip trong danh sách assets.")
        return

    zip_url = asset["browser_download_url"]
    zip_name = asset["name"]
    zip_path = os.path.join(CURRENT_DIR, zip_name)

    print(f"⬇️ Đang tải xuống {zip_url} ...")
    z = requests.get(zip_url, stream=True)
    with open(zip_path, "wb") as f:
        shutil.copyfileobj(z.raw, f)

    # --- B4: Giải nén và ghi đè ---
    print("📂 Giải nén và cập nhật tệp...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(CURRENT_DIR)

    os.remove(zip_path)
    save_local_version(remote_version)

    print(f"✅ Cập nhật hoàn tất! Phiên bản hiện tại: {remote_version}")

    # --- B5: Khởi động lại chương trình chính (tùy chọn) ---
    if os.path.exists(MAIN_EXE):
        print("🚀 Khởi động lại main.exe ...")
        os.startfile(MAIN_EXE)

if __name__ == "__main__":
    try:
        download_and_update()
    except Exception as e:
        print(f"⚠️ Lỗi cập nhật: {e}")
        input("Nhấn Enter để thoát...")
