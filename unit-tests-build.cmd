@echo off
echo ========================================
echo BUILD YAXUNIT EXTENSION
echo Time: %date% %time%
echo ========================================

if not exist "%TESTS_REPO_PATH%" (
    echo ERROR: Tests repo not found: %TESTS_REPO_PATH%
    exit /b 1
)

echo Tests repo: %TESTS_REPO_PATH%
echo Extension: %TESTS_EXTENSION_NAME%
echo IB_PATH: %IB_PATH%
echo.

set "EXT_SRC_PATH=%TESTS_REPO_PATH%"

if not exist "%EXT_SRC_PATH%" (
    echo ERROR: Extension sources not found: %EXT_SRC_PATH%
    exit /b 1
)

echo Building extension %TESTS_EXTENSION_NAME% from %EXT_SRC_PATH%
echo.

vrunner compileext "%EXT_SRC_PATH%" %TESTS_EXTENSION_NAME% --ibconnection "/F%IB_PATH%" --updatedb --settings tools/vrunner.json

if %ERRORLEVEL% equ 0 (
    echo Extension compiled OK, loading into IB...
    vrunner updateext %TESTS_EXTENSION_NAME% --ibconnection "/F%IB_PATH%" --settings tools/vrunner.json
) else (
    echo ERROR: Extension build failed
)

set EXIT_CODE=%ERRORLEVEL%
echo.
echo ========================================
echo BUILD FINISHED. Exit code: %EXIT_CODE%
echo Time: %date% %time%
echo ========================================

if %EXIT_CODE% neq 0 (
    echo ERROR: Extension build failed with code %EXIT_CODE%
    exit /b %EXIT_CODE%
)

echo Extension %TESTS_EXTENSION_NAME% loaded successfully
exit /b 0
