# Sciobraille Privacy Policy Source

Effective date: 19 November 2026

The publishable policy is maintained at `../../docs/privacy-policy.html` and is
linked inside the Android About screen. Version 1.3.0 is offline-first:

- Braille recognition runs with the bundled V2 TFLite model.
- Camera frames and selected Braille images are never uploaded automatically.
- Temporary scanner images are deleted after processing or when the app closes.
- Scan history, learner profile, LMS progress, scores, streaks, milestones,
  settings, and certificates remain on the device.
- No Sciobraille account, advertising SDK, analytics SDK, or cloud sync is
  enabled.
- Android TTS runs through the device speech engine.
- Google ML Kit may download a translation model when the user selects a new
  language; the downloaded model can then run offline.
- Android sharing sends selected content only to the app chosen by the user.
- The optional **Improve the model** action creates a contribution ZIP only
  after the user reviews the transcript and provides dedicated affirmative
  consent. The ZIP includes the model-facing image and training metadata, and
  remains offline until the user chooses a recipient through Android sharing.
- Private model improvement is selected by default. A contribution is eligible
  for a future publicly downloadable research dataset only when the user
  separately selects **Public dataset contribution** and confirms public
  release. Eligibility does not bypass privacy, annotation, or release review.

Support contact: `devajoel8@gmail.com`

Expected public URL after enabling GitHub Pages from `/docs`:
`https://joeldeva.github.io/SCIO-FINAL/privacy-policy.html`
