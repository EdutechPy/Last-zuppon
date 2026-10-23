"""
CuponPY - Ofertas y descuentos por ciudad en Paraguay.

Flujo:
  1. El cliente elige su ciudad y ve las ofertas.
  2. Reclama el cupón (nombre + celular) y recibe un código.
  3. Va al local, muestra el código en el local y obtiene su descuento.
  4. El comercio ingresa el código en su panel y lo marca como canjeado.
"""
import os
import re
import secrets
import sqlite3
from datetime import date, timedelta
from functools import wraps
from io import BytesIO
from urllib.parse import urlencode
import base64

from flask import (Flask, abort, flash, g, jsonify, make_response, redirect,
                   render_template, request, session, url_for)
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash
import qrcode

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cambiar-esto-en-produccion")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ofertas.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
DEMO_FOTOS_DIR = os.path.join(BASE_DIR, "demo_fotos")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024   # fotos de celular de hasta 12 MB
Image.MAX_IMAGE_PIXELS = 60_000_000
os.makedirs(UPLOAD_DIR, exist_ok=True)

CIUDADES = [
    "Asunción", "Capiatá", "Caacupé", "Ciudad del Este", "Concepción",
    "Coronel Oviedo", "Encarnación", "Fernando de la Mora", "Hernandarias",
    "Lambaré", "Luque", "María Auxiliadora", "Mariano Roque Alonso",
    "Minga Guazú", "Naranjal", "Pedro Juan Caballero", "Pilar",
    "Presidente Franco", "San Alberto", "San Lorenzo", "Santa Rita", "Villarrica",
    "Villa Elisa", "Ñemby",
]
CATEGORIAS = [
    "Carnicería", "Supermercado", "Restaurante", "Panadería", "Farmacia",
    "Ferretería", "Ropa y calzado", "Belleza", "Café y helados", "Servicios", "Otros",
]
CAT = {
    "Carnicería":     {"emoji": "🥩", "color": "#ff9aa2"},
    "Supermercado":   {"emoji": "🛒", "color": "#ffe27a"},
    "Restaurante":    {"emoji": "🍔", "color": "#ffb366"},
    "Panadería":      {"emoji": "🥐", "color": "#d4b8ff"},
    "Farmacia":       {"emoji": "💊", "color": "#8fe3c0"},
    "Ferretería":     {"emoji": "🔧", "color": "#9cc9ff"},
    "Ropa y calzado": {"emoji": "👕", "color": "#b8f0a5"},
    "Belleza":        {"emoji": "💇", "color": "#ffb8e1"},
    "Café y helados": {"emoji": "🍦", "color": "#a8ecee"},
    "Servicios":      {"emoji": "🛠️", "color": "#bcc7d9"},
    "Otros":          {"emoji": "🎁", "color": "#e4e1d8"},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS comercios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    telefono TEXT,
    ciudad TEXT NOT NULL,
    direccion TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ofertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comercio_id INTEGER NOT NULL REFERENCES comercios(id),
    titulo TEXT NOT NULL,
    descripcion TEXT,
    categoria TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    direccion TEXT NOT NULL,
    coordenadas TEXT,
    precio_normal INTEGER,
    descuento INTEGER NOT NULL,
    valido_hasta TEXT NOT NULL,
    cupos INTEGER NOT NULL,
    foto TEXT,
    activa INTEGER NOT NULL DEFAULT 1,
    destacada INTEGER NOT NULL DEFAULT 0,
    urgente INTEGER NOT NULL DEFAULT 0,
    creada TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cupones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    oferta_id INTEGER NOT NULL REFERENCES ofertas(id),
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    telefono TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'activo',
    creado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    canjeado_en TEXT
);
"""

OFERTA_SELECT = """
SELECT o.*, c.nombre AS comercio, c.telefono AS comercio_tel,
       (SELECT COUNT(*) FROM cupones WHERE oferta_id = o.id) AS reclamados,
       COALESCE(o.destacada, 0) AS destacada,
       COALESCE(o.urgente, 0) AS urgente
