# pip install google-genai pillow python-dotenv requests

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import base64
import json
import os
import time
from typing import Optional
import random
from textwrap import dedent
import requests
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

# =========================
# Env & API Keys
# =========================
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY in .env")

ARK_API_KEY = os.getenv("ARK_API_KEY")  # สำหรับ BytePlus (ถ้าใช้วิดีโอ)
if not ARK_API_KEY:
    print("WARN: Missing ARK_API_KEY in .env (BytePlus video flow will fail if used)")

# =========================
# Helpers
# =========================
def img_to_data_url(file_path: str) -> str:
    ext = os.path.splitext(file_path.lower())[1]
    mime = (
        "image/jpeg" if ext in [".jpg", ".jpeg"] else
        "image/png"  if ext == ".png" else
        "image/webp" if ext == ".webp" else
        "application/octet-stream"
    )
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"

def combine_images(person_path: str, product_path: str):
    person = Image.open(person_path).convert("RGBA")
    product = Image.open(product_path).convert("RGBA")
    width = person.width + product.width + 50
    height = max(person.height, product.height)
    canvas = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    canvas.paste(person, (0, 0), person)
    x_offset = person.width + 50
    y_offset = (height - product.height) // 2
    canvas.paste(product, (x_offset, y_offset), product)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path: str = f"{ts}_combined.png"
    canvas.save(out_path)
    print(f"Saved -> {out_path}")
    return out_path

def _extract_first_image_bytes(resp_obj) -> Optional[bytes]:
    try:
        for part in resp_obj.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                return part.inline_data.data
    except Exception:
        pass
    return None

def create_poster_prompt(seed=None):
    if seed is not None:
        random.seed(seed)

    atmospheres = [
        "a wild west cowboy town with dusty streets and wooden saloons",
        "a medieval knight's castle courtyard with banners and torches",
        "a prehistoric stone age landscape with caves and bonfires",
        "a dinosaur era jungle with giant ferns and dinosaurs in the distance",
        "a modern city plaza with LED billboards and traffic light trails",
        "a futuristic cyberpunk city with neon lights and holographic ads",
        "a high-tech sci-fi laboratory glowing with plasma energy",
        "a grand concert stage with spotlights, haze, and cheering crowds",
        "a volcanic battlefield with molten lava and erupting sparks",
        "an interstellar space station with stars and planetary views outside",
    ]

    chosen_bg = random.choice(atmospheres)

    prompt = dedent(f"""
        Advertising poster for M-150 energy drink
        - Vertical 9:16 aspect ratio (1080x1920), cinematic poster design
        - Use the face and hairstyle from image exactly as in the original photo.
          Do not alter facial features, skin tone, or hairstyle.
        - Add a second presenter: a woman standing beside the person from image, confident pose.
        - Both presenters should wear outfits that match the chosen background theme,
          blending naturally into the {chosen_bg} setting.
        - Both presenters are holding the product M150 Energy drinks in a natural grip.
        - The M-150 logo on the product must face the camera clearly, sharp and readable, not distorted.
        - Background: {chosen_bg}.
        - Use cinematic lighting: strong rim light around both presenters, dramatic highlights,
          and energy effects around the bottles.
        - The overall mood should feel powerful, energetic, and eye-catching,
          like a blockbuster advertisement poster.
    """).strip()

    return prompt

