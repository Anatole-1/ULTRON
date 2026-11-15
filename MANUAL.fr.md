# ULTRON — Manuel d'utilisation (Français)

> 🇬🇧 English version: [MANUAL.md](MANUAL.md)

ULTRON est un **agent de pentest autonome**. Vous lui donnez une IP cible et il
mène toute la mission seul : reconnaissance → attaque de credentials →
exploitation → post-exploitation en lecture seule → rapport.

**Positionnement honnête.** ULTRON est d'abord un **orchestrateur déterministe**
borné par un scope déclaré. Un LLM local est un **cerveau optionnel** qui n'aide
que sur l'*inconnu*. Le travail fiable est fait par le playbook déterministe ; le
LLM est un bonus, pas une obligation.

---

## ⚠️ 1. Autorisation & scope — À LIRE EN PREMIER

ULTRON n'agit QUE sur des cibles listées dans un **fichier de scope**
(`scope.txt`). C'est vérifié **dans chaque outil** (nmap, enum, SMB, hydra,
exploit, post-exploit, shell) — une cible hors scope est refusée, même en mode
autonome.

- Ne testez que des machines que vous **possédez** ou pour lesquelles vous avez
  une **autorisation écrite explicite**.
- Utilisez un **labo isolé**. Attaquer un tiers sans accord est **illégal**
  (en France : art. 323 du Code pénal).
- La cible vient **toujours de la ligne de commande** ; l'agent ignore toute IP
  que le LLM pourrait suggérer (anti-hallucination).

---

## 2. Prérequis

Sur la machine Kali/Linux qui exécute l'agent :

- **Python 3** et la bibliothèque `requests`.
- **nmap**, **Metasploit** (`msfconsole`), **hydra**, **john** (John the Ripper),
  **netexec** (`nxc`) — standards sur Kali.
- (Optionnel, seulement pour les modes LLM) un serveur **Ollama** joignable sur le
  réseau, p. ex. avec le modèle `qwen3:8b`.

Vérifier ce qui est présent :

```bash
for t in python3 nmap msfconsole hydra john nxc; do command -v $t >/dev/null && echo "$t OK" || echo "$t MANQUANT"; done
```

---

## 3. Préparation (première fois)

Créez votre fichier de scope et mettez-y la/les IP cible(s) (une par ligne) :

```bash
cd ~/ia-pentest-autonome && printf '192.168.56.101\n' > scope.txt
```

`scope.txt` est ignoré par git (local uniquement). Ajoutez chaque IP autorisée.

Si vous utilisez un environnement virtuel Python :

```bash
cd ~/ia-pentest-autonome && python3 -m venv venv && source venv/bin/activate && pip install requests
```

---

## 4. Démarrage rapide

Remplacez `192.168.56.101` par votre cible (dans le scope) dans tous les exemples.

**Reconnaissance seule, sans attaque, sans LLM** (le run le plus sûr pour commencer) :

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast -y
```

**Attaque déterministe complète** (active l'exploitation) :

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit -y
```