FROM ofertas o JOIN comercios c ON c.id = o.comercio_id
"""


# ---------- Base de datos ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    columnas = [fila[1] for fila in db.execute("PRAGMA table_info(ofertas)")]
    if "foto" not in columnas:
        db.execute("ALTER TABLE ofertas ADD COLUMN foto TEXT")
    if "destacada" not in columnas:
        db.execute("ALTER TABLE ofertas ADD COLUMN destacada INTEGER NOT NULL DEFAULT 0")
    if "urgente" not in columnas:
        db.execute("ALTER TABLE ofertas ADD COLUMN urgente INTEGER NOT NULL DEFAULT 0")
    if "coordenadas" not in columnas:
        db.execute("ALTER TABLE ofertas ADD COLUMN coordenadas TEXT")
    if "whatsapp" not in columnas:
        db.execute("ALTER TABLE ofertas ADD COLUMN whatsapp TEXT")
    if "principal" not in columnas:
        db.execute("ALTER TABLE ofertas ADD COLUMN principal INTEGER NOT NULL DEFAULT 0")
    db.commit()
    db.close()


init_db()


# ---------- Utilidades ----------
def hoy():
    return date.today().isoformat()


def solo_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def a_entero(valor, defecto=None):
    try:
        return int(str(valor).replace(".", "").strip())
    except (TypeError, ValueError):
        return defecto


def generar_codigo(db):
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O/1/I para evitar confusiones
    for _ in range(20):
        codigo = "".join(secrets.choice(alfabeto) for _ in range(6))
        if not db.execute("SELECT 1 FROM cupones WHERE codigo = ?", (codigo,)).fetchone():
            return codigo
    raise RuntimeError("No se pudo generar un código único")


def generar_qr(codigo, info_cupon=None):
    """Genera un código QR y lo devuelve como data URI en base64.
    
    Si info_cupon es None, genera solo el código.
    Si info_cupon tiene datos (comercio, descuento), genera URL completa para la app.
    """
    # Si tenemos info del cupón, generar URL completa para la app Android
    if info_cupon:
        params = {
            'id': codigo,
            'cupon': codigo,  # app puede buscar ambos parámetros
            'store': info_cupon.get('comercio', ''),
            'comercio': info_cupon.get('comercio', ''),
            'descuento': f"{info_cupon.get('descuento', '')}%",
            'discount': f"{info_cupon.get('descuento', '')}%"
        }
        # Usar la URL base configurada o localhost por defecto
        base_url = request.url_root.rstrip('/') if request else 'http://localhost:5000'
        qr_content = f"{base_url}/cupon?{urlencode(params)}"
    else:
        # Formato anterior para compatibilidad
        qr_content = codigo
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_content)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#12183a", back_color="white")
    
    # Convertir a base64
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"


def guardar_foto(origen):
    """Procesa una foto (archivo subido o ruta) y devuelve el nombre base, o None si no es imagen.

    Corrige la rotación del celular, quita datos EXIF (ubicación) y guarda dos tamaños:
    1200 px para el detalle y 600 px (_m) para las tarjetas, así carga rápido con datos móviles.
    """
    try:
        img = Image.open(origen)
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        return None
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[-1])
        img = fondo
    else:
        img = img.convert("RGB")
    nombre = secrets.token_hex(8)
    for sufijo, lado in (("", 1200), ("_m", 600)):
        copia = img.copy()
        copia.thumbnail((lado, lado))
        copia.save(os.path.join(UPLOAD_DIR, f"{nombre}{sufijo}.jpg"), "JPEG", quality=82, optimize=True)
    return nombre


def borrar_foto(nombre):
    for sufijo in ("", "_m"):
        try:
            os.remove(os.path.join(UPLOAD_DIR, f"{nombre}{sufijo}.jpg"))
        except OSError:
            pass


@app.template_global("foto_url")
def foto_url(nombre, tam="", externa=False):
    archivo = f"uploads/{nombre}{'_m' if tam == 'm' else ''}.jpg"
    return url_for("static", filename=archivo, _external=externa)


@app.errorhandler(413)
def foto_muy_grande(_e):
    flash("La foto pesa demasiado (máximo 12 MB). Probá con otra.", "error")
    return redirect(request.referrer or url_for("panel"))


@app.template_filter("gs")
def formato_gs(n):
    return f"{int(n):,}".replace(",", ".") + " Gs."


@app.template_filter("fecha")
def formato_fecha(iso):
    try:
        y, m, d = iso[:10].split("-")
        return f"{d}/{m}/{y}"
    except Exception:
        return iso


@app.template_filter("cat")
def meta_categoria(nombre):
    return CAT.get(nombre, CAT["Otros"])


@app.template_filter("cuando")
def cuando(dias):
    if dias <= 0:
        return "Termina hoy"
    if dias == 1:
        return "Termina mañana"
    return f"Quedan {dias} días"


def enriquecer(filas):
    """Agrega cupones restantes y días que faltan para que termine la oferta."""
    salida = []
    for f in filas:
        d = dict(f)
        d["restantes"] = d["cupos"] - d["reclamados"]
        d["dias"] = (date.fromisoformat(d["valido_hasta"]) - date.today()).days
        salida.append(d)
    return salida


def ciudad_mas_activa():
    r = get_db().execute(
        "SELECT ciudad FROM ofertas WHERE activa = 1 AND valido_hasta >= ? "
        "GROUP BY ciudad ORDER BY COUNT(*) DESC LIMIT 1", (hoy(),)).fetchone()
    return r["ciudad"] if r else ""


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("comercio_id"):
            flash("Ingresá a tu cuenta de comercio para continuar.", "error")
            return redirect(url_for("login", next=request.path))
        return vista(*args, **kwargs)
    return envoltura


@app.context_processor
def globales():
    return {"CIUDADES": CIUDADES, "CATEGORIAS": CATEGORIAS, "CAT": CAT,
            "ciudad_actual": g.get("ciudad_actual", request.cookies.get("ciudad", ""))}


# ---------- Público: ver ofertas y reclamar ----------
@app.route("/")
def index():
    param = request.args.get("ciudad")
    elegido = param if param is not None else request.cookies.get("ciudad")
    if elegido is None:                     # primera visita: la ciudad con más ofertas
        elegido = ciudad_mas_activa()
    ciudad = elegido if elegido in CIUDADES else ""
    g.ciudad_actual = ciudad

    categoria = request.args.get("categoria", "").strip()
    q = request.args.get("q", "").strip()

    sql = OFERTA_SELECT + " WHERE o.activa = 1 AND o.valido_hasta >= ?"
    params = [hoy()]
    if ciudad:
        sql += " AND o.ciudad = ?"
        params.append(ciudad)
    if categoria:
        sql += " AND o.categoria = ?"
        params.append(categoria)
    if q:
        sql += " AND (o.titulo LIKE ? OR o.descripcion LIKE ? OR c.nombre LIKE ?)"
        params += [f"%{q}%"] * 3
    sql += " ORDER BY COALESCE(o.principal, 0) DESC, o.id DESC"  # Priorizar ofertas principales

    todas_ofertas = enriquecer(get_db().execute(sql, params).fetchall())
    
    # FILTRAR: Solo mostrar 1 oferta por negocio (la más reciente)
    ofertas_vistas = {}
    ofertas_filtradas = []
    for oferta in todas_ofertas:
        if oferta["comercio_id"] not in ofertas_vistas:
            ofertas_vistas[oferta["comercio_id"]] = True
            ofertas_filtradas.append(oferta)
    
    ofertas = ofertas_filtradas
    vivas = [o for o in ofertas if o["restantes"] > 0]

    destacada, pronto, resto = None, [], ofertas
    if not q and not categoria and vivas:
        # Buscar oferta marcada como destacada, si no hay, usar la más reclamada
        destacadas_marcadas = [o for o in vivas if o.get("destacada", 0) == 1]
        if destacadas_marcadas:
            # Priorizar por más reclamados, luego por ID más alto (más reciente)
            destacada = sorted(destacadas_marcadas, key=lambda o: (-o["reclamados"], -o["id"]))[0]
        else:
            destacada = sorted(vivas, key=lambda o: (-o["reclamados"], -o["id"]))[0]
        
        # Buscar ofertas marcadas como urgentes, si no hay, usar las que terminan pronto
        urgentes_marcadas = [o for o in vivas if o.get("urgente", 0) == 1 and o["id"] != destacada["id"]]
        if urgentes_marcadas:
            # Ordenar por días restantes (las que terminan primero)
            pronto = sorted(urgentes_marcadas, key=lambda o: o["dias"])[:8]
        else:
            pronto = sorted([o for o in vivas if o["dias"] <= 7 and o["id"] != destacada["id"]],
                            key=lambda o: o["dias"])[:8]
        
        usadas = {destacada["id"]} | {o["id"] for o in pronto}
        resto = [o for o in ofertas if o["id"] not in usadas]

    # Otras ciudades con ofertas (para seguir descubriendo)
    otras = [r for r in get_db().execute(
        "SELECT ciudad, COUNT(*) AS n FROM ofertas WHERE activa = 1 AND valido_hasta >= ? "
        "GROUP BY ciudad ORDER BY n DESC", (hoy(),)).fetchall() if r["ciudad"] != ciudad]

    respuesta = make_response(render_template(
        "index.html", ofertas=ofertas, destacada=destacada, pronto=pronto, resto=resto,
        otras=otras, ciudad=ciudad, categoria=categoria, q=q, total=len(vivas)))
    if param is not None:
        respuesta.set_cookie("ciudad", ciudad, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return respuesta


def obtener_oferta(oferta_id):
    oferta = get_db().execute(OFERTA_SELECT + " WHERE o.id = ?", (oferta_id,)).fetchone()
    if not oferta:
        abort(404)
    return oferta


@app.route("/oferta/<int:oferta_id>")
def oferta(oferta_id):
    db = get_db()
    o = obtener_oferta(oferta_id)
    vigente = o["activa"] and o["valido_hasta"] >= hoy()
    restantes = o["cupos"] - o["reclamados"]
    dias = (date.fromisoformat(o["valido_hasta"]) - date.today()).days
    
    # Obtener otras ofertas del mismo negocio (excluyendo la actual)
    otras_ofertas_negocio = enriquecer(db.execute(
        OFERTA_SELECT + """ WHERE o.comercio_id = ? AND o.id != ? 
                           AND o.activa = 1 AND o.valido_hasta >= ?
                           ORDER BY o.id DESC LIMIT 10""",
        (o["comercio_id"], oferta_id, hoy())
    ).fetchall())
    
    return render_template("oferta.html", o=o, vigente=vigente, restantes=restantes, dias=dias,
                          otras_ofertas=otras_ofertas_negocio)


@app.route("/oferta/<int:oferta_id>/reclamar", methods=["POST"])
def reclamar(oferta_id):
    db = get_db()
    o = obtener_oferta(oferta_id)

    if not o["activa"] or o["valido_hasta"] < hoy():
        flash("Esta oferta ya no está disponible.", "error")
        return redirect(url_for("oferta", oferta_id=oferta_id))

    if o["reclamados"] >= o["cupos"]:
        flash("Se agotaron los cupones de esta oferta.", "error")
        return redirect(url_for("oferta", oferta_id=oferta_id))

    codigo = generar_codigo(db)
    db.execute("INSERT INTO cupones (oferta_id, codigo, nombre, telefono) VALUES (?,?,?,?)",
               (oferta_id, codigo, "Usuario", ""))
    db.commit()
    return redirect(url_for("cupon", codigo=codigo))


@app.route("/cupon/<codigo>")
def cupon(codigo):
    c = get_db().execute(
        """SELECT cu.*, o.titulo, o.descuento, o.precio_normal, o.valido_hasta,
                  o.direccion, o.ciudad, o.categoria, o.foto, o.id AS oferta_id, co.nombre AS comercio
           FROM cupones cu
           JOIN ofertas o ON o.id = cu.oferta_id
           JOIN comercios co ON co.id = o.comercio_id
           WHERE cu.codigo = ?""", (codigo.upper(),)).fetchone()
    if not c:
        abort(404)
    vencido = c["valido_hasta"] < hoy()
    # Generar QR con URL completa para que funcione con la app Android
    info_qr = {
        'comercio': c["comercio"],
        'descuento': c["descuento"]
    }
    qr_data = generar_qr(c["codigo"], info_qr)
    return render_template("cupon.html", c=c, vencido=vencido, qr_data=qr_data)


@app.route("/mis-cupones")
def mis_cupones():
    """Muestra los cupones guardados en localStorage del navegador."""
    return render_template("mis_cupones.html")


@app.route("/api/qr/<codigo>")
def api_qr(codigo):
    """API para generar QR de un cupón específico."""
    c = get_db().execute(
        """SELECT cu.codigo, o.descuento, co.nombre AS comercio
           FROM cupones cu
           JOIN ofertas o ON o.id = cu.oferta_id
           JOIN comercios co ON co.id = o.comercio_id
           WHERE cu.codigo = ?""", (codigo.upper(),)).fetchone()
    if not c:
        return jsonify({"error": "Cupón no encontrado"}), 404
    
    # Generar QR con URL completa para la app
    info_qr = {
        'comercio': c["comercio"],
        'descuento': c["descuento"]
    }
    qr_data = generar_qr(c["codigo"], info_qr)
    return jsonify({"qr": qr_data, "codigo": c["codigo"]})


@app.route("/api/cupon/<codigo>")
def api_cupon(codigo):
    """API para obtener información completa de un cupón incluyendo foto."""
    c = get_db().execute(
        """SELECT cu.codigo, cu.estado, cu.canjeado_en, o.titulo, o.descuento, o.foto, o.categoria, o.valido_hasta,
                  o.ciudad, co.nombre AS comercio
           FROM cupones cu
           JOIN ofertas o ON o.id = cu.oferta_id
           JOIN comercios co ON co.id = o.comercio_id
           WHERE cu.codigo = ?""", (codigo.upper(),)).fetchone()
    
    if not c:
        return jsonify({"error": "Cupón no encontrado"}), 404
    
    # Generar QR con URL completa para la app
    info_qr = {
        'comercio': c["comercio"],
        'descuento': c["descuento"]
    }
    
    return jsonify({
        "codigo": c["codigo"],
        "titulo": c["titulo"],
        "descuento": c["descuento"],
        "comercio": c["comercio"],
        "ciudad": c["ciudad"],
        "categoria": c["categoria"],
        "validoHasta": c["valido_hasta"],
        "estado": c["estado"],
        "canjeadoEn": c["canjeado_en"],
        "foto": url_for("static", filename=f"uploads/{c['foto']}_m.jpg", _external=True) if c["foto"] else None,
        "qr": generar_qr(c["codigo"], info_qr)
    })


@app.route("/api/validate-coupon", methods=["POST"])
def validate_coupon():
    """API para validar y canjear cupones desde la app Android Zuppon Scanner."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "code": "INVALID_REQUEST",
                "message": "Solicitud inválida"
            }), 400
        
        coupon_id = data.get("coupon_id", "").strip().upper()
        device_id = data.get("device_id", "")
        
        if not coupon_id:
            return jsonify({
                "status": "error",
                "code": "MISSING_COUPON_ID",
                "message": "Falta el ID del cupón"
            }), 400
        
        db = get_db()
        
        # Buscar el cupón con toda su información
        c = db.execute(
            """SELECT cu.*, o.titulo, o.descuento, o.precio_normal, o.valido_hasta,
                      o.direccion, o.ciudad, o.categoria, co.nombre AS comercio
               FROM cupones cu
               JOIN ofertas o ON o.id = cu.oferta_id
               JOIN comercios co ON co.id = o.comercio_id
               WHERE cu.codigo = ?""", (coupon_id,)).fetchone()
        
        # 1. Cupón no existe
        if not c:
            return jsonify({
                "status": "error",
                "code": "NOT_FOUND",
                "message": "Cupón no encontrado"
            }), 404
        
        # 2. Cupón expirado
        if c["valido_hasta"] < hoy():
            return jsonify({
                "status": "error",
                "code": "EXPIRED",
                "message": "Este cupón ha expirado",
                "expired_at": c["valido_hasta"],
                "coupon": {
                    "id": c["codigo"],
                    "store": c["comercio"],
                    "title": c["titulo"],
                    "discount": f"{c['descuento']}%"
                }
            }), 410
        
        # 3. Cupón ya fue usado
        if c["estado"] == "canjeado":
            return jsonify({
                "status": "error",
                "code": "ALREADY_USED",
                "message": "Este cupón ya fue utilizado",
                "used_at": c["canjeado_en"],
                "used_by_device": device_id,
                "coupon": {
                    "id": c["codigo"],
                    "store": c["comercio"],
                    "title": c["titulo"],
                    "discount": f"{c['descuento']}%"
                }
            }), 409
        
        # 4. Cupón válido - marcarlo como canjeado
        db.execute(
            "UPDATE cupones SET estado='canjeado', canjeado_en=date('now') WHERE id = ?",
            (c["id"],)
        )
        db.commit()
        
        # Calcular precio con descuento
        precio_original = c["precio_normal"] if c["precio_normal"] else 0
        precio_con_descuento = int(precio_original * (1 - c["descuento"] / 100)) if precio_original else 0
        
        # 5. Respuesta exitosa
        return jsonify({
            "status": "success",
            "message": "Cupón validado correctamente",
            "coupon": {
                "id": c["codigo"],
                "store": c["comercio"],
                "discount": f"{c['descuento']}%",
                "original_price": precio_original,
                "discounted_price": precio_con_descuento,
                "title": c["titulo"],
                "city": c["ciudad"],
                "address": c["direccion"]
            },
            "validated_at": hoy()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error validando cupón: {e}")
        return jsonify({
            "status": "error",
            "code": "SERVER_ERROR",
            "message": "Error interno del servidor"
        }), 500





# ---------- Comercios ----------
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        f = request.form
        nombre, email = f.get("nombre", "").strip(), f.get("email", "").strip().lower()
        password, ciudad = f.get("password", ""), f.get("ciudad", "")
        direccion, telefono = f.get("direccion", "").strip(), solo_digitos(f.get("telefono"))

        if not nombre or not email or not direccion or ciudad not in CIUDADES:
            flash("Completá todos los campos obligatorios.", "error")
        elif len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
        else:
            db = get_db()
            try:
                cur = db.execute(
                    "INSERT INTO comercios (nombre, email, password_hash, telefono, ciudad, direccion)"
                    " VALUES (?,?,?,?,?,?)",
                    (nombre, email, generate_password_hash(password), telefono, ciudad, direccion))
                db.commit()
            except sqlite3.IntegrityError:
                flash("Ya existe una cuenta con ese correo.", "error")
            else:
                session.clear()
                session["comercio_id"] = cur.lastrowid
                flash("¡Cuenta creada! Ya podés publicar tu primera oferta.", "ok")
                return redirect(url_for("nueva_oferta"))
    return render_template("registro.html")


@app.route("/ingresar", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        c = get_db().execute("SELECT * FROM comercios WHERE email = ?", (email,)).fetchone()
        if c and check_password_hash(c["password_hash"], request.form.get("password", "")):
            session.clear()
            session["comercio_id"] = c["id"]
            destino = request.args.get("next", "")
            return redirect(destino if destino.startswith("/") and not destino.startswith("//")
                            else url_for("panel"))
        flash("Correo o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("index"))


@app.route("/panel")
@login_requerido
def panel():
    db = get_db()
    comercio = db.execute("SELECT * FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    
    es_admin = comercio["email"] == "admin@gmail.com"
    vista = request.args.get("vista", "ofertas")  # "ofertas" o "negocios"
    categoria = request.args.get("categoria", "").strip()
    ciudad = request.args.get("ciudad", "").strip()
    
    # Si es admin, mostrar TODAS las ofertas de todos los comercios
    if es_admin:
        sql = """SELECT o.*, c.nombre AS comercio_nombre,
                      (SELECT COUNT(*) FROM cupones WHERE oferta_id = o.id) AS reclamados,
                      (SELECT COUNT(*) FROM cupones WHERE oferta_id = o.id AND estado='canjeado') AS canjeados,
                      COALESCE(o.destacada, 0) AS destacada,
                      COALESCE(o.urgente, 0) AS urgente,
                      COALESCE(o.principal, 0) AS principal
               FROM ofertas o
               JOIN comercios c ON c.id = o.comercio_id"""
        params = []
        conditions = []
        
        # Filtrar por categoría si se especifica
        if categoria and categoria in CATEGORIAS:
            conditions.append("o.categoria = ?")
            params.append(categoria)
        
        # Filtrar por ciudad si se especifica
        if ciudad and ciudad in CIUDADES:
            conditions.append("o.ciudad = ?")
            params.append(ciudad)
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY o.id DESC"
        ofertas = [dict(row) for row in db.execute(sql, params).fetchall()]
    else:
        # Usuario normal: solo sus ofertas
        ofertas = [dict(row) for row in db.execute(
            """SELECT o.*,
                      (SELECT COUNT(*) FROM cupones WHERE oferta_id = o.id) AS reclamados,
                      (SELECT COUNT(*) FROM cupones WHERE oferta_id = o.id AND estado='canjeado') AS canjeados,
                      COALESCE(o.principal, 0) AS principal
               FROM ofertas o WHERE o.comercio_id = ? ORDER BY o.id DESC""",
            (session["comercio_id"],)).fetchall()]
    
    # Si es admin y vista es "negocios", cargar todos los negocios
    negocios = []
    if es_admin and vista == "negocios":
        negocios = db.execute(
            """SELECT c.*, 
                      (SELECT COUNT(*) FROM ofertas WHERE comercio_id = c.id) AS total_ofertas,
                      (SELECT COUNT(*) FROM ofertas WHERE comercio_id = c.id AND activa = 1) AS ofertas_activas
               FROM comercios c ORDER BY c.id DESC"""
        ).fetchall()
    
    return render_template("panel.html", comercio=comercio, ofertas=ofertas, negocios=negocios, 
                          hoy=hoy(), es_admin=es_admin, vista=vista)


@app.route("/panel/nueva", methods=["GET", "POST"])
@login_requerido
def nueva_oferta():
    db = get_db()
    comercio = db.execute("SELECT * FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    es_admin = comercio["email"] == "admin@gmail.com"
    
    # Si es admin, cargar todos los comercios
    todos_comercios = []
    if es_admin:
        todos_comercios = db.execute("SELECT id, nombre, ciudad FROM comercios ORDER BY ciudad, nombre").fetchall()
    
    if request.method == "POST":
        f = request.form
        titulo = f.get("titulo", "").strip()
        categoria, ciudad = f.get("categoria", ""), f.get("ciudad", "")
        direccion = f.get("direccion", "").strip()
        coordenadas = f.get("coordenadas", "").strip()
        whatsapp = solo_digitos(f.get("whatsapp", ""))
        descuento = a_entero(f.get("descuento"))
        cupos = a_entero(f.get("cupos"))
        precio = a_entero(f.get("precio_normal")) if f.get("precio_normal", "").strip() else None
        hasta = f.get("valido_hasta", "")
        
        # Si es admin, puede seleccionar el comercio
        comercio_id_seleccionado = a_entero(f.get("comercio_id")) if es_admin else session["comercio_id"]

        errores = []
        if not titulo:
            errores.append("Poné un título a la oferta.")
        if categoria not in CATEGORIAS or ciudad not in CIUDADES:
            errores.append("Elegí una categoría y una ciudad.")
        if not direccion:
            errores.append("Indicá la dirección del local.")
        if descuento is None or not 1 <= descuento <= 99:
            errores.append("El descuento debe estar entre 1% y 99%.")
        if cupos is None or cupos < 1:
            errores.append("Indicá cuántos cupones disponés (mínimo 1).")
        if hasta < hoy():
            errores.append("La fecha límite debe ser hoy o posterior.")
        if es_admin and not comercio_id_seleccionado:
            errores.append("Seleccioná un negocio para la oferta.")

        archivo = request.files.get("foto")
        foto = None
        if not errores and archivo and archivo.filename:
            foto = guardar_foto(archivo)
            if foto is None:
                errores.append("No pudimos leer la foto. Subí una imagen JPG, PNG o WebP.")

        if errores:
            for e in errores:
                flash(e, "error")
        else:
            db.execute(
                """INSERT INTO ofertas (comercio_id, titulo, descripcion, categoria, ciudad,
                                        direccion, coordenadas, whatsapp, precio_normal, descuento, valido_hasta, cupos, foto)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (comercio_id_seleccionado, titulo, f.get("descripcion", "").strip(), categoria,
                 ciudad, direccion, coordenadas if coordenadas else None, whatsapp if whatsapp else None, 
                 precio, descuento, hasta, cupos, foto))
            db.commit()
            flash("Oferta publicada. Ya la pueden ver en tu ciudad.", "ok")
            return redirect(url_for("panel"))
    por_defecto = (date.today() + timedelta(days=14)).isoformat()
    return render_template("nueva.html", comercio=comercio, hoy=hoy(), por_defecto=por_defecto, 
                          es_admin=es_admin, todos_comercios=todos_comercios)


@app.route("/panel/oferta/<int:oferta_id>/editar", methods=["GET", "POST"])
@login_requerido
def editar_oferta(oferta_id):
    db = get_db()
    comercio = db.execute("SELECT * FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    es_admin = comercio["email"] == "admin@gmail.com"
    
    # Admin puede editar cualquier oferta, comercio normal solo las suyas
    if es_admin:
        oferta = db.execute(
            """SELECT o.*, (SELECT COUNT(*) FROM cupones WHERE oferta_id = o.id) AS reclamados
               FROM ofertas o WHERE o.id = ?""", (oferta_id,)).fetchone()
        # Cargar todos los comercios con sus ciudades para el selector
        todos_comercios = db.execute("SELECT id, nombre, ciudad FROM comercios ORDER BY ciudad, nombre").fetchall()
    else:
        oferta = db.execute(
            """SELECT o.*, (SELECT COUNT(*) FROM cupones WHERE oferta_id = o.id) AS reclamados
               FROM ofertas o WHERE o.id = ? AND o.comercio_id = ?""",
            (oferta_id, session["comercio_id"])).fetchone()
        todos_comercios = []
    
    if not oferta:
        abort(404)
    
    if request.method == "POST":
        f = request.form
        titulo = f.get("titulo", "").strip()
        categoria, ciudad = f.get("categoria", ""), f.get("ciudad", "")
        direccion = f.get("direccion", "").strip()
        coordenadas = f.get("coordenadas", "").strip()
        whatsapp = solo_digitos(f.get("whatsapp", ""))
        descuento = a_entero(f.get("descuento"))
        cupos = a_entero(f.get("cupos"))
        precio = a_entero(f.get("precio_normal")) if f.get("precio_normal", "").strip() else None
        hasta = f.get("valido_hasta", "")
        
        # Si es admin, puede cambiar el comercio asignado
        comercio_id_nuevo = a_entero(f.get("comercio_id")) if es_admin else session["comercio_id"]

        errores = []
        if not titulo:
            errores.append("Poné un título a la oferta.")
        if categoria not in CATEGORIAS or ciudad not in CIUDADES:
            errores.append("Elegí una categoría y una ciudad.")
        if not direccion:
            errores.append("Indicá la dirección del local.")
        if descuento is None or not 1 <= descuento <= 99:
            errores.append("El descuento debe estar entre 1% y 99%.")
        if cupos is None or cupos < oferta["reclamados"]:
            errores.append(f"Los cupones disponibles no pueden ser menos que los ya reclamados ({oferta['reclamados']}).")
        if hasta < hoy():
            errores.append("La fecha límite debe ser hoy o posterior.")
        if es_admin and not comercio_id_nuevo:
            errores.append("Seleccioná un comercio para la oferta.")

        # Procesar nueva foto si se subió
        archivo = request.files.get("foto")
        nueva_foto = None
        if not errores and archivo and archivo.filename:
            nueva_foto = guardar_foto(archivo)
            if nueva_foto is None:
                errores.append("No pudimos leer la foto. Subí una imagen JPG, PNG o WebP.")

        if errores:
            for e in errores:
                flash(e, "error")
        else:
            # Actualizar la oferta
            sql = """UPDATE ofertas SET titulo=?, descripcion=?, categoria=?, ciudad=?,
                     direccion=?, coordenadas=?, whatsapp=?, precio_normal=?, descuento=?, valido_hasta=?, cupos=?"""
            params = [titulo, f.get("descripcion", "").strip(), categoria, ciudad,
                     direccion, coordenadas if coordenadas else None, whatsapp if whatsapp else None, 
                     precio, descuento, hasta, cupos]
            
            # Si es admin, actualizar también el comercio_id
            if es_admin:
                sql += ", comercio_id=?"
                params.append(comercio_id_nuevo)
            
            # Si hay nueva foto, actualizarla
            if nueva_foto:
                sql += ", foto=?"
                params.append(nueva_foto)
                # Borrar la foto anterior si existía
                if oferta["foto"]:
                    borrar_foto(oferta["foto"])
            
            sql += " WHERE id=?"
            params.append(oferta_id)
            
            db.execute(sql, params)
            db.commit()
            flash("Oferta actualizada correctamente.", "ok")
            return redirect(url_for("panel"))
    
    return render_template("editar.html", comercio=comercio, oferta=oferta, hoy=hoy(), 
                          es_admin=es_admin, todos_comercios=todos_comercios if es_admin else [])


@app.route("/panel/oferta/<int:oferta_id>/foto", methods=["POST"])
@login_requerido
def cambiar_foto(oferta_id):
    db = get_db()
    comercio = db.execute("SELECT email FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    es_admin = comercio["email"] == "admin@gmail.com"
    
    # Admin puede cambiar cualquier foto, comercio normal solo las suyas
    if es_admin:
        o = db.execute("SELECT foto FROM ofertas WHERE id = ?", (oferta_id,)).fetchone()
    else:
        o = db.execute("SELECT foto FROM ofertas WHERE id = ? AND comercio_id = ?",
                       (oferta_id, session["comercio_id"])).fetchone()
    
    if not o:
        abort(404)
    archivo = request.files.get("foto")
    if not archivo or not archivo.filename:
        flash("Elegí una foto para subir.", "error")
    else:
        nueva = guardar_foto(archivo)
        if nueva is None:
            flash("No pudimos leer la foto. Subí una imagen JPG, PNG o WebP.", "error")
        else:
            db.execute("UPDATE ofertas SET foto = ? WHERE id = ?", (nueva, oferta_id))
            db.commit()
            if o["foto"]:
                borrar_foto(o["foto"])
            flash("Foto actualizada.", "ok")
    return redirect(url_for("panel"))


@app.route("/panel/oferta/<int:oferta_id>/alternar", methods=["POST"])
@login_requerido
def alternar_oferta(oferta_id):
    db = get_db()
    comercio = db.execute("SELECT email FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    es_admin = comercio["email"] == "admin@gmail.com"
    
    # Admin puede alternar cualquier oferta, comercio normal solo las suyas
    if es_admin:
        db.execute("UPDATE ofertas SET activa = 1 - activa WHERE id = ?", (oferta_id,))
    else:
        db.execute("UPDATE ofertas SET activa = 1 - activa WHERE id = ? AND comercio_id = ?",
                   (oferta_id, session["comercio_id"]))
    db.commit()
    return redirect(url_for("panel"))


@app.route("/panel/oferta/<int:oferta_id>/destacar", methods=["POST"])
@login_requerido
def marcar_destacada(oferta_id):
    db = get_db()
    comercio = db.execute("SELECT email FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    es_admin = comercio["email"] == "admin@gmail.com"
    
    if not es_admin:
        abort(403)
    
    # Obtener la ciudad de esta oferta
    oferta = db.execute("SELECT destacada, ciudad FROM ofertas WHERE id = ?", (oferta_id,)).fetchone()
    
    if oferta["destacada"] == 1:
        # Si ya está destacada, solo desmarcala
        db.execute("UPDATE ofertas SET destacada = 0 WHERE id = ?", (oferta_id,))
        flash("Oferta desmarcada como destacada.", "ok")
    else:
        # Desmarcar TODAS las destacadas de la misma ciudad
        db.execute("UPDATE ofertas SET destacada = 0 WHERE ciudad = ?", (oferta["ciudad"],))
        # Marcar solo esta como destacada
        db.execute("UPDATE ofertas SET destacada = 1 WHERE id = ?", (oferta_id,))
        flash(f"Oferta marcada como destacada. Las demás destacadas de {oferta['ciudad']} fueron desmarcadas.", "ok")
    
    db.commit()
    return redirect(url_for("panel"))


@app.route("/panel/oferta/<int:oferta_id>/urgentar", methods=["POST"])
@login_requerido
def marcar_urgente(oferta_id):
    db = get_db()
    comercio = db.execute("SELECT email FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    es_admin = comercio["email"] == "admin@gmail.com"
    
    if not es_admin:
        abort(403)
    
    # Obtener el estado actual
    oferta = db.execute("SELECT urgente FROM ofertas WHERE id = ?", (oferta_id,)).fetchone()
    nuevo_estado = 1 if oferta["urgente"] == 0 else 0
    
    db.execute("UPDATE ofertas SET urgente = ? WHERE id = ?", (nuevo_estado, oferta_id))
    db.commit()
    
    mensaje = "Oferta marcada como urgente." if nuevo_estado == 1 else "Oferta desmarcada como urgente."
    flash(mensaje, "ok")
    return redirect(url_for("panel"))


@app.route("/panel/oferta/<int:oferta_id>/marcar-principal", methods=["POST"])
@login_requerido
def marcar_principal(oferta_id):
    db = get_db()
    comercio = db.execute("SELECT email FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    
    # Obtener la oferta y su comercio
    oferta = db.execute("SELECT comercio_id, principal FROM ofertas WHERE id = ?", (oferta_id,)).fetchone()
    
    if not oferta:
        abort(404)
    
    # Verificar permisos
    es_admin = comercio["email"] == "admin@gmail.com"
    if not es_admin and oferta["comercio_id"] != session["comercio_id"]:
        abort(403)
    
    if oferta["principal"] == 1:
        # Si ya es principal, desmarcala
        db.execute("UPDATE ofertas SET principal = 0 WHERE id = ?", (oferta_id,))
        flash("Oferta desmarcada como principal.", "ok")
    else:
        # Desmarcar TODAS las ofertas principales del mismo negocio
        db.execute("UPDATE ofertas SET principal = 0 WHERE comercio_id = ?", (oferta["comercio_id"],))
        # Marcar solo esta como principal
        db.execute("UPDATE ofertas SET principal = 1 WHERE id = ?", (oferta_id,))
        flash("Esta oferta ahora aparecerá en la página principal. Las demás ofertas de este negocio estarán en su página.", "exito")
    
    db.commit()
    return redirect(url_for("panel"))


@app.route("/panel/negocio/nuevo", methods=["GET", "POST"])
@login_requerido
def nuevo_negocio():
    db = get_db()
    comercio = db.execute("SELECT email FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    
    if comercio["email"] != "admin@gmail.com":
        abort(403)
    
    if request.method == "POST":
        f = request.form
        nombre = f.get("nombre", "").strip()
        email = f.get("email", "").strip().lower()
        password = f.get("password", "")
        telefono = solo_digitos(f.get("telefono"))
        ciudad = f.get("ciudad", "")
        direccion = f.get("direccion", "").strip()
        
        errores = []
        if not nombre or not email or not direccion:
            errores.append("Completá todos los campos obligatorios.")
        if ciudad not in CIUDADES:
            errores.append("Elegí una ciudad válida.")
        if len(password) < 6:
            errores.append("La contraseña debe tener al menos 6 caracteres.")
        
        if errores:
            for e in errores:
                flash(e, "error")
        else:
            try:
                db.execute(
                    "INSERT INTO comercios (nombre, email, password_hash, telefono, ciudad, direccion) VALUES (?,?,?,?,?,?)",
                    (nombre, email, generate_password_hash(password), telefono, ciudad, direccion))
                db.commit()
                flash(f"Negocio '{nombre}' creado exitosamente.", "exito")
                return redirect(url_for("panel", vista="negocios"))
            except sqlite3.IntegrityError:
                flash("Ya existe un negocio con ese correo.", "error")
    
    return render_template("negocio_form.html", comercio=comercio, negocio=None, titulo="Crear nuevo negocio")


@app.route("/panel/negocio/<int:negocio_id>/editar", methods=["GET", "POST"])
@login_requerido
def editar_negocio(negocio_id):
    db = get_db()
    comercio = db.execute("SELECT email FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    
    if comercio["email"] != "admin@gmail.com":
        abort(403)
    
    negocio = db.execute("SELECT * FROM comercios WHERE id = ?", (negocio_id,)).fetchone()
    if not negocio:
        abort(404)
    
    if request.method == "POST":
        f = request.form
        nombre = f.get("nombre", "").strip()
        email = f.get("email", "").strip().lower()
        password = f.get("password", "")
        telefono = solo_digitos(f.get("telefono"))
        ciudad = f.get("ciudad", "")
        direccion = f.get("direccion", "").strip()
        
        errores = []
        if not nombre or not email or not direccion:
            errores.append("Completá todos los campos obligatorios.")
        if ciudad not in CIUDADES:
            errores.append("Elegí una ciudad válida.")
        
        if errores:
            for e in errores:
                flash(e, "error")
        else:
            try:
                # Si hay nueva contraseña, actualizarla
                if password and len(password) >= 6:
                    db.execute(
                        "UPDATE comercios SET nombre=?, email=?, password_hash=?, telefono=?, ciudad=?, direccion=? WHERE id=?",
                        (nombre, email, generate_password_hash(password), telefono, ciudad, direccion, negocio_id))
                else:
                    # Mantener la contraseña actual
                    db.execute(
                        "UPDATE comercios SET nombre=?, email=?, telefono=?, ciudad=?, direccion=? WHERE id=?",
                        (nombre, email, telefono, ciudad, direccion, negocio_id))
                db.commit()
                flash(f"Negocio '{nombre}' actualizado exitosamente.", "exito")
                return redirect(url_for("panel", vista="negocios"))
            except sqlite3.IntegrityError:
                flash("Ya existe un negocio con ese correo.", "error")
    
    return render_template("negocio_form.html", comercio=comercio, negocio=negocio, titulo="Editar negocio")


@app.route("/panel/negocio/<int:negocio_id>/eliminar", methods=["POST"])
@login_requerido
def eliminar_negocio(negocio_id):
    db = get_db()
    comercio = db.execute("SELECT email FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    
    if comercio["email"] != "admin@gmail.com":
        abort(403)
    
    # No permitir eliminar al admin
    negocio = db.execute("SELECT email FROM comercios WHERE id = ?", (negocio_id,)).fetchone()
    if negocio and negocio["email"] == "admin@gmail.com":
        flash("No se puede eliminar la cuenta de administrador.", "error")
        return redirect(url_for("panel", vista="negocios"))
    
    # Verificar si tiene ofertas
    ofertas = db.execute("SELECT COUNT(*) as total FROM ofertas WHERE comercio_id = ?", (negocio_id,)).fetchone()
    if ofertas["total"] > 0:
        flash(f"No se puede eliminar el negocio porque tiene {ofertas['total']} ofertas asociadas. Eliminá las ofertas primero.", "error")
    else:
        db.execute("DELETE FROM comercios WHERE id = ?", (negocio_id,))
        db.commit()
        flash("Negocio eliminado exitosamente.", "exito")
    
    return redirect(url_for("panel", vista="negocios"))


@app.route("/panel/canjear", methods=["POST"])
@login_requerido
def canjear():
    db = get_db()
    comercio = db.execute("SELECT email FROM comercios WHERE id = ?",
                          (session["comercio_id"],)).fetchone()
    es_admin = comercio["email"] == "admin@gmail.com"
    
    codigo = re.sub(r"[^A-Za-z0-9]", "", request.form.get("codigo", "")).upper()
    
    # Admin puede canjear cupones de cualquier comercio
    if es_admin:
        c = db.execute(
            """SELECT cu.*, o.titulo, o.descuento, o.valido_hasta
               FROM cupones cu JOIN ofertas o ON o.id = cu.oferta_id
               WHERE cu.codigo = ?""", (codigo,)).fetchone()
    else:
        c = db.execute(
            """SELECT cu.*, o.titulo, o.descuento, o.valido_hasta
               FROM cupones cu JOIN ofertas o ON o.id = cu.oferta_id
               WHERE cu.codigo = ? AND o.comercio_id = ?""",
            (codigo, session["comercio_id"])).fetchone()

    if not c:
        flash(f"❌ El código {codigo or '—'} no existe en tu comercio.", "error")
    elif c["estado"] == "canjeado":
        flash(f"⚠️ El cupón {codigo} ya fue usado el {formato_fecha(c['canjeado_en'])}.", "error")
    elif c["valido_hasta"] < hoy():
        flash(f"⏰ El cupón {codigo} venció el {formato_fecha(c['valido_hasta'])}.", "error")
    else:
        db.execute("UPDATE cupones SET estado='canjeado', canjeado_en=date('now') WHERE id = ?",
                   (c["id"],))
        db.commit()
        # Mensaje de éxito más destacado
        flash(f"🎉 ¡CUPÓN CANJEADO! Aplicá {c['descuento']}% de descuento en «{c['titulo']}» a {c['nombre']}.", "exito")
    return redirect(url_for("panel"))


@app.errorhandler(404)
def no_encontrado(_e):
    return render_template("404.html"), 404


# ---------- Datos de ejemplo: flask --app app seed ----------
COMERCIOS_DEMO = [
    # (nombre, email, telefono, ciudad, direccion)
    ("Carnicería Don Pedro", "demo@cuponpy.com", "0981123456", "María Auxiliadora", "Ruta 6, frente a la plaza"),
    ("Lomitería El Rey", "lomiteria@cuponpy.com", "0982222333", "María Auxiliadora", "Calle Palma esq. 14 de Mayo"),
    ("Pizzería Nonna Rosa", "pizzeria@cuponpy.com", "0983444555", "María Auxiliadora", "Av. Independencia 450"),
    ("Panadería La Espiga", "panaderia@cuponpy.com", "0984666777", "María Auxiliadora", "Ruta 6 km 2"),
    ("Farmacia Salud Total", "farmacia@cuponpy.com", "0985888999", "María Auxiliadora", "Av. Mcal. López 120"),
    ("Ferretería El Tornillo", "ferreteria@cuponpy.com", "0986111222", "María Auxiliadora", "Calle Comercio 88"),
    ("Boutique Ñandutí", "boutique@cuponpy.com", "0987333444", "María Auxiliadora", "Centro comercial, local 4"),
    ("Estilo Peluquería", "peluqueria@cuponpy.com", "0981555666", "María Auxiliadora", "Calle 15 de Agosto 230"),
    ("Súper Los Pinos", "super@cuponpy.com", "0982777888", "María Auxiliadora", "Av. Principal 900"),
    ("Heladería Frescura", "helados@cuponpy.com", "0983999000", "María Auxiliadora", "Costanera, junto a la plaza"),
    ("Panadería Santa Rita", "panaderia.sr@cuponpy.com", "0984123123", "Santa Rita", "Av. Principal 123, centro"),
]
# (email, titulo, descripcion, categoria, precio_normal, descuento, dias_vigencia, cupos)
OFERTAS_DEMO = [
    ("demo@cuponpy.com", "30% en asado de tira", "Asado de tira fresco, corte del día. Mostrá el cupón en caja.", "Carnicería", 42000, 30, 15, 50),
    ("demo@cuponpy.com", "Combo parrillero: chorizo + costilla", "1 kg de chorizo y 1 kg de costilla para el fin de semana.", "Carnicería", 78000, 20, 6, 40),
    ("lomiteria@cuponpy.com", "2x1 en lomitos completos", "Pedí un lomito y llevate otro gratis, de lunes a jueves.", "Restaurante", 30000, 50, 4, 30),
    ("pizzeria@cuponpy.com", "25% en pizza grande", "Cualquier sabor, para comer en el local o llevar.", "Restaurante", 55000, 25, 10, 60),
    ("panaderia@cuponpy.com", "Media docena de chipa a mitad de precio", "Chipa recién salida del horno, todos los días hasta agotar.", "Panadería", 20000, 50, 3, 25),
    ("panaderia@cuponpy.com", "20% en pan y facturas", "Descuento en toda la panadería después de las 17:00.", "Panadería", None, 20, 20, 100),
    ("farmacia@cuponpy.com", "15% en vitaminas y cuidado personal", "Válido en suplementos, protectores solares y cremas.", "Farmacia", None, 15, 12, 80),
    ("ferreteria@cuponpy.com", "10% en herramientas manuales", "Martillos, destornilladores, llaves y más.", "Ferretería", None, 10, 25, 60),
    ("boutique@cuponpy.com", "40% en remeras de la temporada", "Últimas unidades de la colección. Talles S al XL.", "Ropa y calzado", 90000, 40, 8, 35),
    ("peluqueria@cuponpy.com", "30% en corte + brushing", "Reservá tu turno por WhatsApp y mostrá el cupón al llegar.", "Belleza", 80000, 30, 14, 20),
    ("super@cuponpy.com", "12% en lácteos y verduras", "Solo viernes y sábados, en góndola y verdulería.", "Supermercado", None, 12, 5, 120),
    ("helados@cuponpy.com", "Medio kilo de helado a 20% menos", "Elegí hasta 3 sabores. Ideal para el calor de la tarde.", "Café y helados", 35000, 20, 9, 50),
    ("panaderia.sr@cuponpy.com", "20% en pan y facturas", "Descuento en toda la panadería después de las 17:00.", "Panadería", None, 20, 15, 100),
]


# Nombre de archivo esperado en demo_fotos/ para cada oferta de ejemplo (jpg, png o webp)
FOTOS_DEMO = ["asado", "combo-parrillero", "lomito", "pizza", "chipa", "pan", "vitaminas",
              "herramientas", "remeras", "peluqueria", "verduras", "helado", "pan-santa-rita"]


def foto_demo(slug):
    for ext in ("jpg", "jpeg", "png", "webp"):
        ruta = os.path.join(DEMO_FOTOS_DIR, f"{slug}.{ext}")
        if os.path.exists(ruta):
            return guardar_foto(ruta)
    return None


@app.cli.command("seed")
def seed():
    """Agrega comercios y ofertas de ejemplo (no duplica) y les pone la foto de demo_fotos/ si existe."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    ids, nuevos, con_foto = {}, 0, 0
    for nombre, email, tel, ciudad, direccion in COMERCIOS_DEMO:
        fila = db.execute("SELECT id FROM comercios WHERE email = ?", (email,)).fetchone()
        if fila:
            ids[email] = fila["id"]
        else:
            cur = db.execute(
                "INSERT INTO comercios (nombre,email,password_hash,telefono,ciudad,direccion) VALUES (?,?,?,?,?,?)",
                (nombre, email, generate_password_hash("demo1234"), tel, ciudad, direccion))
            ids[email] = cur.lastrowid
    datos = {c[1]: c for c in COMERCIOS_DEMO}
    for slug, (email, titulo, desc, cat, precio, dto, dias, cupos) in zip(FOTOS_DEMO, OFERTAS_DEMO):
        _, _, _, ciudad, direccion = datos[email]
        existente = db.execute("SELECT id, foto FROM ofertas WHERE comercio_id=? AND titulo=?",
                               (ids[email], titulo)).fetchone()
        if existente:
            oferta_id, foto = existente["id"], existente["foto"]
        else:
            hasta = (date.today() + timedelta(days=dias)).isoformat()
            cur = db.execute(
                """INSERT INTO ofertas (comercio_id,titulo,descripcion,categoria,ciudad,direccion,
                                        precio_normal,descuento,valido_hasta,cupos)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (ids[email], titulo, desc, cat, ciudad, direccion, precio, dto, hasta, cupos))
            oferta_id, foto, nuevos = cur.lastrowid, None, nuevos + 1
        if not foto:
            nombre_foto = foto_demo(slug)
            if nombre_foto:
                db.execute("UPDATE ofertas SET foto=? WHERE id=?", (nombre_foto, oferta_id))
                con_foto += 1
    db.commit()
    print(f"Listo: {nuevos} ofertas nuevas, {con_foto} fotos cargadas desde demo_fotos/.")
    print("Ingresá como comercio con demo@cuponpy.com / demo1234")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
