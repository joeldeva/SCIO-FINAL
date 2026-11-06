package com.sciobraille.scanner.tools

import android.app.AlertDialog
import android.content.Context
import android.text.Editable
import android.text.TextWatcher
import android.widget.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

class LanguagePicker(private val context: Context, private val scope: CoroutineScope,
    private val repository: TranslationRepository, private val local: MlKitTranslationFallback,
    private val onSelect: (AppLanguage) -> Unit) {
    private val preferences = context.getSharedPreferences("language_picker", Context.MODE_PRIVATE)
    fun show() {
        var installed = emptySet<String>()
        var online: Set<String>? = null
        var visible = emptyList<AppLanguage>()
        var query = ""
        val column = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL; setPadding(24,12,24,12) }
        val search = EditText(context).apply { hint = "Search language or script"; contentDescription = "Search translation languages"; setSingleLine(true) }
        val note = TextView(context).apply { text = "Tap to select. Long press for favorites and offline downloads. Translation does not change the Braille writing system."; setPadding(0,12,0,16) }
        val list = ListView(context)
        val adapter = ArrayAdapter<String>(context, android.R.layout.simple_list_item_1, mutableListOf())
        list.adapter = adapter
        column.addView(search); column.addView(note)
        column.addView(list, LinearLayout.LayoutParams(-1,(context.resources.displayMetrics.heightPixels*.48f).toInt()))
        val dialog = AlertDialog.Builder(context).setTitle("Translation languages").setView(column).setNegativeButton("Close",null).create()
        fun refresh() {
            val favorites = preferences.getStringSet("favorites",emptySet()).orEmpty()
            val recent = preferences.getString("recent","").orEmpty().split(',')
            visible = AppLanguage.entries.filter { "${it.displayName} ${it.nativeName} ${it.languageCode}".contains(query,true) }
                .sortedWith(compareBy<AppLanguage> { if (it.languageCode in favorites) 0 else if (it.languageCode in recent) 1 else 2 }.thenBy { it.displayName })
            adapter.clear(); adapter.addAll(visible.map { language ->
                val offline = when {
                    language == AppLanguage.ENGLISH -> "Original text"
                    language.offlineCode in installed -> "Offline model installed"
                    local.supports(language) -> "Offline model downloadable"
                    else -> "Requires online translation"
                }
                val service = online?.let { if (language.backendCode in it) "Online available" else "Online not configured" } ?: "Online availability unknown"
                "${if(language.languageCode in favorites) "★ " else ""}${language.displayName} · ${language.nativeName}\n$offline · $service"
            })
        }
        search.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { query=s.toString(); refresh() }
            override fun afterTextChanged(s: Editable?) = Unit
        })
        list.setOnItemClickListener { _,_,position,_ ->
            val language=visible[position]
            val recent=(listOf(language.languageCode)+preferences.getString("recent","").orEmpty().split(',')).distinct().take(8)
            preferences.edit().putString("recent",recent.joinToString(",")).apply()
            onSelect(language); dialog.dismiss()
        }
        list.setOnItemLongClickListener { _,_,position,_ ->
            val language=visible[position]
            val favorites=preferences.getStringSet("favorites",emptySet()).orEmpty().toMutableSet()
            val actions=mutableListOf(if(language.languageCode in favorites) "Remove favorite" else "Add favorite")
            if(local.supports(language) && language!=AppLanguage.ENGLISH) actions += if(language.offlineCode in installed) "Delete offline model" else "Download offline model (uses data)"
            AlertDialog.Builder(context).setTitle(language.displayName).setItems(actions.toTypedArray()) { _,index ->
                if(index==0) {
                    if(!favorites.add(language.languageCode)) favorites.remove(language.languageCode)
                    preferences.edit().putStringSet("favorites",favorites).apply(); refresh()
                } else scope.launch {
                    note.text="Updating ${language.displayName} model…"
                    runCatching { if(language.offlineCode in installed) local.delete(language) else local.download(language); installed=local.installedCodes() }
                        .onFailure { Toast.makeText(context,"Model update failed. Check connectivity and storage.",Toast.LENGTH_LONG).show() }
                    note.text="${installed.size} offline models installed. Long press a language to manage downloads."; refresh()
                }
            }.show(); true
        }
        refresh(); dialog.show()
        scope.launch { runCatching { local.installedCodes() }.onSuccess { installed=it }; refresh() }
        scope.launch { runCatching { repository.languages() }.onSuccess { online=it }; refresh() }
    }
}
