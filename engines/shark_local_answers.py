"""Deterministic, localized readings of admitted SHARK context. No provider IO."""
from __future__ import annotations

import math
import re
import unicodedata


COPY = {
    "header": ("SHARK responde con la información registrada.", "SHARK answers using recorded information.", "SHARK répond avec les informations enregistrées."),
    "pending": ("Pendiente", "Pending", "En attente"),
    "match": ("Partido", "Match", "Match"),
    "competition": ("Competición", "Competition", "Compétition"),
    "time": ("Fecha y hora Madrid", "Date and time in Madrid", "Date et heure de Madrid"),
    "status": ("Estado registrado", "Recorded status", "État enregistré"),
    "score": ("Marcador", "Score", "Score"),
    "minute": ("Minuto confirmado", "Confirmed minute", "Minute confirmée"),
    "no_match": ("No hay un partido seleccionado. Abre una ficha para consultar ese encuentro.", "No match is selected. Open a match page to ask about that fixture.", "Aucun match sélectionné. Ouvrez sa fiche pour consulter cette rencontre."),
    "no_pick": ("No hay un pronóstico publicado permitido en esta selección. SHARK no crea una apuesta artificial.", "No permitted published prediction is selected. SHARK does not fabricate a bet.", "Aucun pronostic publié autorisé sélectionné. SHARK ne fabrique pas de pari."),
    "prediction": ("Pronóstico registrado", "Recorded prediction", "Pronostic enregistré"),
    "market": ("Mercado", "Market", "Marché"),
    "selection": ("Selección", "Selection", "Sélection"),
    "odds": ("Cuota registrada", "Recorded odds", "Cote enregistrée"),
    "stake": ("Stake registrado (unidades)", "Recorded stake (units)", "Mise enregistrée (unités)"),
    "confidence": ("Índice interno registrado (no probabilidad de acierto)", "Recorded internal index (not a win probability)", "Indice interne enregistré (pas une probabilité de réussite)"),
    "risk": ("Riesgo registrado", "Recorded risk", "Risque enregistré"),
    "reason": ("Motivo registrado", "Recorded reasoning", "Motif enregistré"),
    "wait": ("Si faltan datos, cuota o una selección publicada, espera; no fuerces una apuesta.", "If data, odds or a published selection are missing, wait; do not force a bet.", "Si les données, la cote ou la sélection publiée manquent, attendez ; ne forcez pas un pari."),
    "unavailable": ("No se ha podido confirmar esta lectura local. Consulta la sección correspondiente; no equivale a cero partidos.", "This local reading could not be confirmed. Check the corresponding section; this does not mean zero matches.", "Cette lecture locale n’a pas pu être confirmée. Consultez la rubrique correspondante ; cela ne signifie pas zéro match."),
    "live_empty": ("No hay directos confirmados en esta lectura local. No acredita la ausencia de partidos en otros proveedores.", "There are no confirmed live matches in this local reading. This does not establish that other providers have none.", "Aucun direct confirmé dans cette lecture locale. Cela ne prouve pas l’absence de matchs chez d’autres fournisseurs."),
    "stale": ("Hay observaciones antiguas excluidas del directo; no se presentan como actuales.", "Old observations have been excluded from live results; they are not presented as current.", "Des observations anciennes sont exclues du direct ; elles ne sont pas présentées comme actuelles."),
    "live_count": ("Directos confirmados en esta lectura: {count}.", "Confirmed live matches in this reading: {count}.", "Directs confirmés dans cette lecture : {count}."),
    "agenda_count": ("Partidos disponibles en esta lectura: {count}.", "Matches available in this reading: {count}.", "Matchs disponibles dans cette lecture : {count}."),
    "favorites_empty": ("Todavía no tienes favoritos guardados. Puedes elegirlos en Favoritos.", "You have no saved favorites yet. Choose them in Favorites.", "Vous n’avez pas encore de favoris enregistrés. Choisissez-les dans Favoris."),
    "favorites_no_matches": ("Tus favoritos están guardados, pero esta lectura no contiene encuentros asociados.", "Your favorites are saved, but this reading contains no associated fixtures.", "Vos favoris sont enregistrés, mais cette lecture ne contient aucune rencontre associée."),
    "favorites_count": ("Partidos asociados a tus favoritos en esta lectura: {count}.", "Matches associated with your favorites in this reading: {count}.", "Matchs associés à vos favoris dans cette lecture : {count}."),
    "more": ("Se muestran hasta seis encuentros. Abre la sección para ver el resto.", "Up to six fixtures are shown. Open the section to see the rest.", "Jusqu’à six rencontres sont affichées. Ouvrez la rubrique pour voir la suite."),
    "plan": ("Tu plan efectivo: {plan}.", "Your effective plan: {plan}.", "Votre offre effective : {plan}."),
    "allowance": ("Consultas SHARK hoy: {used}/{limit}; disponibles: {remaining}.", "SHARK questions today: {used}/{limit}; remaining: {remaining}.", "Questions SHARK aujourd’hui : {used}/{limit} ; restantes : {remaining}."),
    "picks_limit": ("Límite configurado de pronósticos diarios: {count}. No garantiza que existan pronósticos publicables.", "Configured daily prediction limit: {count}. This does not guarantee publishable predictions exist.", "Limite configurée de pronostics quotidiens : {count}. Cela ne garantit pas l’existence de pronostics publiables."),
    "combi_limit": ("Límite configurado de partidos por combinada: {count}.", "Configured fixtures per accumulator limit: {count}.", "Limite configurée de matchs par combiné : {count}."),
    "telegram": ("Consultar Telegram aquí no envía mensajes ni modifica tu conexión. Revisa su estado y permisos en la sección Telegram.", "Asking about Telegram here does not send messages or change your connection. Check its status and permissions in Telegram.", "Consulter Telegram ici n’envoie aucun message et ne modifie pas votre connexion. Vérifiez son état et ses permissions dans Telegram."),
    "summary": ("Puedes consultar el calendario, los directos confirmados, tus favoritos, un pronóstico autorizado o los límites de tu plan.", "You can ask about the calendar, confirmed live matches, your favorites, an authorized prediction or your plan limits.", "Vous pouvez consulter le calendrier, les directs confirmés, vos favoris, un pronostic autorisé ou les limites de votre offre."),
    "legal": ("Información deportiva con límites: no garantiza resultados. Los datos ausentes permanecen pendientes.", "Sports information with limitations: results are not guaranteed. Missing data stays pending.", "Informations sportives avec limites : aucun résultat garanti. Les données absentes restent en attente."),
}


