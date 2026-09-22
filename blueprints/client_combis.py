"""Explicit compatibility adapter for the existing combinadas routes.

Registered at application setup by the existing composition root. One set of
handlers owns old and new URLs; no second sports feed or request-time monkeypatch.
"""
from __future__ import annotations
import uuid
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Blueprint, g, jsonify, redirect, render_template, request, session
from engines import client_combi_store as store
from engines.combi_advisor_engine import CombiError, CONTRACT
from engines.security_engine import validate_csrf
from engines.combi_draft_review import review_draft


def create_client_combi_blueprint(db_path):
    bp = Blueprint('client_combis', __name__)

    def values():
        if request.content_length is not None and request.content_length > 65536:
            raise CombiError('PAYLOAD_TOO_LARGE', 'El formulario es demasiado grande.', 413)
        if request.is_json:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                raise CombiError('INVALID_PAYLOAD', 'El cuerpo debe ser un objeto JSON.')
            return data
        data = request.form.to_dict()
        data['pick_ids'] = request.form.getlist('pick_ids')
        return data

    def mutation_guard(data):
        if not session.get('user_id'):
            raise CombiError('AUTH_REQUIRED', 'Inicia sesión para crear tu borrador.', 401)
        token = request.headers.get('X-CSRF-Token') or request.headers.get('X-CSRFToken') or data.get('csrf_token')
        if not validate_csrf(session, token):
            raise CombiError('CSRF_REQUIRED', 'La sesión ha cambiado. Recarga la página antes de continuar.', 403)

    def read_center():
        return store.read_center(db_path, session.get('user_id',''))

    def response_page(result=None, error='', status=200, submitted=None, review=None):
        try:
            center = read_center()
        except CombiError as exc:
            error, status = str(exc), exc.status
            center = {'capabilities':{'plan':'FREE','can_build':False,'can_suggest':False,'max_legs':0},
                      'candidates':[], 'blocked':[], 'saved':[], 'sample_limit':200, 'signed_in':False}
        submitted = submitted if isinstance(submitted, dict) else {}
        selected = submitted.get('pick_ids') or []
        if isinstance(selected, str):
            selected = selected.split(',')
        selected = list(dict.fromkeys(p for p in selected[:200] if isinstance(p, str) and 0 < len(p) <= 180)) if isinstance(selected, list) else []
        if not submitted and result:
            selected = [p['id'] for p in result['legs']]
        entry_message = ''
        target_ids = set()
        if not submitted and not result:
            raw_pick = request.args.get('pick', '')
            raw_match = request.args.get('match_id', '')
            target_pick = raw_pick if len(raw_pick) <= 180 else ''
            target_match = raw_match if len(raw_match) <= 180 else ''
            if raw_pick:
                targeted = [p for p in center['candidates'] if target_pick and p['id'] == target_pick]
                selected = [p['id'] for p in targeted]
                entry_message = ('Selección marcada para revisar; todavía no se ha guardado ninguna combinada.'
                                 if targeted else 'La selección de este enlace no está disponible para combinar en esta lectura.')
            elif raw_match:
                targeted = [p for p in center['candidates'] if target_match and p['match_id'] == target_match]
                selected = [targeted[0]['id']] if len(targeted) == 1 else []
                entry_message = ('Este partido tiene varias selecciones disponibles. Elige solo una.' if len(targeted) > 1
                                 else 'Selección marcada para revisar; todavía no se ha guardado ninguna combinada.' if targeted
                                 else 'Este partido no tiene selecciones elegibles en esta lectura.')
            else:
                targeted = []
            target_ids = {p['id'] for p in targeted}
        # Keep the requested option visible. Never discard the other candidates or
        # perform a new provider lookup just to populate this entry point.
        first = set(selected) | target_ids
        center['candidates'] = sorted(center['candidates'], key=lambda p: p['id'] not in first)
        known = {p['id'] for p in center['candidates']}
        state = {'selected': selected, 'stake': str(submitted.get('stake', (result or {}).get('stake', '0,10')))[:32],
                 'count': str(submitted.get('count', request.args.get('partidos', '3')))[:2],
                 'risk': str(submitted.get('risk', 'conservador'))[:20],
                 'date': str(submitted.get('date', ''))[:10],
                 'unavailable': [pid for pid in selected if pid not in known],
                 'entry_message': entry_message,
                 'expand_more': any(p['id'] in first for p in center['candidates'][6:])}
        return render_template('combis.html', data={}, center=center, preview=result, error=error,
                               form_state=state, review=review, request_id=uuid.uuid4().hex), status

    @bp.route('/combinadas', methods=['GET','POST'])
    def page():
        if request.method == 'GET':
            if request.args.get('borrador'):
                try:
                    review = review_draft(db_path, session.get('user_id', ''), request.args['borrador'])
                    submitted = {'pick_ids': [p['id'] for p in review['comparisons']], 'stake': review['stake']}
                    return response_page(review['preview'], review=review, submitted=submitted)
                except CombiError as exc:
                    return response_page(error=exc.message, status=exc.status)
            return response_page()
        data = {}
        try:
            data = values(); mutation_guard(data)
            if data.get('action') == 'save':
                store.save_draft(db_path,session['user_id'],data)
                return redirect('/combinadas?guardado=1#combinadas-guardadas',code=303)
            result = store.make_preview(db_path,session['user_id'],data)
            return response_page(result, submitted=data)
        except CombiError as exc:
            return response_page(error=exc.message,status=exc.status,submitted=data)

    @bp.get('/api/client/combinadas')
    def collection():
        try:
            if not session.get('user_id'):
                raise CombiError('AUTH_REQUIRED','Inicia sesión para consultar tus borradores.',401)
            result = read_center()
            return jsonify({'ok':True, 'combis':[d['payload'] for d in result['saved'] if not d['locked']], **result})
        except CombiError as exc:
            return jsonify({'ok':False,'error':exc.code,'message':exc.message}), exc.status

    def mutation(save=False):
        try:
            data = values(); mutation_guard(data)
            result = (store.save_draft if save else store.make_preview)(db_path,session['user_id'],data)
            return jsonify({'ok':True,'combi':result,'contract':CONTRACT}), (201 if save and not result.get('replayed') else 200)
        except CombiError as exc:
            return jsonify({'ok':False,'error':exc.code,'message':exc.message}), exc.status

    @bp.post('/api/client/combinadas/preview')
    def preview_api():
        return mutation()

    @bp.post('/api/client/combinadas/save')
    def save_api():
        return mutation(save=True)

    @bp.get('/api/client/combinadas/<draft_id>/review')
    def review_api(draft_id):
        try:
            result = review_draft(db_path, session.get('user_id', ''), draft_id)
            return jsonify({'ok': True, 'review': result})
        except CombiError as exc:
            return jsonify({'ok': False, 'error': exc.code, 'message': exc.message}), exc.status

    @bp.get('/api/shark/combi-advice')
    def advice_api():
        try:
            result = store.read_advice(db_path, session.get('user_id',''),
                     pick_id=request.args.get('pick',''),match_id=request.args.get('match_id',''))
            return jsonify({'ok':True,'advice':result})
        except CombiError as exc:
            return jsonify({'ok':False,'error':exc.code,'message':exc.message}), exc.status

    def advice_for_template(pick_id='', match_id=''):
        cache = getattr(g, 'combi_advice_cache', {})
        lookup = (str(pick_id),str(match_id),str(session.get('user_id','')))
        if lookup not in cache:
            try:
                cache[lookup] = store.read_advice(db_path, lookup[2],pick_id=lookup[0],match_id=lookup[1])
            except CombiError as exc:
                cache[lookup] = {'error':exc.message}
            g.combi_advice_cache = cache
        return cache[lookup]

    @bp.app_context_processor
    def template_helpers():
        return {'combi_advice': advice_for_template}

    @bp.after_app_request
    def private_responses(response):
        if request.path in {'/combis','/combinadas','/api/combis','/api/combis/build','/api/shark/combi-advice','/api/shark/ask','/shark'} or request.path.startswith('/api/client/combinadas'):
            response.headers['Cache-Control'] = 'private, no-store'
            response.vary.add('Cookie')
        return response

    def widget_reply(data):
        question = str(data.get('question') or data.get('q') or '')[:1000]
        number = re.search(r'\b(\d{1,3})\s*(?:partidos?|selecciones?|eventos?)\b', question, re.I) or re.search(r'\bcombi(?:nada)?\s+(?:de|con)\s+(\d{1,3})\b', question, re.I)
        count = int(number.group(1)) if number else 3
        risk = 'agresivo' if 'agresiv' in question.lower() else 'equilibrado' if 'equilibrad' in question.lower() else 'conservador'
        explicit_date = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', question)
        day = datetime.now(ZoneInfo('Europe/Madrid')).date()
        target_date = explicit_date.group(1) if explicit_date else (day+timedelta(days=1)).isoformat() if 'mañana' in question.lower() else day.isoformat() if re.search(r'\bhoy\b',question,re.I) else ''
        try:
            if request.method == 'POST':
                token = request.headers.get('X-CSRF-Token') or request.headers.get('X-CSRFToken') or data.get('csrf_token')
                if not validate_csrf(session, token):
                    raise CombiError('CSRF_REQUIRED', 'Recarga la página para renovar la sesión.', 403)
            result = store.make_preview(db_path, session.get('user_id',''),
                {'mode':'suggest','count':str(count),'risk':risk,'stake':'0.10','date':target_date})
            answer = result['copy_text'] + '\n\n' + '\n'.join(result['warnings'])
            answer += '\nRevisa el borrador desde Combinadas antes de guardarlo. El perfil solo ordena cuotas; no es una predicción.'
        except CombiError as exc:
            if exc.code == 'CSRF_REQUIRED':
                return jsonify({'ok':False,'message':exc.message}), exc.status
            result = None
            answer = exc.message + ' Abre Combinadas para revisar los requisitos y las selecciones disponibles. No he guardado ni apostado nada.'
        return jsonify({'ok':True, 'shark':{'focus':'combis','answer':answer,'next_url':'/combinadas',
                        'actions':[{'label':'Revisar combinadas','href':'/combinadas'}],
                        'context':{'contract':CONTRACT,'preview':result,'external_calls':0},
                        'next_action':'Revisar; no se ha colocado ninguna apuesta.'}})

    @bp.record_once
    def adapt_legacy_routes(state):
        # Adapt three legacy combi entries and the specific widget intent at setup.
        # No duplicate URL rules, before-request interception or runtime rebinding.
        aliases = {'combis_page':('/combis',page), 'api_combis':('/api/combis',collection),
                   'api_combis_build':('/api/combis/build',preview_api)}
        for endpoint,(path,handler) in aliases.items():
            rules = list(state.app.url_map.iter_rules(endpoint)) if endpoint in state.app.view_functions else []
            if rules and any(rule.rule != path for rule in rules):
                raise RuntimeError('Unexpected legacy combi route binding: '+endpoint)
        for endpoint,(path,handler) in aliases.items():
            if endpoint in state.app.view_functions:
                state.app.view_functions[endpoint] = handler
        original_ask = state.app.view_functions.get('api_shark_ask')
        if original_ask:
            if any(rule.rule != '/api/shark/ask' for rule in state.app.url_map.iter_rules('api_shark_ask')):
                raise RuntimeError('Unexpected legacy SHARK route binding')
            def ask_adapter():
                if request.content_length is not None and request.content_length > 65536:
                    return jsonify({'ok':False,'message':'El mensaje es demasiado grande.'}), 413
                data = request.get_json(silent=True) if request.is_json else dict(request.form or request.args)
                data = data if isinstance(data, dict) else {}
                question = str(data.get('question') or data.get('q') or '')[:1000]
                if re.search(r'\bcombi(?:nada)?s?\b',question,re.I):
                    return widget_reply(data)
                return original_ask()
            state.app.view_functions['api_shark_ask'] = ask_adapter
        state.app.extensions['nemesis_combi_routes'] = {'contract':CONTRACT,'legacy_build_is_preview_only':True}

    return bp
