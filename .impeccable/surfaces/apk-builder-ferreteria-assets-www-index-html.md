---
version: 1
slug: "apk-builder-ferreteria-assets-www-index-html"
primary_target: "apk-builder/ferreteria/assets/www/index.html"
related_targets: []
---

# Surface brief — apk-builder/ferreteria/assets/www/index.html

Scope: full app (single-file WebView app). Visitor mode: Operate.
Audience: vendedores de ferreteria (LC 2050) tomando pedidos offline en Android; job: armar y enviar un pedido rapido; task: buscar, sumar cantidades, ver total, enviar/descargar. Frequency: alta, en mostrador o a domicilio. Constraints: offline (sin web fonts), WebView Android, no romper funcionalidad existente (IDs/classes/handlers intactos), light theme (force-dark de WebView viejo descartado).

## Direction contract
THESIS: Un "comprobante de pedido" premium en Material 3 para el mostrador de ferreteria: estructura en azul acero, laton reservado al dinero en movimiento; rechaza el look dashboard-admin (tarjetas uniformes + top bar saturada).
OWN-WORLD: Neutrales con tinte frio (nunca gris puro), primario acero #2F4A63, terciario laton #8A5A00/#FFDFA8, verde profundo solo para precios; escala tipografica Material en Roboto con numeros tabulares; botones stadium, dialogos 28dp, superficies 16-20dp, dock flotante inverse-surface.
STORY: El vendedor escanea el catalogo, toca cantidades, ve crecer el total en el dock y despacha el pedido; la herramienta desaparece en la tarea.
FIRST VIEWPORT (catalogo): top app bar de superficie con titulo 22px "LC 2050", barra de busqueda full-radius con icono, filas de ~80dp (imagen 52dp, sku label, nombre, precio verde tabular, steppers 48dp) y dock oscuro flotante abajo con "N productos · $total" + "Ver pedido".
FORM: code-led; mundo de reemplazo (el look anterior es evidencia, no referencia). Seed: n/a (direccion fijada por el usuario).
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
