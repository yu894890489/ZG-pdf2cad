# 打发布 zip: PyArmor 混淆代码 + 内嵌Python + OpenSCAD, 不含 inputs/outputs 和明文源码
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$stage = Join-Path $env:TEMP 'tower2model_release'
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory $stage | Out-Null

# 1) 先混淆 (需 pyarmor: pip install pyarmor)
pyarmor gen -O (Join-Path $root 'build_obf') (Join-Path $root 'tower2model')
if ($LASTEXITCODE -ne 0) { throw 'pyarmor 混淆失败' }

# 2) 混淆包 + 运行时 (不含明文 tower2model)
Copy-Item (Join-Path $root 'build_obf\tower2model') (Join-Path $stage 'tower2model') -Recurse
Copy-Item (Join-Path $root 'build_obf\pyarmor_runtime_000000') (Join-Path $stage 'pyarmor_runtime_000000') -Recurse

# 3) 内嵌 Python (._pth 已指向上一级=发布根) + OpenSCAD + 文档
Copy-Item (Join-Path $root 'runtime') (Join-Path $stage 'runtime') -Recurse
Copy-Item (Join-Path $root 'README.md'),(Join-Path $root 'config.example.yaml'),(Join-Path $root 'run.bat') $stage
if (Test-Path (Join-Path $root 'vendor\openscad')) {
    New-Item -ItemType Directory (Join-Path $stage 'vendor') -Force | Out-Null
    Copy-Item (Join-Path $root 'vendor\openscad') (Join-Path $stage 'vendor\openscad') -Recurse
}

Compress-Archive -Path (Join-Path $stage '*') -DestinationPath (Join-Path $root 'tower2model_release.zip') -Force
Remove-Item $stage -Recurse -Force
Write-Host "done: $(Join-Path $root 'tower2model_release.zip')"
