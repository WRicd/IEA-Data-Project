py -3 -m venv "$PSScriptRoot\..\.venv"
& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m pip install -r "$PSScriptRoot\..\requirements.txt"
