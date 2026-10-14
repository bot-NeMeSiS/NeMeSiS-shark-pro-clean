"""Presentation helpers and controlled direct-sold ads routes."""
from datetime import datetime, timezone
import os
import secrets
from flask import Blueprint, abort, flash, make_response, redirect, render_template, request, session, url_for
from engines.admin_operations_workbench import build_admin_workbench
from engines import ads_monetization_engine as ads

PAGES = frozenset(('/admin/operations-center','/admin/operations','/admin/company-operations',
                   '/admin/centro-operaciones','/admin/sala-control'))
AD_CLIENT_PATHS = frozenset(('/', '/app', '/sports-hub', '/calendar', '/partidos', '/live',
    '/picks', '/track-record', '/historico', '/seguimiento', '/shark', '/shark-core',
    '/telegram', '/profile', '/plans', '/membership', '/favorites', '/favoritos',
    '/combis', '/combinadas', '/match', '/partido'))


def _is_admin(is_admin):
    try:
        return bool(is_admin())
    except Exception:
        return False


def _placement(path):
    if path in ('/live',):
        return 'live'
    if path in ('/calendar', '/partidos'):
        return 'calendar'
    if path in ('/', '/app', '/sports-hub'):
        return 'home'
    return 'all'


def _event_seen_key(event, campaign_id):
    return f"ads:{event}:{int(campaign_id)}:{datetime.now(timezone.utc).date().isoformat()}"


def _record_once(campaign_id, event):
    key = _event_seen_key(event, campaign_id)
    seen = session.get('_ns_ads_events', [])
    if not isinstance(seen, list):
        seen = []
    if key in seen:
        return
    if ads.record_event(campaign_id, event):
        seen.append(key)
        session['_ns_ads_events'] = seen[-100:]
        session.modified = True


def _campaign_is_deliverable(campaign):
    if not campaign or campaign.get('status') != 'active':
        return False
    try:
        now = datetime.now(timezone.utc)
        start = datetime.fromisoformat(campaign['starts_at'])
        end = datetime.fromisoformat(campaign['ends_at'])
        if start.tzinfo is None or end.tzinfo is None:
            return False
        return start <= now < end and ads.validate_https_url(campaign.get('destination_url')) is not None
    except (TypeError, ValueError, KeyError):
        return False


def _stripe_client():
    secret = os.environ.get('STRIPE_SECRET_KEY')
    if not secret:
        return None
    import stripe
    return stripe.StripeClient(secret)


def _ads_tax_ready():
    return os.environ.get('ADS_STRIPE_TAX_READY', '').lower() == 'true'


def _confirm_stripe_payment(campaign, stripe_session):
    """Fail closed unless the retrieved Checkout Session matches the stored order."""
    try:
        meta = stripe_session.get('metadata') or {}
        if stripe_session.get('id') != campaign.get('stripe_session_id'):
            return False
        if str(meta.get('campaign_id', '')) != str(campaign.get('id')):
            return False
        if stripe_session.get('mode') != 'payment' or stripe_session.get('payment_status') != 'paid':
            return False
        if str(stripe_session.get('currency', '')).lower() != 'eur':
            return False
        if int(stripe_session.get('amount_subtotal') or 0) != int(campaign.get('amount_cents') or 0):
            return False
        return ads.mark_paid(
            campaign['id'], campaign['stripe_session_id'],
            stripe_session.get('payment_intent') if isinstance(stripe_session.get('payment_intent'), str) else None,
        )
    except (TypeError, ValueError, KeyError, AttributeError):
        return False


