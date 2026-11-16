# 📋 Categorías de Negocios - ZupponPy

## Total: 98 Categorías Disponibles

### 🍽️ Alimentos y Bebidas (15)
- 🍽️ Restaurante
- 🛒 Supermercado
- 🥐 Panadería
- 🥩 Carnicería
- ☕ Café
- 🍺 Bar
- 🍦 Heladería
- 🍕 Pizzería
- 🍔 Hamburguesas
- 🥖 Lomitería
- 🥟 Empanadas
- 🍗 Rotisería
- 🌮 Comida rápida
- 🛵 Delivery

### 💇 Belleza y Cuidado Personal (5)
- 💇 Peluquería
- 💈 Barbería
- 💅 Salón de belleza
- 🧖 Spa
- ✨ Centro de estética

### 🚗 Automotriz (7)
- 🚗 Lavadero de autos
- 🛢️ Lubricentro
- 🔧 Taller mecánico
- 🛞 Gomería
- 🚙 Automotriz
- 🏎️ Concesionaria
- ⚙️ Repuestos

### 🔨 Construcción y Hogar (7)
- 🔨 Ferretería
- 🧱 Materiales de construcción
- 🔐 Cerrajería
- 🎨 Pinturería
- 🚰 Plomería
- ⚡ Electricidad

### 👕 Moda y Accesorios (7)
- 👕 Ropa y calzado
- 👗 Boutique
- 👞 Zapatería
- ⚽ Deportes
- 💍 Joyería
- 📿 Bijouterie
- ⌚ Relojería

### 📱 Tecnología (4)
- 📱 Electrónica
- 📱 Celulares
- 💻 Computación
- 🔌 Electrodomésticos

### 🛋️ Hogar y Decoración (3)
- 🛋️ Mueblería
- 🖼️ Decoración
- 🎁 Bazar

### 📚 Papelería y Educación (7)
- 📚 Librería
- ✏️ Papelería
- 🎓 Educación
- 📖 Academia
- 🏫 Instituto
- 👨‍🏫 Cursos
- 🌍 Idiomas

### 🏥 Salud (6)
- 💊 Farmacia
- 🏥 Clínica
- 👨‍⚕️ Consultorio
- 🧪 Laboratorio
- 👓 Óptica
- 🦷 Odontología

### 🐾 Mascotas y Agro (3)
- 🐾 Veterinaria
- 🐶 Pet shop
- 🌾 Agropecuaria

### 💪 Fitness y Deporte (5)
- 💪 Gimnasio
- 🏃 Centro deportivo
- 🧘 Yoga
- 🤸 Pilates
- 💃 Danza

### 📷 Servicios Creativos (4)
- 📷 Fotografía
- 🖨️ Imprenta
- 📢 Publicidad
- 🎨 Diseño

### 🏠 Inmobiliaria y Construcción (3)
- 🏠 Inmobiliaria
- 📐 Arquitectura
- 👷 Construcción

### 💐 Naturaleza y Plantas (3)
- 💐 Floristería
- 🌱 Vivero
- 🌿 Jardinería

### 🏨 Turismo y Hospedaje (4)
- 🏨 Hotel
- 🛏️ Hostel
- 🏢 Apart hotel
- ✈️ Turismo

### 🎉 Eventos (3)
- 🎉 Eventos
- 🍽️ Catering
- 🎊 Salón de fiestas

### 🧸 Juguetes y Regalos (3)
- 🧸 Juguetería
- 🎈 Cotillón
- 🎁 Regalos

### 🧺 Textiles y Confección (3)
- 🧺 Lavandería
- 👔 Tintorería
- 🪡 Sastrería

### 🎸 Entretenimiento (5)
- 🎸 Instrumentos musicales
- 💿 Disquería
- 🎬 Cine
- 🎭 Teatro
- 🎪 Entretenimiento

### 🛠️ General (2)
- 🛠️ Servicios
- 📦 Otros

---

## 🎨 Sistema de Colores

Cada categoría tiene un color único asignado para mejor identificación visual:

### Paleta de Colores por Tipo

**Alimentos**: Tonos cálidos (naranjas, amarillos, rojos)  
**Belleza**: Tonos rosas y lilas  
**Automotriz**: Tonos azules y grises  
**Construcción**: Tonos tierra y amarillos  
**Moda**: Tonos pastel variados  
**Tecnología**: Tonos azules  
**Salud**: Tonos azules claros y verdes  
**Naturaleza**: Tonos verdes  
**Turismo**: Tonos azules  
**Eventos**: Tonos festivos (rosas, lilas)  
**Entretenimiento**: Tonos vibrantes  

## 📝 Uso en el Sistema

### Para Usuarios
Las categorías aparecen en:
- ✅ Formulario de nueva oferta
- ✅ Filtros de búsqueda
- ✅ Tarjetas de ofertas (con emoji y color)
- ✅ Mapa de ofertas
- ✅ Panel de administración

### Para Administradores
Pueden:
- Ver ofertas por categoría
- Filtrar negocios por tipo
- Estadísticas por categoría
- Gestión de ofertas categorizadas

## 🔄 Agregar Nuevas Categorías

Si necesitás agregar más categorías, editá el archivo `app.py`:

```python
# Agregar a la lista CATEGORIAS
CATEGORIAS = [
    ...
    "Nueva Categoría",
    ...
]

# Agregar al diccionario CAT con emoji y color
CAT = {
    ...
    "Nueva Categoría": {"emoji": "🆕", "color": "#hexcolor"},
    ...
}
```

### Recomendaciones de Colores

- Usá colores en formato hexadecimal (`#rrggbb`)
- Preferí colores pastel para mejor legibilidad
- Evitá colores muy oscuros o muy claros
- Cada categoría debe tener un color único

### Emojis Recomendados

- 🍕 Comidas
- 💇 Servicios personales
- 🏠 Hogar
- 🚗 Automotriz
- 💻 Tecnología
- 🎨 Arte y diseño
- 🏃 Deportes
- 📚 Educación
- 🏥 Salud
- 🎉 Eventos

---

**ZupponPy** - Sistema de cupones con 98 categorías disponibles  
Actualizado: Enero 2024 📦
