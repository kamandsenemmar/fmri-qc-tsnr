# fMRI Temporal SNR Quality Control

**Status:** early version, under development 

This project provides a basic quality control pipeline for resting-state fMRI data, focusing on temporal signal-to-noise ratio (tSNR).
It generates an EPI brain mask and calculates voxel-wise tSNR, along with summary statistics within the brain mask.
The pipeline produces a tSNR map, brain mask, statistical summary, and visual QC report.

## Installation
Developed and tested with Python 3.13.0

1. Clone the repository and open the project folder

2. Create a virtual environment:

```powershell
python -m venv .venv
```

3. Activate the virtual environment (Windows PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Install the required packages:

```powershell
python -m pip install -r requirements.txt
```

## Usage

First, download the example dataset (one subject from ADHD-200 via Nilearn):

```powershell
python download_data.py
```

Then run the QC pipeline:

```powershell
python fmri_qc.py data/adhd/data/0010042/0010042_rest_tshift_RPI_voreg_mni.nii.gz --out outputs --discard 5
```

`input` - The path to the input 4D fMRI NIfTI file (required)

`--out` - The directory for the QC results (default: `outputs`)

`--discard` - Number of initial volumes to discard (default: `5`)

## Outputs

`tsnr_map.nii.gz` - NIfTI image of the tSNR map

`mask.nii.gz` - NIfTI image of the generated brain mask

`qc_summary.json` - A statistical summary including mean, median, standard deviation, 5th and 95th percentiles of brain-masked tSNR, mask voxel count, number of volumes used, and TR 

`qc_report.png` - A figure including three axial tSNR slices with a shared intensity scale and colorbar, a mean fMRI image with the brain mask outline, a tSNR histogram and a summary statistics (mean, median and mask voxel count)

## Example QC Report

![Example QC Report](examples/qc_example.png)

## Method

The first N volumes are discarded before calculating tSNR (default N = 5) to exclude potentially unstable initial MRI signals. Running the example with `--discard 0` and `--discard 5` gave a mean brain-masked tSNR of 83.71 to 84.06. An EPI mask is generated using Nilearn `compute_epi_mask()`. tSNR is calculated voxel-wise across the image as the temporal mean divided by the temporal standard deviation. The summary statistics are then calculated using only the tSNR values within the generated brain mask.

$$
\mathrm{tSNR} = \frac{\mu_{\mathrm{time}}}{\sigma_{\mathrm{time}}}
$$

The example ADHD-200 image has already undergone preprocessing, including slice-timing correction, reorientation, volume realignment, and registration to MNI space, which may affect tSNR values compared with raw fMRI data.

**Example data:** ADHD-200 sample (subject 0010042), downloaded using Nilearn.

## Limitations

tSNR is computed on the data as given. The tool does not perform motion correction, detrending or nuisance regression, so values depend on whether the input has been preprocessed. Results from raw and preprocessed data are not directly comparable.

The pipeline assumes that the third array axis corresponds to the axial direction and does not perform image reorientation.

## Next steps

- Framewise displacement from realignment parameters

- Optional detrending before the tSNR calculation

- BIDS-compatible input handling

## Author

Kamand Senemmar