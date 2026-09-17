package com.sciobraille.scanner.lms

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "lessons")
data class LessonEntity(
    @PrimaryKey val id: String,
    val level: Int,
    val title: String,
    val description: String,
    val contentJson: String,
    val orderIndex: Int,
    val isPremium: Boolean,
    val languageCode: String = Language.ENGLISH.code
)
