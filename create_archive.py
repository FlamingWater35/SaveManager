import py7zr
import shutil


output_archive = "C:\\Users\\Admin\\Documents\\work\\projects\\VSCodeProjects\\SaveManager\\main\\source.7z"
distpath = "C:\\Users\\Admin\\Documents\\work\\projects\\VSCodeProjects\\SaveManager\\main\\SaveManager.dist"
compression_filters = [{'id': py7zr.FILTER_LZMA2, 'preset': py7zr.PRESET_DEFAULT}]

def main():
    with py7zr.SevenZipFile(output_archive, mode='w', filters=compression_filters) as archive:
        archive.writeall(path=distpath, arcname="")
    shutil.rmtree(distpath)

if __name__ == "__main__":
    main()