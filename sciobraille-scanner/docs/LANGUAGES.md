# Translation languages and capability limits

The Android picker has 133 entries. This is a catalog, not a claim that every entry is available offline or quality-validated. The configured server advertises available online targets at runtime; an unsupported target produces a clear error. Recognition remains English letters a–z for every target.

Offline model availability below follows the ML Kit supported-language list. The app verifies support against the installed SDK, and translation requires an explicitly downloaded model. Traditional Chinese is not silently substituted by Simplified Chinese. TTS availability is discovered from the phone’s voice engine; no universal voice list is promised.

The UI and learning content are primarily English. Source auto-detection is available at the provider API boundary, while scan translation intentionally uses English.

| Language | Code | Offline translation | Speech |
|---|---|---|---|
| English | `en` | Original text | Matching device voice required |
| Tamil | `ta` | Downloadable model | Matching device voice required |
| Hindi | `hi` | Downloadable model | Matching device voice required |
| Telugu | `te` | Downloadable model | Matching device voice required |
| Malayalam | `ml` | Online provider required | Matching device voice required |
| Kannada | `kn` | Downloadable model | Matching device voice required |
| Bengali | `bn` | Downloadable model | Matching device voice required |
| Marathi | `mr` | Downloadable model | Matching device voice required |
| Gujarati | `gu` | Downloadable model | Matching device voice required |
| Punjabi | `pa` | Online provider required | Matching device voice required |
| Urdu | `ur` | Downloadable model | Matching device voice required |
| Odia (Oriya) | `or` | Online provider required | Matching device voice required |
| Assamese | `as` | Online provider required | Matching device voice required |
| Sanskrit | `sa` | Online provider required | Matching device voice required |
| Afrikaans | `af` | Downloadable model | Matching device voice required |
| Albanian | `sq` | Downloadable model | Matching device voice required |
| Amharic | `am` | Online provider required | Matching device voice required |
| Arabic | `ar` | Downloadable model | Matching device voice required |
| Armenian | `hy` | Online provider required | Matching device voice required |
| Aymara | `ay` | Online provider required | Matching device voice required |
| Azerbaijani | `az` | Online provider required | Matching device voice required |
| Bambara | `bm` | Online provider required | Matching device voice required |
| Basque | `eu` | Online provider required | Matching device voice required |
| Belarusian | `be` | Downloadable model | Matching device voice required |
| Bhojpuri | `bho` | Online provider required | Matching device voice required |
| Bosnian | `bs` | Online provider required | Matching device voice required |
| Bulgarian | `bg` | Downloadable model | Matching device voice required |
| Catalan | `ca` | Downloadable model | Matching device voice required |
| Cebuano | `ceb` | Online provider required | Matching device voice required |
| Chichewa | `ny` | Online provider required | Matching device voice required |
| Chinese (Simplified) | `zh-CN` | Downloadable model | Matching device voice required |
| Chinese (Traditional) | `zh-TW` | Online provider required | Matching device voice required |
| Corsican | `co` | Online provider required | Matching device voice required |
| Croatian | `hr` | Downloadable model | Matching device voice required |
| Czech | `cs` | Downloadable model | Matching device voice required |
| Danish | `da` | Downloadable model | Matching device voice required |
| Dhivehi | `dv` | Online provider required | Matching device voice required |
| Dogri | `doi` | Online provider required | Matching device voice required |
| Dutch | `nl` | Downloadable model | Matching device voice required |
| Esperanto | `eo` | Downloadable model | Matching device voice required |
| Estonian | `et` | Downloadable model | Matching device voice required |
| Ewe | `ee` | Online provider required | Matching device voice required |
| Filipino | `tl` | Downloadable model | Matching device voice required |
| Finnish | `fi` | Downloadable model | Matching device voice required |
| French | `fr` | Downloadable model | Matching device voice required |
| Frisian | `fy` | Online provider required | Matching device voice required |
| Galician | `gl` | Downloadable model | Matching device voice required |
| Georgian | `ka` | Downloadable model | Matching device voice required |
| German | `de` | Downloadable model | Matching device voice required |
| Greek | `el` | Downloadable model | Matching device voice required |
| Guarani | `gn` | Online provider required | Matching device voice required |
| Haitian Creole | `ht` | Downloadable model | Matching device voice required |
| Hausa | `ha` | Online provider required | Matching device voice required |
| Hawaiian | `haw` | Online provider required | Matching device voice required |
| Hebrew | `iw` | Downloadable model | Matching device voice required |
| Hmong | `hmn` | Online provider required | Matching device voice required |
| Hungarian | `hu` | Downloadable model | Matching device voice required |
| Icelandic | `is` | Downloadable model | Matching device voice required |
| Igbo | `ig` | Online provider required | Matching device voice required |
| Ilocano | `ilo` | Online provider required | Matching device voice required |
| Indonesian | `id` | Downloadable model | Matching device voice required |
| Irish | `ga` | Downloadable model | Matching device voice required |
| Italian | `it` | Downloadable model | Matching device voice required |
| Japanese | `ja` | Downloadable model | Matching device voice required |
| Javanese | `jw` | Online provider required | Matching device voice required |
| Kazakh | `kk` | Online provider required | Matching device voice required |
| Khmer | `km` | Online provider required | Matching device voice required |
| Kinyarwanda | `rw` | Online provider required | Matching device voice required |
| Konkani | `gom` | Online provider required | Matching device voice required |
| Korean | `ko` | Downloadable model | Matching device voice required |
| Krio | `kri` | Online provider required | Matching device voice required |
| Kurdish (Kurmanji) | `ku` | Online provider required | Matching device voice required |
| Kurdish (Sorani) | `ckb` | Online provider required | Matching device voice required |
| Kyrgyz | `ky` | Online provider required | Matching device voice required |
| Lao | `lo` | Online provider required | Matching device voice required |
| Latin | `la` | Online provider required | Matching device voice required |
| Latvian | `lv` | Downloadable model | Matching device voice required |
| Lingala | `ln` | Online provider required | Matching device voice required |
| Lithuanian | `lt` | Downloadable model | Matching device voice required |
| Luganda | `lg` | Online provider required | Matching device voice required |
| Luxembourgish | `lb` | Online provider required | Matching device voice required |
| Macedonian | `mk` | Downloadable model | Matching device voice required |
| Maithili | `mai` | Online provider required | Matching device voice required |
| Malagasy | `mg` | Online provider required | Matching device voice required |
| Malay | `ms` | Downloadable model | Matching device voice required |
| Maltese | `mt` | Downloadable model | Matching device voice required |
| Maori | `mi` | Online provider required | Matching device voice required |
| Meiteilon (Manipuri) | `mni-Mtei` | Online provider required | Matching device voice required |
| Mizo | `lus` | Online provider required | Matching device voice required |
| Mongolian | `mn` | Online provider required | Matching device voice required |
| Myanmar | `my` | Online provider required | Matching device voice required |
| Nepali | `ne` | Online provider required | Matching device voice required |
| Norwegian | `no` | Downloadable model | Matching device voice required |
| Oromo | `om` | Online provider required | Matching device voice required |
| Pashto | `ps` | Online provider required | Matching device voice required |
| Persian | `fa` | Downloadable model | Matching device voice required |
| Polish | `pl` | Downloadable model | Matching device voice required |
| Portuguese | `pt` | Downloadable model | Matching device voice required |
| Quechua | `qu` | Online provider required | Matching device voice required |
| Romanian | `ro` | Downloadable model | Matching device voice required |
| Russian | `ru` | Downloadable model | Matching device voice required |
| Samoan | `sm` | Online provider required | Matching device voice required |
| Scots Gaelic | `gd` | Online provider required | Matching device voice required |
| Sepedi | `nso` | Online provider required | Matching device voice required |
| Serbian | `sr` | Online provider required | Matching device voice required |
| Sesotho | `st` | Online provider required | Matching device voice required |
| Shona | `sn` | Online provider required | Matching device voice required |
| Sindhi | `sd` | Online provider required | Matching device voice required |
| Sinhala | `si` | Online provider required | Matching device voice required |
| Slovak | `sk` | Downloadable model | Matching device voice required |
| Slovenian | `sl` | Downloadable model | Matching device voice required |
| Somali | `so` | Online provider required | Matching device voice required |
| Spanish | `es` | Downloadable model | Matching device voice required |
| Sundanese | `su` | Online provider required | Matching device voice required |
| Swahili | `sw` | Downloadable model | Matching device voice required |
| Swedish | `sv` | Downloadable model | Matching device voice required |
| Tajik | `tg` | Online provider required | Matching device voice required |
| Tatar | `tt` | Online provider required | Matching device voice required |
| Thai | `th` | Downloadable model | Matching device voice required |
| Tigrinya | `ti` | Online provider required | Matching device voice required |
| Tsonga | `ts` | Online provider required | Matching device voice required |
| Turkish | `tr` | Downloadable model | Matching device voice required |
| Turkmen | `tk` | Online provider required | Matching device voice required |
| Twi | `ak` | Online provider required | Matching device voice required |
| Ukrainian | `uk` | Downloadable model | Matching device voice required |
| Uyghur | `ug` | Online provider required | Matching device voice required |
| Uzbek | `uz` | Online provider required | Matching device voice required |
| Vietnamese | `vi` | Downloadable model | Matching device voice required |
| Welsh | `cy` | Downloadable model | Matching device voice required |
| Xhosa | `xh` | Online provider required | Matching device voice required |
| Yiddish | `yi` | Online provider required | Matching device voice required |
| Yoruba | `yo` | Online provider required | Matching device voice required |
| Zulu | `zu` | Online provider required | Matching device voice required |

Primary references: [ML Kit languages](https://developers.google.com/ml-kit/language/translation/translation-language-support), [ML Kit Android integration](https://developers.google.com/ml-kit/language/translation/android), [Google v2 API](https://docs.cloud.google.com/translate/docs/reference/rest/v2/translate), [LibreTranslate API](https://docs.libretranslate.com/api/).
