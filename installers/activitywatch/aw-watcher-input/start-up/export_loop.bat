@echo off
:: Schedule the export command to run every n seconds
for /L %%i in (0,0,1) do (
    curl -o export.json http://localhost:5600/api/0/export
    timeout /t 18
)