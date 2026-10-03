package com.sciobraille.scanner.tools

import org.junit.Assert.assertEquals
import org.junit.Test

class SmartAssistRouterTest {
    @Test
    fun routesCoreAccessibleActionsDeterministically() {
        assertEquals(SmartAssistDestination.SCANNER, SmartAssistRouter.route("scan Braille").destination)
        assertEquals(SmartAssistDestination.STORY_READER, SmartAssistRouter.route("read my story book").destination)
        assertEquals(SmartAssistDestination.BRAILLE_STUDIO, SmartAssistRouter.route("convert text to Braille").destination)
        assertEquals(SmartAssistDestination.TACTILE_EXPLORER, SmartAssistRouter.route("feel Braille").destination)
        assertEquals(SmartAssistDestination.LMS_PROGRESS, SmartAssistRouter.route("show my progress").destination)
        assertEquals(SmartAssistDestination.LEARNER_PROFILE, SmartAssistRouter.route("open my profile").destination)
    }

    @Test
    fun unknownCommandReturnsHelpInsteadOfCrashing() {
        assertEquals(SmartAssistDestination.HELP, SmartAssistRouter.route("something unrelated").destination)
    }
}
