# V898 Next Steps

1. Desplegar V898 en Render.
2. Verificar `/api/runtime-version` y confirmar `has_v898_404_pwa_reference_outbox_truth=true`.
3. Abrir la app en incógnito.
4. En dispositivos con PWA antigua, usar `Restablecer app/PWA`.
5. Subir imágenes oficiales a `reference_images/`.
6. Ejecutar `python tools/run_browser_reference_qa.py --base-url https://bot-apuestas-crgf.onrender.com` si Playwright está disponible.
7. Revisar `/admin/not-found-events` con sesión admin.

