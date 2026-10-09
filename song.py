# YuE2 song generator on Runpod Serverless, built with Flash.
# deploy:  flash deploy
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
        "RUNPOD_API_KEY": "",  # the worker never calls Runpod; stops Flash 1.20 copying your deploy key here
    },
)
class SongGenerator:
    def __init__(self):
        # Runs once per worker, so warm requests skip the model load.
        from yue2 import YuE2Pipeline

        self.pipe = YuE2Pipeline.from_pretrained("m-a-p/YuE2-3B", device="cuda")

    async def generate(self, prompt: str, lyrics: str = DEFAULT_LYRICS) -> dict:
        import base64
        import io

        import soundfile as sf

        song = self.pipe(style=prompt, lyrics=lyrics)

        # MP3 keeps the response small enough for a JSON payload.
        buffer = io.BytesIO()
        sf.write(buffer, song.audio, song.sample_rate, format="MP3")
        return {
            "mp3_base64": base64.b64encode(buffer.getvalue()).decode(),
            "seconds": round(len(song.audio) / song.sample_rate, 1),
        }
