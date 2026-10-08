import io

import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from plate_reader_api.brazilian_plate import BrazilianPlate
from plate_reader_api.main import app, get_reader
from plate_reader_api.reader import PlateReading

EXIF_ORIENTATION_TAG = 0x0112
EXIF_ROTATE_90_CLOCKWISE = 6


class StubReader:
    last_image_shape: tuple[int, ...] | None = None

    def read(self, image: np.ndarray) -> list[PlateReading]:
        self.last_image_shape = image.shape
        return [
            PlateReading(
                plate=BrazilianPlate(text="BRA2E19", format="mercosul", confidence=0.97),
                box=(10, 20, 110, 60),
            )
        ]


stub_reader = StubReader()
app.dependency_overrides[get_reader] = lambda: stub_reader
client = TestClient(app)


def jpeg_bytes() -> bytes:
    _, encoded = cv2.imencode(".jpg", np.zeros((50, 50, 3), np.uint8))
    return encoded.tobytes()


def test_returns_plates_read_from_the_image():
    response = client.post("/v1/plates/read", files={"image": ("photo.jpg", jpeg_bytes(), "image/jpeg")})

    assert response.status_code == 200
    assert response.json() == {
        "plates": [
            {"text": "BRA2E19", "format": "mercosul", "confidence": 0.97, "box": [10, 20, 110, 60]}
        ]
    }


def test_reads_phone_photos_upright():
    exif = Image.Exif()
    exif[EXIF_ORIENTATION_TAG] = EXIF_ROTATE_90_CLOCKWISE
    photo = io.BytesIO()
    Image.new("RGB", (200, 100)).save(photo, "JPEG", exif=exif.tobytes())

    client.post("/v1/plates/read", files={"image": ("photo.jpg", photo.getvalue(), "image/jpeg")})

    assert stub_reader.last_image_shape[:2] == (200, 100)


def test_rejects_a_file_that_is_not_an_image():
    response = client.post("/v1/plates/read", files={"image": ("notes.txt", b"hello", "text/plain")})

    assert response.status_code == 422


def test_requires_an_image():
    response = client.post("/v1/plates/read")

    assert response.status_code == 422
