# DESIGN.md — Mi Pedido (app WebView)

Sistema visual registrado desde el código construido (rediseño Material 3, septiembre 2026).
Superficie: `apk-builder/ferreteria/assets/www/index.html` — un solo archivo (HTML+CSS+JS), offline, Android WebView y navegador de escritorio.

## Modo y plataforma

- Modo del visitante: **Operate** (el vendedor completa un pedido).
- Plataforma: WebView Android → gramática **Material Design 3**; light theme único (force-dark de WebViews viejos descartado a propósito).

## Color (roles M3, estrategia Restrained)

| Rol | Valor |
|---|---|
| primary / on-primary | `#2F4A63` (acero) / `#FFFFFF` |
| primary-container / on | `#D3E3F3` / `#0F2C42` |
| secondary-container / on | `#E2E6EC` / `#23272C` |
| tertiary (latón) / on | `#7D5600` / `#FFFFFF` |
| tertiary-container / on | `#FFDEA1` / `#2C1A00` |
| error / error-container | `#BA1A1A` / `#FFDAD6` |
| success (precios) | `#1E6B45` |
| surface (página) | `#F1F3F6` |
| surface (tarjetas) | `#FFFFFF` |
| surface-high (search/chips internos) | `#E4E8EE` |
| on-surface / on-surface-variant | `#191C1F` / `#454A51` |
| outline / outline-variant | `#74777E` / `#C9CCD3` |
| inverse-surface / inverse-on (dock, snackbar) | `#2E3135` / `#F0F2F4` |

- Neutrales siempre con tinte frío (nunca gris puro). Verde solo para dinero; latón solo para la acción comercial del proveedor; error rojo para destrucción/descuento.

## Tipografía

- Familia: **Roboto** (tipografía del sistema Android; app offline sin web fonts) — waiver del detector `overused-font` documentado.
- Escala (rem): app bar 22/500 · títulos de tarjeta 16/600 · cuerpo 15/400–500 · etiquetas SKU 11/600 +0.5px · botones 15/600 +0.2px · montos con `font-variant-numeric: tabular-nums`.

## Forma y elevación

- Radios: filas/tarjetas 16 · paneles ajustes 20 · diálogos 28 · botones/chips/search bar stadium (999) · inputs 8–10.
- Elevación M3 con offset+blur (`--e1..--e3`) reservada a dock, snackbar y diálogos; el resto se separa por tono, no por sombra.

## Componentes

- **Top app bar**: superficie (no saturada), sticky, borde inferior hairline, icon buttons 48dp circulares con state-layer al presionar.
- **Search bar**: stadium 52dp sobre `surface-high`, icono leading, focus-within → blanco + e1.
- **Filas de producto**: min 76dp, imagen 52dp r12, SKU label, nombre 15/500 con ellipsis, precio verde tabular, steppers circulares 48dp (−: `surface-high`, +: `primary-container`).
- **Dock del pedido** (momento firma): barra flotante `inverse-surface` r20 con count+total y CTA "Ver pedido", `left/right 16px + safe-area`.
- **Botones `.btn-full`**: 52dp stadium — WhatsApp `#128C4B` filled · PDF usuario outlined neutral · PDF proveedor filled latón · Guardar filled-tonal primary-container · Seguir agregando outlined primary.
- **Diálogo**: r28, padding 24, e3, imagen 210dp fondo blanco con hairline (fotos de producto sin bordes), acciones con steppers + "Listo" filled primary.
- **Snackbar**: `inverse-surface` r10 con animación slide-up 220ms, encima del dock.
- **Iconografía**: SVG Material filled inline (back, settings, search, box, cart, warning, check, error, close) — sin emojis como iconos.

## Movimiento

- `--ease: cubic-bezier(0.2,0,0,1)`; transición de pantalla fade-through 220ms; diálogos 200ms scale+fade; overlays 160ms; press = state-layer/brightness (sin bounce).

## Superficies del navegador tematizadas

`::selection` primary-container · `:focus-visible` anillo primary · caret primary · tap-highlight transparente · scrollbars del sistema.

## Decisiones duraderas

1. Light theme único (sin `prefers-color-scheme`) para evitar doble inversión del force-dark en WebViews viejos.
2. Roboto como única familia (offline + rostro del sistema Android).
3. Sin tarjetas anidadas: paneles y filas separadas por tono/hairlines.
4. El dock usa `inverse-surface`: es el único elemento oscuro sobre la app clara.
