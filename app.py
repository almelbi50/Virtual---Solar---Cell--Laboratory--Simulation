import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# ==========================================
# 1. الإعدادات الفيزيائية (النموذج الرياضي)
# ==========================================
q = 1.602e-19    # شحنة الإلكترون
k_B = 1.381e-23  # ثابت بولتزمان

def calculate_solar_cell_parameters(G, T_celsius, Isc_ref=5.0, Voc_ref=0.6, area=0.01):
    """حساب خصائص الخلية بناءً على نموذج الدايود الواحد"""
    if G <= 1: # استبعاد القيم الضعيفة جداً أو الليل
        return {'P_max': 0, 'Vmpp': 0, 'Impp': 0, 'FF': 0, 'Efficiency': 0, 'V': [0], 'I': [0], 'P': [0]}
    
    T_kelvin = T_celsius + 273.15
    n = 1.2 # معامل المثالية
    Vt = (n * k_B * T_kelvin) / q # الجهد الحراري
    
    # تصحيح تيار الدائرة القصيرة بناءً على الإشعاع
    Isc = Isc_ref * (G / 1000.0)
    # حساب تيار الإشباع العكسي
    I_o = Isc / (np.exp(Voc_ref / Vt) - 1)
    
    V = np.linspace(0, Voc_ref, 100)
    I = Isc - I_o * (np.exp(V / Vt) - 1)
    I = np.maximum(I, 0)
    P = V * I
    
    idx_mpp = np.argmax(P)
    P_max = P[idx_mpp]
    
    FF = P_max / (Voc_ref * Isc) if (Voc_ref * Isc) > 0 else 0
    Efficiency = (P_max / (G * area)) * 100 if G > 0 else 0
    
    return {
        'V': V, 'I': I, 'P': P,
        'P_max': P_max, 'Vmpp': V[idx_mpp], 
        'Impp': I[idx_mpp], 'FF': FF, 'Efficiency': Efficiency
    }
