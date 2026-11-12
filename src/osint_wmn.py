# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : osint_wmn.py
# Role          : Recherche asynchrone avec les regles WhatsMyName
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Réseau actif : l'appelant doit recueillir l'approbation de l'enquêteur.

Les erreurs sont indéterminées, jamais des preuves d'absence. Aucun réseau
à l'import. Les règles POST ne sont pas prises en charge.
"""
import asyncio
import http.client
import ipaddress
import json
from pathlib import Path
import socket
from urllib.parse import quote, urlsplit

DATA_PATH = Path(__file__).resolve().parent.parent / 'data/tools/wmn-data.json'
TIMEOUT = 8
MAX_BODY = 2 * 1024 * 1024
CONCURRENCY = 10


def _request(url, headers):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError('URL HTTPS publique requise')
    addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError('Adresse non publique interdite')
    connection = http.client.HTTPSConnection(parts.hostname, timeout=TIMEOUT)
    def connect():
        raw = socket.create_connection(addresses[0][4][:2], timeout=TIMEOUT)
        try:
            connection.sock = connection._context.wrap_socket(raw, server_hostname=parts.hostname)
        except BaseException:
            raw.close()
            raise
    connection.connect = connect
    try:
        connection.request('GET', parts.path + ('?' + parts.query if parts.query else ''), headers=headers)
        response = connection.getresponse()
        body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise ValueError('Réponse trop volumineuse')
        return response.status, body.decode('utf-8', errors='replace')
    finally:
        connection.close()


def _check(rule, username):
    account = quote(username, safe='')
    url = rule['uri_check'].replace('{account}', account)
    result = {'site': rule['name'], 'url': rule.get('uri_pretty', rule['uri_check']).replace('{account}', account), 'exists': False}
    try:
        status, body = _request(url, {'User-Agent': 'UCHAMBUZI/WhatsMyName', **rule.get('headers', {})})
        positive = status == rule['e_code'] and (not rule.get('e_string') or rule['e_string'] in body)
        negative = (bool(rule.get('m_string')) and rule['m_string'] in body) or (rule.get('m_code') != rule['e_code'] and status == rule.get('m_code'))
        result['exists'] = bool(positive and not negative)
        if not positive and not negative:
            result['error'] = 'Réponse indéterminée (HTTP %s)' % status
    except (OSError, ValueError, http.client.HTTPException) as exc:
        result['error'] = str(exc)
    return result


async def check_username_async(username: str, limit: int = 50) -> list[dict]:
    if not isinstance(username, str) or not username.strip() or len(username) > 128 or any(ord(c) < 32 or ord(c) == 127 for c in username):
        raise ValueError('Pseudo invalide')
    if type(limit) is not int or not 0 <= limit <= 1000:
        raise ValueError('Limite attendue entre 0 et 1000')
    if limit == 0:
        return []
    rules = json.loads(DATA_PATH.read_text(encoding='utf-8'))['sites']
    rules = [r for r in rules if not r.get('post_body') and not r.get('disabled') and r['uri_check'].startswith('https://')][:limit]
    semaphore = asyncio.Semaphore(CONCURRENCY)
    async def one(rule):
        async with semaphore:
            return await asyncio.to_thread(_check, rule, username)
    return list(await asyncio.gather(*(one(r) for r in rules)))


def check_username(username: str, limit: int = 50) -> list[dict]:
    """Dans une boucle asyncio existante, utiliser check_username_async."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(check_username_async(username, limit))
    raise RuntimeError('Utiliser await check_username_async dans une boucle asyncio')
