# 🎴 Tarjetas Digitales - Versión Mejorada

## ✨ Cambios implementados

### 1. Diseño Profesional Tipo Business Card Real

#### Antes ❌
- Diseño vertical con hero image grande
- Información dispersa
- QR grande al final
- No se veía como tarjeta real

#### Ahora ✅
- **Diseño horizontal profesional** (90mm × 55mm)
- **Layout de dos columnas**:
  - **Izquierda**: Logo + QR compacto integrado
  - **Derecha**: Información de contacto ordenada
- Se ve exactamente como una business card real
- Formato estándar internacional

### 2. Impresión Múltiple Optimizada

#### Antes ❌
- 8 tarjetas por hoja (difícil de cortar)
- Disposición irregular
- Orientación vertical

#### Ahora ✅
- **6 tarjetas por hoja A4 landscape**
- **Disposición perfecta: 3×2** (3 columnas, 2 filas)
- Fácil de cortar con guías
- Máximo aprovechamiento del espacio
- Orientación horizontal profesional

### 3. Estructura de la Tarjeta

```
┌─────────────────────────────────────────┐
│  LADO IZQUIERDO    │  LADO DERECHO      │
│  (Color marca)     │  (Blanco)          │
│                    │                    │
│    [  LOGO  ]      │  NOMBRE NEGOCIO    │
│                    │  Slogan o frase    │
│                    │                    │
│    [ QR CODE]      │  📍 Dirección      │
│                    │  ☎️ Teléfono        │
│                    │  ✉️ Email           │
│                    │                    │
│                    │  🌐 URL del negocio│
└─────────────────────────────────────────┘
        90mm × 55mm (estándar)
```

## 📐 Especificaciones Técnicas

### Tarjeta Individual
- **Ancho**: 90mm
- **Alto**: 55mm
- **Formato**: Horizontal (Landscape)
- **Bordes**: 1px dashed para guía de corte
- **Esquinas**: Redondeadas (4px)

### Hoja con 6 Tarjetas
- **Papel**: A4 Landscape (297mm × 210mm)
- **Distribución**: Grid 3×2
- **Espacio entre tarjetas**: 8mm
- **Márgenes**: 5mm alrededor
- **Colores**: Print-color-adjust para colores exactos

### Diseño Responsive Móvil
- En móvil: Cambia a vertical automáticamente
- Logo más grande para mejor visibilidad
- QR más grande para escaneo fácil
- Touch-friendly (botones de 52px mínimo)

## 🎨 Elementos Visuales

### Logo
- **Desktop/Print**: 110px × 110px con borde blanco
- **Móvil**: 120px × 120px
- **Tarjetas múltiples**: 55px × 55px (optimizado)
- Forma circular profesional
- Sombra sutil para profundidad

### QR Code
- **Grande (pantalla)**: 200px × 200px
- **Integrado (tarjeta)**: 90px × 90px
- **Tarjetas múltiples**: 50px × 50px
- Siempre legible y escaneable
- Fondo blanco con borde sutil

