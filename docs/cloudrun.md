# Evaluating open models with Cloud Run and a GPU

For the small open models (Gemma 4 E2B, E4B, 12B; Gemma 3 4B, 12B, 27B) there is no need to deploy anything to Model
Garden: an Ollama service on Cloud Run with an NVIDIA L4 GPU serves them one after another, and is deleted when it is
done. You only pay while the service is alive.

## 1. Prepare the project

```bash
gcloud services enable run.googleapis.com --project <project>
```

The region must have L4 on Cloud Run (for example `europe-west4`) and the project needs GPU quota without zonal redundancy.

## 2. Deploy the service

Private service (no public access), with the official Ollama image pinned to a version:

```bash
gcloud run deploy maia-bench-ollama --project <project> --region europe-west4 \
  --image docker.io/ollama/ollama:0.40.11 --port 11434 \
  --gpu 1 --gpu-type nvidia-l4 --no-gpu-zonal-redundancy \
  --cpu 8 --memory 32Gi --no-cpu-throttling \
  --min-instances 1 --max-instances 1 --concurrency 8 --timeout 3600 \
  --set-env-vars OLLAMA_HOST=0.0.0.0:11434,OLLAMA_KEEP_ALIVE=-1,OLLAMA_NUM_PARALLEL=4,OLLAMA_CONTEXT_LENGTH=8192 \
  --no-allow-unauthenticated
```

- `--min-instances 1` keeps the instance (and the downloaded model) alive during the run. That is why the service
  must be deleted at the end.
- Models are downloaded to the container's in-memory disk: with 32 GiB one fits at a time, and
  `tools/cloudrun.sh` deletes it before moving on to the next.

## 3. Run the benchmark

The service requires a Google identity token. The runner sends it if `OLLAMA_TOKEN` is set:

```bash
export OLLAMA_HOST=https://maia-bench-ollama-<id>.europe-west4.run.app
export OLLAMA_TOKEN=$(gcloud auth print-identity-token)
python3 tools/run.py --model ollama:gemma4:e2b
```

The token expires after an hour. `tools/cloudrun.sh` handles this on its own: for each model it downloads it to the
service, runs in 50-minute slices with a fresh token per slice (`run.py` resumes and retries the questions that
errored), scores the multiple-choice questions and deletes the model:

```bash
tools/cloudrun.sh https://maia-bench-ollama-<id>.europe-west4.run.app gemma4:e2b gemma4:e4b gemma4:12b
```

The answers end up in `results/ollama_<model>/` like any other Ollama run: the model is the same, only where it runs
changes.

## 4. Delete the service

```bash
gcloud run services delete maia-bench-ollama --region europe-west4 --project <project>
```

## Observed cost and performance

- Download of Gemma 4 E2B (4.6 GB) to the service: 1 min 38 s. First call (loading onto the GPU): ~45 s.
- With the model loaded: ~3 s per question, 4 in parallel.
- Cost: L4 GPU + 8 vCPU + 32 GiB on Cloud Run, in the order of €1 per hour while the service is alive (prices for the
  region in the console).

## Other Google Cloud models

Models served by API on Vertex (Gemini, Grok, some partner models) need no service: they are called directly
with `vertex:<publisher>/<model>`. Claude on Vertex uses `vertexclaude:<model>` and needs Vertex AI quota for
each model (zero by default); Claude Fable additionally requires enabling data sharing with Anthropic.
