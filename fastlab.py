python
from fastapi import FastAPI, Request, Form, HTTPException, File, UploadFile
from typing import List
import hashlib
import numpy as np
import io
import requests
from PIL import Image
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import matplotlib.pyplot as plt
import math

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.post("/image_form", response_class=HTMLResponse)
async def transform_image(request: Request,
                          period: int = Form(),
                          axis: str = Form(),
                          files: List[UploadFile] = File(description="Multiple files as UploadFile"),
                          resp: str = Form()):
    recaptcha_secret = "6LdDV80pAAAAAJ7kIaFSs4mMADU3qSxAYUr92n0_"  # Замените на ваш секретный ключ reCAPTCHA
    recaptcha_data = {
        'secret': recaptcha_secret,
        'response': resp
    }
    recaptcha_url = "https://www.google.com/recaptcha/api/siteverify"
    recaptcha_verification = requests.post(recaptcha_url, data=recaptcha_data)
    recaptcha_result = recaptcha_verification.json()

    if not recaptcha_result['success']:
        raise HTTPException(status_code=400, detail="Ошибка проверки капчи")

    ready = False
    if len(files) > 0 and len(files[0].filename) > 0:
        ready = True

    original_images = []
    transformed_images = []
    original_histogram_images = []
    transformed_histogram_images = []

    if ready:
        print([file.filename.encode('utf-8') for file in files])
        images = ["static/" + hashlib.sha256(file.filename.encode('utf-8')).hexdigest() for file in files]

        content = [await file.read() for file in files]

        p_images = [Image.open(io.BytesIO(con)).convert("RGB") for con in content]

        for i in range(len(p_images)):
            original_image = p_images[i]
            transformed_image = transform_pixels(original_image, period, axis)

            original_histogram = get_histogram(original_image)
            transformed_histogram = get_histogram(transformed_image)

            original_image_path = f"static/original_{i}.jpg"
            transformed_image_path = f"static/transformed_{i}.jpg"
            original_image.save(original_image_path)
            transformed_image.save(transformed_image_path)

            original_histogram_image = create_histogram_image(original_histogram)
            transformed_histogram_image = create_histogram_image(transformed_histogram)

            original_histogram_image_path = f"static/original_histogram_{i}.png"
            transformed_histogram_image_path = f"static/transformed_histogram_{i}.png"
            original_histogram_image.save(original_histogram_image_path)
            transformed_histogram_image.save(transformed_histogram_image_path)

            original_images.append(original_image_path)
            transformed_images.append(transformed_image_path)
            original_histogram_images.append(original_histogram_image_path)
            transformed_histogram_images.append(transformed_histogram_image_path)

        return templates.TemplateResponse("forms.html", {"request": request, "ready": ready,
                                                         "original_images": original_images,
                                                         "transformed_images": transformed_images,
                                                         "original_histogram_images": original_histogram_images,
                                                         "transformed_histogram_images": transformed_histogram_images})


@app.get("/image_form", response_class=HTMLResponse)
async def make_image(request: Request):
    return templates.TemplateResponse("forms.html", {"request": request})


def transform_pixels(image, period, axis):
    pixels = np.array(image)
    height, width, _ = pixels.shape

    if axis == 'horizontal':
        for y in range(height):
            for x in range(width):
                pixels[y, x] = pixels[y, x] * (1 + 0.5 * np.sin(2 * np.pi * x / period))
    else:
        for y in range(height):
            for x in range(width):
                pixels[y, x] = pixels[y, x] * (1 + 0.5 * np.sin(2 * np.pi * y / period))

    return Image.fromarray(pixels.astype(np.uint8))


def get_histogram(image):
    pixels = np.array(image)

    r_histogram, r_bins = np.histogram(pixels[:, :, 0].flatten(), bins=np.arange(0, 257, 10))
    g_histogram, g_bins = np.histogram(pixels[:, :, 1].flatten(), bins=np.arange(0, 257, 10))
    b_histogram, b_bins = np.histogram(pixels[:, :, 2].flatten(), bins=np.arange(0, 257, 10))

    max_length = max(len(r_histogram), len(g_histogram), len(b_histogram))
    r_histogram = np.pad(r_histogram, (0, max_length - len(r_histogram)), mode='constant')
    g_histogram = np.pad(g_histogram, (0, max_length - len(g_histogram)), mode='constant')
    b_histogram = np.pad(b_histogram, (0, max_length - len(b_histogram)), mode='constant')

    return r_histogram.tolist(), g_histogram.tolist(), b_histogram.tolist()


def create_histogram_image(histograms):
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.bar(np.arange(0, len(histograms[0]) * 10, 10), histograms[0], color='r', width=10, label='Red')
    ax.bar(np.arange(0, len(histograms[1]) * 10, 10), histograms[1], color='g', width=10, label='Green')
    ax.bar(np.arange(0, len(histograms[2]) * 10, 10), histograms[2], color='b', width=10, label='Blue')
    ax.set_title('Гистограмма распределения цветов')
    ax.set_xlabel('Значение пиксилей')
    ax.set_ylabel('Частота')
    ax.grid(True)
    ax.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return Image.open(buf)