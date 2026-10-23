# CuponPY

Ofertas y descuentos por ciudad en Paraguay, hechas con Flask + SQLite.

## Cómo funciona
1. El cliente elige su ciudad (ej. María Auxiliadora) y ve las ofertas.
2. Reclama el cupón con su nombre y celular → recibe un código de 6 caracteres.
3. Va al local y muestra el código.
4. El comercio lo ingresa en su panel → se valida y queda marcado como canjeado (no se puede usar dos veces).

## Instalar y correr
```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt   # instala Flask y Pillow
flask --app app seed            # opcional: carga datos de ejemplo
flask --app app run --debug
```
Abrí http://127.0.0.1:5000

Comercio de ejemplo: `demo@cuponpy.com` / `demo1234`

## Fotos
- Cada comercio sube la foto de su oferta al crear la oferta, o después desde **Mi panel → Agregar/Cambiar foto** (desde el celular abre la cámara o la galería).
- La app corrige la rotación, quita la ubicación (EXIF) y genera dos tamaños para que cargue rápido con datos móviles. Se guardan en `static/uploads/`.
- Las ofertas sin foto muestran un emoji de su rubro.
- Para las ofertas de ejemplo: poné fotos en `demo_fotos/` (ver `demo_fotos/LEEME.txt`) y corré `flask --app app seed`.
- Al publicar: hacé copia de seguridad de `static/uploads/` junto con `ofertas.db`.

## Antes de publicarlo en internet
- Definí `SECRET_KEY` como variable de entorno (un valor largo y aleatorio).
- Corré con gunicorn (`gunicorn app:app`) detrás de HTTPS, sin `--debug`.
- Considerá agregar protección CSRF (Flask-WTF) y límite de intentos en el login.
