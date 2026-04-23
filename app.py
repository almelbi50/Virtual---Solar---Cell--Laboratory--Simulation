import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests

# ==========================================
# 1. المحرك الفيزيائي (النموذج الرياضي)
# ==========================================
q = 1.602e-19    
k_B = 1.381e-23  

def calculate_solar_cell_parameters(G, T_celsius, Isc_ref=5.0, Voc_ref=0.6, area=0.01):
    if G <= 1:
        return {'P_max': 0, 'Vmpp': 0, 'Impp': 0, 'FF': 0, 'Efficiency': 0, 
                'V': np.array([0]), 'I': np.array([0]), 'P': np.array([0])}
    
    T_kelvin = T_celsius + 273.15
    n = 1.2 
    Vt = (n * k_B * T_kelvin) / q
    Isc = Isc_ref * (G / 1000.0)
    I_o = Isc / (np.exp(Voc_ref / Vt) - 1)
    
    # توليد 100 نقطة للمنحنى (الجهد من 0 إلى Voc)
    V = np.linspace(0, Voc_ref, 100)
    I = Isc - I_o * (np.exp(V / Vt) - 1)
    I = np.maximum(I, 0)
    P = V * I
    
    idx_mpp = np.argmax(P)
    return {
        'V': V, 'I': I, 'P': P,
        'P_max': P[idx_mpp], 'Vmpp': V[idx_mpp], 
        'Impp': I[idx_mpp], 'FF': P[idx_mpp] / (Voc_ref * Isc),
        'Efficiency': (P[idx_mpp] / (G * area)) * 100
    }

@st.cache_data(ttl=3600)
def fetch_real_solar_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,shortwave_radiation&timezone=auto&forecast_days=1"
    try:
        response = requests.get(url)
        data = response.json()
        return np.arange(24), np.array(data['hourly']['shortwave_radiation'][:24]), np.array(data['hourly']['temperature_2m'][:24])
    except:
        return None, None, None

# ==========================================
# 2. واجهة المستخدم
# ==========================================
st.set_page_config(page_title="مختبر الطاقة الشمسية المطور", layout="wide")
st.title("☀️ مختبر تحليل منحنيات (I-V) المتقدم")

# --- القائمة الجانبية ---
st.sidebar.header("🌍 الموقع والخصائص")
lat = st.sidebar.number_input("Latitude", value=24.4672, format="%.4f")
lon = st.sidebar.number_input("Longitude", value=39.6024, format="%.4f")
area = st.sidebar.slider("مساحة الخلية (m²)", 0.001, 0.1, 0.01)

# جلب ومعالجة البيانات
hours, G_values, T_env_values = fetch_real_solar_data(lat, lon)

if hours is not None:
    # حساب بيانات اليوم بالكامل (Summary)
    full_day_data = []
    hourly_curves = {} # لتخزين مصفوفات V و I لكل ساعة
    
    for h, g, t in zip(hours, G_values, T_env_values):
        res = calculate_solar_cell_parameters(g, t + 15, area=area)
        hourly_curves[h] = res
        full_day_data.append({
            'Hour': h, 'Irradiance': g, 'Power': res['P_max'], 'Efficiency': res['Efficiency']
        })
    
    df_summary = pd.DataFrame(full_day_data)

    # --- قسم تحميل بيانات المنحنى التفصيلية ---
    st.sidebar.divider()
    st.sidebar.subheader("📥 تحميل بيانات المنحنى (I-V)")
    selected_hour = st.sidebar.selectbox("اختر الساعة لاستخراج منحناها:", options=hours, index=12)
    
    # تجهيز ملف CSV للمنحنى المختار (الـ 100 نقطة)
    curve_data = hourly_curves[selected_hour]
    df_curve = pd.DataFrame({
        'Voltage (V)': curve_data['V'],
        'Current (A)': curve_data['I'],
        'Power (W)': curve_data['P']
    })
    
    csv_curve = df_curve.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(
        label=f"تحميل نقاط منحنى الساعة {selected_hour}:00",
        data=csv_curve,
        file_name=f'iv_curve_hour_{selected_hour}.csv',
        mime='text/csv'
    )

    # --- العرض المرئي ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📊 منحنى (I-V) التفصيلي - الساعة {selected_hour}:00")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_curve['Voltage (V)'], y=df_curve['Current (A)'], name="Current (I)", line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=[curve_data['Vmpp']], y=[curve_data['Impp']], mode='markers', name='MPP', marker=dict(size=12, color='red')))
        fig.update_layout(xaxis_title="الجهد (Volt)", yaxis_title="التيار (Ampere)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📝 ملخص الساعة المختارة")
        st.write(f"**الإشعاع:** {G_values[selected_hour]} W/m²")
        st.metric("القدرة القصوى", f"{curve_data['P_max']:.3f} W")
        st.metric("معامل التعبئة (FF)", f"{curve_data['FF']:.3f}")
        st.write("يمكنك تحميل الـ 100 نقطة المكونة لهذا الرسم من القائمة الجانبية.")

    st.divider()
    st.subheader("📅 أداء النظام على مدار 24 ساعة")
    st.line_chart(df_summary.set_index('Hour')['Power'])

else:
    st.error("يرجى التحقق من اتصال الإنترنت لجلب البيانات الجغرافية.")
