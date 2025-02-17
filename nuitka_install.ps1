Set-Location -Path "C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager"

conda activate

conda activate "C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager\.conda"

black SaveManager.py

nuitka --onefile --standalone --windows-console-mode=disable --file-version=2.5.2.0 --product-version=2.5.2.0 --file-description="Save Manager" --product-name="Save Manager" --copyright="© 2025 Flaming Water" --windows-icon-from-ico="C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager\docs\icon.ico" --include-data-dir="C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager\docs=docs" --include-data-files="C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager\docs\openh264-1.8.0-win64.dll=docs/openh264-1.8.0-win64.dll" --output-dir="C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager\main" --enable-plugin=upx --upx-binary="C:\Users\Admin\Documents\work\projects\upx-4.2.4-win64\upx-4.2.4-win64" --lto=yes --clang --remove-output SaveManager.py

Start-Sleep -Seconds 3