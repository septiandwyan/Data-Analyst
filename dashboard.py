from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

sns.set_style('whitegrid')
st.set_page_config(page_title='Dashboard Penyewaan Sepeda', page_icon='🚲', layout='wide')

JAM_SIBUK = [7, 8, 9, 16, 17, 18, 19]


def fmt(angka, desimal=0):
    """Format angka dengan pemisah ribuan titik (gaya Indonesia)."""
    teks = f'{angka:,.{desimal}f}'
    return teks.replace(',', 'X').replace('.', ',').replace('X', '.')


# ---------- Load data ----------
@st.cache_data
def load_data():
    # Lokasi file dihitung dari posisi dashboard.py agar aman saat deploy
    path = Path(__file__).parent / 'main_data.csv'
    main = pd.read_csv(path, parse_dates=['dteday'])

    # Data per jam = seluruh baris
    hour = main

    # Data harian = satu baris per tanggal (kolom berakhiran _day)
    kolom_harian = ['cnt_day', 'casual_day', 'registered_day']
    day = main.drop_duplicates('dteday')[['dteday', 'yr'] + kolom_harian].copy()
    day = day.rename(columns={c: c.removesuffix('_day') for c in kolom_harian})
    return day, hour


day_df, hour_df = load_data()

# ---------- Sidebar ----------
with st.sidebar:
    st.title('🚲 Bike Sharing')
    st.caption('Dashboard analisis penyewaan sepeda 2011-2012')
    st.markdown('**Filter Pertanyaan 1**')
    tahun_pilih = st.multiselect('Tahun', [2011, 2012], default=[2011, 2012])
    bandingkan_libur = st.checkbox('Tampilkan hari libur sebagai pembanding', value=False)
    st.caption('Pertanyaan 2 membandingkan dua tahun sekaligus sehingga tidak memakai filter ini.')

if not tahun_pilih:
    st.warning('Pilih minimal satu tahun pada filter di sidebar.')
    st.stop()

# ---------- Header ----------
st.title('Dashboard Penyewaan Sepeda 🚲')
total_tahun = day_df.groupby('yr')['cnt'].sum()
h1, h2, h3 = st.columns(3)
h1.metric('Total penyewaan 2011-2012', fmt(total_tahun.sum()))
h2.metric('Rata-rata penyewaan per hari', fmt(day_df['cnt'].mean()))
h3.metric('Pertumbuhan 2012 vs 2011', f'{(total_tahun[2012] / total_tahun[2011] - 1) * 100:.1f}%')

tab1, tab2 = st.tabs(['Pertanyaan 1: Jam Sibuk', 'Pertanyaan 2: Pertumbuhan Tahunan'])

# ======================= PERTANYAAN 1 =======================
with tab1:
    st.subheader('Perbandingan penyewaan jam sibuk vs jam lainnya pada hari kerja')
    st.caption('Jam sibuk: 07.00-09.00 dan 16.00-19.00. Dasar penjadwalan penambahan dan redistribusi sepeda.')

    hf = hour_df[hour_df['yr'].isin(tahun_pilih)]
    kerja = hf[hf['workingday'] == 'Hari Kerja'].copy()
    kerja['kategori_jam'] = np.where(kerja['hr'].isin(JAM_SIBUK), 'Jam Sibuk', 'Jam Lain')

    rata = kerja.groupby('kategori_jam')['cnt'].mean()
    selisih_abs = rata['Jam Sibuk'] - rata['Jam Lain']
    selisih_pct = selisih_abs / rata['Jam Lain'] * 100

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Rata-rata jam sibuk', f"{fmt(rata['Jam Sibuk'])} sewa/jam")
    m2.metric('Rata-rata jam lain', f"{fmt(rata['Jam Lain'])} sewa/jam")
    m3.metric('Selisih', f'{fmt(selisih_abs)} sewa/jam')
    m4.metric('Selisih (%)', f'{selisih_pct:.0f}%')
    st.caption(f"Berdasarkan {kerja['dteday'].nunique()} hari kerja "
               f"({', '.join(str(t) for t in sorted(tahun_pilih))}).")

    kiri, kanan = st.columns([2.2, 1])
    with kiri:
        per_jam = kerja.groupby('hr')['cnt'].mean()
        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(per_jam.index, per_jam.values, marker='o', color='steelblue', label='Hari kerja')
        if bandingkan_libur:
            libur = hf[hf['workingday'] == 'Libur'].groupby('hr')['cnt'].mean()
            ax.plot(libur.index, libur.values, marker='o', color='gray', linestyle='--', label='Hari libur')
        for a, b in [(6.5, 9.5), (15.5, 19.5)]:
            ax.axvspan(a, b, color='orange', alpha=0.25)
        for jam in (8, 17):
            ax.annotate(f'{per_jam[jam]:.0f}', (jam, per_jam[jam]), textcoords='offset points',
                        xytext=(0, 8), ha='center', fontweight='bold')
        ax.set_title('Rata-rata Penyewaan per Jam (area oranye = jam sibuk)')
        ax.set_xlabel('Jam')
        ax.set_ylabel('Rata-rata penyewaan per jam')
        ax.set_xticks(range(24))
        ax.legend()
        st.pyplot(fig)
    with kanan:
        urut = ['Jam Sibuk', 'Jam Lain']
        fig, ax = plt.subplots(figsize=(5, 4.8))
        sns.barplot(x=urut, y=[rata[u] for u in urut], hue=urut,
                    palette=['orange', 'steelblue'], legend=False, ax=ax)
        for i, u in enumerate(urut):
            ax.text(i, rata[u] + 6, f'{rata[u]:.0f}', ha='center', fontweight='bold')
        ax.set_title(f'Selisih sekitar {selisih_pct:.0f}%')
        ax.set_ylabel('Rata-rata penyewaan per jam')
        ax.set_xlabel('')
        st.pyplot(fig)

    with st.expander('Lihat rata-rata per jam sibuk'):
        tabel = per_jam.loc[JAM_SIBUK].round(0).astype(int).rename('Rata-rata penyewaan').to_frame()
        tabel.index = [f'{j:02d}.00' for j in tabel.index]
        st.dataframe(tabel)

