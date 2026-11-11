import numpy as np
import nibabel as nib
from nilearn.masking import compute_epi_mask
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
import json

def load_4d(path):
    image = nib.load(path)
    if len(image.shape) !=4:
        raise ValueError("Input image must be 4D")
    header = image.header
    TR = header.get_zooms()[3]
    return image, TR

def discard_volumes(data, n=5):
    trimmed_data = data[:, :, :, n:]
    return trimmed_data

def make_mask(img):
    mask_img = compute_epi_mask(img)
    return mask_img

def compute_tsnr(data):
    mean_img = np.mean(data, axis=3)
    std_img = np.std(data, axis=3)
    tsnr_map = np.divide(mean_img, std_img, out=np.zeros_like(mean_img), where=std_img > 0)
    return tsnr_map

def summarize(tsnr, mask, n_volume, tr):
    boolean_mask = mask.get_fdata().astype(bool)
    masked_tsnr = tsnr[boolean_mask]
    mean_masked_tsnr = np.mean(masked_tsnr)
    median_masked_tsnr = np.median(masked_tsnr)
    std_masked_tsnr = np.std(masked_tsnr)
    five_percentile = np.percentile(masked_tsnr, 5)
    ninetyfive_percentile = np.percentile(masked_tsnr, 95)
    voxels_masked = np.sum(boolean_mask)
    summary = {
        "mean_tsnr": float(mean_masked_tsnr),
        "median_tsnr": float(median_masked_tsnr),
        "std_tsnr": float(std_masked_tsnr),
        "5th percentile": float(five_percentile),
        "95th percentile": float(ninetyfive_percentile),
        "number of voxels inside the mask": int(voxels_masked),
        "Number of volumes remaining after discarding": int(n_volume),
        "TR": float(tr)
    }
    return summary

def make_figure(tsnr, mask_img, data, output_path):
    mean_img = np.mean(data, axis=3)
    masked_data = mask_img.get_fdata()
    boolean_masked = masked_data.astype(bool)
    masked_tsnr = tsnr[boolean_masked]
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    n_slices = tsnr.shape[2]
    slice_indices = [
        int(n_slices * 0.25),
        int(n_slices * 0.50),
        int(n_slices * 0.75)
    ]
    axes[0, 0].imshow(tsnr[:, :, slice_indices[0]].T, cmap="gray", origin="lower")
    axes[0, 0].set_title(f"tSNR - Axial slice {slice_indices[0]}")
    axes[0, 1].imshow(tsnr[:, :, slice_indices[1]].T, cmap="gray", origin="lower")
    axes[0, 1].set_title(f"tSNR - Axial slice {slice_indices[1]}")
    axes[0, 2].imshow(tsnr[:, :, slice_indices[2]].T, cmap="gray", origin="lower")
    axes[0, 2].set_title(f"tSNR - Axial slice {slice_indices[2]}")
    axes[1, 0].imshow(mean_img[:, :, slice_indices[1]].T, cmap="gray", origin="lower")
    axes[1, 0].contour(
        masked_data[:, :, slice_indices[1]].T,
        levels=[0.5],
        colors="red",
        linewidths=1
    )
    axes[1, 0].set_title(f"Mask overlay on mean fMRI - Axial slice {slice_indices[1]}")
    axes[1, 1].hist(masked_tsnr, bins=50)
    axes[1, 1].set_title("Distribution of tSNR within the mask")
    axes[1, 1].set_xlabel("tSNR")
    axes[1, 1].set_ylabel("Number of voxels")
    axes[1, 2].axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser(description="fMRI temporal SNR quality control")
    parser.add_argument("input", help="Path to the input 4D fMRI NIfTI file")
    parser.add_argument("--out", default="outputs", help="Directory for QC results")
    parser.add_argument("--discard", type=int, default=5, help="Number of initial volumes to discard")
    args = parser.parse_args()
    image, tr = load_4d(args.input)
    data = image.get_fdata()
    trimmed_data = discard_volumes(data, args.discard)
    n_volumes = trimmed_data.shape[3]
    mask_img = make_mask(image)
    tsnr_map = compute_tsnr(trimmed_data)
    summary = summarize(tsnr_map, mask_img, n_volumes, tr)
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    tsnr_img = nib.Nifti1Image(tsnr_map, image.affine)
    nib.save(tsnr_img, output_dir / "tsnr_map.nii.gz")
    nib.save(mask_img, output_dir / "mask.nii.gz")
    with open(output_dir / "qc_summary.json", "w") as f:
        json.dump(summary, f, indent=4)
    make_figure(tsnr_map, mask_img, trimmed_data, output_dir / "qc_report.png")
    #print("Number of NaNs: ", np.isnan(tsnr_map).sum())

if __name__ == "__main__":
    main()
