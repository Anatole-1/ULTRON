# ULTRON — Manuel (Français)

> 🇬🇧 [MANUAL.md](MANUAL.md)

Donnez une IP cible à ULTRON ; il déroule reconnaissance → credentials →
exploitation → post-exploitation en lecture seule → rapport, et peut vous rendre
un shell interactif.

**Labo uniquement.** Il lance de vrais exploits. Ne testez que des machines que
vous possédez ou êtes autorisé à tester — tout autre usage est illégal. Chaque
outil refuse une IP absente de `scope.txt`, et la cible vient toujours de la ligne
de commande.

## Prérequis

`nmap`, `metasploit` (`msfconsole`), `hydra`, `john`, `netexec` (`nxc`), Python 3 +
`requests` — standards sur Kali. Les modes LLM nécessitent en plus un serveur
**Ollama** joignable ; `--fast` ne demande rien de plus.

```bash
for t in python3 nmap msfconsole hydra john nxc; do command -v $t >/dev/null && echo "$t OK" || echo "$t MANQUANT"; done
```

## Préparation

Mettez votre/vos cible(s) autorisée(s) dans `scope.txt`, une IP par ligne :

```bash
cd ~/ia-pentest-autonome && printf '192.168.56.101\n' > scope.txt
```

## Les trois modes

| Mode | Flag | LLM ? | Quand |
|---|---|---|---|
| Déterministe | `--fast` | non | Par défaut. Rapide et fiable sur les services connus. |
| Hybride | `--hybrid` | oui | Le playbook pilote ; le LLM n'est appelé que quand il n'a plus de coup connu. |
| LLM d'abord | *(aucun)* | oui | Le LLM choisit chaque étape. Plus lent, plus faible avec un petit modèle. |

## Démarrage rapide

Remplacez `192.168.56.101` par votre cible.

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast -y
```
Reconnaissance seule (sans exploitation).

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit -y
```
Attaque déterministe complète.

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit --shell
```
Pareil, et vous rend un shell root/SYSTEM interactif quand il tombe.

## Options

| Option | Défaut | Signification |
|---|---|---|
| `target` | — | IP cible (dans le scope). Obligatoire. |
| `--exploit` | off | Active l'exploitation. Reco/creds tournent quand même sans. |
| `--shell` | off | Shell root/SYSTEM interactif après un exploit réussi. |
| `--fast` | off | Playbook déterministe, sans LLM. |
| `--hybrid` | off | Playbook + secours LLM sur l'inconnu (nécessite Ollama). |
| `--guided` | off | Valider ou rediriger chaque action (et chaque suggestion LLM). |
| `--wordlist` | `builtin` | `builtin` / `common` / `rockyou`. |
| `-y` | off | Tout auto-approuver ; ne jamais s'arrêter (runs sans surveillance). |
| `-H`, `--host` | localhost | URL Ollama, p. ex. `http://192.168.56.10:11434`. |
| `-m`, `--model` | `qwen3:8b` | Nom du modèle LLM. |
| `-s`, `--scope` | `scope.txt` | Fichier de scope. |
| `--think` | off | Laisser le modèle raisonner en interne (plus lent). |
| `--max-steps` | 8 | Nb max d'étapes de raisonnement. |

## Ce que fait l'agent

`nmap` → `smb_enum` (si SMB ouvert) → **exploit MS17-010** si vulnérable → **spray**
de credentials SMB → module d'**exploit** si un service matche → **hydra** sur les
services d'auth → **réutilisation** des credentials → (hybride) **secours LLM** sur
ce qui n'est pas géré → rapport. Il arrête d'exploiter dès qu'il a un shell.
`--exploit` conditionne chaque étape offensive ; sans lui, seules reco/énum/creds
tournent.

## Le shell interactif (`--shell`)

- **Windows :** vous arrivez sur `meterpreter >`. Tapez `getuid`
  (`NT AUTHORITY\SYSTEM`) ou `shell` pour un `cmd.exe`. Entrée fonctionne.
- **Linux :** une session Meterpreter, ou un **shell root brut** si l'upgrade
  échoue. Sur un shell brut, si Entrée affiche `^M` au lieu de valider,
  **utilisez `Ctrl+J`**.
- **Sortir :** `exit`, puis `exit -y` au prompt `msf >`. Le terminal est restauré
  automatiquement.

## Rapports & logs

Chaque run écrit un rapport Markdown dans `reports/<ip>_<heure>.md` et un
transcript complet du terminal dans `logs/<ip>_<heure>.log`. Les deux sont ignorés
par git.

## Dépannage

| Symptôme | Solution |
|---|---|
| `0 open services` en ~2 s | Cible éteinte/injoignable — allumez-la, vérifiez le réseau. |
| `ping` échoue mais le scan marche | Normal ; les VM bloquent souvent l'ICMP. ULTRON utilise `-Pn`. |
| `no session` après un exploit | Cible éteinte, ou service capricieux/trop sollicité. Relancez ; laissez la VM récupérer. |
| `cannot reach the Ollama server` | N'affecte que `--hybrid`/LLM. Vérifiez `--host`, ou utilisez `--fast`. |
| Entrée affiche `^M` dans un shell | Shell Linux brut — validez avec `Ctrl+J`. Terminal bloqué après la sortie ? `stty sane` + `Ctrl+J`. |
| `REFUSED ... not in scope` | Ajoutez l'IP dans `scope.txt`. |
