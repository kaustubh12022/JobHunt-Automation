@echo off
echo This will open ports 5173 and 5000 for your local network.
echo (Required for mobile access)
echo.
netsh advfirewall firewall add rule name="AutoApply Frontend 5173" dir=in action=allow protocol=TCP localport=5173
netsh advfirewall firewall add rule name="AutoApply Backend 5000" dir=in action=allow protocol=TCP localport=5000
echo.
echo Done! Ports 5173 and 5000 are now accessible from your phone.
pause
