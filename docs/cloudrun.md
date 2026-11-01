# Avaluar models oberts amb Cloud Run i una GPU

Per als models oberts petits (Gemma 4 E2B, E4B, 12B; Gemma 3 4B, 12B, 27B) no cal desplegar res al Model Garden: un
servei d'Ollama a Cloud Run amb una GPU NVIDIA L4 els serveix un darrere l'altre, i s'esborra quan s'acaba. Es paga
només mentre el servei és viu.

## 1. Preparar el projecte

```bash
gcloud services enable run.googleapis.com --project <projecte>
```

La regió ha de tenir L4 a Cloud Run (per exemple `europe-west4`) i el projecte, quota de GPU sense redundància zonal.

## 2. Desplegar el servei

Servei privat (sense accés públic), amb la imatge oficial d'Ollama fixada a una versió:

```bash
gcloud run deploy maia-bench-ollama --project <projecte> --region europe-west4 \
  --image docker.io/ollama/ollama:0.40.11 --port 11434 \
  --gpu 1 --gpu-type nvidia-l4 --no-gpu-zonal-redundancy \
  --cpu 8 --memory 32Gi --no-cpu-throttling \
  --min-instances 1 --max-instances 1 --concurrency 8 --timeout 3600 \
  --set-env-vars OLLAMA_HOST=0.0.0.0:11434,OLLAMA_KEEP_ALIVE=-1,OLLAMA_NUM_PARALLEL=4,OLLAMA_CONTEXT_LENGTH=8192 \
  --no-allow-unauthenticated
```

- `--min-instances 1` manté la instància (i el model descarregat) viva durant la passada. Per això el servei
  s'ha d'esborrar al final.
- Els models es descarreguen al disc en memòria del contenidor: amb 32 GiB n'hi cap un de cada vegada, i
  `tools/cloudrun.sh` l'esborra abans de passar al següent.

## 3. Passar el benchmark

El servei demana un token d'identitat de Google. El runner l'envia si hi ha `OLLAMA_TOKEN`:

```bash
export OLLAMA_HOST=https://maia-bench-ollama-<id>.europe-west4.run.app
export OLLAMA_TOKEN=$(gcloud auth print-identity-token)
python3 tools/executa.py --model ollama:gemma4:e2b
```

El token caduca a l'hora. `tools/cloudrun.sh` ho resol sol: per a cada model el descarrega al servei, executa en
trams de 50 minuts amb un token nou per tram (`executa.py` es reprèn i torna a fer les preguntes amb error), puntua
els tests i esborra el model:

```bash
tools/cloudrun.sh https://maia-bench-ollama-<id>.europe-west4.run.app gemma4:e2b gemma4:e4b gemma4:12b
```

Les respostes queden a `resultats/ollama_<model>/` com qualsevol altra execució amb Ollama: el model és el mateix,
només canvia on corre.

## 4. Esborrar el servei

```bash
gcloud run services delete maia-bench-ollama --region europe-west4 --project <projecte>
```

## Cost i rendiment observats

- Descàrrega de Gemma 4 E2B (4,6 GB) al servei: 1 min 38 s. Primera crida (càrrega a la GPU): ~45 s.
- Amb el model carregat: ~3 s per pregunta, 4 en paral·lel.
- Cost: GPU L4 + 8 vCPU + 32 GiB a Cloud Run, de l'ordre d'1 € per hora mentre el servei és viu (preus de la
  regió a la consola).

## Altres models de Google Cloud

Els models servits per API a Vertex (Gemini, Grok, alguns de partners) no necessiten servei: es criden directament
amb `vertex:<editor>/<model>`. Claude a Vertex fa servir `vertexclaude:<model>` i necessita quota a Vertex AI per a
cada model (per defecte és zero); Claude Fable demana, a més, activar que es comparteixin dades amb Anthropic.
