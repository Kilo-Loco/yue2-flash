# YuE2 song generator on Runpod Serverless, built with Flash.
# deploy:  flash deploy
# run:     python song.py "upbeat synthwave, female vocals, 120 BPM" [lyrics.txt]   (keys + ENDPOINT_ID in .env)
from runpod_flash import DataCenter, Endpoint, GpuGroup, NetworkVolume

DEFAULT_LYRICS = """[Verse]
Neon fades along the lane
Footsteps keep the time of rain

[Chorus]
Let the day come into view
Every road begins with you"""


@Endpoint(
    name="yue2-song",
    gpu=[GpuGroup.ADA_24, GpuGroup.ADA_48_PRO],  # YuE2 needs a BF16 GPU with 24 GB+ (4090, else 48 GB Ada)
    datacenter=DataCenter.US_IL_1,  # a network volume lives in one datacenter, so pin workers to it
    workers=(0, 1),  # scale to zero when idle
    # YuE2 isn't on PyPI, so install its official release wheel from GitHub.
    # Must be a string literal: `flash build` reads this list from the source, it doesn't run it.
    dependencies=[
        "yue2-infer @ https://github.com/multimodal-art-projection/YuE/releases/download/yue2-v0.1.6/yue2_infer-0.1.6-py3-none-any.whl"
    ],
    volume=NetworkVolume(name="yue2-weights", size=20, datacenter=DataCenter.US_IL_1),  # ~8 GB of weights, downloaded once
    env={
        "HF_HOME": "/runpod-volume/huggingface",  # point the Hugging Face cache at the volume
        "RUNPOD_API_KEY": "",  # worker never calls Runpod; stops flash 1.20 injecting your key (see README)
    },
    execution_timeout_ms=20 * 60 * 1000,  # a song takes minutes (flash 1.20 deploy drops this, see README)
)
class SongGenerator:
    def __init__(self):
        # Runs once per worker, so warm requests skip the model load.
        from yue2 import YuE2Pipeline

        self.pipe = YuE2Pipeline.from_pretrained("m-a-p/YuE2-3B", device="cuda", progress=False)

    async def generate(self, prompt: str, lyrics: str = DEFAULT_LYRICS, seed: int = 42) -> dict:
        import base64
        import io

        import soundfile as sf

        song = self.pipe(style=prompt, lyrics=lyrics, seed=seed)

        # MP3 keeps the response small enough for a JSON payload.
        buffer = io.BytesIO()
        sf.write(buffer, song.audio, song.sample_rate, format="MP3")
        return {
            "mp3_base64": base64.b64encode(buffer.getvalue()).decode(),
            "seconds": round(len(song.audio) / song.sample_rate, 1),
        }


async def main(endpoint_id: str, prompt: str, lyrics: str | None = None):
    import base64

    payload = {"prompt": prompt}
    if lyrics:
        payload["lyrics"] = lyrics

    # Queue the job and poll for it. A direct `await SongGenerator().generate()` uses a
    # single synchronous request that gives up after 90s, and a song takes minutes.
    job = await Endpoint(id=endpoint_id).run(payload)
    print(f"Job {job.id} queued, waiting for the song...")
    await job.wait()

    # Flash's handler reports exceptions inside the output, so check both places.
    output = job.output or {}
    if job.error or "error" in output:
        raise SystemExit(job.error or output["error"])

    with open("song.mp3", "wb") as f:
        f.write(base64.b64decode(output["mp3_base64"]))
    print(f"Saved song.mp3 ({output['seconds']}s)")


if __name__ == "__main__":
    import asyncio
    import os
    import sys

    # Call with the restricted caller key, not the deploy key. Flash already loaded .env on
    # import, and its client sends whatever RUNPOD_API_KEY holds, so swap it for this process.
    os.environ["RUNPOD_API_KEY"] = os.environ["RUNPOD_CALLER_KEY"]

    prompt = sys.argv[1] if len(sys.argv) > 1 else "English, warm piano pop, expressive female voice, 88 BPM"
    lyrics = open(sys.argv[2]).read() if len(sys.argv) > 2 else None  # optional lyrics file
    asyncio.run(main(os.environ["ENDPOINT_ID"], prompt, lyrics))
