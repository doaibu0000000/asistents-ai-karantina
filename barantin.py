import base64
import os
import requests
import ddddocr
import config
import time
import json

TOKEN_FILE = "session_token.txt"

ocr = ddddocr.DdddOcr(show_ad=False)
ocr.set_ranges("0123456789")
session = requests.Session()


def simpan_session_data(data_json):
    """Menyimpan seluruh json response login (Token + Profil) ke file teks."""
    with open(TOKEN_FILE, mode="w", encoding="utf-8") as f:
        json.dump(data_json, f, indent=4)
    print("[+] Sesi Login Berhasil Disimpan")


def baca_session_data():
    """Membaca data sesi dari file jika ada."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, mode="r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return None
    return None


def ambil_captcha():
    try:
        response = session.get(config.url_captcha, headers=config.headers).json()
        captcha_token = response["token"]
        captcha = ocr.classification(base64.b64decode(response["image"].split(",")[1]))
        return captcha, captcha_token
    except Exception as e:
        print(f"[-] Gagal mengambil captcha : {e}")
        return None, None


def login_baru():
    captcha, token = ambil_captcha()
    if not captcha:
        return False

    payload = {
        "username": config.USERNAME,
        "password": config.PASSWORD,
        "app": "APP001",
        "ipaddress": "103.152.232.25",
        "captcha": captcha,
        "captchaToken": token,
        "location": {
            "timestamp": 1781070693295,
            "coords": {
                "accuracy": 50000,
                "latitude": -6.5444,
                "longitude": 107.6931,
                "altitude": None,
                "altitudeAccuracy": None,
                "heading": None,
                "speed": None
            }
        }
    }

    try:
        response = session.post(config.url_login, headers=config.headers, json=payload)
        if response.status_code == 200:
            res_json = response.json()
            if "data" in res_json:
                print("[+] LOGIN BERHASIL")

                access_token = res_json["data"]["accessToken"]
                session.headers.update({"Authorization": f"Bearer {access_token}"})

                # Simpan bungkusan penuh (Token + Profil) ke dalam satu file teks
                simpan_session_data(res_json["data"])

                # Cetak data ke konsol saat login sukses pertama kali
                print("\n=== DATA PROFIL USER ===")
                for key, value in res_json["data"].items():
                    if key != "detil" and key != "accessToken":
                        print(f"{key.upper()} : {value}")
                print("========================\n")

                return True
        return False

    except Exception as e:
        print(f"[-] Terjadi Kesalahan saat request login: {e}")
        return False


def login():
    """Mengecek keaktifan sesi melalui audit waktu JWT lokal secara aman."""
    print("[*] Mengecek sesi login sebelumnya...")
    session_data = baca_session_data()

    if session_data and "accessToken" in session_data:
        token_lama = session_data["accessToken"]

        try:
            # 1. Bongkar isi JWT bagian payload secara lokal
            payload_b64 = token_lama.split(".")[1]
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            jwt_decoded = json.loads(base64.b64decode(payload_b64).decode("utf-8"))

            waktu_expired = jwt_decoded.get("exp", 0)
            waktu_sekarang = int(time.time())

            # 2. Jika secara waktu token terbukti masih aktif/hidup
            if waktu_expired and waktu_sekarang < waktu_expired:
                sisa_menit = (waktu_expired - waktu_sekarang) // 60
                print(f"[OK] Sesi login AKTIF! (Token aman untuk {sisa_menit} menit ke depan)")

                # Pasang Bearer token kembali ke headers global session
                session.headers.update({"Authorization": f"Bearer {token_lama}"})

                # 3. Akses dan tampilkan data profil ke konsol langsung dari data file teks
                print("\n=== DATA PROFIL SESI AKTIF ===")
                for key, value in session_data.items():
                    if key != "detil" and key != "accessToken":
                        print(f"{key.upper()} : {value}")

                waktu_terformat = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(waktu_expired))
                print(f"KEDALUWARSA PADA : {waktu_terformat}")
                print("==============================\n")

                return True  # Sukses bypass login baru!
            else:
                print("[-] Sesi login sebelumnya sudah KEDALUWARSA secara waktu.")

        except Exception as e:
            print(f"[-] Gagal membaca struktur data sesi lama: {e}")

    print("[*] Melakukan proses login baru")
    return login_baru()


def get_dashboard_data(url_target, json_data=None):
    """Fungsi super kokoh: Mendukung GET/POST, Bearer/Basic Auth, dan memaksa header JSON."""
    session_data = baca_session_data()
    if not session_data:
        print("[-] Data sesi tidak ditemukan. Silakan login dulu.")
        return None

    method = "POST" if json_data else "GET"

    token_bearer = session_data.get("accessToken")
    akun_mentah = f"{config.DASHBOARD_USER}:{config.DASHBOARD_PASS}"
    akun_encoded = base64.b64encode(akun_mentah.encode("utf-8")).decode("utf-8")

    # Header Versi Bearer (Wajib ditambahkan Content-Type untuk POST Payload)
    headers_bearer = config.headers.copy()
    headers_bearer["Authorization"] = f"Bearer {token_bearer}"
    headers_bearer["Content-Type"] = "application/json"  # <-- KUNCI UTAMA NYA DI SINI

    # Header Versi Basic
    headers_basic = config.headers.copy()
    headers_basic["Authorization"] = f"Basic {akun_encoded}"
    headers_basic["Content-Type"] = "application/json"  # <-- KUNCI UTAMA NYA DI SINI

    if "api3.karantinaindonesia.go.id" in url_target:
        headers_bearer["Host"] = "api3.karantinaindonesia.go.id"
        headers_basic["Host"] = "api3.karantinaindonesia.go.id"

    try:
        # Eksekusi request menggunakan session global
        response = session.request(method, url_target, headers=headers_bearer, json=json_data)

        if response.status_code == 200:
            try:
                return response.json()
            except Exception:
                print(f"[!] Server merespon 200 tetapi isinya bukan JSON. Respon asli: {response.text}")
                return None

        elif response.status_code in [401, 403]:
            # Fallback ke Basic jika Bearer ditolak
            response_alt = session.request(method, url_target, headers=headers_basic, json=json_data)
            if response_alt.status_code == 200:
                return response_alt.json()
            else:
                print(f"[-] Kedua otentikasi ditolak. Status Akhir: {response_alt.status_code}")
                return None
        else:
            print(f"[-] Gagal. Status Code: {response.status_code}. Respon Server: {response.text}")
            return None

    except Exception as e:
        print(f"[-] Terjadi kesalahan saat request dashboard: {e}")
        return None