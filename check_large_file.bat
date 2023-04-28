@echo off
setlocal

:: Set the size limit in bytes (100MB = 104857600 bytes)
set "sizeLimit=104857600"

:: Create/overwrite the output file
echo List of files larger than 100MB > output.txt

:: Loop through each file in the current directory and its subdirectories
for /R %%F in (*) do (
    :: If the file size is greater than the limit, append its path to the output file
    if %%~zF GTR %sizeLimit% (
        echo %%F >> output.txt
    )
)

endlocal