# عرض خريطة توضح الموقع المختار للتأكد من عدم التداخل الجغرافي
st.sidebar.markdown("🗺️ **موقع سحب البيانات:**")
st.sidebar.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=4)
# ==========================================
# 2. ربط البيانات الجغرافية (Real-time API)
# ==========================================
@st.cache_data(ttl=3600) # تحديث البيانات كل ساعة
def fetch_real_solar_data(lat, lon):
    """جلب بيانات الإشعاع والحرارة الحقيقية بناءً على الموقع"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,shortwave_radiation&timezone=auto&forecast_days=1"
    try:
        response = requests.get(url)
        data = response.json()
        hours = np.arange(0, 24, 1)
        G_array = np.array(data['hourly']['shortwave_radiation'][:24])
        T_array = np.array(data['hourly']['temperature_2m'][:24])
        return hours, G_array, T_array
    except:
        return None, None, None

# ==========================================
# 3. واجهة المستخدم (Streamlit Interface)
# ==========================================
st.set_page_config(page_title="مختبر الخلايا الشمسية الجغرافي", layout="wide")

# تصميم الهيدر
st.title("☀️ مختبر الخلايا الشمسية التفاعلي (بيانات حقيقية)")
st.markdown("""
هذا النظام يقوم بربط **نموذج فيزيائي رياضي** ببيانات **الأقمار الصناعية اللحظية** لتمثيل أداء الخلايا الشمسية 
في أي موقع جغرافي حول العالم على مدار 24 ساعة.
""")

# --- القائمة الجانبية ---
st.sidebar.header("🌍 إعدادات الموقع والجهاز")
lat = st.sidebar.number_input("خط العرض (Latitude)", value=24.4672, format="%.4f", help="الموقع الافتراضي: المدينة المنورة")
lon = st.sidebar.number_input("خط الطول (Longitude)", value=39.6024, format="%.4f")

st.sidebar.divider()
st.sidebar.subheader("🔬 خصائص الخلية الشمسية")
area = st.sidebar.slider("مساحة الخلية (m²)", 0.001, 0.1, 0.01, format="%.3f")
cell_temp_offset = st.sidebar.slider("إزاحة حرارة الخلية (°C)", 0, 30, 15, help="الخلية تكون عادة أحر من الجو المحيط")

# --- معالجة البيانات ---
hours, G_values, T_env_values = fetch_real_solar_data(lat, lon)

if hours is not None:
    full_day_results = []
    for h, g, t_env in zip(hours, G_values, T_env_values):
        t_cell = t_env + cell_temp_offset # تقدير حرارة الخلية الفعلية
        res = calculate_solar_cell_parameters(g, t_cell, area=area)
        
        full_day_results.append({
            'Hour': h,
            'Irradiance (W/m2)': round(g, 2),
            'Ambient Temp (°C)': round(t_env, 1),
            'Cell Temp (°C)': round(t_cell, 1),
            'Power Out (W)': round(res['P_max'], 4),
            'Efficiency (%)': round(res['Efficiency'], 2)
        })

    df = pd.DataFrame(full_day_results)

    # --- عرض الإحصائيات الحيوية ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("إجمالي طاقة اليوم", f"{df['Power Out (W)'].sum():.2f} Wh")
    with col2:
        st.metric("أعلى إشعاع مسجل", f"{df['Irradiance (W/m2)'].max():.0f} W/m²")
    with col3:
        st.metric("متوسط الكفاءة", f"{df[df['Power Out (W)']>0]['Efficiency (%)'].mean():.2f} %")
    with col4:
        # استخراج منحنى I-V وقت الظهيرة (ساعة الذروة)
        peak_hour_idx = df['Irradiance (W/m2)'].idxmax()
        peak_res = calculate_solar_cell_parameters(G_values[peak_hour_idx], T_env_values[peak_hour_idx]+cell_temp_offset, area=area)
        st.metric("أعلى قدرة لحظية", f"{peak_res['P_max']:.2f} W")

    # --- الرسوم البيانية ---
    st.divider()
    tab1, tab2, tab3 = st.tabs(["📈 تحليل الأداء الزمني", "🧪 منحنيات المختبر (I-V)", "📋 جدول البيانات"])

    with tab1:
        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(x=df['Hour'], y=df['Irradiance (W/m2)'], name="الإشعاع (W/m²)", fill='tozeroy', line=dict(color='orange')))
        fig_time.add_trace(go.Scatter(x=df['Hour'], y=df['Power Out (W)'], name="الطاقة المنتجة (W)", line=dict(color='green', width=3), yaxis="y2"))
        fig_time.update_layout(
            title="تغير الإشعاع والطاقة خلال 24 ساعة",
            xaxis_title="الساعة",
            yaxis_title="الإشعاع الشمسي",
            yaxis2=dict(title="الطاقة الكهربائية", overlaying='y', side='right'),
            hovermode="x unified"
        )
        st.plotly_chart(fig_time, use_container_width=True)

    with tab2:
        col_iv1, col_iv2 = st.columns([1, 2])
        with col_iv1:
            st.write("### خصائص النقطة القصوى")
            st.info(f"الوقت: {peak_hour_idx}:00")
            st.write(f"**V_mpp:** {peak_res['Vmpp']:.3f} V")
            st.write(f"**I_mpp:** {peak_res['Impp']:.3f} A")
            st.write(f"**Fill Factor:** {peak_res['FF']:.3f}")
        with col_iv2:
            fig_iv = go.Figure()
            fig_iv.add_trace(go.Scatter(x=peak_res['V'], y=peak_res['I'], name="I-V Curve", line=dict(color='blue')))
            fig_iv.add_trace(go.Scatter(x=[peak_res['Vmpp']], y=[peak_res['Impp']], mode='markers', name='MPP Point', marker=dict(size=12, color='red')))
            fig_iv.update_layout(title="منحنى التيار والجهد عند ذروة الإشعاع", xaxis_title="الجهد (V)", yaxis_title="التيار (A)")
            st.plotly_chart(fig_iv, use_container_width=True)

    with tab3:
        st.write("### سجل البيانات التفصيلي")
        st.dataframe(df, use_container_width=True)
        
        # زر التحميل
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("تحميل البيانات كملف CSV للتحليل في Excel", csv, "solar_lab_data.csv", "text/csv")

else:
    st.error("خطأ في الاتصال بمزود بيانات الطقس. يرجى التأكد من اتصال الإنترنت.")