**Attaque complète + shell interactif root/SYSTEM** quand il tombe :

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit --shell
```

---

## 5. Les trois modes

| Mode | Flag | LLM requis ? | Ce qu'il fait |
|---|---|---|---|
| **Déterministe** | `--fast` | Non | Le playbook seul. Rapide, fiable, reproductible. Le défaut recommandé. |
| **Hybride** | `--hybrid` | Oui | Le playbook pilote, et le LLM n'est consulté **que quand le playbook n'a plus de coup connu** (l'« inconnu »). Le meilleur des deux. |
| **LLM d'abord** | *(ni `--fast` ni `--hybrid`)* | Oui | Le LLM pilote chaque étape. Mode historique ; plus lent et moins fiable avec un petit modèle local. |

> Règle simple : **`--fast`** pour les démos et les cibles connues, **`--hybrid`**
> quand vous voulez que l'agent tente de raisonner sur des services sans règle
> intégrée.

---

## 6. Options de la ligne de commande

```
python3 agent.py <ip-cible> [options]
```

| Option | Défaut | Signification |
|---|---|---|
| `target` | — | IP cible (doit être dans le scope). Positionnel, obligatoire. |
| `-s`, `--scope` | `scope.txt` | Chemin du fichier de scope. |
| `-H`, `--host` | `$OLLAMA_HOST` ou `http://localhost:11434` | URL du serveur Ollama (modes LLM/hybride). |
| `-m`, `--model` | `qwen3:8b` | Nom du modèle LLM sur le serveur Ollama. |
| `--max-steps` | `8` | Nb max d'étapes de raisonnement (le playbook `--fast`/`--hybrid` relève son propre plancher pour que les cibles chargées finissent). |
| `--exploit` | off | **Active l'exploitation.** Off par défaut — reco/enum/credentials tournent quand même sans. |
| `--shell` | off | Après un exploit réussi, vous rend un **shell interactif root/SYSTEM** (terminal interactif seulement). |
| `--guided` | off | Valider ou rediriger **chaque action** avant exécution (interactif). En `--hybrid`, vous validez chaque suggestion du LLM. |
| `--fast` | off | Playbook déterministe seul — **aucun LLM, pas besoin d'Ollama**. |
| `--hybrid` | off | Playbook déterministe + secours LLM sur l'inconnu (nécessite Ollama). |
| `--wordlist` | `builtin` | Niveau de liste de credentials : `builtin` (petite liste labo rapide), `common` (liste de John), `rockyou` (plafonnée pour hydra, complète pour john). |
| `-y`, `--yes` | off | Tout auto-approuver ; ne jamais s'arrêter (runs sans surveillance). |
| `--think` | off | Laisser le modèle raisonner en interne (plus lent, plus riche ; modes LLM). |

---

## 7. Ce que fait l'agent (le playbook)

En `--fast` / `--hybrid`, la logique déterministe choisit la prochaine action
selon l'état, dans cet ordre :

1. **nmap** — scanne la cible (`-Pn -sV`, donc les hôtes qui bloquent l'ICMP sont
   quand même vus).
2. **smb_enum** — si SMB (139/445) est ouvert, lance le set NSE Windows
   (`smb-os-discovery`, signature SMB, partages, sessions, `smb-vuln-ms17-010`).
3. **win_exploit** — si MS17-010 est signalé vulnérable *et* que `--exploit` est
   actif, obtient un **shell SYSTEM sans credentials** (MS17-010 via named pipe).
4. **nxc_spray** — si `--exploit` est actif, pulvérise des credentials SMB faibles
   par défaut ; sur un login admin valide, liste les partages et lance une
   collecte Windows en lecture seule.
5. **exploit** — si un service ouvert matche un module Metasploit vérifié de
   l'allow-list (vsftpd, Samba usermap, ProFTPD, Samba trans2open) et que
   `--exploit` est actif, l'exécute et collecte des preuves en lecture seule.
6. **hydra** — brute-force des services d'authentification ouverts (ftp, ssh,
   telnet, mysql, postgres).
7. **reuse** — rejoue chaque credential trouvé contre les autres services d'auth.
8. (hybride seulement) **secours LLM** — quand rien de ce qui précède ne
   s'applique, demande au LLM une action supplémentaire de l'allow-list (p. ex.
   énumérer un port inhabituel).
9. **finish** — écrit le rapport.

L'agent arrête d'exploiter dès qu'il a un shell (il ne martèle pas la machine).

---

## 8. Recettes

**Liste de mots de passe plus grosse** (opt-in, plafonnée pour le brute-force en ligne) :

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit --wordlist rockyou
```

**Run hybride contre un serveur Ollama** (remplacez l'IP du serveur par la vôtre) :

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --hybrid --exploit --host http://192.168.56.10:11434 -y
```

