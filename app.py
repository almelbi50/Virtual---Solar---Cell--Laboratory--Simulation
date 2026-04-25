import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests

# ==========================================
# 1. الإعدادات الفيزيائية (النموذج الهندسي المتقدم)
# ==========================================
q = 1.602e-19    # شحنة الإلكترون (Coulombs)
k_B = 1.381e-23  # ثابت بولتزمان (J/K)

def calculate_solar_cell_parameters(G, T_celsius, Isc_ref=5.0, Voc_ref=0.6, area=0.01):
    """حساب خصائص الخلية مع تضمين التأثير الحراري الديناميكي"""
    if G <= 1: 
        return {'P_max': 0, 'Vmpp': 0, 'Impp': 0, 'FF': 0, 'Efficiency': 0, 'V': np.array([0]), 'I': np.array([0]), 'P': np.array([0])}
    
    T_kelvin = T_celsius + 273.15
    n = 1.2 # معامل المثالية (Ideality Factor)
    
    # حساب الجهد الحراري القياسي
    Vt = (k_B * T_kelvin) / q 
    
    # ----------------------------------------
    # التعديل الجديد: معاملات الحرارة الديناميكية
    # ----------------------------------------
    alpha = 0.0005  # معامل حرارة التيار (يزداد التيار قليلاً مع الحرارة)
    beta = -0.003   # معامل حرارة الجهد (ينخفض الجهد بشدة مع الحرارة)
    delta_T = T_celsius - 25.0 # فارق الحرارة عن الظروف المعيارية (STC)
    
    # تحديث التيار والجهد المرجعي ليتفاعل مع الإشعاع والحرارة
    Isc_dynamic = Isc_ref * (G / 1000.0) * (1 + alpha * delta_T)
    Voc_dynamic = Voc_ref * (1 + beta * delta_T)
    
    # حماية برمجية لمنع الجهد من أن يصبح سالباً في درجات الحرارة المتطرفة
    Voc_dynamic = max(Voc_dynamic, 0.01)
    
    # ----------------------------------------
    
    # حساب تيار الإشباع العكسي بالقيم الديناميكية الجديدة
    I_o = Isc_dynamic / (np.exp(Voc_dynamic / (n * Vt)) - 1)
    
    # معادلة الدايود وتوليد المنحنى
    V = np.linspace(0, Voc_dynamic, 100)
    I = Isc_dynamic - I_o * (np.exp(V / (n * Vt)) - 1)
    
    # منع التيارات السالبة فيزيائياً
    I = np.maximum(I, 0)
    P = V * I
    
    # استخراج مؤشرات الأداء
    idx_mpp = np.argmax(P)
    P_max = P[idx_mpp]
    
    FF = P_max / (Voc_dynamic * Isc_dynamic) if (Voc_dynamic * Isc_dynamic) > 0 else 0
    Efficiency = (P_max / (G * area)) * 100 if G > 0 else 0
    
    return {
        'V': V, 'I': I, 'P': P,
        'P_max': P_max, 'Vmpp': V[idx_mpp], 
        'Impp': I[idx_mpp], 'FF': FF, 'Efficiency': Efficiency
    }

# ==========================================
# 2. ربط البيانات الجغرافية (Real-time API)
# ==========================================
@st.cache_data(ttl=3600)
def fetch_real_solar_data(lat, lon):
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
st.set_page_config(page_title="مختبر الخلايا الشمسية الجغرافي", page_icon="☀️", layout="wide")

