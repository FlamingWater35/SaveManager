Set-Location -Path "C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager"

conda activate

conda activate "C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager\.conda"

black SaveManager.py

pyivf-make_version --source-format yaml --metadata-source version_info.yml --outfile app_version_info.txt

pyinstaller --onefile --windowed --upx-dir "C:\Users\Admin\Documents\work\projects\upx-4.2.4-win64\upx-4.2.4-win64" --icon="C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager\docs\icon.ico" --distpath "C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager\main" --add-data "C:\Users\Admin\Documents\work\projects\VSCodeProjects\SaveManager\docs;docs" --version-file app_version_info.txt --clean SaveManager.py

Start-Sleep -Seconds 3