# ======================= PERTANYAAN 2 =======================
with tab2:
    st.subheader('Pertumbuhan total penyewaan 2012 dibandingkan 2011')
    st.caption('Dasar memperkirakan kebutuhan armada tahun 2013.')

    jenis = st.radio('Jenis pengguna', ['Semua', 'Casual', 'Registered'], horizontal=True)
    kolom = {'Semua': 'cnt', 'Casual': 'casual', 'Registered': 'registered'}[jenis]

    total = day_df.groupby('yr')[kolom].sum()
    pertumbuhan = (total[2012] - total[2011]) / total[2011] * 100

    p1, p2, p3 = st.columns(3)
    p1.metric('Total 2011', fmt(total[2011]))
    p2.metric('Total 2012', fmt(total[2012]), delta=f'{pertumbuhan:.1f}%')
    p3.metric('Pertumbuhan', f'{pertumbuhan:.1f}%')

    kiri, kanan = st.columns(2)
    with kiri:
        nilai_juta = [total[2011] / 1e6, total[2012] / 1e6]
        fig, ax = plt.subplots(figsize=(6, 4.8))
        bars = ax.bar(['2011', '2012'], nilai_juta, color=['lightsteelblue', 'steelblue'])
        for b, v in zip(bars, nilai_juta):
            ax.text(b.get_x() + b.get_width() / 2, v + nilai_juta[1] * 0.015,
                    f'{v:.2f} juta', ha='center', fontweight='bold')
        ax.text(0.5, nilai_juta[1] * 1.1, f'Pertumbuhan +{pertumbuhan:.1f}%', ha='center',
                fontsize=13, fontweight='bold', color='darkgreen')
        ax.set_ylim(0, nilai_juta[1] * 1.2)
        ax.set_title(f'Total Penyewaan per Tahun ({jenis})')
        ax.set_ylabel('Total penyewaan (juta)')
        st.pyplot(fig)
    with kanan:
        bulanan = day_df.groupby([day_df['dteday'].dt.month, 'yr'])[kolom].sum().unstack()
        fig, ax = plt.subplots(figsize=(7, 4.8))
        ax.plot(bulanan.index, bulanan[2011], marker='o', color='lightsteelblue', label='2011')
        ax.plot(bulanan.index, bulanan[2012], marker='o', color='steelblue', label='2012')
        ax.set_title(f'Total Penyewaan per Bulan ({jenis})')
        ax.set_xlabel('Bulan')
        ax.set_ylabel('Total penyewaan')
        ax.set_xticks(range(1, 13))
        ax.legend()
        st.pyplot(fig)

    with st.expander('Lihat pertumbuhan per bulan'):
        tabel = bulanan.copy()
        tabel['Pertumbuhan (%)'] = ((tabel[2012] / tabel[2011] - 1) * 100).round(0).astype(int)
        tabel.index.name = 'Bulan'
        st.dataframe(tabel)

    with st.expander('Skenario kebutuhan armada 2013 (perkiraan kasar)'):
        total_semua = day_df.groupby('yr')['cnt'].sum()
        proy_linear = total_semua[2012] + (total_semua[2012] - total_semua[2011])
        proy_tumbuh = total_semua[2012] * (1 + (total_semua[2012] / total_semua[2011] - 1))
        s1, s2 = st.columns(2)
        s1.metric('Jika kenaikan absolut sama', fmt(proy_linear))
        s2.metric('Jika persentase pertumbuhan sama', fmt(proy_tumbuh))
        st.caption('Perkiraan hanya berdasar dua tahun data sehingga dipakai sebagai rentang, bukan angka pasti.')

st.caption('Catatan: 165 dari 17.544 jam tidak tercatat pada data per jam; pengaruhnya terhadap rata-rata sangat kecil.')
