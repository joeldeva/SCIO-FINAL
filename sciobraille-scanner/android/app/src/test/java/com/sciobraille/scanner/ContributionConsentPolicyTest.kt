package com.sciobraille.scanner

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ContributionConsentPolicyTest {
    @Test
    fun privateContributionDoesNotRequirePublicReleaseConsent() {
        assertTrue(
            ContributionConsentPolicy.canExport(
                correctedTextPresent = true,
                contentConfirmed = true,
                authorizedConfirmed = true,
                modelUseConfirmed = true,
                scope = ContributionPublicationScope.PRIVATE_TRAINING,
                publicReleaseConfirmed = false
            )
        )
    }

    @Test
    fun publicContributionRequiresSeparatePublicReleaseConsent() {
        assertFalse(
            ContributionConsentPolicy.canExport(
                correctedTextPresent = true,
                contentConfirmed = true,
                authorizedConfirmed = true,
                modelUseConfirmed = true,
                scope = ContributionPublicationScope.PUBLIC_DATASET,
                publicReleaseConfirmed = false
            )
        )
        assertTrue(
            ContributionConsentPolicy.canExport(
                correctedTextPresent = true,
                contentConfirmed = true,
                authorizedConfirmed = true,
                modelUseConfirmed = true,
                scope = ContributionPublicationScope.PUBLIC_DATASET,
                publicReleaseConfirmed = true
            )
        )
    }
}
