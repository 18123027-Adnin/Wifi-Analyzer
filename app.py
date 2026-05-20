"""
app.py
Dashboard utama WiFi Analyzer menggunakan Streamlit.
"""

import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import streamlit as st

from scanner import scan_wifi
from analyzer import full_analysis
from firebase_config import init_firebase, upload_scan, get_history


# ─────────────────────────────────────────
# Konfigurasi halaman
# ─────────────────────────────────────────
st.set_page_config(
    page_title="WiFi Analyzer",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .quality-excellent { color: #00C851; font-weight: bold; }
    .quality-good      { color: #33B5E5; font-weight: bold; }
    .quality-fair      { color: #FFBB33; font-weight: bold; }
    .quality-poor      { color: #FF4444; font-weight: bold; }
    .recommend-box     { background: #0D3B26; border-left: 4px solid #00C851;
                         padding: 12px; border-radius: 6px; margin: 8px 0; }
    .warn-box          { background: #3B1A0D; border-left: 4px solid #FF4444;
                         padding: 12px; border-radius: 6px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

QUALITY_COLOR = {
    "Excellent": "#00C851",
    "Good"     : "#33B5E5",
    "Fair"     : "#FFBB33",
    "Poor"     : "#FF4444",
}


# ─────────────────────────────────────────
# Init Firebase sekali saja
# ─────────────────────────────────────────
@st.cache_resource
def get_db():
    return init_firebase()

db = get_db()


# ─────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────
with st.sidebar:
    st.title("📡 WiFi Analyzer")
    st.markdown("**Kelompok 10 — ET3204 LTKA**")
    st.divider()

    st.subheader("⚙️ Pengaturan Scan")
    auto_refresh = st.checkbox("Auto Refresh", value=False)
    refresh_interval = st.slider("Interval (detik)", 10, 120, 30, disabled=not auto_refresh)

    st.divider()
    scan_btn = st.button("🔍 Scan Sekarang", type="primary", use_container_width=True)

    st.divider()
    st.subheader("📋 Filter")
    band_filter = st.multiselect(
        "Band Frekuensi",
        ["2.4 GHz", "5 GHz"],
        default=["2.4 GHz", "5 GHz"]
    )
    quality_filter = st.multiselect(
        "Kualitas Sinyal",
        ["Excellent", "Good", "Fair", "Poor"],
        default=["Excellent", "Good", "Fair", "Poor"]
    )

    st.divider()
    show_history = st.checkbox("Tampilkan Histori Cloud", value=False)


# ─────────────────────────────────────────
# Session state
# ─────────────────────────────────────────
if "networks" not in st.session_state:
    st.session_state.networks = []
if "last_scan_time" not in st.session_state:
    st.session_state.last_scan_time = None
if "analysis" not in st.session_state:
    st.session_state.analysis = {}


# ─────────────────────────────────────────
# Fungsi scan & simpan
# ─────────────────────────────────────────
def do_scan():
    with st.spinner("Memindai jaringan WiFi..."):
        networks = scan_wifi()
        if networks:
            st.session_state.networks       = networks
            st.session_state.last_scan_time = time.strftime("%H:%M:%S")
            st.session_state.analysis       = full_analysis(networks)

            scan_data = {
                "networks"       : networks,
                "timestamp"      : time.strftime("%Y-%m-%dT%H:%M:%S"),
                "total_networks" : len(networks),
            }
            upload_scan(db, scan_data)
            st.success(f"✅ Ditemukan {len(networks)} jaringan. Data tersimpan ke Firebase Firestore.")
        else:
            st.warning("Tidak ada jaringan yang terdeteksi.")


if scan_btn:
    do_scan()

if not st.session_state.networks:
    do_scan()

if auto_refresh:
    time.sleep(refresh_interval)
    do_scan()
    st.rerun()


# ─────────────────────────────────────────
# Data & filter
# ─────────────────────────────────────────
networks = st.session_state.networks
analysis = st.session_state.analysis

filtered = [
    n for n in networks
    if n.get("band") in band_filter
    and n.get("quality") in quality_filter
]


# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.title("📡 WiFi Analyzer Dashboard")
col_time, col_total, col_24, col_5 = st.columns(4)

with col_time:
    st.metric("🕐 Scan Terakhir", st.session_state.last_scan_time or "-")
with col_total:
    st.metric("📶 Total Jaringan", analysis.get("total_networks", 0))
with col_24:
    st.metric("📻 Band 2.4 GHz", analysis.get("networks_24ghz", 0))
with col_5:
    st.metric("🚀 Band 5 GHz", analysis.get("networks_5ghz", 0))

st.divider()


# ─────────────────────────────────────────
# REKOMENDASI CHANNEL
# ─────────────────────────────────────────
st.subheader("🎯 Rekomendasi Channel Optimal")

rec = analysis.get("recommendation", {})
col_rec24, col_rec5 = st.columns(2)

with col_rec24:
    if "2.4GHz" in rec:
        r = rec["2.4GHz"]
        st.markdown(f"""
        <div class="recommend-box">
            <h3 style="color:#00C851; margin:0">✅ 2.4 GHz → Channel {r['channel']}</h3>
            <p style="margin:6px 0 0 0; color:#ccc">{r['reason']}</p>
            <small style="color:#aaa">Skor interferensi: {r['score']}</small>
        </div>
        """, unsafe_allow_html=True)

with col_rec5:
    if "5GHz" in rec:
        r = rec["5GHz"]
        st.markdown(f"""
        <div class="recommend-box">
            <h3 style="color:#00C851; margin:0">✅ 5 GHz → Channel {r['channel']}</h3>
            <p style="margin:6px 0 0 0; color:#ccc">{r['reason']}</p>
            <small style="color:#aaa">Skor interferensi: {r['score']}</small>
        </div>
        """, unsafe_allow_html=True)

congested = analysis.get("congested_channels", [])
overlaps  = analysis.get("overlapping_pairs", [])

if congested:
    st.markdown(f"""
    <div class="warn-box">
        ⚠️ <b>Channel Padat:</b> Channel {', '.join(map(str, congested))} digunakan oleh banyak jaringan.
    </div>
    """, unsafe_allow_html=True)

if overlaps:
    overlap_str = ", ".join([f"Ch{a}↔Ch{b}" for a, b in overlaps])
    st.markdown(f"""
    <div class="warn-box">
        ⚠️ <b>Channel Overlap Terdeteksi:</b> {overlap_str}
    </div>
    """, unsafe_allow_html=True)

st.divider()


# ─────────────────────────────────────────
# TABEL JARINGAN
# ─────────────────────────────────────────
st.subheader("📋 Jaringan WiFi Terdeteksi")

if filtered:
    df = pd.DataFrame(filtered)
    df = df[["ssid", "bssid", "rssi", "channel", "band", "quality", "timestamp"]]
    df.columns = ["SSID", "BSSID", "RSSI (dBm)", "Channel", "Band", "Quality", "Timestamp"]

    def color_quality(val):
        colors = {
            "Excellent": "color: #00C851; font-weight: bold",
            "Good"     : "color: #33B5E5; font-weight: bold",
            "Fair"     : "color: #FFBB33; font-weight: bold",
            "Poor"     : "color: #FF4444; font-weight: bold",
        }
        return colors.get(val, "")

    styled_df = df.style.map(color_quality, subset=["Quality"])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
else:
    st.info("Tidak ada jaringan yang cocok dengan filter.")

st.divider()


# ─────────────────────────────────────────
# BAR CHART RSSI
# ─────────────────────────────────────────
st.subheader("📊 Kekuatan Sinyal (RSSI) per Jaringan")

if filtered:
    df_plot = pd.DataFrame(filtered).sort_values("rssi", ascending=True)
    color_map = {
        "Excellent": "#00C851",
        "Good"     : "#33B5E5",
        "Fair"     : "#FFBB33",
        "Poor"     : "#FF4444",
    }

    fig_rssi = px.bar(
        df_plot,
        x="rssi", y="ssid",
        orientation="h",
        color="quality",
        color_discrete_map=color_map,
        labels={"rssi": "RSSI (dBm)", "ssid": "SSID", "quality": "Kualitas"},
        title="Bar Chart RSSI — Semakin kanan semakin kuat sinyalnya",
        text="rssi",
    )
    fig_rssi.update_layout(
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="#FAFAFA",
        xaxis=dict(range=[-100, -20], gridcolor="#333"),
        yaxis=dict(gridcolor="#333"),
        height=max(300, len(filtered) * 40),
    )
    fig_rssi.update_traces(texttemplate="%{text} dBm", textposition="outside")
    st.plotly_chart(fig_rssi, use_container_width=True)

st.divider()


# ─────────────────────────────────────────
# CHANNEL MAP
# ─────────────────────────────────────────
st.subheader("📻 Channel Map — Distribusi Penggunaan Channel")
col_ch24, col_ch5 = st.columns(2)

with col_ch24:
    st.markdown("**Band 2.4 GHz**")
    nets_24 = [n for n in filtered if "2.4" in n.get("band", "")]
    if nets_24:
        ch_counts_24 = {ch: sum(1 for n in nets_24 if n["channel"] == ch) for ch in range(1, 14)}
        fig_ch24, ax = plt.subplots(figsize=(8, 3))
        fig_ch24.patch.set_facecolor("#0E1117")
        ax.set_facecolor("#0E1117")
        channels = list(ch_counts_24.keys())
        counts   = list(ch_counts_24.values())
        bar_colors = ["#FF4444" if c >= 3 else "#33B5E5" if c >= 1 else "#2A2A3A" for c in counts]
        ax.bar(channels, counts, color=bar_colors, edgecolor="#444", width=0.7)
        rec_ch = rec.get("2.4GHz", {}).get("channel")
        if rec_ch:
            ax.axvline(x=rec_ch, color="#00C851", linestyle="--", linewidth=2, label=f"Rekomendasi: Ch {rec_ch}")
            ax.legend(facecolor="#1E1E2E", labelcolor="white")
        ax.set_xlabel("Channel", color="white")
        ax.set_ylabel("Jumlah Jaringan", color="white")
        ax.set_xticks(channels)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#333")
        st.pyplot(fig_ch24)
    else:
        st.info("Tidak ada jaringan 2.4 GHz setelah filter.")

with col_ch5:
    st.markdown("**Band 5 GHz**")
    nets_5 = [n for n in filtered if "5" in n.get("band", "")]
    if nets_5:
        ch_counts_5 = {}
        for n in nets_5:
            ch = n["channel"]
            ch_counts_5[ch] = ch_counts_5.get(ch, 0) + 1
        fig_ch5, ax5 = plt.subplots(figsize=(8, 3))
        fig_ch5.patch.set_facecolor("#0E1117")
        ax5.set_facecolor("#0E1117")
        channels5 = sorted(ch_counts_5.keys())
        counts5   = [ch_counts_5[ch] for ch in channels5]
        bar_colors5 = ["#FF4444" if c >= 2 else "#33B5E5" for c in counts5]
        ax5.bar(channels5, counts5, color=bar_colors5, edgecolor="#444", width=3)
        rec_ch5 = rec.get("5GHz", {}).get("channel")
        if rec_ch5:
            ax5.axvline(x=rec_ch5, color="#00C851", linestyle="--", linewidth=2, label=f"Rekomendasi: Ch {rec_ch5}")
            ax5.legend(facecolor="#1E1E2E", labelcolor="white")
        ax5.set_xlabel("Channel", color="white")
        ax5.set_ylabel("Jumlah Jaringan", color="white")
        ax5.tick_params(colors="white")
        for spine in ax5.spines.values():
            spine.set_edgecolor("#333")
        st.pyplot(fig_ch5)
    else:
        st.info("Tidak ada jaringan 5 GHz setelah filter.")

st.divider()


# ─────────────────────────────────────────
# INTERFERENCE SCORE
# ─────────────────────────────────────────
st.subheader("⚡ Skor Interferensi per Channel")

interference = analysis.get("interference_scores", {})
if interference:
    df_int = pd.DataFrame(
        sorted(interference.items(), key=lambda x: x[0]),
        columns=["Channel", "Skor Interferensi"]
    )
    df_int["Channel"] = df_int["Channel"].astype(str)
    fig_int = px.bar(
        df_int, x="Channel", y="Skor Interferensi",
        color="Skor Interferensi",
        color_continuous_scale=["#00C851", "#FFBB33", "#FF4444"],
        title="Skor Interferensi (lebih rendah = lebih baik)",
    )
    fig_int.update_layout(
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="#FAFAFA", yaxis=dict(gridcolor="#333"),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_int, use_container_width=True)

st.divider()


# ─────────────────────────────────────────
# HISTORI CLOUD
# ─────────────────────────────────────────
if show_history:
    st.subheader("☁️ Histori Scan dari Firebase Firestore")
    with st.spinner("Mengambil data dari Firestore..."):
        history = get_history(db, limit=10)

    if history:
        for i, scan in enumerate(history):
            with st.expander(f"📅 Scan {i+1} — {scan.get('timestamp', 'N/A')} ({scan.get('total_networks', 0)} jaringan)"):
                nets = scan.get("networks", [])
                if nets:
                    df_hist = pd.DataFrame(nets)[["ssid", "rssi", "channel", "band", "quality"]]
                    df_hist.columns = ["SSID", "RSSI (dBm)", "Channel", "Band", "Quality"]
                    st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada histori scan. Lakukan scan terlebih dahulu.")

st.divider()


# ─────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────
st.markdown("""
<div style="text-align:center; color:#555; font-size:13px; padding-top:8px">
    WiFi Analyzer — Kelompok 10 | ET3204 Layanan Tersambung dan Komputasi Awan<br>
    Muthia Nabilla Azzahra · Belvaraina Tsuraya Sunu · Adnin Sakara
</div>
""", unsafe_allow_html=True)
