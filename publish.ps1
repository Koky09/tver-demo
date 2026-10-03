# Публикация демо на GitHub Pages: коммит -> репозиторий Koky09/tver-demo -> push -> Pages (/docs).
# Повторный запуск просто отправляет новые изменения.
$ErrorActionPreference = 'Stop'
$Owner = 'Koky09'; $Repo = 'tver-demo'
Set-Location $PSScriptRoot

# .env с токеном бота не должен попасть в репозиторий
if (git ls-files --cached -- .env) { throw '.env попал в индекс git — публикация остановлена' }

git add -A
if (git diff --cached --name-only) {
    git commit -q -m "Update booking demos`n`nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
}

$cred = "protocol=https`nhost=github.com`n`n" | git credential-manager get
$tok = ($cred | Where-Object { $_ -like 'password=*' }) -replace '^password=', ''
if (-not $tok) { throw 'Нет сохранённого входа в GitHub' }
$h = @{ Authorization = "Bearer $tok"; Accept = 'application/vnd.github+json'; 'User-Agent' = $Repo }
$api = "https://api.github.com/repos/$Owner/$Repo"

try { Invoke-RestMethod $api -Headers $h | Out-Null; 'Репозиторий уже есть' }
catch {
    Invoke-RestMethod -Method Post https://api.github.com/user/repos -Headers $h -ContentType 'application/json' `
        -Body (@{ name = $Repo; description = 'Онлайн-запись для автосервисов и детейлингов (демо)'; private = $false } | ConvertTo-Json) | Out-Null
    'Репозиторий создан'
}

if (-not (git remote)) { git remote add origin "https://github.com/$Owner/$Repo.git" }
git push -u origin main

try { Invoke-RestMethod "$api/pages" -Headers $h | Out-Null; 'Pages уже включён' }
catch {
    Invoke-RestMethod -Method Post "$api/pages" -Headers $h -ContentType 'application/json' `
        -Body (@{ source = @{ branch = 'main'; path = '/docs' } } | ConvertTo-Json) | Out-Null
    'Pages включён'
}
"Готово: https://$($Owner.ToLower()).github.io/$Repo/"
