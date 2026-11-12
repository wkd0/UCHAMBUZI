# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : osint_guardrails.py
# Role          : Consentement, constats et isolation OSINT
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Garde-fous locaux ; aucune transmission ni approbation implicite."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import installation
from conversation import detect_prompt_injection, isolate_untrusted_content

LEGAL_NOTICE = (
    "OSINT sur personnes : documentez la base légale, la finalité et le périmètre "
    "de l'enquête ; respectez la proportionnalité, la minimisation des données et "
    "les droits des personnes. Une source publique ne donne pas une autorisation "
    "générale de collecte ou de réutilisation. Ce rappel ne vaut pas avis juridique."
)
MAX_MODEL_CHARS = 4000

@dataclass(frozen=True)
class Finding:
    valeur: str
    source: str
    outil: str
    horodatage: str
    certitude: str = 'source unique'
    nature: str = 'hypothèse'

    def __post_init__(self):
        for value in (self.valeur, self.source, self.outil):
            if not isinstance(value, str) or not value.strip() or len(value) > 16000:
                raise ValueError('Constat invalide')
        if self.certitude not in ('observé', 'source unique', 'recoupé'):
            raise ValueError('Certitude invalide')
        if self.nature not in ('hypothèse', 'fait'):
            raise ValueError('Nature invalide')
        stamp = datetime.fromisoformat(self.horodatage)
        if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError('Horodatage UTC requis')

    def to_dict(self):
        return asdict(self)

class LegalConsent:
    """Accusé de lecture local versionné, distinct de tout accord réseau."""
    def __init__(self, root):
        self.path = Path(root) / 'config' / 'osint-consent.json'

    def acknowledged(self):
        installation.no_links(self.path)
        if not self.path.exists():
            return False
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return data.get('notice_sha256') == hashlib.sha256(LEGAL_NOTICE.encode()).hexdigest() and data.get('acknowledged') is True
        except (ValueError, AttributeError):
            return False

    def first_use(self, display, acknowledge):
        if self.acknowledged():
            return False
        display(LEGAL_NOTICE)
        if acknowledge() is True:
            installation.no_links(self.path)
            installation.private_directory(self.path.parent)
            installation.atomic_write(self.path, json.dumps({
                'acknowledged': True,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'notice_sha256': hashlib.sha256(LEGAL_NOTICE.encode()).hexdigest(),
            }).encode(), 0o600)
        return True

def activity_notice(activity):
    if activity not in ('passive', 'active'):
        raise ValueError('Niveau passif/actif requis avant approbation')
    return 'Niveau OSINT : ' + {'passive': 'passif', 'active': 'actif'}[activity]

def model_evidence(content, *, source, kind='tool', max_chars=MAX_MODEL_CHARS):
    """Inspecte tout le contenu, puis borne le conteneur JSON destiné au modèle.

    Aucun résumé génératif : extrait déterministe. Une détection retire le corps.
    Le résultat entier est limité, marqueurs et métadonnées compris.
    """
    if kind not in ('tool', 'web', 'profile') or not isinstance(content, str) or not isinstance(source, str):
        raise ValueError('Source externe invalide')
    if type(max_chars) is not int or not 1024 <= max_chars <= MAX_MODEL_CHARS:
        raise ValueError('Budget modèle invalide')
    patterns = detect_prompt_injection([source, content])
    envelope = isolate_untrusted_content('source mise en quarantaine' if patterns else source[:200], '' if patterns else content[:max_chars])
    envelope.update(kind=kind, detected_patterns=patterns,
                    prompt_injection_detected=bool(patterns),
                    sha256=hashlib.sha256(content.encode()).hexdigest(),
                    truncated=len(content) > max_chars, quarantined=bool(patterns))
    while True:
        wire = json.dumps(envelope, ensure_ascii=True, sort_keys=True)
        if len(wire) <= max_chars:
            return wire
        envelope['truncated'] = True
        envelope['isolated_data'] = envelope['isolated_data'][:max(0, len(envelope['isolated_data'])-(len(wire)-max_chars))]
        if not envelope['isolated_data'] and len(json.dumps(envelope, ensure_ascii=True)) > max_chars:
            raise ValueError('Budget insuffisant pour les métadonnées')


def command_activity(tool_id):
    """Classification exclusivement issue du catalogue validé, jamais du modèle."""
    from tools_catalog import load_catalog
    entry = next((item for item in load_catalog() if item['id'] == tool_id), None)
    if entry is None:
        raise ValueError('Commande absente du catalogue OSINT ; approbation refusée')
    return activity_notice(entry['activity'])
