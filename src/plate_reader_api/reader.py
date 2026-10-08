"""Finds the plates in a photo and reads them as Brazilian plates."""

from dataclasses import dataclass

import cv2
import numpy as np
from fast_plate_ocr import LicensePlateRecognizer
from fast_plate_ocr.core.process import preprocess_image, resize_image
from open_image_models import LicensePlateDetector

from plate_reader_api.brazilian_plate import BrazilianPlate, decode

DEFAULT_DETECTOR_MODEL = "yolo-v9-t-384-license-plate-end2end"
DEFAULT_OCR_MODEL = "cct-s-v2-global-model"


@dataclass(frozen=True)
class PlateReading:
    plate: BrazilianPlate
    box: tuple[int, int, int, int]
    """Pixel coordinates (x1, y1, x2, y2) of the plate in the photo."""


class PlateReader:
    def __init__(
        self,
        detector_model: str = DEFAULT_DETECTOR_MODEL,
        ocr_model: str = DEFAULT_OCR_MODEL,
    ) -> None:
        self._detector = LicensePlateDetector(detection_model=detector_model)
        self._recognizer = LicensePlateRecognizer(hub_ocr_model=ocr_model)

    def read(self, image: np.ndarray) -> list[PlateReading]:
        """Reads every plate in a BGR image, most confident first."""
        config = self._recognizer.config
        height, width = image.shape[:2]
        readings = []
        for detection in self._detector.predict(image):
            box = detection.bounding_box
            x1, y1 = max(box.x1, 0), max(box.y1, 0)
            x2, y2 = min(box.x2, width), min(box.y2, height)
            slot_probs = self._slot_probs(image[y1:y2, x1:x2])
            plate = decode(slot_probs, config.alphabet, config.pad_char)
            readings.append(PlateReading(plate=plate, box=(x1, y1, x2, y2)))
        return sorted(readings, key=lambda reading: reading.plate.confidence, reverse=True)

    def _slot_probs(self, crop: np.ndarray) -> np.ndarray:
        """Runs the OCR model and returns its (slots, alphabet) probability matrix."""
        config = self._recognizer.config
        color_conversion = cv2.COLOR_BGR2RGB if config.image_color_mode == "rgb" else cv2.COLOR_BGR2GRAY
        resized = resize_image(
            cv2.cvtColor(crop, color_conversion),
            config.img_height,
            config.img_width,
            image_color_mode=config.image_color_mode,
            keep_aspect_ratio=config.keep_aspect_ratio,
            interpolation_method=config.interpolation,
            padding_color=config.padding_color,
        )
        (output,) = self._recognizer.model.run(
            [self._recognizer.plate_output_name], {"input": preprocess_image(resized)}
        )
        return output.reshape(config.max_plate_slots, len(config.alphabet))
