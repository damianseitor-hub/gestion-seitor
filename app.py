import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import urllib.parse
import numpy as np
import streamlit.components.v1 as components
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="S&V Gestión", page_icon="⚖️", layout="wide")

# --- 2. ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp {background-color: #f7f9fc;}
    
    /* TÍTULO */
    h1 { 
        color: #002b5c; font-size: 22px !important; font-weight: 800; 
        text-transform: uppercase; border-bottom: 2px solid #e1e4e8; 
        padding-bottom: 10px; margin-bottom: 20px; 
    }
    h3 { font-size: 18px !important; color: #444; margin: 0;}

    /* HEADER DE DATOS (AZUL LIMPIO) */
    .case-header-compact {
        background: linear-gradient(135deg, #002b5c 0%, #001a33 100%);
        color: white; border-radius: 12px; padding: 25px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2); margin-bottom: 15px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .case-name { font-size: 26px; font-weight: 800; margin: 0; }
    .case-details { font-size: 15px; color: #dbeafe; margin-top: 5px;}
    .area-tag { background: rgba(255,255,255,0.15); padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-left: 10px; vertical-align: middle; }

    /* NOTAS FIJAS */
    .fixed-notes { background-color: #fff8e1; border-left: 4px solid #ffc107; color: #856404; padding: 10px; border-radius: 4px; font-size: 14px; margin-bottom: 15px; }

    /* INPUTS Y BOTONES */
    .stTextArea textarea { font-size: 16px; border: 3px solid #002b5c !important; border-radius: 8px; }
    .stButton>button { background-color: #002b5c; color: white; border-radius: 6px; font-weight: bold; border: none; height: 2.8em; }
    
    /* HISTORIAL COMPACTO */
    .hist-row {
        background-color: white; border-bottom: 1px solid #eee;
        padding: 12px 10px; margin-bottom: 5px; border-radius: 5px;
        display: flex; align-items: flex-start;
    }
    .hist-meta { font-size: 11px; color: #666; font-weight: bold; text-transform: uppercase; min-width: 120px; }
    .hist-body { font-size: 15px; color: #222; line-height: 1.4; flex-grow: 1; }
    
    /* Links */
    .btn-link { display: block; width: 100%; padding: 8px; text-align: center; border-radius: 5px; text-decoration: none; font-weight: 700; font-size: 12px; margin-bottom: 4px; border: 1px solid #ccc; }
    .btn-sac {background:#fff; color:#002b5c !important;}
    .btn-drive { display: inline-block; background: #FFD04B; color: #000 !important; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 13px; text-decoration: none; border: 1px solid #e6b800; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CALCULADORA HTML (CÓDIGO COMPLETO SIN COMPRIMIR) ---
HTML_CALCULADORA_FULL = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calculadora Judicial</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 10px; background-color: #fff; color: #333; }
        .container { max-width: 100%; margin: auto; padding: 15px; }
        .tabs { display: flex; margin-bottom: 20px; border-bottom: 2px solid #ddd; }
        .tab-button { background-color: #eee; border: none; padding: 10px; cursor: pointer; flex:1; font-weight: bold; color: #555; }
        .tab-button.active { background-color: #2c3e50; color: white; }
        .tab-content { display: none; padding: 10px 0; }
        .tab-content.active { display: block; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea { width: 100%; padding: 8px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background-color: #34495e; color: white; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; }
        .result { margin-top: 20px; padding: 15px; background-color: #e8f5e9; color: #2e7d32; font-weight: bold; text-align: center; display: none; }
        .link-pj { margin-bottom: 15px; text-align: center; }
        a { color: #007bff; text-decoration: none; }
        
        /* Calendario */
        .calendar-nav { display: flex; justify-content: space-between; margin-bottom: 10px; background:#f0f0f0; padding:5px; }
        .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; background: #eee; }
        .calendar-day { background: #fff; padding: 10px; text-align: center; cursor: pointer; }
        .calendar-day.selected { background: #ffe0b2; border: 1px solid orange; }
        .calendar-day-header { font-weight: bold; text-align: center; padding: 5px; }
        
        /* JUS */
        .jus-box { background-color: #e6f2f9; padding: 15px; text-align: center; border: 1px solid #b3d9f0; border-radius: 8px; }
        .jus-input { font-size: 1.4em; width: 150px; text-align: center; color: #007bff; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="tabs">
            <button class="tab-button active" onclick="openTab('plazos',this)">Plazos</button>
            <button class="tab-button" onclick="openTab('jus',this)">JUS</button>
        </div>

        <div id="plazos" class="tab-content active">
            <label>Fecha de notificación:</label>
            <input type="date" id="fn">
            
            <label>Días eCédula:</label>
            <div style="display:flex; gap:10px;">
                <input type="range" id="rgDC" min="0" max="10" value="3" oninput="u('nDC',this.value)">
                <input type="text" id="nDC" value="3" style="width:50px; text-align:center">
            </div>

            <label>Días Emplazamiento:</label>
            <div style="display:flex; gap:10px;">
                <input type="range" id="rgDE" min="1" max="50" value="5" oninput="u('nDE',this.value)">
                <input type="text" id="nDE" value="5" style="width:50px; text-align:center">
            </div>

            <div class="link-pj"><a href="https://www.justiciacordoba.gob.ar/JusticiaCordoba/servicios/DiasInhabiles.aspx" target="_blank">📅 Ver Días Inhábiles PJ</a></div>
            
            <textarea id="dInh" rows="3" placeholder="Feriados (DD/MM/YYYY)..."></textarea>

            <div class="calendar-nav">
                <button style="width:auto" onclick="chM(-1)">&lt;</button>
                <span id="curM" style="font-weight:bold"></span>
                <button style="width:auto" onclick="chM(1)">&gt;</button>
            </div>
            <div class="calendar-grid" id="calG"></div>

            <button onclick="cP()">Calcular Vencimiento</button>
            <div class="result" id="resP"></div>
        </div>

        <div id="jus" class="tab-content">
            <div class="jus-box">
                <label>Valor JUS ($):</label><br>
                <input type="text" id="vJ" class="jus-input" value="34546.88">
                <br><small><a href="https://www.justiciacordoba.gob.ar/JusticiaCordoba/Servicios/CalculosJudiciales.aspx" target="_blank">Ver Oficial</a></small>
            </div>
            <br>
            <label>Cantidad de JUS:</label>
            <input type="text" id="cJ" value="10">
            <button onclick="cJ()">Calcular a Pesos</button>
            <div class="result" id="resJ"></div>
        </div>
    </div>

    <script>
        let d=new Date(); const mN=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
        
        function openTab(n,b){
            document.getElementById('plazos').style.display='none';
            document.getElementById('jus').style.display='none';
            document.getElementById(n).style.display='block';
            document.querySelectorAll('.tab-button').forEach(x=>x.classList.remove('active'));
            b.classList.add('active');
        }
        
        function u(id,v){document.getElementById(id).value=v;}
        function pN(s){return parseFloat(s.replace(/\./g,'').replace(/,/g,'.'))}
        function fmt(n){return n.toLocaleString('es-AR',{minimumFractionDigits:2})}
        
        function rCal(){
            document.getElementById('curM').innerText=mN[d.getMonth()]+" "+d.getFullYear();
            const g=document.getElementById('calG');
            g.innerHTML='<div>D</div><div>L</div><div>M</div><div>M</div><div>J</div><div>V</div><div>S</div>';
            let f=new Date(d.getFullYear(),d.getMonth(),1).getDay();
            let t=new Date(d.getFullYear(),d.getMonth()+1,0).getDate();
            for(let i=0;i<f;i++)g.innerHTML+='<div style="background:#eee"></div>';
            for(let i=1;i<=t;i++){
                let cd=new Date(d.getFullYear(),d.getMonth(),i);
                let s=cd.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' });
                let sel=document.getElementById('dInh').value.includes(s)?' selected':'';
                g.innerHTML+=`<div class="calendar-day${sel}" onclick="tg('${s}',this)">${i}</div>`;
            }
        }
        
        function tg(s,e){
            let v=document.getElementById('dInh').value;
            if(v.includes(s))v=v.replace(s,'').replace(', ,',',');
            else v+=v?', '+s:s;
            document.getElementById('dInh').value=v; e.classList.toggle('selected');
        }
        function chM(n){d.setMonth(d.getMonth()+n);rCal()}
        
        function cP(){
            let fnv=document.getElementById('fechaNotificacion').value;
            if(!fnv)return;
            let date=new Date(fnv+'T00:00:00');
            let days=parseInt(document.getElementById('nDC').value)+parseInt(document.getElementById('nDE').value);
            let inh=document.getElementById('dInh').value;
            let c=0;
            date.setDate(date.getDate()+1);
            while(c<days){
                let s=date.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' });
                let isWe=date.getDay()==0||date.getDay()==6;
                let isInh=inh.includes(s);
                if(!isWe&&!isInh)c++;
                if(c<days)date.setDate(date.getDate()+1);
            }
            // Cargo
            let final=new Date(date); final.setDate(final.getDate()+1);
            while(final.getDay()==0||final.getDay()==6||inh.includes(final.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' }))) final.setDate(final.getDate()+1);
            
            document.getElementById('resP').style.display='block';
            document.getElementById('resP').innerHTML="Vence: "+date.toLocaleDateString('es-AR')+"<br>Cargo: "+final.toLocaleDateString('es-AR')+" 10hs";
        }
        
        function cJ(){
            let v = pN(document.getElementById('vJ').value);
            let c = pN(document.getElementById('cJ').value);
            document.getElementById('resJ').style.display='block';
            document.getElementById('resJ').innerHTML="$ "+fmt(v*c);
        }
        
        rCal();
    </script>
</body>
</html>
"""

# --- 4. CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    libro = client.open("Bitacora Seitor")
    return libro

try:
    libro = conectar()
    hoja_movimientos = libro.sheet1
    hoja_clientes = libro.worksheet("Clientes")
    conexion = True
except:
    st.error("⚠️ Error de conexión")
    conexion = False

# --- 5. LÓGICA DE NEGOCIO ---
def calcular_progreso(etapa_nombre):
    # Extrae porcentaje del texto "NOMBRE (XX%)"
    if "(" in etapa_nombre and "%)" in etapa_nombre:
        try:
            return int(etapa_nombre.split("(")[1].split("%")[0])
        except: pass
    return 10

def calcular_semaforo(ultima, alerta):
    if str(alerta).upper() == "FALSE": return "⚪", "Pausado", "#ccc"
    try:
        dias = (datetime.now() - datetime.strptime(str(ultima), "%d/%m/%Y")).days
        if dias <= 7: return "🟢", f"Al día ({dias}d)", "#4ade80"
        elif dias <= 21: return "🟡", f"Atención ({dias}d)", "#facc15"
        else: return "🔴", f"CRÍTICO ({dias}d)", "#f87171"
    except: return "⚪", "-", "#ccc"

def log_visto(nombre):
    """Solo se ejecuta al tocar el botón Visto"""
    ahora = datetime.now()
    try:
        cell = hoja_clientes.find(nombre)
        hoja_clientes.update_cell(cell.row, 5, ahora.strftime("%d/%m/%Y"))
        hoja_movimientos.append_row([ahora.strftime("%d/%m/%Y %H:%M"), nombre, "Expediente revisado / Visto", "👁️ Control", "Normal", "Listo"])
        st.toast(f"✅ {nombre}: Registrado.")
        time.sleep(1.5) 
    except: pass

def update_fecha_only(nombre):
    try:
        cell = hoja_clientes.find(nombre)
        hoja_clientes.update_cell(cell.row, 5, datetime.now().strftime("%d/%m/%Y"))
        time.sleep(1)
    except: pass

def actualizar_progreso_manual(nombre, nuevo_porcentaje):
    try:
        # Guardamos texto genérico con porcentaje
        etapa_str = f"ETAPA ({nuevo_porcentaje}%)"
        cell = hoja_clientes.find(nombre)
        hoja_clientes.update_cell(cell.row, 4, etapa_str)
        st.toast(f"✅ Progreso guardado.")
        time.sleep(1.5)
    except Exception as e: st.error(f"Error: {e}")

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
    except Exception as e: st.error(f"Error: {e}")

def editar_nota(nombre, txt_viejo, txt_nuevo):
    try:
        data = hoja_movimientos.get_all_records()
        for i, row in enumerate(data):
            if row['Expediente'] == nombre and row['Nota'] == txt_viejo:
                hoja_movimientos.update_cell(i+2, 3, txt_nuevo)
                st.toast("Editado")
                return
    except: st.error("Error")

def eliminar_nota(nombre, txt_viejo):
    try:
        data = hoja_movimientos.get_all_records()
        for i, row in enumerate(data):
            if row['Expediente'] == nombre and row['Nota'] == txt_viejo:
                hoja_movimientos.delete_rows(i+2)
                st.toast("Eliminado")
                return
    except: st.error("Error")

def link_cal(titulo, fecha):
    base = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    txt = urllib.parse.quote(titulo)
    f_str = fecha.strftime("%Y%m%d")
    return f"{base}&text={txt}&dates={f_str}T090000Z/{f_str}T10000Z"

# --- 6. INTERFAZ ---
if conexion:
    with st.sidebar:
        st.write("### 🏛️ S&V")
        modo = st.radio("Menú", ["Escritorio", "Calculadora", "Alta Caso"], label_visibility="collapsed")
        st.divider()
        st.markdown('<a href="https://www.justiciacordoba.gob.ar/JusticiaCordoba/extranet.aspx" target="_blank" class="btn-link btn-sac">🔐 SAC</a>', unsafe_allow_html=True)
        st.markdown('<a href="https://www.justiciacordoba.gob.ar/JusticiaCordoba/servicios/DiasInhabiles.aspx" target="_blank" class="btn-link btn-sac">📅 Inhábiles</a>', unsafe_allow_html=True)
        st.markdown(f'<a href="file:///C:/Users/damia/Desktop/S&V%20d%C3%ADas%20h%C3%A1biles%20y%20JUS.html" target="_blank" class="btn-link btn-sac">🧮 Calc PC</a>', unsafe_allow_html=True)

    if modo == "Escritorio":
        st.title("SEITOR & VOITZUK | GESTIÓN")

        try:
            df = pd.DataFrame(hoja_clientes.get_all_records())
            lista = df["Nombre Corto"].tolist() if not df.empty else []
        except: lista = []

        if not lista: st.info("Cargá un caso.")
        else:
            seleccion = st.selectbox("Seleccionar:", lista, label_visibility="collapsed")
            
            # Recarga forzada
            info = df[df["Nombre Corto"] == seleccion].iloc[0]
            
            color, estado_txt, hex_c = calcular_semaforo(info.get("Ultima Actualizacion",""), info.get("Alerta Activa", "TRUE"))
            
            # Lógica Manual Pura (Lee el string, extrae el numero)
            etapa_raw = info.get("Etapa Procesal", "INICIO (10%)")
            pct_actual = calcular_progreso(etapa_raw)
            
            nota_fija = info.get("Notas Fijas", "")
            
            # 1. HEADER INTEGRADO (SOLO DATOS)
            st.markdown(f"""
            <div class="case-header-compact">
                <div>
                    <div class="case-name">{seleccion} <span class="area-tag">{info.get('Area','GRAL')}</span></div>
                    <div class="case-details">⚖️ {info.get('Caratula Completa','')} • 🏛️ {info.get('Juzgado','')}</div>
                </div>
                <div style="text-align:right;">
                    <span style="background:{hex_c}; width:12px; height:12px; border-radius:50%; display:inline-block;"></span>
                    <span style="font-size:12px; color:white;">{estado_txt}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if nota_fija: st.markdown(f'<div class="fixed-notes">📌 {nota_fija}</div>', unsafe_allow_html=True)
            
            # 2. BARRA DE PROGRESO MANUAL Y VISIBLE
            st.write(f"**Avance del Proceso:** {pct_actual}%")
            
            # SLIDER PRINCIPAL
            c_prog_1, c_prog_2 = st.columns([4, 1])
            with c_prog_1:
                pct_nuevo = st.slider("Nivel de Avance", 0, 100, pct_actual, label_visibility="collapsed")
                st.caption("Ref: 10% Inicio | 25% Litis | 50% Prueba | 75% Alegatos | 100% Sentencia")
            with c_prog_2:
                if st.button("Actualizar Barra"):
                    actualizar_progreso_manual(seleccion, pct_nuevo)
                    st.rerun()

            # 3. EDICIÓN DATOS
            with st.expander("✏️ Editar Datos del Expediente"):
                with st.form("editar_datos_form"):
                    st.write(f"Editando: **{seleccion}**")
                    e_car = st.text_input("Carátula", value=info.get('Caratula Completa',''))
                    e_juz = st.text_input("Juzgado", value=info.get('Juzgado',''))
                    e_area = st.text_input("Área", value=info.get('Area',''))
                    e_drv = st.text_input("Link Drive", value=info.get('Link Drive',''))
                    e_nota = st.text_area("Notas Fijas", value=nota_fija)
                    if st.form_submit_button("💾 Guardar Cambios"):
                        editar_datos_cliente(seleccion, e_car, e_juz, e_drv, e_area, e_nota)
                        st.rerun()

            st.divider()

            # 4. ACCIÓN
            c_tit, c_btns = st.columns([1.5, 1])
            with c_tit: st.write("### 📝 Nueva Entrada")
            with c_btns:
                cb1, cb2 = st.columns(2)
                with cb1:
                    l_drive = info.get("Link Drive", "")
                    if l_drive: st.markdown(f'<a href="{l_drive}" target="_blank" class="btn-drive">📂 DRIVE</a>', unsafe_allow_html=True)
                with cb2:
                    # BOTÓN VISTO (LOGUEA)
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
                        
                        # SOLO FECHA (NO LOGUEA)
                        update_fecha_only(seleccion)
                        
                        st.success("Guardado")
                        st.rerun()

            st.write(" ")
            st.subheader("📜 Historial")
            
            # 5. HISTORIAL
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

    elif modo == "Calculadora":
        st.title("🛠️ Calculadora")
        components.html(HTML_CALCULADORA_FULL, height=1200, scrolling=True)

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
