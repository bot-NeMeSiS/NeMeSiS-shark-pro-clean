# Feedback Platform Report

## Purpose

Recoger errores, sugerencias, satisfacci?n y fricci?n de usuarios beta sin solicitar informaci?n sensible.

## Structured Feedback

- `feedback_type`: bug, feature_request, satisfaction o general.
- `category`: ?rea del producto afectada.
- `severity`: baja, media, alta o bloqueante.
- `route`: ruta interna saneada.
- `device_context`: desktop, tablet, m?vil o no indicado.
- `title` y `message`: texto limitado y filtrado contra datos sensibles.
- Bugs: pasos, resultado esperado y resultado real obligatorios.

## Privacy

```json
{
  "stores_sensitive_information": false,
  "stores_email": false,
  "stores_phone": false,
  "stores_tokens": false,
  "uses_pseudonymous_user_ref": true,
  "metrics_can_be_disabled_per_submission": true,
  "external_calls": 0,
  "telegram_sends": 0,
  "stripe_calls": 0
}
```

## Reproducibility Contract

```json
{
  "bug_requires_steps": true,
  "bug_requires_expected_result": true,
  "bug_requires_actual_result": true,
  "route_is_sanitized": true,
  "free_text_sensitive_guard": true
}
```

## Current Queue

- Feedback total: 4
- Bugs: 1
- Solicitudes: 1
- Abiertos: 2

## Limitation

La certificaci?n es local. La beta real debe arrancar con usuarios voluntarios y revisi?n humana de cada se?al.
