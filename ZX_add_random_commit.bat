@echo off
setlocal

:: Generate a random number
set /a "randNum=%random% %% 2"

:: Set the base file name
set "baseFileName=zhiqingxurandomfile"

:: Set the full file name
set "fullFileName=%baseFileName%%randNum%.txt"

if exist "%fullFileName%" (
    :: If the file exists, delete it
    del /F /Q "%fullFileName%"

    :: Stage the deletion for commit
    git add --all

    :: Commit the deletion
    git commit -m "Deleted %fullFileName%"

) else (
    :: If the file doesn't exist, create it
    echo.>"%fullFileName%"

    :: Stage the new file for commit
    git add --all

    :: Commit the new file
    git commit -m "Created %fullFileName%"
)

:: Push the commit to the remote repository
git push

endlocal
