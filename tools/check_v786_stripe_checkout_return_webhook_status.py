from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]

def require(cond, msg):
    if not cond:
        print('FAIL:', msg)
        sys.exit(1)

version = (ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()
app = (ROOT/'app.py').read_text(encoding='utf-8')
engine = (ROOT/'engines'/'stripe_payments_engine.py').read_text(encoding='utf-8')
membership = (ROOT/'templates'/'membership.html').read_text(encoding='utf-8')
base = (ROOT/'templates'/'base.html').read_text(encoding='utf-8')
css = (ROOT/'static'/'app.css').read_text(encoding='utf-8')

require(version.startswith(('V786_STRIPE_CHECKOUT_RETURN_WEBHOOK_STATUS_POLISH','V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY','V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH','V789_REAL_LAUNCH_CERTIFICATION_COMMAND_CENTER','V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH','V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL')), f'VERSION inesperada: {version}')
require('APP_VERSION = "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL"' in app or 'APP_VERSION = "V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH"' in app or 'APP_VERSION = "V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY"' in app or 'APP_VERSION = "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL"' in app or 'APP_VERSION = "V785_MEMBERSHIP_STRIPE_FLOW_PRICE_POLISH"' in app or 'APP_VERSION = "V784_SMOKE_PREFLIGHT_VALIDATION_FOUNDATION"' in app or 'APP_VERSION = "V783_HOME_MEMBERSHIP_CLIENT_EXPERIENCE_COMPACT_FINAL"' in app, "APP_VERSION no actualizado")
require('sync_checkout_session' in app and 'def sync_checkout_session' in engine, 'sync de checkout tras retorno no integrado')
require('checkout.return.sync' in engine, 'evento de sync de retorno no registrado')
require('session_id={{CHECKOUT_SESSION_ID}}' in engine, 'success_url Stripe no conserva CHECKOUT_SESSION_ID')
require("request.args.get('pago') == 'exito'" in membership and "request.args.get('sync')" in membership, 'mensajes de pago exitoso/sync no presentes')
require('data-ns-no-loading="1"' in membership, 'botones Stripe no evitan spinner persistente')
require('pageshow' in base and 'nsResetLoadingButtons' in base, 'base no resetea loaders al volver desde Stripe')
require('v786-billing-state' in membership and 'v786-billing-state' in css, 'estado de facturación V786 no pulido')
require('V786 Stripe Checkout return' in css, 'CSS V786 no incluido')
print('OK V786 Stripe Checkout return webhook status polish')
