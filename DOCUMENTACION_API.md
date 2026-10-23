# 📱 Zuppon Scanner - Documentación de Integración API

## 🎯 Descripción General

La aplicación Android **Zuppon Scanner** escanea códigos QR de cupones y valida su uso en tiempo real contra tu servidor. Cuando un comercio escanea un cupón, la app:

1. 📸 Escanea el código QR
2. 📤 Envía la validación a tu servidor
3. ✅ Muestra si el cupón es válido, ya fue usado, o expiró
4. 📊 Guarda historial de escaneos

---

## 🔗 Integración con tu Backend

### **Formato de URL en el Código QR**

Los códigos QR deben contener URLs con este formato:

```
https://zuppon.es/cupon?id=ABC123&store=Heladeria+Frescura&descuento=20%
```

#### Parámetros:
- **`id`** o **`cupon`** (requerido): Identificador único del cupón
- **`store`** o **`comercio`** (opcional): Nombre del comercio
- **`descuento`** o **`discount`** (opcional): Porcentaje o descripción del descuento

---

## 🛠️ API REST que necesitas implementar

### **Endpoint: Validar Cupón**

```http
POST https://zuppon.es/api/validate-coupon
Content-Type: application/json
```

#### Request Body:
```json
{
  "coupon_id": "ABC123",
  "timestamp": 1698073200000,
  "device_id": "android_device_unique_id"
}
```

#### Responses:

##### ✅ **200 OK** - Cupón válido y marcado como usado
```json
{
  "status": "success",
  "message": "Cupón validado correctamente",
  "coupon": {
    "id": "ABC123",
    "store": "Heladería Frescura",
    "discount": "20%",
    "original_price": 35000,
    "discounted_price": 28000
  },
  "validated_at": "2024-10-23T10:30:00Z"
}
```

##### ⚠️ **409 Conflict** - Cupón ya fue utilizado
```json
{
  "status": "error",
  "code": "ALREADY_USED",
  "message": "Este cupón ya fue utilizado",
  "used_at": "2024-10-22T15:20:00Z",
  "used_by_device": "android_device_xyz"
}
```

##### ❌ **410 Gone** - Cupón expirado
```json
{
  "status": "error",
  "code": "EXPIRED",
  "message": "Este cupón ha expirado",
  "expired_at": "2024-10-20T23:59:59Z"
}
```

##### ❌ **404 Not Found** - Cupón no existe
```json
{
  "status": "error",
  "code": "NOT_FOUND",
  "message": "Cupón no encontrado"
}
```

##### ❌ **500 Internal Server Error** - Error del servidor
```json
{
  "status": "error",
  "code": "SERVER_ERROR",
  "message": "Error interno del servidor"
}
```

---

## 🗄️ Base de Datos

### Tabla recomendada: `coupons`

```sql
CREATE TABLE coupons (
    id VARCHAR(255) PRIMARY KEY,
    store_name VARCHAR(255) NOT NULL,
    discount_percentage INT,
    discount_description TEXT,
    original_price DECIMAL(10, 2),
    discounted_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP NULL,
    used_by_device VARCHAR(255) NULL,
    max_uses INT DEFAULT 1,
    current_uses INT DEFAULT 0
);
```

### Tabla recomendada: `coupon_validations` (historial)

```sql
CREATE TABLE coupon_validations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coupon_id VARCHAR(255) NOT NULL,
    device_id VARCHAR(255) NOT NULL,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'already_used', 'expired', 'not_found') NOT NULL,
    FOREIGN KEY (coupon_id) REFERENCES coupons(id)
);
```

---

## 🔧 Implementación del Endpoint (Ejemplo en Node.js/Express)

