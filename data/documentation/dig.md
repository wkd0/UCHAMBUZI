# dig(1) — note de lecture locale

Synthèse rédigée pour UCHAMBUZI, pas une copie intégrale du manuel.
Consultation locale : 2026-11-07, Ubuntu. Aucune consultation Web.
Manuel BIND 9, Internet Systems Consortium, fourni par bind9-dnsutils
1:9.20.24-1ubuntu0.5; en-tête : 9.20.24-1ubuntu0.5-Ubuntu, 2026-06-08.

Sections examinées : NAME, SYNOPSIS, DESCRIPTION, SIMPLE USAGE, OPTIONS,
EXAMPLES, Author, Copyright.
Le programme interroge un serveur DNS et affiche sa réponse. Sans serveur
explicite, la configuration de résolution locale est utilisée. Le fichier
personnel .digrc peut modifier les options; -r désactive sa lecture.
-q distingue un nom des autres arguments, -t sélectionne le type; A est le
choix par défaut. -x réalise une recherche inverse IPv4 ou IPv6, de type PTR.
-v affiche la version. Une réponse DNS ne prouve ni propriété ni attribution.

Précautions UCHAMBUZI : requête réseau susceptible d'être journalisée par le
résolveur et les serveurs interrogés; ce n'est pas une opération purement passive.
Pour e-mail/URL, seul le domaine ou l'hôte extrait et validé est pertinent : aucune
vérification de boîte ni téléchargement de page n'est impliqué.
Aucune requête DNS n'a été exécutée pour rédiger cette note.
Origine conservée : https://bind9.readthedocs.io/en/latest/manpages.html
Cette URL n'a pas été consultée. La provenance vérifiée est le manuel local.

## Portée de la vérification

La note UCHAMBUZI est une synthèse interne au corpus, pas une documentation
publiée ni approuvée par le mainteneur de l'outil. Le statut « upstream_manual »
qualifie le manuel original identifié par le paquet et ses mentions d'auteur.
La présence d'un fichier ou sa seule empreinte n'établit pas cette qualité.
Les empreintes compressée et décompressée ont été recomparées au fichier local
le 2026-11-07. L'authenticité cryptographique du paquet n'a pas été revérifiée.
La consultation concerne cette copie Ubuntu, pas le contenu actuel de l'URL.
Aucune plage de compatibilité n'est connue par test d'exécution. Seule la version
exactement documentée est reconnue; une autre version exige une nouvelle lecture.
La date de revue 2026-12-07 est un seuil expérimental : avant cette date, « current »
ne signifie pas que le contenu distant a été contrôlé ou qu'aucune mise à jour existe.

Une recommandation pour e-mail/URL nécessite un nouvel indice domaine ou IP
explicitement extrait et validé avant préparation. L'existence d'une fiche DNS ne
certifie aucune commande. Le composant de préparation exige en plus un résolveur,
un type DNS, un périmètre et les restrictions réseau déclarées. Une requête DNS
est une interaction réseau active; « network_query » n'est pas « passive ».
