package com.sciobraille.scanner.lms

import org.json.JSONArray
import org.json.JSONObject

data class LessonContent(
    val type: String,
    val goal: String,
    val dots: List<Int> = emptyList(),
    val cells: List<List<Int>> = emptyList(),
    val letter: String? = null,
    val word: String? = null,
    val contraction: String? = null,
    val displaySymbol: String? = null,
    val meaning: String? = null,
    val exampleSentence: String? = null,
    val grade: Int? = null,
    val questions: List<LessonQuestion> = emptyList()
) {
    fun toJson(): String {
        return JSONObject()
            .put("type", type)
            .put("goal", goal)
            .put("dots", JSONArray(dots))
            .put("cells", JSONArray(cells.map { JSONArray(it) }))
            .put("letter", letter)
            .put("word", word)
            .put("contraction", contraction)
            .put("displaySymbol", displaySymbol)
            .put("meaning", meaning)
            .put("exampleSentence", exampleSentence)
            .put("grade", grade)
            .put("questions", JSONArray(questions.map { it.toJson() }))
            .toString()
    }

    companion object {
        fun fromJson(raw: String): LessonContent {
            val json = JSONObject(raw)
            return LessonContent(
                type = json.optString("type"),
                goal = json.optString("goal"),
                dots = json.optJSONArray("dots").toIntList(),
                cells = json.optJSONArray("cells").toNestedIntList(),
                letter = json.optString("letter").takeIf { it.isNotBlank() },
                word = json.optString("word").takeIf { it.isNotBlank() },
                contraction = json.optString("contraction").takeIf { it.isNotBlank() },
                displaySymbol = json.optString("displaySymbol").takeIf { it.isNotBlank() },
                meaning = json.optString("meaning").takeIf { it.isNotBlank() },
                exampleSentence = json.optString("exampleSentence").takeIf { it.isNotBlank() },
                grade = json.optInt("grade").takeIf { json.has("grade") && !json.isNull("grade") },
                questions = json.optJSONArray("questions").toQuestions()
            )
        }
    }
}

data class LessonQuestion(
    val id: String,
    val prompt: String,
    val correctAnswer: String,
    val options: List<String> = emptyList()
) {
    fun toJson(): JSONObject {
        return JSONObject()
            .put("id", id)
            .put("prompt", prompt)
            .put("correctAnswer", correctAnswer)
            .put("options", JSONArray(options))
    }

    companion object {
        fun fromJson(json: JSONObject): LessonQuestion {
            return LessonQuestion(
                id = json.optString("id"),
                prompt = json.optString("prompt"),
                correctAnswer = json.optString("correctAnswer"),
                options = json.optJSONArray("options").toStringList()
            )
        }
    }
}

private fun JSONArray?.toIntList(): List<Int> {
    if (this == null) return emptyList()
    return buildList {
        for (index in 0 until length()) add(optInt(index))
    }
}

private fun JSONArray?.toStringList(): List<String> {
    if (this == null) return emptyList()
    return buildList {
        for (index in 0 until length()) add(optString(index))
    }
}

private fun JSONArray?.toNestedIntList(): List<List<Int>> {
    if (this == null) return emptyList()
    return buildList {
        for (index in 0 until length()) add(optJSONArray(index).toIntList())
    }
}

private fun JSONArray?.toQuestions(): List<LessonQuestion> {
    if (this == null) return emptyList()
    return buildList {
        for (index in 0 until length()) {
            val item = optJSONObject(index) ?: continue
            add(LessonQuestion.fromJson(item))
        }
    }
}
