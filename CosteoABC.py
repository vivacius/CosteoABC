import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURACIÓN GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Leer credenciales desde Streamlit Secrets
creds_dict = st.secrets["GOOGLE_CREDENTIALS"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Abrir archivo y hojas
sheet = client.open("CosteoPoliartesABC")
productos_ws = sheet.worksheet("productos")
actividades_ws = sheet.worksheet("actividades")
centros_ws = sheet.worksheet("centros_costo")
registros_ws = sheet.worksheet("registros_diarios")

# Cargar datos
productos = pd.DataFrame(productos_ws.get_all_records())
actividades = pd.DataFrame(actividades_ws.get_all_records())
centros = pd.DataFrame(centros_ws.get_all_records())

# Constantes de costo
COSTO_HORA_TRABAJADOR = 10777
COSTO_HORA_COMPRESOR = 6200
COSTO_EMPAQUE = 3500
COSTO_MATERIAL_FABRICACION = 162500

st.title("📋 Registro diario de actividades - Costeo ABC")

# --- SELECCIÓN DE ACTIVIDAD ---
actividad_nombre = st.selectbox("Selecciona la Actividad", actividades["N_Actividad"])
actividad = actividades[actividades["N_Actividad"] == actividad_nombre].iloc[0]
centro_id = actividad["CentroCosto_ID"]
centro_nombre = centros[centros["CentroCosto_ID"] == centro_id]["N_CentroCosto"].values[0]
st.info(f"🔖 Centro de Costo asociado: **{centro_nombre}**")

# --- FORMULARIO ---
with st.form("registro_form"):
    fecha = st.date_input("Fecha", value=datetime.today())
    ref_nombre = st.selectbox("Referencia del producto", productos["N_Referencia"])
    ref_codigo = productos.loc[productos["N_Referencia"] == ref_nombre, "Cod_Ref"].values[0]

    unidades = st.number_input("Cantidad de unidades", min_value=1)
    h_trabajador = st.number_input("Horas por trabajador", min_value=0.0, step=0.1)
    trabajadores = st.number_input("Cantidad de trabajadores", min_value=1)
    horas_totales = h_trabajador * trabajadores
    st.write(f"⏱️ **Horas Totales:** {horas_totales:.2f}")

    actividades_compresor = ["Pulida", "Pintura Aerógrafo", "Pintura Madera"]
    if any(act in actividad_nombre for act in actividades_compresor):
        horas_compresor = st.number_input("Horas de compresor", min_value=0.0, step=0.1)
    else:
        horas_compresor = 0.0

    usuario = st.text_input("Usuario")
    observaciones = st.text_area("Observaciones")

    submitted = st.form_submit_button("Registrar")

    if submitted:
        # Calcular Costos
        costo_trabajador = horas_totales * COSTO_HORA_TRABAJADOR
        costo_compresor = horas_compresor * COSTO_HORA_COMPRESOR
        costo_total = costo_trabajador + costo_compresor

        # Agregar costo de material si es "Fabricación imagen"
        if actividad_nombre == "Fabricación imagen":
            costo_total += COSTO_MATERIAL_FABRICACION

        # Agregar costo de empaque si es "Empaque"
        if actividad_nombre == "Empaque":
            costo_total += unidades * COSTO_EMPAQUE

        costo_unitario = costo_total / unidades
        unidades_ajustadas = unidades  # Este valor se puede modificar más adelante si haces consolidación

        nueva_fila = [
            fecha.strftime("%d/%m/%Y"),
            int(centro_id),
            int(actividad["Actividad_ID"]),
            actividad_nombre,
            ref_codigo,
            ref_nombre,
            int(unidades),
            float(h_trabajador),
            int(trabajadores),
            float(horas_totales),
            float(horas_compresor),
            usuario,
            observaciones,
            round(costo_trabajador, 2),
            round(costo_compresor, 2),
            round(costo_total, 2),
            round(costo_unitario, 2),
            unidades_ajustadas
        ]

        registros_ws.append_row(nueva_fila)
        st.success("✅ Registro guardado correctamente.")


#python -m streamlit run c:/Users/sacor/Downloads/CosteoABC.py
