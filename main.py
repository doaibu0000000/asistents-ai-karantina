import barantin
import json
from datetime import datetime  # <-- Tambahkan library tanggal bawaan Python

if __name__ == "__main__":
    print("[*] Memulai Bot Barantin...")

    if barantin.login():
        print("[*] Sesi terverifikasi. Mulai mengakses dashboard data...\n")

        url_filter_ptk = "https://api3.karantinaindonesia.go.id/barantin-sys/ptk/filter"
        print(f"[*] Sedang mengambil data dari: {url_filter_ptk}...")

        # AMBIL TANGGAL HARI INI SECARA REAL-TIME (Format otomatis: YYYY-MM-DD)
        tanggal_hari_ini = datetime.now().strftime("%Y-%m-%d")

        # Payload aman & otomatis mengikuti tanggal komputer berjalan
        payload_filter = {
            "dFrom": tanggal_hari_ini,  # <-- Besok otomatis berubah jadi "2026-06-11"
            "dTo": tanggal_hari_ini,    # <-- Besok otomatis berubah jadi "2026-06-11"
            "search": "AJU",            # <-- TETAP PAKAI "AJU" karena terbukti ampuh dan lolos Error 500
            "jenis_karantina": "",
            "upt_id": "3200",
            "kode_satpel": "3200",
            "pengguna_jasa_id": ""
        }

        # Tembak menggunakan data filter
        data_ptk = barantin.get_dashboard_data(url_filter_ptk, json_data=payload_filter)

        if data_ptk:
            print(f"[+] BERHASIL MENGAMBIL DATA FILTER PTK TANGGAL ({tanggal_hari_ini}):")
            print(json.dumps(data_ptk, indent=4))
        else:
            print("[-] Gagal menarik data filter ptk.")