# Mini app cliente

SPA en **Vite + React + TypeScript** que consume el API cliente de Django para
que un cliente:

- haga login,
- vea sus reservas,
- cancele una reserva con motivo.

## Cómo correrla en desarrollo

Requisitos: Node 22+ y el backend corriendo en `http://127.0.0.1:8000`
(ver el README de la raíz).

```bash
cd client-app
npm install
npm run dev
```

Abrir [http://localhost:5173](http://localhost:5173) y entrar con un cliente
semilla, por ejemplo `alice@example.com` / `demo1234`.

El dev server de Vite redirige `/api` al backend, igual que nginx en la imagen
Docker. El navegador siempre habla con un solo origen, así que Django no
necesita configuración de CORS. Si el backend corre en otra dirección:

```bash
API_PROXY_TARGET=http://localhost:9000 npm run dev
```

## Scripts

| Comando | Qué hace |
|---|---|
| `npm run dev` | Dev server con proxy a Django. |
| `npm run build` | Type-check (`tsc -b`) y build de producción en `dist/`. |
| `npm run lint` | Lint con oxlint. |
| `npm run preview` | Sirve el build de `dist/` localmente. |

## Estructura

```text
src/
  api/
    client.ts      fetch tipado; todo error se convierte en ApiError con un Problem
    endpoints.ts   login, perfil, listado y cancelación
    messages.ts    textos en español por código de error del API
    types.ts       tipos del contrato (API_CONTRACT.md)
  components/
    LoginPage.tsx
    ReservationsPage.tsx
    CancelReservationDialog.tsx
  reservations.ts  etiquetas de estado, formato de fechas, qué se puede cancelar
  session.ts       guardado del token en sessionStorage
  App.tsx          decide entre login y "Mis reservas" según haya token
```

## Decisiones

- **Sin librerías extra.** `fetch` nativo y estado con `useState`: la app tiene
  dos pantallas y un modal, y no justifica Redux, React Query ni axios.
- **Un solo formato de error.** `apiRequest` convierte cualquier fallo (error del
  API, respuesta que no es JSON o servidor caído) en un `ApiError` que lleva un
  `Problem`. La UI decide qué mostrar según `code`, no según el texto.
- **El backend es la fuente de verdad.** La app valida el motivo vacío solo para
  dar feedback rápido; el API lo vuelve a validar. Si la reserva cambió en el
  servidor (`409` o `404`), el modal lo explica y ofrece actualizar la lista.
- **Actualización visual sin recargar.** El endpoint de cancelación devuelve la
  reserva actualizada y la lista se actualiza con esa respuesta.
- **Sesión.** El token se guarda en `sessionStorage`: sobrevive a un refresh y se
  borra al cerrar la pestaña. Cualquier `401` cierra la sesión y vuelve al login
  con un aviso.
- **Fechas.** Se muestran en la zona horaria del navegador con `Intl.DateTimeFormat`.
