. "$PSScriptRoot\scripts\env.ps1"
if (!(Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
if ($env:LABLEDGER_WHEELHOUSE) {
    & .\.venv\Scripts\python -m pip install --no-index --find-links $env:LABLEDGER_WHEELHOUSE -r requirements-lock.txt
} else {
    & .\.venv\Scripts\python -m pip install -r requirements-lock.txt
}
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check network access or LABLEDGER_WHEELHOUSE.' }
& .\.venv\Scripts\python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Installed dependencies are inconsistent.' }
