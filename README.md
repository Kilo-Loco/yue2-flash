# YuE2 on Runpod Flash

Generate a full song, vocals included, from a style prompt and optional lyrics. [YuE2](https://github.com/multimodal-art-projection/YuE), an open-source music model, runs on a Runpod Serverless GPU deployed with [Flash](https://docs.runpod.io/flash/apps/build-app), and a local Streamlit app sends the requests.

## Stack

- **YuE2** (`m-a-p/YuE2-3B`): song generation
- **Runpod Flash**: deploys [`song.py`](song.py) as a Serverless endpoint on an RTX 4090
- **Streamlit**: the local UI in [`app.py`](app.py)

## Requirements

- Python 3.10–3.13 and [uv](https://docs.astral.sh/uv/)
- A Runpod account and an API key with **All** permissions

## Run it

Install the dependencies:

```bash
uv venv && source .venv/bin/activate
uv pip install runpod-flash streamlit
```

Copy the example env file and fill in `RUNPOD_API_KEY`:

```bash
cp .env.example .env
```

Deploy the endpoint. `flash deploy` prints the endpoint ID.

```bash
flash deploy
```

Fill in `ENDPOINT_ID` in `.env`, then start the app:

```bash
streamlit run app.py
```

The first song after a cold start takes a minute or two while a worker starts and loads YuE2.
