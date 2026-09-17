$ErrorActionPreference = "Stop"
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
$gradleBat = Get-ChildItem -Path "$env:USERPROFILE\.gradle\wrapper\dists\gradle-9.0.0-bin" -Recurse -Filter "gradle.bat" | Select-Object -First 1
if (-not $gradleBat) {
    throw "Cached Gradle 9.0.0 gradle.bat was not found."
}
& $gradleBat.FullName @args
