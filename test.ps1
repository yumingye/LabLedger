. "$PSScriptRoot\scripts\env.ps1"
& .\.venv\Scripts\python -m pytest -v --basetemp=.runtime/pytest -o cache_dir=.cache/pytest --junitxml=reports/junit.xml
exit $LASTEXITCODE
