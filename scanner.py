"""
scanner.py
Modul scanning jaringan WiFi menggunakan pywifi.
Mengumpulkan: SSID, BSSID, RSSI, Channel, Frekuensi (2.4/5 GHz)
Hasil scan langsung dikirim ke Firebase Firestore.
"""

import time
import math
from datetime import datetime

try:
    import pywifi
    from pywifi import const
    PYWIFI_AVAILABLE = True
except ImportError:
    PYWIFI_AVAILABLE = False

from firebase_config import upload_scan_result


# ─────────────────────────────────────────
# Konversi frekuensi → channel
# ─────────────────────────────────────────
def freq_to_channel(freq_mhz: int) -> int:
    """Konversi frekuensi MHz ke nomor channel WiFi."""
    if 2412 <= freq_mhz <= 2484:
        if freq_mhz == 2484:
            return 14
        return (freq_mhz - 2407) // 5
    elif 5170 <= freq_mhz <= 5825:
        return (freq_mhz - 5000) // 5
    return 0


def freq_to_band(freq_mhz: int) -> str:
    """Tentukan band (2.4 GHz atau 5 GHz) dari frekuensi."""
    if 2400 <= freq_mhz <= 2500:
        return "2.4 GHz"
    elif 5000 <= freq_mhz <= 5900:
        return "5 GHz"
    return "Unknown"


# ─────────────────────────────────────────
# Konversi RSSI → kualitas sinyal
# ─────────────────────────────────────────
def rssi_to_quality(rssi: int) -> str:
    """Kategorikan kualitas sinyal berdasarkan nilai RSSI (dBm)."""
    if rssi >= -50:
        return "Excellent"
    elif rssi >= -60:
        return "Good"
    elif rssi >= -70:
        return "Fair"
    else:
        return "Poor"


# ─────────────────────────────────────────
# Scan WiFi menggunakan pywifi
# ─────────────────────────────────────────
def scan_wifi() -> list[dict]:
    """
    Pindai jaringan WiFi di sekitar menggunakan pywifi.
    Return list of dict dengan key: ssid, bssid, rssi, channel, frequency, band, quality.
    """
    if not PYWIFI_AVAILABLE:
        print("[WARN] pywifi tidak tersedia. Menggunakan data dummy untuk testing.")
        return _dummy_scan()

    try:
        wifi = pywifi.PyWiFi()
        iface = wifi.interfaces()[0]

        iface.scan()
        time.sleep(2)  # tunggu scan selesai

        results = iface.scan_results()
        networks = []

        for profile in results:
            freq_mhz = getattr(profile, "freq", 0)
            # pywifi kadang menyimpan frekuensi dalam kHz
            if freq_mhz > 100000:
                freq_mhz = freq_mhz // 1000

            channel  = freq_to_channel(freq_mhz)
            band     = freq_to_band(freq_mhz)
            rssi     = int(profile.signal)
            quality  = rssi_to_quality(rssi)

            networks.append({
                "ssid"      : profile.ssid or "(Hidden Network)",
                "bssid"     : profile.bssid,
                "rssi"      : rssi,
                "channel"   : channel,
                "frequency" : freq_mhz,
                "band"      : band,
                "quality"   : quality,
                "timestamp" : datetime.now().isoformat(),
            })

        # Urutkan dari sinyal terkuat
        networks.sort(key=lambda x: x["rssi"], reverse=True)
        return networks

    except Exception as e:
        print(f"[ERROR] Gagal scan WiFi: {e}")
        return []


# ─────────────────────────────────────────
# Data dummy (fallback jika pywifi tidak ada)
# ─────────────────────────────────────────
def _dummy_scan() -> list[dict]:
    """Generate data dummy untuk testing tanpa adapter WiFi nyata."""
    import random
    dummy_networks = [
        ("HomeNet_5G",   "AA:BB:CC:DD:EE:01", -42, 36, 5180),
        ("OfficeWifi",   "AA:BB:CC:DD:EE:02", -58,  6, 2437),
        ("Neighbor_2G",  "AA:BB:CC:DD:EE:03", -71,  6, 2437),
        ("CampusNet",    "AA:BB:CC:DD:EE:04", -80, 11, 2462),
        ("GuestNetwork", "AA:BB:CC:DD:EE:05", -65,  1, 2412),
        ("WiFi_5G_Fast", "AA:BB:CC:DD:EE:06", -48, 40, 5200),
        ("Telkom_IndH",  "AA:BB:CC:DD:EE:07", -74,  1, 2412),
        ("MYREPUBLIC",   "AA:BB:CC:DD:EE:08", -55, 11, 2462),
    ]

    networks = []
    for ssid, bssid, base_rssi, channel, freq in dummy_networks:
        rssi = base_rssi + random.randint(-3, 3)
        networks.append({
            "ssid"      : ssid,
            "bssid"     : bssid,
            "rssi"      : rssi,
            "channel"   : channel,
            "frequency" : freq,
            "band"      : freq_to_band(freq),
            "quality"   : rssi_to_quality(rssi),
            "timestamp" : datetime.now().isoformat(),
        })

    networks.sort(key=lambda x: x["rssi"], reverse=True)
    return networks


# ─────────────────────────────────────────
# Run standalone: scan lalu upload ke Firebase
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("=== WiFi Analyzer - Scanner ===")
    print("Memindai jaringan WiFi di sekitar...\n")

    networks = scan_wifi()

    if not networks:
        print("Tidak ada jaringan yang terdeteksi.")
    else:
        print(f"Ditemukan {len(networks)} jaringan:\n")
        print(f"{'SSID':<25} {'RSSI':>8} {'Ch':>4} {'Band':>8} {'Quality':<10}")
        print("-" * 60)
        for net in networks:
            print(f"{net['ssid']:<25} {net['rssi']:>5} dBm {net['channel']:>4} {net['band']:>8} {net['quality']:<10}")

        print("\nMengirim data ke Firebase Firestore...")
        scan_id = upload_scan_result(networks)
        print(f"Data berhasil disimpan. Scan ID: {scan_id}")
