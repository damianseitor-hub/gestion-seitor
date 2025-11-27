import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import os
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="S&V Gestión", page_icon="⚖️", layout="wide")

# --- 2. ESTILOS CSS (SOLO LO ESENCIAL) ---
st.markdown("""
    <style>
    .stApp {background-color: #f7f9fc;}
    
    h1 { color: #002b5c; font-size: 36px !important; font-weight: 900; text-transform: uppercase; border-bottom: 3px solid #e1e4e8; padding-bottom: 10px; margin-bottom: 20px; }
    h3 { font-size: 20px !important; color: #444; margin: 0;}

    /* HEADER AZUL (SOLO DATOS) */
    .case-header-compact {
        background: linear-gradient(135deg, #002b5c 0%, #001a33 100%) !important;
        color: white !important;
        border-radius: 15px;
        padding: 30px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    .case-name { font-size: 40px; font-weight: 900; margin: 0; color: white !important; text-shadow: 0 2px 4px rgba(0,0,0,0.4); line-height: 1.1; }
    .case-details { font-size: 18px; color: #dbeafe !important; margin-top: 8px;}
    .area-tag { background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 6px; font-size: 14px; font-weight: bold; margin-left: 15px; vertical-align: middle; color: white; }

    /* NOTAS FIJAS */
    .fixed-notes { background-color: #fff3cd; border-left: 6px solid #ffc107; color: #856404; padding: 15px; border-radius: 8px; font-size: 16px; margin-bottom: 20px; }

    /* INPUTS Y BOTONES */
    .stTextArea textarea { font-size: 16px; border: 3px solid #002b5c !important; border-radius: 8px; }
    .stButton>button { background-color: #002b5c; color: white; border-radius: 8px; font-weight: bold; border: none; height: 3em; font-size: 16px; }
    
    /* HISTORIAL */
    .hist-row { background-color: white; border-bottom: 1px solid #eee; padding: 15px 10px; margin-bottom: 8px; border-radius: 8px; display: flex; align-items: flex-start; }
    .hist-meta { font-size: 12px; color: #666; font-weight: bold; text-transform: uppercase; min-width: 130px; }
    .hist-body { font-size: 20px; color: #111; line-height: 1.4; flex-grow: 1; font-weight: 500; }
    
    /* LINKS */
    .btn-link { display: block; width: 100%; padding: 10px; text-align: center; border-radius: 5px; text-decoration: none; font-weight: 700; font-size: 13px; margin-bottom: 5px; border: 1px solid #ccc; }
    .btn-sac {background:#fff; color:#002b5c !important;}
    .btn-drive { display: inline-block; background: #FFD04B; color: #000 !important; padding: 8px 15px; border-radius: 6px; font-weight: bold; font-size: 14px; text-decoration: none; border: 1px solid #e6b800; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN HÍBRIDA (PC + NUBE) ---
@st.cache_resource
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    
    # 1. INTENTO PC (LOCAL)
    if os.path.exists("credentials.json"):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            client = gspread.authorize(creds)
            return client.open("Bitacora Seitor")
        except: pass
            
    # 2. INTENTO NUBE (SECRETS)
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client.open("Bitacora Seitor")
        except: pass

    return None

try:
    libro = conectar()
    if libro:
        hoja_movimientos = libro.sheet1
        hoja_clientes = libro.worksheet("Clientes")
        conexion = True
    else:
        conexion = False
except:
    conexion = False

# --- 4. LÓGICA DE NEGOCIO ---
def calcular_progreso(etapa_nombre):
    # Extrae solo el número del texto
    if "(" in etapa_nombre and "%)" in etapa_nombre:
        try: return int(etapa_nombre.split("(")[1].split("%")[0])
        except: pass
    return 0

def calcular_semaforo(ultima, alerta):
    if str(alerta).upper() == "FALSE": return "⚪", "Pausado", "#ccc"
    try:
        dias = (datetime.now() - datetime.strptime(str(ultima), "%d/%m/%Y")).days
        if dias <= 7: return "🟢", f"{dias}d", "#4ade80"
        elif dias <= 21: return "🟡", f"{dias}d", "#facc15"
        else: return "🔴", f"{dias}d", "#f87171"
    except: return "⚪", "-", "#ccc"

def log_visto(nombre):
    ahora = datetime.now()
    try:
        cell = hoja_clientes.find(nombre)
        hoja_clientes.update_cell(cell.row, 5, ahora.strftime("%d/%m/%Y"))
        hoja_movimientos.append_row([ahora.strftime("%d/%m/%Y %H:%M"), nombre, "Expediente revisado / Visto", "👁️ Control", "Normal", "Listo"])
        st.toast(f"✅ {nombre}: Registrado.")
        time.sleep(1) 
    except: pass

def update_fecha_only(nombre):
    try:
        cell = hoja_clientes.find(nombre)
        hoja_clientes.update_cell(cell.row, 5, datetime.now().strftime("%d/%m/%Y"))
        time.sleep(1)
    except: pass

def actualizar_progreso_manual(nombre, nuevo_porcentaje):
    try:
        # Guarda como "AVANCE (XX%)"
        etapa_str = f"AVANCE ({nuevo_porcentaje}%)"
        cell = hoja_clientes.find(nombre)
        hoja_clientes.update_cell(cell.row, 4, etapa_str)
        st.toast(f"✅ Avance actualizado: {nuevo_porcentaje}%")
        time.sleep(1)
    except Exception as e: st.error(f"Error: {e}")

def eliminar_cliente(nombre):
    try:
        cell = hoja_clientes.find(nombre)
        hoja_clientes.delete_rows(cell.row)
        st.success(f"🗑️ Cliente '{nombre}' eliminado correctamente.")
        time.sleep(2)
        st.rerun()
    except Exception as e:
        st.error(f"Error al eliminar: {e}")

def editar_datos_cliente(nombre, n_car, n_juz, n_drv, n_area, n_nota):
    try:
        cell = hoja_clientes.find(nombre)
        r = cell.row
        hoja_clientes.update_cell(r, 2, n_car) 
        hoja_clientes.update_cell(r, 3, n_juz) 
        hoja_clientes.update_cell(r, 7, n_drv) 
        hoja_clientes.update_cell(r, 8, n_area) 
        hoja_clientes.update_cell(r, 9, n_nota) 
        st.toast("✅ Datos actualizados")
        time.sleep(1)
    except: pass

def editar_nota(nombre, txt_viejo, txt_nuevo):
    try:
        data = hoja_movimientos.get_all_records()
        for i, row in enumerate(data):
            if row['Expediente'] == nombre and row['Nota'] == txt_viejo:
                hoja_movimientos.update_cell(i+2, 3, txt_nuevo)
                st.toast("Editado")
                return
    except: pass

def eliminar_nota(nombre, txt_viejo):
    try:
        data = hoja_movimientos.get_all_records()
        for i, row in enumerate(data):
            if row['Expediente'] == nombre and row['Nota'] == txt_viejo:
                hoja_movimientos.delete_rows(i+2)
                st.toast("Eliminado")
                return
    except: pass

# --- 5. INTERFAZ ---
if conexion:
    with st.sidebar:
        st.write("### 🏛️ S&V")
        # MENÚ SIMPLIFICADO (SIN CALCULADORA)
        modo = st.radio("Menú", ["Escritorio", "Alta Caso"], label_visibility="collapsed")
        st.divider()
        st.markdown('<a href="https://www.justiciacordoba.gob.ar/JusticiaCordoba/extranet.aspx" target="_blank" class="btn-link btn-sac">🔐 SAC</a>', unsafe_allow_html=True)
        st.markdown('<a href="https://www.justiciacordoba.gob.ar/JusticiaCordoba/servicios/DiasInhabiles.aspx" target="_blank" class="btn-link btn-sac">📅 Inhábiles</a>', unsafe_allow_html=True)

    if modo == "Escritorio":
        st.title("SEITOR & VOITZUK | GESTIÓN")

        try:
            df = pd.DataFrame(hoja_clientes.get_all_records())
            lista = df["Nombre Corto"].tolist() if not df.empty else []
        except: lista = []

        if not lista: st.info("Cargá un caso.")
        else:
            seleccion = st.selectbox("Seleccionar:", lista, label_visibility="collapsed")
            info = df[df["Nombre Corto"] == seleccion].iloc[0]
            color, estado_txt, hex_c = calcular_semaforo(info.get("Ultima Actualizacion",""), info.get("Alerta Activa", "TRUE"))
            
            etapa_raw = info.get("Etapa Procesal", "AVANCE (0%)")
            pct_actual = calcular_progreso(etapa_raw)
            nota_fija = info.get("Notas Fijas", "")
            
            # HEADER LIMPIO (SOLO DATOS)
            st.markdown(f"""
            <div class="case-header-compact">
                <div style="width:100%">
                    <div class="header-top">
                        <div>
                            <div class="case-name">{seleccion} <span class="area-tag">{info.get('Area','GRAL')}</span></div>
                            <div class="case-details">⚖️ {info.get('Caratula Completa','')} • 🏛️ {info.get('Juzgado','')}</div>
                        </div>
                        <div style="text-align:right;">
                            <span style="background:{hex_c}; width:15px; height:15px; border-radius:50%; display:inline-block;"></span>
                            <span style="font-size:14px; font-weight:bold; color:white; margin-left:5px;">{estado_txt}</span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if nota_fija: st.markdown(f'<div class="fixed-notes">📌 {nota_fija}</div>', unsafe_allow_html=True)
            
            # CONTROL MANUAL DE AVANCE (CASILLA SIMPLE)
            c_prog_1, c_prog_2 = st.columns([3, 1])
            with c_prog_1:
                # INPUT NUMÉRICO DIRECTO
                pct_nuevo = st.number_input("Avance de Expediente (%)", min_value=0, max_value=100, value=pct_actual)
            with c_prog_2:
                st.write("")
                st.write("")
                if st.button("Actualizar Avance"):
                    actualizar_progreso_manual(seleccion, pct_nuevo)
                    st.rerun()

            # EDICIÓN + ELIMINAR
            with st.expander("✏️ Editar Datos / Eliminar"):
                with st.form("edicion"):
                    e_car = st.text_input("Carátula", value=info.get('Caratula Completa',''))
                    e_juz = st.text_input("Juzgado", value=info.get('Juzgado',''))
                    e_area = st.text_input("Área", value=info.get('Area',''))
                    e_drv = st.text_input("Link Drive", value=info.get('Link Drive',''))
                    e_nota = st.text_area("Notas Fijas", value=nota_fija)
                    if st.form_submit_button("💾 Guardar Cambios"):
                        editar_datos_cliente(seleccion, e_car, e_juz, e_drv, e_area, e_nota)
                        st.rerun()
                
                st.divider()
                st.write("**Zona de Peligro:**")
                if st.button("🗑️ ELIMINAR CLIENTE", type="primary"):
                    eliminar_cliente(seleccion)

            st.divider()

            # ACCIONES
            c_tit, c_btns = st.columns([1.5, 1])
            with c_tit: st.write("### 📝 Nueva Entrada")
            with c_btns:
                cb1, cb2 = st.columns(2)
                with cb1:
                    l_drive = info.get("Link Drive", "")
                    if l_drive: st.markdown(f'<a href="{l_drive}" target="_blank" class="btn-drive">📂 DRIVE</a>', unsafe_allow_html=True)
                with cb2:
                    if st.button("👁️ Visto Hoy"):
                        log_visto(seleccion) 
                        st.rerun()

            with st.form("bitacora"):
                texto = st.text_area("", height=100)
                c1, c2 = st.columns([2, 1])
                with c1: tipo = st.selectbox("Tipo", ["📌 Nota", "⚡ Tarea", "📅 Vencimiento", "📞 Llamada"], label_visibility="collapsed")
                with c2: urg = st.checkbox("🔥 Urgente")
                if st.form_submit_button("GUARDAR", use_container_width=True):
                    if texto:
                        prio = "ALTA" if urg else "Normal"
                        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
                        hoja_movimientos.append_row([ahora, seleccion, texto, tipo, prio, "Pendiente"])
                        update_fecha_only(seleccion)
                        st.success("Guardado")
                        st.rerun()

            st.write(" ")
            st.subheader("📜 Historial")
            df_mov = pd.DataFrame(hoja_movimientos.get_all_records())
            if not df_mov.empty and "Expediente" in df_mov.columns:
                filtro = df_mov[df_mov["Expediente"] == seleccion]
                if not filtro.empty:
                    for i, row in filtro.iloc[::-1].iterrows():
                        color_b = '#dc2626' if row.get('Prioridad') == 'ALTA' else '#002b5c'
                        icon = '🔥' if row.get('Prioridad') == 'ALTA' else '📌'
                        if row.get('Tipo') == '👁️ Control': icon = '👁️'
                        c_data, c_edit = st.columns([0.92, 0.08])
                        with c_data:
                            st.markdown(f"""
                            <div class="hist-row" style="border-left: 4px solid {color_b};">
                                <div style="flex-grow:1;">
                                    <span class="hist-meta">{row['Fecha']} • {row['Tipo']} {icon}</span>
                                    <div class="hist-body">{row['Nota']}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        with c_edit:
                            with st.expander("✏️"):
                                n_txt = st.text_input("Txt", value=row['Nota'], key=f"e_{i}")
                                if st.button("💾", key=f"s_{i}"):
                                    editar_nota(seleccion, row['Nota'], n_txt)
                                    st.rerun()
                                if st.button("🗑️", key=f"d_{i}"):
                                    eliminar_nota(seleccion, row['Nota'])
                                    st.rerun()
                else: st.caption("Vacío.")

    elif modo == "Alta Caso":
        st.title("➕ Nuevo Expediente")
        with st.form("alta"):
            c1, c2 = st.columns(2)
            with c1: n = st.text_input("Nombre Corto")
            with c2: area = st.text_input("Área")
            c = st.text_input("Carátula")
            j = st.text_input("Juzgado")
            l = st.text_input("Link Drive")
            nota = st.text_input("Nota Fija")
            if st.form_submit_button("Crear"):
                hoy = datetime.now().strftime("%d/%m/%Y")
                hoja_clientes.append_row([n, c, j, "INICIO (10%)", hoy, "TRUE", l, area, nota])
                st.success(f"Creado: {n}")
else:
    st.error("⚠️ Error de conexión. Verificá 'credentials.json' en PC o Secrets en Nube.")