"""
analyzer.py
Logika analisis interferensi channel WiFi dan rekomendasi channel optimal.
Mendukung frekuensi 2.4 GHz (channel 1-14) dan 5 GHz (channel 36-165).
"""

from collections import defaultdict


# ─────────────────────────────────────────
# Peta overlap channel (2.4 GHz)
# Channel yang non-overlapping: 1, 6, 11
# ─────────────────────────────────────────
OVERLAP_MAP_24 = {
    1:  [1, 2, 3, 4, 5],
    2:  [1, 2, 3, 4, 5, 6],
    3:  [1, 2, 3, 4, 5, 6, 7],
    4:  [2, 3, 4, 5, 6, 7, 8],
    5:  [3, 4, 5, 6, 7, 8, 9],
    6:  [4, 5, 6, 7, 8, 9, 10],
    7:  [5, 6, 7, 8, 9, 10, 11],
    8:  [6, 7, 8, 9, 10, 11, 12],
    9:  [7, 8, 9, 10, 11, 12, 13],
    10: [8, 9, 10, 11, 12, 13],
    11: [9, 10, 11, 12, 13],
    12: [10, 11, 12, 13, 14],
    13: [11, 12, 13, 14],
    14: [12, 13, 14],
}

# Channel yang tersedia untuk rekomendasi
CHANNELS_24  = [1, 6, 11]          # non-overlapping channels
CHANNELS_5   = list(range(36, 166, 4))  # 36, 40, 44, ..., 165


# ─────────────────────────────────────────
# Hitung skor interferensi per channel
# ─────────────────────────────────────────
def calculate_interference_score(networks: list[dict]) -> dict:
    """
    Hitung skor interferensi untuk setiap channel.
    Skor lebih tinggi = lebih banyak interferensi.

    Rumus:
    - Setiap jaringan di channel yang overlap menyumbang bobotnya
    - Bobot = 10^((RSSI + 100) / 20) — semakin kuat sinyal, semakin besar gangguan
    """
    scores = defaultdict(float)

    for net in networks:
        ch   = net.get("channel", 0)
        rssi = net.get("rssi", -100)
        band = net.get("band", "")

        if "2.4" in band and ch in OVERLAP_MAP_24:
            # Jaringan ini mengganggu semua channel yang overlap dengannya
            weight = 10 ** ((rssi + 100) / 20)
            for affected_ch in OVERLAP_MAP_24[ch]:
                scores[affected_ch] += weight

        elif "5" in band:
            # Di 5 GHz, channel tidak overlap (non-contiguous)
            weight = 10 ** ((rssi + 100) / 20)
            scores[ch] += weight

    return dict(scores)


# ─────────────────────────────────────────
# Hitung jumlah jaringan per channel
# ─────────────────────────────────────────
def count_networks_per_channel(networks: list[dict]) -> dict:
    """Return dict {channel: jumlah_jaringan}."""
    counts = defaultdict(int)
    for net in networks:
        ch = net.get("channel", 0)
        if ch > 0:
            counts[ch] += 1
    return dict(counts)


# ─────────────────────────────────────────
# Rekomendasi channel optimal
# ─────────────────────────────────────────
def recommend_channel(networks: list[dict]) -> dict:
    """
    Rekomendasikan channel terbaik untuk 2.4 GHz dan 5 GHz.

    Return dict:
    {
        "2.4GHz": {"channel": int, "reason": str, "score": float},
        "5GHz"  : {"channel": int, "reason": str, "score": float},
    }
    """
    scores = calculate_interference_score(networks)
    counts = count_networks_per_channel(networks)

    result = {}

    # ── 2.4 GHz ──
    best_24_ch    = None
    best_24_score = float("inf")

    for ch in CHANNELS_24:
        score = scores.get(ch, 0)
        if score < best_24_score:
            best_24_score = score
            best_24_ch    = ch

    net_on_best_24 = counts.get(best_24_ch, 0)
    result["2.4GHz"] = {
        "channel": best_24_ch,
        "score"  : round(best_24_score, 2),
        "networks_count": net_on_best_24,
        "reason" : (
            f"Channel {best_24_ch} memiliki interferensi paling rendah "
            f"({net_on_best_24} jaringan aktif di channel ini)"
        ),
    }

    # ── 5 GHz ──
    networks_5g = [n for n in networks if "5" in n.get("band", "")]

    if networks_5g:
        best_5_ch    = None
        best_5_score = float("inf")

        for ch in CHANNELS_5:
            score = scores.get(ch, 0)
            if score < best_5_score:
                best_5_score = score
                best_5_ch    = ch

        net_on_best_5 = counts.get(best_5_ch, 0)
        result["5GHz"] = {
            "channel": best_5_ch,
            "score"  : round(best_5_score, 2),
            "networks_count": net_on_best_5,
            "reason" : (
                f"Channel {best_5_ch} paling sedikit digunakan di band 5 GHz "
                f"({net_on_best_5} jaringan aktif)"
            ),
        }
    else:
        result["5GHz"] = {
            "channel": 36,
            "score"  : 0,
            "networks_count": 0,
            "reason" : "Tidak ada jaringan 5 GHz terdeteksi, channel 36 disarankan sebagai default.",
        }

    return result


# ─────────────────────────────────────────
# Deteksi channel yang overlap / padat
# ─────────────────────────────────────────
def detect_congested_channels(networks: list[dict], threshold: int = 3) -> list[int]:
    """
    Deteksi channel yang padat (jumlah jaringan ≥ threshold).
    Return list channel yang dianggap padat.
    """
    counts = count_networks_per_channel(networks)
    return [ch for ch, count in counts.items() if count >= threshold]


def detect_overlapping_channels(networks: list[dict]) -> list[tuple]:
    """
    Deteksi pasangan channel yang saling overlap di 2.4 GHz.
    Return list of tuples (channel_a, channel_b) yang overlap.
    """
    channels_used = set()
    for net in networks:
        if "2.4" in net.get("band", ""):
            channels_used.add(net.get("channel", 0))

    overlaps = []
    channels_list = sorted(channels_used)
    for i, ch_a in enumerate(channels_list):
        for ch_b in channels_list[i+1:]:
            if ch_a in OVERLAP_MAP_24 and ch_b in OVERLAP_MAP_24.get(ch_a, []):
                overlaps.append((ch_a, ch_b))

    return overlaps


# ─────────────────────────────────────────
# Ringkasan analisis lengkap
# ─────────────────────────────────────────
def full_analysis(networks: list[dict]) -> dict:
    """
    Return dict lengkap hasil analisis untuk ditampilkan di dashboard.
    """
    return {
        "total_networks"    : len(networks),
        "networks_24ghz"    : len([n for n in networks if "2.4" in n.get("band", "")]),
        "networks_5ghz"     : len([n for n in networks if "5" in n.get("band", "")]),
        "interference_scores": calculate_interference_score(networks),
        "channel_counts"    : count_networks_per_channel(networks),
        "recommendation"    : recommend_channel(networks),
        "congested_channels": detect_congested_channels(networks),
        "overlapping_pairs" : detect_overlapping_channels(networks),
    }
