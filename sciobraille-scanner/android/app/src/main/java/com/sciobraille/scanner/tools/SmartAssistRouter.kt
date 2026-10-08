package com.sciobraille.scanner.tools

enum class SmartAssistDestination {
    BRAILLE_STUDIO,
    TACTILE_EXPLORER,
    STORY_READER,
    LMS_PROGRESS,
    LEARN_HOME,
    SCANNER,
    LEARNER_PROFILE,
    HELP
}

data class SmartAssistDecision(
    val destination: SmartAssistDestination,
    val response: String
)

object SmartAssistRouter {
    fun route(command: String): SmartAssistDecision {
        val normalized = command.lowercase().trim()
        return when {
            normalized.contains("story") || normalized.contains("printed") || normalized.contains("read page") ->
                SmartAssistDecision(SmartAssistDestination.STORY_READER, "Opening Story Reader.")
            normalized.contains("text to braille") || normalized.contains("braille studio") || normalized.contains("convert") ->
                SmartAssistDecision(SmartAssistDestination.BRAILLE_STUDIO, "Opening Braille Studio.")
            normalized.contains("tactile") || normalized.contains("feel braille") || normalized.contains("explore cell") ->
                SmartAssistDecision(SmartAssistDestination.TACTILE_EXPLORER, "Opening tactile Braille exploration.")
            normalized.contains("progress") || normalized.contains("achievement") || normalized.contains("certificate") ->
                SmartAssistDecision(SmartAssistDestination.LMS_PROGRESS, "Opening your learning progress.")
            normalized.contains("profile") || normalized.contains("my name") ->
                SmartAssistDecision(SmartAssistDestination.LEARNER_PROFILE, "Opening your learner profile.")
            normalized.contains("scan") || normalized.contains("camera") || normalized.contains("read braille") ->
                SmartAssistDecision(SmartAssistDestination.SCANNER, "Opening the Braille scanner.")
            normalized.contains("learn") || normalized.contains("lesson") || normalized.contains("practice") ->
                SmartAssistDecision(SmartAssistDestination.LEARN_HOME, "Opening Braille lessons.")
            else -> SmartAssistDecision(
                SmartAssistDestination.HELP,
                "Try saying scan Braille, Braille Studio, Story Reader, tactile explorer, my progress, or learner profile."
            )
        }
    }
}
