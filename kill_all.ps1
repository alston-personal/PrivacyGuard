Get-CimInstance Win32_Process | ForEach-Object { 
    if ($_.CommandLine -like "*main.py*") {
        Write-Host "Killing process $($_.ProcessId): $($_.CommandLine)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Killing python process $($_.Id)"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Get-Process pythonw* -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Killing pythonw process $($_.Id)"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
