import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import json
import os

def init_firebase():
    """Inisialisasi Firebase - support Streamlit Cloud secrets & lokal."""
    if firebase_admin._apps:
        return firestore.client()

    try:
        # Coba dari Streamlit Cloud secrets dulu
        if "firebase" in st.secrets:
            cred_dict = dict(st.secrets["firebase"])
            # private_key perlu decode \n
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cred_dict)
            print("[OK] Firebase terhubung via Streamlit Secrets")

        # Fallback: pakai file lokal (untuk development di laptop)
        elif os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
            print("[OK] Firebase terhubung via serviceAccountKey.json (lokal)")

        else:
            print("[WARN] Tidak ada kredensial Firebase. Mode offline.")
            return None

        firebase_admin.initialize_app(cred)
        return firestore.client()

    except Exception as e:
        print(f"[ERROR] Firebase gagal terhubung: {e}")
        return None


def upload_scan(db, scan_results):
    """Upload hasil scan ke Firestore."""
    if db is None:
        print("[WARN] Firebase tidak tersedia, data tidak disimpan.")
        return None
    try:
        collection = db.collection("wifi_scans")
        doc_ref = collection.add(scan_results)
        print(f"[OK] {len(scan_results.get('networks', []))} jaringan tersimpan ke Firestore.")
        return doc_ref
    except Exception as e:
        print(f"[ERROR] Gagal upload ke Firestore: {e}")
        return None


def get_history(db, limit=10):
    """Ambil histori scan dari Firestore."""
    if db is None:
        return []
    try:
        docs = db.collection("wifi_scans")\
                 .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                 .limit(limit)\
                 .stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"[ERROR] Gagal ambil histori: {e}")
        return []
