# Model benchmark

Small, indicative comparison of local models for the agent's recon-and-report
task, run against the lab target (Metasploitable 2). Three runs per model.

| Model | Runs OK | Accuracy | Avg time | Notes |
|-------|---------|----------|----------|-------|
| qwen2.5:7b | 3/3 | No factual errors | ~26 s | Selected. Most reliable. |
| llama3.1:8b | 2/3 | 1 empty report; invented CVEs once | ~23 s | Thorough when it works, unstable. |
| mistral:7b | 2/3 | Misattributed service versions; 1 crash | ~22 s | Fastest, least reliable. |

## Method
Same target, same system prompt, only `--model` changes. Timed with `time`.
The nmap scan (~12 s) is constant across runs, so time differences reflect the
model's reasoning, not the scan.

## Verdict
`qwen2.5:7b` — for a security tool, accuracy and stability outweigh a few
seconds of speed. It never produced wrong information or crashed.

> Caveat: three runs per model is indicative, not statistically rigorous; LLM
> output varies between runs.

## Mise à jour 08/11 — comparatif modèles sur l'agent complet (8 Go VRAM, RTX 4060)
Mesuré sur une mission complète (recon+exploit+post-exploit), mode -y, cible Metasploitable2 :

| Modèle | Temps | Fiabilité | Note |
|---|---|---|---|
| qwen3:8b + thinking | ~174 s | OK | raisonnement complet |
| **qwen3:8b + no-think** | **~107 s** | OK | raisonnement complet, propre — RETENU |
| qwen3.5:9b + thinking | ~85 s | ÉCHEC | JSON cassé, aucun rapport |
| qwen3.5:9b + no-think | ~72 s | moyen | marche mais champs "thought" vides |

Décision : **qwen3:8b par défaut, thinking désactivé par défaut** (flag `--think` pour
le réactiver). qwen3.5:9b écarté : trop instable (le thinking casse le JSON) ou trop
pauvre en traces (no-think). qwen2.5:7b reste dispo via --model.
Ajouts code : chrono total en fin de run ; `--think` ; garde-fou `think:false` (retiré
et réessayé si le modèle ne le supporte pas, pour ne pas casser les modèles non pensants).
