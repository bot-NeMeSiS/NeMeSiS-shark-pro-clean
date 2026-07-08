# V915 GitHub Actions CI QA

- Workflow creado: `.github/workflows/nemesis-ci.yml`.
- Se ejecuta en pull request, push a main y manual.
- Ejecuta compilacion Python, checks locales, Sentinel static, rutas/imports, build limpio y audit ZIP.
- No requiere secretos.
- Sube reportes y release output como artifact.

