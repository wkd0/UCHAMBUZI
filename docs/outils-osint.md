# Outils OSINT de la V1.0.0

`data/tools/catalog.json` est la liste blanche de référence. La fiche `/tools <nom>`
présente version, source, activité et état détecté. Le catalogue distingue les
paquets Kali, six copies embarquées et le moteur natif WhatsMyName.

| Copie embarquée | Version figée | Accès dans la CLI |
| --- | --- | --- |
| gau | 4eabace ; annonce 2.2.4 | `/archive`, `/domaine`, playbooks |
| maigret | 0.6.6-21577cf | `/pseudo`, playbook `email-pseudo` |
| holehe | 1.61-14da70f | `/email` |
| phoneinfoga | 2.11.0 | `/scenario telephone <numéro E.164>` |
| social-analyzer | 0.45-c585f42 | `/pseudo`, playbook `email-pseudo` |
| blackbird | 471ef970 | `/pseudo` |

`/tools setup` ou `/tools install all` prépare les six copies après accord.
Les bundles Python ciblent amd64 et CPython 3.13. L'installateur sélectionne cet
interpréteur même si Python 3.14 est l'interpréteur système. Les wheels sont
installés avec `--no-index` dans des environnements isolés. Aucune récupération
amont implicite. Les binaires Go sont livrés exécutables.

`/tools verify <nom>` vérifie l'artefact source. Lorsqu'un exécutable installé est
résolu, son manifeste est également vérifié : un fichier ajouté ou altéré hors
cache de bytecode bloque la résolution. Une installation altérée n'est pas
remplacée automatiquement. Les versions ne changent qu'avec un catalogue approuvé.

## Limites des parcours

- `/pseudo` propose WhatsMyName, Maigret, Blackbird et Social Analyzer séparément.
- `/email` propose Holehe. Le playbook `email-pseudo` prend un pseudonyme et
  n'envoie plus celui-ci à un outil exigeant une adresse email.
- PhoneInfoga désactive les scanners à clé et la lecture d'un fichier `.env`
  utilisateur. La première étape est locale ; la deuxième produit des liens
  de recherche. Ces liens ne constituent pas des résultats de recherche vérifiés.
- Blackbird utilise `--username`, désactive les mises à jour automatiques et
  bloque les options IA à clé dans son lanceur géré.
- Les outils mixtes sont classés actifs par précaution. Chaque commande
  disponible attend sa confirmation ; les outils absents sont signalés.
- Subfinder, httpx, dnsx, photon, trufflehog, gitleaks n'ont pas d'artefact approuvé
  livré. Waybackurls reste bloqué faute de licence déclarée et n'est pas distribué.
- Les sources publiques peuvent imposer CAPTCHA, authentification, quotas ou
  indisponibilités. Une erreur ou un délai dépassé ne prouve pas l'absence d'indice.

Consulter [THIRD_PARTY](../THIRD_PARTY.md) pour les licences conservées et
[vendor](../vendor/README.uchambuzi.md) pour les révisions et la reconstruction.
Les résultats de qualification du candidat sont dans la [note V1](releases/1.0.0.md).
