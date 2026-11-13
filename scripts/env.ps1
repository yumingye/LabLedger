$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
@('.runtime/tmp','.cache/pip','.cache/pycache','.cache/powershell','.runtime/matplotlib','.runtime/streamlit','.runtime/home','.runtime/appdata','data','logs','exports','reports','screenshots') | ForEach-Object { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
$env:TEMP = "$ProjectRoot\.runtime\tmp"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = "$ProjectRoot\.cache\pip"
$env:PYTHONPYCACHEPREFIX = "$ProjectRoot\.cache\pycache"
$env:MPLCONFIGDIR = "$ProjectRoot\.runtime\matplotlib"
$env:STREAMLIT_CONFIG_DIR = "$ProjectRoot\.runtime\streamlit"
$env:USERPROFILE = "$ProjectRoot\.runtime\home"
$env:APPDATA = "$ProjectRoot\.runtime\appdata"
$env:LOCALAPPDATA = "$ProjectRoot\.runtime\appdata"
$env:PLAYWRIGHT_BROWSERS_PATH = "$ProjectRoot\.runtime\browsers"
$env:PSModuleAnalysisCachePath = "$ProjectRoot\.cache\powershell\ModuleAnalysisCache"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = 'false'
$env:PYTHONUTF8 = '1'
