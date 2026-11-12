# Éditeur conversationnel Focus

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Description historique de l'éditeur Prompt Toolkit/curses. Le lanceur actuel privilégie l'interface Textual ; ce document ne décrit pas sa saisie ni ne vaut recette.

`FocusEditor` est l'éditeur par défaut de `FocusExtensions` et du lancement normal dans cette branche d'intégration. Il est inclus dans les manifestes d'installation. Aucun stockage n'est activé ; l'historique est en mémoire, initialisable par le constructeur.
Le composant `FocusEditor` est injectable par `FocusExtensions(editor=FocusEditor())`. Entrée soumet ; Ctrl+N ou Alt+Entrée insère une ligne quand le terminal transmet la touche. Les flèches déplacent le curseur ; haut/bas accèdent à l'historique aux limites du texte. Home/End et Ctrl+A/E vont au début/à la fin de la ligne ; Retour arrière et Suppr effacent. Ctrl+Espace étend un préfixe au préfixe commun des suggestions ; `suggestions()` expose toutes les propositions et accepte des fournisseurs injectés.

Les événements `SHIFT_LEFT`, `SHIFT_RIGHT`, `SHIFT_UP`, `SHIFT_DOWN`, `SHIFT_HOME`, `SHIFT_END`, `SHIFT_CTRL_HOME`, `SHIFT_CTRL_END`, `SHIFT_ALT_LEFT` et `SHIFT_ALT_RIGHT` étendent la sélection. Elle est délimitée visuellement par ⟦ et ⟧, sans modification du texte. `selection` expose ses bornes et `copy_selection()` copie le texte dans `clipboard`. La saisie ou la suppression remplace la sélection. Ctrl+C reste réservé au contrôleur. Ces événements symboliques et `COPY_SELECTION` doivent être transmis explicitement par le contrôleur ; leur disponibilité dépend du terminal.

L'éditeur accepte les événements symboliques `SHIFT_ENTER`, `CTRL_HOME`, `CTRL_END`, `ALT_LEFT`, `ALT_RIGHT`, et les délimiteurs de collage `\x1b[200~` et `\x1b[201~`. Le contrôleur active le collage bracketé et reconnaît les séquences xterm de navigation par mots et Ctrl+Home/End lorsque curses les prend en charge ; leur comportement dépend du terminal. Le collage bracketé multiligne a été essayé en PTY ; la navigation par mots reste à essayer sur terminaux réels. Tab reste réservé au changement de région ; Ctrl+Espace lance la complétion non ambiguë. La sélection n'est pas disponible. Un retour à la ligne explicite par Ctrl+N est possible. Aucun historique persistant n'est mis en place.

Le curseur est un index Python dans le texte brut ; `cursor_row` est la ligne visuelle mise à jour par `render_lines`. Les combinants, sélecteurs de variation, modificateurs emoji et séquences ZWJ restent groupés pour les mouvements horizontaux. Il ne s'agit pas d'une segmentation Unicode complète : drapeaux, autres graphèmes et largeur d'emoji varient selon le terminal. Les contrôles sont remplacés visuellement ; le tampon restauré ou collé reste brut. Le rendu enveloppe les longues lignes et le contrôleur cherche à conserver la ligne du curseur visible, y compris sur un petit terminal.
Le collage bracketé convertit CRLF et CR en LF, y compris lorsque les caractères arrivent séparément. Le brouillon et le texte soumis contiennent cette forme normalisée ; les caractères de contrôle sont neutralisés seulement dans le rendu. Les opérations groupent les accents combinants, sélecteurs, modificateurs emoji et séquences ZWJ. La bibliothèque standard ne fournit pas une segmentation complète des graphèmes : drapeaux, certaines écritures et la largeur d'emoji varient selon les terminaux.

L'historique en mémoire préserve le brouillon et les modifications temporaires. `FocusEditor.from_session(session)` charge les messages utilisateur de la session mission 09 uniquement si `history_enabled` est actif. La persistance des nouveaux messages appartient au contrôleur et à la session ; l'éditeur ne la duplique pas. Les suggestions et la copie interne nécessitent un affichage et une commande explicite par l'intégrateur.

Dans le moteur 404cc50, Alt+flèches, Ctrl+Home/End et collage bracketé sont déclarés pour certaines séquences xterm. Le contrôleur doit aussi mapper `ESC [ 1 ; 2 D/C/A/B` vers `SHIFT_LEFT/RIGHT/UP/DOWN`, `ESC [ 1 ; 2 H/F` vers `SHIFT_HOME/END` et prévoir une commande de copie explicite sans utiliser Ctrl+C. Ces séquences dépendent de terminfo et ne garantissent pas tous les terminaux. Qualifier aussi les variantes Shift/Ctrl/Alt et Ctrl+Espace sur Kali, SSH et tmux. La parité UX avec d'autres produits n'est pas démontrée.

Sur le Python 3.14 testé, `curses.define_key` est absent. Le bloc de configuration de `404cc50` abandonne alors l'enregistrement des séquences et l'activation du collage bracketé ; un essai PTY a montré `[200~` et `[201~` insérés dans le texte. Le contrôleur doit décoder les séquences entrantes même sans `define_key`, activer et désactiver le mode bracketé indépendamment de cette fonction, et ne transmettre à l'éditeur que les événements délimités. Les essais du composant avec événements synthétiques ne corrigent pas cette limite terminal.

Le decodeur de sequences du controleur final est independant de curses.define_key. Le mode bracketé est activé séparément.

## Correctifs de recette du contrôleur et des frontières Unicode

Les flèches CSI (`ESC [ A/B/C/D`) et SS3 (`ESC O A/B/C/D`) sont décodées
explicitement, même lorsque ncurses les livre caractère par caractère. Les
préfixes CSI et SS3 reconnus restent en attente entre lectures ; le collage
bracketé conserve ses délimiteurs distincts et son contenu littéral. Escape
isolé reste soumis à un délai de 250 ms : le terminal ne permet pas de distinguer
un appui Escape d'un préfixe dont le caractère suivant arrive au-delà de ce délai.

L'éditeur et le renderer utilisent la même segmentation, y compris les
conjonctions indiciennes GB9c. Le curseur restauré est ramené à une frontière de
graphème ; une insertion reliant deux consonnes ne laisse pas le curseur au
milieu de la conjonction. Déplacements, sélection et suppression utilisent ces
frontières. Le texte source est conservé sans normalisation Unicode NFC/NFD.

Les propriétés Indic_Conjunct_Break sont figées sur Unicode 17.0.0 dans
`focus_view.py`, avec la notice de licence Unicode conservée. Cela ne constitue
pas une implémentation exhaustive de toutes les règles UAX #29 ni une garantie
universelle de largeur des glyphes : la police et le terminal restent déterminants.
Les régressions couvrent notamment devanagari, bengali, télougou, malayalam,
accents combinants, emoji ZWJ avec modificateur, drapeaux et CJK.
