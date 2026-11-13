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
    if n < 0 or n > data.shape[3] - 2:
        raise ValueError(f"--discard must be between 0 and {data.shape[3] - 2}")
    return data[:, :, :, n:]

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
        "tsnr_mean": float(mean_masked_tsnr),
        "tsnr_median": float(median_masked_tsnr),
        "tsnr_std": float(std_masked_tsnr),
        "tsnr_p5": float(five_percentile),
        "tsnr_p95": float(ninetyfive_percentile),
        "mask_voxel_count": int(voxels_masked),
        "n-volumes": int(n_volume),
        "tr_seconds": float(tr)
    }
    return summary

def make_figure(tsnr, mask_img, data, output_path):
    mean_img = np.mean(data, axis=3)
    masked_data = mask_img.get_fdata()
    boolean_masked = masked_data.astype(bool)
    masked_tsnr = tsnr[boolean_masked]
    vmax = np.percentile(masked_tsnr, 99)
    mean_tsnr = np.mean(masked_tsnr)
    median_tsnr = np.median(masked_tsnr)
    voxel_count = np.sum(boolean_masked)
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    n_slices = tsnr.shape[2]
    slice_indices = [
        int(n_slices * 0.25),
        int(n_slices * 0.50),
        int(n_slices * 0.75)
    ]
    im = axes[0, 0].imshow(tsnr[:, :, slice_indices[0]].T, cmap="gray", origin="lower", vmin=0, vmax=vmax)
    axes[0, 0].set_title(f"tSNR - Axial slice {slice_indices[0]}")
    axes[0, 1].imshow(tsnr[:, :, slice_indices[1]].T, cmap="gray", origin="lower", vmin=0, vmax=vmax)
    axes[0, 1].set_title(f"tSNR - Axial slice {slice_indices[1]}")
    axes[0, 2].imshow(tsnr[:, :, slice_indices[2]].T, cmap="gray", origin="lower", vmin=0, vmax=vmax)
    axes[0, 2].set_title(f"tSNR - Axial slice {slice_indices[2]}")
    axes[1, 0].imshow(mean_img[:, :, slice_indices[1]].T, cmap="gray", origin="lower")
    axes[1, 0].contour(
        masked_data[:, :, slice_indices[1]].T,
        levels=[0.5],
        colors="red",
        linewidths=1
    )
    axes[1, 0].set_title(f"Mean fMRI + Mask - Axial slice {slice_indices[1]}")
    axes[1, 1].hist(masked_tsnr, bins=50)
    axes[1, 1].set_title("Distribution of tSNR within the mask")
    axes[1, 1].set_xlabel("tSNR")
    axes[1, 1].set_ylabel("Number of voxels")
    axes[1, 2].axis("off")
    axes[1, 2].text(
        0.1, 0.8,
        f"Mean tSNR: {mean_tsnr: .2f}\n"
        f"Median tSNR: {median_tsnr: .2f}\n"
        f"Voxels within the mask: {voxel_count}",
        transform=axes[1, 2].transAxes
    )
    fig.tight_layout(rect=[0.02, 0.02, 0.96, 0.98], w_pad=2)
    cbar_ax = fig.add_axes([0.94, 0.58, 0.012, 0.328])
    fig.colorbar(im, cax=cbar_ax, label="tSNR")
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

if __name__ == "__main__":
    main()
