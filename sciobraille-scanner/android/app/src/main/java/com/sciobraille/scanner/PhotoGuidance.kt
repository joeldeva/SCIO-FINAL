package com.sciobraille.scanner

object PhotoGuidance {
    val doItems = listOf(
        "Clean the camera lens before scanning.",
        "Place the Braille page flat on a plain, stable surface.",
        "Hold the phone directly above and parallel to the page.",
        "Fill most of the frame with the Braille area while keeping every line visible.",
        "Use light from the upper side of the page so raised dots create clear shadows.",
        "Tap to focus, hold the phone steady, and keep the image sharp.",
        "Use Automatic side detection unless you know which side of the page is facing the camera."
    )

    val avoidItems = listOf(
        "Do not use flat overhead light that removes dot shadows.",
        "Avoid glare, deep hand shadows, blur, digital zoom, and steep camera angles.",
        "Do not crop the first or last Braille cell or cut off a line.",
        "Keep fingers, patterned backgrounds, and unrelated objects outside the Braille area.",
        "Do not contribute images containing faces, identity documents, addresses, medical records, or school records."
    )

    val spokenSummary: String = buildString {
        append("For the clearest Braille scan. ")
        append(doItems.joinToString(" "))
        append(" Things to avoid. ")
        append(avoidItems.joinToString(" "))
    }
}

enum class ContributionPublicationScope(val metadataValue: String) {
    PRIVATE_TRAINING("private_training"),
    PUBLIC_DATASET("public_dataset")
}

internal object ContributionConsentPolicy {
    fun canExport(
        correctedTextPresent: Boolean,
        contentConfirmed: Boolean,
        authorizedConfirmed: Boolean,
        modelUseConfirmed: Boolean,
        scope: ContributionPublicationScope,
        publicReleaseConfirmed: Boolean
    ): Boolean = correctedTextPresent &&
        contentConfirmed &&
        authorizedConfirmed &&
        modelUseConfirmed &&
        (scope != ContributionPublicationScope.PUBLIC_DATASET || publicReleaseConfirmed)
}
