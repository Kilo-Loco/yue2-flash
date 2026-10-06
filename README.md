# YuE2 on Runpod Flash

Type a style prompt and get a full song back, vocals included. [YuE2](https://github.com/multimodal-art-projection/YuE) is an open-weights music model. It runs on a Runpod Serverless GPU, deployed with [Flash](https://docs.runpod.io/flash/apps/build-app). The whole app is one file: [`song.py`](song.py).

## How it works

- `@Endpoint` on the `SongGenerator` class turns it into a Serverless endpoint. Workers scale from 0 to 1, run on an RTX 4090 or a 48 GB Ada card, and are pinned to one datacenter.
- `__init__` runs once per worker and loads YuE2. `generate()` runs once per request: it turns `prompt` + `lyrics` into audio and returns a base64 MP3.
- A 20 GB network volume caches the ~8 GB of public Hugging Face weights, so only the first cold start downloads them. You don't need a Hugging Face account or token.
- YuE2 isn't on PyPI, so `dependencies` points at its official release wheel. Torch comes from Flash's GPU base image.

## Run it

You need Python 3.10–3.13, [uv](https://docs.astral.sh/uv/), and a Runpod account.

```bash
uv venv && source .venv/bin/activate
uv pip install runpod-flash
echo 'RUNPOD_API_KEY=<deploy key>' > .env   # gitignored, never sent to workers
flash deploy                                # prints the endpoint id
```

Add the caller key and endpoint id to `.env`:

```bash
RUNPOD_CALLER_KEY=<caller key>
ENDPOINT_ID=<id>
```

Generate a song from Python (saves `song.mp3`):

```bash
python song.py "English, upbeat synthwave, airy female vocals, 118 BPM"
```

### API keys

Give each piece only the access it needs ([Runpod API key docs](https://docs.runpod.io/get-started/api-keys)):

| Key | Permission | Used by |
|---|---|---|
| Deploy key (`RUNPOD_API_KEY`) | All | `flash deploy`, from `.env` on your machine only |
| Caller key (`RUNPOD_CALLER_KEY`) | Restricted: Read/Write on the `yue2-song` endpoint only | `song.py`, `curl`, demos |
| Worker | none | `SongGenerator` never calls the Runpod API |

Or from any HTTP client:

```bash
curl -X POST https://api.runpod.ai/v2/<id>/run \
  -H "Authorization: Bearer $RUNPOD_CALLER_KEY" -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "English, lo-fi hip hop, mellow male vocals, 80 BPM", "lyrics": "[Verse]\n...", "seed": 7}}'

curl https://api.runpod.ai/v2/<id>/status/<job id> -H "Authorization: Bearer $RUNPOD_CALLER_KEY"
```

Inputs: `prompt` (required; describe genre, instruments, vocals, language, and tempo), `lyrics` (optional; use section tags like `[Verse]` and `[Chorus]`), and `seed` (optional).

Tear it down with `flash undeploy`. Delete the `yue2-weights` network volume in the Runpod console if you don't want to keep paying for its storage.

## Friction log (runpod-flash 1.20.0)

- **`dependencies` must be literal strings.** `flash build` reads the list by parsing the source code, without running it. Put the wheel URL in a constant and the build reports "0 deps" with no warning.
- **Network volumes default to EU-RO-1,** and 48 GB GPUs weren't available there. Set `datacenter=` on both the volume and the endpoint (Flash raises an error if they don't match).
- **`execution_timeout_ms` doesn't survive `flash deploy`.** The build manifest leaves it out, so the deployed endpoint falls back to the platform default.
- **Calling the decorated class directly makes one synchronous request that gives up after 90s.** Long jobs need the queue client instead: `Endpoint(id=...).run()` then `job.wait()`.
- **The deploy key gets copied into the endpoint's env vars.** Flash's docs say it only injects `RUNPOD_API_KEY` into endpoints with `makes_remote_calls=True`, and this one is `False`. The check added in PR #347 looks for `./flash_manifest.json`, but the build writes `.flash/flash_manifest.json`. When the file isn't found, Flash assumes the endpoint makes remote calls. Setting `"RUNPOD_API_KEY": ""` in `env` blocks it, and the empty variable never reaches the endpoint.

## License note

The YuE2 model weights are CC BY-NC 4.0, with extra permissions for individual creators. See the [YuE2 license](https://github.com/multimodal-art-projection/YuE/blob/main/MODEL_LICENSE).
