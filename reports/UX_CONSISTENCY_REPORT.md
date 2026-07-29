# UX Consistency Report

## Status

PASS

## Coverage

- Templates scanned: 193
- Buttons scanned: 145

## Findings

| severity | category | screen | title | evidence |
| --- | --- | --- | --- | --- |
| P3 | visual_system | templates/500.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P2 | copy | templates/account_center.html | Texto tecnico puede quedar visible | todo |
| P3 | component | templates/account_center.html | Demasiados enlaces sin sistema visual compartido | unstyled_links=11 |
| P3 | visual_system | templates/account_center.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/action_platform.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/activity.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/adaptive_experience.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_alerts.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_api_sports_audit.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_app_experience_quality.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_app_feel.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_architecture.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_auto_improvement.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_automation.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_autonomous_picks.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_autopilot_audit.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_backups.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_beta_center.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_betting_center.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_bootstrap.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_calendar_experience.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_client_experience.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_client_screen_audit.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_client_success.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_client_visual_qa.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_codex_automation.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_command_center.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_commercial_readiness.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_company_os.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_compliance_center.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_content_rights.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P2 | copy | templates/admin_dashboard.html | Texto tecnico puede quedar visible | todo |
| P3 | visual_system | templates/admin_data_depth.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_data_marketplace.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_data_memory.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_data_vault.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_final_qa.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_go_live.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_growth_center.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |
| P3 | visual_system | templates/admin_highlights_center.html | Pantalla fuera del sistema visual actual | No se detectan clases ns- ni v933. |


## Permanent Rule

Las pantallas no deben exponer texto tecnico, `None`, `null`, `undefined`, mojibake, botones sin contrato visual ni navegacion mezclada cliente/admin.