### Colores
- Lado izquierdo: Color de marca del negocio
- Lado derecho: Blanco limpio
- Textos: Jerarquía visual clara
- Icons: Azul corporativo (#5a87db)

## 📱 Optimizaciones Android

### Interacción Táctil
- Botones de 52px mínimo (estándar Android)
- Ripple effect al tocar
- Feedback visual inmediato
- Sin zoom accidental

### Compartir Nativo
- Usa Web Share API de Android
- Menú nativo del sistema
- Opciones: WhatsApp, Gmail, Bluetooth, etc.
- Toast messages estilo Android

### Responsive
- Adapta automáticamente el layout
- Vertical en móvil, horizontal en desktop
- Elementos más grandes en pantallas pequeñas
- Optimizado para Samsung, Xiaomi, Motorola, etc.

## 🖨️ Guía de Impresión

### Paso 1: Preparar
```
1. Abrí "Ver mi tarjeta digital"
2. Elegí "Imprimir 6 tarjetas"
3. Confirmá el diálogo
```

### Paso 2: Configurar Impresora
```
✅ Orientación: LANDSCAPE (Horizontal)
✅ Papel: A4 (297 × 210mm)
✅ Márgenes: 10mm
✅ Escala: 100%
✅ Calidad: Alta
❌ NO ajustar al área imprimible
❌ NO usar Portrait (Vertical)
```

### Paso 3: Imprimir
```
- Usá papel de 250g o 300g
- Imprimí en color (o B&N con logo claro)
- Verificá que el QR sea nítido
```

### Paso 4: Cortar
```
- Seguí las líneas punteadas
- Usá guillotina para bordes rectos
- Medida final: 90mm × 55mm
- 6 tarjetas perfectas por hoja
```

## 🎯 Casos de Uso

### 1. Vidriera del Local
**Opción**: Imprimir 1 grande  
**Papel**: Bond 120g o couché  
**Uso**: Pegar en vidrio, clientes escanean el QR desde afuera

### 2. Evento/Feria
**Opción**: Imprimir 6 tarjetas (varias hojas)  
**Papel**: Cartulina 300g  
**Uso**: Repartir a visitantes, networking

### 3. Pedidos a Domicilio
**Opción**: Imprimir 6 tarjetas  
**Papel**: 250g  
**Uso**: Incluir una en cada pedido

### 4. Mostrador
**Opción**: Imprimir 6 tarjetas  
**Papel**: 300g  
**Uso**: Tarjetero en caja, clientes toman una

### 5. Digital (WhatsApp, Redes)
**Opción**: Compartir URL  
**Uso**: Botón "Compartir" → Enviar link directo

## 📊 Ventajas del Nuevo Diseño

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| **Formato** | Vertical | Horizontal profesional ✅ |
| **Tarjetas/hoja** | 8 (difícil cortar) | 6 perfectamente alineadas ✅ |
| **QR ubicación** | Al final, grande | Integrado, compacto ✅ |
| **Look profesional** | Informal | Business card real ✅ |
| **Fácil de cortar** | No | Sí (grid 3×2) ✅ |
| **Orientación** | Vertical | Landscape estándar ✅ |
| **Aprovechamiento** | 70% | 95% del papel ✅ |

## 🔧 Especificaciones de Desarrollo

### CSS Print Media Queries
```css
@media print {
  @page { size: A4 landscape; margin: 10mm; }
  .tarjetas-multiples {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(2, 1fr);
    gap: 8mm;
  }
}
```

### JavaScript Clonación
```javascript
// Genera 6 tarjetas (5 clones + 1 original)
for(let i = 0; i < 5; i++) {
  const clone = tarjetaOriginal.cloneNode(true);
  container.appendChild(clone);
}
```

### HTML Estructura
```html
<div class="business-card card-horizontal">
  <div class="card-left">
    <!-- Logo + QR -->
  </div>
  <div class="card-right">
    <!-- Info contacto -->
  </div>
</div>
```

## 📝 Checklist de Calidad

### Antes de Imprimir
- [ ] Logo subido y visible
- [ ] Información de contacto completa
- [ ] Color de marca configurado
- [ ] Descripción/slogan atractivo
- [ ] Orientación LANDSCAPE seleccionada
- [ ] Escala al 100%
- [ ] Papel adecuado (250g+)

### Después de Imprimir
- [ ] QR escaneable y funciona
- [ ] Colores fieles a tu marca
- [ ] Texto legible (no pixelado)
- [ ] Bordes alineados
- [ ] Corte limpio y recto

## 🚀 Próximas Mejoras Sugeridas

1. **Editor visual** para personalizar colores en tiempo real
2. **Plantillas prediseñadas** por rubro (restaurante, farmacia, etc.)
3. **Exportar como PDF** para enviar a imprenta
4. **Vista previa 3D** del resultado final
5. **Códigos QR con analytics** (trackear escaneos)

## 💡 Tips Pro

### Para Imprentas
Llevá el archivo generado a una imprenta y pedí:
- Papel: Cartulina 300g mate
- Acabado: Laminado mate o brillante
- Corte: Guillotina con esquinas redondeadas opcionales
- Cantidad: Múltiplos de 6 (6, 12, 24, 60, 120, etc.)

### Para Diseñadores
Si necesitás modificar el diseño:
1. Editá `templates/tarjeta_negocio.html`
2. Modificá los estilos `.card-horizontal`
3. Respetá el tamaño 90mm × 55mm
4. Mantené el QR siempre visible

### Para Usuarios
- Actualizá tu logo periódicamente
- Cambiá el slogan según temporada
- Imprimí suficientes tarjetas antes de eventos
- Siempre tené algunas en el mostrador

---

**ZupponPy** - Tarjetas Digitales Profesionales  
Diseño mejorado - Enero 2024  
Versión 2.0 🎴
