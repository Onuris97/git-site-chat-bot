@echo off
echo ========================================
echo RUN YAXUNIT UNIT TESTS
echo Time: %date% %time%
echo ========================================

if not exist "%UNIT_TEST_CONFIG%" (
    echo ERROR: Config file not found: %UNIT_TEST_CONFIG%
    exit /b 1
)

echo Config: %UNIT_TEST_CONFIG%
echo IB_PATH: %IB_PATH%
echo 1C version: %V8_VERSION%
echo.

set "ONEC_EXE_PATH=C:\Program Files\1cv8\%V8_VERSION%\bin\1cv8c.exe"

if not exist "%ONEC_EXE_PATH%" (
    echo ERROR: 1C executable not found: %ONEC_EXE_PATH%
    exit /b 1
)

echo Executable: %ONEC_EXE_PATH%
echo.

for %%F in ("%UNIT_TEST_CONFIG%") do set "CONFIG_ABS_PATH=%%~fF"

if not exist "build\reports\junit" mkdir "build\reports\junit"
if not exist "build\logs" mkdir "build\logs"

echo Running unit tests...
echo Config: %CONFIG_ABS_PATH%
echo.

"%ONEC_EXE_PATH%" ENTERPRISE /F"%IB_PATH%" /N Admin /C "RunUnitTests=%CONFIG_ABS_PATH%"

set EXIT_CODE=%ERRORLEVEL%
echo.
echo ========================================
echo UNIT TESTS FINISHED. Exit code: %EXIT_CODE%
echo Time: %date% %time%
echo ========================================

if %EXIT_CODE% neq 0 (
    echo WARNING: Unit tests finished with errors
    exit /b %EXIT_CODE%
)

echo Unit tests passed successfully
exit /b 0
