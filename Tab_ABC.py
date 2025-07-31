import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# --- CONFIGURACIÓN GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
client = gspread.authorize(credentials)

# --- CARGA DE DATOS DESDE GOOGLE SHEET ---
sheet = client.open("CosteoPoliartesABC")
registros_ws = sheet.worksheet("registros_diarios")
registros = pd.DataFrame(registros_ws.get_all_records())

# Carga centros de costo
centros_ws = sheet.worksheet("centros_costo")
centros_costo = pd.DataFrame(centros_ws.get_all_records())

# --- AJUSTE DE TIPOS DE DATOS ---
registros["Fecha"] = pd.to_datetime(registros["Fecha"])
registros = registros.merge(centros_costo, on="CentroCosto_ID", how="left")

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Costeo ABC", layout="wide")
st.title("📊 Visualización de Costos ABC - Poliartes")

# --- FILTROS INTERACTIVOS ---
with st.sidebar:
    st.header("🔍 Filtros")
    fechas = st.date_input("Filtrar por rango de fechas", [])
    if len(fechas) == 2:
        registros = registros[(registros["Fecha"] >= pd.to_datetime(fechas[0])) &
                              (registros["Fecha"] <= pd.to_datetime(fechas[1]))]

    ccosto_seleccion = st.multiselect("Centro de Costo", options=centros_costo["N_CentroCosto"].unique(), default=None)
    if ccosto_seleccion:
        registros = registros[registros["N_CentroCosto"].isin(ccosto_seleccion)]

    actividad_sel = st.multiselect("Actividad", options=registros["N_Actividad"].unique(), default=None)
    if actividad_sel:
        registros = registros[registros["N_Actividad"].isin(actividad_sel)]

    producto_sel = st.multiselect("Producto (Referencia)", options=registros["N_Referencia"].unique(), default=None)
    if producto_sel:
        registros = registros[registros["N_Referencia"].isin(producto_sel)]

# --- KPIs ---
col1, col2, col3 = st.columns(3)
total_costos = registros["Costo_Total"].sum()
total_actividades = len(registros)
unidades_reales = (registros["Unidades"].sum() / total_actividades) if total_actividades else 0

col1.metric("💰 Total Costos", f"${total_costos:,.0f}")
col2.metric("⚙️ Actividades Registradas", total_actividades)
col3.metric("📦 Unidades Reales Estimadas", f"{unidades_reales:.2f}")

# --- AGRUPACIÓN Y CÁLCULO POR REFERENCIA ---
resumen = registros.groupby("Cod_Ref").agg({
    "Unidades": "sum",
    "N_Referencia": "first",
    "Costo_Total": "sum",
    "N_Actividad": "count"
}).reset_index()

resumen["Unidades_Reales"] = resumen["Unidades"] / resumen["N_Actividad"]
resumen["Costo_Unitario_Promedio"] = resumen["Costo_Total"] / resumen["Unidades_Reales"]

# --- FORMATO MONEDA ---
resumen["Costo_Total"] = resumen["Costo_Total"].apply(lambda x: f"${x:,.0f}")
resumen["Costo_Unitario_Promedio"] = resumen["Costo_Unitario_Promedio"].apply(lambda x: f"${x:,.2f}")

# --- TABLA DE RESUMEN ---
st.subheader("📘 Resumen por Referencia")
st.dataframe(resumen[[ "Cod_Ref", "N_Referencia", "Unidades_Reales", "Costo_Total", "Costo_Unitario_Promedio" ]],
             use_container_width=True)

# --- GRÁFICOS ---
st.subheader("📈 Gráficos")
tab1, tab2 = st.tabs(["Costo Unitario por Referencia", "Distribución por Centro de Costo"])

with tab1:
    resumen_graf = registros.groupby("N_Referencia").agg({
        "Unidades": "sum",
        "Costo_Total": "sum",
        "N_Actividad": "count"
    }).reset_index()
    resumen_graf["Unidades_Reales"] = resumen_graf["Unidades"] / resumen_graf["N_Actividad"]
    resumen_graf["Costo_Unitario_Promedio"] = resumen_graf["Costo_Total"] / resumen_graf["Unidades_Reales"]

    fig1 = px.bar(resumen_graf, x="N_Referencia", y="Costo_Unitario_Promedio",
                  title="Costo Unitario Promedio por Referencia",
                  text_auto=".2s", color="Costo_Unitario_Promedio", color_continuous_scale="Teal")
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    dist_costos = registros.groupby("N_CentroCosto")["Costo_Total"].sum().reset_index()
    fig2 = px.pie(dist_costos, names="N_CentroCosto", values="Costo_Total",
                  title="Distribución de Costos por Centro de Costo",
                  color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig2, use_container_width=True)

# --- DETALLES AGRUPADOS ---
st.subheader("🔍 Detalles de Actividades")

for cc in registros["N_CentroCosto"].unique():
    with st.expander(f"🏷️ Centro de Costo: {cc}", expanded=False):
        actividades = registros[registros["N_CentroCosto"] == cc]["N_Actividad"].unique()
        for act in actividades:
            st.markdown(f"#### 🔧 Actividad: {act}")
            referencias = registros[
                (registros["N_CentroCosto"] == cc) & 
                (registros["N_Actividad"] == act)
            ]["N_Referencia"].unique()
            
            for ref in referencias:
                st.markdown(f"**🖼️ Imagen: {ref}**")
                tabla = registros[
                    (registros["N_CentroCosto"] == cc) &
                    (registros["N_Actividad"] == act) &
                    (registros["N_Referencia"] == ref)
                ][[
                    "Fecha", "Cod_Ref", "Unidades", "Horas_Totales", "Horas_Compresor",
                    "Costo_Trabajador", "Costo_Compresor", "Costo_Total", "Costo_Unitario", "Usuario", "Observaciones"
                ]]
                # Formatear columnas monetarias
                for col in ["Costo_Trabajador", "Costo_Compresor", "Costo_Total", "Costo_Unitario"]:
                    tabla[col] = tabla[col].apply(lambda x: f"${x:,.0f}" if col != "Costo_Unitario" else f"${x:,.2f}")
                st.dataframe(tabla, use_container_width=True)

# --- EXPORTACIÓN A EXCEL ---
with st.expander("📤 Exportar a Excel"):
    from io import BytesIO
    output = BytesIO()
    # Convertir valores monetarios de nuevo a números para exportar correctamente
    export_registros = registros.copy()
    export_resumen = resumen.copy()
    export_resumen["Costo_Total"] = export_resumen["Costo_Total"].replace('[\$,]', '', regex=True).astype(float)
    export_resumen["Costo_Unitario_Promedio"] = export_resumen["Costo_Unitario_Promedio"].replace('[\$,]', '', regex=True).astype(float)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        export_registros.to_excel(writer, index=False, sheet_name='Detalle Actividades')
        export_resumen.to_excel(writer, index=False, sheet_name='Resumen Referencias')
    st.download_button("Descargar archivo Excel", data=output.getvalue(), file_name="resumen_costeo_ABC.xlsx")


#python -m streamlit run c:/Users/sacor/Downloads/Tab_ABC.py