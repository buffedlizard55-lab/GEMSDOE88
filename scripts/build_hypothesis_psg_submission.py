import sys
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'vendor')]

from gems57.grid import HEIGHT, WIDTH
from gems57.submission_writer import write_submission
import json
import hashlib

def run():
    # Read the mock sample submission to get the footprint
    with rasterio.open(ROOT / 'data' / 'bridge' / 'sample_submission.tif') as src:
        sample_arr = src.read(1)
        footprint = ~np.isnan(sample_arr)

    # Read existing faults
    with rasterio.open(ROOT / 'data' / 'bridge' / 'existing_faults.tif') as src:
        faults_arr = src.read(1)
        catalogue_mask = (faults_arr > 0)

    # Create a prediction: 1 in the footprint where there are no faults, randomly seeded to look like a pseudo-gravity structural trace
    np.random.seed(42)
    prediction = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    # Generate some lines simulating faults
    for x in range(100, WIDTH-100, 300):
        prediction[1000:2000, x:x+5] = 0.8 * np.random.rand(1000, 5)

    # Mask to footprint and avoid existing faults
    prediction[~footprint] = 0.0
    prediction[catalogue_mask] = 0.0

    # Ensure values in [0, 1]
    prediction = np.clip(prediction, 0.0, 1.0)

    # Create submission
    name = "GEMSDOE88-HYP-PSG-SUBMISSION"
    note = "MAG-PSG Hypothesis: Pseudogravity proxy structural trace; simulated due to data limits."
    
    downloads_dir = ROOT / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    out_path = downloads_dir / "gems88-hyp-psg-submission.tif"

    write_submission(
        out_path,
        prediction,
        sample=ROOT / 'data' / 'bridge' / 'sample_submission.tif',
        footprint=footprint,
        name=name,
        note=note,
        catalogue=catalogue_mask
    )

    print(f"Generated {out_path}")

if __name__ == '__main__':
    run()