def intent(question):
    text = unicodedata.normalize("NFKD", str(question)).encode("ascii", "ignore").decode().lower()
    for name, words in (
        ("risk", ("riesgo", "peligro", "risk", "risque", "evitar")),
        ("favorites", ("favorito", "favoritos", "favorite", "favorites", "favourite", "favourites", "favoris")),
        ("telegram", ("telegram",)),
        ("membership", ("plan", "planes", "membership", "membresia", "abonnement", "offre", "free", "pro", "elite")),
        ("pick", ("pick", "picks", "pronostico", "pronosticos", "pronostic", "pronostics", "prediction", "predictions", "apuesta", "bet", "selection")),
        ("live", ("directo", "directos", "live", "direct")),
        ("agenda", ("calendario", "calendar", "calendrier", "partidos", "matches", "matchs", "fixtures")),
        ("match", ("partido", "match", "equipo", "team", "equipe")),
    ):
        if any(re.search(r"\b" + word + r"\b", text) for word in words):
            return name
    return "summary"


def render(question, context):
    locale = context.get("locale")
    column = {"en": 1, "fr": 2}.get(locale, 0)
    def text(key, **values):
        return COPY[key][column].format(**values)
    def value(item, *keys):
        for key in keys:
            raw = item.get(key)
            if raw is not None and str(raw).strip():
                return str(raw).strip()
        return text("pending")
    def count(raw):
        return type(raw) is int and raw >= 0
    def number(raw):
        return type(raw) in (int, float) and math.isfinite(raw)
    def match_lines(item, *, live=False):
        lines = [text("match") + ": " + value(item, "home_team") + " vs " + value(item, "away_team"),
                 text("competition") + ": " + value(item, "competition_name", "league_name"),
                 text("time") + ": " + value(item, "client_full_datetime_label", "kickoff_iso", "match_date")]
        frame = item.get("realtime_state") or {}
        verified = frame.get("contract") == "NEMESIS-REALTIME-STATE-V1"
        stale = frame.get("is_stale") or frame.get("status_conflict")
        statuses = {
            "LIVE": ("En directo", "Live", "En direct"), "HALFTIME": ("Descanso", "Half-time", "Mi-temps"),
            "FINISHED": ("Finalizado", "Finished", "Terminé"), "ARCHIVED": ("Finalizado", "Finished", "Terminé"),
            "UPCOMING": ("Programado", "Scheduled", "Programmé"), "POSTPONED": ("Aplazado", "Postponed", "Reporté"),
            "SUSPENDED": ("Suspendido", "Suspended", "Suspendu"), "CANCELLED": ("Cancelado", "Cancelled", "Annulé"),
            "ABANDONED": ("Abandonado", "Abandoned", "Abandonné")}
        status = statuses.get(frame.get("status_canonical")) if verified and not stale else None
        lines.append(text("status") + ": " + (status[column] if status else text("pending")))
        # Both intents use exactly the same canonical score. A rejected explicit
        # pair must never fall back to an unrelated/stale display score string.
        pair_valid = verified and not stale and all(type(frame.get(k)) is int and frame[k] >= 0 for k in ("score_home", "score_away"))
        score = str(frame["score_home"]) + "–" + str(frame["score_away"]) if pair_valid else text("pending")
        lines.append(text("score") + ": " + score)
        if live or (verified and frame.get("is_live") is True and not stale):
            lines.append(text("minute") + ": " + value(frame, "minute"))
        if stale:
            lines.append(text("stale"))
        return "\n".join(lines)

    focus = intent(question)
    lines = [text("header")]
    match, pick = context.get("match") or {}, context.get("pick") or {}
    collections = context.get("collections") or {}
    if focus in ("live", "agenda", "favorites"):
        collection = collections.get(focus) or {}
        state = collection.get("state")
        matches = collection.get("matches") or []
        if focus == "live":
            confirmed = [item for item in matches if (item.get("realtime_state") or {}).get("contract") == "NEMESIS-REALTIME-STATE-V1"
                         and (item.get("realtime_state") or {}).get("is_live") is True
                         and (item.get("realtime_state") or {}).get("is_stale") is False
                         and not (item.get("realtime_state") or {}).get("status_conflict")]
            if len(confirmed) != len(matches):
                state = "UNAVAILABLE"
            matches = confirmed
        if state not in ("AVAILABLE", "EMPTY", "NO_MATCHES"):
            lines.append(text("unavailable"))
        elif focus == "favorites" and state == "EMPTY":
            lines.append(text("favorites_empty"))
        elif focus == "favorites" and state == "NO_MATCHES":
            lines.append(text("favorites_no_matches"))
        elif focus == "live" and not matches:
            lines.append(text("live_empty"))
        else:
            total = collection.get("total")
            if count(total):
                lines.append(text(focus + "_count", count=total))
            for item in matches[:6]:
                frame = item.get("realtime_state") or {}
                if focus == "live" and (frame.get("contract") != "NEMESIS-REALTIME-STATE-V1" or frame.get("is_live") is not True or frame.get("is_stale") or frame.get("status_conflict")):
                    continue
                lines.append(match_lines(item, live=focus == "live"))
            if count(total) and total > len(matches[:6]):
                lines.append(text("more"))
        if focus == "live" and collection.get("stale_excluded"):
            lines.append(text("stale"))
    elif focus == "membership":
        plan = context.get("plan") or {}
        membership = plan.get("membership") or (context.get("user") or {}).get("membership") or "FREE"
        lines.append(text("plan", plan=membership))
        usage, limits = plan.get("usage") or {}, plan.get("limits") or {}
        if all(count(usage.get(k)) for k in ("used", "limit", "remaining")):
            lines.append(text("allowance", **{k: usage[k] for k in ("used", "limit", "remaining")}))
        for key, label in (("daily_picks", "picks_limit"), ("combi_matches", "combi_limit")):
            if count(limits.get(key)):
                lines.append(text(label, count=limits[key]))
    elif focus in ("pick", "risk"):
        if not pick:
            lines.append(text("no_pick"))
        else:
            lines.append(text("prediction") + ": " + value(pick, "home_team") + " vs " + value(pick, "away_team"))
            for key, label in (("market", "market"), ("client_selection_label", "selection"), ("odds", "odds"), ("stake_units", "stake"), ("confidence", "confidence"), ("risk_level", "risk"), ("reasoning", "reason")):
                raw = pick.get(key)
                if key == "client_selection_label":
                    rendered = value(pick, key, "selection_display", "selection")
                elif key in ("odds", "stake_units", "confidence"):
                    rendered = str(raw) if number(raw) and (key != "odds" or raw > 1) else text("pending")
                else:
                    rendered = value(pick, key)
                lines.append(text(label) + ": " + rendered)
        lines.append(text("wait"))
    elif focus == "telegram":
        lines.append(text("telegram"))
    elif focus == "match":
        lines.append(match_lines(match) if match else text("no_match"))
    else:
        lines.append(text("summary"))
        for key in ("agenda", "live"):
            collection = collections.get(key) or {}
            if collection.get("state") in ("AVAILABLE", "EMPTY") and count(collection.get("total")):
                lines.append(text(key + "_count", count=collection["total"]))
        if match:
            lines.append(match_lines(match))
    lines.append(text("legal"))
    return {"focus": focus, "answer": "\n\n".join(lines)}
