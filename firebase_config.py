"""
firebase_config.py
Konfigurasi koneksi ke Firebase Firestore (GCP).
Mengelola penyimpanan dan pengambilan data scan WiFi secara real-time.
"""

import os
from datetime import datetime

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("[WARN] firebase-admin tidak terinstall. Jalankan: pip install firebase-admin")


# ─────────────────────────────────────────
# Inisialisasi Firebase App
# ─────────────────────────────────────────
_db = None

def _init_firebase():
    """Inisialisasi koneksi Firebase (dipanggil sekali saja)."""
    global _db

    if not FIREBASE_AVAILABLE:
        return None

    if _db is not None:
        return _db

    try:
        # Cek apakah app sudah diinisialisasi
        if not firebase_admin._apps:
            key_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")

            if not os.path.exists(key_path):
                raise FileNotFoundError(
                    "serviceAccountKey.json tidak ditemukan!\n"
                    "Download dari: Firebase Console → Project Settings → Service Accounts → Generate new private key\n"
                    f"Letakkan file di: {key_path}"
                )

            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)

        _db = firestore.client()
        print("[OK] Firebase Firestore berhasil terhubung.")
        return _db

    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Gagal inisialisasi Firebase: {e}")
        return None


# ─────────────────────────────────────────
# Upload hasil scan ke Firestore
# ─────────────────────────────────────────
def upload_scan_result(networks: list[dict]) -> str | None:
    """
    Upload satu sesi scan (list of networks) ke Firestore.
    Struktur koleksi: wifi_scans / {scan_id} / networks (sub-collection)

    Return: scan_id jika berhasil, None jika gagal.
    """
    db = _init_firebase()
    if db is None:
        print("[SKIP] Firebase tidak tersedia, data tidak disimpan.")
        return None

    try:
        # Dokumen utama untuk satu sesi scan
        scan_doc = {
            "timestamp"     : datetime.now().isoformat(),
            "total_networks": len(networks),
            "networks"      : networks,  # simpan semua sekaligus dalam satu doc
        }

        # Tambah ke koleksi 'wifi_scans' dengan auto-generated ID
        doc_ref = db.collection("wifi_scans").add(scan_doc)
        scan_id = doc_ref[1].id

        print(f"[OK] {len(networks)} jaringan tersimpan ke Firestore. Doc ID: {scan_id}")
        return scan_id

    except Exception as e:
        print(f"[ERROR] Gagal upload ke Firestore: {e}")
        return None


# ─────────────────────────────────────────
# Ambil histori scan dari Firestore
# ─────────────────────────────────────────
def get_scan_history(limit: int = 20) -> list[dict]:
    """
    Ambil histori hasil scan dari Firestore.
    Return list of scan documents, diurutkan dari terbaru.
    """
    db = _init_firebase()
    if db is None:
        return _dummy_history()

    try:
        docs = (
            db.collection("wifi_scans")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )

        history = []
        for doc in docs:
            data = doc.to_dict()
            data["doc_id"] = doc.id
            history.append(data)

        return history

    except Exception as e:
        print(f"[ERROR] Gagal mengambil histori: {e}")
        return []


def get_latest_scan() -> list[dict]:
    """Ambil hasil scan terbaru dari Firestore."""
    history = get_scan_history(limit=1)
    if history:
        return history[0].get("networks", [])
    return []


# ─────────────────────────────────────────
# Dummy data (fallback tanpa Firebase)
# ─────────────────────────────────────────
def _dummy_history() -> list[dict]:
    """Return dummy history untuk keperluan demo/testing."""
    from datetime import timedelta
    import random

    dummy = []
    for i in range(5):
        ts = (datetime.now() - timedelta(hours=i)).isoformat()
        dummy.append({
            "doc_id"        : f"dummy_{i}",
            "timestamp"     : ts,
            "total_networks": 8,
            "networks"      : [],
        })
    return dummy
