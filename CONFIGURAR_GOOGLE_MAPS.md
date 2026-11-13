# 🗺️ Cómo Configurar Google Maps para el Mapa de Ofertas

## 🎯 Objetivo

Mostrar todas las ofertas con coordenadas en un mapa interactivo de Google Maps.

---

## 📋 Paso a Paso

### 1️⃣ **Obtener una API Key de Google Maps** (GRATIS hasta 28,000 cargas de mapa/mes)

#### A. Crear cuenta en Google Cloud

1. Ve a: https://console.cloud.google.com
2. Inicia sesión con tu cuenta de Google
3. Acepta los términos de servicio

#### B. Crear un proyecto

1. En la parte superior, haz clic en el selector de proyecto
2. Clic en **"Nuevo Proyecto"**
3. Nombre del proyecto: `ZupponPy`
4. Haz clic en **"Crear"**
5. Espera unos segundos hasta que se cree

#### C. Habilitar facturación (Requerido pero NO cobran hasta que pases el límite gratis)

1. En el menú lateral, ve a **"Facturación"**
2. Haz clic en **"Vincular una cuenta de facturación"**
3. Clic en **"Crear cuenta de facturación"**
4. Completa los datos:
   - Nombre de cuenta
   - País: Paraguay
   - Moneda: USD
5. Agrega método de pago (tarjeta de crédito/débito)
   - **NOTA:** Google da $200 USD de crédito gratis cada mes
   - NO te cobrarán a menos que uses más de eso
   - Para un sitio como ZupponPy, nunca llegarás al límite

#### D. Habilitar Google Maps JavaScript API

1. En el menú lateral, ve a **"APIs y servicios"** → **"Biblioteca"**
2. Busca: `Maps JavaScript API`
3. Haz clic en **"Maps JavaScript API"**
4. Haz clic en **"HABILITAR"**
5. Espera unos segundos

#### E. Crear credenciales (API Key)

1. En el menú lateral, ve a **"APIs y servicios"** → **"Credenciales"**
2. Haz clic en **"+ CREAR CREDENCIALES"**
3. Selecciona **"Clave de API"**
4. Se generará una clave como: `AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567`
5. **COPIA esta clave** (la necesitarás en el siguiente paso)

#### F. Restringir la API Key (IMPORTANTE para seguridad)

1. En la ventana de la clave creada, haz clic en **"Restringir clave"**
2. En **"Restricciones de aplicación"**, selecciona:
   - ✅ **"Referentes HTTP (sitios web)"**
3. En **"Restricciones del sitio web"**, agrega:
   ```
   https://zuppon.es/*
   http://localhost:5000/*
   http://127.0.0.1:5000/*
   ```
4. En **"Restricciones de API"**, selecciona:
   - ✅ **"Restringir clave"**
   - Selecciona solo: **"Maps JavaScript API"**
5. Haz clic en **"GUARDAR"**

---

### 2️⃣ **Agregar la API Key a ZupponPy**

#### Opción A: En el archivo HTML (Desarrollo)

1. Abre el archivo: `templates/mapa.html`

2. Busca esta línea (está casi al final):
   ```html
   src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&callback=initMap&libraries=places&language=es&region=PY">
   ```

3. Reemplaza `YOUR_API_KEY` con tu clave real:
   ```html
   src="https://maps.googleapis.com/maps/api/js?key=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567&callback=initMap&libraries=places&language=es&region=PY">
   ```

4. Guarda el archivo

#### Opción B: Variable de entorno (Producción - MÁS SEGURO)

1. Crea una variable de entorno:
   ```bash
   export GOOGLE_MAPS_API_KEY="AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567"
   ```

2. En `app.py`, agrega al inicio:
   ```python
   GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
   ```

3. Pasa la clave al template en la ruta del mapa:
   ```python
   return render_template("mapa.html", ofertas_json=ofertas_json, 
                          ciudad=ciudad, maps_api_key=GOOGLE_MAPS_API_KEY)
   ```

4. En `templates/mapa.html`, usa la variable:
   ```html
   src="https://maps.googleapis.com/maps/api/js?key={{ maps_api_key }}&callback=initMap&libraries=places&language=es&region=PY">
   ```

---

### 3️⃣ **Agregar Coordenadas a las Ofertas**

Para que las ofertas aparezcan en el mapa, necesitan coordenadas.

#### Opción A: Manual (en el formulario de ofertas)

Ya está implementado. Cuando creas/editas una oferta:
1. Campo **"Coordenadas"** en el formulario
2. Formato: `-25.2637,-57.5759` (latitud,longitud)
3. Opcional pero recomendado

#### Opción B: Obtener coordenadas automáticamente

**Cómo obtener coordenadas de una dirección:**

1. **Google Maps:**
   - Ve a https://maps.google.com
   - Busca la dirección del negocio
   - Haz clic derecho en el marcador
   - Selecciona las coordenadas (primer elemento)
   - Formato: `-25.2637, -57.5759`

2. **Desde el código (futuro):**
   - Usar Geocoding API de Google
   - Convertir dirección → coordenadas automáticamente

---

### 4️⃣ **Probar el Mapa**

1. **Reinicia el servidor:**
   ```bash
   python app.py
   ```

2. **Accede al mapa:**
   ```
   http://127.0.0.1:5000/mapa
   ```

3. **Deberías ver:**
   - Mapa de Paraguay
   - Marcadores azules en las ofertas con coordenadas
   - Al hacer clic en un marcador: InfoWindow con detalles

---

## 🎨 Características del Mapa

### Funcionalidades:

✅ **Mapa interactivo de Google Maps**
- Zoom
- Arrastre
- Street View
- Vista satelital

✅ **Marcadores personalizados**
- Color azul (marca ZupponPy)
- Animación al cargar
- Círculos con borde blanco

