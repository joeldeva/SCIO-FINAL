package com.sciobraille.scanner.lms

import android.content.Context
import androidx.room.Database
import androidx.room.migration.Migration
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [
        LessonEntity::class,
        LessonProgressEntity::class,
        UserScoreEntity::class,
        StreakEntity::class
    ],
    version = 3,
    exportSchema = false
)
abstract class LmsDatabase : RoomDatabase() {
    abstract fun lessonDao(): LessonDao
    abstract fun lessonProgressDao(): LessonProgressDao
    abstract fun userScoreDao(): UserScoreDao
    abstract fun streakDao(): StreakDao

    companion object {
        @Volatile
        private var INSTANCE: LmsDatabase? = null

        fun getInstance(context: Context): LmsDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    LmsDatabase::class.java,
                    "brailleeye_lms.db"
                ).addMigrations(MIGRATION_1_2, MIGRATION_2_3).build().also { INSTANCE = it }
            }
        }

        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("ALTER TABLE lesson_progress ADD COLUMN syncStatus TEXT NOT NULL DEFAULT 'NOT_SYNCED'")
                database.execSQL("ALTER TABLE lesson_progress ADD COLUMN lastSyncedAt INTEGER")
                database.execSQL("ALTER TABLE user_scores ADD COLUMN syncStatus TEXT NOT NULL DEFAULT 'NOT_SYNCED'")
                database.execSQL("ALTER TABLE user_scores ADD COLUMN lastSyncedAt INTEGER")
                database.execSQL("ALTER TABLE streaks ADD COLUMN syncStatus TEXT NOT NULL DEFAULT 'NOT_SYNCED'")
                database.execSQL("ALTER TABLE streaks ADD COLUMN lastSyncedAt INTEGER")
            }
        }

        private val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("ALTER TABLE lessons ADD COLUMN languageCode TEXT NOT NULL DEFAULT 'en'")
            }
        }
    }
}
