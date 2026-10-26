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
