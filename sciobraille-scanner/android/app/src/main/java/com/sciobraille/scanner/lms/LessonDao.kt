package com.sciobraille.scanner.lms

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface LessonDao {
    @Query("SELECT * FROM lessons WHERE level = :level ORDER BY orderIndex ASC")
    suspend fun getLessonsByLevel(level: Int): List<LessonEntity>

    @Query("SELECT * FROM lessons WHERE languageCode = :languageCode ORDER BY level ASC, orderIndex ASC")
    suspend fun getLessonsByLanguage(languageCode: String): List<LessonEntity>

    @Query("SELECT * FROM lessons ORDER BY level ASC, orderIndex ASC")
    suspend fun getAllLessons(): List<LessonEntity>

    @Query("SELECT * FROM lessons WHERE id = :lessonId LIMIT 1")
    suspend fun getLessonById(lessonId: String): LessonEntity?

    @Query("SELECT COUNT(*) FROM lessons")
    suspend fun countLessons(): Int

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLessons(lessons: List<LessonEntity>)
}