def create_admin_productivity_blueprint(is_admin):
    bp = Blueprint('admin_productivity',__name__)

    @bp.app_context_processor
    def workbench_helper():
        result = {}
        if request.path in PAGES and _is_admin(is_admin):
            result['admin_workbench'] = build_admin_workbench
        if request.path in AD_CLIENT_PATHS and request.method == 'GET':
            result['ad_campaign'] = ads.active_campaign(placement=_placement(request.path))
        return result

    @bp.after_app_request
    def protect_operational_reading(response):
        if request.path in PAGES or request.path.startswith('/api/admin/operations-center/'):
            response.headers['Cache-Control']='private, no-store'
            response.vary.add('Cookie')
        if request.path.startswith('/ads/'):
            response.headers['Cache-Control'] = 'private, no-store, max-age=0'
            response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @bp.route('/publicidad', methods=['GET', 'POST'])
    def advertiser_portal():
        ads.ensure_schema()
        message = None
        form_data = {}
        if request.method == 'POST':
            form_data = request.form
            if request.form.get('accept_terms') != 'yes':
                message = 'Debes aceptar las condiciones publicitarias para continuar.'
            else:
                data, error = ads.validate_campaign_form(request.form)
                if error:
                    message = error
                else:
                    campaign_id = ads.create_campaign(data, True)
                    stripe = _stripe_client()
                    if stripe is None:
                        message = 'Hemos guardado tu solicitud, pero no se ha realizado ningún cargo. El cobro online aún no está habilitado; contactaremos contigo cuando esté configurado.'
                    else:
                        try:
                            integration_suffix = ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(8))
                            checkout = stripe.v1.checkout.sessions.create({
                                'mode': 'payment',
                                'line_items': [{
                                    'price_data': {
                                        'currency': 'eur',
                                        'unit_amount': data['amount_cents'],
                                        'tax_behavior': 'exclusive',
                                        'product_data': {
                                            'name': f"Publicidad NeMeSiS · {data['package_days']} días",
                                            'description': data['title'][:200],
                                        },
                                    },
                                    'quantity': 1,
                                }],
                                'automatic_tax': {'enabled': True},
                                'tax_id_collection': {'enabled': True},
                                'customer_creation': 'always',
                                'invoice_creation': {'enabled': True, 'invoice_data': {
                                    'description': f"Campaña publicitaria NeMeSiS · {data['package_days']} días",
                                    'metadata': {'campaign_id': str(campaign_id), 'company_name': data['company_name'][:100]},
                                }},
                                'billing_address_collection': 'required',
                                'customer_email': data['contact_email'],
                                'client_reference_id': str(campaign_id),
                                'metadata': {'campaign_id': str(campaign_id), 'package_days': str(data['package_days']),
                                             'company_name': data['company_name'][:100], 'advertiser_name': data['advertiser_name'][:100]},
                                'integration_identifier': f'nemesis_ads_{integration_suffix}',
                                'success_url': url_for('admin_productivity.advertiser_payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                                'cancel_url': url_for('admin_productivity.advertiser_portal', _external=True) + '?cancelled=1',
                            })
                            if not str(checkout.url or '').startswith('https://checkout.stripe.com/'):
                                raise ValueError('Unexpected Checkout URL')
                            ads.save_checkout_session(campaign_id, checkout.id)
                            return redirect(checkout.url, code=303)
                        except Exception:
                            # Never expose provider responses, keys, or account configuration details.
                            with ads.connect() as conn:
                                conn.execute("UPDATE ad_campaigns SET status='awaiting_payment_setup' WHERE id=? AND status='pending_payment'", (campaign_id,))
                            message = 'No se pudo iniciar el pago. No se ha realizado ningún cargo; revisa la configuración de Stripe antes de volver a intentarlo.'
        elif request.args.get('cancelled') == '1':
            message = 'Pago cancelado. No se ha activado ni publicado el anuncio.'
        return render_template('advertiser_portal.html', ad_message=message, form_data=form_data)

    @bp.route('/publicidad/pago-completado', methods=['GET'])
    def advertiser_payment_success():
        session_id = request.args.get('session_id', '')
        stripe = _stripe_client()
        if not stripe or not session_id or len(session_id) > 255:
            return render_template('advertiser_portal.html', ad_message='No hemos podido verificar el pago. No se activará ningún anuncio sin confirmación de Stripe.', form_data={}), 400
        try:
            campaign = ads.campaign_by_session(session_id)
            checkout = stripe.v1.checkout.sessions.retrieve(session_id)
            if not campaign or not _confirm_stripe_payment(campaign, checkout):
                return render_template('advertiser_portal.html', ad_message='El pago aún no está confirmado o los datos no coinciden. La campaña no se ha publicado.', form_data={}), 400
            return render_template('advertiser_portal.html', ad_message='Pago confirmado. Tu anuncio queda pendiente de revisión; no se mostrará hasta que lo aprobemos.', form_data={})
        except Exception:
            return render_template('advertiser_portal.html', ad_message='No hemos podido verificar el pago en este momento. La campaña seguirá sin publicarse hasta confirmar el estado en Stripe.', form_data={}), 503

    @bp.route('/api/stripe/ads-webhook', methods=['POST'])
    def ads_stripe_webhook():
        webhook_secret = os.environ.get('STRIPE_ADS_WEBHOOK_SECRET') or os.environ.get('STRIPE_WEBHOOK_SECRET')
        signature = request.headers.get('Stripe-Signature', '')
        if not webhook_secret or not signature:
            return make_response('Webhook not configured', 503)
        try:
            import stripe
            event = stripe.Webhook.construct_event(request.get_data(cache=False), signature, webhook_secret)
        except Exception:
            return make_response('Invalid webhook signature or payload', 400)
        event_type = event.get('type', '')
        stripe_session = (event.get('data') or {}).get('object') or {}
        if event_type in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
            try:
                campaign = ads.campaign_by_session(stripe_session.get('id'))
                if campaign:
                    _confirm_stripe_payment(campaign, stripe_session)
            except Exception:
                return make_response('Webhook processing failed', 500)
        elif event_type in ('checkout.session.async_payment_failed', 'checkout.session.expired'):
            try:
                campaign = ads.campaign_by_session(stripe_session.get('id'))
                if campaign:
                    ads.mark_payment_failed(
                        campaign['id'], campaign['stripe_session_id'],
                        'payment_expired' if event_type.endswith('.expired') else 'payment_failed',
                    )
            except Exception:
                return make_response('Webhook processing failed', 500)
        return {'received': True}, 200

    @bp.route('/ads/impression/<int:campaign_id>', methods=['GET'])
    def ad_impression(campaign_id):
        campaign = ads.campaign_by_id(campaign_id)
        if _campaign_is_deliverable(campaign):
            _record_once(campaign_id, 'impressions')
        response = make_response('', 204)
        response.headers['Cache-Control'] = 'private, no-store, max-age=0'
        return response

    @bp.route('/ads/click/<int:campaign_id>', methods=['GET'])
    def ad_click(campaign_id):
        campaign = ads.campaign_by_id(campaign_id)
        if not _campaign_is_deliverable(campaign):
            abort(404)
        _record_once(campaign_id, 'clicks')
        return redirect(ads.validate_https_url(campaign['destination_url']), code=302)

    @bp.route('/admin/ads', methods=['GET'])
    def ads_admin():
        if not _is_admin(is_admin):
            abort(403)
        campaigns = ads.list_campaigns()
        paid_states = {'paid_pending_review', 'active', 'paused', 'expired', 'refund_required'}
        return render_template(
            'admin_ads.html',
            campaigns=campaigns,
            revenue_cents=sum(c['amount_cents'] for c in campaigns if c['status'] in paid_states),
            impressions=sum(c['impressions'] for c in campaigns),
            clicks=sum(c['clicks'] for c in campaigns),
            refunds_pending=sum(1 for c in campaigns if c['status'] == 'refund_required'),
        )

    @bp.route('/admin/ads/<int:campaign_id>/action', methods=['POST'])
    def ads_campaign_action(campaign_id):
        if not _is_admin(is_admin):
            abort(403)
        action = request.form.get('action', '')
        ok, message = ads.review_campaign(campaign_id, action)
        flash(message, 'success' if ok else 'warning')
        return redirect(url_for('admin_productivity.ads_admin'), code=303)

    @bp.route('/admin/ads/reconcile', methods=['POST'])
    def ads_reconcile():
        if not _is_admin(is_admin):
            abort(403)
        stripe = _stripe_client()
        if stripe is None:
            flash('Stripe no está configurado; no se ha consultado ni cobrado nada.', 'warning')
            return redirect(url_for('admin_productivity.ads_admin'), code=303)
        checked = confirmed = 0
        for campaign in ads.list_campaigns(limit=100):
            if campaign.get('status') != 'pending_payment' or not campaign.get('stripe_session_id'):
                continue
            try:
                checkout = stripe.v1.checkout.sessions.retrieve(campaign['stripe_session_id'])
                checked += 1
                if _confirm_stripe_payment(stripe, campaign, checkout):
                    confirmed += 1
            except Exception:
                continue
        flash(f'Verificación terminada: {checked} sesiones consultadas y {confirmed} pagos confirmados. Las campañas pagadas siguen pendientes de revisión.', 'success')
        return redirect(url_for('admin_productivity.ads_admin'), code=303)

    return bp
