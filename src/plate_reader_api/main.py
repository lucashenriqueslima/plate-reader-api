"""HTTP API: send a photo, get back the Brazilian plates in it."""

import os
from contextlib import asynccontextmanager
from typing import Annotated

import cv2
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from pydantic import BaseModel

from plate_reader_api.brazilian_plate import PlateFormat
from plate_reader_api.reader import DEFAULT_DETECTOR_MODEL, DEFAULT_OCR_MODEL, PlateReader


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.reader = PlateReader(
        detector_model=os.getenv("DETECTOR_MODEL", DEFAULT_DETECTOR_MODEL),
        ocr_model=os.getenv("OCR_MODEL", DEFAULT_OCR_MODEL),
    )
    yield


app = FastAPI(title="Plate Reader API", lifespan=lifespan)


def get_reader(request: Request) -> PlateReader:
    return request.app.state.reader


class Plate(BaseModel):
    text: str
    format: PlateFormat
    confidence: float
    box: tuple[int, int, int, int]


class ReadPlatesResponse(BaseModel):
    plates: list[Plate]
    """Most confident first. Empty when no plate was found."""


@app.post("/v1/plates/read")
def read_plates(
    image: UploadFile, reader: Annotated[PlateReader, Depends(get_reader)]
) -> ReadPlatesResponse:
    frame = cv2.imdecode(np.frombuffer(image.file.read(), np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=422, detail="The uploaded file is not a valid image.")

    return ReadPlatesResponse(
        plates=[
            Plate(
                text=reading.plate.text,
                format=reading.plate.format,
                confidence=reading.plate.confidence,
                box=reading.box,
            )
            for reading in reader.read(frame)
        ]
    )
