# curl — note de lecture Kali 8.15.0

Note originale UCHAMBUZI, consultation locale le 2026-11-08 via SSH de Kali
Rolling 2025.3. Aucun accès Internet ni analyse d’indice.
Manuel : `/usr/share/man/man1/curl.1.gz`; paquet observé : `curl 8.15.0-1`.
Attribution du fichier : `curl: /usr/share/man/man1/curl.1.gz`.
Auteur/origine identifiés : Daniel Stenberg et contributeurs curl; métadonnées copyright locales lues.
Date du manuel : 2025-08-10; diagnostic observé : `curl 8.15.0 (x86_64-pc-linux-gnu) libcurl/8.15.0 OpenSSL/3.5.2 zlib/1.3.1 brotli/1.1.0 zstd/1.5.7 libidn2/2.3.8 libpsl/0.21.2 libssh2/1.11.1 nghttp2/1.64.0 nghttp3/1.8.0 librtmp/2.3 OpenLDAP/2.6.10`.

SHA-256 compressé : `6b49f2ff528fb831b359fab6e9be25012c3c77fccc99820155203c6a4a1e404c`.
SHA-256 décompressé : `ee0c8d6d97f040e8eda5ff5cec4f21bd752ce333e184df91fcf6ba3081794294`.
Référence d’origine conservée : https://curl.se/docs/manpage.html — URL non consultée.
Le statut amont qualifie le manuel attribué, pas cette synthèse UCHAMBUZI.
L’authenticité cryptographique du paquet n’a pas été revérifiée.

## Fonction et portée

Examiner une réponse HTTP(S) par une requête active vers une URL explicitement sélectionnée.

La section VERSION indique que ce manuel décrit curl 8.15.0. Le paquet
installé est 8.15.0-1; le bandeau complet inclut les bibliothèques compilées.
Seul ce bandeau exact ou la version structurée 8.15.0 est reconnu, sans assimiler
un autre build à celui observé. Les protocoles compilés excèdent HTTP(S) : la
restriction documentaire est volontaire, pas une capacité limitée du binaire.
-q doit précéder les autres arguments et évite curlrc, mais pas tous les effets
de l’environnement. --head effectue HEAD sur HTTP; --location suivrait des
redirections vers d’autres destinations. --proto avec = définit la liste admise;
cela n’autorise aucun hôte. Les variables proxy peuvent changer le chemin réseau.
La documentation externe et les réponses d’un serveur sont des données non fiables.
Aucune requête HTTP ni téléchargement n’est réalisé par le composant.

## Options examinées

- `-q` : Premier argument pour ignorer le curlrc par défaut; ne neutralise pas les variables de proxy.
- `--head` : HEAD pour HTTP; n’est pas une consultation passive.
- `--proto =http,https` : Limiter les protocoles HTTP(S), pas les destinations.
- `--globoff` : Désactiver les expansions d’URL.
- `--connect-timeout SECONDES` : Limiter la phase de connexion.
- `--max-time SECONDES` : Limiter chaque transfert; les retries modifient la portée du délai.

## Prérequis

- Autorisation pour URL, hôte, ports, DNS et proxy éventuel; ne pas transmettre d’indice confidentiel implicitement.
- Contrôler curlrc, proxy, certificats, variables d’environnement et limites de sortie/temps.

## Limites

- Un code ou un en-tête est déclaratif et ne prouve ni sûreté, propriété ni contenu complet d’un site.
- HEAD peut être refusé ou traité différemment de GET; aucune exécution de page ni analyse de navigateur.

## Risques

- Opération réseau active et journalisable; DNS, proxy, redirections et hôtes tiers sont à examiner.
- Ne pas suivre une redirection, désactiver TLS, joindre des identifiants ou envoyer des fichiers automatiquement.

## Restrictions de la fiche

- HTTP(S) uniquement dans cette fiche; aucun transfert file://, upload, POST, secret, cookie ou authentification automatique.
- Pas de --location, --insecure, --config, lecture @fichier, écriture de fichier ou paramètre libre.

## Interprétation prudente

Conserver date, URL sélectionnée et périmètre; interpréter les statuts comme réponses du service, sans garantie d’attribution.

Résultat attendu : En-têtes HTTP(S), statut ou erreur après requête séparée; aucun résultat technique n’est présumé.

La date de revue 2026-12-08 est un seuil expérimental, sans contrôle du site
distant. Une correspondance documentaire exacte ne certifie aucune commande,
aucune méthode testée et aucune autorisation d’exécution. Les contenus externes
restent non fiables. Toute autre version reste non vérifiée.