# --- تحسينات التصميم (CSS المخصص) ---
st.markdown("""
<style>
    /* تغيير تنسيق مؤشرات الأداء لتبدو كبطاقات احترافية */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    /* تحسين شكل الفواصل */
    hr {
        margin-top: 2em;
        margin-bottom: 2em;
        border: 0;
        border-top: 2px solid #f0f2f6;
    }
    /* توسيط النصوص في العناوين */
    .centered-text {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- عرض الشعارات في الأعلى ---
col_logo1, col_space, col_logo2 = st.columns([1, 4, 1])
with col_logo1:
    st.image("https://phy-lab.com/wp-content/uploads/2026/02/شعار-االجامعة-بدون-خلفيه.png", use_container_width=True)
with col_logo2:
    st.image("https://phy-lab.com/wp-content/uploads/2026/02/شعار-الموقع-بدون-خلفيه.png", use_container_width=True)

# --- العنوان الرئيسي ---
st.markdown("<h1 class='centered-text' style='color: #1E3A8A;'>معمل الخلايا الشمسية التفاعلي - المستوى الأول ☀️</h1>", unsafe_allow_html=True)
st.markdown("""
<p class='centered-text' style='color: #555555; font-size: 1.1em;'>
هذا النظام يقوم بربط <b>نموذج فيزيائي رياضي متقدم</b> ببيانات <b>الأقمار الصناعية اللحظية</b> لتمثيل أداء الخلايا الشمسية 
في أي موقع جغرافي حول العالم على مدار 24 ساعة، مع مراعاة تأثير الحرارة على الجهد والتيار.
</p>
""", unsafe_allow_html=True)

st.write("---")

# --- القائمة الجانبية ---
st.sidebar.markdown("<h2 style='text-align: center;'>⚙️ لوحة التحكم</h2>", unsafe_allow_html=True)
st.sidebar.header("🌍 إعدادات الموقع الجغرافي")
lat = st.sidebar.number_input("خط العرض (Latitude)", value=24.4672, format="%.4f")
lon = st.sidebar.number_input("خط الطول (Longitude)", value=39.6024, format="%.4f")

st.sidebar.divider()
st.sidebar.subheader("🔬 خصائص الخلية الشمسية")
area = st.sidebar.slider("مساحة الخلية (m²)", 0.001, 0.1, 0.01, format="%.3f")
cell_temp_offset = st.sidebar.slider("إزاحة حرارة الخلية (°C)", 0, 30, 15)

# --- معالجة البيانات ---
hours, G_values, T_env_values = fetch_real_solar_data(lat, lon)

if hours is not None:
    full_day_results = []
    hourly_curves_data = {} 
    
    for h, g, t_env in zip(hours, G_values, T_env_values):
        t_cell = t_env + cell_temp_offset 
        res = calculate_solar_cell_parameters(g, t_cell, area=area)
        
        hourly_curves_data[h] = res 
        
        full_day_results.append({
            'Hour': h,
            'Irradiance (W/m2)': round(g, 2),
            'Ambient Temp (°C)': round(t_env, 1),
            'Cell Temp (°C)': round(t_cell, 1),
            'Power Out (W)': round(res['P_max'], 4),
            'Efficiency (%)': round(res['Efficiency'], 2)
        })

    df = pd.DataFrame(full_day_results)

    # --- عرض الإحصائيات الحيوية (كبطاقات أنيقة) ---
    st.markdown("### 📊 ملخص الأداء اليومي")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("إجمالي طاقة اليوم", f"{df['Power Out (W)'].sum():.2f} Wh", delta_color="normal")
    with col2:
        st.metric("أعلى إشعاع مسجل", f"{df['Irradiance (W/m2)'].max():.0f} W/m²")
    with col3:
        st.metric("متوسط الكفاءة", f"{df[df['Power Out (W)']>0]['Efficiency (%)'].mean():.2f} %")
    with col4:
        peak_hour_idx = df['Irradiance (W/m2)'].idxmax()
        peak_res = hourly_curves_data[peak_hour_idx]
        st.metric("أعلى قدرة لحظية", f"{peak_res['P_max']:.2f} W")

    st.write("---")

    # --- الرسوم البيانية ---
    tab1, tab2, tab3 = st.tabs(["📈 تحليل الأداء الزمني", "🧪 منحنيات المختبر (I-V)", "📋 جدول البيانات والتحميل"])

    with tab1:
        st.markdown("#### تغير الإشعاع والطاقة خلال 24 ساعة")
        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(x=df['Hour'], y=df['Irradiance (W/m2)'], name="الإشعاع (W/m²)", fill='tozeroy', line=dict(color='#FFA15A', width=2)))
        fig_time.add_trace(go.Scatter(x=df['Hour'], y=df['Power Out (W)'], name="الطاقة المنتجة (W)", line=dict(color='#00CC96', width=4), yaxis="y2"))
        fig_time.update_layout(
            xaxis_title="الساعة",
            yaxis_title="الإشعاع الشمسي (W/m²)",
            yaxis2=dict(title="الطاقة الكهربائية (W)", overlaying='y', side='right'),
            hovermode="x unified",
            margin=dict(l=40, r=40, t=40, b=40),
            plot_bgcolor='rgba(0,0,0,0)' # خلفية شفافة للرسم
        )
        # إضافة شبكة خفيفة
        fig_time.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')
        fig_time.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')
        st.plotly_chart(fig_time, use_container_width=True)

    with tab2:
        col_iv1, col_iv2 = st.columns([1, 2.5])
        with col_iv1:
            st.markdown("#### خصائص النقطة القصوى (MPP)")
            st.info(f"**الوقت ذروة الإشعاع:** {peak_hour_idx}:00", icon="⏱️")
            st.success(f"**V_mpp:** {peak_res['Vmpp']:.3f} V")
            st.success(f"**I_mpp:** {peak_res['Impp']:.3f} A")
            st.warning(f"**Fill Factor:** {peak_res['FF']:.3f}")
        with col_iv2:
            fig_iv = go.Figure()
            fig_iv.add_trace(go.Scatter(x=peak_res['V'], y=peak_res['I'], name="I-V Curve", line=dict(color='#636EFA', width=3)))
            fig_iv.add_trace(go.Scatter(x=[peak_res['Vmpp']], y=[peak_res['Impp']], mode='markers', name='MPP Point', marker=dict(size=14, color='#EF553B', symbol='star')))
            fig_iv.update_layout(
                title="منحنى التيار والجهد عند ذروة الإشعاع", 
                xaxis_title="الجهد (V)", 
                yaxis_title="التيار (A)",
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=40, r=40, t=40, b=40)
            )
            fig_iv.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')
            fig_iv.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')
            st.plotly_chart(fig_iv, use_container_width=True)

    with tab3:
        st.markdown("#### سجل البيانات التفصيلي")
        st.dataframe(df, use_container_width=True)
        
        csv_full = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 تحميل بيانات اليوم كاملة (CSV)", csv_full, "solar_lab_daily_summary.csv", "text/csv")
        
        st.divider()
        
        st.markdown("#### استخراج بيانات منحنى (I-V) التفصيلية")
        st.write("اختر أي ساعة من اليوم لتحميل الـ 100 نقطة (جهد، تيار، قدرة) المكونة لمنحناها.")
        
        col_select, col_download = st.columns([1, 2])
        with col_select:
            selected_hour = st.selectbox("اختر الساعة:", options=hours, index=int(peak_hour_idx))
            
        with col_download:
            st.write("") 
            st.write("")
            curve_data = hourly_curves_data[selected_hour]
            if curve_data['P_max'] > 0:
                df_curve = pd.DataFrame({
                    'Voltage (V)': curve_data['V'],
                    'Current (A)': curve_data['I'],
                    'Power (W)': curve_data['P']
                })
                csv_curve = df_curve.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"📥 تحميل نقاط منحنى الساعة {selected_hour}:00",
                    data=csv_curve,
                    file_name=f'iv_curve_hour_{selected_hour}.csv',
                    mime='text/csv'
                )
            else:
                st.warning("لا يوجد إنتاج للطاقة في هذه الساعة (الليل أو إشعاع منعدم).")

else:
    st.error("خطأ في الاتصال بمزود بيانات الطقس. يرجى التأكد من اتصال الإنترنت.")
