# Límites de los planes gratuitos (consultados 2026-11-10)

| Servicio | Límite relevante | Impacto en el diseño |
|---|---|---|
| Render (web service free) | 750 h/mes; se duerme tras 15 min sin tráfico (~1 min de arranque); sistema de archivos efímero | Nada se guarda en disco; el frontend tolera arranque en frío (reintento y mensaje). Despliegue con Docker en plan free: **no verificado** |
| MongoDB Atlas M0 | 0,5 GB; 500 conexiones; 100 ops/s; 10 GB entrada/salida por 7 días; pausa tras 30 días de inactividad | Pool pequeño; índices mínimos; validación JSON Schema en M0: **no confirmada** (la API valida igualmente con Pydantic) |
| Supabase free | 1 GB Storage; 5 GB egress; 500 MB BD; pausa tras 1 semana sin actividad; límite global de archivo ≤ 50 MB | Límite de la app 5 MB por archivo; bucket privado; descarga vía API del backend |
| GitHub Pages | 1 GB sitio; 100 GB/mes (blando); 10 builds/h (blando) | Solo frontend estático; Pages en repos privados con plan free: **no verificado** |

Cuotas y condiciones cambian: revisar antes de desplegar. Capacidad estimada: 1 GB / 5 MB ≈ 200 certificados al máximo; en la práctica los PDF pesan menos.