```javascript
const express = require('express');
const app = express();
app.use(express.json());

app.post('/api/validate-coupon', async (req, res) => {
    const { coupon_id, timestamp, device_id } = req.body;
    
    try {
        // 1. Buscar el cupón en la base de datos
        const coupon = await db.query(
            'SELECT * FROM coupons WHERE id = ?', 
            [coupon_id]
        );
        
        if (!coupon) {
            return res.status(404).json({
                status: 'error',
                code: 'NOT_FOUND',
                message: 'Cupón no encontrado'
            });
        }
        
        // 2. Verificar si está expirado
        if (new Date() > new Date(coupon.expires_at)) {
            await logValidation(coupon_id, device_id, 'expired');
            return res.status(410).json({
                status: 'error',
                code: 'EXPIRED',
                message: 'Este cupón ha expirado',
                expired_at: coupon.expires_at
            });
        }
        
        // 3. Verificar si ya fue usado
        if (coupon.is_used || coupon.current_uses >= coupon.max_uses) {
            await logValidation(coupon_id, device_id, 'already_used');
            return res.status(409).json({
                status: 'error',
                code: 'ALREADY_USED',
                message: 'Este cupón ya fue utilizado',
                used_at: coupon.used_at,
                used_by_device: coupon.used_by_device
            });
        }
        
        // 4. Marcar el cupón como usado
        await db.query(
            'UPDATE coupons SET is_used = TRUE, used_at = NOW(), used_by_device = ?, current_uses = current_uses + 1 WHERE id = ?',
            [device_id, coupon_id]
        );
        
        // 5. Registrar la validación
        await logValidation(coupon_id, device_id, 'success');
        
        // 6. Respuesta exitosa
        return res.status(200).json({
            status: 'success',
            message: 'Cupón validado correctamente',
            coupon: {
                id: coupon.id,
                store: coupon.store_name,
                discount: `${coupon.discount_percentage}%`,
                original_price: coupon.original_price,
                discounted_price: coupon.discounted_price
            },
            validated_at: new Date().toISOString()
        });
        
    } catch (error) {
        console.error('Error validando cupón:', error);
        return res.status(500).json({
            status: 'error',
            code: 'SERVER_ERROR',
            message: 'Error interno del servidor'
        });
    }
});

async function logValidation(coupon_id, device_id, status) {
    await db.query(
        'INSERT INTO coupon_validations (coupon_id, device_id, status) VALUES (?, ?, ?)',
        [coupon_id, device_id, status]
    );
}

app.listen(3000, () => {
    console.log('API escuchando en puerto 3000');
});
```

---

## 📲 Características de la App Android

### **Pantalla de Escaneo**
- ✅ Cámara en tiempo real
- ✅ Detección automática de QR
- ✅ Marco visual para guiar al usuario
- ✅ Confirmación antes de validar
- ✅ Feedback visual inmediato

### **Pantalla de Historial**
- ✅ Lista de todos los cupones escaneados
- ✅ Estados con colores:
  - 🟢 Verde: Validado correctamente
  - 🟠 Naranja: Ya fue usado
  - 🔴 Rojo: Expirado
  - ⚫ Gris: Error
- ✅ Información completa (comercio, descuento, fecha, hora)
- ✅ Código del cupón para referencia

---

## 🧪 Pruebas

### 1. **Generar un código QR de prueba**

Usa cualquier generador de QR online con esta URL:
```
https://zuppon.es/cupon?id=TEST001&store=Heladeria+Test&descuento=20%
```

### 2. **Mock del servidor (para pruebas sin backend)**

Puedes usar [Mockoon](https://mockoon.com/) o crear un servidor simple con estas respuestas.

### 3. **Testing con Postman**

```bash
POST https://zuppon.es/api/validate-coupon
Content-Type: application/json

{
  "coupon_id": "TEST001",
  "timestamp": 1698073200000,
  "device_id": "test_device"
}
```

---

## 🔐 Seguridad

### Recomendaciones:

1. **Autenticación**: Añade un token API en los headers
   ```kotlin
   connection.setRequestProperty("Authorization", "Bearer YOUR_API_KEY")
   ```

2. **Rate Limiting**: Limita peticiones por dispositivo/IP

3. **HTTPS**: Usa siempre HTTPS en producción

4. **Validación de dispositivo**: Guarda el `device_id` para detectar uso fraudulento

5. **Logs**: Registra todas las validaciones para auditoría

---

## 📈 Métricas y Analytics

Puedes agregar estos endpoints adicionales:

### **GET /api/coupon-stats**
```json
{
  "total_coupons": 50,
  "total_validated": 35,
  "total_expired": 5,
  "total_unused": 10,
  "most_popular_store": "Heladería Frescura"
}
```

### **GET /api/coupon/{id}/history**
```json
{
  "coupon_id": "ABC123",
  "validations": [
    {
      "device_id": "device_1",
      "validated_at": "2024-10-23T10:30:00Z",
      "status": "success"
    }
  ]
}
```

---

## 🚀 Próximos pasos

1. **Implementa el endpoint** `/api/validate-coupon` en tu servidor
2. **Genera códigos QR** para tus cupones con el formato correcto
3. **Instala la app** en un dispositivo Android
4. **Prueba** escaneando un QR de test
5. **Ajusta** según tus necesidades específicas

---

## 💡 Mejoras futuras opcionales

- 🔔 Notificaciones push cuando se valida un cupón
- 📊 Dashboard web para comercios
- 🎨 Branding personalizado por comercio
- 📍 Validación por geolocalización
- 🔄 Sincronización offline y envío cuando hay conexión
- 📱 Modo "comercio" y modo "cliente" en la misma app

---

## 🆘 Soporte

Si necesitas ayuda:
1. Verifica que el servidor responda correctamente con Postman
2. Revisa los logs de Android Studio con `Logcat`
3. Comprueba que las URLs en los QR sean correctas
4. Asegúrate de tener permisos de cámara e internet

---

**¡La app está lista para usar! Solo falta implementar el backend. 🚀**
