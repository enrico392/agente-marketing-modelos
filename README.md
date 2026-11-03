# Cópia própria dos modelos da locução

Este repositório guarda, nos **releases**, uma cópia dos modelos de voz e de transcrição usados pela skill `video-ads`, para que ela rode **offline, sem Hugging Face e sem login em nenhum site**.

| Pasta no release | Modelo | Licença |
|---|---|---|
| `chatterbox-mtl__*` | Chatterbox Multilingual (Resemble AI) | MIT |
| `whisper-small__*` | Whisper small, formato faster-whisper (OpenAI / Systran) | MIT |

## Criar a cópia (uma vez)
1. Repositório **público** (para a skill baixar sem login).
2. Aba **Actions** → **Espelhar modelos da locução** → **Run workflow**. Leva de 10 a 30 minutos.
3. Ao terminar, aparece o release `chatterbox-mtl-v1` com o `manifesto.json` e os arquivos.

## Usar
Na máquina que renderiza: `LOCUCAO_MODELOS_REPO=<dono>/<este-repositorio> bash locucao/scripts/setup.sh` (dentro da skill). Os modelos ficam em `~/locucao/modelos/` e tudo roda offline.