**Hybride + guidé** — l'agent propose, vous décidez (Entrée = accepter, taper une
action pour rediriger, `q` = stop) :

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --hybrid --exploit --host http://192.168.56.10:11434 --guided
```

**Utiliser un modèle plus fort** (s'il est présent sur votre serveur Ollama) :

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --hybrid --exploit --host http://192.168.56.10:11434 --model qwen3.5:9b -y
```

---

## 9. Utiliser le shell interactif (`--shell`)

Quand un exploit tombe et que vous avez passé `--shell`, l'agent vous rend une
session vivante :

- **Windows (MS17-010 / psexec) :** vous arrivez sur `meterpreter >`. Tapez
  `getuid` (affiche `NT AUTHORITY\SYSTEM`), ou `shell` pour un `cmd.exe`. La touche
  Entrée fonctionne normalement.
- **Linux :** vous obtenez une session Meterpreter si l'upgrade réussit, sinon un
  **shell root brut**. Sur un shell brut, l'agent pose un pty automatiquement, mais
  la touche Entrée peut encore envoyer `^M` sans valider — **validez chaque ligne
  avec `Ctrl+J`** (l'agent vous le rappelle à l'écran).

**Pour quitter le shell et laisser l'agent finir :** tapez `exit`, puis `exit -y`
au prompt `msf >`. Votre terminal est restauré automatiquement (`stty sane`).

---

## 10. Rapports et logs

- **Rapport :** un fichier Markdown est écrit dans `reports/<ip>_<horodatage>.md`
  (services ouverts, énumération SMB, credentials, exploitation,
  post-exploitation en lecture seule, analyse).
- **Transcript :** chaque run écrit aussi `logs/<ip>_<horodatage>.log` — tout ce
  qui a défilé dans le terminal, écrit ligne par ligne (survit à un crash). La
  session interactive `--shell` elle-même n'est pas capturée (tty réel).

`reports/` et `logs/` sont ignorés par git.

---

## 11. Étendre ULTRON (ajouter un exploit)

La couverture grandit en ajoutant des modules à l'allow-list. Pour un module
Metasploit, ajoutez une entrée à `MODULES` dans
[exploit_tool.py](exploit_tool.py) avec un `trigger` (la chaîne de service nmap
qui doit le déclencher) :

```python
"ma_cle_module": {
    "module": "exploit/linux/....",
    "payload": "cmd/unix/reverse_perl",
    "desc": "description lisible",
    "trigger": "NomDuService x.y.z",
},
```

C'est le levier le plus efficace pour qu'ULTRON morde sur de nouvelles cibles.

---

## 12. Dépannage

| Symptôme | Cause probable & solution |
|---|---|
| `0 open services` en ~2 s | La VM cible est **éteinte / injoignable**. Vérifiez qu'elle est allumée et sur le même réseau. |
| `ping` échoue mais le scan marche | Normal — beaucoup de VM bloquent l'ICMP. ULTRON utilise `-Pn` partout. |
| `no session` après un exploit | Cible éteinte, ou service capricieux (p. ex. le backdoor vsftpd est quasi usage unique). Relancez ; laissez la VM récupérer entre deux tentatives. |
| `cannot reach the Ollama server` | N'affecte que `--hybrid` / mode LLM. Vérifiez l'URL `--host` et qu'Ollama tourne. Utilisez `--fast` pour vous en passer. |
| Entrée affiche `^M` dans un shell | Shell Linux brut sans pty — **utilisez `Ctrl+J`** pour valider. Si votre terminal reste cassé après la sortie, tapez `stty sane` puis `Ctrl+J`. |
| `REFUSED ... not in scope` | La cible n'est pas dans `scope.txt`. Ajoutez-la (une IP par ligne). |

---

*ULTRON est un projet d'étude, réservé à un usage en labo isolé et autorisé.*
