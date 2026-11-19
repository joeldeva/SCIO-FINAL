# User Contribution Intake

This directory defines the private intake boundary for voluntary Sciobraille
training samples. Actual contribution packages, images, metadata, manifests,
and annotations are intentionally excluded from Git.

## Intake

1. Receive the ZIP created by the Android **Improve the model** action.
2. Keep received packages in a private, access-controlled folder.
3. From the repository root, validate and quarantine them:

   ```powershell
   python sciobraille-model-lab/scripts/import_user_contributions.py C:\private\received
   ```

4. Review every quarantined sample for consent, personal information, image
   quality, transcript correctness, duplicate/near-duplicate leakage, and label
   correctness.
5. Create or correct YOLO boxes manually. The predicted boxes in
   `metadata.json` are review hints, never ground truth.
6. Set `approved_for_training` only after review. Promotion into a future
   versioned master dataset must use a separate audited build script.

## Rules

- Never commit received user images or metadata to the public repository.
- A `private_training` contribution must never be published as source data.
- A `public_dataset` contribution is only eligible for later publication. It
  still requires privacy review, annotation review, documented dataset terms,
  and an explicit release decision before any source data becomes public.
- Never merge quarantine directly into `master_v2`.
- Preserve the contribution ID and consent version in private provenance.
- Honor deletion requests for stored source packages using contribution ID.
- Keep all variants from the same page/capture sequence in one dataset split.
- Run exact and perceptual duplicate checks before promotion.
- Raw model text must remain separate from user-corrected ground truth.

The importer rejects malformed archives, invalid consent records, corrupt
images, duplicate SHA256 images, invalid labels, and out-of-range boxes.