def gen_poster_byteplus(image: str, out_dir: str = ".") -> str:
    if not ARK_API_KEY:
        raise RuntimeError("ARK_API_KEY is required for gen_poster_byteplus")
    url = "https://ark.ap-southeast.bytepluses.com/api/v3/images/generations"
    headers = {"Authorization": f"Bearer {ARK_API_KEY}", "Content-Type": "application/json", "Accept": "application/json"}
    prompt = create_poster_prompt()
    payload = {
        "model": "seedream-4-0-250828",
        "prompt": prompt,
        "image": image,
        "sequential_image_generation": "disabled",
        "response_format": "url",
        "size": "2K",
        "stream": False,
        "watermark": False
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Submit failed: {resp.status_code} {resp.text}")
    data = resp.json()
    url_out = None
    if "data" in data and isinstance(data["data"], list) and data["data"]:
        url_out = data["data"][0].get("url")
    if not url_out:
        raise RuntimeError(f"No image url in response: {data}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"byteplus_m150_{ts}"
    img_path = os.path.join(out_dir, f"{base_name}.png")
    json_path = os.path.join(out_dir, f"{base_name}.json")
    r = requests.get(url_out, stream=True, timeout=120)
    r.raise_for_status()
    with open(img_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Saved image -> {img_path}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved metadata -> {json_path}")
    return img_path

def gen_poster_gemini(person_image_path: str, product_image_path: str, out_dir: str = ".") -> str:
    img_person = Image.open(person_image_path)
    img_product = Image.open(product_image_path)
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = create_poster_prompt()
    resp = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=[prompt, img_person, img_product],
        config={"seed": int(time.time())},
    )
    image_bytes = _extract_first_image_bytes(resp)
    if not image_bytes:
        print(json.dumps(resp.to_dict(), ensure_ascii=False, indent=2))
        raise RuntimeError("No image returned from model")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"m150_poster_{ts}.png")
    Image.open(BytesIO(image_bytes)).save(out_path)
    print(f"Saved -> {out_path}")
    return out_path

def gen_video_gemini_veo3(image_data_url: str) -> str:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    if not client:
        raise RuntimeError("Missing GEMINI_API_KEY in environment")

    if not image_data_url.startswith("data:"):
        raise ValueError("Expected a data URL (data:image/...;base64,...)")

    header, b64data = image_data_url.split(",", 1)
    mime_type = "image/jpeg"
    if header.startswith("data:image/png"):
        mime_type = "image/png"

    image_bytes = base64.b64decode(b64data)
    image = types.Image(image_bytes=image_bytes, mime_type=mime_type)

    prompt = """
    Use this image as the base reference for the presenter and transform it into a dynamic advertising video for an energy drink.
    - The presenter should appear confident, healthy, strong, and cheerful.
    - Their movements should be natural and energetic: walking, lifting the product, smiling with vitality.
    - Ensure the product (energy drink can or bottle) is clearly visible in the presenter's hand, with the logo facing the camera.
    - The atmosphere should feel vibrant and powerful, like a high-energy commercial.
    - Add cinematic lighting, rim light, and subtle energy effects (glows, sparks, or motion streaks) around the presenter and the product.
    - Overall mood: inspiring, motivational, and eye-catching, suitable for a modern energy drink advertisement. 
    """.strip()

    config = types.GenerateVideosConfig(
        aspect_ratio="9:16",
        resolution="720p",
        duration_seconds=8,
        negative_prompt="cartoon, low quality, warped face, logo distortion",
        person_generation="allow_adult",
        number_of_videos=1,
    )

    operation = client.models.generate_videos(
        model="veo-3.0-generate-001",
        prompt=prompt,
        image=image,
        config=config,
    )

    while not operation.done:
        print("Waiting for video generation...")
        time.sleep(10)
        operation = client.operations.get(operation)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"m150_energy_ad_{timestamp}.mp4"

    generated_video = operation.response.generated_videos[0]
    client.files.download(file=generated_video.video)
    generated_video.video.save(out_path)

    print(f"✅ Video saved to {out_path}")
    return out_path


def gen_video_byteplus(image_data_url: str) -> str:
    if not ARK_API_KEY:
        raise RuntimeError("ARK_API_KEY is required for gen_video_byteplus")
    submit_url = "https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks"
    headers = {"Authorization": f"Bearer {ARK_API_KEY}", "Content-Type": "application/json", "Accept": "application/json"}
    prompt_txt = """
        Use this image as the base reference for the presenter and transform it into a dynamic advertising video for an energy drink.
        - The presenter should appear confident, healthy, strong, and cheerful.
        - Their movements should be natural and energetic: walking, lifting the product, smiling with vitality.
        - Ensure the product (energy drink can or bottle) is clearly visible in the presenter's hand, with the logo facing the camera.
        - The atmosphere should feel vibrant and powerful, like a high-energy commercial.
        - Add cinematic lighting, rim light, and subtle energy effects (glows, sparks, or motion streaks) around the presenter and the product.
        - Overall mood: inspiring, motivational, and eye-catching, suitable for a modern energy drink advertisement.
    """.strip()
    payload = {
        "model": "seedance-1-0-lite-i2v-250428",
        "ratio": "9:16",
        "resolution": "720p",
        "content": [
            {"type": "text", "text": prompt_txt},
            {"type": "image_url", "image_url": {"url": image_data_url}, "role": "first_frame"},
        ],
    }
    resp = requests.post(submit_url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Submit failed: {resp.status_code} {resp.text}")
    data = resp.json()
    task_id = data.get("id")
    if not task_id:
        raise RuntimeError(f"No task id in response: {data}")
    print(f"BytePlus task submitted. Task ID = {task_id}")

    fetch_url = f"https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks/{task_id}"
    max_checks = 500
    for i in range(1, max_checks + 1):
        r = requests.get(fetch_url, headers=headers, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"Fetch failed: {r.status_code} {r.text}")
        info = r.json()
        status = info.get("status", "")
        print(f"[{i}/{max_checks}] Status = {status}")
        if status in {"succeeded", "failed", "canceled"}:
            print("Final response JSON:")
            print(json.dumps(info, ensure_ascii=False, indent=2))
            if status != "succeeded":
                raise RuntimeError(f"Task ended with status: {status}")
            video_url = info.get("content", {}).get("video_url")
            if not video_url:
                raise RuntimeError("No video_url in success response")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"{task_id}_{ts}"
            video_path = f"{base_name}.mp4"
            json_path = f"{base_name}.json"
            rr = requests.get(video_url, stream=True, timeout=120)
            rr.raise_for_status()
            with open(video_path, "wb") as f:
                for chunk in rr.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Saved video -> {video_path}")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            print(f"Saved metadata -> {json_path}")
            return video_path
        time.sleep(5)
    raise TimeoutError("Timeout: task not finished in allotted checks")

# =========================
# Main
# =========================
if __name__ == "__main__":
    import concurrent.futures

    PERSON_IMG_PATH = "heart.jpg"
    PRODUCT_IMG_PATH = "m150.jpg"

    def run_byteplus_flow():
        try:
            combined = combine_images(PERSON_IMG_PATH, PRODUCT_IMG_PATH)
            combined_dataurl = img_to_data_url(combined)
            bp_poster_path = gen_poster_byteplus(combined_dataurl)

            print(f"[BytePlus] Poster saved at: {bp_poster_path}")

            bp_poster_dataurl = img_to_data_url(bp_poster_path)
            byteplus_video_path = gen_video_byteplus(bp_poster_dataurl)
            print(f"[BytePlus] Video saved at: {byteplus_video_path}")
        except Exception as e:
            print(f"[BytePlus] Failed: {e}")

    def run_gemini_flow():
        try:
            gm_poster_path = gen_poster_gemini(PERSON_IMG_PATH, PRODUCT_IMG_PATH)

            print(f"[Gemini] Poster saved at: {gm_poster_path}")

            gm_poster_dataurl = img_to_data_url(gm_poster_path)
            gemini_video_path = gen_video_gemini_veo3(gm_poster_dataurl)
            print(f"[Gemini] Video saved at: {gemini_video_path}")
        except Exception as e:
            print(f"[Gemini] Failed: {e}")

    # Run both flows in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(run_byteplus_flow),
            executor.submit(run_gemini_flow),
        ] 
        concurrent.futures.wait(futures)