✅ **InfoWindow al hacer clic**
- Título de la oferta
- Nombre del comercio
- Descuento destacado
- Categoría
- Dirección completa
- Cupones disponibles
- Días restantes
- Botón "Ver oferta"
- Botón "Ver negocio"

✅ **Filtro por ciudad**
- Selector en el header
- Muestra solo ofertas de esa ciudad
- Ajusta zoom automáticamente

✅ **Botón "Ver mapa" en header**
- Accesible desde cualquier página
- Icono de ubicación
- Responsive

✅ **Auto-ajuste de zoom**
- Muestra todos los marcadores
- Zoom inteligente según cantidad

---

## 💰 Costos (Muy Bajo o Gratis)

### Límite Gratis de Google:

- **$200 USD de crédito mensual gratis**
- **28,000 cargas de mapa gratis por mes**
- Después: $7 USD por cada 1,000 cargas adicionales

### Para ZupponPy:

Si tienes **1,000 visitantes al día** que ven el mapa:
- 30,000 vistas/mes
- Costo: ~$0-$14 USD/mes
- **Probablemente $0** porque la mayoría no abrirá el mapa

**Recomendación:** Monitorea el uso en Google Cloud Console.

---

## 🔒 Seguridad

### ✅ Ya Configurado:

1. **Restricción por dominio:**
   - Solo funciona en zuppon.es y localhost
   - Nadie puede usar tu clave en otro sitio

2. **Restricción por API:**
   - Solo puede usar Maps JavaScript API
   - No puede usar otras APIs de Google

3. **Clave no visible en código fuente:**
   - (Si usas variable de entorno)

### ⚠️ NUNCA hagas esto:

- ❌ Subir la API Key a GitHub/GitLab público
- ❌ Compartir la clave en foros/chats
- ❌ Dejar la clave sin restricciones
- ❌ Usar la misma clave en múltiples proyectos

---

## 🐛 Solución de Problemas

### Problema 1: "This page can't load Google Maps correctly"

**Causa:** API Key inválida o mal configurada

**Solución:**
1. Verifica que copiaste la clave completa
2. Verifica que habilitaste Maps JavaScript API
3. Verifica que el dominio está en las restricciones
4. Espera 5 minutos (a veces tarda en activarse)

---

### Problema 2: "Google Maps Platform rejected your request"

**Causa:** Facturación no configurada

**Solución:**
1. Ve a Google Cloud Console
2. Configura cuenta de facturación
3. Vincula al proyecto
4. Espera 5 minutos

---

### Problema 3: Mapa se ve gris/en blanco

**Causa:** Coordenadas inválidas o fuera de rango

**Solución:**
1. Verifica formato: `-25.2637,-57.5759`
2. Latitud: entre -90 y 90
3. Longitud: entre -180 y 180
4. Sin espacios extra
5. Coma como separador

---

### Problema 4: No aparecen marcadores

**Causa:** Ofertas sin coordenadas

**Solución:**
1. Ve a Panel → Editar oferta
2. Agrega coordenadas en el campo
3. Formato: `-25.2637,-57.5759`
4. Guarda la oferta
5. Recarga el mapa

---

### Problema 5: InfoWindow no se cierra

**Causa:** Error de JavaScript

**Solución:**
1. Abre consola del navegador (F12)
2. Busca errores
3. Verifica que el código JavaScript esté completo
4. Recarga página (Ctrl+F5)

---

## 📊 Monitoreo de Uso

### Ver estadísticas en Google Cloud:

1. Ve a: https://console.cloud.google.com
2. Selecciona tu proyecto
3. Menú → **"APIs y servicios"** → **"Panel"**
4. Verás:
   - Solicitudes por día
   - Errores
   - Cuota restante
   - Costo estimado

### Alertas de cuota:

1. En Google Cloud Console
2. **"Facturación"** → **"Presupuestos y alertas"**
3. Crear alerta cuando llegues a $10 USD/mes
4. Recibirás email si te acercas al límite

---

## 🎯 Próximas Mejoras (Opcional)

### 1. Geocodificación automática
- Convertir dirección → coordenadas al guardar oferta
- Usar Geocoding API de Google

### 2. Rutas
- Botón "Cómo llegar"
- Abre Google Maps con direcciones

### 3. Cluster de marcadores
- Agrupar marcadores cercanos
- Mejor performance con muchas ofertas

### 4. Búsqueda de ubicación
- "Ofertas cerca de mí"
- Usar Geolocation API

### 5. Filtros avanzados
- Por categoría
- Por descuento
- Por distancia

---

## ✅ Checklist de Configuración

- [ ] Cuenta de Google Cloud creada
- [ ] Proyecto ZupponPy creado
- [ ] Facturación configurada (con $200 gratis)
- [ ] Maps JavaScript API habilitada
- [ ] API Key generada
- [ ] API Key restringida (dominios + API)
- [ ] API Key agregada en mapa.html
- [ ] Servidor reiniciado
- [ ] Mapa probado en http://localhost:5000/mapa
- [ ] Coordenadas agregadas a ofertas
- [ ] Marcadores visibles en el mapa
- [ ] InfoWindow funcionando
- [ ] Filtro por ciudad funcionando

---

## 🎉 ¡Listo!

Ahora tienes un **mapa interactivo** donde los usuarios pueden:
- 🗺️ Ver todas las ofertas geográficamente
- 📍 Encontrar ofertas cerca de ellos
- 🔍 Explorar ofertas por zona
- 📱 Ir directo a reclamar cupones

**El mapa hace que ZupponPy sea mucho más útil y moderno.** 🚀

---

**Actualizado:** Noviembre 2026  
**Google Maps API:** v3  
**Costo estimado:** $0-$14 USD/mes
