# BrailleEye LMS Accessibility QA

Date: 2026-09-19

Scope: code-level audit of the Android LMS screens. Scanner camera behavior is outside this LMS pass.

## Learn Home

Status: checked.

Fixes made:
- The learning-language selector has a descriptive label that includes the selected language.
- `My Progress` and `Milestones and Certificates` have explicit TalkBack descriptions.
- Level cards expose level, progress, completion count, unlocked state, and lock reason as text.
- Locked premium levels route to the Upgrade screen instead of failing silently.

## Dot Explorer

Status: checked.

Fixes made:
- Each dot is a 104 dp target with a description containing dot number, column, row, and explored state.
- Dots use text, border, fill, and `Done` state; they do not rely on color alone.
- Every dot has TTS and a distinct haptic pattern. The spoken instruction remains available through Repeat.
- Continue announces why it is locked until all six dots are explored.
- Voice toggle and Back controls have descriptive labels.

## Letter Builder

Status: checked.

Fixes made:
- Interactive Braille dots are large targets with position and active/visited state descriptions.
- Progress changes use a polite accessibility live region.
- Correct and incorrect actions have both spoken and haptic feedback.
- Premium letter cards announce that they are locked and route to the Upgrade screen.

## Letter Recognition

Status: checked.

Fixes made:
- Answer controls announce `Answer A`, `Answer B`, and so on, rather than only a letter label.
- The displayed Braille cell exposes a concise dot-pattern description.
- Feedback updates are announced through a polite live region and through TTS.
- Voice answer is explicitly labeled as an unavailable placeholder rather than appearing functional.

## Word Reading

Status: checked.

Fixes made:
- Guided answer choices have explicit answer labels.
- Braille cells provide dot-pattern descriptions, with spoken correct/incorrect feedback and haptics.
- Repeat is available for the current cell instruction.
- Challenge mode is explicitly labeled as a placeholder.

## Grade 2 Contractions

Status: checked.

Fixes made:
- Contraction cards describe the contraction, dot representation, meaning, and completion state.
- Display-only Braille cells expose one cell-level description to TalkBack instead of six disabled dot controls.
- Practice feedback is announced through TTS, haptics, and a polite live region.
- The screen includes Repeat Explanation and predictable Back navigation.

## Scan and Learn

Status: checked.

Fixes made:
- Controls use descriptive command labels: Explain first cell, Next cell, Read full text, and Save practice.
- Detected-cell explanations include letter and dot information in text and TTS.
- Confidence remains available as text, not only visual styling.
- Existing Scanner behavior is unchanged.

## Progress Screen

Status: checked.

Fixes made:
- Overall, level, streak, accuracy, and recent lesson information is present as readable text in addition to progress bars.
- Sync state and last sync time are text-based and Sync now has a descriptive label.
- A-Z accuracy entries remain accessible without charts.

## Upgrade Screen

Status: checked.

Fixes made:
- Locked features state the upgrade reason in text.
- Premium benefits are text items, not decorative graphics.
- Upgrade and Use school code have explicit labels. School-code submission states that verification is still required.

## Certificates And Milestones

Status: checked.

Fixes made:
- Certificates are structured text with the learner name, milestone, issue date, and BrailleEye LMS name.
- The complete certificate has a TalkBack description and is not image-only.
- Share has a text-share path. Download clearly states that PDF output is not implemented.

## Shared Component Fixes

- `BrailleCellView` now distinguishes accessibility modes:
  - Interactive cells expose each dot for exploration.
  - Display-only cells expose a single concise Braille-cell description and hide disabled dot children.
- Shared action buttons set a content description from their label and enforce a 48 dp minimum height.
- LMS feedback and progress changes use accessibility live regions where the screen changes dynamically.

## Remaining Recommendations

- Perform a manual TalkBack pass on a physical Android device with the device language set to English and with speech rate adjusted by the user.
- Test at Android Font size `Largest` and Display size `Largest`; programmatic layouts use 48 dp minimum controls, but the compact lesson headers should be reviewed on small screens.
- Test haptic behavior on at least one device without a vibrator and one device with system haptics disabled.
- Before Play Store release, add automated accessibility checks through Espresso AccessibilityChecks and complete a screen-reader usability session with Braille learners.

## Final QA Addendum

- Android lint completed with zero accessibility-category findings and zero errors.
- Scanner history actions now expose labeled Read, Copy, and Share controls.
- Camera, TalkBack reading order, largest font settings, and haptic behavior still require manual testing on physical Android devices. These items were not claimed as device-verified during this local pass.
